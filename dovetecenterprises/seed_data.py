"""Domain vocabulary for Dovetec Enterprises.

Everything the seeder writes is drawn from here so the dummy data reads like
it belongs to this business: Nairobi-based software engineering, IT solutions
and consulting, serving East African industry verticals.
"""

# ── Service lines (map to app.models.ServiceInquiry.SERVICE_CHOICES) ──
SERVICE_LINES = {
    "software": "Software Engineering",
    "it": "IT Solutions",
    "consulting": "Consulting Services",
    "other": "Other",
}

# ── Industry verticals (mirror app.models.INDUSTRY_CHOICES) ──
# slug -> (label, typical client, flagship concern, delivery focus)
INDUSTRIES = {
    "fintech": {
        "label": "Fintech & Banking",
        "client": "Harambee Sacco Union",
        "concern": "Mobile-first loan origination with offline-first disbursement for members in low-connectivity counties.",
        "focus": "Android money app, core banking integration, USSD fallbacks, audit trails.",
    },
    "health": {
        "label": "Healthcare & Life Sciences",
        "client": "Jamii Health Network",
        "concern": "Patient records that stay available on intermittent connectivity across 38 facilities.",
        "focus": "FHIR-aligned records, offline sync, role-based access, consent management.",
    },
    "education": {
        "label": "Education & EdTech",
        "client": "TechDarasa",
        "concern": "Course delivery and fee collection for schools running on shared devices and low bandwidth.",
        "focus": "LMS, adaptive assessments, M-Pesa fee integration, teacher dashboards.",
    },
    "retail": {
        "label": "Retail & E-commerce",
        "client": "Oddibites",
        "concern": "Growing from a single till to multi-branch retail without losing margin visibility.",
        "focus": "Point of sale, inventory sync, headless storefront, campaign analytics.",
    },
    "manufacturing": {
        "label": "Manufacturing & Logistics",
        "client": "Savannah Freight Forwarders",
        "concern": "Fleet and consignment visibility across the Nairobi–Mombasa–Kisumu corridor.",
        "focus": "Route optimisation, telematics ingestion, warehouse scanning, exception alerts.",
    },
    "agriculture": {
        "label": "Agriculture & AgriTech",
        "client": "Agridoer",
        "concern": "Connecting smallholder farmers to buyers with verified produce and fair pricing.",
        "focus": "Marketplace, aggregation logistics, farm records, M-Pesa payouts.",
    },
    "telecom": {
        "label": "Telecommunications",
        "client": "Coastal Networks Limited",
        "concern": "Network assurance tooling and self-service diagnostics for field technicians.",
        "focus": "OSS integration, telemetry pipelines, self-service portals.",
    },
    "energy": {
        "label": "Energy & Utilities",
        "client": "Rift Solar Collective",
        "concern": "Metering data ingestion and outage prediction across off-grid installations.",
        "focus": "Telemetry ingestion, time-series storage, predictive maintenance.",
    },
    "government": {
        "label": "Government & Public Sector",
        "client": "County Government of Nakuru",
        "concern": "Citizen service portals that remain usable and accessible on shared devices.",
        "focus": "Identity verification, workflow automation, accessibility, audit reporting.",
    },
    "ngo": {
        "label": "NGO & Development",
        "client": "Pamoja Health Initiative",
        "concern": "Field programme monitoring and donor reporting without bespoke spreadsheets.",
        "focus": "Offline data capture, grant dashboards, beneficiary deduplication.",
    },
    "real_estate": {
        "label": "Real Estate & Construction",
        "client": "Savannah Properties",
        "concern": "Project pipeline visibility and client portal communication at scale.",
        "focus": "CRM, project tracking, document workflows, virtual walkthroughs.",
    },
    "hospitality": {
        "label": "Hospitality & Tourism",
        "client": "Kijani Lodges",
        "concern": "Direct bookings and guest experience without heavy OTA commission.",
        "focus": "Booking engine, channel manager, guest CRM, revenue reporting.",
    },
    "media": {
        "label": "Media & Entertainment",
        "client": "TechDarasa Media",
        "concern": "Audience monetisation and content distribution across channels.",
        "focus": "Video delivery, subscription billing, content management, analytics.",
    },
    "transport": {
        "label": "Transport & Mobility",
        "client": "Swahili Express",
        "concern": "Dispatch, rider earnings and vehicle utilisation for a growing fleet.",
        "focus": "Dispatch engine, driver app, settlement, route analytics.",
    },
    "other": {
        "label": "Cross-industry",
        "client": "Dovetec Internal",
        "concern": "Delivery capability baselines for new business lines.",
        "focus": "Discovery, architecture, delivery governance.",
    },
}

# ── Capability tags for shop.Category (rendered as newsletter "services") ──
CAPABILITIES = {
    "Custom Software Engineering": "Product and platform engineering in Python, Django and TypeScript.",
    "Mobile App Development": "Native and cross-platform mobile apps with intuitive user experiences.",
    "Web Application Development": "Responsive, scalable web applications built with modern frameworks.",
    "Cloud & Infrastructure Engineering": "Cloud migration, managed infrastructure, CI/CD and observability.",
    "UI/UX Research and Design": "Interface design grounded in user research and usability testing.",
    "Quality Assurance & Testing": "Automated and manual test strategy, performance and security testing.",
    "System Administration": "Reliable runtimes, patching, backups and incident response.",
    "Data & Analytics Engineering": "Pipelines, reporting layers and decision-grade dashboards.",
    "IT Consulting & Advisory": "Architecture review, tooling selection and delivery governance.",
    "Cybersecurity & Hardening": "Threat modelling, access control, and secure-by-default delivery.",
    "Business Process Automation": "Streamlining business processes through technology enablement.",
    "Technical Support & Maintenance": "Responsive technical support and proactive maintenance services.",
    "Project Management": "Planning, risk control and transparent delivery reporting.",
    "API & Integrations": "Third-party, payments and legacy system integration work.",
    "Training & Developer Enablement": "User training and engineering capability transfer.",
}

# ── Productised offerings (shop.Product) ──
PRODUCTS = {
    "Dovetec Deployment Toolkit": {
        "category": "Cloud & Infrastructure Engineering",
        "price": "149000.00",
        "stock": 40,
        "description": "Repeatable Django deployment pipeline: CI/CD, environment parity, zero-downtime releases and rollback.",
    },
    "AfriLedger Core": {
        "category": "Custom Software Engineering",
        "price": "425000.00",
        "stock": 15,
        "description": "Double-entry ledger and reconciliation engine for SACCOs and microfinance institutions.",
    },
    "FieldSync Mobile Kit": {
        "category": "Mobile App Development",
        "price": "285000.00",
        "stock": 20,
        "description": "Offline-first data capture kit for field teams working on unreliable connectivity.",
    },
    "InsightBoard Analytics": {
        "category": "Data & Analytics Engineering",
        "price": "199000.00",
        "stock": 25,
        "description": "Turnkey reporting layer with scheduled exports, dashboards and role-scoped metrics.",
    },
    "Sentinel Secure Baseline": {
        "category": "Cybersecurity & Hardening",
        "price": "175000.00",
        "stock": 30,
        "description": "Security hardening engagement covering threat modelling, access control and secure defaults.",
    },
    "SupportCare Retainer": {
        "category": "Technical Support & Maintenance",
        "price": "65000.00",
        "stock": 100,
        "description": "Monthly managed support retainer with defined response times and monthly engineering reports.",
    },
}

# ── Editorial content (home.Tag / home.Article / is_resource articles) ──
ARTICLES = [
    {
        "title": "Designing offline-first field data capture for East African programmes",
        "tag": "Mobile Engineering",
        "resource_type": "guide",
        "author": "Dove",
        "excerpt": "Connectivity assumptions break the moment a field team enters a low-signal county. Here is the sync architecture we standardise on.",
        "content": "<p>Field teams across Kenya, Uganda and Tanzania routinely work in areas where a single HTTP request can take forty seconds or simply never return. Any architecture that assumes a reliable connection will fail its users in exactly the places that need the data most.</p><h2>Start from the write path, not the network</h2><p>We design local-first. The device writes to local storage as the system of record, and synchronisation is a separate, retryable concern. Every mutation carries a client-generated identifier so a retried write is idempotent rather than duplicated.</p><h2>Conflict resolution that field teams can explain</h2><p>Last-write-wins is acceptable for sensor readings and unacceptable for inventory adjustments. We keep an append-only operation log and reconcile per field, surfacing genuine conflicts to a supervisor rather than silently picking a winner.</p><h2>Observability for offline systems</h2><p>Queue depth, sync latency and conflict rate are the metrics that matter. We alert on sync age rather than error rate, because a system can report zero errors while quietly falling days behind.</p>",
        "featured": True,
    },
    {
        "title": "What we learned migrating a monolith to an event-driven core",
        "tag": "Architecture",
        "resource_type": "document",
        "author": "admin",
        "excerpt": "An incremental strangler-fig migration, the events that carried the domain, and the two things we would do differently.",
        "content": "<p>Most rewrites fail because they attempt a big-bang cutover. The Agridoer marketplace rebuild took eleven months and we never had a single day of downtime, because we extracted one bounded context at a time and ran both systems in parallel until the new path was proven.</p><h2>Extract by business capability, not by table</h2><p>Table-by-table extraction produces a distributed monolith. We chose capabilities with clear seams: catalogue, ordering, fulfilment, settlement. Each became a service with its own data ownership.</p><h2>Events are a contract</h2><p>Every event carried a schema version from day one. We rejected two event changes outright because consumers had already shipped, which is a cost we accepted in exchange for not breaking partner integrations.</p><h2>What we would do differently</h2><p>We underinvested in reconciliation tooling early, and paid for it during the first month of parallel running. Build the reconciliation dashboard before you need it.</p>",
        "featured": True,
    },
    {
        "title": "Integrating M-Pesa without coupling your domain to Safaricom",
        "tag": "Payments",
        "resource_type": "guide",
        "author": "admin2",
        "excerpt": "A payments abstraction that lets us swap providers, and the callback-verification mistakes that cause double credits.",
        "content": "<p>Tying your credit or order model directly to a M-Pesa call response is the most common integration mistake we inherit. It works until you need a second provider, a sandbox, or a reconciliation report that does not require a STK push log.</p><h2>Model the intent, not the callback</h2><p>We record a payment intent with our own reference, then treat the STK callback as a state transition on that intent. A duplicate callback is therefore harmless by construction.</p><h2>Verify callbacks properly</h2><p>Verification is not optional. The callback must carry the amount and account we initiated against, and both must match our record. A callback that passes the secret alone is not sufficient evidence.</p><h2>Reconciliation is a product feature</h2><p>Daily automated reconciliation against settlement reports catches drift within a day rather than at month end. Finance teams notice immediately when the numbers stop agreeing.</p>",
        "featured": False,
    },
    {
        "title": "Accessibility as an engineering constraint, not an audit finding",
        "tag": "Engineering Practice",
        "resource_type": "article",
        "author": "admin",
        "excerpt": "Public-sector and banking clients increasingly require WCAG conformance. Treating it as a build constraint is cheaper than treating it as a defect.",
        "content": "<p>Accessibility remediation after launch is dramatically more expensive than building it in. Keyboard navigation, focus order, contrast and screen-reader labelling are cheap during component construction and expensive once markup is baked into templates and email clients.</p><h2>Start with the component library</h2><p>We enforce focus visibility, semantic elements and labelling in our shared component primitives. Individual pages then inherit conformance by default rather than by review.</p><h2>Test the way users do</h2><p>Automated checks catch perhaps a third of real issues. The rest need keyboard-only and screen-reader passes, and for shared-device or low-end Android contexts we test on the hardware our users actually hold.</p>",
        "featured": False,
    },
    {
        "title": "Cost control for high-volume messaging on constrained budgets",
        "tag": "Cloud & Infrastructure",
        "resource_type": "article",
        "author": "Dove",
        "excerpt": "Queue depth, batching and idempotency are usually cheaper than negotiating a better per-message price.",
        "content": "<p>Clients running high-volume transactional messaging consistently over-budget by optimising the wrong layer. Provider unit price attracts attention; the actual multiplier is how many messages you send per meaningful event.</p><h2>Deduplicate at the boundary</h2><p>Retries and webhooks are the usual source of volume inflation. Idempotency keys at the queue boundary typically cut message volume by a third before any provider negotiation.</p><h2>Batch where the channel allows</h2><p>Notices that do not require immediate delivery can be batched on a schedule, which changes the cost profile materially under per-batch pricing.</p>",
        "featured": False,
    },
]

RESOURCES = [
    {
        "title": "2026 Engineering Readiness Report",
        "tag": "Research",
        "resource_type": "document",
        "author": "admin2",
        "excerpt": "Our annual assessment of delivery, security and infrastructure practice across 40 engagements.",
        "content": "<p>The 2026 Engineering Readiness Report distils patterns from forty engagements across financial services, healthcare, education, agriculture and the public sector.</p><h2>What we measured</h2><p>Delivery predictability, defect escape rate, time to restore, infrastructure toil and accessibility conformance across the engagements we ran this year.</p><h2>Headline findings</h2><p>Teams that invested in automated regression coverage in the first quarter shipped measurably more predictably in the second half. Teams that deferred observability paid for it during their first major incident, not during delivery.</p><h2>How to use this report</h2><p>Use the maturity bands in the appendix to locate your current position, then treat the gap list as a candidate roadmap for the next two quarters.</p>",
        "featured": True,
    },
    {
        "title": "Legacy System Assessment Playbook",
        "tag": "Research",
        "resource_type": "template",
        "author": "admin",
        "excerpt": "The structured assessment we run before quoting any modernisation or migration engagement.",
        "content": "<p>This playbook is the assessment we run before quoting modernisation work. It is deliberately short: two weeks, fixed scope, fixed questions.</p><h2>Week one: system and data</h2><p>Map the actual runtime topology rather than the documented one, identify the systems of record, and quantify the data that would need to move.</p><h2>Week two: risk and options</h2><p>Rank the findings by delivery risk, and present at least three options with explicit trade-offs rather than a single recommendation.</p><h2>Deliverable</h2><p>A written assessment with a risk register, a phased roadmap and a defensible cost range.</p>",
        "featured": False,
    },
    {
        "title": "Cloud Cost Optimisation Checklist",
        "tag": "Cloud & Infrastructure",
        "resource_type": "template",
        "author": "Dove",
        "excerpt": "The ordered checklist we use to reduce cloud spend without degrading reliability or developer velocity.",
        "content": "<p>Most cloud overspend is structural rather than exotic. This checklist orders the work by impact and risk so you stop the bleeding before starting the optimisation project.</p><h2>Order of operations</h2><ol><li>Right-size consistently over-provisioned compute and databases.</li><li>Eliminate idle and unattached storage.</li><li>Add budgets and anomaly alerts so regressions are visible immediately.</li><li>Commit to reserved capacity only once utilisation is stable.</li><li>Review data transfer and egress, which is frequently the largest surprise.</li></ol><h2>Guardrails</h2><p>Change production infrastructure through infrastructure-as-code with review. Cost work should not become an availability risk.</p>",
        "featured": False,
    },
]

TAGS = [
    "Architecture", "Mobile Engineering", "Cloud & Infrastructure", "Payments",
    "Engineering Practice", "Research", "Security", "Data Engineering",
    "Accessibility", "DevOps",
]

# ── Case studies (app.models.CaseStudy) ──
CASE_STUDIES = [
    {
        "name": "Agridoer",
        "industry": "agriculture",
        "category": "Custom Software Engineering",
        "tagline": "From 3 to 30,000 monthly buyers on a rebuild we never took offline.",
        "description": "We rebuilt an agricultural marketplace onto an event-driven core, taking monthly buyers from roughly 3,000 to 30,000 without a single day of downtime.",
        "overview": "Agridoer connects smallholder farmers to commercial buyers. The original platform was a monolith that stalled under seasonal load, and every release was a high-stakes event. We migrated capability by capability behind a strangler-fig facade while both systems ran in parallel, reconciling orders continuously until the new path was proven.",
        "problem_statement": "The platform took over forty seconds to load at peak harvest, and the checkout path timed out for a large share of mobile users. Every change to the monolith required a full regression pass, so fixes shipped slowly and defects accumulated.",
        "objectives": "Stabilise order capture during seasonal peaks, cut page load times below two seconds, and allow weekly releases without a dedicated regression team.",
        "business_challenge": "Growth had outpaced the platform. Three planned farm partnerships depended on bulk ordering that the monolith could not serve, and competitors were onboarding buyers faster.",
        "research_findings": "Interviews with 26 farmers and 11 buyers showed that offline order capture mattered more than catalogue browsing: the network is weakest exactly where orders are created.",
        "user_needs": "Fast order capture on low-end Android, clear pricing and quality signals, and reliable payment confirmation even on intermittent connections.",
        "features": "Offline-first order capture, an event-driven order and settlement core, a public catalogue API, and a daily reconciliation dashboard used by finance.",
        "user_challenges": "Farmers use shared devices and shared SIMs, and were previously double-submitting orders when a slow response left them unsure whether the request had succeeded.",
        "competitor_data": "Three regional marketplaces were compared on catalogue breadth, logistics coverage and take rate. Agridoer competes on verified produce quality rather than catalogue size.",
        "unique_features": "Client-generated idempotency keys on every order, an append-only audit log shared with buyers, and automated daily reconciliation against settlement reports.",
        "root_cause": "The monolith coupled order capture, inventory and settlement in a single transaction path, so a slow dependency in any layer blocked checkout for everyone.",
        "task_flows": "Browse catalogue, capture order offline, sync when connected, confirm payment, settle on delivery.",
        "featured": True,
    },
    {
        "name": "TechDarasa",
        "industry": "education",
        "category": "Web Application Development",
        "tagline": "A learning platform reaching 180,000 students on school bandwidth.",
        "description": "We built the course delivery, assessment and fee collection platform behind TechDarasa, designed around the connectivity and device reality of Kenyan secondary schools.",
        "overview": "TechDarasa delivers curriculum-aligned courses to secondary schools. Our scope covered the learner application, teacher dashboards, adaptive assessment and M-Pesa fee collection, with an architecture built for shared devices and intermittent connectivity.",
        "problem_statement": "Course material was distributed as downloads, so teachers had no visibility into completion, and fee collection ran through manual reconciliation that consumed several days each term.",
        "objectives": "Deliver courses on devices costing less than the school's budget, track learner progress reliably, and automate fee reconciliation.",
        "business_challenge": "Schools needed reporting at term-end within days of classes finishing, and the previous paper-based process meant results arrived weeks after the teaching they described.",
        "research_findings": "Classroom observation across 14 schools showed a median of four learners sharing one device, making session persistence and resumable progress essential rather than optional.",
        "user_needs": "Resumable lessons on shared devices, assessments that survive a dropped connection, and fee statements parents can trust.",
        "features": "Resumable course player, offline assessment sync, teacher progress dashboards, and M-Pesa fee collection with automated reconciliation.",
        "user_challenges": "Learners share devices between siblings and classmates, so progress was frequently lost between sessions without a durable server-side checkpoint.",
        "competitor_data": "We benchmarked three education platforms on offline capability and device cost. None met the sub-KES 15,000 device class at full feature parity.",
        "unique_features": "Offline assessment sync with idempotent submission, server-side session checkpoints keyed to learner identity rather than device.",
        "root_cause": "Prior delivery assumed reliable connectivity and personal devices, neither of which held in the target classroom environment.",
        "task_flows": "Enrol, download lesson, learn offline, submit assessment, track progress, pay fees.",
        "featured": True,
    },
    {
        "name": "Harambee Sacco Union",
        "industry": "fintech",
        "category": "Custom Software Engineering",
        "tagline": "Loan origination that works where the network does not.",
        "description": "We designed and built mobile-first loan origination with offline disbursement for a SACCO union operating across low-connectivity counties.",
        "overview": "Harambee Sacco Union needed lending operations staff to originate and disburse loans in counties where connectivity is intermittent. We built a field officer application with offline disbursement, integrated with the union's core banking system through an auditable synchronisation layer.",
        "problem_statement": "Field officers travelled hours to reach a branch to originate loans, and disbursements failed silently when the network dropped, leaving reconciliation to be reconstructed by hand at month end.",
        "objectives": "Enable loan origination in the field, guarantee disbursement is never duplicated, and produce audit-ready transaction records.",
        "business_challenge": "Expanding into new counties was limited by branch capacity, and manual reconciliation meant management could not see portfolio health without a month-end delay.",
        "research_findings": "Field shadowing across four counties found that origination was the bottleneck, not underwriting: officers spent more time travelling than assessing.",
        "user_needs": "Fast origination with clear validation, guaranteed-once disbursement, and an audit trail an external auditor would accept.",
        "features": "Offline origination with a device-side approval queue, idempotent disbursement, USSD fallback for confirmation, and a core banking synchronisation adapter.",
        "user_challenges": "Officers worked long distances on unreliable handsets, and a failed disbursement was often indistinguishable from a successful one until reconciliation.",
        "competitor_data": "We compared three field-lending tools on offline capability and audit support. Competitor products assumed connectivity and offered no offline disbursement guarantee.",
        "unique_features": "Device-side approval queue with cryptographic audit logging, and an idempotency key that survives device replacement.",
        "root_cause": "Origination required a live core banking round trip, so the workflow inherited the network's worst-case latency and failure mode.",
        "task_flows": "Register member, assess, approve, disburse, confirm, reconcile.",
        "featured": True,
    },
    {
        "name": "Oddibites",
        "industry": "retail",
        "category": "Business Process Automation",
        "tagline": "Multi-branch retail with margin visibility they had never had.",
        "description": "We delivered point of sale, inventory synchronisation and a headless storefront for a growing food retailer, giving branch managers live margin visibility.",
        "overview": "Oddibites operates a growing food retail network. We unified point of sale across branches, replaced nightly stock reconciliation with live synchronisation, and built a storefront that let the business sell direct without a heavy platform dependency.",
        "problem_statement": "Each branch tracked stock independently, so group-level availability was wrong by the end of every day and shrinkage surfaced only at stocktake.",
        "objectives": "Live inventory across branches, faster checkout, and per-branch margin reporting without manual spreadsheet work.",
        "business_challenge": "Expansion to new branches was slowing because onboarding a location meant reproducing manual processes and training staff on bespoke workflows.",
        "research_findings": "Store visits across five branches showed staff spending 40 to 90 minutes per day on end-of-day stock counts, with the resulting figures rarely used for decisions.",
        "user_needs": "Fast checkout that works on a flaky connection, and a stock figure they can trust without a stocktake.",
        "features": "Offline-tolerant point of sale, live multi-branch inventory, a headless storefront, and automated shrinkage reporting.",
        "user_challenges": "Branch staff treated end-of-day counts as unavoidable paperwork; the previous system gave them no reason to believe anything else was possible.",
        "competitor_data": "We evaluated three retail platforms on multi-branch support and offline checkout. The lowest-cost option required a per-branch subscription that removed margin at their store count.",
        "unique_features": "Offline-tolerant checkout with a reconciliation queue, and per-branch gross margin reporting that surfaced shrinkage the same week it occurred.",
        "root_cause": "Inventory was tracked as a nightly snapshot per branch rather than a continuously reconciled ledger.",
        "task_flows": "Sell in store, sync stock, replenish, report margin, restock centrally.",
        "featured": False,
    },
    {
        "name": "Savannah Freight Forwarders",
        "industry": "manufacturing",
        "category": "Data & Analytics Engineering",
        "tagline": "Consignment visibility across the western corridor.",
        "description": "We built telematics ingestion, route planning and exception alerting for a freight forwarder running the Nairobi to Kisumu and Mombasa corridors.",
        "overview": "Savannah Freight Forwarders needed to know where consignments were and when they would arrive. We built a telematics ingestion pipeline, route planning for multi-stop collections, and exception alerting for delays that customers would otherwise discover for themselves.",
        "problem_statement": "Dispatch relied on phone calls between drivers and dispatchers, and customers learned about delays after the promised delivery window had already passed.",
        "objectives": "Live consignment visibility, earlier exception detection, and accurate arrival estimates for customer commitments.",
        "business_challenge": "Growing volumes made manual dispatch unworkable, and the penalties for late delivery were eroding margin on long-haul contracts.",
        "research_findings": "Dispatch interviews found that most of the working day went to chasing status rather than planning loads, and arrival estimates were given as ranges because drivers reported them verbally.",
        "user_needs": "A single view of every consignment, alerts before a customer complains, and load planning that accounts for return capacity.",
        "features": "Telematics ingestion pipeline, multi-stop route planning, exception alerting against promised windows, and customer-facing consignment tracking.",
        "user_challenges": "Drivers had no reliable way to confirm a delivery when they arrived, causing long delays reconciling paperwork at the depot.",
        "competitor_data": "We compared three fleet platforms on telematics integration and exception alerting. Cheaper options supported tracking but not the alerting our contracts required.",
        "unique_features": "Exception alerting against the promised delivery window rather than a fixed threshold, and offline driver confirmation that syncs on return.",
        "root_cause": "Consignment status lived in phone calls, so it was never structured, never queryable and never available to the systems that needed it.",
        "task_flows": "Plan load, dispatch, track, confirm delivery, invoice.",
        "featured": False,
    },
    {
        "name": "Jamii Health Network",
        "industry": "health",
        "category": "Custom Software Engineering",
        "excerpt": "",
        "tagline": "Patient records that stay available across 38 facilities.",
        "description": "We deployed a patient record system with offline synchronisation across 38 health facilities, built for intermittent connectivity and shared clinical workstations.",
        "overview": "Jamii Health Network operates facilities across a region with uneven connectivity. We built and deployed a patient record system that keeps working when the network does not, with offline synchronisation designed around real clinical workflows rather than idealised ones.",
        "problem_statement": "Records were written on paper when systems were unavailable and transcribed later, producing incomplete histories and double-counted visits at the regional level.",
        "objectives": "Guarantee record availability at every facility, synchronise reliably, and meet consent and access requirements for patient data.",
        "business_challenge": "Facilities were opening faster than the regional system could support, and clinical staff were reverting to paper whenever the system was unreachable.",
        "research_findings": "Workflow studies at six facilities showed paper fallback was routine rather than exceptional, driven by system unavailability rather than preference.",
        "user_needs": "Records that never become unavailable, fast retrieval at the point of care, and access control that respects consent.",
        "features": "Offline-capable records with conflict-aware sync, role-based access, consent management, and an FHIR-aligned integration layer.",
        "user_challenges": "Shared workstations meant one clinician's session could expose another's patient list, and connectivity drops mid-consultation were routine.",
        "competitor_data": "We evaluated three health records products on offline capability and consent modelling. None met both the offline and consent requirements without significant extension.",
        "unique_features": "Conflict-aware synchronisation at the record field rather than document level, and consent enforcement applied at the point of read.",
        "root_cause": "The previous system assumed continuous connectivity, so its failure mode was total unavailability rather than degraded operation.",
        "task_flows": "Register patient, record visit, sync records, retrieve history, honour consent.",
        "featured": True,
    },
]

# ── Community (community.models) ──
COMMUNITY_CATEGORIES = [
    ("Engineering Practice", "How we build, review and ship software."),
    ("Cloud & DevOps", "Infrastructure, deployments and operational practice."),
    ("Data & Analytics", "Pipelines, modelling and reporting."),
    ("Security", "Threat modelling, access control and secure delivery."),
    ("Career & Growth", "Hiring, interviews, progression and working at Dovetec."),
    ("Announcements", "Product and company announcements."),
]

# community.Topic is an MTI child of home.Tag and shares home_tag's unique
# name and unique slug columns with home.Tag. These names are therefore kept
# distinct from the blog TAGS list above, otherwise the two collide.
TOPICS = [
    {"name": "Backend Engineering", "category": "Engineering Practice", "description": "Framework patterns, query optimisation and deployment practice."},
    {"name": "Frontend Engineering", "category": "Engineering Practice", "description": "TypeScript, accessibility and interface architecture."},
    {"name": "Infrastructure & Reliability", "category": "Cloud & DevOps", "description": "Managed infrastructure, observability and cost control."},
    {"name": "Data & Analytics", "category": "Data & Analytics", "description": "Pipelines, warehouses and analytical modelling."},
    {"name": "Application Security", "category": "Security", "description": "Secure design, review practice and threat modelling."},
    {"name": "Engineering Careers", "category": "Career & Growth", "description": "Interviewing, progression and team practice."},
    {"name": "Dovetec Announcements", "category": "Announcements", "description": "Updates from the Dovetec team."},
]

POSTS = [
    {
        "title": "What we look for in a senior backend engineer interview",
        "topic": "Engineering Careers",
        "author": "Sarah Johnson",
        "content": "<p>Our backend interviews are structured so we assess engineering judgement rather than recall. Every candidate gets the same problem, and we are as interested in how you ask questions as in what you build.</p><h2>The exercise</h2><p>You will design a component for idempotent payment capture. We do not expect a particular architecture. We expect you to surface the failure modes, and we will prompt you to consider retries, duplicates and reconciliation.</p><h2>What we score</h2><p>Clarifying questions, explicit failure handling, and whether you can say what you would not build yet. We are not looking for the most elaborate design.</p><h2>What happens after</h2><p>You will meet two engineers and a product manager. We share feedback quickly, usually within two working days.</p>",
    },
    {
        "title": "Reducing our container image size by 70 percent",
        "topic": "Infrastructure & Reliability",
        "author": "Michael Chen",
        "content": "<p>Our application images carried development dependencies and build tooling into production, which slowed every deploy and pushed us near registry limits. A few changes cut the image by 70 percent.</p><h2>Multi-stage builds</h2><p>Build dependencies belong in a builder stage that never ships. The runtime stage installs only what the application imports.</p><h2>Removing build tools</h2><p>Compilers and package managers are not runtime dependencies. Removing them also removed a meaningful part of our attack surface.</p><h2>Measuring it properly</h2><p>We now gate on image size in CI, because a regression here is invisible until it is expensive.</p>",
    },
    {
        "title": "Designing an audit trail people will actually use",
        "topic": "Application Security",
        "author": "Sarah Johnson",
        "content": "<p>An audit log nobody reads is a liability rather than a control. We spent a redesign cycle making ours useful to the people who need it: compliance staff responding to a specific query.</p><h2>Start from the question</h2><p>Ask what someone needs to prove, then log what supports that proof. We log intent, actor and outcome rather than every field change.</p><h2>Make it queryable</h2><p>Logs that require an engineer to write SQL will not be used during an incident. We built the common queries into the interface.</p><h2>Retention must be deliberate</h2><p>Retention is a legal and storage decision, not an implementation detail. We document it per log type.</p>",
    },
    {
        "title": "Writing migrations that are safe to deploy on a Friday",
        "topic": "Backend Engineering",
        "author": "Michael Chen",
        "content": "<p>Most migration incidents are not caused by complex SQL. They come from changes that assume an application version and a database version that agree. A few rules keep deploys boring.</p><h2>Expand, migrate, contract</h2><p>Add the new column, deploy code that writes both forms, backfill, then drop the old column in a later release. Each step is independently safe.</p><h2>Never rename in one step</h2><p>A rename is a drop and an add as far as running code is concerned. Treat it as two deployments.</p><h2>Test against production-shaped data</h2><p>A migration that succeeds on a small fixture set can still lock a large table. Test the shape, not just the logic.</p>",
    },
    {
        "title": "Dovetec Enterprises is now ISO 27001 aligned",
        "topic": "Dovetec Announcements",
        "author": "Sarah Johnson",
        "content": "<p>We have completed our ISO 27001 readiness assessment and our information security management system is now formally documented and in operation.</p><h2>What this means for clients</h2><p>Our processes for access control, change management, incident response and supplier review are now documented and externally assessed. Evidence packs are available to clients under NDA.</p><h2>What we are doing next</h2><p>Certification is in progress. In the meantime our engineering standards continue to tighten, and this platform is where we publish them.</p>",
    },
]

# ── Newsletter ──
NEWSLETTER = {
    "subject": "Q3 Innovation Digest",
    "preheader": "Field-first architecture, offline payments, and our 2026 readiness findings",
    "subtitle": "Everything we shipped this quarter, plus the annual engineering readiness report.",
    "accent_color": "#0071e3",
    "cta_label": "Read the full digest",
    "cta_text": "Case studies, benchmarks and the full readiness report are in the newsroom archive.",
    "content": (
        "<p>Hello,</p>"
        "<p>This quarter we shipped work across agriculture, education and financial services, "
        "and the through-line was the same as last quarter: assume the network will fail.</p>"
        "<p>Our field teams wrote up what offline-first capture actually requires in production, "
        "and our payments team documented why modelling the intent rather than the callback makes "
        "duplicate disbursements structurally impossible. Both write-ups are in this issue.</p>"
        "<p>We have also published the 2026 Engineering Readiness Report, which distils delivery, "
        "security and accessibility patterns from forty engagements.</p>"
        "<p>Questions about any of this? <a href=\"mailto:hello@dovetecenterprises.tech\">Email the team</a>.</p>"
        "<p>Thanks,<br>The Dovetec Enterprises team</p>"
    ),
}
