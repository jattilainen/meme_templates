# Generated by Django 3.0.10 on 2020-11-26 21:38

import django.contrib.postgres.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memeapp', '0006_auto_20201126_1807'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='embedding',
            field=django.contrib.postgres.fields.ArrayField(base_field=models.FloatField(), default=list, size=None),
        ),
    ]