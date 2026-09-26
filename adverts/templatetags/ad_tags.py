from django import template
from adverts.models import Advertisement
import random

register = template.Library()

@register.inclusion_tag('adverts/ad_slot.html')
def render_ad(count=1):
    ads = list(Advertisement.objects.all())
    if ads:
        # Get random ads based on count
        selected_ads = random.sample(ads, min(len(ads), count))
        return {'ads': selected_ads}
    return {'ads': None}
