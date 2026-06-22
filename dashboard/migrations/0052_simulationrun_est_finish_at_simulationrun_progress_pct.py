from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0051_simulationrun_progress_checkpoints'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulationrun',
            name='progress_pct',
            field=models.IntegerField(
                blank=True,
                null=True,
                help_text='Last recorded percent complete (0–100); persisted so the UI can show a meaningful progress bar immediately on page load/reload.',
            ),
        ),
        migrations.AddField(
            model_name='simulationrun',
            name='est_finish_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='Last server-computed estimated finish time; persisted so the UI can show an ETA immediately on page load/reload.',
            ),
        ),
    ]
