# Generated by Django 2.1 on 2018-09-13 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0004_mix_image'),
    ]

    operations = [
        migrations.AddField(
            model_name='dose',
            name='required',
            field=models.BooleanField(default=True),
        ),
    ]
