"""
Development settings — SQLite (default) or PostgreSQL via env vars, debug toolbar, relaxed CORS.
"""

from .base import *  # noqa: F401,F403
import os

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "computproteomics.bmb.sdu.dk"]

_db_engine = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")

if _db_engine == "django.db.backends.sqlite3":
    _sqlite_path = Path(os.environ.get("SQLITE_DB_PATH", BASE_DIR / "db.sqlite3"))  # noqa: F405
    if not _sqlite_path.is_absolute():
        _sqlite_path = BASE_DIR / _sqlite_path  # noqa: F405
    _sqlite_path = _sqlite_path.resolve()
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _sqlite_path,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": _db_engine,
            "NAME": os.environ.get("DB_NAME", "game_db"),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "db"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://computproteomics.bmb.sdu.dk",
    "http://computproteomics.bmb.sdu.dk",
]
