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


class User(BaseModel):
    name: str
    teams: set[str] | None  # None = admin, sees every team

    @property
    def is_admin(self) -> bool:
        return self.teams is None

    def can_see(self, team: str) -> bool:
        return self.teams is None or team in self.teams


def staff(creds: HTTPBasicCredentials = Depends(security)) -> User:
    account = config.staff_accounts().get(creds.username)
    if account is None or not secrets.compare_digest(creds.password.encode(), account["password"].encode()):
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    return User(name=creds.username, teams=account["teams"])


def visible_conversation(conv_id: int, user: User) -> dict:
    """Load a conversation the user may see. Invisible ones answer 404 so their existence is not revealed."""
    conv = db.get_conversation(conv_id)
    if not conv or not user.can_see(conv["team"]):
        raise HTTPException(404)
    return conv


@app.get("/api/me")
def me(user: User = Depends(staff)):
    teams = sorted(config.TEAMS) if user.is_admin else sorted(user.teams)
    return {"user": user.name, "admin": user.is_admin, "teams": teams, "team_labels": config.TEAMS,
            "can_test": user.can_see(config.DEFAULT_TEAM)}


@app.get("/api/staff")
def staff_list(user: User = Depends(staff)):
    """Colleagues the user can hand a conversation to, with the teams they cover."""
    out = []
    for name, acc in config.staff_accounts().items():
        teams = sorted(config.TEAMS) if acc["teams"] is None else sorted(acc["teams"])
        out.append({"name": name, "teams": teams, "admin": acc["teams"] is None})
    return out


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
def web_chat(msg: WebMessage, user: User = Depends(staff)):
    """Talk to the agent from the inbox's test panel (channel 'web'). Test chats start in admissions."""
    if not user.can_see(config.DEFAULT_TEAM):
        raise HTTPException(403, "Le mode test est réservé aux équipes admissions et admin.")
    reply = handle_inbound("web", msg.external_id, msg.name, msg.text)
    return {"reply": reply}


# ---------------- inbox API ----------------
# Every endpoint below is scoped to the caller's teams; admins see everything.

@app.get("/api/conversations")
def conversations(handler: str | None = None, q: str | None = None, lead_status: str | None = None,
                  team: str | None = None, user: User = Depends(staff)):
    return db.list_conversations(handler, q, lead_status, teams=user.teams, team=team)


@app.get("/api/conversations/{conv_id}")
def conversation(conv_id: int, user: User = Depends(staff)):
    conv = visible_conversation(conv_id, user)
    return {"conversation": conv, "contact": db.get_contact(conv["contact_id"]),
            "messages": db.list_messages(conv_id), "escalations": db.list_escalations(conv_id, False)}


@app.post("/api/conversations/{conv_id}/takeover")
def takeover(conv_id: int, user: User = Depends(staff)):
    conv = visible_conversation(conv_id, user)
    db.update_conversation(conv_id, handler="human", assignee=conv["assignee"] or user.name)
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/release")
def release(conv_id: int, user: User = Depends(staff)):
    visible_conversation(conv_id, user)
    db.update_conversation(conv_id, handler="ai")
    return {"ok": True}


class Assign(BaseModel):
    assignee: str


@app.post("/api/conversations/{conv_id}/assign")
def assign(conv_id: int, body: Assign, user: User = Depends(staff)):
    conv = visible_conversation(conv_id, user)
    if body.assignee:
        target = config.staff_accounts().get(body.assignee)
        if target is None:
            raise HTTPException(400, "Collègue inconnu")
        if target["teams"] is not None and conv["team"] not in target["teams"]:
            raise HTTPException(400, f"{body.assignee} ne fait pas partie de l'équipe "
                                     f"{config.TEAMS[conv['team']]}. Transférez d'abord la discussion.")
    db.update_conversation(conv_id, assignee=body.assignee or None)
    return {"ok": True}


class Transfer(BaseModel):
    team: str


@app.post("/api/conversations/{conv_id}/team")
def transfer(conv_id: int, body: Transfer, user: User = Depends(staff)):
    conv = visible_conversation(conv_id, user)
    if body.team not in config.TEAMS:
        raise HTTPException(400, "Équipe inconnue")
    from agent.tools import route_to_team
    route_to_team(conv, body.team, by=user.name)
    return {"ok": True, "still_visible": user.can_see(body.team)}


class Reply(BaseModel):
    text: str


@app.post("/api/conversations/{conv_id}/reply")
def human_reply(conv_id: int, body: Reply, user: User = Depends(staff)):
    conv = visible_conversation(conv_id, user)
    contact = db.get_contact(conv["contact_id"])
    if not meta.send(contact["channel"], contact["external_id"], body.text):
        raise HTTPException(502, "delivery failed")
    db.add_message(conv_id, "out", user.name, body.text)
    notes = json.loads(conv["pending_human_notes"] or "[]") + [body.text]
    db.update_conversation(conv_id, handler="human", assignee=conv["assignee"] or user.name,
                           pending_human_notes=json.dumps(notes, ensure_ascii=False))
    return {"ok": True}


@app.post("/api/conversations/{conv_id}/close")
def close(conv_id: int, user: User = Depends(staff)):
    visible_conversation(conv_id, user)
    db.update_conversation(conv_id, status="closed")
    return {"ok": True}


@app.post("/api/escalations/{esc_id}/resolve")
def resolve(esc_id: int, user: User = Depends(staff)):
    esc = db.get_escalation(esc_id)
    if not esc:
        raise HTTPException(404)
    visible_conversation(esc["conversation_id"], user)
    with db.cursor() as c:
        c.execute("UPDATE escalations SET resolved=1 WHERE id=?", (esc_id,))
    return {"ok": True}


@app.get("/api/escalations")
def escalations(user: User = Depends(staff)):
    return db.list_escalations(teams=user.teams)


# ---------------- contacts ----------------
# A contact is visible when one of their conversations belongs to one of the user's teams.

@app.get("/api/contacts")
def contacts(channel: str | None = None, kind: str | None = None, lead_status: str | None = None,
             text: str | None = None, user: User = Depends(staff)):
    return db.list_contacts({"channel": channel, "kind": kind, "lead_status": lead_status, "text": text},
                            teams=user.teams)


@app.get("/api/contacts/stats")
def stats(user: User = Depends(staff)):
    return db.contact_stats(teams=user.teams)


@app.get("/api/contacts/export.csv")
def export(user: User = Depends(staff)):
    rows = db.list_contacts(teams=user.teams)
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
def ask_contacts(body: Ask, user: User = Depends(staff)):
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
    return {"filters": filters, "explanation": filters.pop("explanation"), "contacts": db.list_contacts(filters, teams=user.teams)}


# ---------------- UI ----------------

@app.get("/")
def inbox(_user: User = Depends(staff)):
    return FileResponse(STATIC / "inbox.html")


@app.get("/health")
def health():
    return {"ok": True, "model": config.MODEL}
