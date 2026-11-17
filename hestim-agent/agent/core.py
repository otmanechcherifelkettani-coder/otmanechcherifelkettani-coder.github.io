"""The agent turn: replay the conversation, call Claude, run tools, return the reply text.

The Claude transcript for each conversation is stored append-only (api_messages) with the exact
content blocks the API returned, so prompt caching hits and nothing in history is ever rewritten.
"""
import json
import logging
import threading
from collections import defaultdict

import anthropic

import config
import db
from agent import tools
from agent.prompt import system_prompt

log = logging.getLogger("hestim.agent")

MAX_TOOL_ROUNDS = 8
FALLBACK_REPLY = {
    "fr": "Merci pour votre message. Un membre de l'équipe HESTIM va vous répondre ici très vite.",
}

_client = None
_conv_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic()
    return _client


def set_client(c):
    """Inject a fake client in tests / simulations."""
    global _client
    _client = c


def _call_claude(messages):
    extra = {}
    if config.SUPPORTS_FALLBACKS:
        # Server-side fallback: if a safety classifier declines, the API re-runs the
        # request on Anthropic's recommended fallback model inside the same call.
        extra = {"betas": ["server-side-fallback-2026-07-01"], "fallbacks": "default"}
    return client().beta.messages.create(
        model=config.MODEL,
        max_tokens=8000,
        system=system_prompt(),
        tools=tools.TOOLS,
        messages=messages,
        output_config={"effort": config.EFFORT},
        cache_control={"type": "ephemeral"},
        **extra,
    )


def _blocks_to_params(content):
    out = []
    for b in content:
        if b.type == "fallback":  # marker of a server-side model switch, not conversation content
            continue
        d = b.model_dump(exclude_none=True, mode="json") if hasattr(b, "model_dump") else dict(b)
        out.append(d)
    return out


def _context_block(contact: dict) -> dict:
    profile = {k: contact.get(k) for k in ("name", "kind", "language", "lead_status", "program_interest",
                                             "level", "intake", "city", "channel")}
    return {"type": "text",
            "text": "[NOTE INTERNE] Fiche contact actuelle : " + json.dumps(profile, ensure_ascii=False)}


def run_turn(conv_id: int, inbound_text: str | None, internal_note: str | None = None) -> str | None:
    """Process one inbound message (or an internal follow-up nudge). Returns text to send, or None."""
    with _conv_locks[conv_id]:
        conv = db.get_conversation(conv_id)
        if conv is None or conv["handler"] != "ai":
            return None
        contact = db.get_contact(conv["contact_id"])

        user_blocks = [_context_block(contact)]
        for note in json.loads(conv.get("pending_human_notes") or "[]"):
            user_blocks.append({"type": "text", "text": f"[NOTE INTERNE] Message envoyé par l'équipe HESTIM au contact : {note}"})
        if internal_note:
            user_blocks.append({"type": "text", "text": f"[NOTE INTERNE] {internal_note}"})
        if inbound_text:
            user_blocks.append({"type": "text", "text": inbound_text})

        messages = db.load_api_messages(conv_id)
        user_msg = {"role": "user", "content": user_blocks}
        messages.append(user_msg)
        db.append_api_message(conv_id, "user", user_blocks)
        db.update_conversation(conv_id, pending_human_notes="[]")

        reply_parts: list[str] = []
        for _ in range(MAX_TOOL_ROUNDS):
            try:
                resp = _call_claude(messages)
            except anthropic.RateLimitError:
                log.exception("rate limited on conversation %s", conv_id)
                return _fail_safe(conv_id, "Limite de débit API atteinte")
            except anthropic.APIStatusError as e:
                log.exception("API error %s on conversation %s", e.status_code, conv_id)
                return _fail_safe(conv_id, f"Erreur API {e.status_code}")
            except anthropic.APIConnectionError:
                log.exception("connection error on conversation %s", conv_id)
                return _fail_safe(conv_id, "API injoignable")

            if resp.stop_reason == "refusal":
                return _fail_safe(conv_id, "Requête refusée par le modèle", record_assistant=True)

            content = _blocks_to_params(resp.content)
            messages.append({"role": "assistant", "content": content})
            db.append_api_message(conv_id, "assistant", content)
            reply_parts += [b["text"] for b in content if b.get("type") == "text" and b.get("text", "").strip()]

            if resp.stop_reason == "pause_turn":
                continue
            if resp.stop_reason == "max_tokens":
                log.warning("max_tokens hit on conversation %s", conv_id)
                break
            if resp.stop_reason != "tool_use":
                break

            results = []
            for b in content:
                if b.get("type") != "tool_use":
                    continue
                err = tools.validate(b["name"], b.get("input"))
                if err:
                    results.append({"type": "tool_result", "tool_use_id": b["id"], "content": err, "is_error": True})
                    continue
                try:
                    out = tools.execute(b["name"], b["input"], db.get_conversation(conv_id))
                    results.append({"type": "tool_result", "tool_use_id": b["id"], "content": out})
                except Exception as e:  # never let one tool crash the turn
                    log.exception("tool %s failed", b["name"])
                    results.append({"type": "tool_result", "tool_use_id": b["id"], "content": str(e), "is_error": True})
            tool_msg = {"role": "user", "content": results}
            messages.append(tool_msg)
            db.append_api_message(conv_id, "user", results)
            reply_parts = []  # only the text after the last tool round is sent to the contact

        reply = "\n\n".join(reply_parts).strip()
        if reply:
            db.add_message(conv_id, "out", "ai", reply)
        return reply or None


def _fail_safe(conv_id: int, reason: str, record_assistant: bool = False) -> str:
    """Hand the conversation to a human and send a holding message."""
    text = FALLBACK_REPLY["fr"]
    db.add_escalation(conv_id, "other", f"L'agent n'a pas pu répondre ({reason}). À reprendre.")
    db.update_conversation(conv_id, handler="human")
    if record_assistant:
        db.append_api_message(conv_id, "assistant", [{"type": "text", "text": text}])
    db.add_message(conv_id, "out", "ai", text)
    return text
