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
def parse_h5_datasets(value):
    """Parse h5_datasets string into a list of dicts with path, shape, dtype.

    Entries are separated by '|'.  Each entry has the form '/Name [d, d] dtype'.
    Returns [{'path': '/Name', 'shape': 'd × d', 'dtype': 'dtype'}, ...]
    """
    import re
    if not value:
        return []
    result = []
    for entry in value.split('|'):
        entry = entry.strip()
        if not entry:
            continue
        m = re.match(r'^(\S+)\s+\[([^\]]*)\]\s+(\S+)$', entry)
        if m:
            path, shape_raw, dtype = m.group(1), m.group(2), m.group(3)
            dims = [d.strip() for d in shape_raw.split(',') if d.strip()]
            shape = ' \u00d7 '.join(dims)
        else:
            path, shape, dtype = entry, '', ''
        result.append({'path': path, 'shape': shape, 'dtype': dtype})
    return result


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
