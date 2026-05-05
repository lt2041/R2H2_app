from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0020_simulationrun_xaxis_datetime'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulation',
            name='datum_date',
            field=models.DateField(
                blank=True,
                null=True,
                help_text='Start date (00:00) used as the datetime axis origin for results charts. Defaults to today if not set.',
            ),
        ),
    ]
