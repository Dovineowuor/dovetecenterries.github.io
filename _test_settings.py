"""Test-only settings: force SQLite so local tests do not touch Neon."""
import os

os.environ["DATABASE_URL"] = ""
os.environ.pop("DATABASE_URL", None)

from dovetecenterprises.settings import *  # noqa: F401,F403
from dovetecenterprises import settings as _base

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Honour DATABASE_NAME so a caller can point at a throwaway file
        # (DATABASE_NAME=/tmp/seed.db) for a genuinely fresh run. Previously
        # this was pinned to the repo's db.sqlite3, which silently ignored the
        # override and reused an already-seeded database.
        "NAME": os.environ.get("DATABASE_NAME")
        or os.path.join(_base.BASE_DIR, "db.sqlite3"),
    }
}

# Never email the real admin address during tests. A failing test used to
# dispatch a real SMTP error report (including a full traceback) to the
# production mailbox, which is noisy and leaks debug output. The locmem
# backend keeps mail in memory so tests can assert on it instead.
ADMINS = [("Test Admin", "test-admin@example.com")]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
DEFAULT_FROM_EMAIL = "test-admin@example.com"
SERVER_EMAIL = "test-admin@example.com"
# A 500 during a test is a test failure, not a reason to mail anyone.
EMAIL_SUBJECT_PREFIX = "[TEST] "

ALLOWED_HOSTS = list(ALLOWED_HOSTS) + ["testserver", "localhost", "127.0.0.1"]
