from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0028_alter_battery_fkt'),
    ]

    operations = [
        migrations.RenameField(
            model_name='battery',
            old_name='rControlMinSoC',
            new_name='rControlTargetSoC',
        ),
    ]
