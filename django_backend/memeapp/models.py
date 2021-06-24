from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings

import os

from uuid import uuid4

import schedule

class Template(models.Model):
    image = models.ImageField(upload_to=path_and_rename_template, default=None)
    published_on = models.DateTimeField(auto_now_add=True)
    # current - meme is new until it is liked in user based approach
    text = models.CharField(max_length=settings.TEXT_MAX_LEN, default="")
    telegram_id = models.CharField(max_length=200)
