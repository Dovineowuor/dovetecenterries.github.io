"""
Seed script to populate enriched, high-quality live data:
- Case Studies (Apple-style storytelling, problem statements, metrics, colors)
- All-Round Articles & Technical Guides (Froala HTML content, tags, SEO metadata)
- Downloadable Resources
- Shop Categories & Products
- Departments & Job Openings
"""
import os
import sys
import django

# Ensure project root is in path and setup Django
sys.path.insert(0, os.getcwd())
import dotenv
dotenv.load_dotenv('.env.local')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dovetecenterprises.settings')
django.setup()

from django.utils import timezone
from django.contrib.auth import get_user_model
from home.models import (
    Article, Tag, Profile, Department, Job, Advertisement
)
from app.models import CaseStudy
from shop.models import Category as ShopCategory, Product

User = get_user_model()
admin_user, _ = User.objects.get_or_create(
    email='dovetecenterprises@gmail.com',
    defaults={
        'username': 'dovetecenterprises',
        'first_name': 'Dovetec',
        'last_name': 'Team',
        'is_active': True,
        'is_staff': True,
        'is_superuser': True,
    }
)
admin_profile, _ = Profile.objects.get_or_create(user=admin_user)
admin_profile.is_verified = True
admin_profile.save()

print(f"Using Author: {admin_user.email}")

# ---------------------------------------------------------
# 1. TAGS
# ---------------------------------------------------------
tags_data = [
    ("Cloud Engineering", "cloud-engineering"),
    ("Backend Architecture", "backend-architecture"),
    ("DevOps & CI/CD", "devops-cicd"),
    ("Mobile Development", "mobile-development"),
    ("FinTech", "fintech"),
    ("AI & Machine Learning", "ai-ml"),
    ("Cybersecurity", "cybersecurity"),
    ("AgriTech", "agritech"),
    ("EdTech", "edtech"),
    ("UI/UX Design", "ui-ux-design"),
]

tags_dict = {}
for name, slug in tags_data:
    t, _ = Tag.objects.get_or_create(name=name, defaults={"slug": slug})
    tags_dict[name] = t
print(f"Created/verified {len(tags_dict)} Tags.")

# ---------------------------------------------------------
# 2. ARTICLES & RESOURCES
# ---------------------------------------------------------
articles_data = [
    {
        "title": "Scaling PostgreSQL for High-Throughput Serverless Django Applications",
        "seo_description": "Learn how we tuned connection pooling, PgBouncer, and query indexes to handle 10,000+ RPS on serverless Django.",
        "category": "Backend Architecture",
        "tags": ["Backend Architecture", "Cloud Engineering"],
        "views": 4820,
        "likes": 340,
        "featured": True,
        "content": """
        <h2>Introduction</h2>
        <p>Deploying Django on serverless platforms such as AWS Lambda or Vercel introduces unique database connectivity challenges. Because each serverless instance spawns isolated worker environments, traditional long-lived database connections quickly exhaust database connection limits.</p>

        <h2>The Challenge: Connection Exhaustion</h2>
        <p>Under burst traffic spikes, standard Django deployments create a new connection per instance. Without proper connection pooling, database servers quickly hit <code>FATAL: sorry, too many clients already</code>.</p>

        <h3>Our Solution & Architecture</h3>
        <ul>
            <li><strong>PgBouncer Transaction Pooling:</strong> We deployed PgBouncer in transaction pooling mode to manage thousands of transient incoming connections.</li>
            <li><strong>Persistent Health Checks:</strong> Enabled <code>conn_max_age=600</code> and <code>conn_health_checks=True</code> in Django settings.</li>
            <li><strong>Neon Serverless Postgres Integration:</strong> Migrated to Neon's websockets pooler for autoscaling compute branches.</li>
        </ul>

        <h2>Key Benchmark Results</h2>
        <p>After implementing these optimizations, response latency dropped by <strong>68%</strong> under high traffic loads, while connection overhead remained below 15% of database capacity.</p>
        """
    },
    {
        "title": "Architecting Event-Driven Microservices with Python, Kafka, and Redis",
        "seo_description": "A comprehensive deep dive into event-driven design, asynchronous messaging, and idempotency guarantees in distributed systems.",
        "category": "Cloud Engineering",
        "tags": ["Backend Architecture", "Cloud Engineering", "DevOps & CI/CD"],
        "views": 3150,
        "likes": 210,
        "featured": True,
        "content": """
        <h2>Why Event-Driven?</h2>
        <p>In modern enterprise platforms, synchronous REST calls between microservices introduce tight coupling and cascading failure modes. Event-driven architecture (EDA) decouples producers from consumers using asynchronous event streams.</p>

        <h2>Core Components</h2>
        <ol>
            <li><strong>Apache Kafka / Redpanda:</strong> Serves as the distributed event log backbone.</li>
            <li><strong>Redis Streams:</strong> Used for fast ephemeral state caching and pub/sub signaling.</li>
            <li><strong>Idempotency Consumers:</strong> Ensuring at-least-once delivery without duplicate execution side effects.</li>
        </ol>

        <h2>Implementation Highlights</h2>
        <p>We designed payload schemas using Protocol Buffers and enforced strict schema registry checks on all outgoing events, reducing inter-service serialization errors to zero.</p>
        """
    },
    {
        "title": "Building Resilient Mobile Applications with Flutter: Clean Architecture & Offline Sync",
        "seo_description": "Learn how to build offline-first Flutter applications using SQLite, Hive, and background sync queues.",
        "category": "Mobile Development",
        "tags": ["Mobile Development", "UI/UX Design"],
        "views": 2940,
        "likes": 185,
        "featured": False,
        "content": """
        <h2>Offline-First Mobility</h2>
        <p>Mobile applications operating in emerging markets need robust offline capabilities to withstand unstable network coverage. Users expect uninterrupted interaction regardless of connection status.</p>

        <h2>Layered Architecture Breakdown</h2>
        <p>By enforcing a strict boundary between <strong>Data Layer</strong>, <strong>Domain Layer (Use Cases)</strong>, and <strong>UI (BLoC/Notifier) Layer</strong>, our team built an offline-first state engine that transparently queues outgoing requests locally and syncs upon internet restoration.</p>
        """
    },
    {
        "title": "The Complete Guide to CI/CD Pipeline Security: Securing Your Code from Commit to Production",
        "seo_description": "Best practices for securing GitHub Actions, secret management, dependency scanning, and container verification.",
        "category": "DevOps & Security",
        "tags": ["DevOps & CI/CD", "Cybersecurity"],
        "views": 5120,
        "likes": 420,
        "featured": True,
        "content": """
        <h2>Supply Chain Vulnerabilities in Modern CI/CD</h2>
        <p>Software supply chain attacks have increased significantly over recent years. Securing developer pipelines requires continuous verification across every stage of development.</p>

        <h2>Key Security Guardrails</h2>
        <ul>
            <li><strong>OIDC Federation:</strong> Eliminate static cloud credentials by issuing ephemeral short-lived IAM roles via GitHub OIDC.</li>
            <li><strong>SAST & Dependency Scanning:</strong> Integrate Trivy and Snyk into automated pre-merge checks.</li>
            <li><strong>Signed Container Artifacts:</strong> Sign Docker builds with Cosign and verify signatures before container execution.</li>
        </ul>
        """
    },
    {
        "title": "Designing Premium User Interfaces: Micro-Animations, Glassmorphism, and Modern CSS",
        "seo_description": "Explore state-of-the-art UI design techniques, smooth CSS transitions, dark mode palettes, and accessibility compliance.",
        "category": "UI/UX Design",
        "tags": ["UI/UX Design"],
        "views": 3890,
        "likes": 295,
        "featured": False,
        "content": """
        <h2>Creating WOW-factor User Experiences</h2>
        <p>Modern design is defined by subtle micro-interactions, responsive spatial typography, and harmonious translucent visual layers.</p>

        <h2>Design System Best Practices</h2>
        <p>Utilizing CSS custom properties, system dark-mode tokens, and hardware-accelerated transforms enables web applications to deliver fluid 60fps animations without sacrificing battery life or responsiveness.</p>
        """
    },
    {
        "title": "2026 Enterprise Engineering Readiness Benchmark Report",
        "seo_description": "Download our comprehensive 42-page industry report analyzing cloud maturity, DevOps velocity, and platform engineering trends.",
        "category": "Cloud Engineering",
        "tags": ["Cloud Engineering", "DevOps & CI/CD"],
        "views": 6400,
        "likes": 510,
        "featured": True,
        "is_resource": True,
        "resource_type": "document",
        "download_count": 890,
        "content": """
        <h2>About the Report</h2>
        <p>The 2026 Enterprise Engineering Readiness Report benchmarks 250+ engineering organizations across cloud infrastructure adoption, release frequency, security automation, and developer experience productivity.</p>
        <p><strong>Key Highlights:</strong></p>
        <ul>
            <li>84% of high-performing teams have adopted automated serverless deployment pipelines.</li>
            <li>Mean Time to Recovery (MTTR) dropped by 45% in teams utilizing continuous observability platforms.</li>
            <li>Detailed architecture blueprints and transition roadmaps included inside.</li>
        </ul>
        """
    }
]

for item in articles_data:
    art, created = Article.objects.get_or_create(
        title=item["title"],
        defaults={
            "content": item["content"],
            "seo_description": item["seo_description"],
            "category": item["category"],
            "views": item["views"],
            "likes": item["likes"],
            "featured": item["featured"],
            "status": "published",
            "author": admin_profile,
            "user": admin_user,
            "is_resource": item.get("is_resource", False),
            "resource_type": item.get("resource_type", "document"),
        }
    )
    for tag_name in item["tags"]:
        if tag_name in tags_dict:
            art.tags.add(tags_dict[tag_name])
    art.save()
    print(f"Article '{art.title[:40]}...' -> {'Created' if created else 'Updated'}")

# ---------------------------------------------------------
# 3. SHOP CATEGORIES & PRODUCTS
# ---------------------------------------------------------
cat_cloud, _ = ShopCategory.objects.get_or_create(
    name="Cloud Engineering & Services",
    defaults={"description": "Managed cloud services, serverless infrastructure, and DevOps architecture."}
)
cat_software, _ = ShopCategory.objects.get_or_create(
    name="Software Toolkits & Licenses",
    defaults={"description": "Developer tools, pre-built enterprise software modules, and templates."}
)

products_data = [
    {
        "name": "Dovetec Pro Developer Toolkit",
        "category": cat_software,
        "price": "49.00",
        "stock": 100,
        "description": "Comprehensive starter toolkit featuring production-grade Django, Next.js, and Terraform templates for rapid application deployment."
    },
    {
        "name": "Enterprise Cloud Architecture Audit",
        "category": cat_cloud,
        "price": "499.00",
        "stock": 15,
        "description": "Full end-to-end security, reliability, and cost-optimization assessment of your cloud infrastructure by senior cloud architects."
    },
    {
        "name": "DevOps Continuous Integration Suite",
        "category": cat_cloud,
        "price": "199.00",
        "stock": 50,
        "description": "Pre-configured CI/CD pipeline modules with automated security scanning, OIDC cloud authorization, and automated regression testing."
    }
]

for pdata in products_data:
    p, created = Product.objects.get_or_create(
        name=pdata["name"],
        defaults={
            "category": pdata["category"],
            "price": pdata["price"],
            "stock": pdata["stock"],
            "description": pdata["description"],
        }
    )
    print(f"Product '{p.name}' -> {'Created' if created else 'Updated'}")

# ---------------------------------------------------------
# 4. ENRICHED CASE STUDIES (Apple Storytelling Design)
# ---------------------------------------------------------
case_studies_data = [
    {
        "name": "PayPulse Africa",
        "tagline": "Scaling Cross-Border Digital Payments for 500,000+ Active Merchants",
        "description": "PayPulse Africa needed a high-availability settlement engine capable of processing millions of daily transactions with zero downtime and sub-second latency.",
        "overview": "We transformed PayPulse's legacy payment system into an event-driven serverless architecture on PostgreSQL and Redis, delivering 99.99% uptime and handling peak peak holiday traffic seamlessly.",
        "status": CaseStudy.STATUS_PUBLISHED,
        "category": cat_cloud,
        "featured": True,
        "accent_color": "#0071e3",
        "primary_color": "#1d1d1f",
        "secondary_color": "#5856d6",
        "bg_color": "#ffffff",
        "bg_secondary_color": "#f5f5f7",
        "problem_statement": "Legacy monolithic payment processing caused recurring timeout errors during regional peak shopping surges, leading to lost transactions and merchant churn.",
        "objectives": "1. Achieve sub-second transaction processing latency.\n2. Scale seamlessly to support 50,000 requests per minute.\n3. Implement automated PCI-DSS compliance logging and auditing.",
        "business_challenge": "Integrating multiple regional bank gateways with varying API formats and reliability metrics while ensuring absolute transactional idempotency.",
        "research_findings": "94% of payment drop-offs were directly correlated with latency spikes exceeding 3 seconds during gateway handshake authentication.",
        "user_needs": "Merchants needed instantaneous transaction verification feedback and real-time dashboard analytics across web and mobile interfaces.",
        "features": "• Real-time payment processing webhook handler\n• Automated reconciliation ledger\n• Multi-currency dynamic rate calculation engine\n• Granular merchant permissions dashboard",
        "unique_features": "Self-healing failover gateway routing that dynamically switches transaction paths if a regional bank endpoint drops below 98% success rates.",
        "major_screens": "Merchant Settlement Dashboard, Live Webhook Monitor, Analytics & Revenue Insights"
    },
    {
        "name": "Agridoer Marketplace",
        "tagline": "Empowering 30,000+ Farmers with Real-Time Direct Marketplace Access",
        "description": "Agridoer replaced an inefficient multi-tier distributor broker network with a direct B2B mobile and web marketplace.",
        "overview": "By engineering an offline-first mobile web application, Agridoer enabled smallholder farmers in rural regions to list produce, receive bids, and coordinate transport directly with commercial buyers.",
        "status": CaseStudy.STATUS_PUBLISHED,
        "category": cat_cloud,
        "featured": True,
        "accent_color": "#34c759",
        "primary_color": "#1c1c1e",
        "secondary_color": "#30b0c7",
        "bg_color": "#ffffff",
        "bg_secondary_color": "#f2f2f7",
        "problem_statement": "Farmers suffered up to 40% crop spoilage due to delayed market price discovery and inefficient logistics dispatch coordination.",
        "objectives": "1. Connect farmers directly with verified wholesale buyers.\n2. Deliver offline SMS/USSD sync capability for low-connectivity regions.\n3. Build an automated route optimization model for crop collection trucks.",
        "business_challenge": "Designing an accessible UI for users with limited smartphone literacy while maintaining high security for escrow payments.",
        "research_findings": "78% of smallholder farmers used basic Android hardware with limited data subscriptions, requiring extreme lightweight asset optimization.",
        "user_needs": "Simple voice/icon-based crop listing workflows and instant M-Pesa/mobile money payout confirmations.",
        "features": "• Low-bandwidth image compression and listing creator\n• Instant mobile money payout integration\n• Geo-tagged collection point logistics tracker",
        "unique_features": "Dynamic price matching algorithm leveraging historical yield data and regional demand forecasts to ensure fair pricing for farmers.",
        "major_screens": "Produce Listing Creation, Live Bidding Terminal, Logistics Route Manager"
    },
    {
        "name": "HealthFlow EHR Platform",
        "tagline": "Streamlining Clinical Workflows Across 120+ Healthcare Centers",
        "description": "HealthFlow modernised medical record management and patient diagnostics across a regional network of clinics.",
        "overview": "We architected a HIPAA/GDPR-compliant SaaS platform with encrypted medical record storage, automated appointment scheduling, and remote telemetry integration.",
        "status": CaseStudy.STATUS_PUBLISHED,
        "category": cat_cloud,
        "featured": True,
        "accent_color": "#ff2d55",
        "primary_color": "#000000",
        "secondary_color": "#af52de",
        "bg_color": "#ffffff",
        "bg_secondary_color": "#f8f9fa",
        "problem_statement": "Paper-based medical charts caused treatment delays, duplicate diagnostic tests, and fragmented patient medical histories across clinic locations.",
        "objectives": "1. Unify patient diagnostic history into a central secure repository.\n2. Reduce clinic check-in wait times by 50%.\n3. Enable instant telemetry sync from diagnostic devices.",
        "business_challenge": "Ensuring strict end-to-end field-level encryption for sensitive patient data without sacrificing query search performance.",
        "research_findings": "Nurses spent up to 3 hours per shift manually transcribe patient vitals into legacy workstation software.",
        "user_needs": "One-click chart lookup, fast prescription generation, and automated patient SMS appointment reminders.",
        "features": "• Encrypted EHR chart builder\n• Telemedicine video consultation hub\n• Automated e-Prescription pharmacy dispatch",
        "unique_features": "Real-time vital signs streaming via Bluetooth Low Energy (BLE) medical monitor synchronization.",
        "major_screens": "Clinical Patient Chart, Doctor Consultation Workspace, Pharmacy Dispatch Queue"
    },
    {
        "name": "EduNexus Adaptive AI",
        "tagline": "Personalized Higher Education Learning Paths for 100,000+ Students",
        "description": "EduNexus delivers adaptive learning recommendations and automated grading for university courses.",
        "overview": "Using automated knowledge graphing and student engagement analytics, EduNexus tailors course materials to individual student progress speeds and learning preferences.",
        "status": CaseStudy.STATUS_PUBLISHED,
        "category": cat_cloud,
        "featured": True,
        "accent_color": "#ff9500",
        "primary_color": "#1d1d1f",
        "secondary_color": "#5856d6",
        "bg_color": "#ffffff",
        "bg_secondary_color": "#f5f5f7",
        "problem_statement": "Standardized lecture paces caused high dropout rates in foundational STEM courses due to unaddressed concept gaps.",
        "objectives": "1. Increase course completion rates by 35%.\n2. Provide real-time struggle notifications to course instructors.\n3. Generate dynamic study plans tailored to knowledge gaps.",
        "business_challenge": "Scaling vector embeddings and real-time recommendation engines for concurrent exam periods with 80,000+ active students.",
        "research_findings": "Students who received targeted micro-assessments within 10 minutes of a concept struggle scored 28% higher in final evaluations.",
        "user_needs": "Distraction-free reading views, interactive code playbooks, and instant feedback on practice exercises.",
        "features": "• Adaptive quiz & assessment generator\n• Real-time student mastery heatmap\n• Interactive code sandbox for technical assignments",
        "unique_features": "AI learning assistant that provides instant hint guides without giving away direct answers.",
        "major_screens": "Student Learning Command Center, Instructor Analytics Portal, Interactive Code Lab"
    }
]

for cs_data in case_studies_data:
    cs, created = CaseStudy.objects.get_or_create(
        name=cs_data["name"],
        defaults={
            "tagline": cs_data["tagline"],
            "description": cs_data["description"],
            "overview": cs_data["overview"],
            "status": cs_data["status"],
            "category": cs_data["category"],
            "featured": cs_data["featured"],
            "accent_color": cs_data["accent_color"],
            "primary_color": cs_data["primary_color"],
            "secondary_color": cs_data["secondary_color"],
            "bg_color": cs_data["bg_color"],
            "bg_secondary_color": cs_data["bg_secondary_color"],
            "problem_statement": cs_data["problem_statement"],
            "objectives": cs_data["objectives"],
            "business_challenge": cs_data["business_challenge"],
            "research_findings": cs_data["research_findings"],
            "user_needs": cs_data["user_needs"],
            "features": cs_data["features"],
            "unique_features": cs_data["unique_features"],
            "major_screens": cs_data["major_screens"],
            "published_at": timezone.now(),
        }
    )
    print(f"Case Study '{cs.name}' -> {'Created' if created else 'Updated'}")

# ---------------------------------------------------------
# 5. DEPARTMENTS & JOBS
# ---------------------------------------------------------
dept_eng, _ = Department.objects.get_or_create(
    name="Engineering & Infrastructure",
    defaults={"description": "Core software architecture, DevOps, and cloud systems."}
)
dept_design, _ = Department.objects.get_or_create(
    name="Product & UI/UX Design",
    defaults={"description": "User experience, design systems, and product research."}
)

jobs_data = [
    {
        "title": "Senior Full-Stack Engineer (Django & React)",
        "location": "Nairobi / Remote",
        "company": "Dovetec Enterprises",
        "salary": "120000.00",
        "level": "Senior",
        "department": dept_eng,
        "employment_type": "Full-time",
        "description": "<p>We are seeking an experienced Full-Stack Engineer to architect scalable cloud applications and Django systems.</p>"
    },
    {
        "title": "Lead Cloud DevOps & Security Engineer",
        "location": "Remote",
        "company": "Dovetec Enterprises",
        "salary": "140000.00",
        "level": "Lead",
        "department": dept_eng,
        "employment_type": "Full-time",
        "description": "<p>Lead our cloud infrastructure automation, Kubernetes orchestration, and zero-trust security architecture.</p>"
    },
    {
        "title": "Product UX/UI Designer",
        "location": "Hybrid / Nairobi",
        "company": "Dovetec Enterprises",
        "salary": "95000.00",
        "level": "Mid-Senior",
        "department": dept_design,
        "employment_type": "Full-time",
        "description": "<p>Create beautiful, accessible, Apple-inspired interface systems and case study storytelling interactions.</p>"
    }
]

for jdata in jobs_data:
    j, created = Job.objects.get_or_create(
        title=jdata["title"],
        defaults={
            "location": jdata["location"],
            "company": jdata["company"],
            "salary": jdata["salary"],
            "level": jdata["level"],
            "department": jdata["department"],
            "employment_type": jdata["employment_type"],
            "description": jdata["description"],
            "is_active": True,
        }
    )
    print(f"Job Opening '{j.title}' -> {'Created' if created else 'Updated'}")

print("\n=======================================================")
print("LIVE DATA SEEDING COMPLETED SUCCESSFULLY!")
print("=======================================================")
