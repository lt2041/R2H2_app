"""Management command: ensure_default_controller

Creates the built-in default Controller DB record (and seeds the physical
.py file) if it does not already exist.  Safe to run multiple times.

Usage
-----
  python manage.py ensure_default_controller

Typical install hook – add to post-migrate signal or run once after
'python manage.py migrate'.
"""
from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Ensure the default_controller.py Controller record exists in the database.'

    def handle(self, *args, **options):
        from dashboard.models import Controller
        from r2h2.config import get_controllers_dir

        # get_controllers_dir() seeds the file on first call
        ctrl_dir = get_controllers_dir()
        default_path = ctrl_dir / 'default_controller.py'

        ctrl, created = Controller.objects.get_or_create(
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

        if created:
            self.stdout.write(self.style.SUCCESS(
                f'Created Controller record: {ctrl}  (file: {default_path})'
            ))
        else:
            self.stdout.write(
                f'Default controller already present: {ctrl}  (file: {default_path})'
            )
