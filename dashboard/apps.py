from django.apps import AppConfig


class DashboardConfig(AppConfig):
    name = 'dashboard'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_seed_default_controller, sender=self)


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
