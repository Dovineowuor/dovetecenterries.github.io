from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from froala_editor.fields import FroalaField
from home.models import Article, Tag, Profile, MetadataMixin, Comment as HomeComment, Reply as HomeReply, Dislike as HomeDislike, Like as HomeLike


MODERATION_PENDING = 'pending'
MODERATION_APPROVED = 'approved'
MODERATION_HIDDEN = 'hidden'
MODERATION_REMOVED = 'removed'
MODERATION_FLAGGED = 'flagged'

MODERATION_CHOICES = [
    (MODERATION_PENDING, 'Pending Approval'),
    (MODERATION_APPROVED, 'Approved'),
    (MODERATION_HIDDEN, 'Hidden'),
    (MODERATION_REMOVED, 'Removed'),
    (MODERATION_FLAGGED, 'Flagged'),
]


class ModerationMixin(models.Model):
    """Mixin adding moderation fields to community models."""
    moderation_state = models.CharField(
        max_length=20, choices=MODERATION_CHOICES, default=MODERATION_PENDING,
        db_index=True,
        help_text="Moderation status. Posts require approval before public visibility.",
    )
    flag_reason = models.TextField(blank=True, null=True)
    flagged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_flagged',
    )
    flagged_at = models.DateTimeField(null=True, blank=True)
    moderator_decision = models.TextField(blank=True, null=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='%(class)s_moderated',
    )
    moderated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    @property
    def is_approved(self):
        return self.moderation_state == MODERATION_APPROVED

    @property
    def is_public(self):
        return self.moderation_state == MODERATION_APPROVED


# Updated community Post model inheriting from Article
class Post(ModerationMixin, Article):
    topic = models.ForeignKey(Tag, on_delete=models.CASCADE, related_name='posts')

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save to enforce moderation: posts require approval."""
        if not self.moderation_state:
            self.moderation_state = MODERATION_PENDING
        super().save(*args, **kwargs)

    @property
    def hashed_id(self):
        return hashlib.md5(str(self.id).encode()).hexdigest() if self.id else None

    def generate_unique_slug(self):
        slug = slugify(self.title)
        unique_slug = slug
        counter = 1
        while Post.objects.filter(slug=unique_slug).exists():
            unique_slug = f"{slug}-{counter}"
            counter += 1
        return unique_slug

    def approve(self, moderator):
        """Approve the post for public visibility."""
        self.moderation_state = MODERATION_APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.save(update_fields=['moderation_state', 'moderated_by', 'moderated_at', 'updated_at'])

    def flag(self, reason, reporter):
        """Flag the post for moderation review."""
        self.moderation_state = MODERATION_FLAGGED
        self.flag_reason = reason
        self.flagged_by = reporter
        self.flagged_at = timezone.now()
        self.save(update_fields=['moderation_state', 'flag_reason', 'flagged_by', 'flagged_at'])


# Updated community Comment model inheriting from home Comment model
class Comment(ModerationMixin, HomeComment):
    comment_ptr = models.OneToOneField(HomeComment, on_delete=models.CASCADE, parent_link=True, default=None)

    def approve(self, moderator):
        self.moderation_state = MODERATION_APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.save(update_fields=['moderation_state', 'moderated_by', 'moderated_at'])

    def flag(self, reason, reporter):
        self.moderation_state = MODERATION_FLAGGED
        self.flag_reason = reason
        self.flagged_by = reporter
        self.flagged_at = timezone.now()
        self.save(update_fields=['moderation_state', 'flag_reason', 'flagged_by', 'flagged_at'])


# Updated community Reply model inheriting from home Reply model
class Reply(ModerationMixin, HomeReply):
    def approve(self, moderator):
        self.moderation_state = MODERATION_APPROVED
        self.moderated_by = moderator
        self.moderated_at = timezone.now()
        self.save(update_fields=['moderation_state', 'moderated_by', 'moderated_at'])

    def flag(self, reason, reporter):
        self.moderation_state = MODERATION_FLAGGED
        self.flag_reason = reason
        self.flagged_by = reporter
        self.flagged_at = timezone.now()
        self.save(update_fields=['moderation_state', 'flag_reason', 'flagged_by', 'flagged_at'])


# Category model
class Category(MetadataMixin):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Event(MetadataMixin):
    """Community event: webinar, workshop, or meetup."""

    TYPE_WEBINAR = 'webinar'
    TYPE_WORKSHOP = 'workshop'
    TYPE_MEETUP = 'meetup'
    TYPE_CONFERENCE = 'conference'
    TYPE_CHOICES = [
        (TYPE_WEBINAR, 'Webinar'),
        (TYPE_WORKSHOP, 'Workshop'),
        (TYPE_MEETUP, 'Meetup'),
        (TYPE_CONFERENCE, 'Conference'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=250, unique=True, null=True, blank=True)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default=TYPE_MEETUP)
    image = models.ImageField(upload_to='events/', blank=True, null=True)
    starts_at = models.DateTimeField(db_index=True)
    ends_at = models.DateTimeField(null=True, blank=True)
    location = models.CharField(max_length=255, blank=True)
    is_online = models.BooleanField(default=False)
    registration_url = models.URLField(blank=True)
    is_published = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['starts_at']
        indexes = [models.Index(fields=['is_published', 'starts_at'])]

    def __str__(self):
        return self.title

    @property
    def is_upcoming(self):
        end = self.ends_at or self.starts_at
        return end >= timezone.now()

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            counter = 1
            while Event.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


# Topic model inheriting from home Tag model
class Topic(Tag):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='topics')
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='topic_images/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, blank=True, related_name='topics')
    featured = models.BooleanField(default=False)

    def __str__(self):
        return self.name


# Like model (proxy)
class Like(HomeLike):
    class Meta:
        proxy = True


# Dislike model (proxy)
class Dislike(HomeDislike):
    class Meta:
        proxy = True
