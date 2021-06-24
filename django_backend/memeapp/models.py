from django.db import models
from django.contrib.auth.models import User
from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.postgres.fields import ArrayField
from django.conf import settings

from memeapp.choices import SCORE_CHOICES, CHECKED_CHOICES
from memeapp.recommend_engine.embedding_generator import default_meme_embedding, default_user_embedding, default_visual_pca, default_text_pca
from memeapp.preprocessing.text_embeddings import default_text_embedding
from memeapp.preprocessing.visual_embeddings import default_visual_embedding

import os

import logging
logger = logging.getLogger("memerecommend")

from uuid import uuid4

import schedule

# have to keep it because it presents in django transactions
def path_and_rename(instance, filename):
    pass

def path_and_rename_meme(instance, filename):
    # path to MEDIA will be added automatically
    upload_to = settings.MEMES_FOLDER
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = '{}.{}'.format(instance.pk, ext)
    else:
        # set filename as random string
        logger.error("image_upload_without_pk")
        filename = '{}.{}'.format(uuid4().hex, ext)
    # return the whole path to the file
    return os.path.join(upload_to, filename)

# small copy-paste here
def path_and_rename_template(instance, filename):
    # path to MEDIA will be added automatically
    upload_to = settings.TEMPLATES_FOLDER
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = '{}.{}'.format(instance.pk, ext)
    else:
        # set filename as random string
        logger.error("image_upload_without_pk")
        filename = '{}.{}'.format(uuid4().hex, ext)
    # return the whole path to the file
    return os.path.join(upload_to, filename)

class Meme(models.Model):
    image = models.ImageField(upload_to=path_and_rename_meme, default=None)
    checked = models.IntegerField(default=0, choices=CHECKED_CHOICES)
    embedding = ArrayField(models.FloatField(), default=default_meme_embedding)
    published_on = models.DateTimeField(auto_now_add=True)
    # current - meme is new until it is liked in user based approach
    is_new_criteria = models.BooleanField(default=True)
    watched = models.IntegerField(default=0)
    likes = models.IntegerField(default=0)
    hash = models.CharField(max_length=20, default="")
    # 'Profile' instead of Profile because it is later in file
    origin = models.CharField(max_length=20, default="")
    start = models.IntegerField(default=-1)
    class Meta:
        indexes = [
            models.Index(fields=['origin']),
            models.Index(fields=['checked']),
            models.Index(fields=['published_on']),
        ]
    text = models.CharField(max_length=settings.TEXT_MAX_LEN, default="")
    lang = models.CharField(max_length=5, default="rus")
    text_embedding = ArrayField(models.FloatField(), default=default_text_embedding)
    visual_embedding = ArrayField(models.FloatField(), default=default_visual_embedding)
    visual_pca = ArrayField(models.FloatField(), default=default_visual_pca)
    text_pca = ArrayField(models.FloatField(), default=default_text_pca)


class Profile(models.Model):
    # auth_user = models.OneToOneField(User, on_delete=models.CASCADE)
    memes = models.ManyToManyField(Meme, through='ProfileMeme')
    embedding = ArrayField(models.FloatField(), default=default_user_embedding)
    telegram_id = models.PositiveIntegerField(
        unique=True,
        default=0,
    )
    start = models.IntegerField(default=-1)
    rejected = models.IntegerField(default=0)
    nickname = models.CharField(max_length=20, default="")
    class Meta:
        indexes = [
            models.Index(fields=['nickname']),
        ]

# decorators are required to save/update our Profile model
# when Django model is saved/updated

# @receiver(post_save, sender=User)
# def create_user_profile(sender, instance, created, **kwargs):
#     if created:
#         Profile.objects.create(auth_user=instance)
#
#
# @receiver(post_save, sender=User)
# def save_user_profile(sender, instance, **kwargs):
#     instance.profile.save()


class ProfileMeme(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE)
    meme = models.ForeignKey(Meme, on_delete=models.CASCADE)
    score = models.IntegerField(choices=SCORE_CHOICES)
    interacted_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['meme']),
            models.Index(fields=['interacted_on']),
        ]


class LogReaction(models.Model):
    user_id = models.IntegerField()
    meme_id = models.IntegerField()
    score = models.IntegerField(choices=SCORE_CHOICES)
    timestamp = models.DateTimeField(auto_now_add=True)
    reacted_recommend_detail = models.IntegerField(default=-1)
    responded_recommend_detail = models.IntegerField(default=-1)
    response_time = models.IntegerField()

class Invite(models.Model):
    user_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    link = models.CharField(max_length=100, default="no_link")


class Template(models.Model):
    image = models.ImageField(upload_to=path_and_rename_template, default=None)
    published_on = models.DateTimeField(auto_now_add=True)
    # current - meme is new until it is liked in user based approach
    text = models.CharField(max_length=settings.TEXT_MAX_LEN, default="")
    telegram_id = models.CharField(max_length=200)


class LogInline(models.Model):
    user_id = models.IntegerField()
    template_id = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    response_time = models.IntegerField()
