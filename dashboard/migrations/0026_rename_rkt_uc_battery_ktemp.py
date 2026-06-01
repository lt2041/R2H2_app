from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0025_controller_filename_to_filefield'),
    ]

    operations = [
        migrations.RenameField(
            model_name='battery',
            old_name='rKT_uc',
            new_name='KTemp',
        ),
    ]
