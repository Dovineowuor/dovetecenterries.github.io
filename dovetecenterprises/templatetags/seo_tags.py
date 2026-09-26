from django import template

import json

register = template.Library()


@register.filter
def abs_url(value, request=None):
    """Return an absolute URL for a possibly-relative path (media/static/paths)."""
    if not value:
        return ''
    value = str(value).strip()
    if value.startswith(('http://', 'https://', '//')):
        return value
    if request is not None:
        try:
            return request.build_absolute_uri(value)
        except Exception:
            return value
    return value


@register.filter
def to_json(value):
    """Serialize a value to a JSON string for JSON-LD blocks."""
    try:
        return json.dumps(value, default=str)
    except Exception:
        return ''


@register.filter
def split(value, arg=','):
    """Split a string into a list using the given separator."""
    if value is None:
        return []
    if arg is None:
        arg = ','
    return str(value).split(str(arg))


@register.filter
def schema_json(value, request=None):
    """Build schema.org JSON-LD for an Article (or dict), with absolute URLs."""
    try:
        if hasattr(value, 'get_schema_org_json_ld'):
            data = value.get_schema_org_json_ld()
        elif isinstance(value, dict):
            data = value
        else:
            return ''
        if request is not None:
            for key in ('image', 'mainEntityOfPage'):
                if data.get(key):
                    data[key] = abs_url(data[key], request)
        return json.dumps(data, default=str)
    except Exception:
        return ''
