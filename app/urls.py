import os
from re import DEBUG
from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

# create url patterns for the main app
urlpatterns = [
    path('', views.index, name='home'),
    path('about/', views.about, name='about_us'),
    path('contact/', views.contact, name='contact_us'),
    path('services/', views.services, name='services'),
    path('portfolio/', views.portfolio, name='portfolio'),
    path('portfolio-showcase/', views.portfolio_showcase, name='portfolio_showcase'),
    path('portfolio-masonry/', views.portfolio_massionry, name='portfolio_masonry'),
    path('case-study/', views.case_study, name='case_studies'),
    path('case-study/<str:slug>/', views.case_study_detail, name='case_study_detail'),
    path('join-our-team/', views.join_our_team, name='join_our_team'),
    path('product-demo/', views.product_demo, name='request_product_demo'),
    path('gallery/', views.gallery, name='gallery'),
    path('products/', views.products, name='products'),
    path('careers/', views.careers, name='careers'),
    path('features/', views.feature_board, name='feature_board'),
    path('features/new/', views.feature_create, name='feature_create'),
    path('features/<slug:slug>/', views.feature_detail, name='feature_detail'),
    path('features/<slug:slug>/vote/', views.feature_vote, name='feature_vote'),
]
if DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
