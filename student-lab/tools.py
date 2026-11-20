"""Atlas Telecom tools: the only actions the agent is allowed to take.

Rule 2 of a good agent: few tools, one job each, and the hard rules
(money, privacy) live HERE in code, not only in the prompt.
"""
import json
from pathlib import Path

DATA = Path(__file__).parent / "data"
CUSTOMERS = json.loads((DATA / "customers.json").read_text())
OUTAGES = json.loads((DATA / "outages.json").read_text())
TICKETS = json.loads((DATA / "tickets.json").read_text())

CREDIT_LIMIT_MAD = 50          # max per credit AND per customer over 30 days

# Who has been verified in THIS conversation. Reset at the start of each run.
SESSION = {"verified_id": None}


def reset_session():
    SESSION["verified_id"] = None


# ---------- the six tools ----------

def verify_customer(phone: str, first_name: str) -> dict:
    """Identity check: phone number AND first name must match the same record."""
    phone = phone.replace(" ", "").replace("+212", "0")
    for c in CUSTOMERS:
        if c["phone"] == phone and c["first_name"].lower() == first_name.strip().lower():
            SESSION["verified_id"] = c["id"]
            return {"verified": True, "customer_id": c["id"]}
    return {"verified": False, "reason": "phone and first name do not match a customer"}


def _require_verified(customer_id: str):
    """Privacy rule in code: only the verified caller's own data can be read or changed."""
    if SESSION["verified_id"] is None:
        return {"error": "customer not verified: call verify_customer first"}
    if customer_id != SESSION["verified_id"]:
        return {"error": "refused: you may only access the verified caller's own account"}
    return None


def get_account(customer_id: str) -> dict:
    """Plan, status, data balance, last bill and due date of the verified customer."""
    if (err := _require_verified(customer_id)):
        return err
    c = next(c for c in CUSTOMERS if c["id"] == customer_id)
    keep = ["first_name", "city", "district", "plan", "monthly_fee_mad", "status",
            "data_balance_gb", "last_bill_mad", "bill_due"]
    return {k: c[k] for k in keep}


def check_outage(city: str, district: str = "") -> dict:
    """Known network outages in a city (optionally one district). Public info, no verification."""
    found = [o for o in OUTAGES
             if o["city"].lower() == city.strip().lower()
             and (not district or district.strip().lower() in [d.lower() for d in o["districts"]])]
    return {"outages": found} if found else {"outages": [], "note": "no known outage there"}


def get_tickets(customer_id: str) -> dict:
    """Past and open support tickets of the verified customer, with number of attempts."""
    if (err := _require_verified(customer_id)):
        return err
    return {"tickets": [t for t in TICKETS if t["customer_id"] == customer_id]}


def give_credit(customer_id: str, amount_mad: float, reason: str) -> dict:
    """Goodwill credit. HARD RULE: at most 50 MAD per customer over 30 days."""
    if (err := _require_verified(customer_id)):
        return err
    c = next(c for c in CUSTOMERS if c["id"] == customer_id)
    remaining = CREDIT_LIMIT_MAD - c["credits_last_30_days"]
    if amount_mad <= 0:
        return {"error": "amount must be positive"}
    if amount_mad > remaining:
        return {"error": f"refused: limit is {CREDIT_LIMIT_MAD} MAD per 30 days, "
                         f"{remaining} MAD left for this customer. Escalate for more."}
    c["credits_last_30_days"] += amount_mad   # in-memory only (synthetic data)
    return {"credited_mad": amount_mad, "reason": reason}


def escalate(reason: str, summary: str) -> dict:
    """Hand the conversation to a human agent. Use when stuck, risky, or out of policy."""
    return {"escalated": True, "queue": "level-2 human", "reason": reason}


# ---------- descriptions the MODEL reads to decide which tool to use ----------

TOOLS = [
    {"name": "verify_customer",
     "description": "Verify the caller's identity with phone number and first name. "
                    "Required before any account data, ticket or credit.",
     "input_schema": {"type": "object", "properties": {
         "phone": {"type": "string"}, "first_name": {"type": "string"}},
         "required": ["phone", "first_name"]}},
    {"name": "get_account",
     "description": "Read the verified customer's plan, status, data balance, last bill and due date.",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                      "required": ["customer_id"]}},
    {"name": "check_outage",
     "description": "Check known network outages in a city, optionally a district. No verification needed.",
     "input_schema": {"type": "object", "properties": {
         "city": {"type": "string"}, "district": {"type": "string"}}, "required": ["city"]}},
    {"name": "get_tickets",
     "description": "List the verified customer's support tickets and how many times they already contacted us.",
     "input_schema": {"type": "object", "properties": {"customer_id": {"type": "string"}},
                      "required": ["customer_id"]}},
    {"name": "give_credit",
     "description": "Give a goodwill credit in MAD to the verified customer. Max 50 MAD per 30 days.",
     "input_schema": {"type": "object", "properties": {
         "customer_id": {"type": "string"}, "amount_mad": {"type": "number"},
         "reason": {"type": "string"}}, "required": ["customer_id", "amount_mad", "reason"]}},
    {"name": "escalate",
     "description": "Hand over to a human: cancellation requests, credits above the limit, "
                    "repeated failures, anything risky or outside these tools.",
     "input_schema": {"type": "object", "properties": {
         "reason": {"type": "string"}, "summary": {"type": "string"}},
         "required": ["reason", "summary"]}},
]

FUNCTIONS = {f.__name__: f for f in
             [verify_customer, get_account, check_outage, get_tickets, give_credit, escalate]}
