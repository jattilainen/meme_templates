from memeapp.models import Profile, Meme, ProfileMeme
from memeapp.choices import APPROVED, REJECTED
from django.conf import settings


def set_user_embedding(user_id: int, user_embedding):
    user_list = Profile.objects.filter(pk=user_id)
    if len(user_list) == 0:
        # throw exception
        return None

    user = user_list[0]
    user.embedding = list(user_embedding)
    user.save()


def set_meme_embedding(meme_id: int, meme_embedding):
    meme_list = Profile.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    meme.embedding = list(meme_embedding)
    meme.save()


def set_meme_text_data(meme_id: int, text, lang, text_embedding):
    meme_list = Meme.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    meme.text = text[:settings.TEXT_MAX_LEN]
    meme.lang = lang
    meme.text_embedding = text_embedding.tolist()
    meme.save()


def set_meme_visual_embedding(meme_id: int, visual_embedding):
    meme_list = Meme.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    meme.visual_embedding = visual_embedding.tolist()
    meme.save()


def set_moderation_result(meme_id: int, approved):
    meme_list = Meme.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    if approved:
        meme.checked = APPROVED
    else:
        meme.checked = REJECTED
    meme.save()


def set_meme_visual_pca(meme_id: int, visual_pca):
    meme_list = Meme.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    meme.visual_pca = visual_pca.tolist()
    meme.save()


def set_meme_text_pca(meme_id: int, text_pca):
    meme_list = Meme.objects.filter(pk=meme_id)
    if len(meme_list) == 0:
        # throw exception
        return None

    meme = meme_list[0]
    meme.text_pca = text_pca.tolist()
    meme.save()