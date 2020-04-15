# Generated by Django 2.2.2 on 2020-04-15 13:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0018_auto_20200414_2101'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='show_only_verified_mixes',
            field=models.BooleanField(default=True),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Init'), (1, 'Press button to start'), (2, 'Serving'), (3, 'Finished'), (4, 'Abandon')], default=0),
        ),
    ]
