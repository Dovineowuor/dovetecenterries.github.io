"""CRM intake helpers: tickets, funnel conversion, notifications, questionnaires."""

import json
import logging
import re

from django.conf import settings
from django.db import transaction
from django.db.models import Q, Case, When, Value, IntegerField
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

import requests

from home.email import send_styled_email

from .media import store_uploaded_media
from .models import (
    Answer, Contact, Organization, Project, Question, Questionnaire,
    QuestionnaireEvent, QuestionnaireTemplate,
    ServiceInquiry, Ticket, TicketActivity,
)


def _organization_for_name(name, industry=''):
    normalized_name = (name or '').strip()
    if not normalized_name:
        return None
    organization = Organization.objects.filter(name__iexact=normalized_name).first()
    if organization:
        if industry and not organization.industry:
            organization.industry = industry
            organization.save(update_fields=['industry', 'updated_at'])
        return organization
    return Organization.objects.create(name=name.strip(), industry=industry)


def _upsert_contact(*, first_name='', last_name='', email, phone='', organization=None,
                    preferred_contact_method=Contact.CONTACT_EMAIL, owner=None):
    email = email.strip().lower()
    contact, _created = Contact.objects.get_or_create(
        email=email,
        defaults={
            'first_name': first_name.strip(), 'last_name': last_name.strip(),
            'phone': phone.strip(), 'organization': organization,
            'preferred_contact_method': preferred_contact_method,
            'portal_user': owner if getattr(owner, 'is_authenticated', False) else None,
        },
    )
    changed = []
    for field, value in {
        'first_name': first_name.strip(), 'last_name': last_name.strip(),
        'phone': phone.strip(), 'organization': organization,
        'preferred_contact_method': preferred_contact_method,
    }.items():
        if value and getattr(contact, field) != value:
            setattr(contact, field, value)
            changed.append(field)
    if getattr(owner, 'is_authenticated', False) and not contact.portal_user:
        contact.portal_user = owner
        changed.append('portal_user')
    if changed:
        contact.save(update_fields=[*changed, 'updated_at'])
    return contact


# ── Notifications ───────────────────────────────────────────────────
def notify(*, recipients, verb, title, body='', link='', actor=None, email_subject=None):
    """Create in-app notifications, email staff, and WhatsApp."""
    from home.models import Notification

    created = []
    send_email = getattr(settings, 'TICKET_NOTIFY_EMAIL', False)
    for recipient in recipients:
        if not recipient or not getattr(recipient, 'is_authenticated', True):
            continue
        if hasattr(recipient, 'email') and not recipient.email:
            continue
        note = Notification.objects.create(
            recipient=recipient, actor=actor, verb=verb,
            title=title[:255], body=body or '', link=link or '',
        )
        if send_email and recipient.is_staff and recipient.email:
            try:
                send_styled_email(
                    email_subject or title[:200],
                    'emails/notification.html',
                    {
                        'heading': title[:120],
                        'preheader': f'{verb or "Notification"}: {title[:80]}',
                        'intro': f'Triggered by {verb or "a workspace event"}.',
                        'body': body,
                        'action_url': absolute_url(link) if link else None,
                        'action_label': 'Open in the portal',
                        'actor': getattr(actor, 'email', None) or actor,
                    },
                    [recipient.email],
                    fail_silently=True,
                )
                note.email_sent = True
                note.save(update_fields=['email_sent'])
            except Exception:
                pass
        created.append(note)
    try:
        notify_whatsapp(
            recipients=recipients, verb=verb, title=title,
            body=body, link=link, actor=actor,
        )
    except Exception:
        _logger.exception('WhatsApp notify failed')
    return created


# ── WhatsApp Messaging ──────────────────────────────────────
_logger = logging.getLogger(__name__)

def _format_wa_number(number):
    """Normalize a phone number to E.164 format for WhatsApp API."""
    digits = re.sub(r'\D', '', str(number or ''))
    if not digits:
        return ''
    if digits.startswith('254') and len(digits) == 12:
        return digits
    if digits.startswith('+') or digits.startswith('254'):
        return digits
    if digits.startswith('7') and len(digits) == 9:
        return '254' + digits
    return digits


def send_whatsapp(to, message, *, channel='notify', notification=None):
    """Send a WhatsApp message via Meta Cloud API to +254742253400 or any verified number."""
    access_token = getattr(settings, 'WHATSAPP_ACCESS_TOKEN', '')
    phone_number_id = getattr(settings, 'WHATSAPP_PHONE_NUMBER_ID', '')
    if not access_token or not phone_number_id:
        _logger.warning('WhatsApp not configured — skipping message to %s', to)
        return False
    to_e164 = _format_wa_number(to)
    if not to_e164:
        _logger.warning('Cannot format WhatsApp number: %s', to)
        return False
    from .models import WhatsAppNotification
    wa = WhatsAppNotification.objects.create(
        recipient_phone=to,
        channel=channel,
        message=message[:5000],
        notification=notification,
    )
    try:
        url = f'https://graph.facebook.com/v18.0/{phone_number_id}/messages'
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        payload = {
            'messaging_product': 'whatsapp',
            'to': to_e164,
            'type': 'text',
            'text': {'body': message[:4096]},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            wa.status = WhatsAppNotification.STATUS_SENT
            wa.sent_at = timezone.now()
            wa.save(update_fields=['status', 'sent_at'])
            _logger.info('WhatsApp sent to %s', to_e164)
            return True
        else:
            wa.status = WhatsAppNotification.STATUS_FAILED
            wa.error_message = resp.text[:500]
            wa.save(update_fields=['status', 'error_message'])
            _logger.error('WhatsApp failed to %s: %s', to_e164, resp.text[:300])
            return False
    except Exception:
        _logger.exception('WhatsApp exception for %s', to)
        wa.status = WhatsAppNotification.STATUS_FAILED
        wa.error_message = str(wa)[:500]
        wa.save(update_fields=['status', 'error_message'])
        return False


def notify_whatsapp(*, recipients, verb, title, body='', link='', actor=None):
    """Send WhatsApp notifications to staff and clients."""
    if not getattr(settings, 'WHATSAPP_NOTIFY_STAFF', True) and not getattr(settings, 'WHATSAPP_NOTIFY_CLIENT', True):
        return []
    delivered = []
    for recipient in recipients:
        if not recipient or not getattr(recipient, 'is_authenticated', True):
            continue
        numbers = []
        if getattr(recipient, 'phone', '') and recipient.is_staff:
            numbers.append(recipient.phone)
        contact = getattr(recipient, 'contact', None)
        if contact:
            if getattr(settings, 'WHATSAPP_NOTIFY_CLIENT', True) and getattr(contact, 'preferred_contact_method', '') == 'whatsapp':
                if getattr(contact, 'phone', ''):
                    numbers.append(contact.phone)
            if getattr(recipient, 'phone', '') and recipient.is_staff:
                numbers.append(recipient.phone)
        for number in numbers:
            wa_number = _format_wa_number(number)
            if not wa_number:
                continue
            msg = f"[{verb}] {title}\n\n{body}\n\n{settings.SITE_URL if hasattr(settings, 'SITE_URL') else ''}{link}"
            if send_whatsapp(wa_number, msg, channel='notify'):
                delivered.append(wa_number)
    return delivered


# ── Questionnaire response logging + client emails ──────────

CONTEXT_DIRECTIVES = {
    QuestionnaireTemplate.CONTEXT_DISCOVERY: [
        "Outline business goals, pain points, and what success looks like.",
        "Share timelines, budget range, and any hard constraints.",
        "Name key stakeholders who will use or approve the solution.",
        "Link examples or references that illustrate the desired outcome.",
    ],
    QuestionnaireTemplate.CONTEXT_ONBOARDING: [
        "Confirm primary contacts, emails, and preferred channels.",
        "List systems, access, and data needed to start work.",
        "Flag compliance, security, or procurement requirements early.",
        "Note launch milestones and any fixed go-live dates.",
    ],
    QuestionnaireTemplate.CONTEXT_SATISFACTION: [
        "Rate recent delivery quality, communication, and responsiveness.",
        "Call out what worked well and where we should improve.",
        "Share any features or support gaps you still need.",
        "Tell us who should be copied on follow-ups.",
    ],
    QuestionnaireTemplate.CONTEXT_END_OF_SERVICE: [
        "Summarize outcomes versus the original brief.",
        "Note open items, warranties, or handover needs.",
        "Share feedback for the closing report and future engagements.",
        "Confirm final stakeholders for sign-off.",
    ],
    QuestionnaireTemplate.CONTEXT_CUSTOM: [
        "Answer each question as completely as you can — you can return later.",
        "Use the help text under a question if anything is unclear.",
        "Reply to this email if you need a walkthrough before submitting.",
    ],
}


def questionnaire_context_directives(context):
    """Human-readable next-step directives for a questionnaire context."""
    return list(CONTEXT_DIRECTIVES.get(context or '', CONTEXT_DIRECTIVES[QuestionnaireTemplate.CONTEXT_CUSTOM]))


def absolute_url(path):
    base = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
    if not path.startswith('/'):
        path = '/' + path
    return f"{base}{path}" if base else path


def log_questionnaire_event(questionnaire, action, *, question=None, actor=None,
                            content='', answer_snapshot=None):
    """
    Append-only log of questionnaire lifecycle / response changes over time.

    Never raises: if the events table is missing (migration not applied yet),
    the primary action (send/email/fill) must still succeed.
    """
    try:
        return QuestionnaireEvent.objects.create(
            questionnaire=questionnaire,
            question=question,
            actor=actor if getattr(actor, 'is_authenticated', False) else None,
            action=action,
            content=content or '',
            answer_snapshot=answer_snapshot,
        )
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Failed to log questionnaire event action=%s questionnaire=%s',
            action, getattr(questionnaire, 'id', None),
        )
        return None


def email_questionnaire_to_client(questionnaire, *, kind='sent', question_count=None,
                                  changed_count=0):
    """
    Immediately email the client about a questionnaire event.

    Includes portal link and context-based directives (discovery, onboarding, …).
    kind: sent | reopened | completed | updated
    """
    inquiry = questionnaire.inquiry
    if not inquiry or not inquiry.email:
        return False

    path = reverse('client_questionnaire_fill', args=[questionnaire.id])
    link = absolute_url(path)
    directives = questionnaire_context_directives(questionnaire.context)
    context_label = dict(QuestionnaireTemplate.CONTEXT_CHOICES).get(
        questionnaire.context, questionnaire.context or 'General',
    )
    count = question_count if question_count is not None else questionnaire.question_count

    if kind == 'completed':
        subject = f"Responses received: {questionnaire.title}"
        opening = (
            f"We received your responses for “{questionnaire.title}”"
            + (f" ({changed_count} answer(s) updated this submit)." if changed_count else ".")
        )
        action_label = "Review responses in your portal"
        steps_heading = "What happens next"
    elif kind == 'reopened':
        subject = f"More questions added: {questionnaire.title}"
        opening = (
            f"We added new questions to “{questionnaire.title}”. "
            "Your previous answers were kept — please complete the new items."
        )
        action_label = "Continue where you left off"
        steps_heading = "Directives for this stage"
    elif kind == 'updated':
        subject = f"Survey updated: {questionnaire.title}"
        opening = f"Updates were saved for “{questionnaire.title}”."
        action_label = "Review your responses"
        steps_heading = "Reminders for this stage"
    else:
        subject = f"Action required: {questionnaire.title}"
        opening = (
            f"A new {context_label.lower()} questionnaire is ready for you: "
            f"“{questionnaire.title}” ({count} question(s))."
        )
        action_label = "Open the survey"
        steps_heading = f"Directives for {context_label}"

    try:
        send_styled_email(
            subject[:200],
            'emails/client_message.html',
            {
                'heading': f'Questionnaire: {questionnaire.title}',
                'preheader': opening[:120],
                'intro': context_label,
                'greeting': inquiry.name or inquiry.email.split('@')[0],
                'paragraphs': [opening],
                'steps_heading': steps_heading,
                'steps': directives,
                'details': [
                    ('Survey', questionnaire.title),
                    ('Context', context_label),
                    ('Questions', count),
                    ('Status', questionnaire.get_status_display()),
                ],
                'action_url': link,
                'action_label': action_label,
            },
            [inquiry.email],
            fail_silently=True,
        )
        return True
    except Exception:
        import logging
        logging.getLogger(__name__).exception(
            'Failed to email client questionnaire=%s kind=%s to=%s',
            getattr(questionnaire, 'id', None), kind, inquiry.email,
        )
        return False


def send_client_survey_notice(questionnaire, *, kind='sent', actor=None, **email_kwargs):
    """Log the event, email the client, WhatsApp, and return (event_or_None, emailed)."""
    content_map = {
        'sent': 'Survey sent to client with context directives.',
        'reopened': 'New questions added; prior answers kept; client notified.',
        'completed': 'Client submitted responses.',
        'updated': 'Responses updated; client notified.',
    }
    action = (
        QuestionnaireEvent.ACTION_SENT if kind == 'sent'
        else QuestionnaireEvent.ACTION_COMPLETED if kind == 'completed'
        else QuestionnaireEvent.ACTION_REOPENED if kind == 'reopened'
        else QuestionnaireEvent.ACTION_UPDATED
    )
    event = log_questionnaire_event(
        questionnaire,
        action,
        actor=actor,
        content=content_map.get(kind, kind),
    )
    emailed = email_questionnaire_to_client(questionnaire, kind=kind, **email_kwargs)
    inquiry = getattr(questionnaire, 'inquiry', None)
    if not emailed:
        _logger.warning(
            'Survey email not sent questionnaire=%s kind=%s inquiry=%s',
            getattr(questionnaire, 'id', None), kind,
            inquiry and inquiry.email,
        )
    if inquiry and getattr(inquiry, 'phone', ''):
        try:
            msg = f"[Survey {kind}] {questionnaire.title}\n\nA new questionnaire is ready: {questionnaire.title} ({questionnaire.question_count} question(s)).\n\nOpen: {inquiry.email}"
            send_whatsapp(inquiry.phone, msg, channel='questionnaire', notification=event)
        except Exception:
            _logger.exception('WhatsApp survey notice failed for questionnaire=%s', getattr(questionnaire, 'id', None))
    if event is not None:
        event.content = (
            (event.content + ' Email sent.' if emailed else event.content + ' Email attempted.')
        )
        event.save(update_fields=['content'])
    return event, emailed


def default_ticket_assignee():
    """Staff user from TICKET_DEFAULT_ASSIGNEE, else first staff, else None."""
    from home.models import User

    email = (getattr(settings, 'TICKET_DEFAULT_ASSIGNEE', '') or '').strip().lower()
    if email:
        user = User.objects.filter(email__iexact=email, is_staff=True).first()
        if user:
            return user
    return User.objects.filter(is_staff=True).order_by('id').first()


# ── Ticket intake ───────────────────────────────────────────────────
@transaction.atomic
def create_ticket(*, subject='', description='', email, first_name='', last_name='',
                  message='', service='other', phone='', organization_name='', industry='',
                  budget_range=ServiceInquiry.BUDGET_UNSPECIFIED, timeline='',
                  preferred_contact_method=Contact.CONTACT_EMAIL,
                  source=ServiceInquiry.SOURCE_WEBSITE, ticket_type=Ticket.TYPE_ISSUE,
                  priority=Ticket.PRIORITY_NORMAL, attachments=(), owner=None,
                  assignee=None):
    """Create a work-queue ticket from public intake (issues first)."""
    email = email.strip().lower()
    valid_services = {v for v, _ in ServiceInquiry.SERVICE_CHOICES}
    valid_budgets = {v for v, _ in ServiceInquiry.BUDGET_CHOICES}
    valid_contact_methods = {v for v, _ in Contact.CONTACT_CHOICES}
    valid_priorities = {v for v, _ in Ticket.PRIORITY_CHOICES}
    if service not in valid_services:
        service = 'other'
    if budget_range not in valid_budgets:
        budget_range = ServiceInquiry.BUDGET_UNSPECIFIED
    if preferred_contact_method not in valid_contact_methods:
        preferred_contact_method = Contact.CONTACT_EMAIL
    if priority not in valid_priorities:
        priority = Ticket.PRIORITY_NORMAL

    organization = _organization_for_name(organization_name, industry)
    contact = _upsert_contact(
        first_name=first_name, last_name=last_name, email=email, phone=phone,
        organization=organization, preferred_contact_method=preferred_contact_method,
        owner=owner,
    )
    body = (message or description or '').strip()
    subject = (subject or '').strip() or (
        f"{contact.display_name} — {dict(ServiceInquiry.SERVICE_CHOICES).get(service, 'Contact')}"
    )[:255]

    ticket = Ticket.objects.create(
        subject=subject[:255],
        description=body,
        type=ticket_type,
        priority=priority,
        service=service,
        source=source,
        industry=(industry or '').strip(),
        budget_range=budget_range,
        timeline=(timeline or '').strip(),
        preferred_contact_method=preferred_contact_method,
        contact=contact,
        organization=organization or contact.organization,
        assigned_to=assignee if assignee is not None else default_ticket_assignee(),
        created_by=owner if getattr(owner, 'is_authenticated', False) else None,
        status=Ticket.STATUS_NEW,
    )
    ticket.log_activity(
        TicketActivity.ACTION_CREATED,
        user=owner if getattr(owner, 'is_authenticated', False) else None,
        content=f"Ticket opened via {ticket.get_source_display()}.",
    )
    if ticket.assigned_to:
        ticket.log_activity(
            TicketActivity.ACTION_ASSIGNED, user=owner,
            to_user=ticket.assigned_to, content='Auto-assigned on intake.',
        )
        notify(
            recipients=[ticket.assigned_to], verb='assigned',
            title=f"New ticket {ticket.reference}: {ticket.subject}",
            body=body[:500], link=reverse('ticket_detail', args=[ticket.id]),
            actor=owner if getattr(owner, 'is_authenticated', False) else None,
            email_subject=f"[Dovetec] Ticket {ticket.reference} assigned",
        )

    uploaded = [
        store_uploaded_media(
            upload,
            owner=owner if getattr(owner, 'is_authenticated', False) else None,
            content_object=ticket,
        )
        for upload in attachments
    ]
    return ticket, uploaded


# ── Ticket → funnel conversion ──────────────────────────────────────
@transaction.atomic
def convert_ticket_to_inquiry(ticket, *, user=None, stage=ServiceInquiry.STAGE_NEW,
                              auto_questionnaire_context=None):
    """Escalate a resolved ticket into a sales-funnel ServiceInquiry."""
    if ticket.inquiry_id:
        return ticket.inquiry, None

    contact = ticket.contact
    inquiry = ServiceInquiry.objects.create(
        name=contact.display_name if contact else ticket.subject,
        email=contact.email if contact else '',
        phone=(contact.phone if contact else None) or None,
        service=ticket.service,
        message=ticket.description,
        organization=ticket.organization or (contact.organization if contact else None),
        contact=contact,
        source=ticket.source,
        industry=ticket.industry,
        budget_range=ticket.budget_range,
        timeline=ticket.timeline,
        preferred_contact_method=ticket.preferred_contact_method,
        stage=stage,
        assigned_to=ticket.assigned_to,
        notes=f"Escalated from ticket {ticket.reference}.",
    )
    ticket.inquiry = inquiry
    ticket.escalated_at = timezone.now()
    if ticket.status in Ticket.OPEN_STATUSES:
        ticket.status = Ticket.STATUS_RESOLVED
        ticket.resolved_at = ticket.resolved_at or timezone.now()
    ticket.save()
    ticket.log_activity(
        TicketActivity.ACTION_CONVERTED, user=user,
        content=f"Escalated to sales lead #{inquiry.id} ({inquiry.get_stage_display()}).",
    )
    notify(
        recipients=[u for u in [ticket.assigned_to, user] if u],
        verb='converted',
        title=f"{ticket.reference} escalated to sales lead",
        body=f"{inquiry.name} · {inquiry.get_service_display()}",
        link=reverse('funnel_inquiry_detail', args=[inquiry.id]),
        actor=user,
    )
    if auto_questionnaire_context:
        attach_questionnaire_for_context(
            inquiry, auto_questionnaire_context, actor=user,
        )
    return inquiry, None


# ── Won deal → delivery project ─────────────────────────────────────
@transaction.atomic
def convert_won_inquiry_to_project(inquiry, *, actor=None):
    """Create (or return) the delivery Project for a won lead.

    Idempotent: one Project per inquiry. Maps identity, service, and
    deal value onto the Project so staff can start delivery immediately.
    """
    existing = Project.objects.filter(converted_from_inquiry=inquiry).first()
    if existing:
        return existing, False

    project = Project.objects.create(
        name=f"{inquiry.get_service_display()} — {inquiry.name}"[:200],
        description=inquiry.message or '',
        organization=inquiry.organization,
        contact=inquiry.contact,
        service=inquiry.service or '',
        source=inquiry.source or '',
        status=Project.STATUS_ACTIVE,
        stage=Project.STATUS_ACTIVE,
        estimated_budget=inquiry.estimated_value or None,
        converted_from_inquiry=inquiry,
    )
    notify(
        recipients=[u for u in [inquiry.assigned_to, actor] if u],
        verb='converted',
        title="Deal won — project created",
        body=f"{project.name} · KES {inquiry.estimated_value or 0}",
        link=reverse('dashboard_edit', args=['app', 'project', project.id]),
        actor=actor,
    )
    return project, True


# ── Questionnaire templates ─────────────────────────────────────────
def pick_template_for(context, industry=''):
    """Active template for a context, preferring an industry match."""
    qs = QuestionnaireTemplate.objects.filter(is_active=True, context=context)
    industry = (industry or '').strip()
    if industry:
        match = qs.filter(
            Q(industry__iexact=industry) | Q(industry='')
        ).annotate(
            _pref=Case(
                When(industry__iexact=industry, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('_pref').first()
        if match:
            return match
    return qs.filter(industry='').first() or qs.first()


def clone_questions(source, target_questionnaire):
    """Copy questions from a template (or another questionnaire) into target."""
    if isinstance(source, QuestionnaireTemplate):
        source_qs = source.questions.all()
    else:
        source_qs = source.questions.all()
    count = 0
    for q in source_qs.order_by('order', 'created_at'):
        Question.objects.create(
            questionnaire=target_questionnaire,
            text=q.text, help_text=q.help_text, question_type=q.question_type,
            options=q.options, required=q.required, order=count + 1,
            context=q.context or '',
        )
        count += 1
    return count


def attach_questionnaire_for_context(inquiry, context, *, actor=None, auto_send=False, template=None):
    """Clone a context template into a live questionnaire for this inquiry (one per context)."""
    if Questionnaire.objects.filter(inquiry=inquiry, context=context).exists():
        return None, 'exists'
    template = template or pick_template_for(context, getattr(inquiry, 'industry', ''))
    if not template:
        return None, 'no_template'
    questionnaire = Questionnaire.objects.create(
        inquiry=inquiry,
        title=template.title,
        intro=template.intro or '',
        source_template=template,
        context=context,
        status='sent' if auto_send else 'draft',
    )
    clone_questions(template, questionnaire)
    if auto_send and questionnaire.questions.exists():
        recipients = []
        if inquiry.contact and inquiry.contact.portal_user:
            recipients.append(inquiry.contact.portal_user)
        if inquiry.assigned_to:
            recipients.append(inquiry.assigned_to)
        notify(
            recipients=recipients, verb='questionnaire_sent',
            title=f"Questionnaire ready: {questionnaire.title}",
            body=f"Context: {dict(QuestionnaireTemplate.CONTEXT_CHOICES).get(context, context)}",
            link=reverse('funnel_questionnaire', args=[inquiry.id]),
            actor=actor,
        )
        # Immediate client email with portal link + context directives
        send_client_survey_notice(questionnaire, kind='sent', actor=actor)
    elif auto_send:
        send_client_survey_notice(questionnaire, kind='sent', actor=actor)
    return questionnaire, 'created'


def normalize_question_text(text):
    """Normalized form used to detect duplicate questions across packages."""
    return ' '.join((text or '').split()).casefold()


def reopen_questionnaire_for_new_questions(questionnaire):
    """
    Unlock a completed live questionnaire after staff add/import questions.

    Existing answers are never deleted — only the completion lock is lifted
    so the client can answer the newly added items and resubmit.
    """
    if questionnaire.status != 'completed':
        return False
    questionnaire.status = 'in_progress' if questionnaire.answered_count else 'sent'
    questionnaire.completed_at = None
    questionnaire.save()
    return True


def import_questions_into(target, source, question_ids=None):
    """
    Merge questions from another template/questionnaire into target.

    Safe on live questionnaires: never deletes existing questions or answers.
    Duplicate question text (case/whitespace-insensitive) is skipped.
    Returns {'added': int, 'skipped': int}.
    """
    if isinstance(target, QuestionnaireTemplate):
        dest_related, dest_field = 'template', target
    else:
        dest_related, dest_field = 'questionnaire', target
    qs = source.questions.all()
    if question_ids:
        qs = qs.filter(id__in=question_ids)
    existing = {
        normalize_question_text(q.text)
        for q in dest_field.questions.all()
    }
    start = dest_field.questions.count()
    added = skipped = 0
    for q in qs.order_by('order', 'created_at'):
        key = normalize_question_text(q.text)
        if key in existing:
            skipped += 1
            continue
        existing.add(key)
        kwargs = {
            'text': q.text, 'help_text': q.help_text, 'question_type': q.question_type,
            'options': q.options, 'required': q.required,
            'order': start + added + 1, 'context': q.context or '',
        }
        kwargs[dest_related] = dest_field
        Question.objects.create(**kwargs)
        added += 1
    reopened = False
    if added and isinstance(target, Questionnaire):
        reopened = reopen_questionnaire_for_new_questions(target)
        log_questionnaire_event(
            target,
            QuestionnaireEvent.ACTION_QUESTIONS_IMPORTED,
            content=(
                f"Merged {added} question(s) from “{getattr(source, 'title', source)}”"
                + (f"; skipped {skipped} duplicate(s)." if skipped else ".")
                + (" Prior answers kept; client re-opened." if reopened else " Prior answers kept.")
            ),
        )
        if reopened:
            email_questionnaire_to_client(
                target, kind='reopened',
                question_count=target.question_count,
            )
            log_questionnaire_event(
                target,
                QuestionnaireEvent.ACTION_REOPENED,
                content='Client emailed to complete newly imported questions.',
            )
    return {'added': added, 'skipped': skipped, 'reopened': reopened}


def swap_questionnaire_questions(questionnaire, template, *, actor=None):
    """Replace live questionnaire questions with a template's (clears answers)."""
    questionnaire.questions.all().delete()
    questionnaire.source_template = template
    questionnaire.title = template.title
    questionnaire.intro = template.intro or ''
    questionnaire.context = template.context
    questionnaire.status = 'draft'
    questionnaire.completed_at = None
    questionnaire.save()
    clone_questions(template, questionnaire)
    if actor:
        if questionnaire.inquiry:
            # best-effort activity if linked via a ticket
            ticket = questionnaire.inquiry.tickets.first()
            if ticket:
                ticket.log_activity(
                    TicketActivity.ACTION_QUESTIONNAIRE, user=actor,
                    content=f"Swapped questionnaire to template “{template.title}”.",
                )
    return questionnaire


def suggest_questionnaire_for_inquiry(inquiry, context):
    """Return (template, already_has) for staff review UI."""
    template = pick_template_for(context, getattr(inquiry, 'industry', ''))
    already = Questionnaire.objects.filter(inquiry=inquiry, context=context).exists()
    return template, already


# Back-compat alias used by older call sites / tests
def create_service_inquiry(*, first_name='', last_name='', email, message, service='other',
                           phone='', organization_name='', industry='',
                           budget_range=ServiceInquiry.BUDGET_UNSPECIFIED, timeline='',
                           preferred_contact_method=Contact.CONTACT_EMAIL,
                           source=ServiceInquiry.SOURCE_WEBSITE, attachments=(), owner=None,
                           subject='', priority=Ticket.PRIORITY_NORMAL,
                           ticket_type=Ticket.TYPE_ENQUIRY):
    """Create a ticket-first enquiry (legacy helper name kept for compatibility)."""
    ticket, uploaded = create_ticket(
        subject=subject, description=message, email=email,
        first_name=first_name, last_name=last_name, message=message,
        service=service, phone=phone, organization_name=organization_name,
        industry=industry, budget_range=budget_range, timeline=timeline,
        preferred_contact_method=preferred_contact_method, source=source,
        ticket_type=ticket_type, priority=priority, attachments=attachments,
        owner=owner,
    )
    # Legacy callers expected (inquiry, assets). Keep ServiceInquiry creation
    # deferred until staff converts — but tests may assert an inquiry exists.
    # Provide a linked inquiry immediately when legacy signature is used.
    inquiry, _ = convert_ticket_to_inquiry(ticket, user=owner if getattr(owner, 'is_authenticated', False) else None)
    return inquiry, uploaded


# ── WhatsApp Webhook ──────────────────────────────────────
def whatsapp_webhook(request):
    """Handle incoming WhatsApp messages from Meta Cloud API."""
    if request.method == 'GET':
        mode = request.GET.get('hub.mode')
        token = request.GET.get('hub.verify_token')
        challenge = request.GET.get('hub.challenge')
        verify_token = getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', 'vercel-whatsapp-verify')
        if mode == 'subscribe' and token == verify_token and challenge:
            return HttpResponse(challenge, status=200)
        return HttpResponse(status=403)

    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            entry = data.get('entry', [{}])[0]
            changes = entry.get('changes', [])
            for change in changes:
                value = change.get('value', {})
                messages = value.get('messages', [])
                for msg in messages:
                    from_number = msg.get('from', '')
                    text = msg.get('text', {}).get('body', '')
                    if text:
                        _logger.info('WhatsApp received from %s: %s', from_number, text[:200])
            return HttpResponse(status=200)
        except Exception:
            _logger.exception('WhatsApp webhook error')
            return HttpResponse(status=400)

    return HttpResponse(status=405)
