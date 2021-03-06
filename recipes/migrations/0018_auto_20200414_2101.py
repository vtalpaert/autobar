# Generated by Django 2.2.2 on 2020-04-14 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0017_auto_20190407_1944'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='ingredient',
            options={},
        ),
        migrations.AddField(
            model_name='order',
            name='doses_served',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='order',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Init'), (1, 'Press button to start'), (2, 'Serving'), (3, 'Done'), (4, 'Abandon')], default=0),
        ),
    ]
