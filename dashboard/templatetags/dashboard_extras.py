from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Look up a dict value by key, returning '' when missing."""
    if dictionary is None:
        return ''
    return dictionary.get(key, '') or ''


@register.filter
def verbose_name(obj):
    """Return a human-readable model verbose name (templates can't access _meta)."""
    try:
        return obj._meta.verbose_name.title()
    except Exception:
        return 'item'
