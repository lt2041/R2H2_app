from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0019_simulation_duration_days'),
    ]

    operations = [
        migrations.AddField(
            model_name='simulationrun',
            name='xaxis_datetime',
            field=models.BooleanField(
                default=True,
                help_text='Display results charts with a datetime x-axis (False = hours index).',
            ),
        ),
    ]
