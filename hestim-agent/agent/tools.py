"""Tools the agent can call. Definitions are a fixed, ordered list so the prompt cache stays warm."""
import json

import db

_NULLABLE_STR = {"type": ["string", "null"]}

TOOLS = [
    {
        "name": "update_contact_profile",
        "description": (
            "Save what you learned about the contact. Call it as soon as a new fact is known "
            "(who they are, level, programme of interest, intake, city, language). "
            "Pass null for fields you did not learn in this message."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "name": _NULLABLE_STR,
                "kind": {"anyOf": [{"type": "string", "enum": ["prospect", "parent", "student", "other"]}, {"type": "null"}]},
                "language": {"anyOf": [{"type": "string", "enum": ["fr", "ar", "darija", "en"]}, {"type": "null"}]},
                "level": {**_NULLABLE_STR, "description": "e.g. 'Bac 2026 Sciences Maths', 'Bac+2 DUT', 'cadre en poste'"},
                "program_interest": _NULLABLE_STR,
                "intake": {**_NULLABLE_STR, "description": "Target start, e.g. 'septembre 2027'"},
                "city": _NULLABLE_STR,
                "note": {**_NULLABLE_STR, "description": "One short fact worth keeping (objection, budget concern, competitor school...)"},
            },
            "required": ["name", "kind", "language", "level", "program_interest", "intake", "city", "note"],
        },
    },
    {
        "name": "set_lead_status",
        "description": "Classify the contact. Re-classify whenever the picture changes.",
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "status": {"type": "string", "enum": ["ready", "undecided", "general", "not_fit", "enrolled"]},
                "reason": {"type": "string", "description": "One sentence justifying the status."},
            },
            "required": ["status", "reason"],
        },
    },
    {
        "name": "request_counselor_call",
        "description": (
            "Hand a READY prospect to an admissions counselor for a call or meeting. "
            "Use after the prospect agrees to be contacted. The AI keeps answering in the chat."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "preferred_time": {**_NULLABLE_STR, "description": "When the prospect prefers to be called, if stated."},
                "summary": {"type": "string", "description": "2-3 lines a counselor can act on without reading the chat."},
            },
            "required": ["preferred_time", "summary"],
        },
    },
    {
        "name": "escalate_to_human",
        "description": (
            "Flag something the team must handle. handoff=true stops the AI and gives the conversation "
            "to a human (angry contact, explicit request, sensitive/urgent case, negotiation). "
            "handoff=false only notifies the team (e.g. a question the knowledge base cannot answer) "
            "and the AI keeps the conversation."
        ),
        "strict": True,
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {
                "category": {"type": "string", "enum": ["admissions", "finance", "scolarite", "urgent", "knowledge_gap", "other"]},
                "summary": {"type": "string", "description": "What is needed, with the contact's exact question."},
                "handoff": {"type": "boolean"},
            },
            "required": ["category", "summary", "handoff"],
        },
    },
    {
        "name": "unsubscribe_contact",
        "description": "The contact asked to stop receiving messages. Stops all follow-ups.",
        "strict": True,
        "input_schema": {"type": "object", "additionalProperties": False, "properties": {}, "required": []},
    },
]


def _append_note(contact: dict, note: str) -> str:
    existing = contact.get("notes") or ""
    return (existing + "\n- " + note).strip() if existing else "- " + note


def execute(name: str, args: dict, conv: dict) -> str:
    """Run one tool against the DB. Returns a short string for the tool_result."""
    contact = db.get_contact(conv["contact_id"])
    cid, conv_id = contact["id"], conv["id"]

    if name == "update_contact_profile":
        fields = {k: args.get(k) for k in ("name", "kind", "language", "level", "program_interest", "intake", "city")}
        if args.get("note"):
            fields["notes"] = _append_note(contact, args["note"])
        db.update_contact(cid, **fields)
        return "Profil mis à jour."

    if name == "set_lead_status":
        status = args["status"]
        updates = {"lead_status": status}
        if status == "enrolled":
            updates["kind"] = "student"
        db.update_contact(cid, **updates)
        db.update_contact(cid, notes=_append_note(db.get_contact(cid), f"[{status}] {args['reason']}"))
        return f"Statut: {status}."

    if name == "request_counselor_call":
        when = args.get("preferred_time") or "non précisé"
        db.update_contact(cid, lead_status="ready")
        db.add_escalation(conv_id, "admissions", f"Appel conseiller demandé (créneau: {when}). {args['summary']}")
        return "Demande transmise à l'équipe admissions. Un conseiller va contacter le prospect."

    if name == "escalate_to_human":
        db.add_escalation(conv_id, args["category"], args["summary"])
        if args["handoff"]:
            db.update_conversation(conv_id, handler="human")
            return "Conversation transférée à l'équipe. Préviens le contact qu'un membre de l'équipe reprend ici."
        return "Équipe notifiée. Continue la conversation."

    if name == "unsubscribe_contact":
        db.update_contact(cid, subscribed=0)
        return "Contact désabonné : plus aucune relance."

    raise ValueError(f"unknown tool {name}")


def validate(name: str, args) -> str | None:
    """Return an error string if args do not match the declared schema's required keys."""
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if spec is None:
        return f"Unknown tool: {name}"
    if not isinstance(args, dict):
        return "Tool input must be a JSON object."
    missing = [k for k in spec["input_schema"]["required"] if k not in args]
    if missing:
        return f"Missing fields: {', '.join(missing)}"
    return None


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False)
