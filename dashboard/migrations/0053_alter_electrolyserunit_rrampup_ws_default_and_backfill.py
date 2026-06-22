from django.db import migrations, models


NEW_RAMP_UP = 5.0e5
OLD_RAMP_UP = 2.05e5


def set_ramp_up_forward(apps, schema_editor):
    ElectrolyserUnit = apps.get_model('dashboard', 'ElectrolyserUnit')
    ElectrolyserUnit.objects.update(rRampUp_W_s=NEW_RAMP_UP)


def set_ramp_up_backward(apps, schema_editor):
    ElectrolyserUnit = apps.get_model('dashboard', 'ElectrolyserUnit')
    ElectrolyserUnit.objects.update(rRampUp_W_s=OLD_RAMP_UP)


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0052_simulationrun_est_finish_at_simulationrun_progress_pct'),
    ]

    operations = [
        migrations.AlterField(
            model_name='electrolyserunit',
            name='rRampUp_W_s',
            field=models.FloatField(
                blank=True,
                default=NEW_RAMP_UP,
                help_text='Positive ramp rate limit for the electrolyser',
                null=True,
            ),
        ),
        migrations.RunPython(set_ramp_up_forward, set_ramp_up_backward),
    ]
