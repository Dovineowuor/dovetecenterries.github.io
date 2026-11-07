"""
Full send-path verification using Django's locmem backend.
Exercises the same code as SMTP: per-recipient render, tracking ids,
NewsletterLog rows, KPI aggregation and MIME multipart + attachment.
"""
import email
import os
import re
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ["DJANGO_SETTINGS_MODULE"] = "_test_settings"
django.setup()

from django.conf import settings  # noqa: E402

settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

from django.core import mail  # noqa: E402

from home.models import Newsletter  # noqa: E402

TARGET = "owuordove@gmail.com"
newsletter = Newsletter.objects.get(subject="Q3 Innovation Digest - rendering test")
newsletter.manual_recipients = TARGET
newsletter.recipients.clear()
newsletter.logs.all().delete()
newsletter.status = "draft"
newsletter.sent_at = None
newsletter.resend_count = 0
newsletter.save()

print("=" * 70)
print("SEND PATH VERIFICATION (locmem backend)")
print("=" * 70)
print("recipients resolved :", newsletter.get_all_recipient_emails())
ok = newsletter.send_newsletter()
print("send_newsletter()   :", ok)
print("status              :", newsletter.status)
print("sent_at             :", newsletter.sent_at)
print("messages captured   :", len(mail.outbox))

assert len(mail.outbox) == 1, f"expected 1 message, got {len(mail.outbox)}"
msg = mail.outbox[0]

print("\n" + "-" * 70)
print("MIME STRUCTURE")
print("-" * 70)
print("subject  :", msg.subject)
print("from     :", msg.from_email)
print("to       :", msg.to)
print("Date     :", msg.message()["Date"])
print("Message-ID present:", bool(msg.message()["Message-ID"]))

raw = msg.message().as_string()
parsed = email.message_from_string(raw)
print("multipart:", parsed.is_multipart())
for part in parsed.walk():
    ctype = part.get_content_type()
    disp = part.get_content_disposition()
    print(f"  part: {ctype:30s} disposition={disp}")

print("\n" + "-" * 70)
print("CONTENT CHECKS")
print("-" * 70)
html_part = next(
    p.get_payload(decode=True).decode() for p in parsed.walk()
    if p.get_content_type() == "text/html"
)
text_part = next(
    p.get_payload(decode=True).decode() for p in parsed.walk()
    if p.get_content_type() == "text/plain"
)

log = newsletter.logs.get()
tracking_id = str(log.tracking_id)

checks = [
    ("html alternative present", 'multipart/alternative' in raw),
    ("text alternative clean", "font-family" not in text_part),
    ("text has no html tags", not re.search(r"<div|<table|<td", text_part)),
    ("html size sane", 20000 < len(html_part) < 60000),
    ("subject rendered", newsletter.subject in html_part),
    ("preheader rendered", newsletter.preheader in html_part),
    ("article section", "Scaling Postgres on Serverless" in html_part),
    ("resource section", "2026 Engineering Readiness Report" in html_part),
    ("service section", "Cloud Engineering" in html_part),
    ("product section", "Dovetec Pro Toolkit" in html_part),
    ("case study section", "Agridoer" in html_part),
    ("advert section", "Sponsor slot available" in html_part),
    ("advert labelled", "Advertisement" in html_part),
    ("attachment listed", "engineering-readiness-2026.txt" in html_part),
    ("tracking pixel uses this log id", f"track/open/{tracking_id}/" in html_part),
    ("click tracking uses this log id", f"track/click/{tracking_id}/" in html_part),
    ("click tracking applied", html_part.count("track/click/") >= 2),
    ("mailto left alone", 'href="mailto:hello@dovetecenterprises.tech"' in html_part),
    ("unsubscribe tokenised", re.search(
        r"https://dovetecenterprises\.site/newsletter/unsubscribe/[0-9a-f-]{32,36}/", html_part
    ) is not None),
    ("no un-tokenised unsubscribe", "/unsubscribe/\"" not in html_part),
    ("no domain typo", "dovetecenterries" not in html_part),
    ("dark mode css", "prefers-color-scheme: dark" in html_part),
    ("mobile breakpoint", "max-width: 620px" in html_part),
    ("caller text version used", text_part.strip().startswith(newsletter.subject)),
]
for name, result in checks:
    print(f"  {'PASS' if result else 'FAIL'}  {name}")

print("\n" + "-" * 70)
print("ATTACHMENT")
print("-" * 70)
att_parts = [p for p in parsed.walk() if p.get_content_disposition() == "attachment"]
for p in att_parts:
    print("  filename:", p.get_filename())
    print("  ctype   :", p.get_content_type())
    print("  bytes   :", len(p.get_payload(decode=True)))

print("\n" + "-" * 70)
print("LOGGING / KPIs")
print("-" * 70)
for l in newsletter.logs.all():
    print(f"  {l.email} status={l.status} tracking_id={l.tracking_id} sent_at={l.sent_at}")
print("  KPI:", newsletter.get_kpi_summary())

print("\n" + "-" * 70)
print("OPEN-TRACKING SIMULATION")
print("-" * 70)
log.mark_opened(ip_address="203.0.113.9", user_agent="Mozilla/5.0 (test)")
log.refresh_from_db()
print("  after open  :", log.status, "opened =", log.opened, "at", log.opened_at)
log.mark_clicked("https://dovetecenterprises.site/blog-detail/x")
log.refresh_from_db()
print("  after click :", log.status, "clicked =", log.clicked, "->", log.clicked_url)
log.mark_read()
log.refresh_from_db()
print("  after read  :", log.status, "read =", log.read, "at", log.read_at)
print("  engagement  :", log.engagement_score)
print("  KPI now     :", newsletter.get_kpi_summary())

failed = [n for n, r in checks if not r]
print("\n" + "=" * 70)
print("RESULT:", "ALL CHECKS PASSED" if not failed else f"{len(failed)} FAILED -> {failed}")
print("=" * 70)
