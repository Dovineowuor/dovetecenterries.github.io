from django.db import models
from home.models import MetadataMixin

class Advertisement(MetadataMixin):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    main_image = models.ImageField(upload_to='ads/main/', verbose_name='Main Image')
    image_2 = models.ImageField(upload_to='ads/optional/', blank=True, null=True, verbose_name='Optional Image 2')
    image_3 = models.ImageField(upload_to='ads/optional/', blank=True, null=True, verbose_name='Optional Image 3')
    url = models.URLField(max_length=255, verbose_name='Link to Ad', help_text='URL where the ad redirects to when clicked')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = 'Advertisement'
        verbose_name_plural = 'Advertisements'

class AdvertLeads(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    company = models.CharField(max_length=100, blank=True, null=True)
    interest = models.CharField(max_length=100, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = 'Advert Lead'
        verbose_name_plural = 'Advert Leads'