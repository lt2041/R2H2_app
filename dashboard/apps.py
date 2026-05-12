from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'dashboard'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_seed_default_controller, sender=self)
        post_migrate.connect(_seed_main_model, sender=self)


def _seed_default_controller(sender, **kwargs):
    """Create the default Controller DB record after migrations, if absent."""
    try:
        import datetime
        from dashboard.models import Controller
        from r2h2.config import get_controllers_dir
        get_controllers_dir()  # seeds the physical file
        Controller.objects.get_or_create(
            filename='default_controller.py',
            defaults={
                'name':         'Default Controller',
                'description':  'Built-in template controller provided with R2H2. '
                                'Copy and rename before modifying.',
                'author':       'R2H2',
                'date_created': datetime.date.today(),
                'verified':     True,
            },
        )
    except Exception:
        pass  # tables may not exist yet during initial migrate; safe to swallow


def _seed_main_model(sender, **kwargs):
    """Silently create the 'Main Model' simulation and its components after migrations, if absent."""
    try:
        from dashboard.management.commands.create_main_model import (
            _BATTERY_DEFAULTS,
            _ELECTROCELL_PEM_DEFAULTS,
            _THERMAL_DEFAULTS,
            _build_electrolyser_defaults,
            _build_simulation_defaults,
        )
        from dashboard.models import Battery, ElectroCellPEM, ElectrolyserUnit, ThermalProperties, Simulation

        kind = 'PEM'
        el_defaults = _build_electrolyser_defaults(kind)
        sim_defaults = _build_simulation_defaults(kind, el_defaults)

        bat, _ = Battery.objects.get_or_create(name='Main Battery', defaults=_BATTERY_DEFAULTS)
        ec, _  = ElectroCellPEM.objects.get_or_create(name='Main Electro Cell', defaults=_ELECTROCELL_PEM_DEFAULTS)
        el, _  = ElectrolyserUnit.objects.get_or_create(name='Main Electrolyser Unit', defaults=el_defaults)
        th, _  = ThermalProperties.objects.get_or_create(name='Main Thermal Properties', defaults=_THERMAL_DEFAULTS)

        sim, _ = Simulation.objects.get_or_create(name='Main Model', defaults=sim_defaults)
        sim.batteries.add(bat)
        sim.electro_cells.add(ec)
        sim.electrolyser_units.add(el)
        sim.thermal_properties.add(th)
    except Exception:
        pass  # tables may not exist yet during initial migrate; safe to swallow
