"""
Combined (single-container) settings.

Django serves both the REST API and the pre-built React frontend.
WhiteNoise is used for efficient static-file delivery so no separate
web-server is needed.  The database defaults to SQLite (zero-config),
but PostgreSQL (or any other engine) can be selected via environment
variables — the same ones used by the production settings.
"""
from .base import *  # noqa: F401,F403
import os

DEBUG = os.environ.get("DEBUG", "False").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "*").split(",")

# ── Database ─────────────────────────────────────────────────────────────────
_db_engine = os.environ.get("DB_ENGINE", "django.db.backends.sqlite3")

if _db_engine == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": _db_engine,
            "NAME": os.environ.get("DB_NAME", "game_db"),
            "USER": os.environ.get("DB_USER", ""),
            "PASSWORD": os.environ.get("DB_PASSWORD", ""),
            "HOST": os.environ.get("DB_HOST", "localhost"),
            "PORT": os.environ.get("DB_PORT", "5432"),
        }
    }

# ── Static files (WhiteNoise) ─────────────────────────────────────────────────
# Insert WhiteNoise right after SecurityMiddleware so it handles static files
# before Django's own middleware stack runs.
_security_idx = MIDDLEWARE.index(  # noqa: F405
    "django.middleware.security.SecurityMiddleware"
)
MIDDLEWARE.insert(  # noqa: F405
    _security_idx + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"  # noqa: F405

# WhiteNoise will compress static assets.  We use the plain (non-manifest)
# variant because Vite already adds content-hash suffixes to its output files,
# so Django's ManifestStaticFilesStorage post-processing is unnecessary and can
# break asset references by renaming already-hashed filenames.
STATICFILES_STORAGE = "whitenoise.storage.CompressedStaticFilesStorage"

# The built React bundle is placed here by the multi-stage Docker build.
STATICFILES_DIRS = [
    BASE_DIR / "frontend_build",  # noqa: F405
]

# Make the React index.html available to Django's template engine so the
# catch-all URL rule can render it for client-side routing.
TEMPLATES[0]["DIRS"] = [BASE_DIR / "frontend_build"]  # noqa: F405

# ── CORS ──────────────────────────────────────────────────────────────────────
# All origins are allowed inside the single container because the browser talks
# to the same host/port for both the API and the React app.
CORS_ALLOW_ALL_ORIGINS = True

# ── Security (relaxed for single-container / ShinyProxy deployments) ──────────
# TLS termination is handled upstream (ShinyProxy / reverse-proxy).
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() in (
    "1",
    "true",
    "yes",
)
CSRF_COOKIE_SECURE = os.environ.get("CSRF_COOKIE_SECURE", "False").lower() in (
    "1",
    "true",
    "yes",
)

# ── ShinyProxy compatibility ──────────────────────────────────────────────────
# ShinyProxy may embed the app in a sub-path.  Setting X_FRAME_OPTIONS to
# SAMEORIGIN (instead of the default DENY) allows iframing from the same host.
X_FRAME_OPTIONS = "SAMEORIGIN"
