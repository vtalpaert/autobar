# Generated by Django 2.1 on 2018-09-14 21:26

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0009_auto_20180914_2023'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='dose',
            name='required',
        ),
    ]
