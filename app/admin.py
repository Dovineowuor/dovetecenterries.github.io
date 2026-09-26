from django.contrib import admin
from .models import (
    Answer, Contact, FeatureRequest, FeatureTask, FeatureVote, FeatureMicrotask, MediaAsset, Organization,
    Plan, Project, Question, Questionnaire, QuestionnaireEvent,
    QuestionnaireTemplate, ServiceInquiry, Subscription, Ticket, TicketActivity, User,
)

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'created_at')
    search_fields = ('username', 'email', 'first_name', 'last_name')

@admin.register(ServiceInquiry)
class ServiceInquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'service', 'stage', 'estimated_value', 'assigned_to', 'created_at')
    list_filter = ('service', 'source', 'stage', 'created_at')
    search_fields = ('name', 'email', 'message')
    readonly_fields = ('created_at', 'stage_updated_at', 'converted_at')
    list_editable = ('stage',)


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'industry', 'website', 'phone', 'created_at')
    search_fields = ('name', 'industry', 'website')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('display_name', 'email', 'organization', 'phone', 'preferred_contact_method')
    list_filter = ('preferred_contact_method', 'organization')
    search_fields = ('first_name', 'last_name', 'email', 'organization__name')


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    fk_name = 'questionnaire'


class TemplateQuestionInline(admin.TabularInline):
    model = Question
    extra = 1
    fk_name = 'template'


@admin.register(Questionnaire)
class QuestionnaireAdmin(admin.ModelAdmin):
    list_display = ('title', 'inquiry', 'status', 'question_count', 'progress_percent', 'created_at', 'completed_at')
    list_filter = ('status', 'created_at')
    search_fields = ('title', 'inquiry__name', 'inquiry__email')
    inlines = [QuestionInline]


@admin.register(QuestionnaireEvent)
class QuestionnaireEventAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'questionnaire', 'action', 'actor', 'question')
    list_filter = ('action', 'created_at')
    search_fields = ('content', 'answer_snapshot', 'questionnaire__title', 'questionnaire__inquiry__email')
    readonly_fields = ('questionnaire', 'question', 'actor', 'action', 'content', 'answer_snapshot', 'created_at')


@admin.register(QuestionnaireTemplate)
class QuestionnaireTemplateAdmin(admin.ModelAdmin):
    list_display = ('title', 'context', 'industry', 'is_active', 'question_count', 'updated_at')
    list_filter = ('context', 'is_active', 'industry')
    search_fields = ('title', 'intro', 'industry')
    inlines = [TemplateQuestionInline]


class TicketActivityInline(admin.TabularInline):
    model = TicketActivity
    extra = 0
    readonly_fields = ('action', 'user', 'from_user', 'to_user', 'content', 'created_at')
    can_delete = False


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = ('reference', 'subject', 'type', 'priority', 'status', 'assigned_to', 'referred_to', 'created_at')
    list_filter = ('type', 'status', 'priority', 'created_at')
    search_fields = ('reference', 'subject', 'description', 'contact__email', 'contact__first_name')
    readonly_fields = ('reference', 'created_at', 'updated_at', 'resolved_at', 'escalated_at')
    list_editable = ('priority', 'status', 'assigned_to')
    inlines = [TicketActivityInline]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'priority', 'organization', 'converted_from_inquiry', 'created_at')
    list_filter = ('status', 'priority', 'created_at')
    search_fields = ('name', 'description', 'organization__name')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'answer', 'updated_at')
    search_fields = ('question__text', 'answer')


@admin.register(MediaAsset)
class MediaAssetAdmin(admin.ModelAdmin):
    list_display = ('original_name', 'kind', 'status', 'size_bytes', 'owner', 'created_at')
    list_filter = ('kind', 'status', 'is_public', 'created_at')
    search_fields = ('original_name', 'alt_text', 'failure_reason')
    readonly_fields = ('original_name', 'mime_type', 'size_bytes', 'failure_reason', 'created_at', 'updated_at')


@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'price', 'currency', 'interval', 'is_active', 'is_default', 'sort_order')
    list_filter = ('interval', 'is_active', 'is_default')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'starts_at', 'ends_at', 'cancel_at_period_end', 'created_at')
    list_filter = ('status', 'plan', 'cancel_at_period_end')
    search_fields = ('user__email', 'plan__name', 'payment_reference')
    readonly_fields = ('created_at', 'updated_at')


class FeatureTaskInline(admin.TabularInline):
    model = FeatureTask
    extra = 0
    readonly_fields = ('assignee', 'due_date', 'completed_at', 'created_at', 'updated_at')
    can_delete = True


class FeatureMicrotaskInline(admin.TabularInline):
    model = FeatureMicrotask
    extra = 0
    readonly_fields = ('assignee', 'created_at', 'updated_at')
    can_delete = True


class FeatureVoteInline(admin.TabularInline):
    model = FeatureVote
    extra = 0
    readonly_fields = ('user', 'created_at')
    can_delete = True


@admin.register(FeatureRequest)
class FeatureRequestAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'category', 'vote_count', 'author', 'created_at')
    list_filter = ('status', 'category', 'created_at')
    search_fields = ('title', 'description', 'staff_notes')
    prepopulated_fields = {'slug': ('title',)}
    inlines = [FeatureVoteInline, FeatureTaskInline]
    readonly_fields = ('vote_count', 'created_at', 'updated_at')


@admin.register(FeatureTask)
class FeatureTaskAdmin(admin.ModelAdmin):
    list_display = ('feature_request', 'title', 'priority', 'status', 'assignee', 'due_date', 'created_at')
    list_filter = ('status', 'priority', 'feature_request')
    search_fields = ('title', 'description')
    raw_id_fields = ('assignee',)
    inlines = [FeatureMicrotaskInline]


@admin.register(FeatureMicrotask)
class FeatureMicrotaskAdmin(admin.ModelAdmin):
    list_display = ('task', 'title', 'status', 'assignee', 'created_at')
    list_filter = ('status', 'task')
    search_fields = ('title',)
    raw_id_fields = ('assignee',)
