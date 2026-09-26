from django.urls import path
from . import views

urlpatterns = [
        # Role-aware router — redirects to admin or client dashboard
    path('', views.dashboard_router, name='dashboard'),

    # ── Admin Dashboard ───────────────────────────────────────────
    path('admin/', views.dashboard_index, name='admin_dashboard'),
    path('crm/clients/', views.dashboard_clients, name='dashboard_clients'),
    path('crm/inquiries/', views.dashboard_inquiries, name='dashboard_inquiries'),
    path('crm/projects/', views.dashboard_projects, name='dashboard_projects'),

    # ── Sales Funnel (Lead → Close) ───────────────────────────────
    path('crm/funnel/', views.dashboard_funnel, name='dashboard_funnel'),
    path('crm/funnel/<int:inquiry_id>/', views.funnel_inquiry_detail, name='funnel_inquiry_detail'),
    path('crm/funnel/<int:inquiry_id>/stage/', views.funnel_update_stage, name='funnel_update_stage'),
    path('crm/funnel/<int:inquiry_id>/details/', views.funnel_update_lead, name='funnel_update_lead'),
    path('crm/funnel/<int:inquiry_id>/questionnaire/', views.funnel_questionnaire, name='funnel_questionnaire'),

    # ── Support tickets (issues first, then escalate) ─────────────
    path('crm/tickets/', views.ticket_queue, name='ticket_queue'),
    path('crm/tickets/<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),

    # ── Notifications ─────────────────────────────────────────────
    path('notifications/', views.notification_list, name='notification_list'),

    # ── Questionnaire templates (library CRUD) ────────────────────
    path('crm/templates/', views.template_list, name='template_list'),
    path('crm/templates/<int:template_id>/', views.template_detail, name='template_detail'),

    # ── Questionnaire Management (full CRUD + responses) ──────────
    path('crm/questionnaires/', views.questionnaire_list, name='questionnaire_list'),
    path('crm/questionnaires/<int:questionnaire_id>/responses/', views.questionnaire_responses, name='questionnaire_responses'),
    path('cms/forums/', views.dashboard_forums, name='dashboard_forums'),
    path('cms/products/', views.dashboard_products, name='dashboard_products'),
    path('cms/articles/', views.dashboard_articles, name='dashboard_articles'),
    path('cms/articles/<int:pk>/publish/', views.dashboard_publish_article, name='dashboard_publish_article'),
    path('cms/adverts/', views.dashboard_adverts, name='dashboard_adverts'),
    path('marketing/newsletters/', views.dashboard_newsletters, name='dashboard_newsletters'),
    path('cms/engagements/', views.dashboard_engagements, name='cms_engagements'),
    path('cms/features/', views.dashboard_features, name='dashboard_features'),
    path('media/', views.dashboard_media, name='dashboard_media'),

    # ── Client Portal ─────────────────────────────────────────────
    path('client/', views.client_dashboard, name='client_dashboard'),
    path('client/orders/', views.client_orders, name='client_orders'),
    path('client/orders/<int:order_id>/', views.client_order_detail, name='client_order_detail'),
    path('client/articles/', views.client_articles, name='client_articles'),
    path('client/profile/', views.client_profile_view, name='client_profile'),
    path('client/questionnaires/', views.client_questionnaires, name='client_questionnaires'),
    path('client/questionnaires/<int:questionnaire_id>/', views.client_questionnaire_fill, name='client_questionnaire_fill'),
    path('client/tickets/', views.client_tickets, name='client_tickets'),
    path('client/tickets/<int:ticket_id>/', views.client_ticket_detail, name='client_ticket_detail'),
    path('client/billing/', views.client_billing, name='client_billing'),
    path('client/billing/choose/<slug:plan_slug>/', views.client_subscription_choose, name='client_subscription_choose'),
    path('client/billing/cancel/', views.client_subscription_cancel, name='client_subscription_cancel'),

    # Generic Custom Admin CRUD
    path('manage/<str:app_label>/<str:model_name>/add/', views.DashboardCreateView.as_view(), name='dashboard_add'),
    path('manage/<str:app_label>/<str:model_name>/<int:pk>/edit/', views.DashboardUpdateView.as_view(), name='dashboard_edit'),
    path('manage/<str:app_label>/<str:model_name>/<int:pk>/delete/', views.DashboardDeleteView.as_view(), name='dashboard_delete'),
]
