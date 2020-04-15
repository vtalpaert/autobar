# Generated by Django 2.2.2 on 2020-04-15 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0020_auto_20200415_1628'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='weight_cell_gain',
            field=models.SmallIntegerField(choices=[(32, 32), (64, 64), (128, 128)], default=128, help_text='Gain 32 is only for channel B, others for channel A'),
        ),
        migrations.AddField(
            model_name='configuration',
            name='weight_module_delay_measure',
            field=models.FloatField(default=0.02, help_text='[s] length of time between two weight measures, try to keep it between 10 and 100Hz'),
        ),
        migrations.AddField(
            model_name='configuration',
            name='weight_module_queue_length',
            field=models.SmallIntegerField(default=10, help_text='Weight is the median on X samples'),
        ),
        migrations.AlterField(
            model_name='configuration',
            name='weight_cell_channel',
            field=models.CharField(choices=[('A', 'A'), ('B', 'B')], default='A', max_length=1),
        ),
    ]