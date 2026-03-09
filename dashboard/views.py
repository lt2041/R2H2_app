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



def simulations(request):
    """Hierarchical view of Simulation models with M2M component relations."""
    sims = Simulation.objects.prefetch_related(
        'batteries',
        'electro_cells',
        'electrolyser_units',
        'thermal_properties',
        'time_outputs',
        'wind_inputs',
    ).order_by('-id')

    sim_data = []
    for sim in sims:
        sim_data.append({
            'obj': sim,
            'components': [
                {
                    'label': 'Battery',
                    'icon': 'battery_charging_full',
                    'table': 'Battery',
                    'items': list(sim.batteries.all()),
                },
                {
                    'label': 'ElectroCellPEM',
                    'icon': 'developer_board',
                    'table': 'ElectroCellPEM',
                    'items': list(sim.electro_cells.all()),
                },
                {
                    'label': 'ElectrolyserUnit',
                    'icon': 'water_do',
                    'table': 'ElectrolyserUnit',
                    'items': list(sim.electrolyser_units.all()),
                },
                {
                    'label': 'ThermalProperties',
                    'icon': 'thermostat',
                    'table': 'ThermalProperties',
                    'items': list(sim.thermal_properties.all()),
                },
                {
                    'label': 'TimeOutput',
                    'icon': 'timeline',
                    'table': 'TimeOutput',
                    'items': list(sim.time_outputs.all()),
                },
                {
                    'label': 'WindInput',
                    'icon': 'air',
                    'table': 'WindInput',
                    'items': list(sim.wind_inputs.all()),
                },
            ],
        })

    return render(request, 'dashboard/simulations.html', {'sim_data': sim_data})


def _model_to_sections(obj):
    """Convert a model instance into ordered display sections.
    Returns a list of {title, icon, fields: [{name, value}]}.
    Skips JSON array fields (shown separately) and private fields.
    """
    scalar_fields, array_fields = [], []
    for field in obj._meta.get_fields():
        if not hasattr(field, 'column'):          # skip reverse relations
            continue
        name = field.name
        if name in ('id',):
            continue
        value = getattr(obj, name, None)
        if isinstance(value, list):               # JSON array
            array_fields.append({'name': name, 'value': value})
        else:
            scalar_fields.append({'name': name, 'value': value})
    return scalar_fields, array_fields


def simulation_detail(request, sim_id):
    """Detail view for a single Simulation showing all component settings."""
    from django.shortcuts import get_object_or_404
    sim = get_object_or_404(
        Simulation.objects.prefetch_related(
            'batteries', 'electro_cells', 'electrolyser_units',
            'thermal_properties', 'time_outputs', 'wind_inputs',
        ),
        pk=sim_id
    )

    def component_detail(obj):
        scalar, arrays = _model_to_sections(obj)
        return {'obj': obj, 'scalar': scalar, 'arrays': arrays}

    groups = [
        {'label': 'Battery',           'icon': 'battery_charging_full', 'items': [component_detail(o) for o in sim.batteries.all()]},
        {'label': 'ElectroCellPEM',    'icon': 'developer_board',       'items': [component_detail(o) for o in sim.electro_cells.all()]},
        {'label': 'ElectrolyserUnit',  'icon': 'water_do',               'items': [component_detail(o) for o in sim.electrolyser_units.all()]},
        {'label': 'ThermalProperties', 'icon': 'thermostat',             'items': [component_detail(o) for o in sim.thermal_properties.all()]},
        {'label': 'TimeOutput',        'icon': 'timeline',               'items': [component_detail(o) for o in sim.time_outputs.all()]},
        {'label': 'WindInput',         'icon': 'air',                    'items': [component_detail(o) for o in sim.wind_inputs.all()]},
    ]

    groups_with_items = [g for g in groups if g['items']]
    groups_empty = [g for g in groups if not g['items']]

    wind_type_label = dict(Simulation._meta.get_field('iWindType').choices).get(sim.iWindType, sim.iWindType)

    sim_settings = [
        {'name': 'Wind data resolution', 'value': wind_type_label,         'unit': ''},
        {'name': 'Number of years',      'value': sim.iNumYears,            'unit': 'yr'},
        {'name': 'Total time',           'value': sim.rTotalTime,           'unit': 's'},
        {'name': 'Time step',            'value': sim.rTimeStep,            'unit': 's'},
        {'name': 'Transient steps',      'value': sim.rTransientSteps,      'unit': ''},
        {'name': 'Single turbine',       'value': sim.bSingleTurb,          'unit': ''},
        {'name': 'Lateral distances',    'value': sim.arLateralDistances,   'unit': 'm'},
        {'name': 'Power divisor',        'value': sim.rDivisor,             'unit': 'W'},
    ]

    return render(request, 'dashboard/simulation_detail.html', {
        'sim': sim,
        'sim_settings': sim_settings,
        'groups': groups_with_items,
        'groups_empty': groups_empty,
    })


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


# Field types that are skipped in the add-new modal (output/array/auto fields)
_SKIP_FIELD_TYPES = ()
_SKIP_JSON = True   # hide JSONField arrays from the modal


def _modal_fields_for(model_class):
    """Return a list of form-field dicts for the Add New modal."""
    from django.db import models as dm
    skip_names = {'id'}
    fields = []
    for f in model_class._meta.get_fields():
        if not hasattr(f, 'column'):
            continue
        if f.name in skip_names:
            continue
        # Skip auto-set fields
        if getattr(f, 'auto_now_add', False) or getattr(f, 'auto_now', False):
            continue
        # Skip JSONField arrays (null default = output/runtime data)
        if isinstance(f, dm.JSONField):
            continue
        # Determine input type
        if isinstance(f, dm.BooleanField):
            ftype = 'checkbox'
        elif isinstance(f, (dm.IntegerField, dm.PositiveIntegerField,
                            dm.FloatField, dm.DecimalField)):
            ftype = 'number'
        elif isinstance(f, dm.TextField):
            ftype = 'textarea'
        elif hasattr(f, 'choices') and f.choices:
            ftype = 'select'
        else:
            ftype = 'text'

        # Resolve default value
        default = None
        if f.default is not dm.fields.NOT_PROVIDED:
            default = f.default() if callable(f.default) else f.default

        fields.append({
            'name': f.name,
            'label': f.name,
            'ftype': ftype,
            'default': default,
            'choices': list(f.choices) if (hasattr(f, 'choices') and f.choices) else [],
            'help_text': getattr(f, 'help_text', '') or '',
            'null': getattr(f, 'null', False),
        })
    return fields


def add_component(request, table_name):
    """POST: create a new component from submitted form data and redirect to browse."""
    from django.shortcuts import redirect
    from django.db import models as dm
    import re as _re
    if request.method == 'POST':
        model_class = apps.get_model('dashboard', table_name)
        kwargs = {}
        for f in model_class._meta.get_fields():
            if not hasattr(f, 'column'):
                continue
            if f.name == 'id':
                continue
            if getattr(f, 'auto_now_add', False) or getattr(f, 'auto_now', False):
                continue
            if isinstance(f, dm.JSONField):
                continue
            raw = request.POST.get(f.name)
            if raw is None:
                continue
            if isinstance(f, dm.BooleanField):
                kwargs[f.name] = (raw.lower() in ('on', 'true', '1', 'yes'))
            elif isinstance(f, (dm.FloatField, dm.DecimalField)):
                try:
                    kwargs[f.name] = float(raw)
                except ValueError:
                    pass
            elif isinstance(f, (dm.IntegerField, dm.PositiveIntegerField)):
                try:
                    kwargs[f.name] = int(raw)
                except ValueError:
                    pass
            else:
                kwargs[f.name] = raw

        # Make the name unique: strip any existing suffix, find next integer
        if 'name' in kwargs and hasattr(model_class, '_meta'):
            base_name = _re.sub(r'-\d+$', '', kwargs['name'])
            existing = set(
                model_class.objects
                .filter(name__regex=rf'^{_re.escape(base_name)}(-\d+)?$')
                .values_list('name', flat=True)
            )
            if base_name in existing or existing:
                n = 1
                while f'{base_name}-{n}' in existing:
                    n += 1
                kwargs['name'] = f'{base_name}-{n}'

        model_class.objects.create(**kwargs)
    return redirect('dashboard-browse', table_name=table_name)


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
        'table_name': table_name,
        'modal_fields': _modal_fields_for(model_class),
    }

    return render(request, "dashboard/browse.html", context)
