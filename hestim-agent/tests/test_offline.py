"""Offline tests: no API key needed. A fake Claude client scripts the model's responses."""
import hashlib
import hmac
import json
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import db  # noqa: E402
from agent import core  # noqa: E402
from channels import meta  # noqa: E402


class Block(SimpleNamespace):
    def model_dump(self, **_):
        return {k: v for k, v in vars(self).items() if v is not None}


def text(t):
    return Block(type="text", text=t)


def tool(name, inp, id_="tu_1"):
    return Block(type="tool_use", id=id_, name=name, input=inp)


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))
        self.messages = SimpleNamespace(create=self._create)

    def _create(self, **kw):
        self.calls.append(json.loads(json.dumps(kw["messages"], default=str)))
        stop, content = self.script.pop(0)
        return SimpleNamespace(stop_reason=stop, content=content)


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    db.reset_for_tests(str(tmp_path / "t.db"))
    config.WHATSAPP_TOKEN = config.INSTAGRAM_PAGE_TOKEN = ""
    config.META_APP_SECRET = ""
    yield


def test_parse_whatsapp_and_instagram():
    wa = {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": {
        "contacts": [{"wa_id": "2126000", "profile": {"name": "Sara"}}],
        "messages": [{"from": "2126000", "type": "text", "text": {"body": "salam"}}]}}]}]}
    ig = {"object": "instagram", "entry": [{"messaging": [
        {"sender": {"id": "ig1"}, "message": {"text": "hello"}},
        {"sender": {"id": "page"}, "message": {"text": "echo", "is_echo": True}}]}]}
    assert meta.parse_webhook(wa) == [{"channel": "whatsapp", "external_id": "2126000", "name": "Sara", "text": "salam"}]
    assert meta.parse_webhook(ig) == [{"channel": "instagram", "external_id": "ig1", "name": None, "text": "hello"}]


def test_signature():
    config.META_APP_SECRET = "s3cret"
    body = b'{"a":1}'
    sig = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
    assert meta.verify_signature(body, sig)
    assert not meta.verify_signature(body, "sha256=bad")
    assert not meta.verify_signature(body, None)


def test_turn_with_tools_qualifies_lead():
    fake = FakeClient([
        ("tool_use", [Block(type="thinking", thinking="", signature="sig"),
                      tool("update_contact_profile", {"name": None, "kind": "prospect", "language": "darija",
                                                      "level": "Bac 2027 SM", "program_interest": "Ingénierie",
                                                      "intake": None, "city": "Casablanca", "note": "demande les frais"}),
                      tool("set_lead_status", {"status": "undecided", "reason": "veut d'abord le prix"}, "tu_2")]),
        ("end_turn", [text("Les frais dépendent du programme. Chnou l'niveau dyalek ?")]),
    ])
    core.set_client(fake)
    _c, conv = db.get_or_create_conversation("whatsapp", "2126000", "Sara")
    reply = core.run_turn(conv["id"], "chhal les frais?")
    assert "frais" in reply
    contact = db.get_contact(conv["contact_id"])
    assert contact["lead_status"] == "undecided" and contact["language"] == "darija"
    assert "demande les frais" in contact["notes"]
    # second call replays the exact assistant blocks (thinking + tool_use) and both tool results in ONE message
    second = fake.calls[1]
    assert second[-2]["content"][0]["type"] == "thinking"
    assert [b["type"] for b in second[-1]["content"]] == ["tool_result", "tool_result"]
    # history persisted append-only: user, assistant, tool results, assistant
    assert [m["role"] for m in db.load_api_messages(conv["id"])] == ["user", "assistant", "user", "assistant"]


def test_handoff_stops_ai_and_human_notes_flow_back():
    core.set_client(FakeClient([
        ("tool_use", [tool("escalate_to_human", {"category": "urgent", "summary": "harcèlement", "handoff": True})]),
        ("end_turn", [text("Je transmets à l'équipe, quelqu'un vous répond ici.")]),
    ]))
    _c, conv = db.get_or_create_conversation("web", "u1")
    core.run_turn(conv["id"], "situation grave")
    assert db.get_conversation(conv["id"])["handler"] == "human"
    assert core.run_turn(conv["id"], "allo?") is None  # AI silent while a human owns it
    assert db.list_escalations(conv["id"])[0]["category"] == "urgent"

    from fastapi.testclient import TestClient
    import app as app_module
    client = TestClient(app_module.app)
    auth = (config.INBOX_USER, config.INBOX_PASSWORD)
    assert client.post(f"/api/conversations/{conv['id']}/reply", json={"text": "Bonjour, ici Amal."}, auth=auth).status_code == 200
    assert client.post(f"/api/conversations/{conv['id']}/release", auth=auth).status_code == 200
    fake = FakeClient([("end_turn", [text("Avec plaisir !")])])
    core.set_client(fake)
    core.run_turn(conv["id"], "merci")
    last_user = fake.calls[0][-1]["content"]
    assert any("Bonjour, ici Amal." in b["text"] for b in last_user)


def test_refusal_and_api_error_fail_safe():
    core.set_client(FakeClient([("refusal", [])]))
    _c, conv = db.get_or_create_conversation("web", "u2")
    reply = core.run_turn(conv["id"], "x")
    assert "équipe" in reply and db.get_conversation(conv["id"])["handler"] == "human"


def test_invalid_tool_input_returns_error_result():
    fake = FakeClient([
        ("tool_use", [tool("set_lead_status", {"status": "ready"})]),
        ("end_turn", [text("ok")]),
    ])
    core.set_client(fake)
    _c, conv = db.get_or_create_conversation("web", "u3")
    core.run_turn(conv["id"], "x")
    res = fake.calls[1][-1]["content"][0]
    assert res["is_error"] and "reason" in res["content"]


def test_followup_candidates_and_unsubscribe():
    _c, conv = db.get_or_create_conversation("web", "u4")
    db.update_contact(conv["contact_id"], kind="prospect", lead_status="undecided")
    db.add_message(conv["id"], "in", "contact", "hmm")
    db.add_message(conv["id"], "out", "ai", "Une question ?")
    assert db.followup_candidates(db.now() + 1, 1)
    db.update_contact(conv["contact_id"], subscribed=0)
    assert not db.followup_candidates(db.now() + 1, 1)


def test_inbox_api_and_webhook():
    from fastapi.testclient import TestClient
    import app as app_module
    core.set_client(FakeClient([("end_turn", [text("Bonjour ! Quel programme vous intéresse ?")])]))
    client = TestClient(app_module.app)
    r = client.get("/webhook", params={"hub.mode": "subscribe", "hub.verify_token": config.META_VERIFY_TOKEN, "hub.challenge": "42"})
    assert r.text == "42"
    payload = {"object": "instagram", "entry": [{"messaging": [{"sender": {"id": "ig9"}, "message": {"text": "bonjour"}}]}]}
    assert client.post("/webhook", json=payload).status_code == 200
    auth = (config.INBOX_USER, config.INBOX_PASSWORD)
    assert client.get("/api/conversations").status_code == 401
    convs = client.get("/api/conversations", auth=auth).json()
    assert len(convs) == 1 and convs[0]["channel"] == "instagram"
    detail = client.get(f"/api/conversations/{convs[0]['id']}", auth=auth).json()
    assert [m["direction"] for m in detail["messages"]] == ["in", "out"]
    assert client.get("/api/contacts/stats", auth=auth).json()["by_channel"][0]["total"] == 1
    assert "hestim_contacts" in client.get("/api/contacts/export.csv", auth=auth).headers["content-disposition"]
    assert client.get("/", auth=auth).status_code == 200


def test_system_prompt_is_stable_and_contains_kb():
    from agent.prompt import system_prompt
    assert system_prompt() == system_prompt()
    assert "[À CONFIRMER]" in system_prompt()
