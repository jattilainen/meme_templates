from django.conf import settings
from django.core.files import File
from memeapp.models import Meme
from memeapp.choices import ON_REVIEW, APPROVED
from memeapp.getters import get_origin_meme_by_hash

from shutil import copyfile
import PIL.Image
import os
import imagehash
import numpy as np


def check_image(image_path):
    image = PIL.Image.open(image_path)
    width, height = image.size
    image_size = os.stat(image_path).st_size
    if (width > settings.MAX_WIDTH_PROPORTION * height):
        return False, settings.TOO_WIDE_ERROR
    if (height > settings.MAX_HEIGHT_PROPORTION * width):
        return False, settings.TOO_HIGH_ERROR
    if (image_size > settings.MAX_IMAGE_SIZE):
        return False, settings.TOO_LARGE_ERROR
    return True, 0

def generate_hash(image_path):
    image = PIL.Image.open(image_path)
    return imagehash.phash(image)


def create_meme(image_path, prechecked, origin, start=-1):
    is_valid, code = check_image(image_path)
    if not is_valid:
        return code
    
    current_meme_id = get_origin_meme_by_hash(origin, generate_hash(image_path))
    if current_meme_id != -1:
        return -current_meme_id

    # until image is uploaded meme is ON_REVIEW
    new_image = Meme.objects.create(
        checked=ON_REVIEW,
        hash=generate_hash(image_path),
        start=start,
        origin=origin,
    )
    try:
        new_image.image.save(image_path, File(open(image_path, "rb")))
        # we can set checked True only here to avoid showing it before
        new_image.checked = prechecked
        new_image.save()
        return new_image.pk
    except:
        new_image.delete()
        return settings.UNKNOWN_UPLOAD_ERROR

def set_start_meme(image_path, start):
    if start < 0:
        return settings.UNKNOWN_UPLOAD_ERROR
    is_valid, code = check_image(image_path)
    if not is_valid:
        return code

    start_cnt = Meme.objects.filter(start=start).count()
    if start_cnt > 1:
        print("There is more than 1 meme with start={}".format(start))
        return settings.UNKNOWN_UPLOAD_ERROR

    if start_cnt == 0:
        new_image = Meme.objects.create(
            checked=APPROVED,
            hash=generate_hash(image_path),
            start=start,
            origin="start",
        )
        try:
            new_image.image.save(image_path, File(open(image_path, "rb")))
            new_image.save()
            return new_image.pk
        except:
            new_image.delete()
            return settings.UNKNOWN_UPLOAD_ERROR
    else:
        start_meme = Meme.objects.get(start=start)
        start_meme.hash = generate_hash(image_path)
        try:
            start_meme.image.save(image_path, File(open(image_path, "rb")))
            start_meme.save()
            return start_meme.pk
        except:
            start_meme.delete()
            return settings.UNKNOWN_UPLOAD_ERROR
