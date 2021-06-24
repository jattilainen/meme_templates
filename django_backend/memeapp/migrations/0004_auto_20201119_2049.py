# Generated by Django 3.1.1 on 2020-11-19 20:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('memeapp', '0003_profile_tg_login'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='meme',
            name='path',
        ),
        migrations.AddField(
            model_name='meme',
            name='checked',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='meme',
            name='image',
            field=models.ImageField(default=None, upload_to='memes'),
        ),
    ]
