"""Seed richer sample questionnaire templates, plans, and feature-board placeholders."""
from django.db import migrations


def seed_templates(apps, schema_editor):
    QuestionnaireTemplate = apps.get_model('app', 'QuestionnaireTemplate')
    Question = apps.get_model('app', 'Question')

    # title, context, industry, intro, [(text, type, options, required), ...]
    samples = [
        (
            'Discovery — needs & goals', 'discovery', '',
            'Help us understand your goals before we scope the work.',
            [
                ('What business problem are you trying to solve?', 'textarea', '', True),
                ('Who are the primary users of this solution?', 'text', '', False),
                ('What does success look like in 6–12 months?', 'textarea', '', True),
                ('Are there existing systems we must integrate with?', 'text', '', False),
                ('What is your rough budget range?', 'choice',
                 'Under KES 50,000,KES 50,000–250,000,KES 250,000–1M,Over KES 1M,Not sure yet', True),
                ('Target launch window?', 'choice',
                 'ASAP,1–3 months,3–6 months,6+ months,Exploring only', False),
            ],
        ),
        (
            'Client onboarding', 'onboarding', '',
            'Welcome aboard — a few details so we can start strong.',
            [
                ('Primary point of contact and preferred channel?', 'text', '', True),
                ('Key stakeholders and roles?', 'textarea', '', False),
                ('Access credentials / environments needed?', 'textarea', '', False),
                ('Brand guidelines or design references?', 'text', '', False),
                ('Preferred communication cadence?', 'choice',
                 'Daily standups,Weekly sync, Biweekly,Async only (Slack/Email),As needed', True),
                ('Do you have a technical champion on your side?', 'boolean', '', False),
            ],
        ),
        (
            'End-of-service handover', 'end_of_service', '',
            'Final handover checklist for your completed engagement.',
            [
                ('Confirm deliverables received.', 'boolean', '', True),
                ('Any outstanding items or punch-list?', 'textarea', '', False),
                ('Training completed for your team?', 'boolean', '', True),
                ('Where should documentation be stored?', 'text', '', False),
                ('Final budget vs estimate (notes)?', 'textarea', '', False),
            ],
        ),
        (
            'Satisfaction survey', 'satisfaction', '',
            'Your feedback helps us improve delivery for the next team.',
            [
                ('How satisfied are you with the delivery overall?', 'choice',
                 'Very satisfied,Satisfied,Neutral,Dissatisfied,Very dissatisfied', True),
                ('How responsive was our team?', 'choice',
                 'Excellent,Good,Average,Poor', True),
                ('Would you recommend us?', 'boolean', '', True),
                ('Why / why not?', 'textarea', '', False),
                ('What should we improve next time?', 'textarea', '', False),
            ],
        ),
        (
            'Technical discovery — fintech', 'discovery', 'fintech',
            'Fintech-specific discovery questions.',
            [
                ('Regulatory / compliance constraints (CBK, PCI, data residency)?', 'textarea', '', True),
                ('Core banking or wallet systems to integrate?', 'text', '', False),
                ('KYC/AML flow already defined?', 'boolean', '', False),
                ('Transaction volume expected in year one?', 'number', '', False),
                ('Audit logging requirements?', 'textarea', '', False),
            ],
        ),
        (
            'Technical discovery — health', 'discovery', 'health',
            'Healthcare-specific discovery questions.',
            [
                ('Patient data sensitivity / HIPAA-like requirements?', 'textarea', '', True),
                ('EMR/EHR systems in use?', 'text', '', False),
                ('Offline-first needs for clinics?', 'boolean', '', False),
                ('Who is the clinical product owner?', 'text', '', False),
            ],
        ),
        (
            'Custom kickoff workshop', 'custom', '',
            'Placeholder set for facilitated kickoff workshops.',
            [
                ('Workshop date and attendees?', 'text', '', True),
                ('Top 3 outcomes for the workshop?', 'textarea', '', True),
                ('Existing artifacts to review?', 'textarea', '', False),
                ('Decision makers present?', 'boolean', '', False),
            ],
        ),
        (
            'Security & compliance checklist', 'custom', '',
            'Optional security questionnaire for enterprise deals.',
            [
                ('Data classification of in-scope information?', 'choice',
                 'Public,Internal,Confidential,Restricted', True),
                ('SSO / MFA required?', 'boolean', '', False),
                ('Penetration test in last 12 months?', 'boolean', '', False),
                ('Incident response contact?', 'text', '', False),
                ('Vendor risk questionnaire attached?', 'boolean', '', False),
            ],
        ),
    ]

    for title, context, industry, intro, questions in samples:
        template, created = QuestionnaireTemplate.objects.get_or_create(
            title=title,
            defaults={
                'context': context,
                'industry': industry,
                'is_active': True,
                'intro': intro,
            },
        )
        if not template.questions.exists():
            for i, (text, qtype, options, required) in enumerate(questions, start=1):
                Question.objects.create(
                    template=template,
                    text=text,
                    question_type=qtype,
                    options=options or None,
                    required=required,
                    order=i,
                    context=context,
                )


def seed_plans(apps, schema_editor):
    Plan = apps.get_model('app', 'Plan')
    plans = [
        {
            'name': 'Free',
            'slug': 'free',
            'description': 'Core portal access for every registered client.',
            'price': '0',
            'currency': 'KES',
            'interval': 'monthly',
            'features': 'Client portal\nSupport tickets\nQuestionnaires\nOrder history',
            'is_active': True,
            'is_default': True,
            'sort_order': 0,
        },
        {
            'name': 'Pro',
            'slug': 'pro',
            'description': 'Priority support and advanced portal tools for growing teams.',
            'price': '4999',
            'currency': 'KES',
            'interval': 'monthly',
            'features': (
                'Everything in Free\nPriority ticket routing\n'
                'Advanced project analytics\nEarly feature access\n'
                'Extended file storage'
            ),
            'is_active': True,
            'is_default': False,
            'sort_order': 1,
        },
        {
            'name': 'Enterprise',
            'slug': 'enterprise',
            'description': 'Dedicated success contact and custom SLAs.',
            'price': '24999',
            'currency': 'KES',
            'interval': 'monthly',
            'features': (
                'Everything in Pro\nDedicated success manager\n'
                'Custom SLA\nSSO readiness review\n'
                'Quarterly business reviews'
            ),
            'is_active': True,
            'is_default': False,
            'sort_order': 2,
        },
    ]
    for data in plans:
        Plan.objects.update_or_create(slug=data['slug'], defaults=data)


def seed_features(apps, schema_editor):
    FeatureRequest = apps.get_model('app', 'FeatureRequest')
    samples = [
        ('Dark mode for the client portal', 'platform', 'open',
         'Allow clients to switch the portal to a dark theme for late-night work sessions.',
         12),
        ('Weekly email digest of ticket updates', 'portal', 'planned',
         'Send a Monday summary of open tickets, stage changes, and pending questionnaires.',
         9),
        ('Upvote roadmap items in the community', 'community', 'in_progress',
         'Let authenticated users upvote feature requests so we can prioritise the public roadmap.',
         15),
        ('M-Pesa auto-renew for Pro plan', 'billing', 'open',
         'Auto-renew monthly Pro subscriptions via STK push before the period ends.',
         7),
        ('Export questionnaire responses to CSV from the client portal', 'portal', 'shipped',
         'Clients can download their own submitted questionnaire answers as CSV.',
         5),
    ]
    from django.utils.text import slugify
    for title, category, status, description, votes in samples:
        slug = slugify(title)[:220]
        obj, _ = FeatureRequest.objects.get_or_create(
            title=title,
            defaults={
                'slug': slug,
                'category': category,
                'status': status,
                'description': description,
                'vote_count': votes,
            },
        )
        if not obj.slug:
            obj.slug = slugify(title)[:220] or f'feature-{obj.pk}'
            obj.save(update_fields=['slug'])


def unseed(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0015_plan_alter_questionnaire_inquiry_featurerequest_and_more'),
    ]

    operations = [
        migrations.RunPython(seed_templates, unseed),
        migrations.RunPython(seed_plans, unseed),
        migrations.RunPython(seed_features, unseed),
    ]
