import numpy as np

from memeapp.models import ProfileMeme, Meme, Profile
from django.db.models import F
import json
from django.conf import settings
from memeapp.choices import LIKE, DISLIKE, APPROVED, ON_REVIEW, RECOMMEND_ERROR, RECOMMEND_START, AUTHOR_LIKE
from memeapp.creators import create_meme
from memeapp.origin_manager import is_meme_from_user, is_meme_from_group, get_id_by_origin
from memeapp.getters import has_user_seen_meme, get_random_memes, get_memes_visual_pca, get_memes_text_pca
from memeapp.setters import set_meme_text_data, set_meme_visual_embedding, set_meme_visual_pca, set_meme_text_pca, set_meme_embedding
import logging
from memeapp.preprocessing.visual_embeddings import get_visual_embedding
from memeapp.preprocessing.text_embeddings import get_text_and_embedding
import pickle as pkl

logger = logging.getLogger("memerecommend")

def reaction_to_rating(reaction):
        if reaction == 'like':
            return LIKE
        elif reaction == 'dislike':
            return DISLIKE

def is_positive(rating):
    return rating > 0

# def get_start_meme(index):


def get_next_meme(user_id, start=-1):
    if start >= settings.N_START_MEMES:
        meme_id, recommend_details = settings.recommend_engine.inference(user_id)
    else:
        meme_id_set = Meme.objects.filter(start=start)
        logger.info("start_selected {}".format(start))
        start += 1
        if len(meme_id_set) == 0:
            recommend_details = RECOMMEND_ERROR
        else:
            meme_id = meme_id_set[0].id
            recommend_details = RECOMMEND_START
    if (recommend_details == RECOMMEND_ERROR):
        logger.info("meme_not_found {}".format(user_id))
        return RECOMMEND_ERROR, RECOMMEND_ERROR, start
    return meme_id, recommend_details, start


def submit_reaction(user_id, meme_id, reaction, recommend_details):
    if has_user_seen_meme(user_id, meme_id):
        logger.warning("reaction_repeated {} {} {} {}".format(user_id, meme_id, reaction, recommend_details))
        return

    rating = reaction_to_rating(reaction)
    meme_list = Meme.objects.filter(pk=meme_id)
    if (len(meme_list) == 0):
        logger.error("reaction_for_unknown_meme {} {} {} {}".format(user_id, meme_id, reaction, recommend_details))
        return
    meme = meme_list[0]

    user_list = Profile.objects.filter(pk=user_id)
    if (len(user_list) == 0):
        logger.error("reaction_from_unknown_user {} {} {} {}".format(user_id, meme_id, reaction, recommend_details))
        return
    user = user_list[0]

    profile_meme = ProfileMeme.objects.create(
            user=user,
            meme=meme,
            score=rating)
    if recommend_details != AUTHOR_LIKE:
        # avoiding race condition
        meme.watched = F('watched') + 1
        if (is_positive(rating)):
            meme.likes = F('likes') + 1
        meme.save(update_fields=['watched', 'likes', 'is_new_criteria'])
    # settings.recommend_engine.process_reaction(user_id, meme_id, rating)
    logger.info("reaction_submitted {} {} {} {}".format(user_id, meme_id, reaction, recommend_details))


def process_new_meme(image_path, origin):
    if is_meme_from_user(origin):
        code = create_meme(image_path, prechecked=ON_REVIEW, origin=origin)
        if code > 0:
            submit_reaction(user_id=get_id_by_origin(origin), meme_id=code, reaction='like', recommend_details=AUTHOR_LIKE)
    elif is_meme_from_group(origin):
        code = create_meme(image_path, prechecked=APPROVED, origin=origin)
    return code


def approved_processing(meme_id):
    model_pca_visual = pkl.load(open(settings.VIS_PCA_PATH, 'rb'))
    model_pca_text_rus = pkl.load(open(settings.TEXT_PCA_PATH_RUS, 'rb'))
    model_pca_text_en = pkl.load(open(settings.TEXT_PCA_PATH_EN, 'rb'))
    meme = Meme.objects.get(pk=meme_id)
    path = meme.image.path
    visual_embedding = get_visual_embedding(path)
    text, lang, text_embedding = get_text_and_embedding(path)
    visual_pca = model_pca_visual.transform(np.array([visual_embedding]))[0]
    if lang == 'en':
        text_pca = model_pca_text_en.transform(np.array([text_embedding]))[0]
    elif lang == 'rus':
        text_pca = model_pca_text_rus.transform(np.array([text_embedding]))[0]

    random_memes, random_embeddings = get_random_memes(2000, lang=meme.lang, embeddings=True)
    random_vis = get_memes_visual_pca(random_memes)
    random_text = get_memes_text_pca(random_memes)
    dist = settings.recommend_engine.context_distance(visual_pca, text_pca, random_vis, random_text, meme.lang)

    _, closest_embeddings = settings.recommend_engine.get_k_largest_by_marks(
        random_memes,
        5,
        -dist,
        extra=random_embeddings)
    average_embedding = np.mean(closest_embeddings, axis=1)

    set_meme_embedding(meme_id, average_embedding)

    set_meme_text_data(meme_id, text, lang, text_embedding)
    set_meme_visual_embedding(meme_id, visual_embedding)
    set_meme_visual_pca(meme_id, visual_pca)
    set_meme_text_pca(meme_id, text_pca)


