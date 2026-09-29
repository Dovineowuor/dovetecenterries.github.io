"""Create admin accounts and load domain-aligned dummy data.

Run:  python manage.py seed_dummy_data

Creates administrators (and a staff account), then populates every app with
idempotent sample data drawn from dovetecenterprises.seed_data, so the site
looks like a real Dovetec Enterprises deployment: Nairobi-based software
engineering and IT consulting across East African industry verticals.

Content-creation signals are disconnected for the duration of the run.
Without this, each Article, Product, Topic and Post created here would also
generate its own Newsletter row, burying the intended sample digest.
"""
import getpass
import os
import secrets
import string
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.text import slugify

from dovetecenterprises import seed_data as S

from home.models import (
    ApplicationNote, Article, Comment, Department, Dislike, DiscussionTopic,
    Feedback, Interview, Job, JobApplication, Like, Notification,
    Newsletter, NewsletterAttachment, NewsletterContentReference, NewsletterLog,
    NewsletterSubscription, Reply, Report, SourceTracker, Tag,
)
from home.models import Advertisement as HomeAdvertisement
from home.models import User as AuthUser
from home.roles import ensure_role_groups
from home.signals import (
    create_article_newsletter, create_post_newsletter,
    create_product_newsletter, create_topic_newsletter,
)
from app.models import (
    Answer, CaseStudy, Contact, FeatureMicrotask, FeatureRequest, FeatureTask,
    FeatureVote, MediaAsset, Organization, Plan, Project, Questionnaire,
    QuestionnaireEvent, QuestionnaireTemplate, Question, ServiceInquiry,
    Subscription, Ticket, TicketActivity, WhatsAppNotification,
)
from shop.models import (
    Cart, CartItem, Category as ShopCategory, Keyword, Order, OrderItem,
    Payment, Product,
)
from community.models import Category as CommunityCategory, Event, Post, Topic
from community.models import Comment as CommunityComment
from community.models import Dislike as CommunityDislike
from community.models import Reply as CommunityReply
from adverts.models import Advertisement as SiteAdvertisement, AdvertLeads as AdvertLead

# ── Accounts ───────────────────────────────────────────────────────────
# No account carries a password here. Passwords are resolved at run time from
# --password, the SEED_PASSWORD environment variable, or a freshly generated
# random value, so no credential is ever committed to the repository.
ADMINS = [
    {
        "email": "admin@dovetecenterprises.tech",
        "first_name": "Sarah", "last_name": "Johnson",
        "title": "Principal Consultant",
        "bio": "Principal consultant at Dovetec Enterprises, leading software engineering engagements across East Africa.",
    },
    {
        "email": "dove@dovetecenterprises.tech",
        "first_name": "Dove", "last_name": "Owino",
        "title": "Founder & Lead Engineer",
        "bio": "Founder of Dovetec Enterprises. Builds delivery practice and architecture for fintech and healthcare clients.",
    },
    {
        "email": "admin2@dovetecenterprises.tech",
        "first_name": "Michael", "last_name": "Chen",
        "title": "Head of Engineering",
        "bio": "Heads engineering at Dovetec Enterprises. Focus on infrastructure, observability and delivery reliability.",
    },
]
STAFF = {
    "email": "staff@dovetecenterprises.tech",
    "first_name": "Achieng", "last_name": "Otieno",
    "title": "Support Engineer",
    "bio": "Support and maintenance at Dovetec Enterprises.",
}
CLIENTS = [
    ("james.otieno@harambeesacco.co.ke", "James", "Otieno", "Chief Executive Officer"),
    ("linda.mwangi@oddibites.co.ke", "Linda", "Mwangi", "Operations Director"),
    ("grace.njeri@techdarasa.ac.ke", "Grace", "Njeri", "Head of ICT"),
    ("daniel.kimani@savannahfreight.com", "Daniel", "Kimani", "Fleet Manager"),
    ("esther.wanjiku@jamiihealth.or.ke", "Esther", "Wanjiku", "Clinical Systems Lead"),
    ("peter.kariuki@rift-solar.co.ke", "Peter", "Kariuki", "Operations Lead"),
]

DEPARTMENTS = [
    ("Software Engineering", "Product and platform engineering across web, mobile and backend."),
    ("Cloud & Infrastructure", "Managed infrastructure, deployments and reliability."),
    ("Quality Assurance", "Test strategy, automation and performance engineering."),
    ("Design", "User research, interface design and design systems."),
    ("Client Success", "Onboarding, support and account management."),
]

JOBS = [
    ("Senior Backend Engineer", "Software Engineering", "Nairobi, Kenya (Hybrid)", "Senior", "330000.00",
     "<p>We are looking for a senior backend engineer to work on payment and lending systems for financial services clients across East Africa.</p><h2>What you will do</h2><p>Design and build services in Python and Django, integrate with payment providers, and own the reliability of systems our clients depend on.</p><h2>What we are looking for</h2><p>Deep Python and Django experience, sound judgement about data modelling, and comfort working in domains where correctness matters more than velocity.</p>"),
    ("Mobile Engineer (Android)", "Software Engineering", "Nairobi, Kenya (Hybrid)", "Mid", "250000.00",
     "<p>Join the team building offline-first mobile applications for field teams and consumers across Kenya, Uganda and Tanzania.</p><h2>What you will do</h2><p>Build Android applications in Kotlin, own the synchronisation architecture, and work directly with clients to understand the constraints their users actually face.</p>"),
    ("DevOps Engineer", "Cloud & Infrastructure", "Nairobi, Kenya (Remote-friendly)", "Mid", "270000.00",
     "<p>You will own our deployment pipeline, observability stack and cloud cost management.</p><h2>What you will do</h2><p>Build reproducible infrastructure as code, improve deployment safety, and keep cloud spend proportionate to client value.</p>"),
    ("QA Automation Engineer", "Quality Assurance", "Nairobi, Kenya (Hybrid)", "Mid", "220000.00",
     "<p>We need a QA engineer to build the automated regression suites that let our teams ship weekly with confidence.</p><h2>What you will do</h2><p>Design test strategy, build automated coverage in pytest and Playwright, and make quality visible rather than aspirational.</p>"),
    ("UI/UX Designer", "Design", "Nairobi, Kenya (Hybrid)", "Mid", "210000.00",
     "<p>Design interfaces for public sector and financial services products, where accessibility and trust are non-negotiable.</p><h2>What you will do</h2><p>Run user research, design and prototype, and work with engineers to keep our component library accessible by default.</p>"),
    ("Client Success Manager", "Client Success", "Nairobi, Kenya (Hybrid)", "Senior", "235000.00",
     "<p>Own the relationship with a portfolio of clients across the region, from onboarding through steady state.</p><h2>What you will do</h2><p>Translate client outcomes into engineering priorities, and make sure the value we promised is the value they receive.</p>"),
]

# ── CRM ───────────────────────────────────────────────────────────────
ORGANIZATIONS = [
    ("Harambee Sacco Union", "fintech", "https://harambeesacco.co.ke"),
    ("TechDarasa", "education", "https://techdarasa.ac.ke"),
    ("Oddibites", "retail", "https://oddibites.co.ke"),
    ("Agridoer", "agriculture", "https://agridoer.co.ke"),
    ("Jamii Health Network", "health", "https://jamiihealth.or.ke"),
    ("Savannah Freight Forwarders", "manufacturing", "https://savannahfreight.com"),
    ("Coastal Networks Limited", "telecom", "https://coastalnet.co.ke"),
    ("Rift Solar Collective", "energy", "https://rift-solar.co.ke"),
    ("Pamoja Health Initiative", "ngo", "https://pamojahealth.org"),
]

# Substring of the client email domain -> industry slug. Several client
# domains differ from their organisation name, so this is keyed explicitly
# rather than derived.
CLIENT_INDUSTRY_BY_DOMAIN = {
    "harambeesacco": "fintech",
    "techdarasa": "education",
    "oddibites": "retail",
    "jamiihealth": "health",
    "savannahfreight": "manufacturing",
    "coastalnet": "telecom",
    "rift-solar": "energy",
    "pamojahealth": "ngo",
    "agridoer": "agriculture",
}

# Client email -> organisation name in ORGANIZATIONS, so CRM contacts are
# anchored to a real account rather than an arbitrary org of the same
# industry.
CLIENT_ORGANIZATION_BY_EMAIL = {
    "james.otieno@harambeesacco.co.ke": "Harambee Sacco Union",
    "grace.njeri@techdarasa.ac.ke": "TechDarasa",
    "linda.mwangi@oddibites.co.ke": "Oddibites",
    "esther.wanjiku@jamiihealth.or.ke": "Jamii Health Network",
    "daniel.kimani@savannahfreight.com": "Savannah Freight Forwarders",
    "peter.kariuki@rift-solar.co.ke": "Rift Solar Collective",
}

TICKETS = [
    ("Unable to complete checkout on the mobile app", "issue", "open", "high", "software",
     "Members report that the payment step hangs after submitting on Android 13. Started after the Friday release.",
     "grace.njeri@techdarasa.ac.ke"),
    ("Request for invoice reissue", "enquiry", "resolved", "normal", "it",
     "The March invoice was issued to the wrong entity after the group restructure. Please reissue to the new entity.",
     "linda.mwangi@oddibites.co.ke"),
    ("Adding two new staff users to the dashboard", "enquiry", "open", "normal", "other",
     "We have two new finance staff who need dashboard access with reporting permissions.",
     "daniel.kimani@savannahfreight.com"),
    ("Data export timing out for large date ranges", "issue", "new", "urgent", "software",
     "Exports beyond roughly 90 days time out. We need a year of history for a board pack this week.",
     "esther.wanjiku@jamiihealth.or.ke"),
    ("Clarification on the support retainer terms", "enquiry", "waiting", "low", "consulting",
     "Could you confirm whether the retainer includes after-hours response for a production incident?",
     "peter.kariuki@rift-solar.co.ke"),
    ("SSO integration requirements for a new client", "enquiry", "open", "high", "consulting",
     "The client requires SAML SSO with SCIM provisioning before their internal rollout.",
     "james.otieno@harambeesacco.co.ke"),
    ("Offline sync failing on older Android devices", "issue", "open", "high", "software",
     "A subset of members on Android 8 and 9 report sync failures that we cannot reproduce on newer devices.",
     "james.otieno@harambeesacco.co.ke"),
    ("Request to disable a deprecation warning", "issue", "closed", "low", "it",
     "The deprecation banner appears for an endpoint we still call and cannot yet migrate away from.",
     "daniel.kimani@savannahfreight.com"),
]

PROJECTS = [
    ("Harambee field lending platform", "active", "high", "software", "fintech",
     "Continued delivery on the field origination and offline disbursement platform.", 4500000.00),
    ("TechDarasa fee collection phase 2", "active", "medium", "software", "education",
     "M-Pesa fee collection with automated reconciliation and parent statements.", 2800000.00),
    ("Oddibites multi-branch retail rollout", "completed", "medium", "it", "retail",
     "Point of sale and live inventory across six branches.", 1900000.00),
    ("Jamii Health records rollout", "active", "high", "software", "health",
     "Patient record deployment across 38 facilities with offline synchronisation.", 6200000.00),
    ("Savannah telematics integration", "on_hold", "low", "software", "manufacturing",
     "Telematics ingestion and exception alerting, paused pending vendor API access.", 3100000.00),
    ("Coastal Networks assurance tooling", "active", "medium", "consulting", "telecom",
     "Self-service diagnostics tooling for field technicians.", 2200000.00),
]

PLANS = [
    ("Starter", "starter", 0.00, "monthly", True,
     "Up to 3 team members\n5 GB storage\nCommunity support\nMonthly backups"),
    ("Growth", "growth", 45000.00, "monthly", False,
     "Up to 25 team members\n100 GB storage\nPriority support\nDaily backups\nCustom domains"),
    ("Scale", "scale", 120000.00, "monthly", False,
     "Unlimited team members\n1 TB storage\nDedicated success manager\nHourly backups\nSLA and audit logs"),
    ("Annual Growth", "annual-growth", 450000.00, "yearly", False,
     "Everything in Growth\nTwo months free\nQuarterly architecture review"),
]

FEATURE_REQUESTS = [
    ("Dark mode across the admin dashboard", "open", "platform", 24,
     "Night-shift staff report the bright interface causes eye strain during overnight operations reviews."),
    ("Bulk user import from CSV", "in_progress", "portal", 41,
     "Onboarding large cohorts currently requires one record at a time through the admin interface."),
    ("Scheduled report delivery by email", "open", "portal", 33,
     "Leadership teams want the same dashboard delivered on a schedule rather than remembered to check."),
    ("Per-role dashboard permissions", "planned", "platform", 28,
     "Finance staff need reporting access without visibility into other operational areas."),
    ("Mobile-friendly invoice viewer", "shipped", "portal", 19,
     "Field staff need to view and share invoices from mobile devices during site visits."),
    ("Webhook retries with backoff", "open", "billing", 12,
     "Failed webhooks currently require manual replay, which delays downstream reconciliation."),
]

FEATURE_TASKS = [
    ("Dark mode across the admin dashboard", "Add theme tokens to the design system", "high", "todo"),
    ("Dark mode across the admin dashboard", "Migrate admin components to token variables", "medium", "in_progress"),
    ("Bulk user import from CSV", "Define the import contract and validation rules", "high", "done"),
    ("Bulk user import from CSV", "Implement the import job with progress reporting", "high", "in_progress"),
    ("Scheduled report delivery by email", "Add a delivery schedule model", "medium", "todo"),
    ("Per-role dashboard permissions", "Map existing groups to report scopes", "high", "todo"),
]

# ── Adverts ───────────────────────────────────────────────────────────
ADVERT_SLOTS = [
    ("Cloud migration readiness", "Reach engineering leaders evaluating a migration. Book a scoping call.", "https://dovetecenterprises.vercel.app/services/"),
    ("ISO 27001 readiness review", "A two-week assessment of your security posture and evidence pack.", "https://dovetecenterprises.vercel.app/services/"),
    ("Managed support retainer", "Dependable engineering support with defined response times.", "https://dovetecenterprises.vercel.app/services/"),
    ("Offline-first architecture workshop", "A two-day workshop for teams shipping to low-connectivity markets.", "https://dovetecenterprises.vercel.app/services/"),
]


def _png(colour, size=(600, 400)):
    """Build a small solid-colour PNG so mandatory ImageFields get a real file."""
    buf = BytesIO()
    Image.new("RGB", size, colour).save(buf, format="PNG")
    buf.seek(0)
    return buf


def _txt(body, name):
    return ContentFile(body.encode("utf-8"), name=name)


def _ago(days=0, hours=0):
    """A past timestamp, so published_at ordering looks like a real archive."""
    return timezone.now() - timezone.timedelta(days=days, hours=hours)


def _published(model, days_ago=30):
    """Publish a content row, backdating it so the archive has a spread of dates.

    Every content model mixes in an SEO block whose ``published_at`` is left
    null by default (meaning "never published"). The sample site is a live
    site, so all seeded content is published; backdating keeps the ordering
    on the blog, careers and community pages plausible.
    """
    return _ensure(model, published_at=_ago(days_ago))


def _seo(instance, title, description, *, url="", kind="page", days_ago=30):
    """Write the full SEO block a MetadataMixin model carries.

    Every content, taxonomy and CRM model mixes in the same eight SEO columns
    plus a ``published_at``. They all default to blank, which leaves search
    engines and social cards with nothing to show, so seeded rows are given a
    complete, self-consistent block.
    """
    canonical = url or f"https://dovetecenterprises.vercel.app/{kind}/{slugify(title)}/"
    return _ensure(
        instance,
        meta_title=f"{title} | Dovetec Enterprises",
        meta_description=description[:250],
        canonical_url=canonical,
        og_title=title,
        og_description=description[:250],
        twitter_card="summary_large_image",
        twitter_title=title,
        twitter_description=description[:250],
    )


def _blurb_for(model, row, title):
    """A one-line description for a model's SEO block, per model type."""
    label = model.__name__
    if label == "Tag":
        return f"Articles, guides and case studies filed under {title}."
    if label == "Department":
        return row.description or f"The {title} team at Dovetec Enterprises."
    if label == "Job":
        return row.description or f"Open {title} role at Dovetec Enterprises."
    if label == "Category":
        return f"Browse {title} from Dovetec Enterprises."
    if label == "Product":
        return (
            f"{title} from Dovetec Enterprises: "
            f"KES {row.price:,.0f}. Delivered with setup and support included."
        )
    if label == "Keyword":
        return f"{title} solutions delivered by Dovetec Enterprises."
    if label == "Topic":
        return f"Community discussion about {title}."
    if label == "Event":
        return row.description or f"{title}, hosted by Dovetec Enterprises."
    if label == "SourceTracker":
        return f"Candidate sourcing through {title}."
    if label == "Newsletter":
        return row.subtitle or f"{title} from Dovetec Enterprises."
    if label == "Advertisement":
        return row.description or f"{title} advertised through Dovetec Enterprises."
    if label == "ServiceInquiry":
        return f"Service enquiry from {row.name} about {row.service}."
    if label == "Project":
        return row.description or f"{title} delivered by Dovetec Enterprises."
    if label == "CaseStudy":
        return f"How {title} was designed, built and delivered."
    return f"{title} from Dovetec Enterprises."


def _ensure(instance, **fields):
    """Write seeder-owned fields onto a row, whether or not it already existed.

    Data migration 0016 pre-creates a good number of these rows, so a
    get_or_create reports created=False and its ``defaults`` never land. That
    left whole columns null on any database migrated before this command ran.
    Updating explicitly makes the seeder converge on the same shape either
    way, and keeps reruns idempotent because nothing is written unless the
    value actually differs.
    """
    if not any(getattr(instance, name) != value for name, value in fields.items()):
        return instance
    for name, value in fields.items():
        setattr(instance, name, value)
    instance.save(update_fields=list(fields))
    return instance


class Command(BaseCommand):
    help = "Create admin accounts and load industry-aligned dummy data across all apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", default=None,
            help=(
                "Password to set on every account this run creates. Omit to use "
                "$SEED_PASSWORD, else you are prompted, else a random password is "
                "generated and shown once."
            ),
        )
        parser.add_argument(
            "--flush-newsletters", action="store_true",
            help="Delete auto-generated Newsletter rows before seeding the sample digest.",
        )
        parser.add_argument(
            "--no-images", action="store_true",
            help="Skip image uploads; mandatory image fields are left blank.",
        )

    def _resolve_password(self, supplied):
        """Resolve a password for this run without ever committing one.

        Order: --password, $SEED_PASSWORD, interactive prompt, random.
        """
        if supplied:
            return supplied, "supplied via --password"
        env = os.environ.get("SEED_PASSWORD")
        if env:
            return env, "supplied via $SEED_PASSWORD"
        if not sys.stdin.isatty():
            # Non-interactive (CI, deploy) with no secret available: generate
            # one and print it rather than silently shipping a default.
            return self._random_password(), "generated (no password available)"
        typed = getpass.getpass("Password for seeded accounts: ")
        if not typed:
            raise CommandError("Password must not be empty.")
        if len(typed) < 12:
            raise CommandError(
                "Password must be at least 12 characters; use --password, "
                "$SEED_PASSWORD, or a longer value."
            )
        return typed, "entered interactively"

    @staticmethod
    def _random_password():
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        return "".join(secrets.choice(alphabet) for _ in range(24))

    def handle(self, *args, **opts):
        password, origin = self._resolve_password(opts["password"])
        self.stdout.write(f"Seed password {origin}.")
        make_images = not opts["no_images"]

        # Creating Articles/Products/Topics/Posts fires receivers that each
        # manufacture a Newsletter. Silence them for the run so the only
        # newsletter in the database is the one we author deliberately.
        with self._content_signals_disconnected():
            with transaction.atomic():
                groups = ensure_role_groups()
                summary = {}
                summary["accounts"] = self._accounts(password, groups)
                summary["taxonomy"] = self._taxonomy()
                summary["content"] = self._content(summary["taxonomy"], make_images)
                summary["case_studies"] = self._case_studies(summary["taxonomy"], make_images)
                summary["crm"] = self._crm(summary["accounts"])
                summary["catalog"] = self._catalog(summary["taxonomy"], make_images)
                summary["community"] = self._community(summary["accounts"], summary["taxonomy"], make_images)
                summary["talent"] = self._talent()
                summary["platform"] = self._platform(
                    summary["accounts"], summary["crm"], summary["content"]["articles"]
                )
                summary["questionnaires"] = self._questionnaires(summary["crm"])
                summary["engagement"] = self._engagement(summary["content"])
                summary["newsletter"] = self._newsletter(
                    summary["taxonomy"], summary["content"], make_images
                )
                summary["adverts"] = self._adverts(summary["taxonomy"], make_images)
                self._blank_fields()
                if opts["flush_newsletters"]:
                    summary["newsletter"]["removed"] = Newsletter.objects.filter(
                        subject__startswith=("📖", "🛍️", "🤝", "🔥")
                    ).delete()[0]

        self.stdout.write(self.style.MIGRATE_HEADING("\nSeeded Dovetec Enterprises dummy data"))
        for section, counts in summary.items():
            # Report creation counts only. Returning the ORM objects passed
            # between steps would dump hundreds of repr() lines.
            made = counts.get("made") if isinstance(counts, dict) else None
            if made is None and isinstance(counts, dict):
                made = counts
            if not made:
                continue
            self.stdout.write(f"  {section}:")
            for key, value in made.items():
                self.stdout.write(f"    {key}: {value}")
        if opts["password"] is not None or os.environ.get("SEED_PASSWORD") \
                or not sys.stdin.isatty():
            # Show it once so the operator can sign in; never re-printed and
            # never stored in the repository.
            self.stdout.write(self.style.SUCCESS(
                f"\nSign in at /admin/ as {ADMINS[0]['email']}\n"
                f"Password (shown once): {password}"
            ))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\nSign in at /admin/ as {ADMINS[0]['email']} "
                f"with the password you entered."
            ))

    class _content_signals_disconnected:
        def __enter__(self):
            self.pairs = [
                (create_article_newsletter, Article),
                (create_product_newsletter, Product),
                (create_topic_newsletter, Topic),
                (create_post_newsletter, Post),
            ]
            for receiver, sender in self.pairs:
                post_save.disconnect(receiver, sender=sender)
            return self

        def __exit__(self, *exc):
            for receiver, sender in self.pairs:
                post_save.connect(receiver, sender=sender)
            return False

    # ── Accounts ───────────────────────────────────────────────────────
    def _blank_fields(self):
        """Fill the columns that no model-level pass owns.

        A few columns are left blank by design everywhere else: the SEO block
        on taxonomy rows, the structured design payloads on case studies, and
        the handful of free-text notes that depend on a row's status. Handling
        them in one place keeps every model's shape complete and means a new
        app only needs its own section to stay consistent with the rest.
        """
        SITE = "https://dovetecenterprises.vercel.app"

        # 1. SEO block on every model that carries one.
        for model, kind in [
            (Tag, "blog"), (Department, "careers"), (Job, "careers"),
            (ShopCategory, "shop"), (Keyword, "shop"), (Product, "shop"),
            (CommunityCategory, "community"),
            (Topic, "community"), (Event, "community"), (SourceTracker, "careers"),
            (Newsletter, "newsletter"), (SiteAdvertisement, "advertise"),
            (ServiceInquiry, "contact-us"), (Project, "services"),
            (CaseStudy, "case-studies"),
        ]:
            names = {f.name for f in model._meta.get_fields()}
            if "meta_title" not in names:
                # Not every model carries the SEO mixin (SourceTracker is a
                # plain reporting table, for instance).
                continue
            name_field = next(
                (c for c in ("name", "title", "source_name", "subject") if c in names),
                None,
            )
            if name_field is None:
                continue
            for index, row in enumerate(model.objects.all()):
                title = getattr(row, name_field) or str(row)
                _seo(
                    row, title, _blurb_for(model, row, title),
                    url=f"{SITE}/{kind}/{slugify(title)}/",
                    kind=kind, days_ago=30 + index * 3,
                )

        # 2. Design case studies: the structured UX payloads the templates read.
        for index, case in enumerate(CaseStudy.objects.all()):
            _ensure(
                case,
                persona_data={
                    "name": case.name,
                    "role": "Operations lead",
                    "goals": ["Reduce data entry time", "Work offline in the field"],
                    "frustrations": ["Duplicate paper forms", "No visibility past submission"],
                },
                task_mapping={
                    "capture": "Field officer records a customer visit",
                    "verify": "Supervisor approves the captured record",
                    "report": "Manager exports a monthly summary",
                },
                matrix_data={
                    "columns": ["Task", "Frequency", "Pain", "Owner"],
                    "rows": [
                        ["Data capture", "Daily", "High", "Field officer"],
                        ["Verification", "Daily", "Medium", "Supervisor"],
                        ["Reporting", "Weekly", "Low", "Manager"],
                    ],
                },
                sketches=["Wireframe: dashboard", "Wireframe: capture form",
                          "Wireframe: report export"],
                major_screens=["Dashboard", "Capture form", "Approval queue", "Reports"],
                screens=[
                    {"name": "Dashboard", "purpose": "Daily overview of field activity"},
                    {"name": "Capture form", "purpose": "Offline-first record entry"},
                    {"name": "Approval queue", "purpose": "Supervisor review"},
                ],
            )

        # 3. Status-dependent free text.
        for index, ticket in enumerate(Ticket.objects.all()):
            _ensure(
                ticket,
                timeline=(
                    "Signed SOW and 50% deposit received; sprint one starts "
                    "after the client confirms the data fields."
                    if ticket.status in ("open", "waiting", "new") else
                    "Delivered in three two-week sprints with a fortnight of "
                    "post-launch support included in the SOW."
                ),
            )

        for index, sub in enumerate(Subscription.objects.all()):
            who = sub.user.email if sub.user_id else f"subscriber-{index}"
            _ensure(
                sub,
                payment_reference=f"MPE-{2400 + index}-{slugify(who)[:6]}",
                notes=(
                    "Annual plan, invoiced monthly. Renews automatically unless "
                    "cancelled a month before the period end."
                ),
            )

        for index, tracker in enumerate(SourceTracker.objects.all()):
            _ensure(
                tracker,
                source_url=f"{SITE}/careers/",
                notes=(
                    "Tracked from the careers page CTA; counted on the careers "
                    "dashboard alongside the other channels."
                ),
            )

        for index, keyword in enumerate(Keyword.objects.all()):
            _ensure(
                keyword,
                description=(
                    f"{keyword.name} services and support from Dovetec Enterprises. "
                    "Fixed-scope delivery with post-launch maintenance included."
                ),
            )

        for index, request_row in enumerate(FeatureRequest.objects.all()):
            _ensure(
                request_row,
                staff_notes=(
                    "Voted up by existing customers on the same plan tier. "
                    "Scheduled for triage in the next product review."
                ),
            )

        # 4. A failed upload and a failed WhatsApp send, so the error columns
        #    the dashboards read are exercised rather than always empty.
        failed_asset, _ = MediaAsset.objects.get_or_create(
            original_name="client-upload-corrupt.png",
            defaults={"kind": "image", "status": "failed", "is_public": False},
        )
        _ensure(
            failed_asset,
            mime_type="image/png", size_bytes=0, alt_text="",
            failure_reason="Upload rejected: the file is not a readable PNG.",
        )
        for note in WhatsAppNotification.objects.all():
            number = (note.recipient_phone or "").replace(" ", "")
            _ensure(note, recipient_WhatsApp=f"https://wa.me/{number.lstrip('+')}")
        sent = list(WhatsAppNotification.objects.order_by("pk")[:1])
        if sent:
            _ensure(
                sent[0], status="failed",
                error_message="Recipient's WhatsApp number is not on WhatsApp.",
            )

        # 5. Resources: the URL only means something on a resource row.
        for index, article in enumerate(Article.objects.filter(is_resource=False)[:2]):
            _ensure(
                article, is_resource=True,
                resource_url=f"{SITE}/blog-detail/{slugify(article.title)}",
            )
        for index, post in enumerate(Post.objects.filter(is_resource=False)[:1]):
            _ensure(
                post, is_resource=True,
                resource_url=f"{SITE}/community/{slugify(post.title)}",
            )

        # 6. Newsletter presentation options and the optional CTA.
        for newsletter in Newsletter.objects.all():
            _ensure(
                newsletter,
                # An example.com address, not a real inbox: seed data is
                # committed, and this column is only there to show the
                # "send to specific people" path in the admin.
                manual_recipients="editor@example.com",
                content_type="digest",
                cta_title="Read the full digest",
                subtitle="What we shipped, learned and are planning next.",
            )

        # 7. Applications are not public pages, but the column exists.
        for application in JobApplication.objects.all():
            if not application.canonical_url:
                _ensure(
                    application,
                    canonical_url=f"{SITE}/careers/{slugify(application.job.title)}/",
                )

    def _accounts(self, password, groups):
        client_group, staff_group, admin_group = groups
        made = {"admins": 0, "staff": 0, "clients": 0, "subscriptions": 0}

        def upsert(spec, group, elevate=False):
            user, created = AuthUser.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                },
            )
            if elevate:
                # Only a superuser can reach /admin/ and the role signal reads
                # is_superuser to decide group membership.
                if not (user.is_superuser and user.is_staff):
                    user.is_superuser = True
                    user.is_staff = True
                    user.set_password(password)
                    user.save(update_fields=["is_superuser", "is_staff", "password"])
            elif created:
                user.set_password(password)
                user.save()
            # A realistic last_login makes the admin's "active users" panel
            # show something, and every seeded account is a real sign-in.
            if user.last_login is None:
                user.last_login = _ago(1 + len(user.email) % 6, hours=len(user.email) % 12)
                user.save(update_fields=["last_login"])
            profile = getattr(user, "profile", None)
            if profile is not None:
                profile.is_verified = True
                profile.title = spec.get("title") or ""
                profile.bio = spec.get("bio") or ""
                profile.save()
            # sync_user_primary_role_group runs on save; assign explicitly too.
            user.groups.set([group])
            return user, created

        for spec in ADMINS:
            _, created = upsert(spec, admin_group, elevate=True)
            made["admins"] += 1 if created else 0

        staff_spec = dict(STAFF)
        _, created = upsert(staff_spec, staff_group, elevate=True)
        if created:
            # A staff account needs /admin/ access but not superuser rights.
            user = AuthUser.objects.get(email=STAFF["email"])
            user.is_superuser = False
            user.save(update_fields=["is_superuser"])
            user.groups.set([staff_group])
        made["staff"] += 1 if created else 0

        for index, (email, first, last, title) in enumerate(CLIENTS):
            spec = {"email": email, "first_name": first, "last_name": last,
                    "title": title, "bio": "", "password": password}
            user, created = upsert(spec, client_group)
            made["clients"] += 1 if created else 0
            sub, sub_created = NewsletterSubscription.objects.get_or_create(
                email=email,
                defaults={
                    "is_verified": True,
                    # Subscribers are portal users, so the preference centre
                    # can be shown inside the client portal as well as by link.
                    "user": user,
                    "verified_at": _ago(80 - index * 4),
                },
            )
            if not sub.is_verified or sub.unsubscribed_at or sub.user_id != user.pk:
                sub.is_verified = True
                sub.unsubscribed_at = None
                sub.user = user
                sub.verified_at = sub.verified_at or _ago(80)
                sub.save(update_fields=["is_verified", "unsubscribed_at", "user", "verified_at"])
            made["subscriptions"] += 1 if sub_created else 0

        # One deliberately unsubscribed contact, so opt-out handling is visible.
        NewsletterSubscription.objects.get_or_create(
            email="former.subscriber@example.com",
            defaults={
                "is_verified": True,
                "unsubscribed_at": _ago(30),
                "verified_at": _ago(120),
            },
        )
        return made

    # ── Taxonomy ───────────────────────────────────────────────────────
    def _taxonomy(self):
        made = {"tags": 0, "capabilities": 0, "community_categories": 0, "keywords": 0}
        tags = {}
        for name in S.TAGS:
            tag, created = Tag.objects.get_or_create(
                name=name, defaults={"slug": slugify(name), "published_at": _ago(120)}
            )
            if not tag.published_at:
                _published(tag, 120)
            tags[name] = tag
            made["tags"] += 1 if created else 0

        capabilities = {}
        for name, description in S.CAPABILITIES.items():
            category, created = ShopCategory.objects.get_or_create(
                name=name, defaults={"description": description, "published_at": _ago(120)}
            )
            if not category.published_at:
                _published(category, 120)
            capabilities[name] = category
            made["capabilities"] += 1 if created else 0

        communities = {}
        for name, description in S.COMMUNITY_CATEGORIES:
            category, created = CommunityCategory.objects.get_or_create(
                name=name, defaults={"description": description, "published_at": _ago(120)}
            )
            if not category.published_at:
                _published(category, 120)
            communities[name] = category
            made["community_categories"] += 1 if created else 0

        keywords = {}
        for name in ("Django", "Python", "PostgreSQL", "Kubernetes", "M-Pesa",
                     "TypeScript", "Flutter", "Android", "FHIR", "USSD"):
            keyword, created = Keyword.objects.get_or_create(
                name=name, defaults={"published_at": _ago(120)}
            )
            if not keyword.published_at:
                _published(keyword, 120)
            keywords[name] = keyword
            made["keywords"] += 1 if created else 0

        return {
            "tags": tags,
            "capabilities": capabilities,
            "communities": communities,
            "keywords": keywords,
            "made": made,
        }

    # ── Editorial content ──────────────────────────────────────────────
    def _content(self, tax, make_images):
        authors = {
            u.first_name: u
            for u in AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS])
        }
        made = {"articles": 0, "resources": 0, "comments": 0, "replies": 0,
                "likes": 0, "dislikes": 0}

        # A real editorial board is never 100% published, and the dashboard's
        # content-workflow chart only reads as a chart when the statuses
        # differ. Older rows are more likely to be archived; the tail of the
        # list is still in draft.
        ARTICLE_STATUS_CYCLE = [
            "published", "published", "published", "archived", "published",
            "scheduled", "published", "draft", "archived", "published",
            "draft", "published", "scheduled", "published", "published",
        ]
        # Shared across every group, because each group numbers its own rows
        # from zero and a per-group cycle makes all the groups look alike.
        article_sequence = []

        def publish(spec, is_resource, index):
            author_user = authors.get(spec.get("author", "")) or next(iter(authors.values()), None)
            kind = "resource" if is_resource else "article"
            title = spec["title"]
            article_sequence.append(index)
            status = ARTICLE_STATUS_CYCLE[
                len(article_sequence) % len(ARTICLE_STATUS_CYCLE)
            ]
            # Backdate by index so /blog/ has a believable publication order.
            published_at = _ago(90 - index * 7, hours=index)
            article, created = Article.objects.get_or_create(
                title=title,
                defaults={
                    "content": spec["content"],
                    "status": status,
                    "published_at": published_at,
                    "featured": spec.get("featured", False),
                    "is_resource": is_resource,
                    "resource_type": spec["resource_type"],
                    "user": author_user,
                    "author": getattr(author_user, "profile", None),
                    "views": 120 + (len(title) * 7),
                    "category": spec["tag"],
                    # SEO block: the template falls back to title/content, but
                    # a live article carries an explicit description and canonical.
                    "seo_description": spec["excerpt"],
                    "meta_title": f"{title} | Dovetec Enterprises",
                    "meta_description": spec["excerpt"],
                    "og_title": title,
                    "og_description": spec["excerpt"],
                    "twitter_card": "summary_large_image",
                    "twitter_title": title,
                    "twitter_description": spec["excerpt"],
                    "canonical_url": (
                        "https://dovetecenterprises.vercel.app/blog-detail/" + slugify(title)
                    ),
                },
            )
            if created:
                # kind is "article"/"resource" (singular) to match the section
                # names; pluralise for the counter keys.
                made[f"{kind}s"] += 1
            # A draft or scheduled row has no publication date yet; an
            # archived one keeps the date it originally went out on.
            _ensure(
                article,
                status=status,
                published_at=published_at if status in ("published", "archived") else None,
                category=spec["tag"],
                seo_description=spec["excerpt"],
                meta_title=f"{title} | Dovetec Enterprises",
                meta_description=spec["excerpt"],
                og_title=title,
                og_description=spec["excerpt"],
                twitter_card="summary_large_image",
                twitter_title=title,
                twitter_description=spec["excerpt"],
                canonical_url=(
                    "https://dovetecenterprises.vercel.app/blog-detail/" + slugify(title)
                ),
            )
            article.tags.add(tax["tags"][spec["tag"]])
            if make_images and not article.image:
                article.image.save(
                    f"{article.slug}.png", _png((32, 99, 155)), save=True
                )
            return article

        articles = [publish(spec, False, i) for i, spec in enumerate(S.ARTICLES)]
        resources = [publish(spec, True, i) for i, spec in enumerate(S.RESOURCES)]

        # Engagement from the client accounts, so blog KPIs are not all zero.
        clients = list(AuthUser.objects.filter(
            email__in=[c[0] for c in CLIENTS]
        ))[: len(articles)]
        for index, article in enumerate(articles):
            for offset, user in enumerate(clients):
                if (index + offset) % len(clients) == 0:
                    # Comment.hashed_id is unique per (article, user).
                    Comment.objects.get_or_create(
                        article=article, user=user,
                        defaults={"content": "Clear write-up, and the failure-mode section is the part "
                                             "most teams skip. We adopted the expand/migrate/contract "
                                             "approach on our own schema as a result."},
                    )
            if clients:
                Like.objects.get_or_create(user=clients[index % len(clients)], article=article)
        made["comments"] = Comment.objects.count()
        made["likes"] = Like.objects.count()

        # A few negative signals, so the dislike KPI and moderation path have data.
        for index, article in enumerate(articles[:3]):
            if not clients:
                break
            user = clients[(index + 2) % len(clients)]
            _, created = Dislike.objects.get_or_create(user=user, article=article)
            made["dislikes"] += 1 if created else 0

        if clients and articles:
            first = articles[0]
            comment = Comment.objects.filter(article=first, user=clients[0]).first()
            if comment:
                _, created = Reply.objects.get_or_create(
                    comment=comment, user=clients[1 % len(clients)],
                    defaults={"content": "Agreed. We also underinvested in reconciliation tooling "
                                         "and paid for it during the first month of parallel running."},
                )
                made["replies"] += 1 if created else 0
            Report.objects.get_or_create(
                article=first, user=clients[0],
                defaults={"reason": "Duplicate of an earlier post on offline sync."},
            )

        self._feedback(articles)
        return {"articles": articles, "resources": resources, "made": made}

    # ── Case studies ──────────────────────────────────────────────────
    def _case_studies(self, tax, make_images):
        """Publish one case study per flagship engagement, per industry."""
        made = {"case_studies": 0}
        for spec in S.CASE_STUDIES:
            industry = S.INDUSTRIES[spec["industry"]]
            case_study, created = CaseStudy.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "slug": slugify(spec["name"]),
                    "description": spec["description"],
                    "category": tax["capabilities"].get(spec["category"]),
                    "status": CaseStudy.STATUS_PUBLISHED,
                    "tagline": spec["tagline"],
                    "overview": spec["overview"],
                    "featured": spec.get("featured", False),
                    "accent_color": "#0071e3",
                    "problem_statement": spec.get("problem_statement", ""),
                    "objectives": spec.get("objectives", ""),
                    "business_challenge": spec.get("business_challenge", ""),
                    "research_findings": spec.get("research_findings", ""),
                    "user_needs": spec.get("user_needs", ""),
                    "features": spec.get("features", ""),
                    "user_challenges": spec.get("user_challenges", ""),
                    "competitor_data": spec.get("competitor_data", ""),
                    "unique_features": spec.get("unique_features", ""),
                    "root_cause": spec.get("root_cause", ""),
                    "task_flows": spec.get("task_flows", ""),
                },
            )
            if created:
                made["case_studies"] += 1
            if make_images and not case_study.hero_image:
                case_study.hero_image.save(
                    f"{case_study.slug}-hero.png", _png((20, 90, 140)), save=True
                )
        return made

    def _feedback(self, articles):
        samples = [
            ("Peter Kariuki", "peter.kariuki@rift-solar.co.ke",
             "The readiness report is the most useful artefact you have published. "
             "We used the maturity bands to justify an observability budget internally."),
            ("Esther Wanjiku", "esther.wanjiku@jamiihealth.or.ke",
             "Requested a follow-up on the offline synchronisation design, specifically the "
             "conflict resolution approach for clinical records."),
            ("Linda Mwangi", "linda.mwangi@oddibites.co.ke",
             "The cost checklist found about a fifth of our monthly spend in the first pass. "
             "Thank you for publishing it rather than selling it as a service."),
        ]
        for name, email, message in samples:
            Feedback.objects.get_or_create(
                name=name, email=email, defaults={"message": message}
            )

    # ── CRM ────────────────────────────────────────────────────────────
    def _crm(self, accounts):
        made = {"organizations": 0, "contacts": 0, "inquiries": 0, "tickets": 0,
                "projects": 0, "tickets_activities": 0}
        staff = AuthUser.objects.filter(email__in=[
            a["email"] for a in ADMINS
        ] + [STAFF["email"]])

        orgs = {}
        for name, industry, website in ORGANIZATIONS:
            org, created = Organization.objects.get_or_create(
                name=name,
                defaults={"website": website, "industry": industry,
                          "phone": "+254 700 000 000",
                          "address": f"{name} offices, Nairobi, Kenya"},
            )
            orgs[name] = org
            made["organizations"] += 1 if created else 0

        contacts = {}
        portal_users = {
            u.email: u for u in AuthUser.objects.filter(email__in=[c[0] for c in CLIENTS])
        }
        for email, first, last, title in CLIENTS:
            contact, created = Contact.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first, "last_name": last, "job_title": title,
                    "phone": "+254 712 000 000",
                },
            )
            # Data migration 0016 pre-creates these contacts, so get_or_create
            # returns created=False and the defaults above never land. Backfill
            # the links explicitly or they stay null on an existing database.
            updates = []
            portal_user = portal_users.get(email)
            if portal_user is not None and contact.portal_user_id != portal_user.pk:
                contact.portal_user = portal_user
                updates.append("portal_user")
            org = orgs.get(CLIENT_ORGANIZATION_BY_EMAIL.get(email, ""))
            if org is not None and contact.organization_id != org.pk:
                contact.organization = org
                updates.append("organization")
            if updates:
                contact.save(update_fields=updates)
            contacts[email] = contact
            made["contacts"] += 1 if created else 0

        # Inquiries drive the sales funnel. ServiceInquiry has no subject
        # field, so the enquiry topic leads the message and name is the
        # contact's full name.
        inquiries = []
        for index, (topic, desc, email) in enumerate([
            ("Field lending platform for our members",
             "We are a SACCO union with members across several counties and need loan origination "
             "to work where connectivity is poor. Could you scope this?",
             "james.otieno@harambeesacco.co.ke"),
            ("Learning platform and fee collection",
             "We want to consolidate course delivery and fee collection for our secondary schools. "
             "What would an implementation look like across 14 schools?",
             "grace.njeri@techdarasa.ac.ke"),
            ("Multi-branch stock visibility",
             "Our stores cannot see group-level stock until the nightly count. We need live visibility.",
             "linda.mwangi@oddibites.co.ke"),
            ("Patient records across 38 facilities",
             "We need a records system that stays available when the network does not. "
             "What is your approach to synchronisation?",
             "esther.wanjiku@jamiihealth.or.ke"),
            ("Fleet visibility and dispatch",
             "We would like consignment tracking and exception alerting along our main corridors.",
             "daniel.kimani@savannahfreight.com"),
            ("Security posture review",
             "A client has asked for an ISO 27001 readiness assessment before we bid. Can you deliver it?",
             "peter.kariuki@rift-solar.co.ke"),
            ("Integrating the county revenue collector",
             "We pay out to agents twice a day and the reconciliation is manual. "
             "Can this be integrated with the county collector?",
             "james.otieno@harambeesacco.co.ke"),
            ("Replace the paper warehouse picking lists",
             "Our pickers still work from printed lists and mis-pick on the third shift.",
             "linda.mwangi@oddibites.co.ke"),
            ("Bulk results entry for the term",
             "Clerks enter results for 1,400 candidates by hand. We need a bulk "
             "import with validation before moderation.",
             "grace.njeri@techdarasa.ac.ke"),
            ("Consolidate three clinic systems",
             "We acquired two smaller providers and now run three systems that "
             "do not share patient identifiers.",
             "esther.wanjiku@jamiihealth.or.ke"),
        ]):
            service = ["software", "it", "consulting"][index % 3]
            # Weighted rather than one-per-stage: a real funnel decays, and a
            # perfectly flat pipeline makes the dashboard chart unreadable.
            stage = ["new", "new", "new", "contacted", "contacted",
                     "qualified", "proposal", "negotiation", "won", "won"][index]
            contact = contacts[email]
            # Won enquiries are published to the case-study pipeline; earlier
            # stages stay unpublished until the work is signed off.
            is_won = stage == "won"
            inquiry, created = ServiceInquiry.objects.get_or_create(
                name=f"{contact.first_name} {contact.last_name}",
                email=email,
                message=f"{topic}. {desc}",
                defaults={
                    "service": service,
                    "industry": self._industry_for(email),
                    "source": "service_page",
                    "stage": stage,
                    "budget_range": ["under_50k", "50k_250k", "250k_1m", "over_1m"][index % 4],
                    "estimated_value": [0, 750000, 2500000, 5000000][index % 4],
                    "timeline": ["immediately", "1-3 months", "3-6 months"][index % 3],
                    "contact": contact,
                    "assigned_to": staff[index % staff.count()] if staff.count() else None,
                    "published_at": _ago(75 - index * 6) if is_won else None,
                    "notes": (
                        "Discovery questionnaire sent and answered. The client is "
                        "ready for a scoping workshop before a fixed-price proposal."
                        if is_won else
                        "Awaiting a response from the client. Follow up scheduled "
                        "for the end of the week."
                    ),
                    "converted_at": _ago(70 - index * 6) if is_won else None,
                },
            )
            inquiries.append(inquiry)
            made["inquiries"] += 1 if created else 0
            _ensure(
                inquiry,
                published_at=_ago(75 - index * 6) if is_won else None,
                notes=(
                    "Discovery questionnaire sent and answered. The client is "
                    "ready for a scoping workshop before a fixed-price proposal."
                    if is_won else
                    "Awaiting a response from the client. Follow up scheduled "
                    "for the end of the week."
                ),
                converted_at=_ago(70 - index * 6) if is_won else None,
            )

        staff_list = list(staff)
        assignees = {i: staff_list[i % len(staff_list)] for i in range(len(TICKETS))} \
            if staff_list else {}
        for index, (subject, ttype, status, priority, service, desc, email) in enumerate(TICKETS):
            contact = contacts.get(email)
            org = contact.organization if contact else None
            assignee = assignees.get(index)
            closed = status in ("resolved", "closed")
            escalated = priority == "urgent"
            ticket, created = Ticket.objects.get_or_create(
                subject=subject,
                defaults={
                    "description": desc,
                    "type": ttype,
                    "status": status,
                    "priority": priority,
                    "service": service,
                },
            )
            if created:
                made["tickets"] += 1
            _ensure(
                ticket,
                source="client_portal",
                industry=self._industry_for(email) if email else "other",
                contact=contact,
                organization=org,
                assigned_to=assignee,
                # Closed tickets carry a resolver; referrals carry a referrer.
                created_by=assignee,
                referred_to=(
                    staff_list[(index + 1) % len(staff_list)]
                    if escalated and staff_list else None
                ),
                inquiry=next(
                    (i for i in inquiries if i.contact_id == getattr(contact, "pk", None)),
                    None,
                ),
                resolved_at=_ago(6 - index % 5) if closed else None,
                escalated_at=_ago(9) if escalated else None,
            )
            activity_plan = [
                ("created", "Ticket created from the client portal."),
                ("assigned", "Assigned to the support queue."),
                ("note", "Initial triage completed; reproducing on staging."),
            ]
            if closed:
                activity_plan.append(("resolved", "Fix verified in production by the client."))
            if escalated:
                activity_plan.append(("escalated", "Escalated to engineering lead."))
            for action, content in activity_plan[: {
                "new": 1, "open": 2, "waiting": 3, "resolved": 4, "closed": 4
            }[status]]:
                activity, activity_created = TicketActivity.objects.get_or_create(
                    ticket=ticket, action=action, content=content,
                )
                made["tickets_activities"] += 1 if activity_created else 0
                # user authored it; from/to carry the handoff. Written for
                # existing rows too, since 0016 pre-creates activities.
                _ensure(
                    activity,
                    user=assignee,
                    from_user=assignee if action in ("assigned", "escalated") else None,
                    to_user=(
                        ticket.referred_to if action == "escalated"
                        else assignee if action == "assigned" else None
                    ),
                )

        # Project has no industry field; pair each project with the inquiry
        # that originated it. converted_from_inquiry is deliberately left
        # unset: completing a project that carries one fires a signal which
        # builds a questionnaire and sends notifications.
        for index, (name, status, priority, service, industry, desc, budget) in enumerate(PROJECTS):
            organization = orgs.get(next(
                (oname for oname, ind, _ in ORGANIZATIONS if ind == industry), ""
            ))
            started = timezone.now().date() - timezone.timedelta(days=120 - index * 9)
            project, created = Project.objects.get_or_create(
                name=name,
                defaults={
                    "description": desc,
                    "status": status,
                    "stage": status,
                    "priority": priority,
                    "service": service,
                    "source": "website",
                    "estimated_budget": budget,
                    "organization": organization,
                    "contact": next(
                        (c for c in contacts.values()
                         if organization and c.organization_id == organization.pk),
                        None,
                    ),
                    "start_date": started,
                    "target_end_date": started + timezone.timedelta(days=150),
                    "actual_end_date": (
                        started + timezone.timedelta(days=150) if status == "completed" else None
                    ),
                    "actual_budget": budget if status == "completed" else None,
                    "deliverables": (
                        "Event-driven order core, public catalogue API, offline order "
                        "capture, daily reconciliation dashboard, runbooks and a "
                        "recorded handover with the client's engineering team."
                    ),
                    "published_at": _ago(60 - index * 8),
                    "client_feedback": (
                        "Delivered on scope with the reconciliation tooling the team "
                        "asked for during the first month of parallel running."
                        if status == "completed" else ""
                    ),
                },
            )
            if created:
                made["projects"] += 1
            _ensure(
                project,
                source="website",
                contact=next(
                    (c for c in contacts.values()
                     if organization and c.organization_id == organization.pk),
                    None,
                ),
                start_date=started,
                target_end_date=started + timezone.timedelta(days=150),
                actual_end_date=(
                    started + timezone.timedelta(days=150) if status == "completed" else None
                ),
                actual_budget=budget if status == "completed" else None,
                deliverables=(
                    "Event-driven order core, public catalogue API, offline order "
                    "capture, daily reconciliation dashboard, runbooks and a "
                    "recorded handover with the client's engineering team."
                ),
                published_at=_ago(60 - index * 8),
            )
            if created:
                inquiry = next(
                    (i for i in inquiries
                     if i.industry == industry and i.stage in ("won", "negotiation", "proposal")),
                    None,
                )
                if inquiry is not None:
                    project.converted_from_inquiry = inquiry
                    project.save(update_fields=["converted_from_inquiry"])

        # Subscriptions are reported by _accounts, which owns the creation
        # count; repeating the total here would read as a creation count.
        return {
            "made": made,
            "organizations": orgs,
            "contacts": contacts,
            "inquiries": inquiries,
        }

    @staticmethod
    def _industry_for(email):
        """Map a client email address to its industry slug.

        Keyed on the distinctive part of each client domain, since domains
        here are not always the organisation name (savannahfreight.com,
        rift-solar.co.ke, jamiihealth.or.ke).
        """
        domain = email.split("@")[-1].lower()
        for key, industry in CLIENT_INDUSTRY_BY_DOMAIN.items():
            if key in domain:
                return industry
        return "other"

    # ── Shop ───────────────────────────────────────────────────────────
    def _catalog(self, tax, make_images):
        made = {"products": 0, "orders": 0, "order_items": 0, "payments": 0,
                "carts": 0, "cart_items": 0}
        for index, (name, spec) in enumerate(S.PRODUCTS.items()):
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "price": spec["price"],
                    "stock": spec["stock"],
                    "category": tax["capabilities"][spec["category"]],
                    "description": spec["description"],
                    "published_at": _ago(100 - index * 5),
                },
            )
            if not product.published_at:
                _published(product, 100 - index * 5)
            if created:
                made["products"] += 1
                product.keywords.add(*[
                    tax["keywords"][k] for k in
                    ("Django", "Python", "PostgreSQL") if k in tax["keywords"]
                ])
                if make_images:
                    product.image.save(f"{product.pk}.png", _png((200, 60, 40)), save=True)

        products = list(Product.objects.filter(name__in=S.PRODUCTS))
        for index, product in enumerate(products):
            order_status = ["pending", "paid", "shipped", "delivered", "cancelled"][index % 5]
            order, created = Order.objects.get_or_create(
                customer_name=f"Order {index + 1:03d}",
                customer_email=f"buyer{index + 1}@example.com",
                defaults={
                    "status": order_status,
                    "customer_phone": "+254 700 000 000",
                    "address": f"{index + 1} Riverside Drive, Nairobi",
                    "city": "Nairobi",
                },
            )
            if created:
                made["orders"] += 1
                item = OrderItem.objects.create(
                    order=order, product=product, quantity=1 + index % 3,
                    price_at_purchase=product.price,
                )
                made["order_items"] += 1
                order.update_total()
                Payment.objects.get_or_create(
                    order=order,
                    transaction_id=f"SEED-TXN-{index + 1:04d}",
                    defaults={
                        "amount": item.price_at_purchase * item.quantity,
                        "payment_method": ["Mpesa", "PayPal", "CreditCard"][index % 3],
                        "is_successful": order_status in ("paid", "shipped", "delivered"),
                    },
                )
                made["payments"] += 1

        # Abandoned carts, so the shop dashboard's cart metrics and the
        # cart/cart_item tables are populated rather than empty.
        carts = [
            ("seed-cart-session-0001", [0, 2]),
            ("seed-cart-session-0002", [1]),
            ("seed-cart-session-0003", [3, 4]),
        ]
        for session_key, product_indexes in carts:
            cart, created = Cart.objects.get_or_create(session_key=session_key)
            made["carts"] += 1 if created else 0
            for position, product_index in enumerate(product_indexes):
                if product_index >= len(products):
                    continue
                _, item_created = CartItem.objects.get_or_create(
                    cart=cart, product=products[product_index],
                    defaults={"quantity": 1 + position},
                )
                made["cart_items"] += 1 if item_created else 0
        return made

    # ── Community ──────────────────────────────────────────────────────
    def _community(self, accounts, tax, make_images):
        made = {"topics": 0, "posts": 0, "comments": 0, "replies": 0,
                "dislikes": 0, "events": 0}
        authors = {u.first_name: u for u in AuthUser.objects.filter(
            email__in=[a["email"] for a in ADMINS]
        )}
        moderators = [u for u in authors.values()]

        topics = {}
        for index, spec in enumerate(S.TOPICS):
            topic, created = Topic.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "slug": slugify(spec["name"]),
                    "category": tax["communities"][spec["category"]],
                    "description": spec["description"],
                    "published_at": _ago(70 - index * 6),
                },
            )
            if not topic.published_at:
                _published(topic, 70 - index * 6)
            topics[spec["name"]] = topic
            made["topics"] += 1 if created else 0

        for index, spec in enumerate(S.POSTS):
            author = authors.get(spec["author"].split()[0])
            title = spec["title"]
            summary = spec["content"][:180].rsplit(" ", 1)[0] + "."
            post, created = Post.objects.get_or_create(
                title=title,
                defaults={
                    "content": spec["content"],
                    "topic": topics[spec["topic"]],
                    "category": spec["topic"],
                    "status": "published",
                    "published_at": _ago(45 - index * 5),
                    "moderation_state": "approved",
                    "user": author,
                    "author": author.profile if author else None,
                    "views": 80 + len(spec["content"]),
                    "seo_description": summary,
                    "meta_title": f"{title} | Dovetec Community",
                    "meta_description": summary,
                    "og_title": title,
                    "og_description": summary,
                    "twitter_card": "summary_large_image",
                    "twitter_title": title,
                    "twitter_description": summary,
                    "canonical_url": (
                        "https://dovetecenterprises.vercel.app/community/post/"
                        + slugify(title)
                    ),
                },
            )
            if created:
                made["posts"] += 1
            _ensure(
                post,
                topic=topics[spec["topic"]],
                category=spec["topic"],
                seo_description=summary,
                meta_title=f"{title} | Dovetec Community",
                meta_description=summary,
                og_title=title,
                og_description=summary,
                twitter_card="summary_large_image",
                twitter_title=title,
                twitter_description=summary,
                canonical_url=(
                    "https://dovetecenterprises.vercel.app/community/post/" + slugify(title)
                ),
                published_at=_ago(45 - index * 5),
            )

        client_users = list(AuthUser.objects.filter(email__in=[c[0] for c in CLIENTS]))
        posts = list(Post.objects.all())
        for index, post in enumerate(posts):
            if not client_users:
                break
            user = client_users[index % len(client_users)]
            comment, created = community_comment(post, user)
            made["comments"] += 1 if created else 0

            # Replies hang off the comment, not the post, so the thread view
            # and the reply counters both have data.
            if index % 2 == 0 and client_users:
                replier = client_users[(index + 1) % len(client_users)]
                reply, reply_created = CommunityReply.objects.get_or_create(
                    comment=comment, user=replier,
                    defaults={
                        "content": "Worth adding that we tried the opposite here and "
                                   "reversed it. The simpler version survived contact "
                                   "with real data far longer.",
                        "moderation_state": "approved",
                    },
                )
                made["replies"] += 1 if reply_created else 0

        # A moderation spread: one flagged comment awaiting a decision and one
        # already-approved flag, so both dashboard queues have rows. Only rows
        # that were actually flagged carry the flag_* fields.
        flagged_index = 0
        for index, post in enumerate(posts):
            if index >= 3 or not client_users:
                break
            comment = CommunityComment.objects.filter(article=post).first()
            if comment is None:
                continue
            moderator = moderators[flagged_index % len(moderators)] if moderators else None
            reporter = client_users[(index + 1) % len(client_users)]
            if flagged_index == 0:
                CommunityComment.objects.filter(pk=comment.pk).update(
                    moderation_state="flagged",
                    flag_reason="Contains an unverified pricing claim from a competitor.",
                    flagged_by=reporter,
                    flagged_at=_ago(3),
                )
            else:
                CommunityComment.objects.filter(pk=comment.pk).update(
                    flag_reason="Off-topic for this thread.",
                    flagged_by=reporter,
                    flagged_at=_ago(9),
                    moderator_decision="Kept visible; off-topic but constructive.",
                    moderated_by=moderator,
                    moderated_at=_ago(8),
                )
            flagged_index += 1
        made["flagged_comments"] = CommunityComment.objects.filter(
            moderation_state="flagged"
        ).count()

        # A moderation spread across posts, comments and replies so every
        # dashboard moderation queue has rows. Only rows that were actually
        # flagged carry flag_* fields, and only rows a moderator has ruled on
        # carry moderator_* fields.
        discussion_topics = list(DiscussionTopic.objects.all())
        for index, post in enumerate(posts):
            if index >= 3 or not client_users:
                break
            moderator = moderators[index % len(moderators)] if moderators else None
            reporter = client_users[(index + 1) % len(client_users)]
            if index == 0:
                # Awaiting a moderator decision.
                Post.objects.filter(pk=post.pk).update(
                    moderation_state="flagged",
                    flag_reason="Contains a client name we have no consent to publish.",
                    flagged_by=reporter,
                    flagged_at=_ago(4),
                )
            else:
                # Flagged, reviewed, and left visible.
                Post.objects.filter(pk=post.pk).update(
                    flag_reason="Off-topic for this topic.",
                    flagged_by=reporter,
                    flagged_at=_ago(11),
                    moderator_decision="Kept visible; off-topic but constructive.",
                    moderated_by=moderator,
                    moderated_at=_ago(10),
                )
            # Posts that open a discussion point carry the thread.
            if index < len(discussion_topics) and post.discussion_topic_id is None:
                Post.objects.filter(pk=post.pk).update(
                    discussion_topic=discussion_topics[index]
                )
        made["flagged_posts"] = Post.objects.filter(moderation_state="flagged").count()

        replies = list(CommunityReply.objects.all())
        for index, reply in enumerate(replies):
            if not client_users:
                break
            reporter = client_users[(index + 2) % len(client_users)]
            CommunityReply.objects.filter(pk=reply.pk).update(
                flag_reason="Contains a link to an unvetted third-party service.",
                flagged_by=reporter,
                flagged_at=_ago(2),
                moderator_decision=(
                    "Link removed, reply kept." if index == 0 else
                    "Kept visible after review; link resolves to our documentation."
                ),
                moderated_by=moderators[index % len(moderators)] if moderators else None,
                moderated_at=_ago(1),
            )
        made["flagged_replies"] = replies[0].pk if replies else 0

        for index, post in enumerate(posts[:2]):
            if not client_users:
                break
            _, created = CommunityDislike.objects.get_or_create(
                user=client_users[(index + 3) % len(client_users)], article=post
            )
            made["dislikes"] += 1 if created else 0

        now = timezone.now()
        for index, (title, event_type, days) in enumerate([
            ("Designing for intermittent connectivity", "webinar", 14),
            ("Django performance clinic", "workshop", 21),
            ("Kenya Python community meetup", "meetup", 7),
            ("Fintech architecture conference", "conference", 45),
        ]):
            event, created = Event.objects.get_or_create(
                title=title,
                defaults={
                    "description": f"A {event_type} on {title.lower()} hosted by Dovetec Enterprises.",
                    "starts_at": now + timezone.timedelta(days=days),
                    "ends_at": now + timezone.timedelta(days=days, hours=3),
                    "event_type": event_type,
                    "location": "Nairobi, Kenya" if event_type != "webinar" else "Online",
                    "is_online": event_type == "webinar",
                    "registration_url": "https://dovetecenterprises.vercel.app/contact-us/",
                },
            )
            _ensure(event, published_at=_ago(30 - index * 4))
            made["events"] += 1 if created else 0

        return made

    # ── Talent ─────────────────────────────────────────────────────────
    def _talent(self):
        made = {"departments": 0, "jobs": 0, "applications": 0, "sources": 0,
                "interviews": 0, "application_notes": 0}
        admins = list(AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS]))
        staff = AuthUser.objects.filter(email=STAFF["email"]).first()

        # Each department is owned by a different admin, so the org chart
        # on /careers/ and the department manager field both have data.
        manager_for = {
            name: admins[index % len(admins)] if admins else None
            for index, (name, _blurb) in enumerate(DEPARTMENTS)
        }
        departments = {}
        for name, description in DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                name=name,
                defaults={
                    "description": description,
                    "headcount": 4,
                    "location": "Nairobi, Kenya",
                    "manager": manager_for.get(name),
                    "published_at": _ago(150),
                },
            )
            _ensure(dept, manager=manager_for.get(name), location="Nairobi, Kenya",
                    published_at=_ago(150))
            departments[name] = dept
            made["departments"] += 1 if created else 0

        for index, (title, dept, location, level, salary, description) in enumerate(JOBS):
            job, created = Job.objects.get_or_create(
                title=title,
                defaults={
                    "description": description,
                    "location": location,
                    "company": "Dovetec Enterprises",
                    "salary": salary,
                    "level": level,
                    "department": departments[dept],
                    "employment_type": "Full-time",
                    "published_at": _ago(40 - index * 5),
                },
            )
            if created:
                made["jobs"] += 1
            _ensure(job, published_at=_ago(40 - index * 5))

        source_rows = [
            ("LinkedIn", "social_media", 0),
            ("Job board", "job_board", 15000),
            ("Referral", "referral", 0),
            ("Company website", "company_website", 3000),
        ]
        for source, stype, cost in source_rows:
            tracker, created = SourceTracker.objects.get_or_create(
                source_name=source,
                defaults={"source_type": stype, "cost_per_hire": cost or None},
            )
            if created:
                made["sources"] += 1
            _ensure(tracker, cost_per_hire=cost or None)

        jobs = list(Job.objects.all())
        applicants = [
            ("Wanjiru Kamau", "wanjiru.kamau@example.com", "shortlisted", "high", "referral"),
            ("Brian Mutiso", "brian.mutiso@example.com", "interview_scheduled", "medium", "linkedin"),
            ("Faith Chebet", "faith.chebet@example.com", "new", "medium", "job_portal"),
            ("Kevin Otieno", "kevin.otieno@example.com", "assessment", "high", "social_media"),
            ("Mercy Achieng", "mercy.achieng@example.com", "offer", "urgent", "referral"),
            ("Samuel Kiprono", "samuel.kiprono@example.com", "rejected", "low", "indeed"),
        ]
        reviewer = admins[1] if len(admins) > 1 else (admins[0] if admins else None)
        recruiter = staff
        for index, (name, email, status, priority, source) in enumerate(applicants):
            if index >= len(jobs):
                break
            job = jobs[index]
            interview_spec = S.INTERVIEWS.get(name)
            advanced = status not in ("new",)
            rejected = status == "rejected"
            applied_at = _ago(28 - index * 4)
            # Interview dates are stored as a past offset; negative values in
            # INTERVIEWS mean the interview already happened.
            interview_date = (
                _ago(-interview_spec["scheduled_in_days"]) if interview_spec else None
            )
            application, created = JobApplication.objects.get_or_create(
                job=job, candidate_name=name, candidate_email=email,
                defaults={"status": status, "priority": priority, "source": source},
            )
            if created:
                made["applications"] += 1
            _ensure(
                application,
                status=status,
                priority=priority,
                source=source,
                source_detail=f"Applied for the {job.title} posting on the careers page.",
                meta_title=f"{name} — {job.title} | Dovetec Enterprises",
                meta_description=(
                    f"Application from {name} for the {job.title} role at Dovetec "
                    f"Enterprises."
                ),
                og_title=f"{name} — {job.title}",
                og_description=f"Application from {name} for the {job.title} role.",
                twitter_card="summary",
                twitter_title=f"{name} — {job.title}",
                twitter_description=f"Application from {name} for the {job.title} role.",
                published_at=applied_at,
                department=job.department,
                candidate_phone=f"+254 733 {100 + index:03d} {200 + index:03d}",
                candidate_linkedin=f"https://www.linkedin.com/in/{name.split()[0].lower()}",
                cover_letter=(
                    f"I am applying for the {job.title} role. My background is closest "
                    f"to the {job.department.name if job.department else 'engineering'} work "
                    f"you describe, and I would rather solve a real problem in your domain "
                    f"than repeat a project I have already shipped."
                ),
                rating={"new": None, "assessment": 3, "shortlisted": 4,
                        "interview_scheduled": 4, "offer": 5}.get(status),
                notes=(
                    f"Stage: {status.replace('_', ' ')}. Reviewed by the delivery lead "
                    f"and discussed in the weekly pipeline meeting."
                ),
                assigned_to=recruiter,
                reviewed_by=reviewer,
                applied_at=applied_at,
                status_changed_at=_ago(20 - index * 4),
                started_at=_ago(18 - index * 4) if advanced else None,
                interview_date=interview_date,
                interview_location=(
                    interview_spec["location"] if interview_spec else "Not scheduled"
                ),
                offer_amount=310000.0 if status in ("offer", "hired") else None,
                offer_date=_ago(6) if status in ("offer", "hired") else None,
                offer_conditions=(
                    "Two-week notice period, completed background check, and "
                    "confidentiality and IP assignment as per the engagement letter."
                    if status in ("offer", "hired") else None
                ),
                rejection_reason=(
                    "Strong application, but we moved to an internal candidate for "
                    "this specific role. Kept on file for future openings."
                    if rejected else None
                ),
                # employee_type is NOT NULL: applicants have not agreed terms
                # yet, so a candidate stages it as "Prospective".
                employee_type="Full-time" if status in ("offer", "hired") else "Prospective",
            )
            for note_index, (action, author_name, content) in enumerate(
                S.APPLICATION_NOTES.get(name, [])
            ):
                author = next(
                    (a for a in admins if a.first_name == author_name),
                    reviewer or recruiter,
                )
                _, note_created = ApplicationNote.objects.get_or_create(
                    application=application, action=action, content=content,
                    defaults={
                        "user": author,
                        "attachments": "cv.pdf" if action == "created" else None,
                    },
                )
                made["application_notes"] += 1 if note_created else 0

            if interview_spec:
                interviewer = admins[0] if admins else None
                interview, interview_created = Interview.objects.get_or_create(
                    application=application,
                    interview_stage=interview_spec["interview_stage"],
                    defaults={
                        "interview_type": interview_spec["interview_type"],
                        "interviewer": interviewer,
                        "scheduled_at": interview_date,
                        "duration_minutes": interview_spec["duration_minutes"],
                        "location": interview_spec["location"],
                        "notes": interview_spec["notes"],
                        "outcome": interview_spec["outcome"],
                        "feedback": interview_spec["feedback"],
                    },
                )
                made["interviews"] += 1 if interview_created else 0
        return made

    # ── Platform (plans, features, notifications) ──────────────────────
    def _platform(self, accounts, crm, crm_articles=None):
        crm_articles = crm_articles or list(Article.objects.filter(is_discussion=False))
        made = {"plans": 0, "subscriptions": 0, "feature_requests": 0,
                "feature_votes": 0, "feature_tasks": 0, "microtasks": 0,
                "media_assets": 0, "whatsapp_queue": 0, "notifications": 0}

        plans = {}
        for name, slug, price, interval, is_default, features in PLANS:
            plan, created = Plan.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name, "price": price, "interval": interval,
                    "is_default": is_default, "features": features,
                    "currency": "KES",
                },
            )
            plans[slug] = plan
            made["plans"] += 1 if created else 0

        clients = list(AuthUser.objects.filter(email__in=[c[0] for c in CLIENTS]))
        for index, user in enumerate(clients):
            slug = ["growth", "scale", "starter", "annual-growth"][index % 4]
            subscription, created = Subscription.objects.get_or_create(
                user=user, plan=plans[slug],
                defaults={"status": "active" if index % 3 else "past_due"},
            )
            made["subscriptions"] += 1 if created else 0
            # Active subscriptions renew; past-due ones were left to lapse so
            # the dunning queue has a row.
            _ensure(subscription, ends_at=_ago(-365) if index % 3 else _ago(12))

        admins = list(AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS]))
        requests = {}
        for index, (title, status, category, votes, description) in enumerate(FEATURE_REQUESTS):
            request, created = FeatureRequest.objects.get_or_create(
                slug=slugify(title)[:220],
                defaults={
                    "title": title, "description": description,
                    "status": status, "category": category, "vote_count": votes,
                    "author": admins[index % len(admins)] if admins else None,
                },
            )
            requests[title] = request
            made["feature_requests"] += 1 if created else 0
            _ensure(request, author=admins[index % len(admins)] if admins else None)

        for index, user in enumerate(clients):
            title, _, _, votes, _ = FEATURE_REQUESTS[index % len(FEATURE_REQUESTS)]
            _, created = FeatureVote.objects.get_or_create(
                user=user, feature_request=requests[title]
            )
            made["feature_votes"] += 1 if created else 0

        for index, (title, task_title, priority, status) in enumerate(FEATURE_TASKS):
            request = requests.get(title)
            if request is None:
                continue
            task, created = FeatureTask.objects.get_or_create(
                feature_request=request, title=task_title,
                defaults={"priority": priority, "status": status},
            )
            made["feature_tasks"] += 1 if created else 0
            _ensure(
                task,
                priority=priority,
                status=status,
                description=(
                    f"Deliverable for {request.title!r}. Tracked against the "
                    f"quarterly roadmap commitment and reviewed at the "
                    f"mid-sprint planning meeting."
                ),
                assignee=admins[index % len(admins)] if admins else None,
                due_date=(timezone.now() + timezone.timedelta(days=21 - index * 5)).date(),
                completed_at=_ago(4) if status == "done" else None,
            )

            # Break each task into slices so the microtask board is not empty.
            for micro_title, micro_status, micro_desc, due_days in \
                    S.MICROTASKS.get(task_title, []):
                _, micro_created = FeatureMicrotask.objects.get_or_create(
                    task=task, title=micro_title,
                    defaults={
                        "description": micro_desc,
                        "status": micro_status,
                        "assignee": task.assignee,
                        "completed_at": _ago(due_days) if micro_status == "done" else None,
                    },
                )
                made["microtasks"] += 1 if micro_created else 0

        for index, (name, kind) in enumerate([("Dovetec brand guidelines", "document"),
                                              ("Platform architecture overview", "document"),
                                              ("Product UI screenshots", "image")]):
            asset, created = MediaAsset.objects.get_or_create(
                original_name=name,
                defaults={"kind": kind, "status": "ready", "is_public": True},
            )
            made["media_assets"] += 1 if created else 0
            _ensure(
                asset,
                kind=kind,
                status="ready",
                is_public=True,
                mime_type="image/png" if kind == "image" else "application/pdf",
                size_bytes=184320 if kind == "image" else 962560,
                alt_text=(
                    "Product interface screenshots from the Dovetec client portal."
                    if kind == "image" else ""
                ),
                owner=admins[index % len(admins)] if admins else None,
            )
            # content_type/object_id are a GenericForeignKey: the asset is
            # really "attached to" an Article, not just filed in a library.
            if asset.content_type_id is None and crm_articles:
                linked = crm_articles[index % len(crm_articles)]
                asset.content_type = ContentType.objects.get_for_model(linked)
                asset.object_id = linked.pk
                asset.save(update_fields=["content_type", "object_id"])

        # Each WhatsApp row hangs off an in-app Notification, which is how
        # the CRM keeps an auditable record of what the client was told.
        for index, contact in enumerate(crm["contacts"].values()):
            if contact.portal_user_id is None:
                continue
            message = "Your Dovetec support ticket has been assigned and is now in triage."
            notification, _ = Notification.objects.get_or_create(
                title="Support ticket assigned",
                body=(
                    f"Your ticket has been assigned to our support queue and is now "
                    f"in triage. We will follow up as soon as we have a fix or need "
                    f"more information from you."
                ),
                recipient=contact.portal_user,
                defaults={
                    "actor": admins[0] if admins else None,
                    "verb": "assigned",
                    "link": "https://dovetecenterprises.vercel.app/contact-us/",
                    "email_sent": True,
                    "whatsapp_sent": index % 2 == 0,
                    "read_at": _ago(2) if index % 3 else None,
                },
            )
            whatsapp, created = WhatsAppNotification.objects.get_or_create(
                message=message,
                recipient_name=f"{contact.first_name} {contact.last_name}",
                recipient_phone=contact.phone or "+254 700 000 000",
                channel="ticket",
            )
            made["whatsapp_queue"] += 1 if created else 0
            _ensure(
                whatsapp,
                status="sent" if index % 2 == 0 else "pending",
                notification=notification,
                sent_at=_ago(2) if index % 2 == 0 else None,
            )
        made["notifications"] = Notification.objects.count()
        return made

    # ── Discovery questionnaires ───────────────────────────────────────
    def _questionnaires(self, crm):
        """Send real discovery questionnaires against the seeded inquiries.

        QuestionnaireTemplate/Question are populated by data migration 0014,
        so this reuses that bank rather than duplicating it: each
        Questionnaire points at a template, gets Answers for that
        template's questions, and records its own event trail. A few
        per-engagement questions are attached to the Questionnaire itself,
        which is how the dashboard's custom-question path is exercised.
        """
        made = {"questionnaires": 0, "answers": 0, "events": 0, "custom_questions": 0}
        admins = list(AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS]))
        by_topic = {i.message.split(".")[0]: i for i in crm["inquiries"]}

        for spec in S.QUESTIONNAIRES:
            inquiry = by_topic.get(spec["inquiry"])
            template = QuestionnaireTemplate.objects.filter(
                title=spec["template"]
            ).first()
            if inquiry is None or template is None:
                continue
            completed = spec["status"] == "completed"
            started = _ago(70 - len(spec["events"]) * 6)
            questionnaire, created = Questionnaire.objects.get_or_create(
                inquiry=inquiry, title=template.title,
                defaults={
                    "intro": spec["intro"],
                    "status": spec["status"],
                    "source_template": template,
                    "context": spec["context"],
                    "completed_at": _ago(58) if completed else None,
                },
            )
            if created:
                made["questionnaires"] += 1
            _ensure(
                questionnaire,
                intro=spec["intro"],
                status=spec["status"],
                source_template=template,
                context=spec["context"],
                completed_at=_ago(58) if completed else None,
            )

            bank = list(template.questions.order_by("order"))

            # Per-engagement questions the template bank does not carry.
            custom_questions = []
            for order, (text, qtype, help_text, q_order, required) in enumerate(
                spec.get("custom_questions", []), start=1
            ):
                question, q_created = Question.objects.get_or_create(
                    questionnaire=questionnaire, text=text,
                    defaults={
                        "help_text": help_text,
                        "question_type": qtype,
                        "required": required,
                        "order": q_order,
                        "context": spec["context"],
                    },
                )
                _ensure(question, help_text=help_text, question_type=qtype,
                        required=required, order=q_order, context=spec["context"])
                custom_questions.append(question)
                made["custom_questions"] += 1 if q_created else 0

            if spec["status"] in ("in_progress", "completed"):
                answered = spec.get("answers", [])
                pairs = list(zip(bank, answered))
                pairs += list(zip(custom_questions, spec.get("answers_custom", [])))
                for question, text_answer in pairs:
                    _, answer_created = Answer.objects.get_or_create(
                        question=question, defaults={"answer": text_answer}
                    )
                    made["answers"] += 1 if answer_created else 0

            # The event log is the audit trail, so each step records the
            # question it concerned and the answer that was captured.
            answered = spec.get("answers", [])
            for position, action in enumerate(spec["events"]):
                event, event_created = QuestionnaireEvent.objects.get_or_create(
                    questionnaire=questionnaire, action=action,
                    defaults={
                        "actor": admins[0] if admins else None,
                        "content": {
                            "created": "Questionnaire created from the inquiry.",
                            "sent": "Questionnaire emailed to the client contact.",
                            "opened": "Client opened the questionnaire link.",
                            "answered": "Client submitted their answers.",
                            "completed": "Questionnaire marked complete by the delivery lead.",
                        }[action],
                        "created_at": started + timezone.timedelta(hours=position * 6),
                    },
                )
                made["events"] += 1 if event_created else 0
                # "answered" and "completed" sit after "created" and "sent",
                # so the nth such event corresponds to the nth bank answer.
                answer_index = position - 2
                _ensure(
                    event,
                    actor=admins[0] if admins else None,
                    question=(
                        bank[answer_index]
                        if action in ("answered", "completed")
                        and 0 <= answer_index < len(bank) else None
                    ),
                    answer_snapshot=(
                        answered[answer_index]
                        if action in ("answered", "completed")
                        and 0 <= answer_index < len(answered) else None
                    ),
                )
        return made

    # ── Article discussion threads ─────────────────────────────────────
    def _engagement(self, content):
        """Discussion threads, article reactions and in-app notifications.

        Runs after _content and _community so there are articles, posts and
        comments to hang the engagement off.
        """
        made = {"discussion_topics": 0, "discussion_replies": 0, "notifications": 0}
        admins = list(AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS]))
        authors = {u.first_name: u for u in admins}
        clients = list(AuthUser.objects.filter(email__in=[c[0] for c in CLIENTS]))
        articles = content["articles"]

        for index, spec in enumerate(S.DISCUSSION_TOPICS):
            author = authors.get(spec["author"]) or (admins[0] if admins else None)
            topic, created = DiscussionTopic.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "slug": slugify(spec["title"]),
                    "description": spec["description"],
                    "status": spec["status"],
                    "author": author.profile if author else None,
                    "is_pinned": spec["is_pinned"],
                    "vote_count": len(spec["replies"]) * 2,
                },
            )
            if created:
                made["discussion_topics"] += 1
            if index >= len(articles):
                continue

            # Discussions are articles flagged as discussion, so a seeded
            # article carries the thread rather than a detached record.
            article = articles[index]
            if not article.is_discussion or article.discussion_topic_id != topic.pk:
                article.is_discussion = True
                article.discussion_topic = topic
                article.save(update_fields=["is_discussion", "discussion_topic"])

            # home.Reply hangs off a Comment, so the thread needs an opening
            # comment to reply to. The topic description becomes that comment.
            if author is None:
                DiscussionTopic.objects.filter(pk=topic.pk).update(
                    reply_count=len(spec["replies"])
                )
                continue
            root, _ = Comment.objects.get_or_create(
                article=article, user=author,
                defaults={"content": spec["description"]},
            )
            for position, body in enumerate(spec["replies"]):
                replier = clients[position % len(clients)] if clients else author
                _, reply_created = Reply.objects.get_or_create(
                    comment=root, user=replier, content=body,
                )
                made["discussion_replies"] += 1 if reply_created else 0

            DiscussionTopic.objects.filter(pk=topic.pk).update(
                reply_count=len(spec["replies"])
            )

        # Notifications for the delivery team, so the in-app bell and the
        # notification list are not empty on first sign-in.
        notification_specs = [
            ("New support ticket awaiting triage", "ticket",
             "A new ticket arrived from the client portal and has not been assigned yet.",
             "https://dovetecenterprises.vercel.app/contact-us/", 1),
            ("Discovery questionnaire completed", "questionnaire_completed",
             "Jamii Health completed the clinical records discovery questionnaire. "
             "The answers are ready for review ahead of the scoping workshop.",
             "https://dovetecenterprises.vercel.app/services/", 2),
            ("Newsletter digest published", "note",
             "The Q3 Innovation Digest was published to the newsletter archive and is "
             "awaiting review before scheduling.",
             "https://dovetecenterprises.vercel.app/newsletter/", 0),
            ("Job application moved to offer", "stage_change",
             "Mercy Achieng has completed the final round for the backend lead role "
             "and the offer letter is ready to prepare.",
             "https://dovetecenterprises.vercel.app/careers/", 3),
        ]
        for index, (title, verb, body, link, unread_days) in enumerate(notification_specs):
            recipient = admins[index % len(admins)] if admins else None
            if recipient is None:
                break
            _, created = Notification.objects.get_or_create(
                title=title, recipient=recipient,
                defaults={
                    "actor": admins[0] if admins else None,
                    "verb": verb,
                    "body": body,
                    "link": link,
                    "email_sent": index % 2 == 0,
                    "whatsapp_sent": False,
                    # read_days=0 leaves it unread in the notification centre.
                    "read_at": _ago(unread_days) if unread_days else None,
                },
            )
            made["notifications"] += 1 if created else 0
        return made

    # ── Newsletter ─────────────────────────────────────────────────────
    # ── Adverts app (separate models from home.Advertisement) ──────────
    def _adverts(self, tax, make_images):
        """Populate the adverts app.

        The adverts app has its own Advertisement model (main_image is
        mandatory) plus AdvertLeads, which the newsletter slots do not cover.
        """
        made = {"advertisements": 0, "leads": 0}

        for index, (title, description, url) in enumerate(ADVERT_SLOTS):
            advert, created = SiteAdvertisement.objects.get_or_create(
                title=title,
                defaults={"description": description, "url": url,
                          "published_at": _ago(20 - index * 3)},
            )
            _ensure(advert, description=description, url=url,
                    published_at=_ago(20 - index * 3))
            if created:
                made["advertisements"] += 1
            if make_images and not advert.main_image:
                advert.main_image.save(
                    f"ad-{index + 1}.png", _png((60, 90, 150)), save=True
                )

        leads = [
            ("James Otieno", "james.otieno@harambeesacco.co.ke", "+254 712 100 001",
             "Harambee Sacco Union", "Mobile field app",
             "We have 40 field officers across four counties and need offline capture."),
            ("Linda Mwangi", "linda.mwangi@oddibites.co.ke", "+254 712 100 002",
             "Oddibites", "Payment integration",
             "Looking for M-Pesa checkout plus a reconciled payout report."),
            ("Grace Njeri", "grace.njeri@techdarasa.ac.ke", "+254 712 100 003",
             "TechDarasa", "Learning platform",
             "Fee collection and parent portals for three campuses."),
        ]
        for name, email, phone, company, interest, message in leads:
            _, created = AdvertLead.objects.get_or_create(
                email=email,
                defaults={
                    "name": name,
                    "phone": phone,
                    "company": company,
                    "interest": interest,
                    "message": message,
                },
            )
            made["leads"] += 1 if created else 0

        return made

    def _newsletter(self, tax, content, make_images):
        made = {"newsletter": 0, "references": 0, "attachments": 0, "logs": 0,
                "advertisements": 0}

        adverts = []
        for index, (title, description, url) in enumerate(ADVERT_SLOTS):
            # home.Advertisement has no published_at field; it is dated by
            # created_at (auto_now_add). Backdating that keeps the digest's
            # slot ordering believable.
            advert, created = HomeAdvertisement.objects.get_or_create(
                title=title,
                defaults={"description": description, "url": url},
            )
            if not created:
                wanted_created = _ago(20 - index * 3)
                if abs((advert.created_at - wanted_created).days) > 1:
                    HomeAdvertisement.objects.filter(pk=advert.pk).update(
                        created_at=wanted_created
                    )
                    advert.refresh_from_db()
            if created:
                made["advertisements"] += 1
                if make_images and not advert.image:
                    advert.image.save(
                        f"advert-{index + 1}.png", _png((90, 40, 140)), save=True
                    )
            adverts.append(advert)

        spec = S.NEWSLETTER
        # The digest is published and sent, so the archive and the KPI panels
        # both have something real behind them rather than a bare draft.
        sent_at = _ago(9)
        newsletter, created = Newsletter.objects.get_or_create(
            subject=spec["subject"],
            defaults={
                "preheader": spec["preheader"],
                "subtitle": spec["subtitle"],
                "content": spec["content"],
                "status": "sent",
                "published_at": _ago(10),
                "sent_at": sent_at,
                "scheduled_for": sent_at,
                # content_id is an integer FK-ish column; it cannot be set
                # before the row exists, so _ensure() below fills in the pk.
                "accent_color": spec["accent_color"],
                "cta_label": spec["cta_label"],
                "cta_text": spec["cta_text"],
                "cta_url": "https://dovetecenterprises.vercel.app/newsletter/",
                "advertisement": adverts[0] if adverts else None,
            },
        )
        made["newsletter"] += 1 if created else 0
        _ensure(
            newsletter,
            status="sent",
            content_id=newsletter.pk,
            published_at=_ago(10),
            sent_at=sent_at,
            scheduled_for=sent_at,
        )

        newsletter.recipients.set(
            NewsletterSubscription.objects.filter(unsubscribed_at__isnull=True)
        )
        newsletter.adverts.set(adverts)

        # One reference per content kind so the digest exercises every section.
        references = {
            "article": content["articles"][0] if content["articles"] else None,
            "resource": content["resources"][0] if content["resources"] else None,
            "service": tax["capabilities"].get("Custom Software Engineering"),
            "product": Product.objects.filter(name="AfriLedger Core").first(),
            "case_study": CaseStudy.objects.filter(name="Agridoer").first(),
            "advertisement": adverts[0] if adverts else None,
        }
        for reference in newsletter.content_references.all():
            reference.delete()
        for order, (kind, obj) in enumerate(references.items()):
            if obj is None:
                continue
            NewsletterContentReference.objects.create(
                newsletter=newsletter, kind=kind, content_object=obj, order=order
            )
            made["references"] += 1

        if make_images and not newsletter.attachments.exists():
            body = (
                "Dovetec Enterprises\n"
                "2026 Engineering Readiness Report\n\n"
                "Patterns from forty engagements across financial services, healthcare,\n"
                "education, agriculture and the public sector.\n"
            )
            NewsletterAttachment.objects.create(
                newsletter=newsletter,
                name="engineering-readiness-2026.txt",
                description="Summary of the 2026 Engineering Readiness Report.",
                file=_txt(body, "engineering-readiness-2026.txt"),
                order=0,
            )
            made["attachments"] += 1

        # Prior sends with realistic engagement, so KPI panels are not empty
        # and the dashboard's turnout chart has a genuine spread rather than
        # three identical bars. Outcomes cover opened, read, clicked-through,
        # unsubscribed and hard-bounced.
        user_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0",
            "Mozilla/5.0 (Android 15; Mobile; rv:133.0) Gecko/133.0 Firefox/133.0",
        ]
        # (status, opened, clicked, read, bounced, unsubscribed)
        OUTCOMES = [
            ("opened", True, True, True, False, False),
            ("clicked", True, True, False, False, False),
            ("opened", True, False, True, False, False),
            ("read", True, False, True, False, False),
            ("sent", False, False, False, False, False),
            ("sent", False, False, False, False, False),
            ("unsubscribed", False, False, False, False, True),
            ("bounced", False, False, False, True, False),
        ]
        extra_recipients = [
            "rebecca.mwangi@example.com", "ian.korir@example.com",
            "mercy.otieno@example.com", "brian.kimutai@example.com",
            "susan.njenga@example.com",
        ]
        click_targets = [
            "newsletter/", "services/", "blog/", "contact/",
            "case-studies/", "blog-detail/agridoer-fintech-infrastructure/",
        ]
        sends = [(sub.email, sub.user) for sub in newsletter.recipients.all()]
        sends += [(email, None) for email in extra_recipients]
        for index, (email, user) in enumerate(sends):
            if index >= len(OUTCOMES):
                break
            status, opened, clicked, read, bounced, unsubscribed = OUTCOMES[index]
            bounces = {
                "status": "bounced", "bounce_reason": "550 5.1.1 User unknown",
                "error": "SMTP 550: recipient address rejected: user unknown",
            } if bounced else {"status": status}
            log, created = NewsletterLog.objects.get_or_create(
                newsletter=newsletter, email=email,
            )
            if created:
                made["logs"] += 1
            _ensure(
                log,
                user=user,
                user_agent=user_agents[index % len(user_agents)],
                sent_at=sent_at,
                opened=opened, clicked=clicked, read=read,
                bounced=bounced, unsubscribed=unsubscribed,
                opened_at=_ago(8, hours=3) if opened else None,
                clicked_at=_ago(8, hours=2) if clicked else None,
                # A click with no destination is incoherent: every click in the
                # digest points at one of its own tracked CTAs.
                clicked_url=(
                    f"https://dovetecenterprises.vercel.app/{click_targets[index % len(click_targets)]}"
                    if clicked else None
                ),
                ip_address=(
                    # Documentation/test ranges only (RFC 5737), never a real
                    # recipient address.
                    f"198.51.100.{index % 250 + 1}" if opened else None
                ),
                read_at=_ago(8, hours=1) if read else None,
                **bounces,
            )
        return made


def community_comment(post, user):
    """Create a moderated community comment on a post.

    Kept in a helper because community.Comment is an MTI child of home.Comment
    and shares the parent's unique (article, user) constraint.
    """
    from community.models import Comment as CommunityComment
    return CommunityComment.objects.get_or_create(
        article=post, user=user,
        defaults={
            "content": "Useful, thank you. We hit the same issue and ended up taking a different approach.",
            "moderation_state": "approved",
        },
    )
