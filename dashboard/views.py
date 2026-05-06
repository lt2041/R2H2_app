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
    Uses MetaInfo.ui_display_fields for human-readable labels when available.
    """
    ui_map = getattr(getattr(obj.__class__, 'MetaInfo', None), 'ui_display_fields', {})
    # Build a lookup of all concrete fields by name
    all_fields = {f.name: f for f in obj._meta.get_fields() if hasattr(f, 'column')}
    scalar_fields, array_fields = [], []

    # Iterate in ui_display_fields order when available, then append remaining fields
    ordered_names = list(ui_map.keys()) if ui_map else []
    remaining = [n for n in all_fields if n not in ui_map and n != 'id']
    for name in ordered_names + remaining:
        if name == 'id' or name not in all_fields:
            continue
        label = ui_map.get(name, name)
        value = getattr(obj, name, None)
        if isinstance(value, list):
            array_fields.append({'name': label, 'value': value})
        else:
            scalar_fields.append({'name': label, 'value': value})
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
        scalar_rows = [scalar[i:i+2] for i in range(0, len(scalar), 2)]
        return {'obj': obj, 'scalar': scalar, 'scalar_rows': scalar_rows, 'arrays': arrays}

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

    from datetime import date as _today_date
    datum_display = sim.datum_date.strftime('%d %b %Y') if sim.datum_date else None

    sim_settings = [
        {'name': 'Wind data resolution', 'value': wind_type_label,         'unit': ''},
        {'name': 'Duration',             'value': sim.duration_days,        'unit': 'days', 'editable': 'duration_days'},
        {'name': 'Datum date',           'value': datum_display,            'unit': '',     'editable': 'datum_date',
         'raw': sim.datum_date.isoformat() if sim.datum_date else ''},
        {'name': 'Number of years',      'value': sim.iNumYears,            'unit': 'yr'},
        {'name': 'Total time',           'value': sim.rTotalTime,           'unit': 's'},
        {'name': 'Time step',            'value': sim.rTimeStep,            'unit': 's'},
        {'name': 'Transient steps',      'value': sim.rTransientSteps,      'unit': ''},
        {'name': 'Single turbine',       'value': sim.bSingleTurb,          'unit': ''},
        {'name': 'Lateral distances',    'value': sim.arLateralDistances,   'unit': 'm'},
        {'name': 'Power divisor',        'value': sim.rDivisor,             'unit': 'W'},
    ]
    # Group into rows of 3 for 6-column layout
    sim_settings_pairs = [sim_settings[i:i+2] for i in range(0, len(sim_settings), 2)]

    latest_run = sim.runs.first()   # newest first via Meta ordering
    sim_runs   = list(sim.runs.all())

    return render(request, 'dashboard/simulation_detail.html', {
        'sim': sim,
        'sim_settings': sim_settings,
        'sim_settings_pairs': sim_settings_pairs,
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
    /inputs/            (snapshot of all component and simulation settings at run time)
        simulation/     (scalar attrs from Simulation model)
        battery_<N>/    (one sub-group per linked Battery)
        electrocellpem_<N>/
        electrolyserunit_<N>/
        thermalproperties_<N>/
        windinput_<N>/
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

    def _write_obj_attrs(grp, obj):
        """Write all concrete scalar fields of a Django model instance as HDF5 attrs."""
        for field in obj._meta.get_fields():
            if not hasattr(field, 'column'):
                continue
            name = field.name
            val = getattr(obj, name, None)
            if val is None:
                grp.attrs[name] = 'None'
            elif isinstance(val, bool):
                grp.attrs[name] = int(val)
            elif isinstance(val, (int, float, str)):
                grp.attrs[name] = val
            elif hasattr(val, 'isoformat'):      # date / datetime
                grp.attrs[name] = val.isoformat()
            elif isinstance(val, list):
                try:
                    arr = np.asarray(val)
                    if arr.dtype.kind in ('i', 'u', 'f'):
                        grp.create_dataset(name, data=arr.astype(np.float64),
                                           compression='gzip', compression_opts=4)
                    else:
                        grp.attrs[name] = str(val)
                except Exception:
                    grp.attrs[name] = str(val)
            else:
                grp.attrs[name] = str(val)

    sim_obj = run.simulation

    with h5py.File(abs_path, 'w') as f:
        # ── /meta ────────────────────────────────────────────────────────────
        meta = f.create_group('meta')
        meta.attrs['sim_name']             = sim_obj.name
        meta.attrs['run_id']               = run.pk
        meta.attrs['kind']                 = str(results.get('Kind', ''))
        meta.attrs['runtime_s']            = float(results.get('Runtime_s', 0.0))
        meta.attrs['use_cooling_feedback'] = bool(results.get('UseCoolingFeedback', False))
        meta.attrs['insulated']            = bool(results.get('Insulated', False))

        # ── /inputs ──────────────────────────────────────────────────────────
        inp = f.create_group('inputs')

        sim_grp = inp.create_group('simulation')
        _write_obj_attrs(sim_grp, sim_obj)

        for i, obj in enumerate(sim_obj.batteries.all()):
            _write_obj_attrs(inp.create_group(f'battery_{i}'), obj)
        for i, obj in enumerate(sim_obj.electro_cells.all()):
            _write_obj_attrs(inp.create_group(f'electrocellpem_{i}'), obj)
        for i, obj in enumerate(sim_obj.electrolyser_units.all()):
            _write_obj_attrs(inp.create_group(f'electrolyserunit_{i}'), obj)
        for i, obj in enumerate(sim_obj.thermal_properties.all()):
            _write_obj_attrs(inp.create_group(f'thermalproperties_{i}'), obj)
        for i, obj in enumerate(sim_obj.wind_inputs.all()):
            _write_obj_attrs(inp.create_group(f'windinput_{i}'), obj)

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

        # If user set a duration override, truncate wind data to requested hours
        duration_days = run.simulation.duration_days
        if duration_days:
            import numpy as np
            max_hours = duration_days * 24
            wi = sim_engine.windinputs
            if wi is not None and hasattr(wi, 'arPowerInput') and wi.arPowerInput is not None:
                n_hours = wi.arPowerInput.shape[1]
                if max_hours < n_hours:
                    # arPowerInput shape: (time_steps_per_hour, num_hours)
                    # Only truncate the hours axis (axis 1); arTime is the
                    # within-hour time axis and must be left unchanged.
                    wi.arPowerInput = wi.arPowerInput[:, :max_hours]

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


def view_run_results(request, sim_id, run_id):
    """GET: display interactive charts for a completed SimulationRun."""
    from django.shortcuts import get_object_or_404
    from django.conf import settings as dj_settings
    from pathlib import Path
    import json as _json

    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    sim = run.simulation

    if not run.output_path:
        from django.contrib import messages
        messages.error(request, 'No results file found for this run.')
        return redirect('dashboard-simulation-detail', sim_id=sim_id)

    abs_path = Path(dj_settings.MEDIA_ROOT) / run.output_path
    if not abs_path.exists():
        from django.contrib import messages
        messages.error(request, f'Results file not found: {run.output_path}')
        return redirect('dashboard-simulation-detail', sim_id=sim_id)

    import h5py
    import numpy as np

    years_data = []      # list of dicts, one per year group
    meta_info = {}

    with h5py.File(abs_path, 'r') as f:
        # Read metadata attrs
        if 'meta' in f:
            m = f['meta']
            meta_info = {k: (v.item() if hasattr(v, 'item') else v)
                         for k, v in m.attrs.items()}

        # Collect sorted year groups
        year_keys = sorted(
            [k for k in f.keys() if k.startswith('year_')],
            key=lambda s: int(s.split('_')[1])
        )

        for yk in year_keys:
            yr_grp = f[yk]
            ydata = {'label': f'Year {int(yk.split("_")[1]) + 1}'}

            # Battery
            bat = yr_grp.get('battery', {})
            for key in ('arSoc', 'arSocMax', 'arSocMin', 'arSocAv', 'arRCD', 'arBatteryRating'):
                if key in bat:
                    arr = bat[key][:]
                    # Downsample to at most 8760 points to keep JSON small
                    if len(arr) > 8760:
                        step = len(arr) // 8760
                        arr = arr[::step]
                    ydata[key] = arr.tolist()

            # Electrolyser
            elec = yr_grp.get('electrolyser', {})
            if 'arElecOnAv' in elec:
                arr = elec['arElecOnAv'][:]
                if len(arr) > 8760:
                    arr = arr[:8760]
                ydata['arElecOnAv'] = arr.tolist()
            if 'arHourlyDegradation' in elec:
                deg = elec['arHourlyDegradation'][:]
                # Sum across units → 1-D
                if deg.ndim == 2:
                    deg = deg.mean(axis=0)
                if len(deg) > 8760:
                    deg = deg[:8760]
                ydata['arHourlyDegradation'] = deg.tolist()

            # H2
            h2g = yr_grp.get('h2', {})
            if 'arTotalH2' in h2g:
                arr = h2g['arTotalH2'][:]
                if len(arr) > 8760:
                    arr = arr[:8760]
                ydata['arTotalH2'] = arr.tolist()

            years_data.append(ydata)

    # Append per-year wind speed data from the linked WindInput H5 file
    try:
        wind_path = _resolve_wind_h5_path(sim)
        with h5py.File(wind_path, 'r') as wf:
            if 'WindSpeed' in wf:
                ws_full = wf['WindSpeed'][0].tolist()  # shape (N,)
                # Distribute hours across years by matching year data lengths
                offset = 0
                for yd in years_data:
                    ref = (yd.get('arSoc') or yd.get('arTotalH2') or yd.get('arElecOnAv') or [])
                    n = len(ref)
                    yd['arWindSpeed'] = ws_full[offset: offset + n] if n else []
                    offset += n
    except Exception:
        pass  # wind data is optional — silently skip if unavailable

    # Compute per-year cumulative hour offsets from datum
    from datetime import date as _date
    datum = sim.datum_date or _date.today()
    datum_iso = datum.isoformat()
    year_cumulative_hours = []
    cumulative = 0
    for yd in years_data:
        year_cumulative_hours.append(cumulative)
        ref = (yd.get('arSoc') or yd.get('arTotalH2') or yd.get('arElecOnAv') or [])
        cumulative += len(ref)

    context = {
        'run': run,
        'sim': sim,
        'meta_info': meta_info,
        'years_data_json': _json.dumps(years_data),
        'year_cumulative_hours_json': _json.dumps(year_cumulative_hours),
        'datum_iso': datum_iso,
        'n_years': len(years_data),
        'n_years_range': range(len(years_data)),
        'xaxis_datetime': run.xaxis_datetime,
        'update_xaxis_url': f'/simulations/{sim_id}/run/{run_id}/xaxis/',
    }
    return render(request, 'dashboard/run_results.html', context)


@require_POST
def update_sim_datum(request, sim_id):
    """POST: save datum_date for a Simulation (used as datetime axis origin in results)."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    raw = request.POST.get('datum_date', '').strip()
    sim = get_object_or_404(Simulation, pk=sim_id)
    if raw == '':
        sim.datum_date = None
    else:
        from datetime import date as _date
        try:
            sim.datum_date = _date.fromisoformat(raw)
        except ValueError:
            return JsonResponse({'error': 'Invalid date format (expected YYYY-MM-DD).'}, status=400)
    sim.save(update_fields=['datum_date'])
    display = sim.datum_date.strftime('%d %b %Y') if sim.datum_date else None
    return JsonResponse({'datum_date': sim.datum_date.isoformat() if sim.datum_date else '',
                         'datum_display': display})


@require_POST
def update_run_xaxis(request, sim_id, run_id):
    """POST: toggle datetime vs hours x-axis preference for a run's results charts."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    run = get_object_or_404(SimulationRun, pk=run_id, simulation_id=sim_id)
    val = request.POST.get('xaxis_datetime', 'true').strip().lower()
    run.xaxis_datetime = (val == 'true')
    run.save(update_fields=['xaxis_datetime'])
    return JsonResponse({'xaxis_datetime': run.xaxis_datetime})


@require_POST
def update_sim_duration(request, sim_id):
    """POST: save duration_days override for a Simulation."""
    from django.http import JsonResponse
    from django.shortcuts import get_object_or_404
    raw = request.POST.get('duration_days', '').strip()
    sim = get_object_or_404(Simulation, pk=sim_id)
    if raw == '' or raw is None:
        sim.duration_days = None
    else:
        try:
            days = int(raw)
            sim.duration_days = max(1, days)
        except ValueError:
            return JsonResponse({'error': 'Invalid value.'}, status=400)
    sim.save(update_fields=['duration_days'])
    return JsonResponse({'duration_days': sim.duration_days})





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
