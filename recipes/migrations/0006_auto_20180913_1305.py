# Generated by Django 2.1 on 2018-09-13 13:05

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('recipes', '0005_dose_required'),
    ]

    operations = [
        migrations.AddField(
            model_name='ingredient',
            name='added_separately',
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name='dispenser',
            name='ingredient',
            field=models.ForeignKey(limit_choices_to={'added_separately': False}, null=True, on_delete=django.db.models.deletion.SET_NULL, to='recipes.Ingredient'),
        ),
    ]
