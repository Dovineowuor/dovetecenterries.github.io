# adverts/urls.py

from django.urls import path
from .views import advertise_view

urlpatterns = [
    path('', advertise_view, name='advertise'),
]
