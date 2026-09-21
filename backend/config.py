"""
config.py - Environment configuration for the Homis app.

Reads all environment-dependent settings (secret key, database connection
info) from the process environment via python-dotenv, so the same code can
run locally and in production without modification.
"""

import os
from datetime import timedelta

from dotenv import load_dotenv
from sqlalchemy.engine import URL

# Load variables defined in a local .env file (SECRET_KEY, DB_*, ...) into
# the process environment. In production these are typically injected by
# the hosting platform instead, in which case .env may simply not exist -
# load_dotenv() silently does nothing if the file is missing.
load_dotenv()


def env_bool(name, default=False):
    """Read a strict, predictable boolean from the environment."""
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}

# Secret key used by Flask to cryptographically sign the session cookie.
# Read from the environment (see .env) instead of being hardcoded, so it
# never has to live in source control. No fallback is provided on purpose:
# if SECRET_KEY is missing from .env, the app should fail loudly (KeyError)
# rather than silently falling back to a weak, predictable key - anyone
# who knows this value can forge valid session cookies for any user.
SECRET_KEY = os.environ["SECRET_KEY"]

# All values fall back to local docker-compose defaults where it's safe to
# do so (host/port/database), but do NOT fall back to sensitive values
# (user/password) - the credentials from .env MUST be present, or the app
# will refuse to start with a clear KeyError instead of silently running
# with a hardcoded default password.
SQLALCHEMY_DATABASE_URI = URL.create(
    "mysql+pymysql",
    username=os.environ["DB_USER"],
    password=os.environ["DB_PASSWORD"],
    host=os.environ.get("DB_HOST", "127.0.0.1"),
    port=int(os.environ.get("DB_PORT", 3306)),
    database=os.environ.get("DB_NAME", "homis_db"),
)
SQLALCHEMY_TRACK_MODIFICATIONS = False

APP_ENV = os.environ.get("APP_ENV", "development").lower()
FLASK_DEBUG = env_bool("FLASK_DEBUG", False)
AUTO_CREATE_SCHEMA = env_bool("AUTO_CREATE_SCHEMA", APP_ENV != "production")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", APP_ENV == "production")
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.environ.get("SESSION_LIFETIME_HOURS", 8)))
MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024))
MAX_MESSAGE_LENGTH = int(os.environ.get("MAX_MESSAGE_LENGTH", 2_000))
SOCKET_MESSAGE_LIMIT = int(os.environ.get("SOCKET_MESSAGE_LIMIT", 30))
SOCKET_MESSAGE_WINDOW_SECONDS = int(os.environ.get("SOCKET_MESSAGE_WINDOW_SECONDS", 60))
SOCKETIO_CORS_ALLOWED_ORIGINS = None  # None permits only same-origin Socket.IO clients.
