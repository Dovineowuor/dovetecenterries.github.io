"""Send the test newsletter to owuordove@gmail.com via real Gmail SMTP."""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ["DJANGO_SETTINGS_MODULE"] = "_test_settings"
django.setup()

from django.conf import settings  # noqa: E402
from django.core.mail import get_connection  # noqa: E402

from home.models import Newsletter  # noqa: E402

TARGET = "owuordove@gmail.com"

newsletter = Newsletter.objects.get(subject="Q3 Innovation Digest - rendering test")

# Test only: send to the single test address.
newsletter.manual_recipients = TARGET
newsletter.recipients.clear()
newsletter.save()

print("EMAIL_HOST     :", settings.EMAIL_HOST, settings.EMAIL_PORT, "tls=", settings.EMAIL_USE_TLS)
print("EMAIL_HOST_USER:", settings.EMAIL_HOST_USER)
print("from           :", settings.DEFAULT_FROM_EMAIL)
print("to             :", TARGET)
print("-" * 60)

conn = get_connection()
try:
    conn.open()
    print("SMTP: connected OK")
    conn.close()
except Exception as exc:
    print(f"SMTP: FAILED -> {type(exc).__name__}: {exc}")
    sys.exit(1)

print("-" * 60)
ok = newsletter.send_newsletter()
print("send_newsletter() returned:", ok)

newsletter.refresh_from_db()
print("status   :", newsletter.status)
print("sent_at  :", newsletter.sent_at)
print("resends  :", newsletter.resend_count)

for log in newsletter.logs.all():
    print(
        f"log: {log.email}  status={log.status}  tracking_id={log.tracking_id}  "
        f"sent_at={log.sent_at}  error={log.error!r}"
    )

print("-" * 60)
print("KPI summary:", newsletter.get_kpi_summary())
