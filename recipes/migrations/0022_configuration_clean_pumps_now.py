# Generated by Django 2.2.2 on 2020-04-15 18:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0021_auto_20200415_1734'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuration',
            name='clean_pumps_now',
            field=models.BooleanField(default=False, help_text='Trigger cleaning the pumps now. Tips: lift the weight module to skip to next pump'),
        ),
    ]