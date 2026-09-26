from django.contrib import admin
from .models import Advertisement, AdvertLeads

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):
    list_display = ('title', 'url', 'created_at')
    search_fields = ('title', 'description')

@admin.register(AdvertLeads)
class AdvertLeadsAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'interest', 'created_at')
    search_fields = ('name', 'email', 'company')
