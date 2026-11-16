"""HESTIM agent server: Meta webhooks, staff inbox API + UI, follow-up scheduler.

Run:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import csv
import io
import json
import logging
import secrets
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse, StreamingResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

import config
import db
from agent import core
from channels import meta

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("hestim.app")
STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(_app):
    scheduler = None
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        import nurture
        scheduler = BackgroundScheduler()
        scheduler.add_job(nurture.run_followups, "interval", minutes=30, id="followups")
        scheduler.start()
    except Exception:
        log.exception("scheduler not started")
    yield
    if scheduler:
        scheduler.shutdown(wait=False)


app = FastAPI(title="HESTIM Agent", lifespan=lifespan)
security = HTTPBasic()


def staff(creds: HTTPBasicCredentials = Depends(security)) -> str:
    ok = secrets.compare_digest(creds.username, config.INBOX_USER) and \
        secrets.compare_digest(creds.password, config.INBOX_PASSWORD)
    if not ok:
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    return creds.username


# ---------------- inbound pipeline ----------------

def handle_inbound(channel: str, external_id: str, name: str | None, text: str) -> str | None:
    _contact, conv = db.get_or_create_conversation(channel, external_id, name)
    db.add_message(conv["id"], "in", "contact", text)
    if conv["handler"] != "ai":
        return None  # a human owns this conversation; it shows up in the inbox
    reply = core.run_turn(conv["id"], text)
    if reply:
        meta.send(channel, external_id, reply)
    return reply


@app.get("/webhook")
def verify(request: Request):
    p = request.query_params
    if p.get("hub.mode") == "subscribe" and p.get("hub.verify_token") == config.META_VERIFY_TOKEN:
        return PlainTextResponse(p.get("hub.challenge", ""))
    raise HTTPException(403)


@app.post("/webhook")
async def webhook(request: Request, background: BackgroundTasks):
    raw = await request.body()
    if not meta.verify_signature(raw, request.headers.get("x-hub-signature-256")):
        raise HTTPException(401, "bad signature")
    for m in meta.parse_webhook(json.loads(raw or b"{}")):
        background.add_task(handle_inbound, m["channel"], m["external_id"], m["name"], m["text"])
    return {"ok": True}  # answer Meta within its timeout; the agent runs in the background


class WebMessage(BaseModel):
    external_id: str
    text: str
    name: str | None = None


@app.post("/api/chat")
def web_chat(msg: WebMessage, _user: str = Depends(staff)):
    """Talk to the agent from the inbox's test panel (channel 'web')."""
    reply = handle_inbound("web", msg.external_id, msg.name, msg.text)
    return {"reply": reply}


# ---------------- inbox API ----------------

@app.get("/api/conversations")
def conversations(handler: str | None = None, q: str | None = None, lead_status: str | None = None,
                  _user: str = Depends(staff)):
    return db.list_conversations(handler, q, lead_status)


@app.get("/api/conversations/{conv_id}")
def conversation(conv_id: int, _user: str = Depends(staff)):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404)
    return {"conversation": conv, "contact": db.get_contact(conv["contact_id"]),
            "messages": db.list_messages(conv_id), "escalations": db.list_escalations(conv_id, False)}


@app.post("/api/conversations/{conv_id}/takeover")
def takeover(conv_id: int, user: str = Depends(staff)):
    db.update_conversation(conv_id, handler="human", assignee=db.get_conversation(conv_id)["assignee"] or user)
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/release")
def release(conv_id: int, _user: str = Depends(staff)):
    db.update_conversation(conv_id, handler="ai")
    return {"ok": True}


class Assign(BaseModel):
    assignee: str


@app.post("/api/conversations/{conv_id}/assign")
def assign(conv_id: int, body: Assign, _user: str = Depends(staff)):
    db.update_conversation(conv_id, assignee=body.assignee)
    return {"ok": True}


class Reply(BaseModel):
    text: str
    author: str | None = None


@app.post("/api/conversations/{conv_id}/reply")
def human_reply(conv_id: int, body: Reply, user: str = Depends(staff)):
    conv = db.get_conversation(conv_id)
    if not conv:
        raise HTTPException(404)
    contact = db.get_contact(conv["contact_id"])
    if not meta.send(contact["channel"], contact["external_id"], body.text):
        raise HTTPException(502, "delivery failed")
    db.add_message(conv_id, "out", body.author or user, body.text)
    notes = json.loads(conv["pending_human_notes"] or "[]") + [body.text]
    db.update_conversation(conv_id, handler="human", pending_human_notes=json.dumps(notes, ensure_ascii=False))
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/close")
def close(conv_id: int, _user: str = Depends(staff)):
    db.update_conversation(conv_id, status="closed")
    return {"ok": True}


@app.post("/api/escalations/{esc_id}/resolve")
def resolve(esc_id: int, _user: str = Depends(staff)):
    with db.cursor() as c:
        c.execute("UPDATE escalations SET resolved=1 WHERE id=?", (esc_id,))
    return {"ok": True}


@app.get("/api/escalations")
def escalations(_user: str = Depends(staff)):
    return db.list_escalations()


# ---------------- contacts ----------------

@app.get("/api/contacts")
def contacts(channel: str | None = None, kind: str | None = None, lead_status: str | None = None,
             text: str | None = None, _user: str = Depends(staff)):
    return db.list_contacts({"channel": channel, "kind": kind, "lead_status": lead_status, "text": text})


@app.get("/api/contacts/stats")
def stats(_user: str = Depends(staff)):
    return db.contact_stats()


@app.get("/api/contacts/export.csv")
def export(_user: str = Depends(staff)):
    rows = db.list_contacts()
    buf = io.StringIO()
    if rows:
        w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": "attachment; filename=hestim_contacts.csv"})


class Ask(BaseModel):
    question: str


ASK_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "channel": {"anyOf": [{"type": "string", "enum": ["whatsapp", "instagram", "web"]}, {"type": "null"}]},
        "kind": {"anyOf": [{"type": "string", "enum": ["prospect", "parent", "student", "other", "unknown"]}, {"type": "null"}]},
        "lead_status": {"anyOf": [{"type": "string", "enum": ["new", "ready", "undecided", "general", "not_fit", "enrolled"]}, {"type": "null"}]},
        "language": {"anyOf": [{"type": "string", "enum": ["fr", "ar", "darija", "en"]}, {"type": "null"}]},
        "city": {"type": ["string", "null"]},
        "program_contains": {"type": ["string", "null"]},
        "text": {"type": ["string", "null"]},
        "explanation": {"type": "string"},
    },
    "required": ["channel", "kind", "lead_status", "language", "city", "program_contains", "text", "explanation"],
}


@app.post("/api/contacts/ask")
def ask_contacts(body: Ask, _user: str = Depends(staff)):
    """'Demandez à l'IA': turn a natural-language question into contact filters."""
    resp = core.client().messages.create(
        model=config.MODEL,
        max_tokens=2000,
        output_config={"effort": "low", "format": {"type": "json_schema", "schema": ASK_SCHEMA}},
        system="Tu convertis une question d'un conseiller HESTIM sur sa base de contacts en filtres. "
               "Mets null pour tout filtre non demandé. 'explanation' : une phrase en français.",
        messages=[{"role": "user", "content": body.question}],
    )
    if resp.stop_reason == "refusal":
        raise HTTPException(422, "question refusée")
    filters = json.loads(next(b.text for b in resp.content if b.type == "text"))
    return {"filters": filters, "explanation": filters.pop("explanation"), "contacts": db.list_contacts(filters)}


# ---------------- UI ----------------

@app.get("/")
def inbox(_user: str = Depends(staff)):
    return FileResponse(STATIC / "inbox.html")


@app.get("/health")
def health():
    return {"ok": True, "model": config.MODEL}
