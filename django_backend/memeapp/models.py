from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.conf import settings

import os

from uuid import uuid4

import schedule


def path_and_rename_template(instance, filename):
    # path to MEDIA will be added automatically
    upload_to = settings.TEMPLATES_FOLDER
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = '{}.{}'.format(instance.pk, ext)
    else:
        # set filename as random string
        filename = '{}.{}'.format(uuid4().hex, ext)
    # return the whole path to the file
    return os.path.join(upload_to, filename)

class Template(models.Model):
    image = models.ImageField(upload_to=path_and_rename_template, default=None)
    published_on = models.DateTimeField(auto_now_add=True)
    # current - meme is new until it is liked in user based approach
    text = models.CharField(max_length=settings.TEXT_MAX_LEN, default="")
    telegram_id = models.CharField(max_length=200)
