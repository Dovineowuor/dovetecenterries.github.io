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
from io import BytesIO
from pathlib import Path

from PIL import Image
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone
from django.utils.text import slugify

from dovetecenterprises import seed_data as S

from home.models import (
    Article, Comment, Department, Feedback, Job, JobApplication, Like,
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
    CaseStudy, Contact, FeatureRequest, FeatureTask, FeatureVote,
    MediaAsset, Organization, Plan, Project, ServiceInquiry, Subscription,
    Ticket, TicketActivity, WhatsAppNotification,
)
from shop.models import (
    Category as ShopCategory, Keyword, Order, OrderItem, Payment, Product,
)
from community.models import Category as CommunityCategory, Event, Post, Topic
from adverts.models import Advertisement as SiteAdvertisement, AdvertLeads as AdvertLead

# ── Accounts ───────────────────────────────────────────────────────────
ADMINS = [
    {
        "email": "admin@dovetecenterprises.tech",
        "password": "REDACTED",
        "first_name": "Sarah", "last_name": "Johnson",
        "title": "Principal Consultant",
        "bio": "Principal consultant at Dovetec Enterprises, leading software engineering engagements across East Africa.",
    },
    {
        "email": "dove@dovetecenterprises.tech",
        "password": "REDACTED",
        "first_name": "Dove", "last_name": "Owino",
        "title": "Founder & Lead Engineer",
        "bio": "Founder of Dovetec Enterprises. Builds delivery practice and architecture for fintech and healthcare clients.",
    },
    {
        "email": "admin2@dovetecenterprises.tech",
        "password": "REDACTED",
        "first_name": "Michael", "last_name": "Chen",
        "title": "Head of Engineering",
        "bio": "Heads engineering at Dovetec Enterprises. Focus on infrastructure, observability and delivery reliability.",
    },
]
STAFF = {
    "email": "staff@dovetecenterprises.tech",
    "password": "REDACTED",
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


class Command(BaseCommand):
    help = "Create admin accounts and load industry-aligned dummy data across all apps."

    def add_arguments(self, parser):
        parser.add_argument(
            "--password", default=None,
            help="Password to set on every account created (default: %(default)r).",
        )
        parser.add_argument(
            "--flush-newsletters", action="store_true",
            help="Delete auto-generated Newsletter rows before seeding the sample digest.",
        )
        parser.add_argument(
            "--no-images", action="store_true",
            help="Skip image uploads; mandatory image fields are left blank.",
        )

    def handle(self, *args, **opts):
        password = opts["password"]
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
                summary["platform"] = self._platform(summary["accounts"], summary["crm"])
                summary["newsletter"] = self._newsletter(
                    summary["taxonomy"], summary["content"], make_images
                )
                summary["adverts"] = self._adverts(summary["taxonomy"], make_images)
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
        self.stdout.write(self.style.SUCCESS(
            f"\nSign in at /admin/ as {ADMINS[0]['email']} / {password}"
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
                    user.set_password(spec["password"])
                    user.save(update_fields=["is_superuser", "is_staff", "password"])
            elif created:
                user.set_password(spec["password"])
                user.save()
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

        for email, first, last, title in CLIENTS:
            spec = {"email": email, "first_name": first, "last_name": last,
                    "title": title, "bio": "", "password": password}
            _, created = upsert(spec, client_group)
            made["clients"] += 1 if created else 0
            sub, sub_created = NewsletterSubscription.objects.get_or_create(
                email=email, defaults={"is_verified": True}
            )
            if not sub.is_verified or sub.unsubscribed_at:
                sub.is_verified = True
                sub.unsubscribed_at = None
                sub.save(update_fields=["is_verified", "unsubscribed_at"])
            made["subscriptions"] += 1 if sub_created else 0

        # One deliberately unsubscribed contact, so opt-out handling is visible.
        NewsletterSubscription.objects.get_or_create(
            email="former.subscriber@example.com",
            defaults={"is_verified": True, "unsubscribed_at": timezone.now()},
        )
        return made

    # ── Taxonomy ───────────────────────────────────────────────────────
    def _taxonomy(self):
        tags = {}
        for name in S.TAGS:
            tag, _ = Tag.objects.get_or_create(
                name=name, defaults={"slug": slugify(name)}
            )
            tags[name] = tag

        capabilities = {}
        for name, description in S.CAPABILITIES.items():
            category, _ = ShopCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            capabilities[name] = category

        communities = {}
        for name, description in S.COMMUNITY_CATEGORIES:
            category, _ = CommunityCategory.objects.get_or_create(
                name=name, defaults={"description": description}
            )
            communities[name] = category

        keywords = {}
        for name in ("Django", "Python", "PostgreSQL", "Kubernetes", "M-Pesa",
                     "TypeScript", "Flutter", "Android", "FHIR", "USSD"):
            keyword, _ = Keyword.objects.get_or_create(name=name)
            keywords[name] = keyword

        return {
            "tags": tags,
            "capabilities": capabilities,
            "communities": communities,
            "keywords": keywords,
            "made": {
                "tags": Tag.objects.count(),
                "capabilities": ShopCategory.objects.count(),
                "community_categories": CommunityCategory.objects.count(),
                "keywords": Keyword.objects.count(),
            },
        }

    # ── Editorial content ──────────────────────────────────────────────
    def _content(self, tax, make_images):
        authors = {
            u.first_name: u
            for u in AuthUser.objects.filter(email__in=[a["email"] for a in ADMINS])
        }
        made = {"articles": 0, "resources": 0}

        def publish(spec, is_resource):
            author_user = authors.get(spec.get("author", "")) or next(iter(authors.values()), None)
            article, created = Article.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "content": spec["content"],
                    "status": "published",
                    "featured": spec.get("featured", False),
                    "is_resource": is_resource,
                    "resource_type": spec["resource_type"],
                    "user": author_user,
                    "author": getattr(author_user, "profile", None),
                    "views": 120 + (len(spec["title"]) * 7),
                },
            )
            if created:
                made["resources" if is_resource else "articles"] += 1
            article.tags.add(tax["tags"][spec["tag"]])
            if make_images and not article.image:
                article.image.save(
                    f"{article.slug}.png", _png((32, 99, 155)), save=True
                )
            return article

        articles = [publish(spec, False) for spec in S.ARTICLES]
        resources = [publish(spec, True) for spec in S.RESOURCES]

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

        if clients and articles:
            first = articles[0]
            comment = Comment.objects.filter(article=first, user=clients[0]).first()
            if comment:
                Reply.objects.get_or_create(
                    comment=comment, user=clients[1 % len(clients)],
                    defaults={"content": "Agreed. We also underinvested in reconciliation tooling "
                                         "and paid for it during the first month of parallel running."},
                )
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
        for email, first, last, title in CLIENTS:
            contact, created = Contact.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first, "last_name": last, "job_title": title,
                    "phone": "+254 712 000 000",
                },
            )
            # Anchor each client contact to the organisation that employs them.
            org = orgs.get(CLIENT_ORGANIZATION_BY_EMAIL.get(email, ""))
            if org is not None:
                contact.organization = org
                contact.save(update_fields=["organization"])
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
        ]):
            service = ["software", "it", "consulting"][index % 3]
            stage = ["new", "contacted", "qualified", "proposal",
                     "negotiation", "won"][index % 6]
            contact = contacts[email]
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
                },
            )
            inquiries.append(inquiry)
            made["inquiries"] += 1 if created else 0

        for subject, ttype, status, priority, service, desc, email in TICKETS:
            ticket, created = Ticket.objects.get_or_create(
                subject=subject,
                defaults={
                    "description": desc,
                    "type": ttype,
                    "status": status,
                    "priority": priority,
                    "service": service,
                    "contact": contacts.get(email),
                    "assigned_to": staff.first() if staff.exists() else None,
                },
            )
            if created:
                made["tickets"] += 1
                for action, content in [
                    ("created", "Ticket created from the client portal."),
                    ("assigned", "Assigned to the support queue."),
                    ("note", "Initial triage completed; reproducing on staging."),
                ][: {"new": 1, "open": 2, "waiting": 3, "resolved": 3, "closed": 3}[status]]:
                    TicketActivity.objects.create(ticket=ticket, action=action, content=content)
                    made["tickets_activities"] += 1

        # Project has no industry field; pair each project with the inquiry
        # that originated it. converted_from_inquiry is deliberately left
        # unset: completing a project that carries one fires a signal which
        # builds a questionnaire and sends notifications.
        by_topic = {i.message.split(".")[0]: i for i in inquiries}
        for name, status, priority, service, industry, desc, budget in PROJECTS:
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
                    "organization": orgs.get(next(
                        (oname for oname, ind, _ in ORGANIZATIONS if ind == industry), ""
                    )),
                    "start_date": timezone.now().date(),
                    "actual_end_date": (
                        timezone.now().date() if status == "completed" else None
                    ),
                    "client_feedback": (
                        "Delivered on scope with the reconciliation tooling the team "
                        "asked for during the first month of parallel running."
                        if status == "completed" else ""
                    ),
                },
            )
            if created:
                made["projects"] += 1
                inquiry = next(
                    (i for i in inquiries
                     if i.industry == industry and i.stage in ("won", "negotiation", "proposal")),
                    None,
                )
                if inquiry is not None:
                    project.converted_from_inquiry = inquiry
                    project.save(update_fields=["converted_from_inquiry"])

        made["subscribers"] = NewsletterSubscription.objects.filter(
            unsubscribed_at__isnull=True
        ).count()
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
        made = {"products": 0, "orders": 0, "payments": 0}
        for name, spec in S.PRODUCTS.items():
            product, created = Product.objects.get_or_create(
                name=name,
                defaults={
                    "price": spec["price"],
                    "stock": spec["stock"],
                    "category": tax["capabilities"][spec["category"]],
                    "description": spec["description"],
                },
            )
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
        return made

    # ── Community ──────────────────────────────────────────────────────
    def _community(self, accounts, tax, make_images):
        made = {"topics": 0, "posts": 0, "comments": 0, "events": 0}
        authors = {u.first_name: u for u in AuthUser.objects.filter(
            email__in=[a["email"] for a in ADMINS]
        )}

        topics = {}
        for spec in S.TOPICS:
            topic, created = Topic.objects.get_or_create(
                name=spec["name"],
                defaults={
                    "slug": slugify(spec["name"]),
                    "category": tax["communities"][spec["category"]],
                    "description": spec["description"],
                },
            )
            topics[spec["name"]] = topic
            made["topics"] += 1 if created else 0

        for spec in S.POSTS:
            author = authors.get(spec["author"].split()[0])
            post, created = Post.objects.get_or_create(
                title=spec["title"],
                defaults={
                    "content": spec["content"],
                    "topic": topics[spec["topic"]],
                    "status": "published",
                    "moderation_state": "approved",
                    "user": author,
                    "author": author.profile if author else None,
                    "views": 80 + len(spec["content"]),
                },
            )
            if created:
                made["posts"] += 1

        client_users = list(AuthUser.objects.filter(email__in=[c[0] for c in CLIENTS]))
        for index, post in enumerate(Post.objects.all()):
            if not client_users:
                break
            user = client_users[index % len(client_users)]
            comment, created = community_comment(post, user)
            made["comments"] += 1 if created else 0

        now = timezone.now()
        for index, (title, event_type, days) in enumerate([
            ("Designing for intermittent connectivity", "webinar", 14),
            ("Django performance clinic", "workshop", 21),
            ("Kenya Python community meetup", "meetup", 7),
            ("Fintech architecture conference", "conference", 45),
        ]):
            _, created = Event.objects.get_or_create(
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
            made["events"] += 1 if created else 0

        return made

    # ── Talent ─────────────────────────────────────────────────────────
    def _talent(self):
        made = {"departments": 0, "jobs": 0, "applications": 0, "sources": 0}
        departments = {}
        for name, description in DEPARTMENTS:
            dept, created = Department.objects.get_or_create(
                name=name, defaults={"description": description, "headcount": 4}
            )
            departments[name] = dept
            made["departments"] += 1 if created else 0

        for title, dept, location, level, salary, description in JOBS:
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
                },
            )
            if created:
                made["jobs"] += 1

        for source, stype in [("LinkedIn", "social_media"), ("Job board", "job_board"),
                              ("Referral", "referral"), ("Company website", "company_website")]:
            _, created = SourceTracker.objects.get_or_create(
                source_name=source, defaults={"source_type": stype}
            )
            made["sources"] += 1 if created else 0

        jobs = list(Job.objects.all())
        applicants = [
            ("Wanjiru Kamau", "wanjiru.kamau@example.com", "shortlisted", "high", "referral"),
            ("Brian Mutiso", "brian.mutiso@example.com", "interview_scheduled", "medium", "linkedin"),
            ("Faith Chebet", "faith.chebet@example.com", "new", "medium", "job_portal"),
            ("Kevin Otieno", "kevin.otieno@example.com", "assessment", "high", "social_media"),
            ("Mercy Achieng", "mercy.achieng@example.com", "offer", "urgent", "referral"),
        ]
        for index, (name, email, status, priority, source) in enumerate(applicants):
            if index >= len(jobs):
                break
            _, created = JobApplication.objects.get_or_create(
                job=jobs[index], candidate_name=name, candidate_email=email,
                defaults={"status": status, "priority": priority, "source": source},
            )
            made["applications"] += 1 if created else 0
        return made

    # ── Platform (plans, features, notifications) ──────────────────────
    def _platform(self, accounts, crm):
        made = {"plans": 0, "subscriptions": 0, "feature_requests": 0,
                "feature_votes": 0, "feature_tasks": 0, "media_assets": 0,
                "whatsapp_queue": 0}

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
            _, created = Subscription.objects.get_or_create(
                user=user, plan=plans[slug],
                defaults={"status": "active" if index % 3 else "past_due"},
            )
            made["subscriptions"] += 1 if created else 0

        requests = {}
        for title, status, category, votes, description in FEATURE_REQUESTS:
            request, created = FeatureRequest.objects.get_or_create(
                slug=slugify(title)[:220],
                defaults={
                    "title": title, "description": description,
                    "status": status, "category": category, "vote_count": votes,
                },
            )
            requests[title] = request
            made["feature_requests"] += 1 if created else 0

        for index, user in enumerate(clients):
            title, _, _, votes, _ = FEATURE_REQUESTS[index % len(FEATURE_REQUESTS)]
            _, created = FeatureVote.objects.get_or_create(
                user=user, feature_request=requests[title]
            )
            made["feature_votes"] += 1 if created else 0

        for title, task_title, priority, status in FEATURE_TASKS:
            request = requests.get(title)
            if request is None:
                continue
            _, created = FeatureTask.objects.get_or_create(
                feature_request=request, title=task_title,
                defaults={"priority": priority, "status": status},
            )
            made["feature_tasks"] += 1 if created else 0

        for name, kind in [("Dovetec brand guidelines", "document"),
                           ("Platform architecture overview", "document"),
                           ("Product UI screenshots", "image")]:
            asset, created = MediaAsset.objects.get_or_create(
                original_name=name,
                defaults={"kind": kind, "status": "ready", "is_public": True},
            )
            made["media_assets"] += 1 if created else 0

        for index, contact in enumerate(crm["contacts"].values()):
            _, created = WhatsAppNotification.objects.get_or_create(
                message="Your Dovetec support ticket has been assigned and is now in triage.",
                recipient_name=f"{contact.first_name} {contact.last_name}",
                recipient_phone=contact.phone or "+254 700 000 000",
                channel="ticket",
                defaults={"status": "pending"},
            )
            made["whatsapp_queue"] += 1 if created else 0
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
                defaults={"description": description, "url": url},
            )
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
            advert, created = HomeAdvertisement.objects.get_or_create(
                title=title,
                defaults={"description": description, "url": url},
            )
            if created:
                made["advertisements"] += 1
                if make_images and not advert.image:
                    advert.image.save(
                        f"advert-{index + 1}.png", _png((90, 40, 140)), save=True
                    )
            adverts.append(advert)

        spec = S.NEWSLETTER
        newsletter, created = Newsletter.objects.get_or_create(
            subject=spec["subject"],
            defaults={
                "preheader": spec["preheader"],
                "subtitle": spec["subtitle"],
                "content": spec["content"],
                "status": "draft",
                "accent_color": spec["accent_color"],
                "cta_label": spec["cta_label"],
                "cta_text": spec["cta_text"],
                "cta_url": "https://dovetecenterprises.vercel.app/newsletter/",
                "advertisement": adverts[0] if adverts else None,
            },
        )
        made["newsletter"] += 1 if created else 0

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
        newsletter.content_references.all().delete()
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

        # Prior sends with realistic engagement, so KPI panels are not empty.
        for index, sub in enumerate(newsletter.recipients.all()):
            if index >= 3:
                break
            log, created = NewsletterLog.objects.get_or_create(
                newsletter=newsletter, email=sub.email,
                defaults={"status": "sent", "sent_at": timezone.now() - timezone.timedelta(days=9)},
            )
            if created:
                made["logs"] += 1
            if index == 0:
                log.mark_opened()
            elif index == 1:
                log.mark_opened()
                log.mark_clicked("https://dovetecenterprises.vercel.app/newsletter/")
            else:
                log.mark_opened()
                log.mark_clicked("https://dovetecenterprises.vercel.app/portfolio/")
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
