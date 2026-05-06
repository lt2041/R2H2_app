from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Return d[key], or '' if missing. Allows dynamic key lookup in templates."""
    return d.get(key, '')
