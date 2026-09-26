from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Article, DiscussionTopic, Job, Newsletter, NewsletterSubscription, Notification, Profile, Reply, Report, Tag, Comment, User, JobApplication, Department, Interview, ApplicationNote, SourceTracker

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

@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ('subject', 'status', 'created_at', 'sent_at')
    search_fields = ('subject', 'content')
    list_filter = ('status', 'created_at')
    list_per_page = 20
    fieldsets = (
        (None, {'fields': ('subject', 'content', 'recipients', 'manual_recipients')}),
        ('Scheduling & Tracking', {'fields': ('scheduled_for', 'tracking_enabled')}),
        ('System Info', {'fields': ('status', 'sent_at', 'slug'), 'classes': ('collapse',)}),
    )
    readonly_fields = ('sent_at', 'slug')

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
