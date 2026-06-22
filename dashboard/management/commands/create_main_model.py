"""
Management command: create_main_model
--------------------------------------
Creates a 'Main Model' Simulation with all component objects pre-populated from
the reference_data defaults (reference_data/python/renew2h2.py).

All component names are prefixed with 'Main '.
The command is idempotent: it skips creation if objects already exist.

Usage:
    python manage.py create_main_model
    python manage.py create_main_model --kind ALK   # default: PEM
    python manage.py create_main_model --overwrite  # recreate even if exists
"""

import math
from django.core.management.base import BaseCommand
from dashboard.models import (
    Battery,
    ElectroCellPEM,
    ElectrolyserUnit,
    ThermalProperties,
    Simulation,
)


# ---------------------------------------------------------------------------
# Reference-data defaults (mirrors initialise_simulation() in renew2h2.py)
# ---------------------------------------------------------------------------

_BATTERY_DEFAULTS = dict(
    name='Main Battery',
    rKt=4.14e-10,
    rKs=1.04,
    KTemp=6.93e-2,
    rAlphaSei=5.75e-2,
    rKd1=1.4e5,
    rKd2=-5.01e-1,
    rKd3=-1.23e5,
    rBetaSei=121.0,
    rTcRef=55.0,
    rSoCRef=0.5,
    arInitialSoC=0.5,
    rFt=0.0,
    rFc=0.0,
    rBatteryMWh=15.0,
    # rInitialBatteryRating and rBatteryRating are computed below
    rInitialBatteryRating=15.0 * 3.6e9,   # MWh → J
    rBatteryRating=15.0 * 3.6e9,
    rRCD=1.0,
    rControlTargetSoC=0.5,
    rBatteryProportionalGain=15.0 * 3.6e9 / 3600.0 / 10e6,  # matches initialise_simulation
    rReplacementThreshold=0.7,
    iNumReplacements=0,
    aiReplacementHour=None,
)

_ELECTROCELL_PEM_DEFAULTS = dict(
    name='Main Electro Cell',
    iNumCurrent=1000,
    rA_cell=1000.0,
    rI_rated=3.0,
    rT_0=20.0,
    rT=55.0,
    rE_min0=1.55,
    rR_0=0.345,
    rD_rt=-0.0045,
    rV_cellNom=2.1,
    rV_bank=633.5,
    rI_bank=3000.0,
    rF1=0.25,
    rF2=0.996,
    arFaradayTemp_C=[40.0, 60.0, 80.0],
    arFaradayF1=[150.0, 200.0, 250.0],
    arFaradayF2=[0.99, 0.985, 0.98],
)

_THERMAL_DEFAULTS = dict(
    name='Main Thermal Properties',
    rAmbientTemp=15.0,
    rTauHeating=1200.0,   # 20 * 60
    rTauCooling=1800.0,   # 30 * 60
    rTargetTemp=60.0,
    rMinTemp=50.0,
)

# Technology presets (mirrors _TECH_PRESETS in renew2h2.py)
_TECH_PRESETS = {
    'PEM': {
        'topology': dict(iN_stacks=4, iN_banks=2, iNumElectro=5, iN_cell=100),
        'dynamics': dict(
            rTimeConst=0.0,
            rDeadBandRatio=2.0,
            r_s=1.42e-10,
            r_f=3.33e-7,
            r_o=1.47e-4,
            rRampUp_W_s=5.0e5,
            rRampDown_W_s=5.0e5,
        ),
    },
    'ALK': {
        'topology': dict(iN_stacks=9, iN_banks=3, iNumElectro=5, iN_cell=100),
        'dynamics': dict(
            rTimeConst=120.0,
            rDeadBandRatio=3.0,
            r_s=1.0e-10,
            r_f=2.0e-7,
            r_o=3.0e-4,
            rRampUp_W_s=5.0e5,
            rRampDown_W_s=3.0e5,
        ),
    },
}


def _build_electrolyser_defaults(kind: str) -> dict:
    """Build ElectrolyserUnit field values for the given technology."""
    preset = _TECH_PRESETS.get(kind.upper(), _TECH_PRESETS['PEM'])
    topo = preset['topology']
    dyn = preset['dynamics']

    iN_stacks = topo['iN_stacks']
    iN_banks = topo['iN_banks']
    iNumElectro = topo['iNumElectro']
    iN_cell = topo['iN_cell']
    iControlLevel = 2  # Bank level (default)

    # iNumUnits and rDivisor computed as in initialise_simulation()
    iNumUnits = iNumElectro * iN_banks        # iControlLevel == 2
    rDivisor = iN_stacks * iN_cell            # iControlLevel == 2

    return dict(
        name='Main Electrolyser Unit',
        iN_stacks=iN_stacks,
        iN_banks=iN_banks,
        iNumElectro=iNumElectro,
        iN_cell=iN_cell,
        iControlLevel=iControlLevel,
        iNumUnits=iNumUnits,
        rDegradation=1e-30,
        rTurnDownRatio=0.125,
        rAncillaryPowerFrac=0.0,
        **dyn,
    )


def _build_simulation_defaults(kind: str, el_defaults: dict) -> dict:
    """Build Simulation field values."""
    rDivisor = el_defaults['iN_stacks'] * el_defaults['iN_cell']  # iControlLevel == 2
    return dict(
        name='Main Model',
        description=f'Main Model simulation created from reference defaults ({kind} electrolyser).',
        bSingleTurb=True,
        iWindType=0,
        iNumYears=1,
        rTotalTime=3700.0,
        rTimeStep=1.0,
        rTransientSteps=101,
        rDivisor=float(rDivisor),
        arLateralDistances=None,
    )


class Command(BaseCommand):
    help = (
        'Create a "Main Model" Simulation with reference-data components '
        '(Battery, ElectroCellPEM, ElectrolyserUnit, ThermalProperties). '
        'All component names are prefixed with "Main ". Idempotent by default.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--kind',
            default='PEM',
            choices=['PEM', 'ALK'],
            help='Electrolyser technology preset (default: PEM)',
        )
        parser.add_argument(
            '--overwrite',
            action='store_true',
            default=False,
            help='Delete and recreate objects even if they already exist.',
        )

    def handle(self, *args, **options):
        kind = options['kind'].upper()
        overwrite = options['overwrite']

        self.stdout.write(self.style.MIGRATE_HEADING(
            f'Creating "Main Model" simulation (kind={kind}, overwrite={overwrite}) …'
        ))

        el_defaults = _build_electrolyser_defaults(kind)
        sim_defaults = _build_simulation_defaults(kind, el_defaults)

        # --- Battery ---
        bat = self._get_or_create(Battery, 'Main Battery', _BATTERY_DEFAULTS, overwrite)

        # --- ElectroCellPEM ---
        ec = self._get_or_create(ElectroCellPEM, 'Main Electro Cell', _ELECTROCELL_PEM_DEFAULTS, overwrite)

        # --- ElectrolyserUnit ---
        el = self._get_or_create(ElectrolyserUnit, 'Main Electrolyser Unit', el_defaults, overwrite)

        # --- ThermalProperties ---
        th = self._get_or_create(ThermalProperties, 'Main Thermal Properties', _THERMAL_DEFAULTS, overwrite)

        # --- Simulation ---
        sim_name = 'Main Model'
        if overwrite:
            Simulation.objects.filter(name=sim_name).delete()
            self.stdout.write(f'  Deleted existing Simulation "{sim_name}"')

        sim, created = Simulation.objects.get_or_create(
            name=sim_name,
            defaults=sim_defaults,
        )
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created Simulation "{sim_name}" (id={sim.pk})'))
        else:
            self.stdout.write(f'  Simulation "{sim_name}" already exists (id={sim.pk}) — skipped')

        # Link components (idempotent M2M add)
        sim.batteries.add(bat)
        sim.electro_cells.add(ec)
        sim.electrolyser_units.add(el)
        sim.thermal_properties.add(th)

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Done. Simulation "{sim_name}" (id={sim.pk}) linked to:\n'
            f'  Battery            : {bat.name} (id={bat.pk})\n'
            f'  ElectroCellPEM     : {ec.name} (id={ec.pk})\n'
            f'  ElectrolyserUnit   : {el.name} (id={el.pk})\n'
            f'  ThermalProperties  : {th.name} (id={th.pk})\n'
        ))

    # ------------------------------------------------------------------
    def _get_or_create(self, model, name, defaults, overwrite):
        if overwrite:
            model.objects.filter(name=name).delete()
            self.stdout.write(f'  Deleted existing {model.__name__} "{name}"')

        obj, created = model.objects.get_or_create(name=name, defaults=defaults)
        label = model.__name__
        if created:
            self.stdout.write(self.style.SUCCESS(f'  Created {label} "{name}" (id={obj.pk})'))
        else:
            self.stdout.write(f'  {label} "{name}" already exists (id={obj.pk}) — skipped')
        return obj
