from memeapp.models import Profile, Meme, ProfileMeme
from django.utils import timezone
from django.db.models import Sum
from memeapp.choices import LIKE, DISLIKE, APPROVED, ON_REVIEW, REJECTED
import numpy as np
import datetime
from scipy.stats import binom_test
from django.db.models import Q

from collections import defaultdict

import logging
logger = logging.getLogger("memerecommend")

def get_users_embeddings(users_ids):
    if (len(users_ids) == 0):
        return np.empty(0)
    # fetch memes
    users_embeddings = dict(list(Profile.objects.filter(pk__in=list(users_ids)).values_list('pk', 'embedding')))  # dict {pk: hash}

    # declare function to map ids to embeddings
    f = np.vectorize(lambda x: np.array(users_embeddings[x]), otypes=[np.ndarray])

    # fetch their hashes
    embeddings = f(users_ids)

    return np.stack(embeddings, axis=0)


def get_memes_embeddings(memes_ids):
    if (len(memes_ids) == 0):
        return np.empty(0)
    # fetch memes
    memes_embeddings = dict(list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'embedding')))  # dict {pk: hash}

    # declare function to map ids to embeddings
    f = np.vectorize(lambda x: np.array(memes_embeddings[x]), otypes=[np.ndarray])

    # fetch their hashes
    embeddings = f(memes_ids)

    return np.stack(embeddings, axis=0)


def get_memes_hashes(memes_ids):
    # fetch memes
    memes_hashes = dict(list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'hash')))  # dict {pk: hash}

    # declare function to map ids to hashes
    f = np.vectorize(lambda x: memes_hashes[x], otypes=[str])

    # fetch their hashes
    hashes = f(memes_ids)

    return hashes


def get_memes_origins(memes_ids):
    # fetch memes
    memes_origins = dict(list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'origin')))  # dict {pk: origin}

    # declare function to map ids to origins
    f = np.vectorize(lambda x: memes_origins[x], otypes=[str])

    # fetch their hashes
    origins = f(memes_ids)

    return origins


def get_memes_stats(memes_ids):
    memes_likes = dict(list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'likes')))
    memes_views = dict(list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'watched')))

    # declare function to map ids to likes and views
    unpack_likes = np.vectorize(lambda x: memes_likes[x], otypes=[int])
    unpack_views = np.vectorize(lambda x: memes_views[x], otypes=[int])

    # fetch their likes, views
    likes = unpack_likes(memes_ids)
    views = unpack_views(memes_ids)

    return likes, views


def get_memes_langs(memes_ids):
    # fetch memes
    memes_langs = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'lang')))  # dict {pk: lang}


    # declare function to map ids to langs
    f = np.vectorize(lambda x: memes_langs[x], otypes=[str])

    return f(memes_ids)


def get_memes_visual_embeddings(memes_ids):
    if (len(memes_ids) == 0):
        return np.empty(0)
    # fetch memes
    memes_vis = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'visual_embedding')))  # dict {pk: visual}

    # declare function to map ids to visuals
    f = np.vectorize(lambda x: np.array(memes_vis[x]), otypes=[np.ndarray])

    return np.stack(f(memes_ids), axis=0)


def get_memes_visual_pca(memes_ids):
    if (len(memes_ids) == 0):
        return np.empty(0)
    # fetch memes
    memes_pca = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'visual_pca')))  # dict {pk: visual}

    # declare function to map ids to visuals
    f = np.vectorize(lambda x: np.array(memes_pca[x]), otypes=[np.ndarray])

    return np.stack(f(memes_ids), axis=0)


def get_memes_text_embeddings(memes_ids):
    if (len(memes_ids) == 0):
        return np.empty(0)
    # fetch memes
    memes_text = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'text_embedding')))  # dict {pk: text}

    # declare function to map ids to text
    f = np.vectorize(lambda x: np.array(memes_text[x]), otypes=[np.ndarray])

    return np.stack(f(memes_ids), axis=0)


def get_memes_text_pca(memes_ids):
    if len(memes_ids) == 0:
        return np.empty(0)
    # fetch memes
    text_pca = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'text_pca')))  # dict {pk: pca}

    # declare function to map ids to text
    f = np.vectorize(lambda x: np.array(text_pca[x]), otypes=[np.ndarray])

    return np.stack(f(memes_ids), axis=0)


def get_memes_published_on(memes_ids):
    # fetch memes
    memes_times = dict(
        list(Meme.objects.filter(pk__in=list(memes_ids)).values_list('pk', 'published_on')))  # dict {pk: time}

    # declare function to map ids to times
    f = np.vectorize(lambda x: memes_times[x], otypes=[datetime.datetime])

    return f(memes_ids)


def get_user_like_history(user_id: int, n=-1, langs=False, visual_pca=False, text_pca=False, exclude=None):
    # Get n last likes (n = -1 for all)
    return get_user_history(user_id, n, liked=True, checked=APPROVED, embeddings=True, ratings=False, origins=False, langs=langs,
                            visual_pca=visual_pca, text_pca=text_pca, exclude=exclude)  # ([ids], [embeddings])


def get_user_interact_history(user_id: int, n=-1):
    # Get n last interactions (n = -1 for all)
    return get_user_history(user_id, n, liked=False, checked=None, embeddings=True, ratings=True, origins=False)  # ([ids], [embeddings], [ratings])


def get_user_origins_history(user_id: int, n=-1):
    # Get n last interactions (n = -1 for all)
    return get_user_history(user_id, n, liked=False, checked=None, embeddings=False, ratings=True, origins=True)  # ([ids], [ratings], [origins])


def get_user_history(user_id: int, n=-1, liked=False, checked=None, exclude=None, embeddings=False, ratings=False, origins=False, langs=False, visual_pca=False, text_pca=False):
    # For custom queries
    # fetch users
    if n < -1:  # invalid length, throw exception
        return None
    user_list = Profile.objects.filter(pk=user_id)
    if len(user_list) == 0: # Invalid ID
        return None
    user = user_list[0]
    return_values = []  # Array of results

    # fetch liked or seen memes
    query = Q(user=user)
    if liked:
        query = query & Q(score=LIKE)
    if checked is not None:
        query = query & Q(meme__checked=checked)
    if exclude is not None:
        query = query & ~Q(meme__pk__in=exclude)
    profile_memes = ProfileMeme.objects.filter(query).order_by('-interacted_on') # minus for descending order
    # filter length of output if required
    if n != -1:
        profile_memes = profile_memes[:n]

    # get ids, embeddings and ratings
    memes_ids = np.array(profile_memes.values_list('meme__pk', flat=True))
    return_values.append(memes_ids)
    if embeddings:
        return_values.append(get_memes_embeddings(memes_ids))
    if ratings:
        return_values.append(np.array(profile_memes.values_list('score', flat=True)))
    if origins:
        return_values.append(get_memes_origins(memes_ids))
    if langs:
        return_values.append(get_memes_langs(memes_ids))
    if visual_pca:
        return_values.append(get_memes_visual_pca(memes_ids))
    if text_pca:
        return_values.append(get_memes_text_pca(memes_ids))

    # return (простите)
    if len(return_values) == 1:
        return return_values[0]
    else:
        return return_values


def get_meme_history(meme_id: int, n=-1, liked=False, embeddings=False, ratings=False):
    # For custom queries
    # fetch meme
    if n < -1:  # invalid length, throw exception
        return None

    memes_list = Meme.objects.filter(pk=meme_id)
    if len(memes_list) == 0:    # invalid ID, throw exception
        return None

    meme = memes_list[0]
    # fetch users who interacted or liked
    query = Q(meme=meme)
    if liked:
        query = query & Q(score=LIKE)
    meme_profiles = ProfileMeme.objects.filter(query).order_by('-interacted_on')  # minus for descending order

    # filter length of output if required
    if n != -1:
        meme_profiles = meme_profiles[:n]

    return_values = []  # Array of results
    # get ids, embeddings and ratings
    users_ids = np.array(meme_profiles.values_list('user__pk', flat=True))
    return_values.append(users_ids)

    if embeddings:
        return_values.append(get_users_embeddings(users_ids))

    if ratings:
        return_values.append(np.array(meme_profiles.values_list('score', flat=True)))

    # return
    if len(return_values) == 1:
        return return_values[0]
    else:
        return return_values


def get_users_history(user_ids: list, n=-1):
    users_tuple = '(%s)' % ','.join(map(str, user_ids))
    if n == -1:
        raw_query = '''select ranked_scores.* from (SELECT memeapp_ProfileMeme.*, \
        rank() OVER (PARTITION BY user_id ORDER BY interacted_on DESC) \
        FROM memeapp_ProfileMeme WHERE user_id in {}) ranked_scores \
        '''.format(users_tuple)
    else:
        raw_query = '''select ranked_scores.* from (SELECT memeapp_ProfileMeme.*, \
        rank() OVER (PARTITION BY user_id ORDER BY interacted_on DESC) \
        FROM memeapp_ProfileMeme WHERE user_id in {}) ranked_scores \
        where rank <= {}'''.format(users_tuple, n)

    from django.db import connection, transaction
    cursor = connection.cursor()
    cursor.execute(raw_query)
    profileMemes = cursor.fetchall()

    memes_ids = {}
    scores = {}
    for user_id in user_ids:
        memes_ids[user_id] = []
        scores[user_id] = []

    for p in profileMemes:
        memes_ids[p[3]].append(p[2])
        scores[p[3]].append(p[1])

    memes_ids = {k:np.array(v) for k,v in memes_ids.items()}
    scores = {k:np.array(v) for k,v in scores.items()}
    return memes_ids, scores


def get_meme_like_history(meme_id: int, n=-1):
    # get n last likes of a meme (n=-1 for all)
    return get_meme_history(meme_id, n, liked=True, embeddings=True, ratings=False)  # ([ids], [embeddings])


def get_meme_interact_history(meme_id: int, n=-1):
    # Get n last interactions (n = -1 for all)
    return get_meme_history(meme_id, n, liked=False, embeddings=True, ratings=True)  # ([ids], [embeddings], [ratings])


def get_random_memes(n: int, new=None, from_user=None, checked=None, n_last_days=None, lang=None, embeddings=False, visual_pca=False, text_pca=False, stats=False,
                     hashes=False, published_on=False):
    if n <= 0:
        raise ValueError('requested non-positive number of memes')

    # fetch memes
    query = Q()
    if not new is None:
        query = query & Q(is_new_criteria=new)
    if not from_user is None:
        if from_user:
            query = query & Q(origin__startswith="u")
        else:
            query = query & Q(origin__startswith="g")
    if n_last_days:
        cur_date_utc = timezone.now()
        n_days_ago = cur_date_utc  - timezone.timedelta(n_last_days)
        query = query & Q(published_on__range=(n_days_ago, cur_date_utc))

    if not checked is None:
        query = query & Q(checked=checked)

    if lang is not None:
        query = query & Q(lang=lang)

    memes = Meme.objects.filter(query).order_by('?')[:n]
    categories = ['pk']
    result = list()
    result.append(np.array(memes.values_list('pk', flat=True)))
    memes_ids = result[-1]
    if embeddings:
        result.append(get_memes_embeddings(memes_ids))
    if stats:
        stats = get_memes_stats(memes_ids)
        result.append(stats[0])
        result.append(stats[1])
    if hashes:
        result.append(get_memes_hashes(memes_ids))
    if published_on:
        result.append(get_memes_published_on(memes_ids))
    if visual_pca:
        result.append(get_memes_visual_pca(memes_ids))
    if text_pca:
        result.append(get_memes_text_pca(memes_ids))
    if len(result) == 0:
        return [np.zeros(0)] * len(categories)
    if len(result) > 1:
        return result
    return result[0]


def get_random_users(n: int, embeddings=False):
    if n <= 0:
        # throw Exception
        return None

    # fetch users
    users = np.array(Profile.objects.all().order_by('?')[:n].values_list('pk', flat=True))
    if embeddings:
        return users, get_users_embeddings(users)
    return users


def get_oldest_on_review():
    # Get meme
    memes = Meme.objects.filter(checked=ON_REVIEW).order_by('published_on')
    if len(memes) == 0:
        return -1
    return memes[0].pk


def get_on_review_count():
    return Meme.objects.filter(checked=ON_REVIEW).count()

def get_origin_on_review_count(origin):
    return Meme.objects.filter(checked=ON_REVIEW).filter(origin=origin).count()


def get_last_memes_from_origin(origin: str, n=-1):
    if n != -1:
        memes = Meme.objects.filter(checked=APPROVED, origin=origin).order_by('published_on')[:n].values_list('pk', flat=True)
    else:
        memes = Meme.objects.filter(checked=APPROVED, origin=origin).values_list('pk', flat=True)

    memes = np.array(memes)
    return memes, get_memes_embeddings(memes)

def get_users_count():
    return Profile.objects.count()

def get_memes_count():
    return Meme.objects.count()

def get_total_views():
    return Meme.objects.aggregate(Sum('watched'))['watched__sum']

def get_total_likes():
    return Meme.objects.aggregate(Sum('likes'))['likes__sum']

def get_user_views(user_id):
    return ProfileMeme.objects.filter(user__pk=user_id).count()

def get_user_likes(user_id):
    return ProfileMeme.objects.filter(user__pk=user_id, score=LIKE).count()

def get_uploaded_count(origin):
    return Meme.objects.filter(origin=origin).count()

def get_uploaded_views(origin):
    return Meme.objects.filter(origin=origin).aggregate(Sum('watched'))['watched__sum']

def get_uploaded_likes(origin):
    return Meme.objects.filter(origin=origin).aggregate(Sum('likes'))['likes__sum']

def get_uploaded_max_liked(origin):
    meme = Meme.objects.filter(origin=origin).order_by('-likes').first()
    if (meme is None):
        return -1, -1
    return meme.pk, meme.likes

def get_all_users():
    return list(Profile.objects.all().values_list('pk', 'telegram_id'))

def get_meme_of_the_day():
    query = Q()
    query = query & Q(checked=APPROVED)

    cur_date_utc = timezone.now()
    cur_date_utc_clean = cur_date_utc.replace(minute=0, second=0, microsecond=0)
    yesterday_utc_clean = cur_date_utc_clean - timezone.timedelta(10000)
    query = query & Q(published_on__range=(yesterday_utc_clean, cur_date_utc_clean))
    all_memes = Meme.objects.filter(query)
    min_val = 1 + 1e-1
    best_meme = -1
    cnt = 0
    for meme in all_memes:
        cnt += 1
        binom_test_result = binom_test(meme.likes, meme.watched, 0.5, 'greater')
        if binom_test_result < min_val:
            min_val = binom_test_result
            best_meme = meme
    return best_meme, cnt

def has_user_seen_meme(user_id, meme_id):
    return ProfileMeme.objects.filter(user__pk=user_id, meme__pk=meme_id).count() > 0

def does_nickname_exist(text):
    return Profile.objects.filter(nickname=text).count() > 0

def get_origin_nth_meme(origin, n):
    return Meme.objects.filter(origin=origin).order_by('-published_on')[n]

def get_origin_range_memes_stats(origin, start, end):
    memes = Meme.objects.filter(origin=origin).order_by('-published_on')[start:end].values_list('pk', 'likes', 'watched', 'checked')
    result = list(map(lambda x: np.array(x), zip(*memes)))
    return result

def get_n_uploads_a_day(origin):
    start_day = timezone.now().replace(hour=0, minute=0, second=0)
    end_day = timezone.now().replace(hour=23, minute=59, second=59)
    time_left_type = 'hours'
    time_left = 24 - timezone.now().hour
    if time_left == 1:
        time_left = 60 - timezone.now().minute
        time_left_type = 'minutes'
    return Meme.objects.filter(origin=origin, published_on__gte=start_day, published_on__lte=end_day).count(), time_left, time_left_type

def get_origin_meme_by_hash(origin, hash):
    ids = Meme.objects.filter(origin=origin, hash=hash).values_list('pk', flat=True)
    if (len(ids) > 0):
        return ids[0]
    return -1
