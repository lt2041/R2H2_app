# Django specific libraries
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.apps import apps

# Django REST framework
# ...

# Std libraries
import re
from django.utils.html import escape

# Django models
from .models import *

# Local src libraries
# ...



def home(request):

    # Get counts for each model
    Battery_count = Battery.objects.count()
    ElectroCellPEM_count = ElectroCellPEM.objects.count()
    ElectrolyserUnit_count = ElectrolyserUnit.objects.count()
    ThermalProperties_count = ThermalProperties.objects.count()
    TimeOutput_count = TimeOutput.objects.count()
    WindInput_count = WindInput.objects.count()

    # Pass data to HTML template
    context = {
        'Battery_count': Battery_count,
        'ElectroCellPEM_count': ElectroCellPEM_count,
        'ElectrolyserUnit_count': ElectrolyserUnit_count,
        'ThermalProperties_count': ThermalProperties_count,
        'TimeOutput_count': TimeOutput_count,
        'WindInput_count': WindInput_count,
    }

    return render(request, 'dashboard/home.html', context)



### -------------------------------- Browse -------------------------------- ###


def format_cell_value(value):
    if value is None or value == '':
        return '—'
    s = str(value)
    m = re.match(r'^([\[\(])(.*)([\]\)])$', s, re.DOTALL)
    if m:
        bracket_open, inner, bracket_close = m.group(1), m.group(2), m.group(3)
        parts = [p.strip() for p in inner.split(',')]
        if len(parts) >= 3:
            def fmt(p):
                try:
                    return f"{float(p):.6g}"
                except ValueError:
                    return p
            full_array = re.escape(s)
            count = len(parts)
            preview = f"{bracket_open}{fmt(parts[0])}, ..., {fmt(parts[-1])}{bracket_close}"
            return mark_safe(
                f'{preview}<br>'
                f'<span class="array-badge" data-tooltip="{full_array}" '
                f'style="white-space:nowrap;cursor:help;background:#e0e0e0;'
                f'border-radius:999px;padding:1px 8px;font-size:0.75em;">'
                f'array [{count}]</span>'
            )
    return s


def browse(request, table_name=None):

    model_class = apps.get_model('dashboard', table_name)

    # Use ui_column_names from MetaInfo if available, else fall back to all model fields
    metainfo = getattr(model_class, 'MetaInfo', None)
    ui_column_names = getattr(metainfo, 'ui_column_names', None)
    ui_nice_name = getattr(metainfo, 'ui_nice_name', table_name.replace('_', ' '))

    if ui_column_names:
        columns = list(ui_column_names.keys())    # field names for data lookup
        headers = list(ui_column_names.values())  # display labels for table headers
    else:
        columns = [field.name for field in model_class._meta.fields]
        headers = columns  # fall back: use field name as header

    # Identify which of the requested columns are FK fields, so we can
    # select_related them and resolve their display value via str() rather
    # than showing a raw integer ID.
    fk_fields = {
        f.name
        for f in model_class._meta.get_fields()
        if hasattr(f, 'many_to_one') and f.many_to_one and f.name in columns
    }

    qs = model_class.objects.order_by('-id')
    if fk_fields:
        qs = qs.select_related(*fk_fields)

    rows = []
    for obj in qs:
        row = {}
        for col in columns:
            val = getattr(obj, col, '')
            if col in fk_fields:
                related = val
                row[col] = str(related) if related is not None else '—'
            else:
                row[col] = format_cell_value(val)
        rows.append(row)

    context = {
        'columns': columns,
        'headers': headers,
        'rows': rows,
        'total_count': model_class.objects.count(),
        'ui_nice_name': ui_nice_name,
    }

    return render(request, "dashboard/browse.html", context)
