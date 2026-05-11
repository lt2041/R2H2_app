"""
Migration 0025 – convert Controller.filename (CharField) to Controller.file (FileField).

Both CharField and FileField map to VARCHAR in the database, so no actual schema
change is needed.  We use SeparateDatabaseAndState to update only Django's
migration state while leaving the DB column ('filename') untouched.
"""

import django.db.models.deletion
from django.db import migrations, models


def _controller_storage():
    """Same deferred storage used by the model field."""
    from django.core.files.storage import FileSystemStorage
    from r2h2.config import get_controllers_dir
    return FileSystemStorage(location=str(get_controllers_dir()), base_url=None)


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0024_controller_edit_history'),
    ]

    operations = [
        # No DB work needed — VARCHAR column 'filename' stays as-is.
        # We only need to update Django's internal schema state so that:
        #   1. The Python attribute is renamed from 'filename' → 'file'
        #   2. The field type is recorded as FileField (still backed by the
        #      same VARCHAR column via db_column='filename')
        migrations.SeparateDatabaseAndState(
            database_operations=[],   # zero DB changes
            state_operations=[
                migrations.RenameField(
                    model_name='controller',
                    old_name='filename',
                    new_name='file',
                ),
                migrations.AlterField(
                    model_name='controller',
                    name='file',
                    field=models.FileField(
                        db_column='filename',
                        help_text='The .py controller file stored in <data_root>/controllers/. '
                                  'Upload here or create/edit via the simulation editor.',
                        storage=_controller_storage,
                        unique=True,
                        upload_to='',
                    ),
                ),
            ],
        ),
    ]
