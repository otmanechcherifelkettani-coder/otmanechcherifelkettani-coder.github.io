"""WhatsApp Cloud API and Instagram Messaging: webhook parsing, signature check, sending."""
import hashlib
import hmac
import logging

import httpx

import config

log = logging.getLogger("hestim.channels")
GRAPH = "https://graph.facebook.com"


def verify_signature(raw_body: bytes, header: str | None) -> bool:
    """Check X-Hub-Signature-256. If no app secret is configured (local dev), accept."""
    if not config.META_APP_SECRET:
        return True
    if not header or not header.startswith("sha256="):
        return False
    expected = hmac.new(config.META_APP_SECRET.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.split("=", 1)[1])


def parse_webhook(payload: dict) -> list[dict]:
    """Normalise a Meta webhook into [{channel, external_id, name, text}] (text messages only)."""
    out = []
    obj = payload.get("object")
    for entry in payload.get("entry", []):
        if obj == "whatsapp_business_account":
            for change in entry.get("changes", []):
                value = change.get("value", {})
                names = {c.get("wa_id"): c.get("profile", {}).get("name") for c in value.get("contacts", [])}
                for m in value.get("messages", []):
                    text = _wa_text(m)
                    if text:
                        out.append({"channel": "whatsapp", "external_id": m["from"],
                                    "name": names.get(m["from"]), "text": text})
        elif obj == "instagram":
            for ev in entry.get("messaging", []):
                msg = ev.get("message") or {}
                if msg.get("is_echo"):
                    continue
                if msg.get("text"):
                    out.append({"channel": "instagram", "external_id": ev["sender"]["id"],
                                "name": None, "text": msg["text"]})
    return out


def _wa_text(m: dict) -> str | None:
    t = m.get("type")
    if t == "text":
        return m["text"]["body"]
    if t == "button":
        return m["button"].get("text")
    if t == "interactive":
        i = m["interactive"]
        return (i.get("button_reply") or i.get("list_reply") or {}).get("title")
    if t in ("audio", "image", "video", "document", "sticker"):
        caption = (m.get(t) or {}).get("caption")
        return caption or f"[Le contact a envoyé un fichier de type {t} que tu ne peux pas lire. Demande-lui de l'écrire en texte si c'est important.]"
    return None


def send(channel: str, external_id: str, text: str) -> bool:
    try:
        if channel == "whatsapp":
            if not (config.WHATSAPP_TOKEN and config.WHATSAPP_PHONE_NUMBER_ID):
                log.info("[whatsapp dry-run] -> %s: %s", external_id, text)
                return True
            r = httpx.post(
                f"{GRAPH}/{config.GRAPH_VERSION}/{config.WHATSAPP_PHONE_NUMBER_ID}/messages",
                headers={"Authorization": f"Bearer {config.WHATSAPP_TOKEN}"},
                json={"messaging_product": "whatsapp", "to": external_id, "type": "text",
                      "text": {"body": text[:4096]}},
                timeout=20,
            )
        elif channel == "instagram":
            if not config.INSTAGRAM_PAGE_TOKEN:
                log.info("[instagram dry-run] -> %s: %s", external_id, text)
                return True
            r = httpx.post(
                f"{GRAPH}/{config.GRAPH_VERSION}/me/messages",
                params={"access_token": config.INSTAGRAM_PAGE_TOKEN},
                json={"recipient": {"id": external_id}, "message": {"text": text[:1000]}},
                timeout=20,
            )
        else:  # web / simulator: nothing to deliver
            return True
        if r.status_code >= 400:
            log.error("send %s failed %s: %s", channel, r.status_code, r.text[:300])
            return False
        return True
    except httpx.HTTPError:
        log.exception("send %s failed", channel)
        return False
