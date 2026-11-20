"""Tools for the Atlas Telecom level-1 support agent (fictional company, synthetic data).

Course principles visible here:
- Few tools, each doing one job, with descriptions written for the model (when to use it, what it returns).
- Deterministic code enforces the money and privacy rules. The prompt explains them; the code guarantees them.
- Mutating tools (issue_credit, escalate_to_human) are logged and capped.
"""
import json
import pathlib
import re

import llm

DATA = pathlib.Path(__file__).parent / "data"
CUSTOMERS = json.loads((DATA / "customers.json").read_text(encoding="utf-8"))
OUTAGES = json.loads((DATA / "outages.json").read_text(encoding="utf-8"))
TICKETS = json.loads((DATA / "tickets.json").read_text(encoding="utf-8"))

AUTO_CREDIT_LIMIT_MAD = 50


def _schema(properties: dict, required: list) -> dict:
    return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}


TOOLS = [
    {
        "name": "verify_customer",
        "description": "Verify a caller before sharing ANY account detail. Needs the phone number on the account "
                       "(any format: 06..., +212 6..., with spaces) and the caller's first name. Returns the "
                       "customer_id and city when both match, otherwise verified=false. Never guess a phone number.",
        "input_schema": _schema({
            "phone": {"type": "string", "description": "Phone number as given by the caller"},
            "first_name": {"type": "string", "description": "First name as given by the caller"},
        }, ["phone", "first_name"]),
        "strict": True,
    },
    {
        "name": "get_account",
        "description": "Plan, line status (active or suspended_unpaid), data balance, last bill and due date, and "
                       "credits already given in the last 30 days. Only for a customer_id returned by verify_customer.",
        "input_schema": _schema({"customer_id": {"type": "string"}}, ["customer_id"]),
        "strict": True,
    },
    {
        "name": "check_outage",
        "description": "Known network incidents for a city (optionally a district). Use it whenever a caller reports "
                       "no service or slow service. No verification needed. Returns an empty list when nothing is known.",
        "input_schema": _schema({
            "city": {"type": "string"},
            "district": {"type": ["string", "null"], "description": "District if known, else null"},
        }, ["city", "district"]),
        "strict": True,
    },
    {
        "name": "get_open_tickets",
        "description": "Support tickets for a verified customer, with how many troubleshooting attempts were made.",
        "input_schema": _schema({"customer_id": {"type": "string"}}, ["customer_id"]),
        "strict": True,
    },
    {
        "name": "issue_credit",
        "description": f"Give a goodwill credit in MAD. Allowed only for a verified customer affected by a confirmed "
                       f"outage, at most {AUTO_CREDIT_LIMIT_MAD} MAD, and only if no credit was given in the last 30 days. "
                       f"Larger or repeated requests return needs_human_approval: then escalate instead.",
        "input_schema": _schema({
            "customer_id": {"type": "string"},
            "amount_mad": {"type": "number"},
            "reason": {"type": "string"},
            "outage_id": {"type": "string", "description": "The confirmed outage id from check_outage"},
        }, ["customer_id", "amount_mad", "reason", "outage_id"]),
        "strict": True,
    },
    {
        "name": "escalate_to_human",
        "description": "Hand the conversation to a human agent. Required for: contract termination, legal threats, "
                       "credits above the limit, a third failed troubleshooting attempt, or anything you cannot verify "
                       "from your tools. Write a summary a human can act on without re-asking the customer.",
        "input_schema": _schema({
            "customer_id": {"type": ["string", "null"]},
            "summary": {"type": "string"},
            "priority": {"type": "string", "enum": ["low", "normal", "high"]},
        }, ["customer_id", "summary", "priority"]),
        "strict": True,
    },
]


def normalise_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw or "")
    if digits.startswith("212"):
        digits = "0" + digits[3:]
    return digits


def _customer(customer_id: str):
    return next((c for c in CUSTOMERS if c["id"] == customer_id), None)


def verify_customer(phone: str, first_name: str) -> dict:
    match = next((c for c in CUSTOMERS if c["phone"] == normalise_phone(phone)), None)
    if match and match["first_name"].strip().lower() == (first_name or "").strip().lower():
        return {"verified": True, "customer_id": match["id"], "city": match["city"], "district": match["district"]}
    return {"verified": False, "reason": "phone and first name do not match an account"}


def get_account(customer_id: str) -> dict:
    c = _customer(customer_id)
    if not c:
        return {"error": "unknown customer_id"}
    keys = ["plan", "monthly_fee_mad", "status", "data_balance_gb", "last_bill_mad", "bill_due", "credits_last_30_days"]
    return {k: c[k] for k in keys}


def check_outage(city: str, district=None) -> dict:
    hits = [o for o in OUTAGES if o["city"].lower() == (city or "").lower()
            and (not district or district.lower() in [d.lower() for d in o["districts"]])]
    return {"outages": hits}


def get_open_tickets(customer_id: str) -> dict:
    return {"tickets": [t for t in TICKETS if t["customer_id"] == customer_id]}


def issue_credit(customer_id: str, amount_mad: float, reason: str, outage_id: str) -> dict:
    c = _customer(customer_id)
    if not c:
        return {"status": "rejected", "why": "unknown customer_id"}
    outage = next((o for o in OUTAGES if o["id"] == outage_id), None)
    if not outage or outage["city"] != c["city"] or c["district"] not in outage["districts"]:
        return {"status": "rejected", "why": "no confirmed outage affecting this customer"}
    if amount_mad > AUTO_CREDIT_LIMIT_MAD or c["credits_last_30_days"] > 0:
        return {"status": "needs_human_approval", "why": "above limit or credit already given in last 30 days"}
    return {"status": "issued", "amount_mad": amount_mad}


def escalate_to_human(customer_id, summary: str, priority: str) -> dict:
    return {"status": "escalated", "queue": "L2", "priority": priority}


IMPLEMENTATIONS = {
    "verify_customer": verify_customer,
    "get_account": get_account,
    "check_outage": check_outage,
    "get_open_tickets": get_open_tickets,
    "issue_credit": issue_credit,
    "escalate_to_human": escalate_to_human,
}


@llm.traceable(run_type="tool", name="tool")
def execute(name: str, tool_input: dict):
    """Returns (result, is_error). A failing tool is reported to the model, never silently dropped."""
    fn = IMPLEMENTATIONS.get(name)
    if fn is None:
        return {"error": f"unknown tool {name}"}, True
    try:
        return fn(**tool_input), False
    except Exception as exc:  # the model sees the error and can recover or escalate
        return {"error": f"{type(exc).__name__}: {exc}"}, True
