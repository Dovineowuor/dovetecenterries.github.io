# Dovetec platform modernization roadmap

## Summary

Deliver as dependency-ordered, independently releasable epics. Establish shared data, permissions, media, and moderation foundations before expanding dashboards and public-facing modules.

## Foundation tasks

1. Replace ad-hoc role checks with Django Groups and permissions:
   - Client portal: request services, track enquiries/projects, view invoices/orders, and pay.
   - Staff: dashboard access only for granted modules/actions.
   - Administrator: full CRUD and permission management.
2. Centralize object-level ownership checks so clients can only access their own records and attachments.
3. Create a reusable dashboard design system: responsive navigation, mobile drawer, responsive tables/cards, loading/empty/error states, accessible controls, and shared CRUD list/detail/form patterns.
4. Add dashboard analytics cards and charts for CRM, content, commerce, community, careers, and media using server-provided aggregate data.
5. Introduce a MediaAsset model and upload service for images, documents, blueprints, charts, and resources:
   - Validate type, size, filename, and ownership; generate safe storage names and image derivatives.
   - Record upload, processing, and rendering-failure states; expose retry-friendly admin diagnostics.
   - Use Vercel Blob when `BLOB_READ_WRITE_TOKEN` is set (`dovetecenterprises.blob_storage.VercelBlobStorage`); fall back to local `MEDIA_ROOT` otherwise. Surface the active backend in deployment checks.

## CRM, enquiries, and client portal

6. Replace the single-purpose enquiry record with a linked CRM model:
   - Organization, Contact, Lead/Enquiry, Service Request, Deal, Activity/Note, Attachment, and Project/Delivery records.
   - Preserve existing service enquiries through data migration and route contact/service forms into the unified intake flow.
   - Support intake fields for goals, budget, timeline, industry, technical requirements, preferred contact method, and attachments.
7. Add lead assignment, stage history, follow-up reminders, value forecasting, qualification data, and inquiry-to-client/project conversion.
8. Expand the client portal with a dashboard for requests, status timeline, questionnaires, shared files, project updates, quotes/invoices, orders, and payments.
9. Build staff CRM dashboards for pipeline value, conversions, workload, ageing leads, overdue follow-ups, and activity history.

## CMS and public content

10. Upgrade Articles with structured editorial and sharing metadata: canonical URL, meta title/description, Open Graph/Twitter fields, author, publication dates, schema.org Article JSON-LD, preview image validation, and sitemap integration.
11. Replace static portfolio/case-study pages with reusable models for industry, service, technology, challenge, solution, outcomes/KPIs, gallery/media, testimonial, project URL, featured status, and SEO/social metadata.
12. Add admin CRUD, public listing/detail/filter pages, and reusable card/detail components for portfolio and case studies.
13. Upgrade Products and categories with admin CRUD, slugs, publish/visibility state, inventory controls, media gallery, SEO metadata, and category management.
14. Add Careers models and staff dashboard workflows for job posts, departments, locations, employment type, applications, CV/portfolio attachments, candidate status, assignment, notes, and hiring analytics.

## Community and moderation

15. Make forum categories, topics, posts, and replies fully manageable from the dashboard.
16. Add moderation states: pending, approved, hidden, removed, and flagged; store flag reason, reporter, moderator decision, and audit timestamps.
17. Require moderator approval before public publication; allow moderators to hide or pull down approved content and restore it where appropriate.
18. Add staff moderation queues, filters, notification counts, and dashboard reporting for pending and flagged content.

## Support tickets, notifications, questionnaire library

22. Support-first ticket queue for public intake:
    - Contact/services forms create a Ticket (issue or enquiry), auto-assigned to staff.
    - Staff queue with mine/unassigned/open/referred filters, status workflow, priority.
    - Transfer (ownership move + note), Refer (notify without ownership change), activity trail.
    - Escalate resolved tickets into the sales funnel as a ServiceInquiry.
23. In-app notifications with unread badges and optional staff email:
    - Events: assigned, transferred, referred, status/priority changes, stage changes, questionnaire sent/completed, convert.
24. Questionnaire template library (full CRUD):
    - Contexts: discovery, onboarding, end_of_service, satisfaction, custom; optional industry filter.
    - Assign/clone, swap (replaces questions), import questions across templates.
    - Auto-suggest on funnel stage qualified (discovery) and won (onboarding); satisfaction suggested on ticket resolve.
25. Client portal: My Tickets list/detail with public updates.

## Deferred features (now implemented)

26. Sample questionnaire templates and question sets:
    - Seed migration ships richer industry/context templates (discovery, onboarding, end-of-service, satisfaction) with typed questions.
27. Premium subscriptions:
    - `Plan` / `Subscription` models, seeded Free/Pro/Enterprise plans, client Billing & Plan page, placeholder checkout + cancel.
    - Staff can manage plans in Django admin; payment gateway wiring remains a follow-up.
28. Feature-request board:
    - Public board at `/features/` with search/status filter, upvote toggle, and suggest form.
    - Staff moderation at `/dashboard/cms/features/` (status updates).
29. Project-completion questionnaire auto-trigger:
    - `post_save` on `Project` attaches and sends the end-of-service questionnaire when status becomes completed and a converted inquiry exists.
    - `Questionnaire.inquiry` is now a ForeignKey (multiple lifecycle questionnaires per inquiry).
30. Won deal → delivery project auto-conversion:
    - Moving a funnel lead to Won creates a linked `Project` (idempotent; one per inquiry).
    - Maps organization, contact, service, source, and estimated deal value onto the project.

## Delivery order and verification

19. Implement in this order: permissions and shared UI → media → CRM/intake/client portal → dashboard analytics → articles/portfolio/products → careers → community moderation.
20. For every model change, ship migrations, data migration/backfill where existing records exist, Django admin support, permission tests, and responsive template checks.
21. Test client ownership boundaries, staff permission denial, upload validation/failure rendering, responsive dashboard breakpoints, CRM conversion/history, SEO metadata output, CRUD validation, and moderation visibility rules.

## Assumptions

- Roles are Client, Staff, and Administrator, implemented with Django’s built-in Groups and permissions rather than a custom permissions engine.
- Forum submissions require approval before public visibility.
- Durable production media uses Vercel Blob when `BLOB_READ_WRITE_TOKEN` is set; local `FileSystemStorage` is the fallback when no token is present (not durable on serverless).
- Public contact and services intake create Tickets first; staff escalate to the sales funnel when appropriate (optional questionnaire context on convert).
- Notifications are database-backed with polling badges plus best-effort email (`TICKET_NOTIFY_EMAIL`); no websocket layer.
- `TICKET_DEFAULT_ASSIGNEE` env (email) picks the default ticket owner; otherwise the first staff user is used.
