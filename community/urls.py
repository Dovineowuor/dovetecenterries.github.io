from django.urls import path
from .views import (
    topic_list, topic_detail, post_detail, toggle_like, toggle_dislike,
    add_comment, add_reply, trending, product_updates, get_inspired,
    events, directory,
)

urlpatterns = [
    path('', topic_list, name='community'),
    path('trending/', trending, name='community_trending'),
    path('product-updates/', product_updates, name='community_product_updates'),
    path('get-inspired/', get_inspired, name='community_get_inspired'),
    path('events/', events, name='community_events'),
    path('directory/', directory, name='community_directory'),
    path('topic/<slug:topic_slug>/', topic_detail, name='topic_detail'),
    path('post/<slug:post_slug>/', post_detail, name='post_detail'),
    path('post/<slug:post_slug>/like/', toggle_like, name='toggle_like'),
    path('post/<slug:post_slug>/dislike/', toggle_dislike, name='toggle_dislike'),
    path('comment/<slug:post_slug>/', add_comment, name='add_comment'),
    path('reply/', add_reply, name='add_reply'),
]
