import os
import uuid

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from home.models import MetadataMixin
from shop.models import Category as ShopCategory


def media_asset_upload_path(instance, filename):
    """Generate a non-guessable local storage path while retaining the suffix."""
    extension = os.path.splitext(filename)[1].lower()
    created_at = instance.created_at or timezone.now()
    return f'media_assets/{created_at:%Y/%m}/{uuid.uuid4().hex}{extension}'


# Shared industry choices for intake forms, orgs, and questionnaire templates
INDUSTRY_CHOICES = [
    ('', 'Select industry…'),
    ('fintech', 'Fintech & Banking'),
    ('health', 'Healthcare & Life Sciences'),
    ('education', 'Education & EdTech'),
    ('retail', 'Retail & E-commerce'),
    ('manufacturing', 'Manufacturing & Logistics'),
    ('agriculture', 'Agriculture & AgriTech'),
    ('telecom', 'Telecommunications'),
    ('energy', 'Energy & Utilities'),
    ('government', 'Government & Public Sector'),
    ('ngo', 'NGO & Development'),
    ('real_estate', 'Real Estate & Construction'),
    ('hospitality', 'Hospitality & Tourism'),
    ('media', 'Media & Entertainment'),
    ('transport', 'Transport & Mobility'),
    ('other', 'Other'),
]


class MediaAsset(models.Model):
    """A reusable uploaded file that can be attached to any domain record."""

    STATUS_UPLOADED = 'uploaded'
    STATUS_READY = 'ready'
    STATUS_FAILED = 'failed'
    STATUS_CHOICES = [
        (STATUS_UPLOADED, 'Uploaded'),
        (STATUS_READY, 'Ready'),
        (STATUS_FAILED, 'Failed'),
    ]

    KIND_IMAGE = 'image'
    KIND_DOCUMENT = 'document'
    KIND_ARCHIVE = 'archive'
    KIND_OTHER = 'other'
    KIND_CHOICES = [
        (KIND_IMAGE, 'Image'),
        (KIND_DOCUMENT, 'Document'),
        (KIND_ARCHIVE, 'Archive'),
        (KIND_OTHER, 'Other'),
    ]

    file = models.FileField(upload_to=media_asset_upload_path, blank=True, null=True)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=150, blank=True)
    size_bytes = models.PositiveBigIntegerField(default=0)
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_OTHER)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_UPLOADED, db_index=True)
    failure_reason = models.TextField(blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    is_public = models.BooleanField(default=False)
    metadata = models.JSONField(default=dict, blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='media_assets',
    )
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True)
    object_id = models.PositiveBigIntegerField(null=True, blank=True)
    content_object = GenericForeignKey('content_type', 'object_id')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Image derivatives for responsive display
    large_image = models.ImageField(upload_to='derivatives/large/', blank=True, null=True)
    medium_image = models.ImageField(upload_to='derivatives/medium/', blank=True, null=True)
    small_image = models.ImageField(upload_to='derivatives/small/', blank=True, null=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['owner', 'status']),
        ]

    def __str__(self):
        return self.original_name

    @staticmethod
    def kind_for_mime_type(mime_type):
        if mime_type.startswith('image/'):
            return MediaAsset.KIND_IMAGE
        if mime_type in {'application/zip', 'application/x-zip-compressed'}:
            return MediaAsset.KIND_ARCHIVE
        if mime_type:
            return MediaAsset.KIND_DOCUMENT
        return MediaAsset.KIND_OTHER

    def clean(self):
        super().clean()
        if not self.file or self.status == self.STATUS_FAILED:
            return
        uploaded_file = self.file.file
        mime_type = getattr(uploaded_file, 'content_type', self.mime_type)
        size = getattr(uploaded_file, 'size', self.size_bytes)
        if mime_type not in settings.MEDIA_ALLOWED_CONTENT_TYPES:
            raise ValidationError({'file': 'This file type is not allowed.'})
        if size > settings.MEDIA_MAX_UPLOAD_BYTES:
            raise ValidationError({'file': 'This file exceeds the 15 MiB upload limit.'})

    @property
    def is_renderable_image(self):
        return self.status == self.STATUS_READY and self.kind == self.KIND_IMAGE and bool(self.file)

    @property
    def preview_url(self):
        if self.is_renderable_image:
            # Use the small derivative for preview if available, else original
            if self.small_image and self.small_image.url:
                return self.small_image.url
            return self.file.url if self.file else ''
        return ''

# Create user model    
class User(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    password = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user')
    username = models.CharField(max_length=100, unique=True, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.username:
            if self.email:
                self.username = self.email.split('@')[0]
            else:
                self.username = (self.first_name + self.last_name).lower()
        super(User, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.username


class Organization(models.Model):
    """A client company or institution represented in the CRM."""

    name = models.CharField(max_length=255, unique=True)
    website = models.URLField(blank=True)
    industry = models.CharField(max_length=120, blank=True)
    phone = models.CharField(max_length=30, blank=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Contact(models.Model):
    """A person who can own several enquiries for one organization."""

    CONTACT_EMAIL = 'email'
    CONTACT_PHONE = 'phone'
    CONTACT_WHATSAPP = 'whatsapp'
    CONTACT_CHOICES = [
        (CONTACT_EMAIL, 'Email'),
        (CONTACT_PHONE, 'Phone'),
        (CONTACT_WHATSAPP, 'WhatsApp'),
    ]

    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='contacts',
    )
    portal_user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='crm_contact',
    )
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    job_title = models.CharField(max_length=120, blank=True)
    preferred_contact_method = models.CharField(
        max_length=20, choices=CONTACT_CHOICES, default=CONTACT_EMAIL,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'last_name', 'email']

    @property
    def display_name(self):
        return f'{self.first_name} {self.last_name}'.strip() or self.email

    def __str__(self):
        return self.display_name

class ServiceInquiry(MetadataMixin):
    SERVICE_CHOICES = [
        ('software', 'Software Engineering'),
        ('it', 'IT Solutions'),
        ('consulting', 'Consulting Services'),
        ('other', 'Other'),
    ]

    # ── Sales Funnel Stages (first contact → close) ─────────────
    STAGE_NEW = 'new'
    STAGE_CONTACTED = 'contacted'
    STAGE_QUALIFIED = 'qualified'
    STAGE_PROPOSAL = 'proposal'
    STAGE_NEGOTIATION = 'negotiation'
    STAGE_WON = 'won'
    STAGE_LOST = 'lost'

    STAGE_CHOICES = [
        (STAGE_NEW, 'New Lead'),
        (STAGE_CONTACTED, 'Contacted'),
        (STAGE_QUALIFIED, 'Qualified'),
        (STAGE_PROPOSAL, 'Proposal Sent'),
        (STAGE_NEGOTIATION, 'Negotiation'),
        (STAGE_WON, 'Won (Converted)'),
        (STAGE_LOST, 'Lost'),
    ]

    # Ordered pipeline used for funnel board columns (lost kept last)
    PIPELINE_STAGES = [STAGE_NEW, STAGE_CONTACTED, STAGE_QUALIFIED, STAGE_PROPOSAL, STAGE_NEGOTIATION, STAGE_WON]

    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True, null=True)
    service = models.CharField(max_length=20, choices=SERVICE_CHOICES)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    # ── CRM identity and discovery context ───────────────────────
    SOURCE_WEBSITE = 'website'
    SOURCE_SERVICE_PAGE = 'service_page'
    SOURCE_REFERRAL = 'referral'
    SOURCE_MANUAL = 'manual'
    SOURCE_CHOICES = [
        (SOURCE_WEBSITE, 'Website contact form'),
        (SOURCE_SERVICE_PAGE, 'Service request form'),
        (SOURCE_REFERRAL, 'Referral'),
        (SOURCE_MANUAL, 'Manual entry'),
    ]
    BUDGET_UNSPECIFIED = 'unspecified'
    BUDGET_UNDER_50K = 'under_50k'
    BUDGET_50K_250K = '50k_250k'
    BUDGET_250K_1M = '250k_1m'
    BUDGET_OVER_1M = 'over_1m'
    BUDGET_CHOICES = [
        (BUDGET_UNSPECIFIED, 'Not specified'),
        (BUDGET_UNDER_50K, 'Under KES 50,000'),
        (BUDGET_50K_250K, 'KES 50,000–250,000'),
        (BUDGET_250K_1M, 'KES 250,000–1,000,000'),
        (BUDGET_OVER_1M, 'Over KES 1,000,000'),
    ]
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inquiries',
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='inquiries',
    )
    source = models.CharField(max_length=30, choices=SOURCE_CHOICES, default=SOURCE_WEBSITE)
    industry = models.CharField(max_length=120, blank=True)
    budget_range = models.CharField(max_length=30, choices=BUDGET_CHOICES, default=BUDGET_UNSPECIFIED)
    timeline = models.CharField(max_length=120, blank=True)
    preferred_contact_method = models.CharField(
        max_length=20, choices=Contact.CONTACT_CHOICES, default=Contact.CONTACT_EMAIL,
    )
    media_assets = GenericRelation('MediaAsset', related_query_name='service_inquiry')

    # ── Funnel / CRM fields ──────────────────────────────────────
    stage = models.CharField(
        max_length=20,
        choices=STAGE_CHOICES,
        default=STAGE_NEW,
        db_index=True,
        help_text="Current stage in the sales funnel."
    )
    estimated_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0.00,
        help_text="Estimated deal value (KES)."
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_inquiries',
        help_text="Sales rep handling this lead."
    )
    notes = models.TextField(blank=True, null=True, help_text="Internal follow-up notes.")
    stage_updated_at = models.DateTimeField(auto_now=True)
    converted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-stage_updated_at']
        indexes = [models.Index(fields=['stage', '-stage_updated_at'])]

    def __str__(self):
        return f"Inquiry from {self.name} for {self.get_service_display()}"

    def save(self, *args, **kwargs):
        if self.contact:
            self.email = self.contact.email
            self.name = self.contact.display_name
            if not self.phone:
                self.phone = self.contact.phone
            if not self.organization:
                self.organization = self.contact.organization
        super().save(*args, **kwargs)

    # ── Funnel helpers ───────────────────────────────────────────
    @property
    def questionnaire(self):
        """Latest questionnaire (back-compat with former OneToOne reverse)."""
        return self.questionnaires.order_by('-created_at').first()

    @property
    def is_won(self):
        return self.stage == self.STAGE_WON

    @property
    def is_lost(self):
        return self.stage == self.STAGE_LOST

    @property
    def is_open(self):
        """A lead still actively in the pipeline (not won or lost)."""
        return self.stage not in (self.STAGE_WON, self.STAGE_LOST)

    @property
    def next_stage(self):
        """The next forward-moving stage in the pipeline, if any."""
        if self.stage in self.PIPELINE_STAGES[:-1]:
            return self.PIPELINE_STAGES[self.PIPELINE_STAGES.index(self.stage) + 1]
        return None

    @classmethod
    def funnel_summary(cls):
        """
        Aggregate counts and value per stage for funnel analytics,
        ordered from first contact to close.
        """
        from django.db.models import Count, Sum
        rows = (
            cls.objects.values('stage')
            .annotate(count=Count('id'), value=Sum('estimated_value'))
        )
        summary = {row['stage']: row for row in rows}
        return [
            summary.get(stage, {'stage': stage, 'count': 0, 'value': None})
            for stage in cls.PIPELINE_STAGES + [cls.STAGE_LOST]
        ]


# ── Support / pre-sales ticket queue ────────────────────────────────
class Ticket(models.Model):
    """Work-queue item created from public intake, assigned to staff.

    Tickets are issues first. Once resolved they can be escalated into
    the sales funnel as a ServiceInquiry.
    """

    TYPE_ISSUE = 'issue'
    TYPE_ENQUIRY = 'enquiry'
    TYPE_CHOICES = [
        (TYPE_ISSUE, 'Issue / Support'),
        (TYPE_ENQUIRY, 'Sales Enquiry'),
    ]

    STATUS_NEW = 'new'
    STATUS_OPEN = 'open'
    STATUS_WAITING = 'waiting'
    STATUS_RESOLVED = 'resolved'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_NEW, 'New'),
        (STATUS_OPEN, 'Open'),
        (STATUS_WAITING, 'Waiting on Client'),
        (STATUS_RESOLVED, 'Resolved'),
        (STATUS_CLOSED, 'Closed'),
    ]
    OPEN_STATUSES = (STATUS_NEW, STATUS_OPEN, STATUS_WAITING)

    PRIORITY_LOW = 'low'
    PRIORITY_NORMAL = 'normal'
    PRIORITY_HIGH = 'high'
    PRIORITY_URGENT = 'urgent'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_NORMAL, 'Normal'),
        (PRIORITY_HIGH, 'High'),
        (PRIORITY_URGENT, 'Urgent'),
    ]

    reference = models.CharField(max_length=20, unique=True, blank=True, editable=False)
    subject = models.CharField(max_length=255)
    description = models.TextField()
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_ISSUE, db_index=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_NEW, db_index=True)

    service = models.CharField(max_length=20, choices=ServiceInquiry.SERVICE_CHOICES, default='other')
    source = models.CharField(max_length=30, choices=ServiceInquiry.SOURCE_CHOICES, default=ServiceInquiry.SOURCE_WEBSITE)
    industry = models.CharField(max_length=120, blank=True)
    budget_range = models.CharField(max_length=30, choices=ServiceInquiry.BUDGET_CHOICES, default=ServiceInquiry.BUDGET_UNSPECIFIED)
    timeline = models.CharField(max_length=120, blank=True)
    preferred_contact_method = models.CharField(
        max_length=20, choices=Contact.CONTACT_CHOICES, default=Contact.CONTACT_EMAIL,
    )

    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets',
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True, related_name='tickets',
    )
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_tickets', help_text="Staff member who owns this ticket.",
    )
    referred_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='referred_tickets', help_text="Staff member referred for advice (ownership unchanged).",
    )
    inquiry = models.ForeignKey(
        ServiceInquiry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='tickets', help_text="Sales funnel lead after escalation.",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='created_tickets',
    )

    resolved_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    media_assets = GenericRelation('MediaAsset', related_query_name='ticket')

    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['status', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]

    def __str__(self):
        return f"{self.reference} — {self.subject}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.reference:
            self.reference = f"TK-{self.pk:05d}"
            super().save(update_fields=['reference'])

    @property
    def is_open(self):
        return self.status in self.OPEN_STATUSES

    @property
    def age_hours(self):
        from django.utils import timezone as tz
        end = self.resolved_at or tz.now()
        return max(0, int((end - self.created_at).total_seconds() // 3600))

    def log_activity(self, action, *, user=None, from_user=None, to_user=None, content=''):
        return TicketActivity.objects.create(
            ticket=self, action=action, user=user,
            from_user=from_user, to_user=to_user, content=content or '',
        )


class TicketActivity(models.Model):
    """Append-only activity trail for tickets (assign, transfer, refer, …)."""

    ACTION_CREATED = 'created'
    ACTION_ASSIGNED = 'assigned'
    ACTION_TRANSFERRED = 'transferred'
    ACTION_REFERRED = 'referred'
    ACTION_STATUS_CHANGE = 'status_change'
    ACTION_PRIORITY_CHANGE = 'priority_change'
    ACTION_ESCALATED = 'escalated'
    ACTION_NOTE = 'note'
    ACTION_CONVERTED = 'converted'
    ACTION_QUESTIONNAIRE = 'questionnaire'
    ACTION_CHOICES = [
        (ACTION_CREATED, 'Created'),
        (ACTION_ASSIGNED, 'Assigned'),
        (ACTION_TRANSFERRED, 'Transferred'),
        (ACTION_REFERRED, 'Referred'),
        (ACTION_STATUS_CHANGE, 'Status Changed'),
        (ACTION_PRIORITY_CHANGE, 'Priority Changed'),
        (ACTION_ESCALATED, 'Escalated'),
        (ACTION_NOTE, 'Note'),
        (ACTION_CONVERTED, 'Converted to Lead'),
        (ACTION_QUESTIONNAIRE, 'Questionnaire'),
    ]

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='activity_log')
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default=ACTION_NOTE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_activities',
    )
    from_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_activities_from',
    )
    to_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ticket_activities_to',
    )
    content = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['ticket', 'action'])]

    def __str__(self):
        return f"{self.ticket.reference} · {self.get_action_display()}"


# ── Client Questionnaires (custom per inquiry / service request) ────
class QuestionnaireTemplate(models.Model):
    """Reusable preset questionnaire staff can assign, swap, and import from."""

    CONTEXT_DISCOVERY = 'discovery'
    CONTEXT_ONBOARDING = 'onboarding'
    CONTEXT_END_OF_SERVICE = 'end_of_service'
    CONTEXT_SATISFACTION = 'satisfaction'
    CONTEXT_CUSTOM = 'custom'
    CONTEXT_CHOICES = [
        (CONTEXT_DISCOVERY, 'Discovery'),
        (CONTEXT_ONBOARDING, 'Onboarding'),
        (CONTEXT_END_OF_SERVICE, 'End of Service'),
        (CONTEXT_SATISFACTION, 'Satisfaction'),
        (CONTEXT_CUSTOM, 'Custom'),
    ]

    title = models.CharField(max_length=250)
    intro = models.TextField(blank=True, null=True, help_text="Shown to the client before the questions.")
    context = models.CharField(max_length=40, choices=CONTEXT_CHOICES, default=CONTEXT_CUSTOM, db_index=True)
    industry = models.CharField(
        max_length=120, blank=True,
        help_text="Optional industry filter; blank matches any industry.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['context', 'title']

    def __str__(self):
        return f"{self.title} ({self.get_context_display()})"

    @property
    def question_count(self):
        return self.questions.count()


class Questionnaire(models.Model):
    """A custom questionnaire attached to a service inquiry, answered by the client."""

    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent to Client'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ]

    inquiry = models.ForeignKey(
        ServiceInquiry,
        on_delete=models.CASCADE,
        related_name='questionnaires',
        help_text="One lifecycle questionnaire (discovery, onboarding, end-of-service, …).",
    )
    title = models.CharField(max_length=250)
    intro = models.TextField(blank=True, null=True, help_text="Shown to the client before the questions.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft', db_index=True)
    source_template = models.ForeignKey(
        QuestionnaireTemplate, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='spawned_questionnaires',
    )
    context = models.CharField(
        max_length=40, blank=True,
        help_text="Lifecycle context that produced this questionnaire, if any.",
    )
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Questionnaire for {self.inquiry.name} ({self.get_status_display()})"

    @property
    def question_count(self):
        return self.questions.count()

    @property
    def answered_count(self):
        return Answer.objects.filter(
            question__questionnaire=self
        ).exclude(answer__isnull=True).exclude(answer='').count()

    @property
    def progress_percent(self):
        total = self.question_count
        if not total:
            return 0
        return round((self.answered_count / total) * 100)

    @property
    def is_editable_by_client(self):
        return self.status in ('sent', 'in_progress')


class Question(models.Model):
    """A single custom question inside a questionnaire or template bank."""

    TYPE_TEXT = 'text'
    TYPE_TEXTAREA = 'textarea'
    TYPE_NUMBER = 'number'
    TYPE_CHOICE = 'choice'
    TYPE_BOOLEAN = 'boolean'

    QUESTION_TYPES = [
        (TYPE_TEXT, 'Short Text'),
        (TYPE_TEXTAREA, 'Long Text'),
        (TYPE_NUMBER, 'Number'),
        (TYPE_CHOICE, 'Multiple Choice'),
        (TYPE_BOOLEAN, 'Yes / No'),
    ]

    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name='questions',
        null=True, blank=True,
        help_text="Live questionnaire this question belongs to (clone target).",
    )
    template = models.ForeignKey(
        'QuestionnaireTemplate', on_delete=models.CASCADE, related_name='questions',
        null=True, blank=True,
        help_text="Reusable library template this question belongs to.",
    )
    text = models.CharField(max_length=500)
    help_text = models.CharField(max_length=300, blank=True, null=True)
    question_type = models.CharField(max_length=20, choices=QUESTION_TYPES, default=TYPE_TEXT)
    options = models.TextField(
        blank=True, null=True,
        help_text="Comma-separated options for multiple choice questions."
    )
    required = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    context = models.CharField(
        max_length=40, blank=True,
        help_text="Optional context tag (discovery, satisfaction, …) for import filters.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.text[:80]

    @property
    def option_list(self):
        if self.question_type == self.TYPE_CHOICE and self.options:
            return [o.strip() for o in self.options.split(',') if o.strip()]
        return []

    def client_answer(self):
        """Convenience accessor for the client's latest answer."""
        return self.answers.order_by('-updated_at').first()

    def clean(self):
        super().clean()
        if not self.questionnaire_id and not self.template_id:
            raise ValidationError('A question must belong to a questionnaire or a template.')


class Answer(models.Model):
    """The client's response to a questionnaire question."""

    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    answer = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['question__order']

    def __str__(self):
        return f"Answer to Q{self.question.id}: {str(self.answer)[:50]}"


class QuestionnaireEvent(models.Model):
    """Append-only timeline of questionnaire lifecycle and response changes over time."""

    ACTION_SENT = 'sent'
    ACTION_ANSWERED = 'answered'
    ACTION_UPDATED = 'updated'
    ACTION_COMPLETED = 'completed'
    ACTION_REOPENED = 'reopened'
    ACTION_CLEAR_RESPONSES = 'clear_responses'
    ACTION_QUESTION_ADDED = 'question_added'
    ACTION_QUESTIONS_IMPORTED = 'questions_imported'
    ACTION_STAFF_EDITED = 'staff_edited'
    ACTION_STAFF_DELETED = 'staff_deleted'
    ACTION_CHOICES = [
        (ACTION_SENT, 'Sent to client'),
        (ACTION_ANSWERED, 'Answered'),
        (ACTION_UPDATED, 'Answer updated'),
        (ACTION_COMPLETED, 'Completed'),
        (ACTION_REOPENED, 'Reopened'),
        (ACTION_CLEAR_RESPONSES, 'Responses cleared'),
        (ACTION_QUESTION_ADDED, 'Question added'),
        (ACTION_QUESTIONS_IMPORTED, 'Questions imported'),
        (ACTION_STAFF_EDITED, 'Staff correction'),
        (ACTION_STAFF_DELETED, 'Staff deleted answer'),
    ]

    questionnaire = models.ForeignKey(
        Questionnaire, on_delete=models.CASCADE, related_name='events',
    )
    question = models.ForeignKey(
        Question, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='events',
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='questionnaire_events',
        help_text="Who performed the action; null = system or unauthenticated client email match.",
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, db_index=True)
    content = models.TextField(blank=True)
    answer_snapshot = models.TextField(
        blank=True, null=True,
        help_text="Answer value at the time of this event (for response history).",
    )
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['questionnaire', 'created_at']),
        ]

    def __str__(self):
        return f"{self.get_action_display()} · {self.questionnaire_id} @ {self.created_at}"


# ── WhatsApp Notification Delivery Log ──────────────────────
class WhatsAppNotification(models.Model):
    """Tracks WhatsApp message delivery to staff/clients."""
    STATUS_PENDING = 'pending'
    STATUS_SENT = 'sent'
    STATUS_FAILED = 'failed'
    STATUS_DELIVERED = 'delivered'
    STATUS_READ = 'read'
    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SENT, 'Sent'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_READ, 'Read'),
    ]
    CHANNEL_NOTIFY = 'notify'
    CHANNEL_INQUIRY = 'inquiry'
    CHANNEL_PROJECT = 'project'
    CHANNEL_QUESTIONNAIRE = 'questionnaire'
    CHANNEL_TICKET = 'ticket'
    CHANNEL_CHOICES = [
        (CHANNEL_NOTIFY, 'General notification'),
        (CHANNEL_INQUIRY, 'New inquiry'),
        (CHANNEL_PROJECT, 'Project update'),
        (CHANNEL_QUESTIONNAIRE, 'Questionnaire event'),
        (CHANNEL_TICKET, 'Ticket update'),
    ]
    recipient_name = models.CharField(max_length=200, blank=True)
    recipient_phone = models.CharField(max_length=20, blank=True)
    recipient_WhatsApp = models.CharField(max_length=20, blank=True)
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default=CHANNEL_NOTIFY)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    notification = models.ForeignKey(
        'home.Notification', on_delete=models.CASCADE,
        null=True, blank=True, related_name='whatsapp_notifications',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'created_at'])]

    def __str__(self):
        return f"WA {self.get_channel_display()} → {self.recipient_phone} ({self.status})"


# ── Project/Delivery records ──────────────────────────────
class Project(MetadataMixin):
    """A delivery project resulting from a converted inquiry/deal."""

    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_ON_HOLD = 'on_hold'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ON_HOLD, 'On Hold'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(
        Organization, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projects',
    )
    contact = models.ForeignKey(
        Contact, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='projects',
    )
    service = models.CharField(max_length=20, choices=ServiceInquiry.SERVICE_CHOICES, blank=True)
    source = models.CharField(max_length=30, choices=ServiceInquiry.SOURCE_CHOICES, blank=True)
    stage = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
        db_index=True,
    )
    priority = models.CharField(
        max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM,
    )
    start_date = models.DateField(null=True, blank=True)
    target_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)
    estimated_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Estimated project budget (KES)."
    )
    actual_budget = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Actual project spend."
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE,
    )
    deliverables = models.TextField(blank=True, null=True, help_text="Comma-separated list of deliverables")
    attachments = models.ManyToManyField(
        MediaAsset, blank=True, related_name='projects', related_query_name='project',
    )
    client_feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    converted_from_inquiry = models.ForeignKey(
        ServiceInquiry, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='converted_projects',
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['stage', 'priority']),
            models.Index(fields=['organization', 'status']),
        ]

    def __str__(self):
        return f"Project {self.name} - {self.get_status_display()}"

    @property
    def is_active(self):
        return self.status == self.STATUS_ACTIVE

    @property
    def is_completed(self):
        return self.status == self.STATUS_COMPLETED


class CaseStudy(MetadataMixin):
    """A case study with brand-specific assets and Apple-design storytelling sections."""

    STATUS_DRAFT = 'draft'
    STATUS_REVIEW = 'review'
    STATUS_PUBLISHED = 'published'
    STATUS_ARCHIVED = 'archived'
    STATUS_CHOICES = [
        (STATUS_DRAFT, 'Draft'),
        (STATUS_REVIEW, 'In Review'),
        (STATUS_PUBLISHED, 'Published'),
        (STATUS_ARCHIVED, 'Archived'),
    ]

    CATEGORY_SAAS = 'saas'
    CATEGORY_MOBILE = 'mobile'
    CATEGORY_WEB = 'web'
    CATEGORY_CONSULTING = 'consulting'
    CATEGORY_ECOMMERCE = 'ecommerce'
    CATEGORY_EDTECH = 'edtech'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_SAAS, 'SaaS Platform'),
        (CATEGORY_MOBILE, 'Mobile App'),
        (CATEGORY_WEB, 'Web Application'),
        (CATEGORY_CONSULTING, 'Consulting'),
        (CATEGORY_ECOMMERCE, 'E-Commerce'),
        (CATEGORY_EDTECH, 'EdTech'),
        (CATEGORY_OTHER, 'Other'),
    ]

    name = models.CharField(max_length=200, help_text="Brand/project name")
    slug = models.SlugField(max_length=250, unique=True, null=True, blank=True)
    tagline = models.CharField(max_length=300, blank=True, help_text="Short tagline for the case study")
    description = models.TextField(help_text="Full description of the case study")
    overview = models.TextField(blank=True, help_text="High-level overview paragraph")
    category = models.ForeignKey(ShopCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='case_studies', help_text='Category from existing shop entities')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT)

    # ── Brand Assets ──
    accent_color = models.CharField(max_length=7, default='#0071e3', help_text="Brand accent color (hex)")
    primary_color = models.CharField(max_length=7, default='#1d1d1f', help_text="Brand primary color (hex)")
    secondary_color = models.CharField(max_length=7, default='#5856d6', help_text="Brand secondary color (hex)")
    bg_color = models.CharField(max_length=7, default='#ffffff', help_text="Background color (hex)")
    bg_secondary_color = models.CharField(max_length=7, default='#f5f5f7', help_text="Secondary background color (hex)")
    logo_image = models.ImageField(upload_to='case_studies/logos/', blank=True, null=True, help_text="Brand logo")
    hero_image = models.ImageField(upload_to='case_studies/heroes/', blank=True, null=True, help_text="Hero/cover image")
    favicon = models.ImageField(upload_to='case_studies/favicons/', blank=True, null=True)

    # ── Metadata ──
    featured = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ── Section Content (structured for Apple design) ──
    problem_statement = models.TextField(blank=True, help_text="Problem statement section content")
    objectives = models.TextField(blank=True, help_text="Objectives & goals section content")
    business_challenge = models.TextField(blank=True, help_text="Business challenge section content")
    research_findings = models.TextField(blank=True, help_text="Quantitative research findings")
    user_needs = models.TextField(blank=True, help_text="User needs section content")
    features = models.TextField(blank=True, help_text="Features & functionalities section content")
    user_challenges = models.TextField(blank=True, help_text="Product user challenges section content")
    competitor_data = models.TextField(blank=True, help_text="Competitor analysis data (JSON or HTML)")
    unique_features = models.TextField(blank=True, help_text="Unique features section content")
    persona_data = models.TextField(blank=True, help_text="User persona data (JSON or HTML)")
    task_mapping = models.TextField(blank=True, help_text="Task mapping section content")
    matrix_data = models.TextField(blank=True, help_text="Eisenhower matrix data")
    root_cause = models.TextField(blank=True, help_text="Root cause analysis content")
    task_flows = models.TextField(blank=True, help_text="Task flows content")
    sketches = models.TextField(blank=True, help_text="Sketches section content")
    major_screens = models.TextField(blank=True, help_text="Major screens section content")
    screens = models.TextField(blank=True, help_text="Screens section content")

    class Meta:
        ordering = ['-published_at', '-created_at']
        indexes = [
            models.Index(fields=['status', 'featured']),
            models.Index(fields=['category']),
            models.Index(fields=['published_at']),
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    def get_accent_rgb(self):
        """Convert hex accent color to RGB tuple for CSS use."""
        color = self.accent_color.lstrip('#')
        return tuple(int(color[i:i+2], 16) for i in (0, 2, 4))

    @property
    def css_variables(self):
        """Return CSS custom properties for this brand."""
        return {
            '--brand-accent': self.accent_color,
            '--brand-primary': self.primary_color,
            '--brand-secondary': self.secondary_color,
            '--brand-bg': self.bg_color,
            '--brand-bg-secondary': self.bg_secondary_color,
            '--brand-gradient': f'linear-gradient(135deg, {self.accent_color} 0%, {self.secondary_color} 100%)',
        }

    @property
    def gradient_css(self):
        return f'linear-gradient(135deg, {self.accent_color} 0%, {self.secondary_color} 100%)'


# ── Premium subscriptions ──────────────────────────────────────────
class Plan(models.Model):
    """Billing plan for portal premium tiers."""

    INTERVAL_MONTHLY = 'monthly'
    INTERVAL_YEARLY = 'yearly'
    INTERVAL_CHOICES = [
        (INTERVAL_MONTHLY, 'Monthly'),
        (INTERVAL_YEARLY, 'Yearly'),
    ]

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=80, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    currency = models.CharField(max_length=8, default='KES')
    interval = models.CharField(max_length=16, choices=INTERVAL_CHOICES, default=INTERVAL_MONTHLY)
    features = models.TextField(
        blank=True,
        help_text="One feature per line.",
    )
    is_active = models.BooleanField(default=True, db_index=True)
    is_default = models.BooleanField(default=False, help_text="Assigned when a user has no paid plan.")
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.name} ({self.get_interval_display()})"

    @property
    def feature_list(self):
        return [line.strip() for line in (self.features or '').splitlines() if line.strip()]

    @property
    def is_free(self):
        return self.price == 0

    def save(self, *args, **kwargs):
        if self.is_default:
            Plan.objects.filter(is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Subscription(models.Model):
    """A user's current (or historical) plan enrollment."""

    STATUS_ACTIVE = 'active'
    STATUS_CANCELLED = 'cancelled'
    STATUS_EXPIRED = 'expired'
    STATUS_PAST_DUE = 'past_due'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_PAST_DUE, 'Past Due'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscriptions',
    )
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE, db_index=True)
    starts_at = models.DateTimeField(default=timezone.now)
    ends_at = models.DateTimeField(null=True, blank=True, help_text="Null = open-ended (free or manual).")
    cancel_at_period_end = models.BooleanField(default=False)
    payment_reference = models.CharField(max_length=120, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['user', 'status'])]

    def __str__(self):
        return f"{self.user} → {self.plan.name} ({self.get_status_display()})"

    @property
    def is_currently_active(self):
        if self.status != self.STATUS_ACTIVE:
            return False
        if self.ends_at and self.ends_at < timezone.now():
            return False
        return self.starts_at <= timezone.now()

    @classmethod
    def active_for(cls, user):
        """Return the user's active subscription, or None."""
        if not user or not getattr(user, 'is_authenticated', False):
            return None
        return (
            cls.objects.filter(user=user, status=cls.STATUS_ACTIVE)
            .select_related('plan')
            .filter(models.Q(ends_at__isnull=True) | models.Q(ends_at__gte=timezone.now()))
            .first()
        )

    @classmethod
    def plan_for(cls, user):
        """Return the Plan a user is on (active sub, else default free plan)."""
        sub = cls.active_for(user)
        if sub:
            return sub.plan
        return Plan.objects.filter(is_default=True, is_active=True).first()

    @classmethod
    def has_premium(cls, user):
        plan = cls.plan_for(user)
        return bool(plan and not plan.is_free and plan.is_active)


# ── Feature-request board ──────────────────────────────────────────
class FeatureRequest(models.Model):
    """Public product feature board with upvotes and staff status."""

    STATUS_OPEN = 'open'
    STATUS_PLANNED = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_SHIPPED = 'shipped'
    STATUS_DECLINED = 'declined'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_PLANNED, 'Planned'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DECLINED, 'Declined'),
    ]
    PUBLIC_STATUSES = (STATUS_OPEN, STATUS_PLANNED, STATUS_IN_PROGRESS, STATUS_SHIPPED)

    CATEGORY_PLATFORM = 'platform'
    CATEGORY_PORTAL = 'portal'
    CATEGORY_COMMUNITY = 'community'
    CATEGORY_BILLING = 'billing'
    CATEGORY_OTHER = 'other'
    CATEGORY_CHOICES = [
        (CATEGORY_PLATFORM, 'Platform'),
        (CATEGORY_PORTAL, 'Client Portal'),
        (CATEGORY_COMMUNITY, 'Community'),
        (CATEGORY_BILLING, 'Billing'),
        (CATEGORY_OTHER, 'Other'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=False)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default=CATEGORY_PLATFORM)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feature_requests',
    )
    vote_count = models.PositiveIntegerField(default=0)
    staff_notes = models.TextField(blank=True, help_text="Internal notes (not shown publicly).")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-vote_count', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or 'feature'
            slug = base
            n = 2
            while FeatureRequest.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_public(self):
        return self.status in self.PUBLIC_STATUSES

    @property
    def status_badge(self):
        return {
            self.STATUS_OPEN: 'bg-secondary',
            self.STATUS_PLANNED: 'bg-info',
            self.STATUS_IN_PROGRESS: 'bg-primary',
            self.STATUS_SHIPPED: 'bg-success',
            self.STATUS_DECLINED: 'bg-danger',
        }.get(self.status, 'bg-secondary')

    def user_has_voted(self, user):
        if not user or not getattr(user, 'is_authenticated', False):
            return False
        return self.votes.filter(user=user).exists()


class FeatureVote(models.Model):
    """One upvote per user per feature request."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='feature_votes',
    )
    feature_request = models.ForeignKey(
        FeatureRequest, on_delete=models.CASCADE, related_name='votes',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('user', 'feature_request')]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user} ▲ {self.feature_request.title}"


class FeatureTask(models.Model):
    """A task within a feature request (featurewise breakdown)."""

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'
    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_DONE, 'Done'),
    ]

    feature_request = models.ForeignKey(
        FeatureRequest, on_delete=models.CASCADE,
        related_name='tasks',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, db_index=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feature_tasks',
    )
    due_date = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.feature_request.title}: {self.title}"

    @property
    def is_overdue(self):
        return self.due_date and self.due_date < timezone.now().date() and self.status != self.STATUS_DONE


class FeatureMicrotask(models.Model):
    """A microtask within a feature task."""

    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_DONE, 'Done'),
    ]

    task = models.ForeignKey(
        FeatureTask, on_delete=models.CASCADE,
        related_name='microtasks',
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO, db_index=True)
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='feature_microtasks',
    )
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.task.title}: {self.title}"
