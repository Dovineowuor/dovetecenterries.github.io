from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.html import format_html
from .models import (
    ApplicationNote, Article, Comment, Department, DiscussionTopic, Interview, Job,
    JobApplication, Newsletter, NewsletterAttachment, NewsletterContentReference,
    NewsletterLog, NewsletterSubscription, Notification, Profile, Reply, Report,
    SourceTracker, Tag, User,
)

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'password1', 'password2'),
        }),
    )
    search_fields = ('email', 'first_name', 'last_name', 'username')
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions')

# Register the custom User model and UserAdmin
admin.site.register(User, UserAdmin)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', 'recipient', 'verb', 'email_sent', 'read_at', 'created_at')
    list_filter = ('verb', 'email_sent', 'created_at')
    search_fields = ('title', 'body', 'recipient__email')
    readonly_fields = ('recipient', 'actor', 'verb', 'title', 'body', 'link', 'email_sent', 'read_at', 'created_at')


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ('title', 'author', 'status', 'scheduled_at', 'featured', 'created_at')
    list_filter = ('status', 'featured', 'created_at')
    search_fields = ('title', 'content')
    fieldsets = (
        (None, {'fields': ('title', 'content', 'author', 'image')}),
        ('Publication', {'fields': ('status', 'scheduled_at', 'featured', 'category', 'tags')}),
        ('SEO', {'fields': ('seo_description', 'slug', 'meta_title', 'meta_description', 'canonical_url', 'og_title', 'og_description', 'og_image', 'twitter_card', 'twitter_title', 'twitter_description', 'twitter_image', 'published_at'), 'classes': ('collapse',)}),
        ('Resource', {'fields': ('is_resource', 'resource_type', 'resource_file', 'resource_url')}),
        ('Discussion', {'fields': ('is_discussion', 'discussion_topic')}),
    )
    readonly_fields = ('slug',)


# Admin configuration for the Profile model
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Profile._meta.fields]

# Admin configuration for the Tag model
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Tag._meta.fields]

# Admin configuration for the Comment model
@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Comment._meta.fields]

# Admin configuration for the Reply model
@admin.register(Reply)
class ReplyAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Reply._meta.fields]

class NewsletterContentReferenceInline(GenericTabularInline):
    model = NewsletterContentReference
    extra = 1
    ct_field = 'content_type'
    ct_fk_field = 'object_id'
    fields = ('kind', 'content_type', 'object_id', 'order')


class NewsletterAttachmentInline(admin.TabularInline):
    model = NewsletterAttachment
    extra = 1
    fields = ('name', 'file', 'content_type', 'description', 'order', 'size')
    readonly_fields = ('size',)


class NewsletterLogInline(admin.TabularInline):
    model = NewsletterLog
    extra = 0
    can_delete = False
    max_num = 200
    fields = ('email', 'status', 'sent_at', 'opened', 'opened_at', 'clicked', 'clicked_at', 'read', 'read_at', 'error')
    readonly_fields = fields
    ordering = ('-created_at',)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(NewsletterAttachment)
class NewsletterAttachmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'newsletter', 'content_type', 'size', 'order')
    list_filter = ('content_type',)
    search_fields = ('name', 'description', 'newsletter__subject')
    raw_id_fields = ('newsletter',)


@admin.register(NewsletterContentReference)
class NewsletterContentReferenceAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'newsletter', 'kind', 'order')
    list_filter = ('kind',)
    search_fields = ('newsletter__subject',)
    raw_id_fields = ('newsletter',)


@admin.register(NewsletterLog)
class NewsletterLogAdmin(admin.ModelAdmin):
    list_display = ('email', 'newsletter', 'status', 'sent_at', 'opened', 'clicked', 'read', 'bounced', 'engagement_score')
    list_filter = ('status', 'opened', 'clicked', 'read', 'bounced', 'unsubscribed', 'newsletter')
    search_fields = ('email', 'newsletter__subject')
    readonly_fields = ('tracking_id', 'sent_at', 'opened_at', 'clicked_at', 'read_at', 'created_at', 'updated_at')
    raw_id_fields = ('newsletter', 'user')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(description='Engagement')
    def engagement_score(self, obj):
        return obj.engagement_score


@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'status', 'recipient_count', 'open_rate', 'click_rate', 'created_at', 'sent_at')
    search_fields = ('subject', 'content', 'preheader', 'subtitle')
    list_filter = ('status', 'created_at', 'click_tracking_enabled', 'tracking_pixel_enabled')
    list_editable = ()
    date_hierarchy = 'created_at'
    list_per_page = 20
    readonly_fields = ('sent_at', 'slug', 'status', 'resend_count', 'kpi_summary')
    actions = ('send_now', 'resend_to_undelivered', 'retry_failed_only')
    inlines = (NewsletterContentReferenceInline, NewsletterAttachmentInline, NewsletterLogInline)
    fieldsets = (
        (None, {'fields': ('subject', 'preheader', 'subtitle', 'content')}),
        ('Campaign Content', {'fields': ('content_type', 'content_id', 'adverts', 'advertisement', 'allow_attachments')}),
        ('Call to Action', {'fields': ('cta_title', 'cta_text', 'cta_label', 'cta_url', 'accent_color')}),
        ('Audience', {'fields': ('recipients', 'manual_recipients')}),
        ('Delivery & Tracking', {'fields': ('scheduled_for', 'tracking_enabled', 'tracking_pixel_enabled', 'click_tracking_enabled')}),
        ('Performance', {'fields': ('kpi_summary',), 'classes': ('collapse',)}),
        ('System Info', {'fields': ('status', 'sent_at', 'resend_count', 'slug'), 'classes': ('collapse',)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related('logs')

    @admin.display(description='Recipients')
    def recipient_count(self, obj):
        return len(obj.get_all_recipient_emails())

    @admin.display(description='Open rate')
    def open_rate(self, obj):
        if not obj.pk:
            return '-'
        return f"{obj.get_kpi_summary()['open_rate']}%"

    @admin.display(description='Click rate')
    def click_rate(self, obj):
        if not obj.pk:
            return '-'
        return f"{obj.get_kpi_summary()['click_rate']}%"

    @admin.display(description='KPIs')
    def kpi_summary(self, obj):
        if not obj.pk:
            return '-'
        k = obj.get_kpi_summary()
        return format_html(
            '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(90px,1fr));'
            'gap:10px;font-size:13px">'
            '<div><strong>{}</strong><br>Delivered</div>'
            '<div><strong>{}%</strong><br>Opened</div>'
            '<div><strong>{}%</strong><br>Clicked</div>'
            '<div><strong>{}%</strong><br>Read / signed in</div>'
            '<div><strong>{}</strong><br>Bounced</div>'
            '<div><strong>{}</strong><br>Unsubscribed</div>'
            '<div><strong>{}</strong><br>Failed</div>'
            '<div><strong>{}</strong><br>Resends</div>'
            '</div>',
            k['sent'], k['open_rate'], k['click_rate'], k['read_rate'],
            k['bounced'], k['unsubscribed'], k['failed'], obj.resend_count or 0,
        )

    @admin.action(description='Send newsletter now')
    def send_now(self, request, queryset):
        sent = failed = 0
        for newsletter in queryset:
            try:
                if newsletter.send_newsletter():
                    sent += 1
                else:
                    failed += 1
            except Exception as exc:
                failed += 1
                self.message_user(request, f"{newsletter.subject}: {exc}", level='error')
        self.message_user(request, f"Sent {sent}, skipped/failed {failed}.", level='warning' if failed else 'success')

    @admin.action(description='Resend to undelivered recipients')
    def resend_to_undelivered(self, request, queryset):
        for newsletter in queryset:
            newsletter.resend_newsletter(only_failed=True)
        self.message_user(request, f"Resent {queryset.count()} newsletter(s) to undelivered recipients.", level='success')

    @admin.action(description='Retry failed deliveries only')
    def retry_failed_only(self, request, queryset):
        for newsletter in queryset:
            newsletter.send_newsletter(resend=True, only_failed=True)
        self.message_user(request, f"Retried failed deliveries for {queryset.count()} newsletter(s).", level='success')

@admin.register(NewsletterSubscription)
class NewsletterSubscriptionAdmin(admin.ModelAdmin):
    list_display = [field.name for field in NewsletterSubscription._meta.fields]
    search_fields = ('email',)
    ordering = ('email',)
    list_per_page = 20
    fieldsets = (
        (None, {'fields': ('email', 'user')}),
    )

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = [field.name for field in Job._meta.fields]
    search_fields = ('title',)
    list_filter = ('is_active',)
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'
    list_per_page = 20
    fieldsets = (
        (None, {'fields': ('title', 'description', 'location', 'company')}),
        ('Permissions', {'fields': ('is_active',)}),
    )
    readonly_fields = ('created_at',)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.company = request.user
        if obj.image:
            obj.image = obj.image.url
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        if obj:
            return ['title', 'description', 'location', 'company']
        return super().get_readonly_fields(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['title'].widget.attrs['readonly'] = True
        return form
    
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('article', 'user', 'created_at')
    search_fields = ('reason', 'article__title', 'user__email')
    ordering = ('-created_at',)
    list_per_page = 20
    fieldsets = (
        (None, {'fields': ('article', 'user', 'reason')}),
        ('System', {'fields': ('created_at',), 'classes': ('collapse',)}),
    )
    readonly_fields = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('article', 'user')


@admin.register(JobApplication)
class JobApplicationAdmin(admin.ModelAdmin):
    list_display = ('candidate_name', 'candidate_email', 'job', 'status', 'source', 'priority', 'rating', 'applied_at')
    list_filter = ('status', 'source', 'priority', 'applied_at')
    search_fields = ('candidate_name', 'candidate_email', 'job__title', 'department__name')
    readonly_fields = ('applied_at', 'updated_at', 'status_changed_at')
    list_editable = ('status', 'priority', 'rating')


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ('application', 'interview_stage', 'interview_type', 'scheduled_at', 'interviewer', 'outcome')
    list_filter = ('interview_stage', 'interview_type', 'outcome', 'created_at')
    search_fields = ('application__candidate_name', 'location')
    list_editable = ('outcome',)


@admin.register(ApplicationNote)
class ApplicationNoteAdmin(admin.ModelAdmin):
    list_display = ('application', 'action', 'user', 'created_at')
    list_filter = ('action', 'created_at')
    search_fields = ('content', 'application__candidate_name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(SourceTracker)
class SourceTrackerAdmin(admin.ModelAdmin):
    list_display = ('source_name', 'source_type', 'applications_count', 'hired_count', 'conversion_rate')
    list_filter = ('source_type',)
    search_fields = ('source_name',)
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'location', 'headcount', 'manager', 'created_at')
    search_fields = ('name', 'location')
    list_editable = ('headcount',)


# Admin configuration for the DiscussionTopic model
@admin.register(DiscussionTopic)
class DiscussionTopicAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'author', 'is_pinned', 'vote_count', 'created_at')
    list_filter = ('status', 'is_pinned', 'created_at')
    search_fields = ('title', 'description')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at')
