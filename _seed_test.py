"""
Seed a newsletter exercising every content type, render it, and report.
Does NOT send. Run: python _seed_test.py
"""
import os
import sys

import django

sys.path.insert(0, os.getcwd())
os.environ["DJANGO_SETTINGS_MODULE"] = "_test_settings"
django.setup()

from django.utils import timezone  # noqa: E402

from home.models import (  # noqa: E402
    Advertisement, Article, Newsletter, NewsletterAttachment,
    NewsletterContentReference, NewsletterSubscription, Tag,
)
from app.models import CaseStudy  # noqa: E402
from shop.models import Category as ShopCategory, Product  # noqa: E402

TEST_EMAIL = "owuordove@gmail.com"

tag, _ = Tag.objects.get_or_create(name="Engineering", defaults={"slug": "engineering"})

article, _ = Article.objects.get_or_create(
    title="Scaling Postgres on Serverless",
    defaults={
        "content": "<p>How we tuned connection pooling for a serverless Django deployment.</p>",
        "status": "published",
    },
)
article.tags.add(tag)
article.save()

resource, _ = Article.objects.get_or_create(
    title="2026 Engineering Readiness Report",
    defaults={
        "content": "<p>Our annual benchmark report. 42 pages.</p>",
        "status": "published",
        "is_resource": True,
    },
)

service, _ = ShopCategory.objects.get_or_create(
    name="Cloud Engineering", defaults={"description": "Managed cloud, CI/CD and observability."}
)

product, _ = Product.objects.get_or_create(
    name="Dovetec Pro Toolkit",
    defaults={
        "price": "49.00",
        "stock": 25,
        "category": service,
        "description": "Deployment and monitoring toolkit.",
    },
)

case_study, _ = CaseStudy.objects.get_or_create(
    name="Agridoer",
    defaults={
        "description": "Rebuilt an agricultural marketplace.",
        "tagline": "From 3 to 30k monthly buyers.",
        "overview": "We replaced a monolith with an event-driven architecture.",
        "status": CaseStudy.STATUS_PUBLISHED,
        "featured": True,
    },
)

advert, _ = Advertisement.objects.get_or_create(
    title="Sponsor slot available",
    defaults={
        "description": "Reach 5,000+ engineering decision makers every week.",
        "url": "https://dovetecenterprises.site/advertise/",
    },
)

subscription, _ = NewsletterSubscription.objects.get_or_create(email=TEST_EMAIL)
subscription.is_verified = True
subscription.unsubscribed_at = None
subscription.save()

newsletter, created = Newsletter.objects.get_or_create(
    subject="Q3 Innovation Digest - rendering test",
    defaults={
        "preheader": "Everything we shipped this quarter",
        "subtitle": "A quarter of shipping, plus a free readiness report.",
        "content": (
            "<p>Hi there,</p>"
            "<p>Here is what we shipped in Q3. "
            '<a href="/blog/">Read the engineering blog</a> and '
            '<a href="https://dovetecenterprises.site/case-study/">browse our case studies</a>. '
            'Questions? <a href="mailto:hello@dovetecenterprises.tech">Email us</a>.</p>'
            "<p>Thanks,<br>The Dovetec team</p>"
        ),
        "manual_recipients": TEST_EMAIL,
        "status": "draft",
        "accent_color": "#0071e3",
        "cta_title": "See what we built",
        "cta_text": "Full case studies and the engineering report inside.",
        "cta_label": "Browse our work",
        "cta_url": "https://dovetecenterprises.site/portfolio/",
        "advertisement": advert,
    },
)

newsletter.recipients.set([subscription])
newsletter.adverts.set([advert])

reference_map = {
    "article": article,
    "resource": resource,
    "service": service,
    "product": product,
    "case_study": case_study,
    "advertisement": advert,
}
newsletter.content_references.all().delete()
for order, (kind, obj) in enumerate(reference_map.items()):
    NewsletterContentReference.objects.create(
        newsletter=newsletter, kind=kind, content_object=obj, order=order
    )

newsletter.save()

attachment, _ = NewsletterAttachment.objects.get_or_create(
    newsletter=newsletter,
    name="engineering-readiness-2026.txt",
    defaults={
        "description": "Placeholder report used to verify attachment delivery.",
        "order": 0,
    },
)
if not attachment.file:
    from django.core.files.base import ContentFile
    attachment.file.save(
        "engineering-readiness-2026.txt",
        ContentFile(b"Dovetec Enterprises\n2026 Engineering Readiness Report\n\nTest attachment.\n"),
        save=True,
    )

print(f"newsletter id      : {newsletter.id}")
print(f"created            : {created}")
print(f"status             : {newsletter.status}")
print(f"slug               : {newsletter.slug}")
print(f"recipients         : {newsletter.get_all_recipient_emails()}")
print(f"content_references : {list(newsletter.content_references.values_list('kind', flat=True))}")
print(f"attachments        : {[a.name for a in newsletter.attachments.all()]}")

groups = newsletter._resolve_content_groups()
print("\nresolved sections:")
for key, items in groups.items():
    print(f"  {key:12s} {len(items)}  {[str(i)[:40] for i in items]}")

from django.template.loader import render_to_string  # noqa: E402
from django.utils.html import strip_tags  # noqa: E402

html = newsletter._build_html_content(
    tracking_id="00000000-0000-0000-0000-000000000001",
    unsubscribe_url=f"{os.getenv('SITE_URL', 'https://dovetecenterprises.site')}/newsletter/unsubscribe/{subscription.token}/",
)
os.makedirs("/tmp/opencode/preview", exist_ok=True)
with open("/tmp/opencode/preview/newsletter.html", "w") as fh:
    fh.write(html)
with open("/tmp/opencode/preview/newsletter.txt", "w") as fh:
    fh.write(strip_tags(html))

print(f"\nhtml bytes         : {len(html)}")
print(f"text bytes         : {len(strip_tags(html))}")
print("previews written   : /tmp/opencode/preview/newsletter.{html,txt}")

print("\ntraced links:")
import re
for link in re.findall(r'href="([^"]*track/click[^"]*)"', html)[:8]:
    print("  ", link[:120])
print("\ntracking pixel     :", bool(re.search(r'track/open/', html)))
print("unsubscribe link   :", bool(re.search(r'newsletter/unsubscribe/', html)))
