from django import forms
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from froala_editor.fields import FroalaField
from django.utils import timezone
from django.utils.text import slugify
import hashlib
import logging
import mimetypes
import uuid
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from dovetecenterprises import settings

logger = logging.getLogger(__name__)

_SEND_LOCKS = {}


class MetadataMixin(models.Model):
    """Abstract mixin providing SEO and social sharing metadata fields."""
    meta_title = models.CharField(max_length=200, blank=True, help_text="Override meta title for SEO")
    meta_description = models.CharField(max_length=500, blank=True, help_text="Override meta description for SEO")
    canonical_url = models.URLField(max_length=500, blank=True, help_text="Canonical URL for SEO")
    og_title = models.CharField(max_length=200, blank=True, help_text="Open Graph title")
    og_description = models.CharField(max_length=500, blank=True, help_text="Open Graph description")
    og_image = models.ImageField(upload_to='og_images/', blank=True, null=True, help_text="Open Graph image")
    twitter_card = models.CharField(max_length=50, blank=True, help_text="Twitter card type (summary, summary_large_image)")
    twitter_title = models.CharField(max_length=200, blank=True, help_text="Twitter title")
    twitter_description = models.CharField(max_length=500, blank=True, help_text="Twitter description")
    twitter_image = models.ImageField(upload_to='twitter_images/', blank=True, null=True, help_text="Twitter image")
    published_at = models.DateTimeField(null=True, blank=True, help_text="Actual publication date")

    class Meta:
        abstract = True

    def get_meta_title(self):
        """Return the most appropriate title for this page."""
        return self.meta_title if self.meta_title else (self.title if hasattr(self, 'title') else '')

    def get_meta_description(self):
        """Return the most appropriate description for this page."""
        return self.meta_description if self.meta_description else (self.seo_description[:160] if hasattr(self, 'seo_description') and self.seo_description else '')

    def get_og_title(self):
        """Return the Open Graph title."""
        return self.og_title or self.get_meta_title()

    def get_og_description(self):
        """Return the Open Graph description."""
        return self.og_description or self.get_meta_description()

    def get_og_image(self):
        """Return the Open Graph image URL."""
        if self.og_image and self.og_image.url:
            return self.og_image.url
        return ''

    def get_twitter_title(self):
        """Return the Twitter card title."""
        return self.twitter_title or self.get_meta_title()

    def get_twitter_description(self):
        """Return the Twitter card description."""
        return self.twitter_description or self.get_meta_description()

    def get_twitter_image(self):
        """Return the Twitter card image URL."""
        if self.twitter_image and self.twitter_image.url:
            return self.twitter_image.url
        return self.get_og_image()


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model using email as the unique identifier."""

    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    username = models.CharField(max_length=30, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    objects = UserManager()

    class Meta:
        permissions = [
            ('access_dashboard', 'Can access the staff dashboard'),
        ]

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    def save(self, *args, **kwargs):
        if not self.username:
            self.username = self.email.split('@')[0]
        super().save(*args, **kwargs)

    # ── Convenience helpers ─────────────────────────────────────
    @property
    def is_client(self):
        """True for portal clients (not staff/admin accounts)."""
        return not self.is_staff and not self.is_superuser

    @property
    def is_admin_role(self):
        """True for Administrators group / superusers."""
        return self.is_superuser or self.groups.filter(name='Administrators').exists()

    @property
    def display_name(self):
        if self.username:
            return self.username
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

    @property
    def display_name(self):
        if self.username:
            return self.username
        return f"{self.first_name} {self.last_name}"

    def __str__(self):
        return self.email

    def get_full_name(self):
        """Return the first_name plus the last_name, with a space in between."""
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name

class Profile(models.Model):
    """
    Profile model extends the built-in User model with additional fields.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    is_verified = models.BooleanField(default=False)
    token = models.CharField(max_length=100, null=True, blank=True)
    otp = models.CharField(max_length=6, null=True, blank=True)
    otp_timestamp = models.DateTimeField(null=True, blank=True)
    hashed_id = models.CharField(max_length=64, unique=True, editable=False)
    image = models.ImageField(upload_to='profile', blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)

    def is_otp_expired(self):
        """Check if the OTP is expired (10 minutes)."""
        if self.otp_timestamp:
            return timezone.now() > self.otp_timestamp + timezone.timedelta(minutes=10)
        return True

    def is_token_expired(self):
        """Check if the token is expired (1 hour from user registration)."""
        return timezone.now() > self.user.date_joined + timezone.timedelta(hours=1)

    def save(self, *args, **kwargs):
        """Override save method to generate hashed_id if not present."""
        if not self.hashed_id:
            self.hashed_id = hashlib.sha256(str(self.user.id).encode()).hexdigest()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.email

class Tag(MetadataMixin):
    """
    Tag model for categorizing articles.
    """
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=150, unique=True, null=True, blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class DiscussionTopic(models.Model):
    """A community discussion topic that articles can be linked to."""
    STATUS_OPEN = 'open'
    STATUS_ACTIVE = 'active'
    STATUS_CLOSED = 'closed'
    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_ACTIVE, 'Active'),
        (STATUS_CLOSED, 'Closed'),
    ]
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=False)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    author = models.ForeignKey('Profile', on_delete=models.SET_NULL, null=True, blank=True, related_name='discussion_topics')
    is_pinned = models.BooleanField(default=False)
    vote_count = models.PositiveIntegerField(default=0)
    reply_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-vote_count', '-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)[:200] or 'discussion'
            slug = base
            n = 2
            while DiscussionTopic.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_public(self):
        return self.status == self.STATUS_OPEN


class Article(models.Model):
    """
    Article model with fields for SEO and content editing using Froala.
    
    Args:
        id (AutoField): Unique identifier for the article.
        title (CharField): Title of the article.
        content (FroalaField): Content of the article.
        seo_description (TextField): Description for SEO purposes.
        slug (SlugField): Unique slug for the article.
        user (ForeignKey): Reference to the User who created the article.
        image (ImageField): Featured image for the article.
        created_at (DateTimeField): Timestamp when the article was created.
        updated_at (DateTimeField): Timestamp when the article was last updated.
        category (CharField): Category of the article.
        tags (ManyToManyField): Tags associated with the article.
        likes (PositiveIntegerField): Number of likes for the article.
        dislikes (PositiveIntegerField): Number of dislikes for the article.
        views (PositiveIntegerField): Number of views for the article.
        author (ForeignKey): Reference to the Profile who created the article.
        featured (BooleanField): Indicates if the article is featured.
        
    Methods:
        __str__(): Returns a string representation of the article.
        save(*args, **kwargs): Overrides the save method to generate a unique slug if not present.
        hashed_id(): Generates a hashed_id for the article if ID exists.
        generate_unique_slug(): Generates a unique slug for the
    """
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=1000, unique=True)
    content = FroalaField()
    seo_description = models.TextField(max_length=500, blank=True, null=True)
    slug = models.SlugField(max_length=1000, unique=True, null=True, blank=True)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='blog', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    category = models.CharField(max_length=100, blank=True, null=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='articles')
    likes = models.PositiveIntegerField(default=0)
    dislikes = models.PositiveIntegerField(default=0)
    views = models.PositiveIntegerField(default=0)
    author = models.ForeignKey(Profile, blank=True, null=True, on_delete=models.CASCADE, related_name='articles')
    featured = models.BooleanField(default=False)
    status = models.CharField(
        max_length=20, 
        choices=[('draft', 'Draft'), ('scheduled', 'Scheduled'), ('published', 'Published'), ('archived', 'Archived')],
        default='published'
    )
    scheduled_at = models.DateTimeField(null=True, blank=True, help_text="Future date to schedule publication")
    deleted = models.BooleanField(default=False)
    # Resource-specific fields
    # Newsletter performance counters (rolled up by Newsletter._update_content_performance)
    newsletter_sent_count = models.PositiveIntegerField(default=0, help_text="Times included in a newsletter send")
    newsletter_open_count = models.PositiveIntegerField(default=0, help_text="Newsletter opens attributed to this article")
    newsletter_click_count = models.PositiveIntegerField(default=0, help_text="Newsletter link clicks attributed to this article")
    newsletter_read_count = models.PositiveIntegerField(default=0, help_text="Newsletter recipients who signed in")
    newsletter_failed_count = models.PositiveIntegerField(default=0, help_text="Newsletter deliveries that failed")
    is_resource = models.BooleanField(default=False, help_text="Mark as a downloadable resource")
    resource_type = models.CharField(max_length=20, choices=[
        ('document', 'Document (PDF/Doc)'),
        ('guide', 'Guide/Tutorial'),
        ('template', 'Template'),
        ('reference', 'Reference Material'),
        ('tool', 'Tool/Software'),
        ('video', 'Video'),
        ('other', 'Other'),
    ], default='other', blank=True, null=True, help_text="Type of resource")
    resource_file = models.FileField(upload_to='resources', blank=True, null=True, help_text="Downloadable resource file")
    resource_url = models.URLField(max_length=500, blank=True, help_text="External resource URL")
    # Discussion-specific fields
    is_discussion = models.BooleanField(default=False, help_text="Mark as a community discussion point")
    discussion_topic = models.ForeignKey('DiscussionTopic', on_delete=models.SET_NULL, null=True, blank=True, related_name='articles', help_text="Associated discussion topic")
    hashed_id = models.CharField(max_length=64, unique=True, editable=False, null=True, blank=True)
    # Structured editorial and sharing metadata
    meta_title = models.CharField(max_length=200, blank=True, help_text="Override meta title for SEO")
    meta_description = models.CharField(max_length=500, blank=True, help_text="Override meta description for SEO")
    canonical_url = models.URLField(max_length=500, blank=True, help_text="Canonical URL for SEO")
    og_title = models.CharField(max_length=200, blank=True, help_text="Open Graph title")
    og_description = models.CharField(max_length=500, blank=True, help_text="Open Graph description")
    og_image = models.ImageField(upload_to='og_images/', blank=True, null=True, help_text="Open Graph image")
    twitter_card = models.CharField(max_length=50, blank=True, help_text="Twitter card type (summary, summary_large_image)")
    twitter_title = models.CharField(max_length=200, blank=True, help_text="Twitter title")
    twitter_description = models.CharField(max_length=500, blank=True, help_text="Twitter description")
    twitter_image = models.ImageField(upload_to='twitter_images/', blank=True, null=True, help_text="Twitter image")
    published_at = models.DateTimeField(null=True, blank=True, help_text="Actual publication date")


    class Meta:
        abstract = False

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save method to handle slugs and instant publication."""
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        # If published manually but no schedule set, set to now
        if self.status == 'published' and not self.scheduled_at:
            self.scheduled_at = timezone.now()
            
        super().save(*args, **kwargs)


    @property
    def hashed_id(self):
        """Generate a hashed_id for the article if ID exists."""
        return hashlib.sha256(str(self.id).encode()).hexdigest() if self.id else None

    def generate_unique_slug(self):
        """Generate a unique slug for the article."""
        slug = slugify(self.title)
        unique_slug = slug
        counter = 1
        while Article.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{slug}-{counter}"
            counter += 1
        return unique_slug

    def get_schema_org_json_ld(self):
        """Generate schema.org Article JSON-LD markup."""
        return {
            '@context': 'https://schema.org',
            '@type': 'Article',
            'headline': self.title,
            'image': self.og_image.url if self.og_image else (self.image.url if self.image else ''),
            'author': {
                '@type': 'Profile',
                'name': self.author.user.get_full_name() if self.author else '',
                'email': self.author.user.email if self.author else '',
            },
            'datePublished': self.created_at.isoformat() if self.created_at else '',
            'dateModified': self.updated_at.isoformat() if self.updated_at else '',
            'description': self.seo_description or self.meta_description or '',
            'mainEntityOfPage': self.canonical_url or self.get_absolute_url(),
        }

    def get_absolute_url(self):
        """Return the canonical URL for the article."""
        return f"/blog-detail/{self.slug}/" if self.slug else '/'

class Comment(models.Model):
    """
    Comment model represents a user's comment on an article.

    Attributes:
        article (ForeignKey): Reference to the related Article object.
        user (ForeignKey): Reference to the User who made the comment.
        content (TextField): The content of the comment.
        created_at (DateTimeField): Timestamp when the comment was created.
        hashed_id (CharField): Unique hashed identifier for the comment.
        is_deleted (BooleanField): Indicates if the comment is soft deleted.

    Methods:
        __str__(): Returns a string representation of the comment.
        save(*args, **kwargs): Overrides the save method to generate a hashed_id if it doesn't exist.
        delete(*args, **kwargs): Overrides the delete method to perform a soft delete by setting is_deleted to True.
    """
    article = models.ForeignKey(Article, related_name='comments', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    hashed_id = models.CharField(max_length=64, unique=True, editable=False, null=True, blank=True)
    is_deleted = models.BooleanField(default=False)  # Soft delete field

    def __str__(self):
        return f"Comment by {self.user.username} on {self.article.title}"

    def save(self, *args, **kwargs):
        if not self.hashed_id:
            self.hashed_id = hashlib.sha256(f"{self.article.id}-{self.user.id}".encode()).hexdigest()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()

class Reply(models.Model):
    """
    Reply model linked to a Comment.
    """
    comment = models.ForeignKey(Comment, related_name='replies', on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    hashed_id = models.CharField(max_length=64, unique=True, editable=False, null=True, blank=True)

    def __str__(self):
        return f"Reply by {self.user.username} on comment {self.comment.id}"

    def save(self, *args, **kwargs):
        """Override save method to generate hashed_id if not present."""
        if not self.hashed_id:
            self.hashed_id = hashlib.sha256(f"{self.comment.id}-{self.user.id}".encode()).hexdigest()
        super().save(*args, **kwargs)

class Like(models.Model):
    """
    Like model for users to like articles.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} liked {self.article.title}"
    
class Dislike(models.Model):
    """
    Dislike model for users to dislike articles.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    dislike_ptr = models.PositiveBigIntegerField(default=0)

    def __str__(self):
        return f"{self.user.username} disliked {self.article.title}"

    
class Feedback(models.Model):
    """
    Feedback model for users to provide feedback.
    """
    name = models.CharField(max_length=100)
    email = models.EmailField()
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.name}"
    
class Report(models.Model):
    """
    Report model for users to report articles or comments.
    """
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


class Notification(models.Model):
    """In-app notification for staff/client events (tickets, funnel, questionnaires)."""

    VERB_ASSIGNED = 'assigned'
    VERB_TRANSFERRED = 'transferred'
    VERB_REFERRED = 'referred'
    VERB_STATUS_CHANGE = 'status_change'
    VERB_PRIORITY_CHANGE = 'priority_change'
    VERB_ESCALATED = 'escalated'
    VERB_CONVERTED = 'converted'
    VERB_STAGE_CHANGE = 'stage_change'
    VERB_QUESTIONNAIRE_SENT = 'questionnaire_sent'
    VERB_QUESTIONNAIRE_COMPLETED = 'questionnaire_completed'
    VERB_NOTE = 'note'
    VERB_CHOICES = [
        (VERB_ASSIGNED, 'Assigned'),
        (VERB_TRANSFERRED, 'Transferred'),
        (VERB_REFERRED, 'Referred'),
        (VERB_STATUS_CHANGE, 'Status changed'),
        (VERB_PRIORITY_CHANGE, 'Priority changed'),
        (VERB_ESCALATED, 'Escalated'),
        (VERB_CONVERTED, 'Converted'),
        (VERB_STAGE_CHANGE, 'Stage changed'),
        (VERB_QUESTIONNAIRE_SENT, 'Questionnaire sent'),
        (VERB_QUESTIONNAIRE_COMPLETED, 'Questionnaire completed'),
        (VERB_NOTE, 'Note'),
    ]

    recipient = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='notifications',
    )
    actor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='notifications_actor',
    )
    verb = models.CharField(max_length=40, choices=VERB_CHOICES, default=VERB_NOTE)
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True)
    link = models.CharField(max_length=500, blank=True)
    email_sent = models.BooleanField(default=False)
    whatsapp_sent = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['recipient', 'read_at'])]

    def __str__(self):
        return f"→ {self.recipient.email}: {self.title}"

    @property
    def is_unread(self):
        return self.read_at is None

    def __str__(self):
        return f"Report by {self.user.username} on {self.article.title}"
        if image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Image file too large ( > 5MB )")
        return image
    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        content = cleaned_data.get('content')

        if title and content:
            if 'bad word' in title or 'bad word' in content:
                raise forms.ValidationError('Title or content contains inappropriate language')

        return cleaned_data
class Advertisement(models.Model):  
    """
    Advertisement model for managing advertisements on the website.
    """
    title = models.CharField(max_length=100)
    description = models.TextField()
    image = models.ImageField(upload_to='advertisements')
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class Job(MetadataMixin, models.Model):
    """
    Job model for managing job postings.
    """
    title = models.CharField(max_length=100)
    description = FroalaField(
        options={
            'heightMin': 200,
            'heightMax': 500,
            'toolbarButtons': ['bold', 'italic', 'underline', 'paragraphFormat', 'align']
        }
    )
    location = models.CharField(max_length=100)
    company = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2)
    level = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    department = models.ForeignKey(
        'Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='jobs',
    )
    employment_type = models.CharField(
        max_length=50, blank=True,
        help_text="e.g., Full-time, Part-time, Contract, Internship"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def __str__(self):
        return self.title
    def clean(self):
        cleaned_data = super().clean()
        title = cleaned_data.get('title')
        description = cleaned_data.get('description')

        if title and description:
            if 'bad word' in title or 'bad word' in description:
                raise forms.ValidationError('Title or description contains inappropriate language')

        return cleaned_data
class NewsletterSubscription(models.Model):
    """
    NewsletterSubscription model for managing newsletter subscriptions.
    """
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='newsletter_subscriptions')
    email = models.EmailField(unique=True)
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    is_verified = models.BooleanField(default=False)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)



    def __str__(self):
        return self.email
    
class Newsletter(MetadataMixin):
    """
    Newsletter model for managing email campaigns with enhanced features and validation.
    """
    subject = models.CharField(max_length=200, help_text="Newsletter subject line")
    content = FroalaField(
        help_text="Newsletter content in HTML format",
        options={
            'heightMin': 200,
            'heightMax': 500,
            'toolbarButtons': ['bold', 'italic', 'underline', 'paragraphFormat', 'align'],
            'placeholderText': 'Enter newsletter content here...'
        },
        image_upload=True,
        file_upload=True,
    )
    recipients = models.ManyToManyField(
        NewsletterSubscription, 
        related_name='newsletters',
        limit_choices_to={'unsubscribed_at': None},
        blank=True
    )
    manual_recipients = models.TextField(
        blank=True, 
        help_text="Ad-hoc email addresses separated by commas (e.g., contact@example.com, lead@example.com)"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, 
                            choices=[('draft', 'Draft'),
                                   ('scheduled', 'Scheduled'),
                                   ('sending', 'Sending'),
                                   ('sent', 'Sent'),
                                   ('partial', 'Partially Sent'),
                                   ('failed', 'Failed')],
                            default='draft')
    slug = models.SlugField(max_length=250, unique=True, null=True, blank=True)
    tracking_enabled = models.BooleanField(default=True)
    accent_color = models.CharField(max_length=7, default='#007bff', help_text='Brand accent color for email design')
    content_type = models.CharField(max_length=20, blank=True, help_text='Content type: article, service, product, case_study, resource, advertisement')
    content_id = models.PositiveIntegerField(null=True, blank=True, help_text='ID of the related content')
    allow_attachments = models.BooleanField(default=True, help_text='Allow attachments in this newsletter')
    resend_count = models.PositiveIntegerField(default=0, help_text='Number of times this newsletter has been resent')
    tracking_pixel_enabled = models.BooleanField(default=True, help_text='Enable tracking pixel for open tracking')
    click_tracking_enabled = models.BooleanField(default=True, help_text='Enable click tracking')
    advertisement = models.ForeignKey('Advertisement', on_delete=models.SET_NULL, null=True, blank=True, related_name='newsletters', help_text='Primary advertisement for this newsletter')
    adverts = models.ManyToManyField('Advertisement', blank=True, related_name='newsletter_placements', help_text='Advertisements to render as blocks in this newsletter')
    preheader = models.CharField(max_length=300, blank=True, help_text='Preview text shown in the inbox next to the subject')
    subtitle = models.CharField(max_length=300, blank=True, help_text='Optional subtitle shown under the headline')
    cta_title = models.CharField(max_length=200, blank=True, help_text='Call-to-action headline')
    cta_text = models.TextField(blank=True, help_text='Call-to-action body copy')
    cta_label = models.CharField(max_length=100, blank=True, help_text='Call-to-action button label')
    cta_url = models.URLField(max_length=500, blank=True, help_text='Call-to-action destination URL')

    class Meta:
        ordering = ['-created_at']
        indexes = [models.Index(fields=['status', 'scheduled_for']), models.Index(fields=['content_type', 'content_id'])]

    def get_all_recipient_emails(self):
        """
        Combine verified subscribers and manual ad-hoc emails.

        Only verified subscribers who haven't unsubscribed. Addresses that have
        unsubscribed are always excluded, including when typed into
        ``manual_recipients`` — an opt-out must be honoured on every send.
        """
        emails = list(
            self.recipients.filter(
                unsubscribed_at__isnull=True,
                is_verified=True
            ).values_list('email', flat=True)
        )
        if self.manual_recipients:
            emails.extend(e.strip() for e in self.manual_recipients.split(',') if '@' in e)

        # Honour prior opt-outs regardless of how the address was supplied.
        unsubscribed = {
            (u or '').strip().lower()
            for u in NewsletterSubscription.objects.filter(
                unsubscribed_at__isnull=False
            ).values_list('email', flat=True)
        }
        return sorted({e for e in emails if e and e.strip().lower() not in unsubscribed})

    def get_verified_recipients(self):
        """Get verified newsletter subscription objects."""
        return self.recipients.filter(unsubscribed_at__isnull=True, is_verified=True)

    def get_failed_emails(self):
        """Get emails that failed in previous attempts."""
        from .models import NewsletterLog
        return list(
            NewsletterLog.objects.filter(
                newsletter=self,
                status='failed'
            ).values_list('email', flat=True).distinct()
        )

    def send_newsletter(self, batch_size=500, resend=False, only_failed=False):
        """
        Render and send this newsletter to its recipients.

        Each recipient gets a personalised copy carrying their own tracking id, so
        opens, clicks and logins are attributed per-recipient. Supports file
        attachments, content references (articles, resources, services, products,
        case studies, adverts), resends, and failed-only retries.
        """
        import threading

        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives, get_connection

        from .models import NewsletterAttachment, NewsletterLog

        guard = _SEND_LOCKS.setdefault(self.pk, threading.Lock())
        if not guard.acquire(blocking=False):
            logger.warning(
                "Newsletter %r is already being sent; skipping duplicate call.", self.subject
            )
            return False
        try:
            return self._send_locked(batch_size=batch_size, resend=resend, only_failed=only_failed)
        finally:
            guard.release()

    def _send_locked(self, batch_size=500, resend=False, only_failed=False):
        """Body of send_newsletter, executed while holding the per-newsletter lock."""
        from django.conf import settings
        from django.core.mail import EmailMultiAlternatives, get_connection

        from .models import NewsletterAttachment, NewsletterLog

        if self.status == 'sent' and not (resend or only_failed):
            logger.info("Newsletter %r already sent; skipping.", self.subject)
            return False

        recipients = self.get_all_recipient_emails()
        if only_failed:
            failed = set(self.get_failed_emails())
            recipients = [e for e in recipients if e in failed]
        if resend and not only_failed and self.status == 'sent':
            recipients = [e for e in recipients if e not in set(self.get_delivered_emails())]

        admin_emails = [addr for _, addr in (settings.ADMINS or []) if addr]
        recipients.extend(addr for addr in admin_emails if addr not in recipients)

        for subscription in self.recipients.filter(
            user__isnull=False, user__is_active=True, user__email__isnull=False
        ):
            addr = subscription.user.email
            if addr and addr not in recipients:
                recipients.append(addr)

        recipients = sorted({addr.strip().lower() for addr in recipients if addr and '@' in addr})

        if not recipients:
            logger.warning("Newsletter %r has no recipients; aborting.", self.subject)
            return False

        subscriptions = {
            (s.email or '').strip().lower(): s
            for s in self.recipients.all()
        }

        # Read attachment payloads once so every recipient reuses the same bytes.
        payloads = []
        if self.allow_attachments:
            for attachment in NewsletterAttachment.objects.filter(newsletter=self).order_by('order'):
                try:
                    attachment.file.open('rb')
                    payloads.append((
                        attachment.file.read(),
                        attachment.name or attachment.file.name.rsplit('/', 1)[-1],
                        attachment.content_type or 'application/octet-stream',
                    ))
                except Exception as exc:
                    logger.error("Could not read attachment %s: %s", attachment.name, exc)

        site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
        connection = get_connection()
        now = timezone.now()

        self.status = 'sending'
        self.save(update_fields=['status'])

        sent_count = 0
        failed_count = 0

        try:
            for start_index in range(0, len(recipients), batch_size):
                batch = recipients[start_index:start_index + batch_size]
                for address in batch:
                    log = NewsletterLog.objects.create(
                        newsletter=self,
                        email=address,
                        status='sent',
                        user=subscriptions[address].user if address in subscriptions and subscriptions[address].user_id else None,
                        sent_at=now,
                    )
                    subscription = subscriptions.get(address)
                    if not (subscription and subscription.token):
                        # Manually entered recipients have no subscription row yet.
                        # Create one so every email carries a valid, per-recipient
                        # unsubscribe token instead of a shared link. The token
                        # itself comes from the field default so its format stays
                        # identical to tokens issued by the signup flow.
                        subscription, _ = NewsletterSubscription.objects.get_or_create(
                            email=address,
                            defaults={'is_verified': True},
                        )
                        subscriptions[address] = subscription
                    unsubscribe_url = f"{site_url}/newsletter/unsubscribe/{subscription.token}/"

                    try:
                        html_content = self._build_html_content(
                            tracking_id=log.tracking_id,
                            unsubscribe_url=unsubscribe_url,
                        )
                        text_content = self._build_text_content(
                            tracking_id=log.tracking_id,
                            unsubscribe_url=unsubscribe_url,
                        )
                        message = EmailMultiAlternatives(
                            subject=self.subject,
                            body=text_content,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[address],
                            connection=connection,
                        )
                        message.attach_alternative(html_content, 'text/html')
                        for data, name, mime in payloads:
                            message.attach(name, data, mime)
                        message.send(fail_silently=False)
                        sent_count += 1
                    except Exception as exc:
                        failed_count += 1
                        log.status = 'failed'
                        log.error = str(exc)
                        log.save(update_fields=['status', 'error'])
                        logger.error("Failed to send %r to %s: %s", self.subject, address, exc)

            if failed_count and sent_count:
                new_status = 'partial'
            elif failed_count:
                new_status = 'failed'
            else:
                new_status = 'sent'

            self.status = new_status
            self.sent_at = timezone.now()
            if resend and not only_failed:
                self.resend_count = (self.resend_count or 0) + 1
            self.save(update_fields=['status', 'sent_at', 'resend_count'])

            self._update_content_performance(sent_count, failed_count, 0, 0)

            logger.info(
                "Newsletter %r dispatched: %s sent, %s failed (status=%s).",
                self.subject, sent_count, failed_count, new_status,
            )
            return True
        except Exception as exc:
            self.status = 'failed'
            self.save(update_fields=['status'])
            logger.error("Newsletter %r aborted: %s", self.subject, exc)
            raise

    def resend_newsletter(self, only_failed=False):
        """
        Resend this newsletter. By default only recipients who were not
        successfully delivered the first time receive it again.
        """
        if only_failed:
            return self.send_newsletter(resend=True, only_failed=True)
        return self.send_newsletter(resend=True)

    def get_delivered_emails(self):
        """
        Addresses that already received this newsletter successfully.
        """
        from .models import NewsletterLog
        return list(
            NewsletterLog.objects.filter(newsletter=self)
            .exclude(status='failed')
            .values_list('email', flat=True)
            .distinct()
        )

    def _update_content_performance(self, sent, failed, opened, clicked):
        """
        Roll newsletter delivery counts into the referenced content so article,
        case study, service and product performance can be reported.
        """
        counters = (
            ('newsletter_sent_count', sent),
            ('newsletter_open_count', opened),
            ('newsletter_click_count', clicked),
            ('newsletter_failed_count', failed),
        )

        try:
            groups = self._resolve_content_groups()
        except Exception as exc:
            logger.error("Could not resolve content references for %r: %s", self.subject, exc)
            return

        seen = set()
        for objects in groups.values():
            for obj in objects:
                if obj is None:
                    continue
                # Key on model + pk: PKs are only unique per table, so an
                # Article(pk=1) would otherwise mask a CaseStudy(pk=1).
                key = (type(obj)._meta.label_lower, obj.pk)
                if key in seen:
                    continue
                seen.add(key)
                changed = []
                for field, value in counters:
                    if not value or not hasattr(obj, field):
                        continue
                    try:
                        setattr(obj, field, (getattr(obj, field) or 0) + value)
                        changed.append(field)
                    except (TypeError, ValueError):
                        continue
                if not changed:
                    continue
                try:
                    obj.save(update_fields=changed)
                except Exception as exc:
                    logger.warning("Could not update performance on %r: %s", obj, exc)

    def _resolve_content_groups(self):
        """
        Resolve the content references attached to this newsletter, grouped by kind
        so the email template can render each section.
        """
        from django.contrib.contenttypes.models import ContentType
        from .models import Article, Advertisement
        from app.models import CaseStudy
        from shop.models import Category as ShopCategory, Product

        groups = {
            'articles': [],
            'services': [],
            'products': [],
            'case_studies': [],
            'resources': [],
            'adverts': [],
        }

        for ref in self.content_references.select_related('content_type').all():
            obj = ref.content_object
            if obj is None:
                continue
            kind = ref.kind
            if kind == 'article':
                groups['articles'].append(obj)
            elif kind == 'resource':
                groups['resources'].append(obj)
            elif kind == 'service':
                groups['services'].append(obj)
            elif kind == 'product':
                groups['products'].append(obj)
            elif kind == 'case_study':
                groups['case_studies'].append(obj)
            elif kind == 'advertisement':
                groups['adverts'].append(obj)

        # Legacy single content_type/content_id reference
        if not any(groups.values()) and self.content_type and self.content_id:
            mapping = {
                'article': ('articles', Article.objects.filter(pk=self.content_id).first()),
                'resource': ('resources', Article.objects.filter(pk=self.content_id).first()),
                'service': ('services', ShopCategory.objects.filter(pk=self.content_id).first()),
                'product': ('products', Product.objects.filter(pk=self.content_id).first()),
                'case_study': ('case_studies', CaseStudy.objects.filter(pk=self.content_id).first()),
                'advertisement': ('adverts', Advertisement.objects.filter(pk=self.content_id).first()),
            }
            bucket, obj = mapping.get(self.content_type, (None, None))
            if bucket and obj is not None:
                groups[bucket].append(obj)

        if self.advertisement_id and self.advertisement not in groups['adverts']:
            groups['adverts'].insert(0, self.advertisement)

        for advert in self.adverts.all():
            if advert not in groups['adverts']:
                groups['adverts'].append(advert)

        return groups

    def _rewrite_links(self, html, tracking_id):
        """
        Rewrite every anchor in the given HTML to route through the click tracker.
        Fragment-only, mailto:, tel:, sms: and javascript: links are left untouched.
        """
        import re
        from urllib.parse import quote

        from django.conf import settings
        site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
        pattern = re.compile(r'<a\b([^>]*?)\bhref="([^"]+)"([^>]*)>(.*?)</a>', re.DOTALL | re.IGNORECASE)

        def replace(match):
            before_attrs, href, after_attrs, inner = match.groups()
            href = href.strip()
            if not href or href.startswith('#'):
                return match.group(0)
            if href.lower().startswith(('mailto:', 'tel:', 'sms:', 'javascript:')):
                return match.group(0)
            if href.lower().startswith(('http://', 'https://')):
                target = href
            else:
                target = f'{site_url}{href}'
            tracked = f'{site_url}/track/click/{tracking_id}/?url={quote(target, safe="")}'
            return f'<a{before_attrs}href="{tracked}"{after_attrs}>{inner}</a>'

        return pattern.sub(replace, html or '')

    def _build_html_content(self, tracking_id=None, unsubscribe_url=None):
        """
        Render the newsletter as a responsive, Apple-style HTML email.
        """
        from django.conf import settings
        from django.template.loader import render_to_string

        site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
        groups = self._resolve_content_groups()

        body = self.content or ''
        if self.click_tracking_enabled and tracking_id:
            body = self._rewrite_links(body, tracking_id)

        context = {
            'newsletter': self,
            'site_url': site_url,
            'accent_color': self.accent_color or '#0071e3',
            'year': timezone.now().year,
            'preheader': self.preheader,
            'content': body,
            'articles': groups['articles'],
            'services': groups['services'],
            'products': groups['products'],
            'case_studies': groups['case_studies'],
            'resources': groups['resources'],
            'adverts': groups['adverts'],
            'attachments': self.attachments.all() if self.allow_attachments else [],
            'service_url': self.cta_url or f"{site_url}/services/",
            'cta_title': self.cta_title,
            'cta_text': self.cta_text,
            'cta_label': self.cta_label,
            'cta_url': self.get_cta_link(),
            'unsubscribe_url': unsubscribe_url or f"{site_url}/unsubscribe/",
            'tracking_pixel_url': (
                f"{site_url}/track/open/{tracking_id}/" if (tracking_id and self.tracking_pixel_enabled) else ''
            ),
        }
        return render_to_string('emails/newsletter.html', context)

    def _html_to_text(self, html):
        """
        Convert an HTML fragment to readable plain text: drop script/style, turn
        block boundaries into newlines, then strip remaining markup.
        """
        import re

        from django.utils.html import strip_tags

        if not html:
            return ''

        cleaned = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.DOTALL | re.IGNORECASE)
        cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(
            r'</\s*(p|div|li|tr|td|h1|h2|h3|h4|h5|h6|blockquote|section)\s*>',
            '\n\n',
            cleaned,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r'<li[^>]*>', '  - ', cleaned, flags=re.IGNORECASE)
        text = strip_tags(cleaned)
        text = text.replace('&nbsp;', ' ').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = re.sub(r'[ \t]+', ' ', text)
        return re.sub(r'\n{3,}', '\n\n', text).strip()

    def _build_text_content(self, tracking_id=None, unsubscribe_url=None):
        """
        Build the plain-text alternative: no CSS, no markup, readable in any client.
        """
        import re

        from django.conf import settings
        from django.utils.html import strip_tags

        site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
        groups = self._resolve_content_groups()

        def label(obj, *names):
            for name in names:
                value = getattr(obj, name, None)
                if value:
                    return str(value)
            return str(obj)

        def summary(obj, *names, limit=140):
            for name in names:
                value = getattr(obj, name, None)
                if value:
                    return self._html_to_text(str(value)).replace('\n', ' ')[:limit]
            return ''

        lines = [self.subject, '']
        if self.preheader:
            lines += [self.preheader, '']
        if self.subtitle:
            lines += [self.subtitle, '']
        lines += ['=' * 60, '']

        body = self._html_to_text(self.content)
        if body:
            lines += [body, '']

        if groups['articles']:
            lines += ['FROM THE BLOG', '-' * 60]
            for article in groups['articles']:
                url = f"{site_url}/blog-detail/{article.slug}"
                lines += [f"* {label(article, 'title', 'name')}", f"  {url}"]
                text = summary(article, 'content', 'seo_description')
                if text:
                    lines += [f"  {text}"]
            lines += ['']

        if groups['resources']:
            lines += ['FREE RESOURCES', '-' * 60]
            for resource in groups['resources']:
                target = getattr(resource, 'get_absolute_url', None)
                url = f"{site_url}{target()}" if callable(target) else ''
                lines += [f"* {label(resource, 'title', 'name')}", f"  {url}"]
            lines += ['']

        if groups['services']:
            lines += ['OUR SERVICES', '-' * 60]
            for service in groups['services']:
                lines += [f"* {label(service, 'title', 'name')}", f"  {summary(service, 'description', 'content', limit=120)}"]
            lines += [f"Browse all services: {site_url}/services/", '']

        if groups['products']:
            lines += ['FEATURED PRODUCTS', '-' * 60]
            for product in groups['products']:
                lines += [f"* {label(product, 'name', 'title')} - {product.price}", f"  {site_url}/shop/"]
            lines += ['']

        if groups['case_studies']:
            lines += ['CASE STUDIES', '-' * 60]
            for case_study in groups['case_studies']:
                lines += [f"* {label(case_study, 'name', 'title')}", f"  {site_url}/case-study/{case_study.slug}/"]
                text = summary(case_study, 'tagline', 'overview', 'description')
                if text:
                    lines += [f"  {text}"]
            lines += ['']

        if groups['adverts']:
            lines += ['SPONSORED', '-' * 60]
            for advert in groups['adverts']:
                lines += [f"* {label(advert, 'title', 'name')} - {getattr(advert, 'url', '')}"]
                text = summary(advert, 'description', limit=120)
                if text:
                    lines += [f"  {text}"]
            lines += ['']

        if self.allow_attachments:
            attachments = list(self.attachments.all())
            if attachments:
                lines += ['ATTACHMENTS', '-' * 60]
                for attachment in attachments:
                    size = f" ({attachment.size} bytes)" if attachment.size else ''
                    lines += [f"* {attachment.name}{size}"]
                lines += ['']

        cta_label = self.cta_label or 'Get started'
        lines += ['-' * 60, self.get_cta_link(), cta_label, '']

        if unsubscribe_url:
            lines += [f"Unsubscribe: {unsubscribe_url}", '']
        lines += [f"You are receiving this because you subscribed to the Dovetec Digest.", '']
        lines += [f"© {timezone.now().year} Dovetec Enterprises. All rights reserved."]

        text = re.sub(r'[ \t]+', ' ', '\n'.join(lines))
        return re.sub(r'\n{3,}', '\n\n', text).strip() + '\n'

    def get_cta_link(self):
        """Return the call-to-action destination for this newsletter."""
        from django.conf import settings
        if self.cta_url:
            return self.cta_url
        site_url = (getattr(settings, 'SITE_URL', '') or '').rstrip('/')
        if self.content_type == 'case_study' and self.content_id:
            return f"{site_url}/case-study/"
        if self.content_type == 'product' and self.content_id:
            return f"{site_url}/shop/"
        if self.content_type == 'article' and self.content_id:
            return f"{site_url}/blog/"
        return f"{site_url}/services/" if site_url else '/services/'

    def get_kpi_summary(self):
        """
        Aggregate delivery KPIs for this newsletter.
        """
        from django.db.models import Count, Q

        totals = self.logs.aggregate(
            total=Count('id'),
            sent=Count('id', filter=Q(status='sent') | Q(status='opened') | Q(status='clicked') | Q(status='read')),
            opened=Count('id', filter=Q(opened=True)),
            clicked=Count('id', filter=Q(clicked=True)),
            read=Count('id', filter=Q(read=True)),
            bounced=Count('id', filter=Q(bounced=True)),
            unsubscribed=Count('id', filter=Q(unsubscribed=True)),
            failed=Count('id', filter=Q(status='failed')),
        )
        totals['open_rate'] = round(totals['opened'] / totals['total'] * 100, 1) if totals['total'] else 0.0
        totals['click_rate'] = round(totals['clicked'] / totals['total'] * 100, 1) if totals['total'] else 0.0
        totals['read_rate'] = round(totals['read'] / totals['total'] * 100, 1) if totals['total'] else 0.0
        totals['bounce_rate'] = round(totals['bounced'] / totals['total'] * 100, 1) if totals['total'] else 0.0
        return totals

    def clean(self):
        cleaned_data = super().clean()
        if not self.subject:
            raise forms.ValidationError("Subject is required")
        return cleaned_data

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.generate_unique_slug()
        
        # If set to scheduled/sent but no date provided, set to now
        if (self.status in ['scheduled', 'sent']) and not self.scheduled_for:
            self.scheduled_for = timezone.now()
            
        super().save(*args, **kwargs)


    def generate_unique_slug(self):
        base_slug = slugify(self.subject)
        slug = base_slug
        counter = 1
        while Newsletter.objects.filter(slug=slug).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        return slug

    @property
    def hashed_id(self):
        return hashlib.sha256(str(self.id).encode()).hexdigest() if self.id else None

    def __str__(self):
        return f"{self.subject} ({self.status})"


# ── Career/Job Application model ──────────────────────
class JobApplication(MetadataMixin, models.Model):
    """Applicant Tracking System - Application for a job posting."""

    SOURCE_JOB_PORTAL = 'job_portal'
    SOURCE_LINKEDIN = 'linkedin'
    SOURCE_INDEED = 'indeed'
    SOURCE_REFERRAL = 'referral'
    SOURCE_COMPANY_WEBSITE = 'company_website'
    SOURCE_SOCIAL_MEDIA = 'social_media'
    SOURCE_CAREER_FAIR = 'career_fair'
    SOURCE_INTERNAL = 'internal'

    SOURCE_CHOICES = [
        (SOURCE_JOB_PORTAL, 'Job Portal'),
        (SOURCE_LINKEDIN, 'LinkedIn'),
        (SOURCE_INDEED, 'Indeed'),
        (SOURCE_REFERRAL, 'Employee Referral'),
        (SOURCE_COMPANY_WEBSITE, 'Company Website'),
        (SOURCE_SOCIAL_MEDIA, 'Social Media'),
        (SOURCE_CAREER_FAIR, 'Career Fair'),
        (SOURCE_INTERNAL, 'Internal Transfer'),
    ]

    STAGE_NEW = 'new'
    STAGE_SCREENED = 'screened'
    STAGE_SHORTLISTED = 'shortlisted'
    STAGE_INTERVIEW_SCHEDULED = 'interview_scheduled'
    STAGE_INTERVIEW_COMPLETE = 'interview_complete'
    STAGE_ASSESSMENT = 'assessment'
    STAGE_OFFER = 'offer'
    STAGE_NEGOTIATION = 'negotiation'
    STAGE_HIRED = 'hired'
    STAGE_REJECTED = 'rejected'
    STAGE_WITHDRAWN = 'withdrawn'

    PIPELINE_STAGES = [
        STAGE_NEW, STAGE_SCREENED, STAGE_SHORTLISTED,
        STAGE_INTERVIEW_SCHEDULED, STAGE_INTERVIEW_COMPLETE,
        STAGE_ASSESSMENT, STAGE_OFFER, STAGE_NEGOTIATION, STAGE_HIRED,
    ]

    STATUS_CHOICES = [
        (STAGE_NEW, 'New Application'),
        (STAGE_SCREENED, 'Screened'),
        (STAGE_SHORTLISTED, 'Shortlisted'),
        (STAGE_INTERVIEW_SCHEDULED, 'Interview Scheduled'),
        (STAGE_INTERVIEW_COMPLETE, 'Interview Complete'),
        (STAGE_ASSESSMENT, 'Assessment'),
        (STAGE_OFFER, 'Offer Extended'),
        (STAGE_NEGOTIATION, 'In Negotiation'),
        (STAGE_HIRED, 'Hired'),
        (STAGE_REJECTED, 'Rejected'),
        (STAGE_WITHDRAWN, 'Withdrawn'),
    ]

    job = models.ForeignKey(
        Job, on_delete=models.CASCADE, related_name='applications',
        help_text="The job position being applied for.",
    )
    department = models.ForeignKey(
        'Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='applications',
        help_text="Department the applicant is applying to.",
    )
    candidate_name = models.CharField(max_length=200, help_text="Full legal name of the candidate.")
    candidate_email = models.EmailField(help_text="Primary email for candidate communication.")
    candidate_phone = models.CharField(max_length=30, blank=True)
    candidate_linkedin = models.URLField(max_length=500, blank=True, help_text="Candidate's LinkedIn profile URL")
    cover_letter = models.TextField(blank=True, null=True, help_text="Candidate's cover letter")
    resume = models.FileField(
        upload_to='job_applications/resumes/', blank=True, null=True,
        help_text="CV or resume file (PDF, DOC, DOCX - max 5MB)"
    )
    portfolio = models.FileField(
        upload_to='job_applications/portfolios/', blank=True, null=True,
        help_text="Portfolio or work samples link/file"
    )
    source = models.CharField(
        max_length=30, choices=SOURCE_CHOICES, default=SOURCE_JOB_PORTAL,
        help_text="How the candidate found this job posting.",
    )
    source_detail = models.CharField(max_length=200, blank=True, help_text="Specific source detail (e.g., job board name, referrer name)")
    status = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=STAGE_NEW,
        db_index=True,
        help_text="Current stage in the applicant tracking pipeline.",
    )
    priority = models.CharField(
        max_length=20, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('urgent', 'Urgent')],
        default='medium',
        help_text="Application priority for recruiter workflow.",
    )
    rating = models.PositiveIntegerField(null=True, blank=True, help_text="Candidate rating (1-5) by recruiter.")
    applied_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status_changed_at = models.DateTimeField(auto_now=True, help_text="When current status was set.")
    notes = models.TextField(blank=True, null=True, help_text="Internal recruiter notes.")
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ats_applications_assigned',
        help_text="Recruiter assigned to this application.",
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='ats_applications_reviewed',
    )
    interview_date = models.DateTimeField(null=True, blank=True, help_text="Scheduled interview date and time.")
    interview_location = models.CharField(max_length=500, blank=True, help_text="Interview location or video link.")
    offer_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Offered salary.")
    offer_date = models.DateTimeField(null=True, blank=True)
    offer_conditions = models.TextField(blank=True, null=True, help_text="Offer terms and conditions.")
    rejection_reason = models.TextField(blank=True, null=True, help_text="Reason for rejection.")
    started_at = models.DateTimeField(null=True, blank=True, help_text="Candidate's availability start date.")
    employee_type = models.CharField(max_length=50, blank=True, help_text="Full-time, Part-time, Contract, etc.")

    class Meta:
        ordering = ['-applied_at']
        indexes = [
            models.Index(fields=['status', 'applied_at']),
            models.Index(fields=['job', 'status']),
            models.Index(fields=['department', 'status']),
            models.Index(fields=['candidate_email']),
            models.Index(fields=['source', 'applied_at']),
        ]

    def __str__(self):
        return f"#{self.id}: {self.candidate_name} - {self.job.title}"

    @property
    def is_active(self):
        """Return True if application is still in active pipeline."""
        return self.status not in (self.STAGE_HIRED, self.STAGE_REJECTED, self.STAGE_WITHDRAWN)

    @property
    def pipeline_progress(self):
        """Return progress as percentage through the pipeline."""
        if self.status == self.STAGE_HIRED:
            return 100
        if self.status in (self.STAGE_REJECTED, self.STAGE_WITHDRAWN):
            return 0
        try:
            current_idx = self.PIPELINE_STAGES.index(self.status)
            total = len(self.PIPELINE_STAGES)
            return round((current_idx / (total - 1)) * 100, 1)
        except ValueError:
            return 0

    def move_to_stage(self, new_status, user=None):
        """Move application to a new pipeline stage."""
        if new_status not in dict(self.STATUS_CHOICES):
            raise ValueError(f"Invalid status: {new_status}")
        self.status = new_status
        self.status_changed_at = timezone.now()
        if user:
            self.reviewed_by = user
        self.save(update_fields=['status', 'status_changed_at', 'reviewed_by', 'updated_at'])

    @property
    def days_in_pipeline(self):
        """Return number of days since application was submitted."""
        if self.applied_at:
            return (timezone.now() - self.applied_at).days
        return 0


# ── ATS Interview Model ──────────────────────────────
class Interview(models.Model):
    """Scheduled interview for a job application."""

    INTERVIEW_PHONE = 'phone'
    INTERVIEW_VIDEO = 'video'
    INTERVIEW_IN_PERSON = 'in_person'
    INTERVIEW_ON_SITE = 'on_site'

    INTERVIEW_TYPE_CHOICES = [
        (INTERVIEW_PHONE, 'Phone Screening'),
        (INTERVIEW_VIDEO, 'Video Call'),
        (INTERVIEW_IN_PERSON, 'In-Person'),
        (INTERVIEW_ON_SITE, 'On-Site'),
    ]

    STAGE_INITIAL = 'initial'
    STAGE_TECHNICAL = 'technical'
    STAGE_BEHAVIORAL = 'behavioral'
    STAGE_FINAL = 'final'
    STAGE_HR = 'hr'

    INTERVIEW_STAGE_CHOICES = [
        (STAGE_INITIAL, 'Initial Screening'),
        (STAGE_TECHNICAL, 'Technical'),
        (STAGE_BEHAVIORAL, 'Behavioral'),
        (STAGE_FINAL, 'Final'),
        (STAGE_HR, 'HR'),
    ]

    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name='interviews',
    )
    interview_type = models.CharField(
        max_length=20, choices=INTERVIEW_TYPE_CHOICES, default=INTERVIEW_VIDEO,
    )
    interview_stage = models.CharField(
        max_length=20, choices=INTERVIEW_STAGE_CHOICES, default=STAGE_INITIAL,
    )
    interviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='interviews_conducted',
    )
    scheduled_at = models.DateTimeField()
    duration_minutes = models.PositiveIntegerField(default=60)
    location = models.CharField(max_length=500, blank=True, help_text="Location or video link")
    notes = models.TextField(blank=True, null=True)
    outcome = models.CharField(max_length=20, choices=[('pass', 'Passed'), ('fail', 'Failed'), ('pending', 'Pending')], default='pending')
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['scheduled_at']
        indexes = [
            models.Index(fields=['scheduled_at', 'interviewer']),
            models.Index(fields=['application', 'interview_stage']),
        ]

    def __str__(self):
        return f"Interview for #{self.application.id} - {self.interview_stage}"

    @property
    def is_upcoming(self):
        return self.scheduled_at > timezone.now() and self.outcome == 'pending'

    @property
    def is_overdue(self):
        return self.scheduled_at < timezone.now() and self.outcome == 'pending'


# ── ATS Activity/Note Model ──────────────────────────
class ApplicationNote(models.Model):
    """Activity log notes for a job application."""

    ACTION_CREATED = 'created'
    ACTION_STATUS_CHANGE = 'status_change'
    ACTION_ASSIGNED = 'assigned'
    ACTION_INTERVIEW = 'interview'
    ACTION_OFFER = 'offer'
    ACTION_REJECTED = 'rejected'
    ACTION_NOTE = 'note'
    ACTION_ATTACHMENT = 'attachment'

    ACTION_CHOICES = [
        (ACTION_CREATED, 'Application Created'),
        (ACTION_STATUS_CHANGE, 'Status Changed'),
        (ACTION_ASSIGNED, 'Assigned to Recruiter'),
        (ACTION_INTERVIEW, 'Interview Scheduled'),
        (ACTION_OFFER, 'Offer Extended'),
        (ACTION_REJECTED, 'Rejected'),
        (ACTION_NOTE, 'Note Added'),
        (ACTION_ATTACHMENT, 'Attachment Uploaded'),
    ]

    application = models.ForeignKey(
        JobApplication, on_delete=models.CASCADE, related_name='activity_log',
    )
    action = models.CharField(max_length=30, choices=ACTION_CHOICES, default=ACTION_NOTE)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
    )
    content = models.TextField()
    attachments = models.TextField(blank=True, null=True, help_text="Comma-separated file references")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['application', 'action']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"#{self.application.id} - {self.get_action_display()} by {self.user or 'System'}"


# ── ATS Source Tracking Model ──────────────────────
class SourceTracker(models.Model):
    """Track job posting sources and their effectiveness."""

    source_name = models.CharField(max_length=100)
    source_url = models.URLField(max_length=500, blank=True)
    source_type = models.CharField(
        max_length=30,
        choices=[
            ('job_board', 'Job Board'),
            ('social_media', 'Social Media'),
            ('referral', 'Referral Program'),
            ('career_fair', 'Career Fair'),
            ('company_website', 'Company Website'),
            ('internal', 'Internal'),
            ('other', 'Other'),
        ],
        default='job_board',
    )
    cost_per_hire = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    applications_count = models.PositiveIntegerField(default=0)
    hired_count = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-hired_count']

    def __str__(self):
        return f"{self.source_name} ({self.applications_count} apps, {self.hired_count} hired)"

    @property
    def conversion_rate(self):
        if self.applications_count > 0:
            return round((self.hired_count / self.applications_count) * 100, 1)
        return 0.0


# ── Department model ──────────────────────────────────
class Department(MetadataMixin):
    """Organizational department for filtering job posts."""

    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    headcount = models.PositiveIntegerField(default=0)
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='managed_departments',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def open_positions(self):
        return Job.objects.filter(department=self, is_active=True).count()

    @property
    def total_applications(self):
        return self.applications.filter(is_active=True).count()


class NewsletterLog(models.Model):
    """Per-recipient delivery record and KPI tracker for a newsletter."""
    STATUS_SENT = 'sent'
    STATUS_OPENED = 'opened'
    STATUS_CLICKED = 'clicked'
    STATUS_READ = 'read'
    STATUS_BOUNCED = 'bounced'
    STATUS_FAILED = 'failed'
    STATUS_UNSUBSCRIBED = 'unsubscribed'
    STATUS_CHOICES = [
        (STATUS_SENT, 'Sent'),
        (STATUS_OPENED, 'Opened'),
        (STATUS_CLICKED, 'Clicked'),
        (STATUS_READ, 'Read'),
        (STATUS_BOUNCED, 'Bounced'),
        (STATUS_FAILED, 'Failed'),
        (STATUS_UNSUBSCRIBED, 'Unsubscribed'),
    ]
    newsletter = models.ForeignKey('Newsletter', on_delete=models.CASCADE, related_name='logs')
    email = models.EmailField()
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='newsletter_logs')
    tracking_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, help_text='Tracking identifier for open/click tracking')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_SENT)
    sent_at = models.DateTimeField(null=True, blank=True)
    opened = models.BooleanField(default=False, help_text='Tracking pixel fired')
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked = models.BooleanField(default=False)
    clicked_url = models.URLField(max_length=500, blank=True, null=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    read = models.BooleanField(default=False, help_text='Recipient signed in from this email')
    read_at = models.DateTimeField(null=True, blank=True)
    bounced = models.BooleanField(default=False)
    bounce_reason = models.TextField(blank=True, null=True)
    unsubscribed = models.BooleanField(default=False)
    error = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['newsletter', 'status']),
            models.Index(fields=['email', 'status']),
        ]

    def __str__(self):
        return f"{self.email} - {self.get_status_display()} - {self.newsletter.subject}"

    @property
    def engagement_score(self):
        """Weighted engagement score: opens 1, clicks 2, reads 2, unsubscribe -1."""
        score = 0
        if self.opened:
            score += 1
        if self.clicked:
            score += 2
        if self.read:
            score += 2
        if self.unsubscribed:
            score -= 1
        return max(score, 0)

    def mark_opened(self, ip_address=None, user_agent=None):
        if not self.opened:
            self.opened = True
            self.opened_at = timezone.now()
            self.status = self.STATUS_OPENED
        if ip_address:
            self.ip_address = ip_address
        if user_agent:
            self.user_agent = user_agent[:500]
        self.save(update_fields=['opened', 'opened_at', 'status', 'ip_address', 'user_agent', 'updated_at'])

    def mark_clicked(self, url):
        if not self.clicked:
            self.clicked = True
            self.clicked_at = timezone.now()
            self.status = self.STATUS_CLICKED
        if url:
            self.clicked_url = url[:500]
        self.save(update_fields=['clicked', 'clicked_at', 'status', 'clicked_url', 'updated_at'])

    def mark_read(self):
        if not self.read:
            self.read = True
            self.read_at = timezone.now()
            self.status = self.STATUS_READ
            self.save(update_fields=['read', 'read_at', 'status', 'updated_at'])


class NewsletterAttachment(models.Model):
    """Attachments for newsletters (resources, PDFs, images)."""""
    newsletter = models.ForeignKey('Newsletter', on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='newsletter_attachments/')
    name = models.CharField(max_length=200)
    content_type = models.CharField(max_length=50, blank=True)
    description = models.TextField(blank=True)
    size = models.PositiveIntegerField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.size and self.file:
            try:
                self.size = self.file.size
            except (OSError, ValueError):
                self.size = None
        if not self.content_type and self.file:
            guess = mimetypes.guess_type(self.file.name)[0]
            if guess:
                self.content_type = guess
        super().save(*args, **kwargs)


class NewsletterContentReference(models.Model):
    """
    Generic link from a newsletter to a piece of content (article, resource,
    service, product, case study, or advertisement) rendered in the email.
    """
    KIND_ARTICLE = 'article'
    KIND_RESOURCE = 'resource'
    KIND_SERVICE = 'service'
    KIND_PRODUCT = 'product'
    KIND_CASE_STUDY = 'case_study'
    KIND_ADVERTISEMENT = 'advertisement'
    KIND_CHOICES = [
        (KIND_ARTICLE, 'Article'),
        (KIND_RESOURCE, 'Resource'),
        (KIND_SERVICE, 'Service'),
        (KIND_PRODUCT, 'Product'),
        (KIND_CASE_STUDY, 'Case Study'),
        (KIND_ADVERTISEMENT, 'Advertisement'),
    ]

    newsletter = models.ForeignKey('Newsletter', on_delete=models.CASCADE, related_name='content_references')
    kind = models.CharField(max_length=20, choices=KIND_CHOICES, default=KIND_ARTICLE)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, related_name='+')
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order', 'created_at']
        indexes = [models.Index(fields=['newsletter', 'kind'])]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.content_object}"
