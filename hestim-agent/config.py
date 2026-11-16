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

FOLLOWUP_AFTER_HOURS = float(os.getenv("FOLLOWUP_AFTER_HOURS", "20"))
