from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0050_rename_fkt_battery_rkt_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulationrun',
            name='progress_checkpoints',
            field=models.JSONField(
                blank=True,
                default=list,
                help_text='List of {"t": <epoch_float>, "h": <sim_hours_done>} snapshots used to compute a robust ETA that is resilient to hibernation.',
            ),
        ),
    ]
