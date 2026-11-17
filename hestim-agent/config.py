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


def staff_accounts() -> dict[str, str]:
    """Per-person logins: INBOX_USERS="Amal:pw1,Karim:pw2". Falls back to the single INBOX_USER."""
    accounts = {}
    for pair in os.getenv("INBOX_USERS", "").split(","):
        if ":" in pair:
            name, pw = pair.split(":", 1)
            if name.strip() and pw:
                accounts[name.strip()] = pw
    return accounts or {INBOX_USER: INBOX_PASSWORD}


# Server-side refusal fallback exists for Opus 5.5 / Opus 5 / Sonnet 5.5 / Fable; not for Haiku.
SUPPORTS_FALLBACKS = not MODEL.startswith("claude-haiku")

FOLLOWUP_AFTER_HOURS = float(os.getenv("FOLLOWUP_AFTER_HOURS", "20"))
