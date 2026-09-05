"""Central configuration. All secrets come from environment variables
(or a local .env file, loaded via python-dotenv if present)."""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:  # python-dotenv optional
    pass

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# SQLite by default; switch to PostgreSQL by setting DATABASE_URL, e.g.
#   DATABASE_URL=postgresql://user:pass@host:5432/lcd
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'lcd.db')}")

# A hard-coded fallback keeps local development working, but production MUST
# set JWT_SECRET. create_app() logs a loud warning when it is unchanged.
DEV_JWT_SECRET = "dev-secret-change-me"
JWT_SECRET = os.environ.get("JWT_SECRET", DEV_JWT_SECRET)
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "168"))  # 7 days

# Gemini AI. When GEMINI_API_KEY is unset the AI service runs in
# deterministic "demo mode" so the whole application remains functional.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

UPLOAD_DIR = os.environ.get("UPLOAD_DIR", os.path.join(BASE_DIR, "uploads"))
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "20"))

# Browser origins allowed to call the API cross-origin. Comma-separated.
# The Vite dev server proxies /api, so same-origin requests are unaffected.
CORS_ORIGINS = [
    o.strip() for o in os.environ.get(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if o.strip()
]

# Lightweight in-memory rate limits (per process). Auth and demo endpoints are
# the only public, write-capable surfaces worth protecting by default.
RATE_LIMIT_AUTH_PER_HOUR = int(os.environ.get("RATE_LIMIT_AUTH_PER_HOUR", "40"))
RATE_LIMIT_DEMO_PER_HOUR = int(os.environ.get("RATE_LIMIT_DEMO_PER_HOUR", "25"))

# Supported UI languages (validated server-side on profile updates).
SUPPORTED_LANGUAGES = {"en", "hi", "kn", "ta", "te", "ml", "mr", "bn"}

# Legal disclaimer shown on every AI-generated surface.
LEGAL_DISCLAIMER = (
    "This application provides informational and decision-support assistance "
    "and is not a substitute for advice from a qualified legal professional. "
    "AI-generated content may contain errors and must be verified by a qualified "
    "legal professional before any action is taken."
)

ALLOWED_EXTENSIONS = {"pdf", "docx", "txt", "png", "jpg", "jpeg", "gif", "webp"}