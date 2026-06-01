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


@register.filter
def fmt_float(value):
    """Format a number for display in form inputs.
    Uses Python ':,g' which:
    - applies thousand-comma separators for numbers in normal range (e.g. 96,485)
    - auto-switches to scientific notation for very small/large values (e.g. 4.14e-10)
    - strips trailing zeros (e.g. 15.0 → 15, 0.50 → 0.5)
    Non-numeric values are returned unchanged; None returns ''."""
    if value is None:
        return ''
    try:
        f = float(value)
        return f'{f:,g}'
    except (TypeError, ValueError):
        return value
