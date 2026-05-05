# Django specific libraries
from django.shortcuts import render
from django.utils.safestring import mark_safe
from django.apps import apps
from django.views.decorators.http import require_POST
import json

# Django REST framework
# ...

# Std libraries
import re
from django.utils.html import escape

# Django models
from .models import *
from .models import SimulationRun

# Local src libraries
# ...



def landing(request):
    """Landing page: overview of app with workflow guide and quick stats."""
    from .models import Simulation, SimulationRun, WindInput
    context = {
        'sim_count': Simulation.objects.count(),
        'run_count': SimulationRun.objects.count(),
        'wind_count': WindInput.objects.exclude(wind_file='').count(),
        'recent_runs': SimulationRun.objects.select_related('simulation').order_by('-started_at')[:5],
    }
    return render(request, 'dashboard/landing.html', context)


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

    linked_ids = {
        'Battery':           set(sim.batteries.values_list('id', flat=True)),
        'ElectroCellPEM':    set(sim.electro_cells.values_list('id', flat=True)),
        'ElectrolyserUnit':  set(sim.electrolyser_units.values_list('id', flat=True)),
        'ThermalProperties': set(sim.thermal_properties.values_list('id', flat=True)),
        'TimeOutput':        set(sim.time_outputs.values_list('id', flat=True)),
        'WindInput':         set(sim.wind_inputs.values_list('id', flat=True)),
    }

    groups_with_items = [g for g in groups if g['items']]
    groups_empty = [
        {
            **g,
            'available': [
                {'id': o.pk, 'label': str(o)}
                for o in _GROUP_M2M[g['label']][0].objects.exclude(
                    pk__in=linked_ids[g['label']]
                ).order_by('id')
            ],
            'available_json': json.dumps([
                {'id': o.pk, 'label': str(o)}
                for o in _GROUP_M2M[g['label']][0].objects.exclude(
                    pk__in=linked_ids[g['label']]
                ).order_by('id')
            ]),
        }
        for g in groups if not g['items']
    ]

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

    latest_run = sim.runs.first()   # newest first via Meta ordering
    sim_runs   = list(sim.runs.all())

    return render(request, 'dashboard/simulation_detail.html', {
        'sim': sim,
        'sim_settings': sim_settings,
        'groups': groups_with_items,
        'groups_empty': groups_empty,
        'latest_run': latest_run,
        'sim_runs': sim_runs,
    })


# Map from group label → (model_class, m2m manager name on Simulation)
_GROUP_M2M = {
    'Battery':           (Battery,           'batteries'),
    'ElectroCellPEM':    (ElectroCellPEM,    'electro_cells'),
    'ElectrolyserUnit':  (ElectrolyserUnit,  'electrolyser_units'),
    'ThermalProperties': (ThermalProperties, 'thermal_properties'),
    'TimeOutput':        (TimeOutput,        'time_outputs'),
    'WindInput':         (WindInput,         'wind_inputs'),
}


def link_components(request, sim_id):
    """POST: add selected component IDs to a simulation M2M relation."""
    from django.shortcuts import get_object_or_404, redirect
    if request.method == 'POST':
        sim = get_object_or_404(Simulation, pk=sim_id)
        label = request.POST.get('group_label', '')
        ids = request.POST.getlist('component_ids')
        if label in _GROUP_M2M and ids:
            model_class, manager_name = _GROUP_M2M[label]
            objs = model_class.objects.filter(pk__in=ids)
            getattr(sim, manager_name).add(*objs)
    return redirect('dashboard-simulation-detail', sim_id=sim_id)


def _resolve_wind_h5_path(sim):
    """Return the absolute Path to the HDF5 file from the first linked WindInput
    that has a wind_file set.  Raises ValueError if none is found."""
    from django.conf import settings as _settings
    for wi in sim.wind_inputs.exclude(wind_file='').exclude(wind_file__isnull=True):
        abs_path = _Path(_settings.MEDIA_ROOT) / wi.wind_file.name
        if abs_path.exists():
            return abs_path
    raise ValueError(
        f"Simulation '{sim.name}' has no linked WindInput with a valid wind file. "
        "Upload an HDF5 file on the Wind Data page and link it via a WindInput component."
    )


def _save_run_outputs(run, results: dict) -> str:
    """Serialise simulation results to an HDF5 file under MEDIA_ROOT/outputs/.

    Returns the relative path (from MEDIA_ROOT) of the saved file, e.g.
    ``outputs/run_42_Simulation-0_20260505-143012.h5``.

    Structure written to HDF5
    ─────────────────────────
    /meta/
        sim_name        str
        run_id          int
        kind            str
        runtime_s       float
        use_cooling_feedback  bool
        insulated       bool
    /year_<N>/          (one group per simulated year)
        battery/
            arSoc, arSocMax, arSocMin, arSocAv, arRCD, arBatteryRating  (1-D float64)
        electrolyser/
            arElecOnAv          (1-D float64)
            arHourlyDegradation (2-D float64, shape [n_units, n_hours])
        h2/
            arTotalH2           (1-D float64, cumulative kg/s per hour)
    """
    import h5py
    import numpy as np
    import re
    from django.conf import settings as dj_settings
    from pathlib import Path
    from django.utils import timezone as tz

    media_root = Path(dj_settings.MEDIA_ROOT)
    out_dir = media_root / 'outputs'
    out_dir.mkdir(parents=True, exist_ok=True)

    sim_name_slug = re.sub(r'[^\w\-]', '_', run.simulation.name)[:40]
    ts = tz.localtime(run.started_at).strftime('%Y%m%d-%H%M%S') if run.started_at else 'unknown'
    filename = f'run_{run.pk}_{sim_name_slug}_{ts}.h5'
    abs_path = out_dir / filename

    year_results = results.get('YearResults', [])

    with h5py.File(abs_path, 'w') as f:
        # ── /meta ────────────────────────────────────────────────────────────
        meta = f.create_group('meta')
        meta.attrs['sim_name']             = run.simulation.name
        meta.attrs['run_id']               = run.pk
        meta.attrs['kind']                 = str(results.get('Kind', ''))
        meta.attrs['runtime_s']            = float(results.get('Runtime_s', 0.0))
        meta.attrs['use_cooling_feedback'] = bool(results.get('UseCoolingFeedback', False))
        meta.attrs['insulated']            = bool(results.get('Insulated', False))

        # ── /year_N ──────────────────────────────────────────────────────────
        for yr_idx, yr in enumerate(year_results):
            grp = f.create_group(f'year_{yr_idx}')
            log = yr.get('Log', {})

            # Battery time-series
            bat = grp.create_group('battery')
            for key in ('arSoc', 'arSocMax', 'arSocMin', 'arSocAv',
                        'arRCD', 'arBatteryRating'):
                arr = log.get(key)
                if arr is not None:
                    bat.create_dataset(key, data=np.asarray(arr, dtype=np.float64),
                                       compression='gzip', compression_opts=4)

            # Electrolyser time-series
            elec = grp.create_group('electrolyser')
            for key in ('arElecOnAv',):
                arr = log.get(key)
                if arr is not None:
                    elec.create_dataset(key, data=np.asarray(arr, dtype=np.float64),
                                        compression='gzip', compression_opts=4)
            deg = log.get('arHourlyDegradation')
            if deg is not None:
                elec.create_dataset('arHourlyDegradation',
                                    data=np.asarray(deg, dtype=np.float64),
                                    compression='gzip', compression_opts=4)

            # H2 production
            h2 = grp.create_group('h2')
            arr = yr.get('TotalH2')
            if arr is not None:
                h2.create_dataset('arTotalH2', data=np.asarray(arr, dtype=np.float64),
                                  compression='gzip', compression_opts=4)

    # Return path relative to MEDIA_ROOT
    return str(abs_path.relative_to(media_root))


def _run_simulation_thread(run_id):
    """Background worker: update SimulationRun status while running."""
    from django.utils import timezone
    try:
        run = SimulationRun.objects.select_related('simulation').get(pk=run_id)
        run.status = SimulationRun.RUNNING
        run.started_at = timezone.now()
        run.save(update_fields=['status', 'started_at'])

        from r2h2.r2h2 import R2H2
        wind_path = _resolve_wind_h5_path(run.simulation)
        sim_engine = R2H2(run.simulation, wind_h5_path=str(wind_path))

        _progress_interval = 50  # update DB message every N hours
        _progress_start = timezone.now()

        def _on_progress(year, total_years, hour, total_hours):
            if hour % _progress_interval == 0:
                total_steps  = total_years * total_hours
                done_steps   = year * total_hours + hour
                pct = int(done_steps / total_steps * 100) if total_steps else 0
                elapsed = (timezone.now() - _progress_start).total_seconds()
                if done_steps > 0 and elapsed > 0:
                    total_s   = elapsed / done_steps * total_steps
                    finish_at = timezone.localtime(
                        _progress_start + timezone.timedelta(seconds=total_s)
                    )
                    eta_str = (f' [est. {_fmt_duration(total_s)}'
                               f', done ~{finish_at.strftime("%H:%M:%S")}]')
                else:
                    eta_str = ''
                msg = (f'Year {year+1}/{total_years} \u2014 hour {hour+1}/{total_hours} \u2014 {pct}\u00a0%{eta_str}')
                SimulationRun.objects.filter(pk=run.pk).update(message=msg)

        results = sim_engine.run(run_id=run.pk, progress_callback=_on_progress)

        # Only mark DONE if user hasn't cancelled in the meantime
        run.refresh_from_db(fields=['status'])
        if run.status == SimulationRun.CANCELLED:
            return

        # Persist outputs to HDF5
        try:
            rel_path = _save_run_outputs(run, results)
            run.output_path = rel_path
        except Exception as save_exc:
            run.output_path = ''
            import logging
            logging.getLogger(__name__).warning(
                'Could not save run #%s outputs: %s', run.pk, save_exc)

        run.status  = SimulationRun.DONE
        desc = run.description.strip()
        if desc:
            suffix = desc if len(desc) <= 80 else desc[:77] + '…'
            run.message = f'Completed. {suffix}'
        else:
            run.message = f'Simulation \u201c{run.simulation.name}\u201d completed successfully.'
        run.finished_at = timezone.now()
        run.save(update_fields=['status', 'message', 'finished_at', 'output_path'])
    except InterruptedError:
        # User cancelled — the cancel view already wrote CANCELLED status; nothing to do
        pass
    except Exception as exc:
        try:
            run.status  = SimulationRun.ERROR
            run.message = str(exc)
            run.finished_at = timezone.now()
            run.save(update_fields=['status', 'message', 'finished_at'])
        except Exception:
            pass


def run_simulation(request, sim_id):
    """POST: create a SimulationRun, redirect immediately, run in background thread."""
    from django.shortcuts import get_object_or_404, redirect
    from django.contrib import messages
    import threading
    if request.method == 'POST':
        sim = get_object_or_404(Simulation, pk=sim_id)
        run = SimulationRun.objects.create(simulation=sim, status=SimulationRun.PENDING)
        messages.success(request, f'Simulation \u201c{sim.name}\u201d started.')
        t = threading.Thread(target=_run_simulation_thread, args=(run.pk,), daemon=True)
        t.start()
    return redirect('dashboard-simulation-detail', sim_id=sim_id)


def _fmt_duration(seconds):
    """Format a duration in seconds as hh:mm:ss."""
    s = int(seconds)
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    return f'{h:02d}:{m:02d}:{sec:02d}'


def poll_simulation_run(request, sim_id, run_id):
    """GET: return JSON status of a SimulationRun for client-side polling."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    dur = run.duration_seconds
    if dur is not None:
        duration_str = _fmt_duration(dur)
    elif run.started_at is not None:
        elapsed = (timezone.now() - run.started_at).total_seconds()
        duration_str = _fmt_duration(elapsed)
    else:
        duration_str = ''
    return JsonResponse({
        'status':      run.status,
        'message':     run.message or '',
        'duration':    duration_str,
        'output_path': run.output_path or '',
        'done':        run.status in (SimulationRun.DONE, SimulationRun.ERROR, SimulationRun.CANCELLED),
    })


@require_POST
def cancel_simulation_run(request, sim_id, run_id):
    """POST: mark a pending/running SimulationRun as cancelled (error status)."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    from django.utils import timezone
    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    if run.status in (SimulationRun.PENDING, SimulationRun.RUNNING):
        run.status = SimulationRun.CANCELLED
        run.message = 'Cancelled by user.'
        run.finished_at = timezone.now()
        run.save(update_fields=['status', 'message', 'finished_at'])
    return JsonResponse({'status': run.status, 'message': run.message})


@require_POST
def delete_simulation_run(request, sim_id, run_id):
    """POST: delete a single finished SimulationRun."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    # Refuse to delete an active run — cancel it first
    if run.status in (SimulationRun.PENDING, SimulationRun.RUNNING):
        return JsonResponse({'error': 'Cannot delete an active run. Cancel it first.'}, status=400)
    # Remove the HDF5 output file if it exists
    if run.output_path:
        from django.conf import settings as dj_settings
        from pathlib import Path
        abs_path = Path(dj_settings.MEDIA_ROOT) / run.output_path
        try:
            abs_path.unlink(missing_ok=True)
        except Exception:
            pass
    run.delete()
    return JsonResponse({'deleted': run_id})


@require_POST
def update_run_description(request, sim_id, run_id):
    """POST: save a user-supplied description for a SimulationRun."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    desc = request.POST.get('description', '').strip()[:200]
    run.description = desc
    # Refresh the completion message to reflect the new description
    if run.status == SimulationRun.DONE:
        if desc:
            suffix = desc if len(desc) <= 80 else desc[:77] + '\u2026'
            run.message = f'Completed. {suffix}'
        else:
            run.message = f'Simulation \u201c{run.simulation.name}\u201d completed successfully.'
        run.save(update_fields=['description', 'message'])
    else:
        run.save(update_fields=['description'])
    return JsonResponse({'description': run.description, 'message': run.message})





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


# ─── Wind data upload ──────────────────────────────────────────────────────────

import os as _os
from django.http import JsonResponse
from r2h2.config import get_wind_data_dir, load_config, get_config_path
import yaml as _yaml
import pandas as _pd
from pathlib import Path as _Path


def wind_data(request):
    """Page listing uploaded wind HDF5 files with a drag-and-drop uploader."""
    from django.conf import settings as django_settings
    wind_dir = get_wind_data_dir()
    media_root = _Path(django_settings.MEDIA_ROOT)

    # Fetch all linked WindInput records keyed by filename
    wi_qs = WindInput.objects.exclude(wind_file='').exclude(wind_file__isnull=True)
    wi_by_name = {_Path(wi.wind_file.name).name: wi for wi in wi_qs}

    # Backfill metadata for records that were uploaded before the new fields existed
    needs_save = []
    for wi in wi_by_name.values():
        if wi.h5_datasets == '' and wi.ts_start is None:
            full_path = media_root / wi.wind_file.name
            if full_path.exists():
                meta = _introspect_wind_h5(full_path)
                for k, v in meta.items():
                    setattr(wi, k, v)
                needs_save.append(wi)
    if needs_save:
        fields = ['h5_datasets', 'ts_start', 'ts_end', 'ts_resolution', 'ts_n_hours']
        for wi in needs_save:
            wi.save(update_fields=fields)

    files = sorted(
        [
            {
                'name': f.name,
                'size_mb': round(f.stat().st_size / 1e6, 2),
                'modified': _pd.Timestamp(f.stat().st_mtime, unit='s').strftime('%Y-%m-%d %H:%M'),
                'wind_input': wi_by_name.get(f.name),
            }
            for f in wind_dir.iterdir()
            if f.suffix.lower() in ('.h5', '.hdf5', '.hdf')
        ],
        key=lambda x: x['name'],
    )
    cfg = load_config() or {}
    wind_dir_str = cfg.get('paths', {}).get('wind_data_dir', str(wind_dir))
    return render(request, 'dashboard/wind_data.html', {
        'files': files,
        'wind_dir': wind_dir_str,
    })


def _introspect_wind_h5(path):
    """Return a dict of HDF5 metadata for a wind file.

    Keys: h5_datasets, ts_start, ts_end, ts_resolution, ts_n_hours.
    All values default to safe empty/None on any error.
    """
    meta = {'h5_datasets': '', 'ts_start': None, 'ts_end': None,
            'ts_resolution': None, 'ts_n_hours': None}
    try:
        import h5py, numpy as np
        datasets = []
        with h5py.File(path, 'r') as f:
            def _collect(name, obj):
                if isinstance(obj, h5py.Dataset):
                    datasets.append(f'/{name} {list(obj.shape)} {obj.dtype}')
            f.visititems(_collect)
            meta['h5_datasets'] = ', '.join(datasets)
            # Time axis
            if '/Time' in f:
                t = f['/Time'][:].ravel()
                if len(t) > 1:
                    meta['ts_start']      = float(t[0])
                    meta['ts_end']        = float(t[-1])
                    meta['ts_resolution'] = float(round(t[1] - t[0], 6))
            # Hour count from WindSpeed
            if '/WindSpeed' in f:
                ws = f['/WindSpeed'][:].ravel()
                meta['ts_n_hours'] = int(len(ws))
    except Exception:
        pass
    return meta


@require_POST
def wind_data_upload(request):
    """AJAX endpoint: receive one or more HDF5 files and save them to wind_data_dir."""
    if not request.FILES:
        return JsonResponse({'error': 'No files received.'}, status=400)

    wind_dir = get_wind_data_dir()
    saved = []
    errors = []

    for field_name, uploaded_file in request.FILES.items():
        name = _Path(uploaded_file.name).name  # strip any path components
        if _Path(name).suffix.lower() not in ('.h5', '.hdf5', '.hdf'):
            errors.append(f'{name}: not a recognised HDF5 extension (.h5 / .hdf5 / .hdf)')
            continue
        dest = wind_dir / name
        try:
            with open(dest, 'wb') as fh:
                for chunk in uploaded_file.chunks():
                    fh.write(chunk)
            # Introspect HDF5 metadata
            meta = _introspect_wind_h5(dest)
            # Create or retrieve the linked WindInput record and update metadata
            rel_path = 'wind_data/' + name
            wind_input, created = WindInput.objects.get_or_create(
                wind_file=rel_path,
                defaults={'name': _Path(name).stem, **meta},
            )
            if not created:
                for k, v in meta.items():
                    setattr(wind_input, k, v)
                wind_input.save(update_fields=list(meta.keys()))
            saved.append({
                'name': name,
                'size_mb': round(dest.stat().st_size / 1e6, 2),
                'wind_input_id': wind_input.id,
            })
        except OSError as exc:
            errors.append(f'{name}: {exc}')

    status = 200 if saved else 400
    return JsonResponse({'saved': saved, 'errors': errors}, status=status)


@require_POST
def wind_data_set_dir(request):
    """AJAX endpoint: update wind_data_dir in config.yaml."""
    new_dir = request.POST.get('wind_data_dir', '').strip()
    if not new_dir:
        return JsonResponse({'error': 'No directory provided.'}, status=400)
    try:
        from r2h2.config import update_wind_data_dir
        cfg = update_wind_data_dir(new_dir)
        return JsonResponse({'wind_data_dir': cfg['paths']['wind_data_dir']})
    except Exception as exc:
        return JsonResponse({'error': str(exc)}, status=500)
