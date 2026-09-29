from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.utils import timezone
from django.db import models
from django.db.models import Count, Q, Sum
from functools import wraps
from app.media import store_uploaded_media
from app.models import (
    Answer, FeatureRequest, MediaAsset, Plan, Project, Questionnaire, Question,
    QuestionnaireEvent, QuestionnaireTemplate, ServiceInquiry, Subscription, Ticket, TicketActivity,
)
from app.crm import (
    attach_questionnaire_for_context, clone_questions, convert_ticket_to_inquiry,
    convert_won_inquiry_to_project, email_questionnaire_to_client, import_questions_into,
    log_questionnaire_event, notify, reopen_questionnaire_for_new_questions,
    send_client_survey_notice, swap_questionnaire_questions,
)
from community.models import Topic, Post
from shop.models import Product, Order, Payment
from home.models import User, Article, Newsletter, NewsletterLog, NewsletterSubscription, Comment, Job, Notification
from adverts.models import Advertisement
from .forms import MediaAssetUploadForm, ServiceInquiryForm

# Staff/Admin access is granted through Django's built-in Groups and permissions.
admin_required = user_passes_test(
    lambda u: u.is_authenticated and (u.groups.filter(name='Staff').exists() or u.groups.filter(name='Administrators').exists() or u.is_superuser),
    login_url='login_view',
    redirect_field_name=None,
)

# Client-only portal access. Staff accounts must not fall through to this area
# even when legacy records still carry the old default client role.
client_required = user_passes_test(
    lambda u: u.is_authenticated and u.groups.filter(name='Clients').exists(),
    login_url='login_view',
    redirect_field_name=None,
)

# Flexible role-based decorator — pass one or more group names
def role_required(*group_names):
    """Decorator that requires the user to be in one of the specified groups."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(settings.LOGIN_URL or 'login_view')
            if not request.user.groups.filter(name__in=group_names).exists():
                return redirect('dashboard_router')
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# Ownership check: user owns the given object or is staff/admin
def check_object_ownership(user, obj, field='owner'):
    """Return True if user owns obj (by field) or is staff/admin."""
    if user.is_superuser or user.is_staff:
        return True
    owner = getattr(obj, field, None)
    return owner is not None and owner == user


# Ownership check for objects with email-based ownership
def check_object_ownership_by_email(user, obj, email_field='email'):
    """Return True if user owns obj by matching email (for client portal)."""
    if user.is_superuser or user.is_staff:
        return True
    obj_email = getattr(obj, email_field, None)
    return obj_email is not None and obj_email == user.email

@login_required(login_url='login_view')
def dashboard_router(request):
    """Route users to the appropriate dashboard based on their role."""
    if not request.user.is_authenticated:
        return redirect('login_view')
    if request.user.is_superuser or request.user.is_staff or request.user.has_perm('home.access_dashboard'):
        return dashboard_index(request)
    return redirect('client_dashboard')


@login_required(login_url='login_view')
@admin_required
def dashboard_index(request):
    """ Main entry point for the Admin Dashboard. """
    lead_stage_summary = ServiceInquiry.funnel_summary()
    article_status_summary = (
        Article.objects.values('status')
        .annotate(total=Count('id'))
        .order_by('status')
    )
    pipeline_value = (
        ServiceInquiry.objects.filter(stage__in=ServiceInquiry.PIPELINE_STAGES[:-1])
        .aggregate(total=Sum('estimated_value'))['total'] or 0
    )
    # ── Commerce analytics ───────────────────────────────────────
    open_orders = Order.objects.exclude(status__in=['delivered', 'cancelled']).count()
    total_orders = Order.objects.count()
    completed_orders = Order.objects.filter(status='delivered').count()
    # ── Community analytics ───────────────────────────────────────
    total_topics = Topic.objects.count()
    total_posts = Post.objects.count()
    # ── Media analytics ───────────────────────────────────────────
    total_assets = MediaAsset.objects.count()
    ready_assets = MediaAsset.objects.filter(status=MediaAsset.STATUS_READY).count()
    failed_assets = MediaAsset.objects.filter(status=MediaAsset.STATUS_FAILED).count()
    # ── Careers analytics ─────────────────────────────────────────
    total_jobs = Job.objects.count()
    active_jobs = Job.objects.filter(is_active=True).count()
    # ── Additional pipeline metrics ────────────────────────────────
    total_leads = ServiceInquiry.objects.count()
    won_leads = ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_WON).count()
    lost_leads = ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_LOST).count()
    open_leads = total_leads - won_leads - lost_leads
    won_value = (
        ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_WON)
        .aggregate(total=Sum('estimated_value'))['total'] or 0
    )
    conversion_rate = round((won_leads / total_leads) * 100, 1) if total_leads else 0.0

    # ── Chart series ────────────────────────────────────────────────
    # Charts are fed in a fixed, meaningful order rather than whatever order
    # the database happens to return, and each series carries the values a
    # contrast-first palette needs. Ordering matters as much as colouring:
    # a funnel read left-to-right has to start wide and end narrow, and a
    # workflow chart has to run draft -> published -> archived.
    stage_choices = dict(ServiceInquiry.STAGE_CHOICES)
    stage_order = list(ServiceInquiry.PIPELINE_STAGES) + [
        key for key, _label in ServiceInquiry.STAGE_CHOICES
        if key not in ServiceInquiry.PIPELINE_STAGES
    ]
    stage_counts = {row['stage']: row for row in lead_stage_summary}
    lead_labels, lead_values, lead_values_kes = [], [], []
    for stage in stage_order:
        if stage not in stage_choices:
            continue
        row = stage_counts.get(stage, {})
        lead_labels.append(stage_choices[stage])
        lead_values.append(row.get('count', 0))
        lead_values_kes.append(float(row.get('value') or 0))
    # Funnel stages with no enquiries yet must still render, otherwise the
    # bar chart silently changes width as data moves around.
    lead_keys = [s for s in stage_order if s in stage_choices]

    article_order = ['draft', 'scheduled', 'published', 'archived']
    article_counts = {row['status']: row['total'] for row in article_status_summary}
    article_status_labels = [
        dict(Article._meta.get_field('status').choices).get(s, s.title()) for s in article_order
    ]
    article_status_values = [article_counts.get(s, 0) for s in article_order]

    project_summary = (
        Project.objects.values('status')
        .annotate(total=Count('id'), value=Sum('estimated_budget'))
        .order_by('status')
    )
    project_order = ['active', 'completed', 'on_hold', 'cancelled']
    project_counts = {row['status']: row for row in project_summary}
    project_status_labels = [
        dict(Project._meta.get_field('status').choices).get(s, s.replace('_', ' ').title())
        for s in project_order
    ]
    project_status_values = [project_counts.get(s, {}).get('total', 0) for s in project_order]
    project_budget_values = [
        float(project_counts.get(s, {}).get('value') or 0) for s in project_order
    ]

    # Newsletter turnout: a genuine funnel, because every stage is a subset
    # of the send. Opening a log moves it to "read", so the counts have to be
    # read as "reached at least this far", not as mutually exclusive buckets.
    logs = NewsletterLog.objects.all()
    delivered = logs.exclude(bounced=True).exclude(status='failed').count()
    opened = logs.filter(opened=True).count()
    clicked = logs.filter(clicked=True).count()
    read = logs.filter(read=True).count()
    bounced = logs.filter(bounced=True).count()
    unsubscribed = logs.filter(unsubscribed=True).count()
    total_logs = logs.count()

    def _rate(part, whole):
        return round((part / whole) * 100, 1) if whole else 0.0

    context = {
        'total_users': User.objects.count(),
        'total_leads': total_leads,
        'recent_leads': ServiceInquiry.objects.order_by('-created_at')[:5],
        'total_topics': total_topics,
        'total_products': Product.objects.count(),
        'open_orders': open_orders,
        'total_orders': total_orders,
        'completed_orders': completed_orders,
        'published_articles': Article.objects.filter(status='published').count(),
        'pipeline_value': pipeline_value,
        # Chart series.
        'lead_chart_keys': lead_keys,
        'lead_chart_labels': lead_labels,
        'lead_chart_values': lead_values,
        'lead_chart_values_kes': lead_values_kes,
        'article_chart_labels': article_status_labels,
        'article_chart_values': article_status_values,
        'article_chart_keys': article_order,
        'project_chart_labels': project_status_labels,
        'project_chart_values': project_status_values,
        'project_chart_budget': project_budget_values,
        'project_chart_keys': project_order,
        'newsletter_chart_labels': ['Delivered', 'Opened', 'Read', 'Clicked', 'Unsubscribed', 'Bounced'],
        'newsletter_chart_values': [delivered, opened, read, clicked, unsubscribed, bounced],
        'newsletter_chart_rates': [
            _rate(delivered, total_logs), _rate(opened, delivered),
            _rate(read, delivered), _rate(clicked, delivered),
            _rate(unsubscribed, delivered), _rate(bounced, total_logs),
        ],
        'newsletter_total_sends': total_logs,
        'page_title': 'Dovetec Hub (CRM & CMS)'
    }
    return render(request, 'dashboard/index.html', context)


# ─────────────────────────────────────────────────────────────────
# CLIENT PORTAL DASHBOARD VIEWS
# ─────────────────────────────────────────────────────────────────

@login_required(login_url='login_view')
@client_required
def client_dashboard(request):
    """Client portal home — overview of recent activity."""
    user = request.user
    try:
        profile = user.profile
    except Exception:
        profile = None

    # Orders placed with the user's email - client-owned only
    orders = Order.objects.filter(customer_email=user.email).order_by('-order_date')[:10]

    # Published articles authored by the user - client-owned only
    articles = Article.objects.filter(user=user, status='published').order_by('-created_at')[:5]

    # Draft articles awaiting review - client-owned only
    draft_articles = Article.objects.filter(user=user, status='draft').order_by('-created_at')[:5]

    # Recent payments - client-owned only
    recent_payments = Payment.objects.filter(order__customer_email=user.email).order_by('-payment_date')[:5]

    context = {
        'profile': profile,
        'orders': orders,
        'articles': articles,
        'draft_articles': draft_articles,
        'recent_payments': recent_payments,
        'page_title': 'My Portal',
    }
    return render(request, 'dashboard/client/dashboard.html', context)


@login_required(login_url='login_view')
@client_required
def client_orders(request):
    """List all orders associated with the logged-in client."""
    user = request.user
    orders = Order.objects.filter(customer_email=user.email).order_by('-order_date')

    context = {
        'orders': orders,
        'page_title': 'My Orders',
    }
    return render(request, 'dashboard/client/orders.html', context)


@login_required(login_url='login_view')
@client_required
def client_order_detail(request, order_id):
    """Detailed view of a single order placed by the client."""
    user = request.user
    order = get_object_or_404(Order, id=order_id, customer_email=user.email)
    items = order.items.select_related('product').all()
    payments = order.payments.all().order_by('-payment_date')

    context = {
        'order': order,
        'items': items,
        'payments': payments,
        'page_title': f'Order #{order.id}',
    }
    return render(request, 'dashboard/client/order_detail.html', context)


@login_required(login_url='login_view')
@client_required
def client_articles(request):
    """List all articles authored by the logged-in client."""
    user = request.user
    articles = Article.objects.filter(user=user).order_by('-created_at')

    context = {
        'articles': articles,
        'page_title': 'My Articles',
    }
    return render(request, 'dashboard/client/articles.html', context)


@login_required(login_url='login_view')
@client_required
def client_profile_view(request):
    """Display the client's profile information."""
    user = request.user
    profile = None
    try:
        profile = user.profile
    except Exception:
        pass

    context = {
        'user': user,
        'profile': profile,
        'page_title': 'My Profile',
    }
    return render(request, 'dashboard/client/profile.html', context)

@login_required
@admin_required
def dashboard_clients(request):
    """ CRM: Manage registered clients/users """
    users = User.objects.all().order_by('-date_joined')
    context = {
        'users': users,
        'page_title': 'Clients Database'
    }
    return render(request, 'dashboard/crm_clients.html', context)

@login_required
@admin_required
def dashboard_inquiries(request):
    """ CRM: Manage service inquiries and leads """
    inquiries = ServiceInquiry.objects.select_related('organization', 'contact', 'assigned_to').order_by('-created_at')
    context = {
        'inquiries': inquiries,
        'page_title': 'Service Inquiries Pipeline'
    }
    return render(request, 'dashboard/crm_inquiries.html', context)


@login_required
@admin_required
def dashboard_funnel(request):
    """
    CRM: Sales funnel pipeline — leads grouped by stage from first
    contact (New Lead) through to close (Won) plus Lost.
    """
    from django.db.models import Sum
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from decimal import Decimal, InvalidOperation

    stages = ServiceInquiry.PIPELINE_STAGES + [ServiceInquiry.STAGE_LOST]
    stage_labels = dict(ServiceInquiry.STAGE_CHOICES)

    stage_columns = []
    for stage in stages:
        leads = (
            ServiceInquiry.objects
            .filter(stage=stage)
            .select_related('assigned_to')
        )
        stage_columns.append({
            'stage': stage,
            'label': stage_labels[stage],
            'leads': leads,
            'count': leads.count(),
            'value': sum((l.estimated_value for l in leads), Decimal('0')),
        })

    # ── Funnel analytics ─────────────────────────────────────────
    total_leads = ServiceInquiry.objects.count()
    won_leads = ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_WON).count()
    lost_leads = ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_LOST).count()
    open_leads = total_leads - won_leads - lost_leads
    won_value = (
        ServiceInquiry.objects.filter(stage=ServiceInquiry.STAGE_WON)
        .aggregate(total=Sum('estimated_value'))['total'] or Decimal('0')
    )
    pipeline_value = sum(
        (col['value'] for col in stage_columns if col['stage'] != ServiceInquiry.STAGE_LOST),
        Decimal('0'),
    )
    conversion_rate = round((won_leads / total_leads) * 100, 1) if total_leads else 0.0

    # Sales reps available for lead assignment
    User = get_user_model()
    sales_reps = User.objects.filter(is_staff=True)

    context = {
        'stage_columns': stage_columns,
        'stage_choices': ServiceInquiry.STAGE_CHOICES,
        'sales_reps': sales_reps,
        'total_leads': total_leads,
        'won_leads': won_leads,
        'lost_leads': lost_leads,
        'open_leads': open_leads,
        'won_value': won_value,
        'pipeline_value': pipeline_value,
        'conversion_rate': conversion_rate,
        'page_title': 'Sales Funnel (Lead → Close)',
    }
    return render(request, 'dashboard/crm_funnel.html', context)


@login_required
@admin_required
def funnel_inquiry_detail(request, inquiry_id):
    """CRM: Read-only detail page for a single sales-funnel lead.

    Shows every field, lets the admin move the lead between stages
    (POST to ``funnel_update_stage``), and links out to the generic
    edit / delete views and to the questionnaire builder.
    """
    inquiry = get_object_or_404(
        ServiceInquiry.objects.select_related('organization', 'contact', 'assigned_to'),
        id=inquiry_id,
    )
    context = {
        'inquiry': inquiry,
        'stage_choices': ServiceInquiry.STAGE_CHOICES,
        'page_title': f"Lead — {inquiry.name}",
    }
    return render(request, 'dashboard/crm_inquiry_detail.html', context)


@login_required
@admin_required
def funnel_update_stage(request, inquiry_id):
    """
    CRM: Move a lead to a different funnel stage (forward, backward,
    won or lost). POST only.
    """
    from django.utils import timezone

    inquiry = get_object_or_404(ServiceInquiry, id=inquiry_id)

    if request.method == 'POST':
        new_stage = request.POST.get('stage')
        valid_stages = [c[0] for c in ServiceInquiry.STAGE_CHOICES]

        if new_stage in valid_stages:
            old_stage = inquiry.stage
            inquiry.stage = new_stage
            if new_stage == ServiceInquiry.STAGE_WON and not inquiry.converted_at:
                inquiry.converted_at = timezone.now()
            inquiry.save()
            messages.success(request, f"{inquiry.name} moved to {inquiry.get_stage_display()}.")
            recipients = [u for u in [inquiry.assigned_to, request.user] if u]
            notify(
                recipients=recipients, verb='stage_change',
                title=f"Lead moved to {inquiry.get_stage_display()}",
                body=f"{inquiry.name} · {old_stage} → {new_stage}",
                link=f"/dashboard/crm/funnel/{inquiry.id}/",
                actor=request.user,
            )
            # Contextual questionnaire suggestions (staff reviews before send)
            if new_stage == ServiceInquiry.STAGE_QUALIFIED:
                qs, status = attach_questionnaire_for_context(
                    inquiry, QuestionnaireTemplate.CONTEXT_DISCOVERY, actor=request.user,
                )
                if status == 'created':
                    messages.info(
                        request,
                        f"Discovery questionnaire auto-attached from template “{qs.source_template}”. "
                        "Review and send when ready.",
                    )
            elif new_stage == ServiceInquiry.STAGE_WON:
                project, created_project = convert_won_inquiry_to_project(
                    inquiry, actor=request.user,
                )
                if created_project:
                    messages.success(
                        request,
                        f"Delivery project “{project.name}” created from this won deal.",
                    )
                qs, status = attach_questionnaire_for_context(
                    inquiry, QuestionnaireTemplate.CONTEXT_ONBOARDING, actor=request.user,
                )
                if status == 'created':
                    messages.info(
                        request,
                        f"Onboarding questionnaire auto-attached from template “{qs.source_template}”.",
                    )
        else:
            messages.error(request, 'Invalid funnel stage.')

    return redirect(request.POST.get('next') or 'dashboard_funnel')


@login_required
@admin_required
def funnel_update_lead(request, inquiry_id):
    """
    CRM: Update deal details (value, assignment, notes) for a lead.
    """
    from decimal import Decimal, InvalidOperation
    from django.contrib.auth import get_user_model

    inquiry = get_object_or_404(ServiceInquiry, id=inquiry_id)

    if request.method == 'POST':
        value = request.POST.get('estimated_value')
        assigned_to_id = request.POST.get('assigned_to')
        notes = request.POST.get('notes', '').strip()

        if value:
            try:
                inquiry.estimated_value = Decimal(value)
            except (InvalidOperation, ValueError):
                messages.error(request, 'Invalid deal value.')
                return redirect('dashboard_funnel')

        User = get_user_model()
        if assigned_to_id:
            inquiry.assigned_to = User.objects.filter(id=assigned_to_id, is_staff=True).first()
        else:
            inquiry.assigned_to = None

        inquiry.notes = notes or None
        inquiry.save()
        messages.success(request, f"Lead {inquiry.name} updated.")

    return redirect(request.POST.get('next') or 'dashboard_funnel')


# ─────────────────────────────────────────────────────────────────
# QUESTIONNAIRES — custom per inquiry / service request (full CRUD)
# ─────────────────────────────────────────────────────────────────

@login_required
@admin_required
def funnel_questionnaire(request, inquiry_id):
    """
    CRM: Build and manage the custom questionnaire attached to a lead's
    service request — full CRUD on questions plus response collection.
    """
    inquiry = get_object_or_404(ServiceInquiry, id=inquiry_id)
    questionnaire = inquiry.questionnaires.order_by('-created_at').first()
    if questionnaire is None:
        questionnaire = Questionnaire.objects.create(
            inquiry=inquiry,
            title=f"{inquiry.get_service_display()} Requirements — {inquiry.name}",
        )

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add_question':
            text = request.POST.get('text', '').strip()
            if text:
                question = Question.objects.create(
                    questionnaire=questionnaire,
                    text=text[:500],
                    help_text=request.POST.get('help_text', '').strip() or None,
                    question_type=request.POST.get('question_type', Question.TYPE_TEXT),
                    options=request.POST.get('options', '').strip() or None,
                    required=bool(request.POST.get('required')),
                    order=questionnaire.questions.count() + 1,
                )
                log_questionnaire_event(
                    questionnaire,
                    QuestionnaireEvent.ACTION_QUESTION_ADDED,
                    question=question,
                    actor=request.user,
                    content=f'Added question: {question.text[:200]}',
                )
                # A new question means the client must revisit the form;
                # existing answers are kept so prior responses stay valid.
                reopened = reopen_questionnaire_for_new_questions(questionnaire)
                if reopened:
                    log_questionnaire_event(
                        questionnaire,
                        QuestionnaireEvent.ACTION_REOPENED,
                        actor=request.user,
                        content='Reopened after new question; existing answers preserved.',
                    )
                    emailed = email_questionnaire_to_client(
                        questionnaire, kind='reopened',
                        question_count=questionnaire.question_count,
                    )
                    messages.success(
                        request,
                        'Question added. Existing responses kept — '
                        + ('client emailed to complete the new question.' if emailed
                           else 'client notified in portal.'),
                    )
                else:
                    messages.success(request, 'Question added. Existing responses kept.')
            else:
                messages.error(request, 'Question text is required.')

        elif action == 'edit_question':
            question = questionnaire.questions.filter(id=request.POST.get('question_id')).first()
            if question:
                question.text = request.POST.get('text', '').strip() or question.text
                question.help_text = request.POST.get('help_text', '').strip() or None
                question.question_type = request.POST.get('question_type', question.question_type)
                question.options = request.POST.get('options', '').strip() or None
                question.required = bool(request.POST.get('required'))
                question.save()
                messages.success(request, 'Question updated.')
            else:
                messages.error(request, 'Question not found.')

        elif action == 'move_question':
            question = questionnaire.questions.filter(id=request.POST.get('question_id')).first()
            direction = request.POST.get('direction')
            if question and direction == 'up' and question.order > 1:
                Question.objects.filter(questionnaire=questionnaire, order=question.order - 1).update(order=question.order)
                question.order -= 1
                question.save()
                messages.success(request, 'Question reordered.')
            elif question and direction == 'down':
                Question.objects.filter(questionnaire=questionnaire, order=question.order + 1).update(order=question.order)
                question.order += 1
                question.save()
                messages.success(request, 'Question reordered.')

        elif action == 'delete_question':
            questionnaire.questions.filter(id=request.POST.get('question_id')).delete()
            messages.success(request, 'Question removed.')

        elif action == 'update_meta':
            questionnaire.title = request.POST.get('title', questionnaire.title).strip() or questionnaire.title
            questionnaire.intro = request.POST.get('intro', '').strip() or None
            questionnaire.save()
            messages.success(request, 'Questionnaire details saved.')

        elif action == 'send':
            if questionnaire.questions.exists():
                questionnaire.status = 'sent'
                questionnaire.save()
                send_client_survey_notice(
                    questionnaire, kind='sent', actor=request.user,
                    question_count=questionnaire.question_count,
                )
                notify(
                    recipients=[u for u in [inquiry.assigned_to, request.user] if u],
                    verb='questionnaire_sent',
                    title=f"Questionnaire sent to {inquiry.email}",
                    body=questionnaire.title,
                    link=f"/dashboard/crm/funnel/{inquiry.id}/questionnaire/",
                    actor=request.user,
                )
                messages.success(
                    request,
                    f"Questionnaire emailed to {inquiry.email} with context directives. "
                    "It now appears in their client portal.",
                )
            else:
                messages.error(request, 'Add at least one question before sending.')

        elif action == 'reset':
            questionnaire.status = 'draft'
            questionnaire.save()
            messages.success(request, 'Questionnaire reset to draft.')

        elif action == 'clear_responses':
            Answer.objects.filter(question__questionnaire=questionnaire).delete()
            questionnaire.status = 'sent'
            questionnaire.completed_at = None
            questionnaire.save()
            log_questionnaire_event(
                questionnaire,
                QuestionnaireEvent.ACTION_CLEAR_RESPONSES,
                actor=request.user,
                content='All client responses cleared; questionnaire reopened.',
            )
            messages.success(request, 'All client responses cleared. The questionnaire is open again.')

        elif action == 'delete_questionnaire':
            questionnaire.delete()
            messages.success(request, f"Questionnaire for {inquiry.name} deleted.")
            return redirect('dashboard_funnel')

        elif action == 'attach_template':
            template_id = request.POST.get('template_id')
            template = QuestionnaireTemplate.objects.filter(id=template_id, is_active=True).first()
            if template:
                if questionnaire.questions.exists() and not request.POST.get('confirm_replace'):
                    messages.error(
                        request,
                        'This questionnaire already has questions. Confirm replace to swap, '
                        'or clear questions first.',
                    )
                else:
                    questionnaire.delete()
                    new_q, status = attach_questionnaire_for_context(
                        inquiry, template.context, actor=request.user, template=template,
                    )
                    if status == 'exists':
                        messages.error(request, 'A questionnaire already exists for this lead.')
                    elif status == 'no_template':
                        messages.error(request, 'Template not found.')
                    else:
                        messages.success(
                            request,
                            f"Attached template “{template.title}” ({template.get_context_display()}).",
                        )
            else:
                messages.error(request, 'Template not found or inactive.')

        elif action == 'swap_template':
            template_id = request.POST.get('template_id')
            template = QuestionnaireTemplate.objects.filter(id=template_id, is_active=True).first()
            if template:
                if questionnaire.questions.exists() and not request.POST.get('confirm_replace'):
                    messages.error(
                        request,
                        'Confirm replace to swap all questions with this template '
                        '(this clears answers). Prefer “Merge packages” to keep responses.',
                    )
                else:
                    swap_questionnaire_questions(questionnaire, template, actor=request.user)
                    messages.success(
                        request,
                        f"Swapped to template “{template.title}”. Existing answers were cleared.",
                    )
            else:
                messages.error(request, 'Template not found or inactive.')

        elif action == 'import_questions':
            # Merge packages: multi-select templates and/or one detailed source.
            # Never clears existing questions or answers.
            source_ids = request.POST.getlist('import_template_ids')
            single_id = request.POST.get('source_template_id')
            question_ids = request.POST.getlist('import_question_ids')
            if single_id and single_id not in source_ids:
                source_ids.append(single_id)
            sources = list(
                QuestionnaireTemplate.objects.filter(id__in=source_ids).distinct()
            )
            if not sources:
                messages.error(request, 'Select at least one package to import from.')
            else:
                total_added = total_skipped = 0
                any_result_reopened = False
                for source in sources:
                    ids = None
                    if (
                        single_id
                        and str(source.id) == str(single_id)
                        and question_ids
                    ):
                        ids = question_ids
                    result = import_questions_into(questionnaire, source, ids)
                    total_added += result['added']
                    total_skipped += result['skipped']
                    any_result_reopened = any_result_reopened or result.get('reopened', False)
                detail = (
                    f"Merged {total_added} question(s) from {len(sources)} package(s)."
                    if total_added
                    else 'No new questions to merge — all were already present.'
                )
                if total_skipped:
                    detail += f" Skipped {total_skipped} duplicate(s)."
                if total_added:
                    detail += ' Existing answers kept.'
                    if any_result_reopened:
                        detail += ' Client emailed about the new questions.'
                messages.success(request, detail)

        return redirect('funnel_questionnaire', inquiry_id=inquiry.id)

    templates = QuestionnaireTemplate.objects.filter(is_active=True)
    import_source = None
    source_id = request.GET.get('source')
    if source_id:
        import_source = QuestionnaireTemplate.objects.filter(id=source_id).first()
    context = {
        'inquiry': inquiry,
        'questionnaire': questionnaire,
        'questions': questionnaire.questions.prefetch_related('answers'),
        'question_types': Question.QUESTION_TYPES,
        'templates': templates,
        'import_source': import_source,
        'page_title': f"Questionnaire — {inquiry.name}",
    }
    return render(request, 'dashboard/crm_questionnaire.html', context)


@login_required
@admin_required
def questionnaire_list(request):
    """CRM: Master list of all questionnaires with search + delete."""
    from django.db.models import Q

    query = request.GET.get('q', '').strip()
    questionnaires = Questionnaire.objects.select_related('inquiry').order_by('-updated_at')
    if query:
        questionnaires = questionnaires.filter(
            Q(title__icontains=query) |
            Q(inquiry__name__icontains=query) |
            Q(inquiry__email__icontains=query)
        )

    if request.method == 'POST' and request.POST.get('action') == 'delete':
        Questionnaire.objects.filter(id=request.POST.get('questionnaire_id')).delete()
        messages.success(request, 'Questionnaire deleted.')
        return redirect('questionnaire_list')

    context = {
        'questionnaires': questionnaires,
        'query': query,
        'page_title': 'Questionnaires',
    }
    return render(request, 'dashboard/crm_questionnaires.html', context)


@login_required
@admin_required
def questionnaire_responses(request, questionnaire_id):
    """
    CRM: Collect and manage client responses — review, edit or delete
    individual answers, and export everything as CSV.
    """
    questionnaire = get_object_or_404(Questionnaire, id=questionnaire_id)
    inquiry = questionnaire.inquiry

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'edit_answer':
            answer = Answer.objects.filter(
                id=request.POST.get('answer_id'),
                question__questionnaire=questionnaire,
            ).first()
            if answer:
                previous = answer.answer or ''
                question_obj = answer.question
                answer.answer = request.POST.get('answer', '').strip() or None
                answer.save()
                log_questionnaire_event(
                    questionnaire,
                    QuestionnaireEvent.ACTION_STAFF_EDITED,
                    question=question_obj,
                    actor=request.user,
                    content=(
                        f'Staff corrected “{(question_obj.text if question_obj else "")[:120]}”'
                        + (f' (was: {previous[:80]})' if previous else '')
                    ),
                    answer_snapshot=answer.answer,
                )
                messages.success(request, 'Response updated. Change logged to the activity timeline.')
        elif action == 'delete_answer':
            answer = Answer.objects.filter(
                id=request.POST.get('answer_id'),
                question__questionnaire=questionnaire,
            ).first()
            if answer:
                snapshot = answer.answer
                question_obj = answer.question
                qtext = question_obj.text if question_obj else ''
                answer_pk = answer.pk
                answer.delete()
                log_questionnaire_event(
                    questionnaire,
                    QuestionnaireEvent.ACTION_STAFF_DELETED,
                    question=question_obj,
                    actor=request.user,
                    content=f'Staff deleted answer for “{(qtext or "")[:120]}”.',
                    answer_snapshot=snapshot,
                )
            remaining = questionnaire.answered_count
            if remaining == questionnaire.question_count and questionnaire.question_count:
                questionnaire.status = 'completed'
            else:
                questionnaire.status = 'sent'
                questionnaire.completed_at = None
            questionnaire.save()
            messages.success(request, 'Response deleted. Change logged to the activity timeline.')
        return redirect('questionnaire_responses', questionnaire_id=questionnaire.id)

    questions = questionnaire.questions.prefetch_related('answers')
    activity = questionnaire.events.select_related('question', 'actor')[:50]

    # ── CSV export ───────────────────────────────────────────────
    if request.GET.get('format') == 'csv':
        import csv
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = (
            f'attachment; filename="questionnaire-{questionnaire.id}-{inquiry.email}.csv"'
        )
        writer = csv.writer(response)
        writer.writerow(['Client', 'Email', 'Service', 'Question #', 'Question', 'Type', 'Answer', 'Answered At'])
        for q in questions:
            answer = q.client_answer()
            writer.writerow([
                inquiry.name, inquiry.email, inquiry.get_service_display(),
                q.order, q.text, q.get_question_type_display(),
                answer.answer if answer else '', answer.updated_at if answer else '',
            ])
        return response

    context = {
        'questionnaire': questionnaire,
        'inquiry': inquiry,
        'questions': questions,
        'activity': activity,
        'page_title': f"Responses — {questionnaire.title}",
    }
    return render(request, 'dashboard/crm_responses.html', context)


# ── Client portal questionnaire views ─────────────────────────────

@login_required(login_url='login_view')
@client_required
def client_questionnaires(request):
    """List the questionnaires attached to this client's inquiries."""
    questionnaires = (
        Questionnaire.objects
        .filter(inquiry__email=request.user.email)
        .select_related('inquiry')
    )
    context = {
        'questionnaires': questionnaires,
        'page_title': 'My Questionnaires',
    }
    return render(request, 'dashboard/client/questionnaires.html', context)


@login_required(login_url='login_view')
@client_required
def client_questionnaire_fill(request, questionnaire_id):
    """
    Client fills in (or reviews) the questionnaire attached to their
    service request. Locked once completed — reopened automatically
    if the admin adds new questions.
    """
    questionnaire = get_object_or_404(
        Questionnaire,
        id=questionnaire_id,
        inquiry__email=request.user.email,  # ownership check
    )
    questions = questionnaire.questions.all()

    if request.method == 'POST' and questionnaire.is_editable_by_client:
        answered_any = False
        changed = 0
        for question in questions:
            raw = request.POST.get(f'question_{question.id}', '').strip()
            if raw:
                answered_any = True
            existing = Answer.objects.filter(question=question).first()
            previous = (existing.answer or '') if existing else None
            answer, was_created = Answer.objects.update_or_create(
                question=question,
                defaults={'answer': raw or None},
            )
            if was_created and raw:
                changed += 1
                log_questionnaire_event(
                    questionnaire,
                    QuestionnaireEvent.ACTION_ANSWERED,
                    question=question,
                    actor=request.user,
                    content=f'Client answered “{question.text[:160]}”',
                    answer_snapshot=raw,
                )
            elif existing is not None and (raw or '') != (previous or ''):
                changed += 1
                log_questionnaire_event(
                    questionnaire,
                    QuestionnaireEvent.ACTION_UPDATED,
                    question=question,
                    actor=request.user,
                    content=(
                        f'Client updated “{question.text[:160]}”'
                        + (f' (was: {previous[:80]})' if previous else '')
                    ),
                    answer_snapshot=raw,
                )

        questionnaire.status = 'completed' if answered_any else 'in_progress'
        questionnaire.completed_at = timezone.now() if answered_any else None
        questionnaire.save()

        if answered_any:
            event, emailed = send_client_survey_notice(
                questionnaire, kind='completed', actor=request.user,
                changed_count=changed,
            )
            # Staff in-app (and optional email) when fully done
            if questionnaire.status == 'completed' and questionnaire.inquiry.assigned_to:
                notify(
                    recipients=[questionnaire.inquiry.assigned_to],
                    verb='questionnaire_completed',
                    title=f"Questionnaire completed: {questionnaire.title}",
                    body=questionnaire.inquiry.email,
                    link=f"/dashboard/crm/questionnaires/{questionnaire.id}/responses/",
                    actor=request.user,
                )
        else:
            log_questionnaire_event(
                questionnaire,
                QuestionnaireEvent.ACTION_UPDATED,
                actor=request.user,
                content='Client saved progress without final answers.',
            )

        messages.success(request, 'Your responses have been submitted. Thank you!')
        return redirect('client_questionnaire_fill', questionnaire_id=questionnaire.id)

    answer_map = {
        a.question_id: a.answer
        for a in Answer.objects.filter(question__questionnaire=questionnaire)
    }

    context = {
        'questionnaire': questionnaire,
        'questions': questions,
        'answer_map': answer_map,
        'readonly': not questionnaire.is_editable_by_client,
        'page_title': questionnaire.title,
    }
    return render(request, 'dashboard/client/questionnaire_fill.html', context)

@login_required
@admin_required
def dashboard_forums(request):
    """ CMS: Manage community topics """
    topics = Topic.objects.select_related('category').order_by('-created_at')
    context = {
        'topics': topics,
        'page_title': 'Community Forums CMS'
    }
    return render(request, 'dashboard/cms_forums.html', context)


@login_required
@admin_required
def dashboard_projects(request):
    """CRM: Manage delivery projects."""
    projects = Project.objects.select_related('organization', 'contact', 'converted_from_inquiry').order_by('-created_at')
    context = {
        'projects': projects,
        'page_title': 'Delivery Projects',
    }
    return render(request, 'dashboard/crm_projects.html', context)


# ── Support ticket queue (issues first) ─────────────────────────────

@login_required
@admin_required
def ticket_queue(request):
    """Staff queue: my / unassigned / all tickets with filters."""
    scope = request.GET.get('scope', 'mine')
    status_f = request.GET.get('status', '')
    priority_f = request.GET.get('priority', '')
    type_f = request.GET.get('type', '')
    q = request.GET.get('q', '').strip()

    tickets = Ticket.objects.select_related(
        'contact', 'organization', 'assigned_to', 'referred_to', 'inquiry',
    )
    if scope == 'mine':
        tickets = tickets.filter(assigned_to=request.user)
    elif scope == 'unassigned':
        tickets = tickets.filter(assigned_to__isnull=True, status__in=Ticket.OPEN_STATUSES)
    elif scope == 'open':
        tickets = tickets.filter(status__in=Ticket.OPEN_STATUSES)
    elif scope == 'referred':
        tickets = tickets.filter(referred_to=request.user)
    # else all

    if status_f:
        tickets = tickets.filter(status=status_f)
    if priority_f:
        tickets = tickets.filter(priority=priority_f)
    if type_f:
        tickets = tickets.filter(type=type_f)
    if q:
        tickets = tickets.filter(
            Q(reference__icontains=q) | Q(subject__icontains=q)
            | Q(description__icontains=q) | Q(contact__email__icontains=q)
            | Q(contact__first_name__icontains=q)
        )

    counts = {
        'mine': Ticket.objects.filter(assigned_to=request.user, status__in=Ticket.OPEN_STATUSES).count(),
        'unassigned': Ticket.objects.filter(assigned_to__isnull=True, status__in=Ticket.OPEN_STATUSES).count(),
        'open': Ticket.objects.filter(status__in=Ticket.OPEN_STATUSES).count(),
        'referred': Ticket.objects.filter(referred_to=request.user).count(),
        'all': Ticket.objects.count(),
        'urgent': Ticket.objects.filter(priority=Ticket.PRIORITY_URGENT, status__in=Ticket.OPEN_STATUSES).count(),
    }
    staff = User.objects.filter(is_staff=True).order_by('first_name', 'last_name', 'email')
    context = {
        'tickets': tickets[:200],
        'scope': scope,
        'status_f': status_f,
        'priority_f': priority_f,
        'type_f': type_f,
        'q': q,
        'counts': counts,
        'staff': staff,
        'status_choices': Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'type_choices': Ticket.TYPE_CHOICES,
        'page_title': 'Support Tickets',
    }
    return render(request, 'dashboard/crm_tickets.html', context)


@login_required
@admin_required
def ticket_detail(request, ticket_id):
    """Ticket detail: status, transfer, refer, priority, notes, convert."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('contact', 'organization', 'assigned_to', 'referred_to', 'inquiry'),
        id=ticket_id,
    )
    staff = User.objects.filter(is_staff=True).order_by('first_name', 'last_name', 'email')
    import_templates = QuestionnaireTemplate.objects.filter(is_active=True)

    if request.method == 'POST':
        action = request.POST.get('action')
        note = request.POST.get('content', '').strip()

        if action == 'status':
            new_status = request.POST.get('status')
            valid = {c[0] for c in Ticket.STATUS_CHOICES}
            if new_status in valid and new_status != ticket.status:
                old = ticket.status
                ticket.status = new_status
                if new_status == Ticket.STATUS_RESOLVED and not ticket.resolved_at:
                    ticket.resolved_at = timezone.now()
                if new_status in Ticket.OPEN_STATUSES:
                    ticket.resolved_at = None
                ticket.save()
                ticket.log_activity(
                    TicketActivity.ACTION_STATUS_CHANGE, user=request.user,
                    content=f"{old} → {new_status}" + (f" · {note}" if note else ''),
                )
                notify(
                    recipients=[u for u in [ticket.assigned_to, request.user] if u],
                    verb='status_change',
                    title=f"{ticket.reference} → {ticket.get_status_display()}",
                    body=ticket.subject,
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
                if new_status == Ticket.STATUS_RESOLVED:
                    sug = QuestionnaireTemplate.objects.filter(
                        is_active=True, context=QuestionnaireTemplate.CONTEXT_SATISFACTION,
                    ).first()
                    if sug:
                        messages.info(
                            request,
                            f"Satisfaction template “{sug.title}” available — attach from the questionnaire panel.",
                        )
                messages.success(request, f"Status set to {ticket.get_status_display()}.")
            else:
                messages.error(request, 'Invalid status.')

        elif action == 'priority':
            new_p = request.POST.get('priority')
            valid = {c[0] for c in Ticket.PRIORITY_CHOICES}
            if new_p in valid and new_p != ticket.priority:
                old = ticket.priority
                ticket.priority = new_p
                ticket.save()
                ticket.log_activity(
                    TicketActivity.ACTION_PRIORITY_CHANGE, user=request.user,
                    content=f"{old} → {new_p}" + (f" · {note}" if note else ''),
                )
                notify(
                    recipients=[u for u in [ticket.assigned_to, request.user] if u],
                    verb='priority_change',
                    title=f"{ticket.reference} priority → {ticket.get_priority_display()}",
                    body=ticket.subject,
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
                messages.success(request, f"Priority set to {ticket.get_priority_display()}.")
            else:
                messages.error(request, 'Invalid priority.')

        elif action == 'assign':
            user_id = request.POST.get('user_id')
            new_assignee = User.objects.filter(id=user_id, is_staff=True).first() if user_id else None
            old = ticket.assigned_to
            if new_assignee != old:
                ticket.assigned_to = new_assignee
                ticket.save()
                ticket.log_activity(
                    TicketActivity.ACTION_ASSIGNED, user=request.user,
                    from_user=old, to_user=new_assignee, content=note,
                )
                recipients = [u for u in [old, new_assignee, request.user] if u]
                notify(
                    recipients=recipients, verb='assigned',
                    title=f"{ticket.reference} assigned to {new_assignee or 'Unassigned'}",
                    body=ticket.subject,
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
                messages.success(request, f"Assigned to {new_assignee or 'Unassigned'}.")
            else:
                messages.info(request, 'Assignee unchanged.')

        elif action == 'transfer':
            user_id = request.POST.get('user_id')
            new_assignee = User.objects.filter(id=user_id, is_staff=True).first()
            if not new_assignee:
                messages.error(request, 'Choose a staff member to transfer to.')
            elif note == '':
                messages.error(request, 'A transfer reason/note is required.')
            else:
                old = ticket.assigned_to
                ticket.assigned_to = new_assignee
                ticket.referred_to = None
                ticket.save()
                ticket.log_activity(
                    TicketActivity.ACTION_TRANSFERRED, user=request.user,
                    from_user=old, to_user=new_assignee, content=note,
                )
                notify(
                    recipients=[u for u in [old, new_assignee, request.user] if u],
                    verb='transferred',
                    title=f"{ticket.reference} transferred to {new_assignee.get_short_name()}",
                    body=note[:400],
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
                messages.success(request, f"Transferred to {new_assignee.get_short_name()}.")

        elif action == 'refer':
            user_id = request.POST.get('user_id')
            referee = User.objects.filter(id=user_id, is_staff=True).first()
            if not referee:
                messages.error(request, 'Choose a staff member to refer to.')
            elif note == '':
                messages.error(request, 'A referral note is required.')
            else:
                ticket.referred_to = referee
                ticket.save()
                ticket.log_activity(
                    TicketActivity.ACTION_REFERRED, user=request.user,
                    from_user=ticket.assigned_to, to_user=referee, content=note,
                )
                notify(
                    recipients=[referee, request.user], verb='referred',
                    title=f"You were referred {ticket.reference} by {request.user.get_short_name()}",
                    body=note[:400],
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
                messages.success(request, f"Referred to {referee.get_short_name()} (ownership unchanged).")

        elif action == 'accept_transfer':
            old = ticket.assigned_to
            ticket.assigned_to = request.user
            ticket.referred_to = None
            ticket.save()
            ticket.log_activity(
                TicketActivity.ACTION_TRANSFERRED, user=request.user,
                from_user=old, to_user=request.user, content='Accepted referral / took ownership.',
            )
            notify(
                recipients=[u for u in [old, request.user] if u],
                verb='transferred',
                title=f"{ticket.reference} now owned by {request.user.get_short_name()}",
                body=ticket.subject,
                link=f"/dashboard/crm/tickets/{ticket.id}/",
                actor=request.user,
            )
            messages.success(request, 'You now own this ticket.')

        elif action == 'note':
            if note:
                ticket.log_activity(TicketActivity.ACTION_NOTE, user=request.user, content=note)
                messages.success(request, 'Note added.')
            else:
                messages.error(request, 'Note text is required.')

        elif action == 'escalate':
            if ticket.inquiry_id:
                messages.info(request, 'Already escalated to the sales funnel.')
            else:
                stage = request.POST.get('stage', ServiceInquiry.STAGE_NEW)
                if stage not in {c[0] for c in ServiceInquiry.STAGE_CHOICES}:
                    stage = ServiceInquiry.STAGE_NEW
                context_choice = request.POST.get('questionnaire_context', '')
                inquiry, _ = convert_ticket_to_inquiry(
                    ticket, user=request.user, stage=stage,
                    auto_questionnaire_context=context_choice or None,
                )
                messages.success(
                    request,
                    f"Escalated to sales lead “{inquiry.name}” ({inquiry.get_stage_display()}).",
                )
                return redirect('funnel_inquiry_detail', inquiry_id=inquiry.id)

        elif action == 'attach_questionnaire':
            template_id = request.POST.get('template_id')
            template = QuestionnaireTemplate.objects.filter(id=template_id, is_active=True).first()
            if not template:
                messages.error(request, 'Template not found.')
            elif not ticket.inquiry_id:
                messages.error(request, 'Escalate to sales first, or questionnaire needs a lead.')
            else:
                q, status = attach_questionnaire_for_context(
                    ticket.inquiry, template.context, actor=request.user, template=template,
                )
                if status == 'exists':
                    messages.error(request, 'Lead already has a questionnaire — open it from the funnel.')
                elif status == 'no_template':
                    messages.error(request, 'No template matched.')
                else:
                    ticket.log_activity(
                        TicketActivity.ACTION_QUESTIONNAIRE, user=request.user,
                        content=f"Attached template “{template.title}”.",
                    )
                    messages.success(request, f"Attached “{template.title}” to the linked lead.")

        return redirect('ticket_detail', ticket_id=ticket.id)

    activity = ticket.activity_log.select_related('user', 'from_user', 'to_user')
    suggested = QuestionnaireTemplate.objects.filter(
        is_active=True,
        context__in=[
            QuestionnaireTemplate.CONTEXT_SATISFACTION,
            QuestionnaireTemplate.CONTEXT_DISCOVERY,
            QuestionnaireTemplate.CONTEXT_CUSTOM,
        ],
    )
    context = {
        'ticket': ticket,
        'activity': activity,
        'staff': staff,
        'templates': import_templates,
        'suggested_templates': suggested,
        'status_choices': Ticket.STATUS_CHOICES,
        'priority_choices': Ticket.PRIORITY_CHOICES,
        'questionnaire_contexts': QuestionnaireTemplate.CONTEXT_CHOICES,
        'page_title': f"{ticket.reference} — {ticket.subject}",
    }
    return render(request, 'dashboard/crm_ticket_detail.html', context)


@login_required
@admin_required
def notification_list(request):
    """In-app notification inbox."""
    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'mark_all':
            Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
            messages.success(request, 'All notifications marked as read.')
        elif action == 'mark':
            Notification.objects.filter(
                id=request.POST.get('id'), recipient=request.user, read_at__isnull=True,
            ).update(read_at=timezone.now())
        return redirect('notification_list')

    notes = Notification.objects.filter(recipient=request.user)
    unread = notes.filter(read_at__isnull=True).count()
    context = {
        'notifications': notes[:100],
        'unread': unread,
        'page_title': 'Notifications',
    }
    return render(request, 'dashboard/notifications.html', context)


# ── Questionnaire template library (full CRUD) ──────────────────────

@login_required
@admin_required
def template_list(request):
    """Preset questionnaire templates — list, search, create, delete."""
    q = request.GET.get('q', '').strip()
    context_f = request.GET.get('context', '')
    templates = QuestionnaireTemplate.objects.all()
    if q:
        templates = templates.filter(Q(title__icontains=q) | Q(industry__icontains=q))
    if context_f:
        templates = templates.filter(context=context_f)

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'create':
            title = request.POST.get('title', '').strip()
            if title:
                t = QuestionnaireTemplate.objects.create(
                    title=title[:250],
                    intro=request.POST.get('intro', '').strip() or None,
                    context=request.POST.get('context', QuestionnaireTemplate.CONTEXT_CUSTOM),
                    industry=request.POST.get('industry', '').strip(),
                )
                messages.success(request, f"Template “{t.title}” created. Add questions next.")
                return redirect('template_detail', template_id=t.id)
            messages.error(request, 'Title is required.')
        elif action == 'delete':
            t = QuestionnaireTemplate.objects.filter(id=request.POST.get('template_id')).first()
            if t:
                t.delete()
                messages.success(request, 'Template deleted.')

    context = {
        'templates': templates,
        'q': q,
        'context_f': context_f,
        'context_choices': QuestionnaireTemplate.CONTEXT_CHOICES,
        'page_title': 'Questionnaire Template Library',
    }
    return render(request, 'dashboard/crm_templates.html', context)


@login_required
@admin_required
def template_detail(request, template_id):
    """Edit a template + full question CRUD + import from another template."""
    template = get_object_or_404(QuestionnaireTemplate, id=template_id)
    other_templates = QuestionnaireTemplate.objects.filter(is_active=True).exclude(id=template.id)
    import_source = None
    source_id = request.GET.get('source')
    if source_id:
        import_source = QuestionnaireTemplate.objects.filter(id=source_id).first()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_meta':
            template.title = request.POST.get('title', template.title).strip() or template.title
            template.intro = request.POST.get('intro', '').strip() or None
            template.context = request.POST.get('context', template.context)
            template.industry = request.POST.get('industry', '').strip()
            template.is_active = bool(request.POST.get('is_active'))
            template.save()
            messages.success(request, 'Template saved.')

        elif action == 'add_question':
            text = request.POST.get('text', '').strip()
            if text:
                Question.objects.create(
                    template=template,
                    text=text[:500],
                    help_text=request.POST.get('help_text', '').strip() or None,
                    question_type=request.POST.get('question_type', Question.TYPE_TEXT),
                    options=request.POST.get('options', '').strip() or None,
                    required=bool(request.POST.get('required')),
                    order=template.questions.count() + 1,
                    context=request.POST.get('context_tag', '').strip(),
                )
                messages.success(request, 'Question added.')
            else:
                messages.error(request, 'Question text is required.')

        elif action == 'edit_question':
            question = template.questions.filter(id=request.POST.get('question_id')).first()
            if question:
                question.text = request.POST.get('text', '').strip() or question.text
                question.help_text = request.POST.get('help_text', '').strip() or None
                question.question_type = request.POST.get('question_type', question.question_type)
                question.options = request.POST.get('options', '').strip() or None
                question.required = bool(request.POST.get('required'))
                question.context = request.POST.get('context_tag', '').strip()
                question.save()
                messages.success(request, 'Question updated.')

        elif action == 'move_question':
            question = template.questions.filter(id=request.POST.get('question_id')).first()
            direction = request.POST.get('direction')
            if question and direction == 'up' and question.order > 1:
                Question.objects.filter(template=template, order=question.order - 1).update(order=question.order)
                question.order -= 1
                question.save()
            elif question and direction == 'down':
                Question.objects.filter(template=template, order=question.order + 1).update(order=question.order)
                question.order += 1
                question.save()

        elif action == 'delete_question':
            template.questions.filter(id=request.POST.get('question_id')).delete()
            messages.success(request, 'Question removed.')

        elif action == 'import_questions':
            source_ids = request.POST.getlist('import_template_ids')
            single_id = request.POST.get('source_template_id')
            question_ids = request.POST.getlist('import_question_ids')
            if single_id and single_id not in source_ids:
                source_ids.append(single_id)
            sources = list(
                QuestionnaireTemplate.objects.filter(id__in=source_ids)
                .exclude(id=template.id)
                .distinct()
            )
            if not sources:
                messages.error(request, 'Select at least one package to import from.')
            else:
                total_added = total_skipped = 0
                for source in sources:
                    ids = None
                    if single_id and str(source.id) == str(single_id) and question_ids:
                        ids = question_ids
                    result = import_questions_into(template, source, ids)
                    total_added += result['added']
                    total_skipped += result['skipped']
                detail = (
                    f"Merged {total_added} question(s) from {len(sources)} package(s)."
                    if total_added
                    else 'No new questions to merge — all were already present.'
                )
                if total_skipped:
                    detail += f" Skipped {total_skipped} duplicate(s)."
                messages.success(request, detail)

        return redirect('template_detail', template_id=template.id)

    context = {
        'template': template,
        'questions': template.questions.all(),
        'question_types': Question.QUESTION_TYPES,
        'context_choices': QuestionnaireTemplate.CONTEXT_CHOICES,
        'other_templates': other_templates,
        'import_source': import_source,
        'page_title': f"Template — {template.title}",
    }
    return render(request, 'dashboard/crm_template_detail.html', context)


# ── Client portal tickets ───────────────────────────────────────────

@login_required(login_url='login_view')
@client_required
def client_tickets(request):
    """Read-only list of this client's support tickets."""
    tickets = (
        Ticket.objects
        .filter(Q(contact__portal_user=request.user) | Q(contact__email=request.user.email))
        .select_related('contact', 'organization', 'assigned_to', 'inquiry')
        .order_by('-updated_at')
    )
    context = {
        'tickets': tickets,
        'page_title': 'My Support Tickets',
    }
    return render(request, 'dashboard/client/tickets.html', context)


@login_required(login_url='login_view')
@client_required
def client_ticket_detail(request, ticket_id):
    """Client view of one ticket + public replies via notes (read status/activity)."""
    ticket = get_object_or_404(
        Ticket.objects.select_related('contact', 'organization', 'assigned_to', 'inquiry'),
        id=ticket_id,
    )
    owned = (
        (ticket.contact and ticket.contact.portal_user_id == request.user.id)
        or (ticket.contact and ticket.contact.email == request.user.email)
        or request.user.is_staff
    )
    if not owned:
        raise PermissionDenied

    if request.method == 'POST' and ticket.is_open:
        body = request.POST.get('content', '').strip()
        if body:
            ticket.log_activity(TicketActivity.ACTION_NOTE, user=request.user, content=body)
            if ticket.assigned_to:
                notify(
                    recipients=[ticket.assigned_to], verb='note',
                    title=f"Client update on {ticket.reference}",
                    body=body[:400],
                    link=f"/dashboard/crm/tickets/{ticket.id}/",
                    actor=request.user,
                )
            messages.success(request, 'Update added. Our team has been notified.')
            return redirect('client_ticket_detail', ticket_id=ticket.id)

    activity = ticket.activity_log.select_related('user', 'from_user', 'to_user')
    # Clients only see notes/status/priority — not internal transfers of other staff detail is OK
    context = {
        'ticket': ticket,
        'activity': activity,
        'page_title': f"{ticket.reference} — {ticket.subject}",
    }
    return render(request, 'dashboard/client/ticket_detail.html', context)


@login_required
@admin_required
def dashboard_products(request):
    """ CMS: Manage products """
    products = Product.objects.all().order_by('-created_at')
    context = {
        'products': products,
        'page_title': 'Products Catalog CMS'
    }
    return render(request, 'dashboard/cms_products.html', context)

@login_required
@admin_required
def dashboard_articles(request):
    """ CMS: Manage blog posts and articles """
    articles = Article.objects.all().order_by('-created_at')
    context = {
        'articles': articles,
        'page_title': 'Articles & Blog CMS'
    }
    return render(request, 'dashboard/cms_articles.html', context)

@login_required
@admin_required
def dashboard_adverts(request):
    """ CMS: Manage Advertisements """
    adverts = Advertisement.objects.all().order_by('-created_at')
    context = {
        'adverts': adverts,
        'page_title': 'Adverts Management'
    }
    return render(request, 'dashboard/cms_adverts.html', context)

@login_required
@admin_required
def dashboard_newsletters(request):
    """ Marketing: Manage Newsletters and Broadcasts """
    newsletters = Newsletter.objects.all().order_by('-created_at')
    subscribers = NewsletterSubscription.objects.all().order_by('-subscribed_at')
    subs_count = subscribers.filter(unsubscribed_at__isnull=True).count()
    context = {
        'newsletters': newsletters,
        'subscribers': subscribers,
        'subs_count': subs_count,
        'page_title': 'Newsletter & Marketing Hub'
    }
    return render(request, 'dashboard/cms_newsletters.html', context)

@login_required
@admin_required
def dashboard_engagements(request):
    """ CRM: Moderate community and blog comments/engagements """
    # Simple search filter
    query = request.GET.get('q', '')
    comments = Comment.objects.select_related('user', 'article').order_by('-created_at')
    
    if query:
        comments = comments.filter(content__icontains=query)

    context = {
        'comments': comments,
        'page_title': 'Engagements & Comments Moderation',
        'q': query
    }
    return render(request, 'dashboard/cms_engagements.html', context)

@login_required
@admin_required
def dashboard_publish_article(request, pk):
    """ Editorial Workflow: Approve and publish a draft article """
    article = get_object_or_404(Article, pk=pk)
    article.status = 'published'
    article.save()
    messages.success(request, f"Article '{article.title}' has been successfully published!")
    return redirect(request.GET.get('next', reverse('dashboard_articles')))


@login_required
@admin_required
def dashboard_media(request):
    """Media library for safe uploads and failed-render/request diagnostics."""
    if not request.user.has_perm('app.view_mediaasset'):
        raise PermissionDenied

    form = MediaAssetUploadForm()
    if request.method == 'POST':
        if not request.user.has_perm('app.add_mediaasset'):
            raise PermissionDenied
        form = MediaAssetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            asset, stored = store_uploaded_media(
                form.cleaned_data['file'],
                owner=request.user,
                alt_text=form.cleaned_data['alt_text'],
                is_public=form.cleaned_data['is_public'],
            )
            if stored:
                messages.success(request, f'{asset.original_name} is ready for use.')
            else:
                messages.error(request, f'{asset.original_name} was rejected: {asset.failure_reason}')
            return redirect('dashboard_media')

    assets = MediaAsset.objects.select_related('owner', 'content_type').all()
    context = {
        'assets': assets,
        'form': form,
        'ready_count': assets.filter(status=MediaAsset.STATUS_READY).count(),
        'failed_count': assets.filter(status=MediaAsset.STATUS_FAILED).count(),
        'page_title': 'Media Library',
    }
    return render(request, 'dashboard/media_library.html', context)


@login_required
@admin_required
def dashboard_moderation(request):
    """Staff moderation queue for pending and flagged content."""
    from community.models import Post, Comment, Reply, MODERATION_PENDING, MODERATION_FLAGGED, MODERATION_APPROVED, MODERATION_HIDDEN, MODERATION_REMOVED
    from home.models import Article

    query = request.GET.get('q', '')
    pending_posts = Post.objects.filter(moderation_state=MODERATION_PENDING)
    flagged_posts = Post.objects.filter(moderation_state=MODERATION_FLAGGED)
    pending_comments = Comment.objects.filter(moderation_state__in=[MODERATION_PENDING, MODERATION_FLAGGED])
    pending_replies = Reply.objects.filter(moderation_state__in=[MODERATION_PENDING, MODERATION_FLAGGED])

    if query:
        pending_posts = pending_posts.filter(
            models.Q(title__icontains=query) | models.Q(content__icontains=query)
        )
        pending_comments = pending_comments.filter(content__icontains=query)

    pending_count = (
        pending_posts.count() + flagged_posts.count() +
        pending_comments.count() + pending_replies.count()
    )

    context = {
        'pending_posts': pending_posts[:20],
        'flagged_posts': flagged_posts[:20],
        'pending_comments': pending_comments[:20],
        'pending_replies': pending_replies[:20],
        'pending_count': pending_count,
        'query': query,
        'page_title': 'Moderation Queue',
    }
    return render(request, 'dashboard/cms_moderation.html', context)


@login_required
@admin_required
def dashboard_ats(request):
    """Applicant Tracking System - hiring pipeline overview."""
    from home.models import JobApplication, Interview, Department, Job
    from django.db.models import Count, Q

    query = request.GET.get('q', '')
    applications = JobApplication.objects.select_related('job', 'department', 'assigned_to').order_by('-applied_at')
    interviews = Interview.objects.select_related('application', 'interviewer').filter(outcome='pending').order_by('scheduled_at')

    if query:
        applications = applications.filter(
            Q(candidate_name__icontains=query) |
            Q(candidate_email__icontains=query) |
            Q(job__title__icontains=query)
        )

    # Pipeline summary
    pipeline_stats = {
        'total': JobApplication.objects.count(),
        'new': JobApplication.objects.filter(status=JobApplication.STAGE_NEW).count(),
        'screened': JobApplication.objects.filter(status=JobApplication.STAGE_SCREENED).count(),
        'shortlisted': JobApplication.objects.filter(status=JobApplication.STAGE_SHORTLISTED).count(),
        'interview': JobApplication.objects.filter(
            status__in=[JobApplication.STAGE_INTERVIEW_SCHEDULED, JobApplication.STAGE_INTERVIEW_COMPLETE, JobApplication.STAGE_ASSESSMENT]
        ).count(),
        'offer': JobApplication.objects.filter(status=JobApplication.STAGE_OFFER).count(),
        'hired': JobApplication.objects.filter(status=JobApplication.STAGE_HIRED).count(),
        'rejected': JobApplication.objects.filter(status=JobApplication.STAGE_REJECTED).count(),
        'withdrawn': JobApplication.objects.filter(status=JobApplication.STAGE_WITHDRAWN).count(),
    }

    # Department breakdown
    department_breakdown = (
        Department.objects.filter(applications__is_active=True)
        .annotate(app_count=Count('applications'))
        .order_by('-app_count')
    )

    # Source effectiveness
    source_breakdown = (
        SourceTracker.objects.all()
        .annotate(total=Count('id'))
        .order_by('-hired_count')[:5]
    )

    # Overdue interviews
    overdue_interviews = interviews.filter(scheduled_at__lt=timezone.now()).count()

    context = {
        'applications': applications[:20],
        'interviews': interviews[:10],
        'pipeline_stats': pipeline_stats,
        'department_breakdown': department_breakdown,
        'source_breakdown': source_breakdown,
        'overdue_interviews': overdue_interviews,
        'query': query,
        'page_title': 'Applicant Tracking System',
    }
    return render(request, 'dashboard/cms_ats.html', context)


@login_required
@admin_required
def dashboard_ats_application(request, application_id):
    """View a single ATS application with full pipeline details."""
    from home.models import JobApplication, Interview, ApplicationNote
    application = get_object_or_404(JobApplication, id=application_id)
    interviews = Interview.objects.filter(application=application).order_by('scheduled_at')
    notes = ApplicationNote.objects.filter(application=application).order_by('-created_at')[:20]

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'move_stage':
            new_status = request.POST.get('status')
            application.move_to_stage(new_status, request.user)
            messages.success(request, f"Application moved to {application.get_status_display()}.")
        elif action == 'add_note':
            content = request.POST.get('content', '').strip()
            if content:
                ApplicationNote.objects.create(
                    application=application,
                    action=ApplicationNote.ACTION_NOTE,
                    user=request.user,
                    content=content,
                )
                messages.success(request, 'Note added.')

    context = {
        'application': application,
        'interviews': interviews,
        'notes': notes,
        'page_title': f"Application #{application.id} - {application.candidate_name}",
    }
    return render(request, 'dashboard/cms_ats_application.html', context)


# ==========================================
# UNIFIED CUSTOM DASHBOARD CRUD (CMS & CRM)
# ==========================================
from django.apps import apps
from django.views.generic import CreateView, UpdateView, DeleteView
from django import forms
from django.urls import reverse
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import Http404

class AdminSecurityMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        if not self.request.user.is_authenticated:
            return False
        if self.request.user.is_superuser:
            return True
        if not self.request.user.has_perm('home.access_dashboard'):
            return False
        action = getattr(self, 'permission_action', None)
        if not action:
            return True
        return self.request.user.has_perm(
            f'{self.model._meta.app_label}.{action}_{self.model._meta.model_name}'
        )

class DynamicModelMixin:
    """ Dynamically loads the model based on URL kwargs app_label and model_name """
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        try:
            self.model = apps.get_model(self.kwargs['app_label'], self.kwargs['model_name'])
        except LookupError:
            raise Http404("Model not found")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for name, field in form.fields.items():
            if isinstance(field.widget, forms.CheckboxSelectMultiple):
                # ManyToMany checkbox list styling
                field.widget.attrs.update({'class': 'form-check-input', 'is_checkbox_select_multiple': True})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({'class': 'form-check-input'})
            else:
                field.widget.attrs.update({'class': 'form-control'})
        return form

class DashboardCreateView(AdminSecurityMixin, DynamicModelMixin, CreateView):
    template_name = 'dashboard/unified_form.html'
    fields = '__all__'
    permission_action = 'add'
    
    def get_form_class(self):
        form_class = super().get_form_class()
        # Customizations for Newsletter
        if self.kwargs.get('model_name') == 'newsletter':
            if 'recipients' in form_class.base_fields:
                form_class.base_fields['recipients'].widget = forms.CheckboxSelectMultiple()
        # Clean CRM form for Sales Inquiries — hides internal fields
        # (user FK, password, auto-managed timestamps, questionnaire FK).
        if self.kwargs.get('app_label') == 'app' and self.kwargs.get('model_name') == 'serviceinquiry':
            return ServiceInquiryForm
        return form_class
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('dashboard'))
        
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c['page_title'] = f"Add {self.model._meta.verbose_name.title()}"
        c['next_url'] = self.request.GET.get('next', '')
        return c

class DashboardUpdateView(AdminSecurityMixin, DynamicModelMixin, UpdateView):
    template_name = 'dashboard/unified_form.html'
    fields = '__all__'
    permission_action = 'change'

    def get_form_class(self):
        form_class = super().get_form_class()
        if self.kwargs.get('model_name') == 'newsletter':
            if 'recipients' in form_class.base_fields:
                form_class.base_fields['recipients'].widget = forms.CheckboxSelectMultiple()
        # Clean CRM form for Sales Inquiries — hides internal fields
        # (user FK, password, auto-managed timestamps, questionnaire FK).
        if self.kwargs.get('app_label') == 'app' and self.kwargs.get('model_name') == 'serviceinquiry':
            return ServiceInquiryForm
        return form_class
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('dashboard'))
        
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c['page_title'] = f"Edit {self.model._meta.verbose_name.title()}"
        c['next_url'] = self.request.GET.get('next', '')
        return c

class DashboardDeleteView(AdminSecurityMixin, DynamicModelMixin, DeleteView):
    template_name = 'dashboard/unified_confirm_delete.html'
    permission_action = 'delete'
    
    def get_success_url(self):
        return self.request.GET.get('next', reverse('dashboard'))
        
    def get_context_data(self, **kwargs):
        c = super().get_context_data(**kwargs)
        c['page_title'] = f"Delete {self.model._meta.verbose_name.title()}"
        c['next_url'] = self.request.GET.get('next', '')
        return c


# ── Client billing / plans ─────────────────────────────────────────

@login_required(login_url='login_view')
@client_required
def client_billing(request):
    """Show current plan, active subscription, and available premium plans."""
    subscription = Subscription.active_for(request.user)
    current_plan = Subscription.plan_for(request.user)
    plans = Plan.objects.filter(is_active=True)

    context = {
        'subscription': subscription,
        'current_plan': current_plan,
        'plans': plans,
        'page_title': 'Billing & Plan',
    }
    return render(request, 'dashboard/client/billing.html', context)


@login_required(login_url='login_view')
@client_required
def client_subscription_choose(request, plan_slug):
    """Placeholder checkout — records a pending-style active sub for staff confirm."""
    plan = get_object_or_404(Plan, slug=plan_slug, is_active=True)
    if plan.is_free:
        messages.info(request, 'You are already on the free plan.')
        return redirect('client_billing')
    if request.method != 'POST':
        return redirect('client_billing')

    existing = Subscription.active_for(request.user)
    if existing and existing.plan_id == plan.id:
        messages.info(request, f'You are already subscribed to {plan.name}.')
        return redirect('client_billing')

    if existing:
        existing.status = Subscription.STATUS_CANCELLED
        existing.save(update_fields=['status', 'updated_at'])

    Subscription.objects.create(
        user=request.user,
        plan=plan,
        status=Subscription.STATUS_ACTIVE,
        payment_reference=f'pending-{timezone.now().strftime("%Y%m%d%H%M%S")}',
        notes='Checkout placeholder — payment gateway wiring pending.',
    )
    messages.success(
        request,
        f'{plan.name} selected. Staff will confirm payment until checkout is wired.',
    )
    return redirect('client_billing')


@login_required(login_url='login_view')
@client_required
def client_subscription_cancel(request):
    """Cancel the active subscription at period end (status → cancelled now)."""
    if request.method != 'POST':
        return redirect('client_billing')
    subscription = Subscription.active_for(request.user)
    if not subscription:
        messages.info(request, 'No active subscription to cancel.')
        return redirect('client_billing')
    subscription.status = Subscription.STATUS_CANCELLED
    subscription.cancel_at_period_end = True
    subscription.save(update_fields=['status', 'cancel_at_period_end', 'updated_at'])
    messages.success(request, 'Subscription cancelled. You keep access through the current period.')
    return redirect('client_billing')


# ── Staff: feature-request moderation ──────────────────────────────

@login_required(login_url='login_view')
@admin_required
def dashboard_features(request):
    """List + filter public feature requests and update roadmap status."""
    q = request.GET.get('q', '').strip()
    status_f = request.GET.get('status', '')
    features = FeatureRequest.objects.all()
    if q:
        features = features.filter(Q(title__icontains=q) | Q(description__icontains=q))
    if status_f and status_f in dict(FeatureRequest.STATUS_CHOICES):
        features = features.filter(status=status_f)

    if request.method == 'POST':
        feature_id = request.POST.get('feature_id')
        new_status = request.POST.get('status')
        feature = FeatureRequest.objects.filter(id=feature_id).first()
        if feature and new_status in dict(FeatureRequest.STATUS_CHOICES):
            feature.status = new_status
            feature.save(update_fields=['status', 'updated_at'])
            messages.success(request, f'“{feature.title}” → {feature.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status update.')
        return redirect('dashboard_features')

    context = {
        'features': features,
        'q': q,
        'status_f': status_f,
        'status_choices': FeatureRequest.STATUS_CHOICES,
        'page_title': 'Feature Board',
    }
    return render(request, 'dashboard/cms_features.html', context)
