# Generated by Django 3.1.4 on 2021-01-19 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memeapp', '0029_auto_20210119_1020'),
    ]

    operations = [
        migrations.AddField(
            model_name='logreaction',
            name='responded_recommend_detail',
            field=models.IntegerField(default=-1),
        ),
        migrations.AlterField(
            model_name='logreaction',
            name='reacted_recommend_detail',
            field=models.IntegerField(default=-1),
        ),
    ]
