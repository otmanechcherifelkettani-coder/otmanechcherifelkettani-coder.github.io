import os
from dotenv import load_dotenv

load_dotenv()

MODEL = os.getenv("HESTIM_MODEL", "claude-opus-5-5")
EFFORT = os.getenv("HESTIM_EFFORT", "low")
AGENT_NAME = os.getenv("AGENT_NAME", "Nora")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
INSTAGRAM_PAGE_TOKEN = os.getenv("INSTAGRAM_PAGE_TOKEN", "")
META_VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "change-me")
META_APP_SECRET = os.getenv("META_APP_SECRET", "")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v21.0")

INBOX_USER = os.getenv("INBOX_USER", "admissions")
INBOX_PASSWORD = os.getenv("INBOX_PASSWORD", "change-me")
DB_PATH = os.getenv("DB_PATH", "data/hestim.db")


# Teams a conversation can belong to. Every conversation is in exactly one team.
TEAMS = {
    "admissions": "Admissions",
    "finance": "Finance",
    "scolarite": "Scolarité",
    "vie_etudiante": "Vie étudiante & urgences",
}
DEFAULT_TEAM = "admissions"  # where every new conversation starts

# When the agent escalates, the conversation moves to the team that owns that category.
ESCALATION_TEAM = {
    "admissions": "admissions",
    "knowledge_gap": "admissions",
    "other": "admissions",
    "finance": "finance",
    "scolarite": "scolarite",
    "urgent": "vie_etudiante",
}


def staff_accounts() -> dict[str, dict]:
    """Per-person logins with a role.

    INBOX_USERS="Amal:pw1:finance,Karim:pw2:admissions|scolarite,Direction:pw3:admin"
    Role is `admin` (sees everything) or one or more teams separated by `|`.
    A login without a role is admissions only. Falls back to INBOX_USER (admin).
    """
    accounts = {}
    for entry in os.getenv("INBOX_USERS", "").split(","):
        parts = entry.split(":")
        if len(parts) < 2 or not parts[0].strip() or not parts[1]:
            continue
        name, pw = parts[0].strip(), parts[1]
        role = parts[2].strip() if len(parts) > 2 and parts[2].strip() else DEFAULT_TEAM
        if role == "admin":
            teams = None  # all teams
        else:
            teams = {t.strip() for t in role.split("|") if t.strip() in TEAMS}
            if not teams:
                raise ValueError(f"INBOX_USERS: unknown role '{role}' for {name}. Use admin or {', '.join(TEAMS)}")
        accounts[name] = {"password": pw, "teams": teams}
    return accounts or {INBOX_USER: {"password": INBOX_PASSWORD, "teams": None}}


# Server-side refusal fallback exists for Opus 5.5 / Opus 5 / Sonnet 5.5 / Fable; not for Haiku.
SUPPORTS_FALLBACKS = not MODEL.startswith("claude-haiku")

FOLLOWUP_AFTER_HOURS = float(os.getenv("FOLLOWUP_AFTER_HOURS", "20"))
