from django import template

register = template.Library()


@register.filter
def dict_get(d, key):
    """Return d[key], or '' if missing. Allows dynamic key lookup in templates."""
    return d.get(key, '')


@register.filter
def split_csv(value):
    """Split a comma-separated string into a list of stripped tokens."""
    if not value:
        return []
    return [v.strip() for v in value.split(',') if v.strip()]


@register.filter
def zip(a, b):
    """Zip two iterables together for parallel iteration in templates."""
    import builtins
    return builtins.zip(a, b)
