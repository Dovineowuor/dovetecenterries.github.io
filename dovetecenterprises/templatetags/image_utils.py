from django import template
from django.template.defaultfilters import stringfilter
import os

register = template.Library()

@register.filter
@stringfilter
def to_webp(path):
    """Convert an image path to WebP format"""
    if path:
        base, ext = os.path.splitext(path)
        if ext.lower() in ['.jpg', '.jpeg', '.png']:
            return f"{base}.webp"
    return path

@register.filter
def srcset(path, sizes="300,600,900,1200"):
    """Generate a srcset string for responsive images"""
    if not path:
        return ""
        
    base, ext = os.path.splitext(path)
    if ext.lower() not in ['.jpg', '.jpeg', '.png']:
        return ""
        
    srcset_parts = []
    for size in sizes.split(','):
        size = size.strip()
        srcset_parts.append(f"{base}-{size}w.webp {size}w")
    
    return ", ".join(srcset_parts)
