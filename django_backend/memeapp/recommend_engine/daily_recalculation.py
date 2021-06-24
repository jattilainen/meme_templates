from memeapp.models import ProfileMeme, Meme, Profile
import json
from django.conf import settings
from django.db.models import Max
from memeapp.choices import LIKE, DISLIKE, APPROVED, ON_REVIEW, RECOMMEND_ERROR, RECOMMEND_START, AUTHOR_LIKE
from memeapp.getters import get_memes_visual_embeddings, get_memes_text_embeddings, get_memes_text_pca, get_memes_visual_pca
from sklearn.decomposition import PCA
from sklearn.preprocessing import QuantileTransformer
import pickle as pkl

import scipy
import implicit
import time
import logging
import numpy as np

logger = logging.getLogger("memerecommend")


def recalculate_content_pca(memes):
    print('in2')
    memes_rus = list()
    memes_en = list()
    memes_all = list()
    for meme in memes:
        if meme.checked != APPROVED:
            continue
        if meme.lang == 'rus':
            memes_rus.append(meme.pk)
        elif meme.lang == 'en':
            memes_en.append(meme.pk)
        memes_all.append(meme.pk)

    visual = get_memes_visual_embeddings(memes_all)
    text_rus = get_memes_text_embeddings(memes_rus)
    text_en = get_memes_text_embeddings(memes_en)
    model_vis = PCA(n_components=settings.VISUAL_PCA_SIZE)
    model_txt_rus = PCA(n_components=settings.TEXT_PCA_SIZE)
    model_txt_en = PCA(n_components=settings.TEXT_PCA_SIZE)
    visual_pca = model_vis.fit_transform(visual)
    text_pca_rus = model_txt_rus.fit_transform(text_rus)
    text_pca_en = model_txt_en.fit_transform(text_en)
    pos_rus = 0
    pos_en = 0
    pos_visual = 0
    for i in range(len(memes)):
        if memes[i].checked != APPROVED:
            continue
        memes[i].visual_pca = visual_pca[pos_visual].tolist()
        pos_visual += 1
        if memes[i].lang == 'rus':
            memes[i].text_pca = text_pca_rus[pos_rus].tolist()
            pos_rus += 1
        elif memes[i].lang == 'en':
            memes[i].text_pca = text_pca_en[pos_en].tolist()
            pos_en += 1
        memes[i].save()
    pkl.dump(model_vis, open(settings.VIS_PCA_PATH, "wb"))
    pkl.dump(model_txt_rus, open(settings.TEXT_PCA_PATH_RUS, "wb"))
    pkl.dump(model_txt_en, open(settings.TEXT_PCA_PATH_EN, "wb"))


def recalculate_quantile(memes):
    memes_rus = list()
    memes_en = list()
    memes_all = list()
    for meme in memes:
        if meme.checked != APPROVED:
            continue
        if meme.lang == 'rus':
            memes_rus.append(meme.pk)
        elif meme.lang == 'en':
            memes_en.append(meme.pk)
        memes_all.append(meme.pk)
    recalc_rus = np.random.choice(memes_rus, settings.QUANT_FIT_NUM, replace=False)
    recalc_en = np.random.choice(memes_en, settings.QUANT_FIT_NUM, replace=False)
    recalc_vis = np.random.choice(memes_all, settings.QUANT_FIT_NUM, replace=False)
    embeddings_rus = get_memes_text_pca(recalc_rus)
    embeddings_en = get_memes_text_pca(recalc_en)
    embeddings_vis = get_memes_visual_pca(recalc_vis)
    dists_rus = ((embeddings_rus[:, None] - embeddings_rus[None, :]) ** 2).sum(2).flatten()
    dists_en = ((embeddings_en[:, None] - embeddings_en[None, :]) ** 2).sum(2).flatten()
    dists_vis = ((embeddings_vis[:, None] - embeddings_vis[None, :]) ** 2).sum(2).flatten()
    qt_rus = QuantileTransformer(output_distribution='normal')
    qt_en = QuantileTransformer(output_distribution='normal')
    qt_vis = QuantileTransformer(output_distribution='normal')
    qt_rus.fit(np.array(dists_rus).reshape(-1, 1))
    qt_en.fit(np.array(dists_en).reshape(-1, 1))
    qt_vis.fit(np.array(dists_vis).reshape(-1, 1))
    pkl.dump(qt_rus, open(settings.PATH_TO_TEXT_RUS_QT, "wb"))
    pkl.dump(qt_en, open(settings.PATH_TO_TEXT_EN_QT, "wb"))
    pkl.dump(qt_vis, open(settings.PATH_TO_VIS_QT, "wb"))


def daily_recalculation(config_data):
    print('in')
    start = time.time()

    users = Profile.objects.all()
    max_user_pk = users.aggregate(Max('id'))['id__max']
    memes = Meme.objects.all()
    max_meme_pk = memes.aggregate(Max('id'))['id__max']
    scores = np.zeros((max_meme_pk + 1, max_user_pk + 1));

    recalculate_content_pca(memes)
    recalculate_quantile(memes)

    interactions = ProfileMeme.objects.all()
    for interaction in interactions:
        # in case new user on meme appeared after last operation
        if (interaction.meme_id > max_meme_pk or interaction.user_id > max_user_pk):
            continue
        if interaction.score == LIKE: 
            scores[interaction.meme_id][interaction.user_id] = 1
        else:
            scores[interaction.meme_id][interaction.user_id] = config_data['DailyRecalculation']['dislike_weight']
    train = scipy.sparse.coo_matrix(scores)
    # -2 for, because user bias and meme bias are added implicitly
    model = implicit.lmf.LogisticMatrixFactorization(factors=settings.DIMENSION - 2, regularization=config_data['DailyRecalculation']['regularization'])
    model.fit(train)

    user_embeddings = model.user_factors
    for user in users:
        user.embedding = user_embeddings[user.pk].tolist()
        user.save()

    meme_embeddings = model.item_factors
    for meme in memes:
        meme.embedding = meme_embeddings[meme.pk].tolist()
        meme.is_new_criteria = False
        meme.save()
     
    end = time.time()
    total_time = (end - start)
    logger.info("Recalculation is completed in {} secs".format(total_time))
