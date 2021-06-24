import numpy as np
from memeapp.getters import get_random_memes, get_random_users, get_users_embeddings, get_user_history, get_memes_embeddings, get_meme_history, get_meme_interact_history, get_user_like_history, get_user_interact_history, get_memes_hashes, get_memes_stats, get_users_history, get_user_origins_history,  get_last_memes_from_origin, get_user_likes, get_user_views
from memeapp.origin_manager import get_user_origin
from django.conf import settings
from django.utils import timezone
from memeapp.choices import APPROVED, LIKE, DISLIKE, USER_BASED, ITEM_BASED, RANDOM_RECOMMEND, ORIGIN_BASED, TOP_DAY_BASED, N_LAST_DAYS_RANDOM, TOP_BASED
from scipy.stats import binom_test
import time
import pickle as pk
from sklearn.preprocessing import QuantileTransformer

import logging
logger = logging.getLogger("memerecommend")


def cosine_similarity(source_embedding, target_embeddings):
    if len(target_embeddings) == 0:
        return np.empty()
    similarity = np.dot(target_embeddings, source_embedding)
    target_norms = np.sqrt(np.sum(target_embeddings ** 2, axis=1))
    source_norm = np.sqrt(np.sum(source_embedding ** 2))
    similarity /= target_norms
    similarity /= source_norm
    return similarity


def euclidean_distance(source_embedding, target_embeddings):
    return ((target_embeddings - source_embedding) ** 2).sum(1)


class RecommendEngine:
    def __init__(self,
                 n_users_first_stage,
                 n_users_second_stage,
                 n_memes_from_users_to_compare,
                 min_recall_threshold,
                 n_memes_from_nearest_users,
                 n_memes_to_get_user_based,
                 n_random_users_to_try_user_based,
                 n_last_liked_memes_from_user,
                 n_memes_from_our_meme,
                 n_memes_to_get_item_based,
                 n_random_memes_to_try_item_based,
                 n_last_memes_to_choose_origin,
                 n_memes_from_origin_to_choose,
                 n_memes_to_get_origin_based,
                 n_memes_to_try_random_based,
                 n_memes_to_get_random_based,
                 n_memes_pool_top_day,
                 n_memes_for_binom_top_day,
                 n_memes_to_get_top_day_based,
                 n_memes_to_try_n_last_days_random_based,
                 n_memes_to_get_n_last_days_random_based,
                 n_last_days_random,
                 random_priority_power,
                 methods_probs
                ):
        # print(getattr(models, model_name))
        # self.model = getattr(models, model_name)(**model_params)
        self.embedding_size = settings.DIMENSION

        self.methods_probs = methods_probs

        # user_based_inference params
        self.n_users_first_stage = n_users_first_stage
        self.n_users_second_stage = n_users_second_stage
        self.n_memes_from_users_to_compare = n_memes_from_users_to_compare
        self.min_recall_threshold = min_recall_threshold
        self.n_memes_from_nearest_users = n_memes_from_nearest_users
        self.n_memes_to_get_user_based = n_memes_to_get_user_based
        self.n_random_users_to_try_user_based = n_random_users_to_try_user_based

        # item_based_inference params
        self.n_last_liked_memes_from_user = n_last_liked_memes_from_user
        self.n_memes_from_our_meme = n_memes_from_our_meme
        self.n_memes_to_get_item_based = n_memes_to_get_item_based
        self.n_random_memes_to_try_item_based = n_random_memes_to_try_item_based

        # origin_based_inference params
        self.n_last_memes_to_choose_origin = n_last_memes_to_choose_origin
        self.n_memes_from_origin_to_choose = n_memes_from_origin_to_choose
        self.n_memes_to_get_origin_based = n_memes_to_get_origin_based

        # random_based_inference params
        self.n_memes_to_try_random_based = n_memes_to_try_random_based
        self.n_memes_to_get_random_based = n_memes_to_get_random_based
        self.n_views_to_be_confident_in_meme = 5
        self.n_chances_to_find_new_memes = 10

        # top_day_based_inference params
        self.n_memes_pool_top_day = n_memes_pool_top_day
        self.n_memes_for_binom_top_day = n_memes_for_binom_top_day
        self.n_memes_to_get_top_day_based = n_memes_to_get_top_day_based

        # n_latest_random_based_inference model_params
        self.n_memes_to_try_n_last_days_random_based = n_memes_to_try_n_last_days_random_based
        self.n_memes_to_get_n_last_days_random_based = n_memes_to_get_n_last_days_random_based
        self.random_priority_power = random_priority_power
        self.n_last_days_random = n_last_days_random

        # load qt models
        self.quantile_trans_visual = pk.load(open(settings.PATH_TO_VIS_QT, 'rb'))
        self.quantile_trans_txt_rus = pk.load(open(settings.PATH_TO_TEXT_RUS_QT, 'rb'))
        self.quantile_trans_txt_en = pk.load(open(settings.PATH_TO_TEXT_EN_QT, 'rb'))

    def get_k_largest_by_marks(self, ids, k, ratings, extra=None):
        if len(ids) != len(ratings):
            if (extra is None):
                return ids
            else:
                return ids, extra
        if k >= len(ids):
            if extra is None:
                return ids
            else:
                return ids, extra

        ratings_partition = np.argpartition(ratings, len(ids) - k)
        if extra is None:
            return ids[ratings_partition[len(ids) - k:]]
        else:
            return ids[ratings_partition[len(ids) - k:]], extra[ratings_partition[len(ids) - k:]]

    # мемы в other должны быть того же lang что и мем, к которому ищут соседей!
    def context_distance(self, meme_vis_embedding, meme_text_embedding, other_vis_embeddings, other_text_embeddings, lang):
        text_distances = euclidean_distance(meme_text_embedding, other_text_embeddings)
        vis_distances = euclidean_distance(meme_vis_embedding, other_vis_embeddings)
        vis_distances_quantized = self.quantile_trans_visual.transform(vis_distances.reshape(-1, 1)).flatten()
        if lang == 'rus':
            text_distances_quantized = self.quantile_trans_txt_rus.transform(text_distances.reshape(-1, 1)).flatten()
        elif lang == 'en':
            text_distances_quantized = self.quantile_trans_txt_en.transform(text_distances.reshape(-1, 1)).flatten()
        else:
            raise ValueError('Illegal language: {}'.format(lang))
        combined_distances = vis_distances_quantized + text_distances_quantized
        return combined_distances


    # this function returns indices of new memes for user
    def filter_repetitions(self, memes_ids, memes_hashes, user_id):
        # can be done with less getters
        user_history = get_user_history(user_id)
        user_hashes = get_memes_hashes(user_history)
        mask = np.in1d(memes_hashes, user_hashes)
        indices = np.arange(memes_ids.shape[0])
        return indices[~mask]

    def filter_repetitions_and_get_probs(self, user_id,
                                               memes_ids,
                                               memes_hashes,
                                               memes_likes=None,
                                               memes_views=None,
                                               memes_dates=None,
                                               date_power=1,
                                               n_last_days=1,
                                               method='stats'):
        new_memes_indices = self.filter_repetitions(memes_ids, memes_hashes, user_id)
        if len(new_memes_indices) > 0:
            memes_ids = memes_ids[new_memes_indices]
            if method == 'stats':
                memes_likes = memes_likes[new_memes_indices]
                memes_views = memes_views[new_memes_indices]
                probabilities = (memes_likes + self.n_views_to_be_confident_in_meme) / (memes_views + self.n_views_to_be_confident_in_meme)
                probabilities /= probabilities.sum()
                return memes_ids, probabilities
            if method == 'dates':
                memes_dates = memes_dates[new_memes_indices]
                probabilities = np.zeros(memes_ids.shape[0])
                cur_date_utc = timezone.now()
                for i, date in enumerate(memes_dates):
                    probabilities[i] = 1 / ((cur_date_utc - date).days + 1) ** date_power
                probabilities /= probabilities.sum()
                return memes_ids, probabilities
        return None, None

    # def process_reaction(self, user_id, meme_id, rating):
        # reaction can be string, json or whatever is convenient for backend
        # self.model.learning_iteration(user_id, meme_id, rating)


    def inference(self, user_id):
        user_embedding = get_users_embeddings([user_id])[0]

        # выбираем один из подходов в соответствие с вероятностями methods_probs
        random_method = np.random.choice(list(self.methods_probs.keys()), p=list(self.methods_probs.values()))
        if random_method == 'user_based':
            logger.info("user_based_selected {}".format(user_id))
            user_based_memes_ids = self.user_based_inference(
                                        user_id,
                                        user_embedding,
                                        self.n_users_first_stage,
                                        self.n_users_second_stage,
                                        self.n_memes_from_users_to_compare,
                                        self.min_recall_threshold,
                                        self.n_memes_from_nearest_users,
                                        self.n_memes_to_get_user_based,
                                        self.n_random_users_to_try_user_based)
            if len(user_based_memes_ids) == 0:
                # если никого нет, то отправляем в random
                random_method = 'random'
            else:
                # иначе выбираем рандомный среди оставшихся
                user_based_meme = np.random.choice(user_based_memes_ids)
                return user_based_meme, USER_BASED
        if random_method == 'item_based':
            logger.info("item_based_selected {}".format(user_id))
            item_based_memes_ids = self.item_based_inference(
                                        user_id,
                                        user_embedding,
                                        self.n_last_liked_memes_from_user,
                                        self.n_memes_from_our_meme,
                                        self.n_memes_to_get_item_based,
                                        self.n_random_memes_to_try_item_based,)
            if len(item_based_memes_ids) == 0:
                # если никого нет, то отправляем в random
                random_method = 'random'
            else:
                # иначе выбираем рандомный среди оставшихся
                item_based_meme = np.random.choice(item_based_memes_ids)
                return item_based_meme, ITEM_BASED
        if random_method == 'origin_based':
            logger.info("origin_based_selected {}".format(user_id))
            origin_based_memes_ids = self.origin_based_inference(
                                        user_id,
                                        user_embedding,
                                        self.n_last_memes_to_choose_origin,
                                        self.n_memes_from_origin_to_choose,
                                        self.n_memes_to_get_origin_based)
            if len(origin_based_memes_ids) == 0:
                # если никого нет, то отправляем в random
                random_method = 'random'
            else:
                # иначе выбираем рандомный среди остmemes_datesавшихся
                origin_based_meme = np.random.choice(origin_based_memes_ids)
                return origin_based_meme, ORIGIN_BASED
        if random_method == 'top_day_based':
            logger.info("top_day_based_selected {}".format(user_id))
            top_day_based_memes_ids = self.top_day_based_inference(
                                        self.n_memes_pool_top_day,
                                        self.n_memes_for_binom_top_day,
                                        self.n_memes_to_get_top_day_based,
                                        user_id)
            if len(top_day_based_memes_ids) == 0:
                # если никого нет, то отправляем в random
                random_method = 'random'
            else:
                # иначе выбираем рандомный среди оставшихся
                top_day_based_meme = np.random.choice(top_day_based_memes_ids)
                return top_day_based_meme, TOP_DAY_BASED
        if random_method == 'n_last_random':
            logger.info(" n_last_days_random_selected {}".format(user_id))
            n_last_days_random_based_memes_ids = self.n_last_days_random_based_inference(
                                        self.n_memes_to_try_n_last_days_random_based,
                                        self.n_memes_to_get_n_last_days_random_based,
                                        self.n_last_days_random,
                                        self.random_priority_power,
                                        user_id)
            if len(n_last_days_random_based_memes_ids) == 0:
                # если никого нет, то отправляем в random
                random_method = 'random'
            else:
                # иначе выбираем рандомный среди оставшихся
                n_last_days_random_based_meme = np.random.choice(n_last_days_random_based_memes_ids)
                return n_last_days_random_based_meme, N_LAST_DAYS_RANDOM
        if random_method == 'top_based':
            logger.info(" top_based_selected {}".format(user_id))
            # hardcode of parameter, sorry
            top_based_memes_ids = self.top_based_inference(user_id, 4000, 1)
            if len(top_based_memes_ids) == 0:
                random_method = 'random'
            else:
                top_based_meme = np.random.choice(top_based_memes_ids)
                return top_based_meme, TOP_BASED

        if random_method == 'random':
            logger.info("random_selected {}".format(user_id))
            # выбираем рандомные n_memes_to_get_random_based мемов
            random_based_memes_ids = self.random_based_inference(self.n_memes_to_try_random_based, self.n_memes_to_get_random_based, user_id)
            if len(random_based_memes_ids) == 0:
                return -1, -1
            random_based_meme = np.random.choice(random_based_memes_ids)
            return  random_based_meme, RANDOM_RECOMMEND

    def user_based_inference(self,
                             user_id,
                             user_embedding,
                             n_users_first_stage,
                             n_users_second_stage,
                             n_memes_from_users_to_compare,
                             min_recall_threshold,
                             n_memes_from_user,
                             max_memes_to_get,
                             n_random_users_to_try):
        # ищем ближайших среди этих юзеров
        random_users_ids, random_users_embeddings = get_random_users(n_random_users_to_try, embeddings=True)
        random_users_embeddings = random_users_embeddings[random_users_ids != user_id]
        random_users_ids = random_users_ids[random_users_ids != user_id]
        if len(random_users_embeddings) == 0:
            return np.empty(0)
        random_users_similarity = cosine_similarity(user_embedding, random_users_embeddings) # считаем расстояния

        # оставляем n_users_first_stage самых близких юзеров с помощью k-ой порядковой статистики
        filtered_users_ids = self.get_k_largest_by_marks(random_users_ids, n_users_first_stage, random_users_similarity)

        # вторая итерация отбора, оставляем n_users_second_stage
        this_memes_ids, _, this_memes_ratings = get_user_interact_history(user_id, n_memes_from_users_to_compare)
        this_liked_memes_ids = this_memes_ids[this_memes_ratings == LIKE]
        this_disliked_memes_ids = this_memes_ids[this_memes_ratings == DISLIKE]
        user_to_approve_stats = np.zeros((filtered_users_ids.shape[0], 3))
        memes_ids, scores = get_users_history(filtered_users_ids, n_memes_from_users_to_compare)
        for i, filtered_user_id in enumerate(filtered_users_ids):
            filtered_memes_ids, filtered_memes_ratings = memes_ids[filtered_user_id], scores[filtered_user_id]
            liked_memes_ids = filtered_memes_ids[filtered_memes_ratings == LIKE]
            disliked_memes_ids = filtered_memes_ids[filtered_memes_ratings == DISLIKE]
            n_likes_intersection = np.intersect1d(this_liked_memes_ids, liked_memes_ids).shape[0]
            n_diff_opinion_1 = np.intersect1d(this_disliked_memes_ids, liked_memes_ids).shape[0]
            n_diff_opinion_2 = np.intersect1d(this_liked_memes_ids, disliked_memes_ids).shape[0]
            if n_likes_intersection + n_diff_opinion_1 == liked_memes_ids.shape[0]:
                 user_to_approve_stats[i, 1] = 0
                 continue
            # recall:
            if (this_memes_ids.shape[0] != 0 and filtered_memes_ids.shape[0] != 0):
                user_to_approve_stats[i, 0] = min(n_likes_intersection / this_memes_ids.shape[0], n_likes_intersection / filtered_memes_ids.shape[0])
            else:
                user_to_approve_stats[i, 0] = 0

            # F-measure of precisions
            if n_likes_intersection + n_diff_opinion_1 == 0:
                precision_1 = 0
            else:
                precision_1 = n_likes_intersection / (n_likes_intersection + n_diff_opinion_1)

            if n_likes_intersection + n_diff_opinion_2 == 0:
                precision_2 = 0
            else:
                precision_2 = n_likes_intersection / (n_likes_intersection + n_diff_opinion_2)
            if (precision_1 + precision_2 == 0):
                F_measure = 0
            else:
                F_measure = 2 * precision_1 * precision_2 / (precision_1 + precision_2)
            user_to_approve_stats[i, 1] = F_measure

        logger.info("max_F_measure {} {}".format(user_id, user_to_approve_stats[:, 1].max()))
        logger.info("max_min_recall {} {}".format(user_id, user_to_approve_stats[:, 0].max()))

        recall_condition = (user_to_approve_stats[:, 0] >= min_recall_threshold)
        if recall_condition.sum() != 0:
            filtered_users_ids = filtered_users_ids[recall_condition]
        logger.info("filtered_users_found {} {}".format(user_id, len(filtered_users_ids)))

        if recall_condition.sum() != 0:
            users_f_measure = user_to_approve_stats[:, 1][recall_condition]
            logger.info("max_filtered_F_measure {} {}".format(user_id, user_to_approve_stats[:, 1].max()))
        else:
            users_f_measure = user_to_approve_stats[:, 1]
        final_users_ids = self.get_k_largest_by_marks(filtered_users_ids, n_users_second_stage, users_f_measure)


        # здесь будут эмбединги выбранных мемов
        answer_embeddings = np.zeros([n_users_second_stage * n_memes_from_user, self.embedding_size])
        answer_ids = np.zeros([n_users_second_stage * n_memes_from_user], dtype=int) # здесь будут id выбранных мемов
        i1 = 0
        for try_user_id in final_users_ids:
            # получаем последние n_memes_from_user мемов, лайкнутых данным юзером
            memes_ids, memes_embeddings = get_user_like_history(try_user_id, n_memes_from_user, exclude=this_memes_ids)
            if len(memes_embeddings) == 0:
                memes_embeddings = np.zeros((0, settings.DIMENSION))
            # заполняем матрицы
            i2 = i1 + len(memes_embeddings) # in case he liked less then n_memes_from_user
            answer_embeddings[i1:i2, :] = memes_embeddings
            answer_ids[i1:i2] = memes_ids
            i1 = i2

        # оставляем только уникальные
        memes_to_check_ids, unique_indices = np.unique(answer_ids[:i1], return_index=True)
        memes_to_check_embeddings = answer_embeddings[:i1, :][unique_indices]
        # берем их хэши и фильтруем
        memes_to_check_hashes = get_memes_hashes(memes_to_check_ids)
        new_indices = self.filter_repetitions(memes_to_check_ids, memes_to_check_hashes, user_id)
        memes_to_check_ids = memes_to_check_ids[new_indices]
        memes_to_check_embeddings = memes_to_check_embeddings[new_indices]

        # если в целом взяли по юзерам мемов очень мало, лучше возьмем в итог меньше мемов, но зато хороших
        n_memes_to_get = int(min(np.floor(len(memes_to_check_ids) * 0.1) + 1, max_memes_to_get))

        ratings = np.dot(memes_to_check_embeddings, user_embedding)
        return self.get_k_largest_by_marks(memes_to_check_ids, n_memes_to_get, ratings)

    
    def top_based_inference(self, user_id, n_memes_to_try, max_memes_to_get):
        # выбираем пул рандомны мемов, среди которых будем искать лучшие
        random_memes_ids, random_memes_likes, random_memes_views, random_memes_hashes = get_random_memes(n_memes_to_try, checked=APPROVED, hashes=True, stats=True)
        new_memes_indices = self.filter_repetitions(random_memes_ids, random_memes_hashes, user_id)
        random_memes_ids = random_memes_ids[new_memes_indices]
        random_memes_likes = random_memes_likes[new_memes_indices]
        random_memes_views = random_memes_views[new_memes_indices]
        ratings = np.zeros(len(random_memes_ids))
        for i in range(len(random_memes_ids)):
            p_value = binom_test(random_memes_likes[i], random_memes_views[i], 0.5, 'greater')
            ratings[i] = 1 - p_value
        return self.get_k_largest_by_marks(random_memes_ids, max_memes_to_get, ratings)
        
        

    def item_based_inference(self,
                             user_id,
                             user_embedding,
                             n_last_liked_memes_from_user,
                             n_memes_from_our_meme,
                             max_memes_to_get,
                             n_random_memes_to_try):
        # выбираем последние лайкнутые мемы юзера
        user_n_last_liked_memes_ids, user_n_last_liked_memes_embeds, user_n_last_liked_memes_langs, user_n_last_liked_memes_visual,\
            user_n_last_liked_memes_text = get_user_like_history(user_id,
                                                                n_last_liked_memes_from_user, langs=True,
                                                                visual_pca=True, text_pca=True)

        # выбираем пул рандомны мемов, среди которых будем искать ближайших
        random_memes_ids_rus, random_memes_embeddings_rus, random_memes_hashes_rus, random_memes_visual_embeddings_rus, random_memes_text_embeddings_rus\
            = get_random_memes(n_random_memes_to_try // 2, new=False, checked=APPROVED, embeddings=True, hashes=True,
                               visual_pca=True, text_pca=True, lang='rus')
        random_memes_ids_en, random_memes_embeddings_en, random_memes_hashes_en, random_memes_visual_embeddings_en, random_memes_text_embeddings_en \
            = get_random_memes((n_random_memes_to_try + 1) // 2, new=False, checked=APPROVED, embeddings=True, hashes=True,
                               visual_pca=True, text_pca=True, lang='en')
        # сразу фильтруем ненужные, от геттера хешей можно избавиться
        new_memes_indices_rus = self.filter_repetitions(random_memes_ids_rus, random_memes_hashes_rus, user_id)
        random_memes_ids_rus = random_memes_ids_rus[new_memes_indices_rus]
        random_memes_embeddings_rus = random_memes_embeddings_rus[new_memes_indices_rus]
        random_memes_visual_embeddings_rus = random_memes_visual_embeddings_rus[new_memes_indices_rus]
        random_memes_text_embeddings_rus = random_memes_text_embeddings_rus[new_memes_indices_rus]

        new_memes_indices_en = self.filter_repetitions(random_memes_ids_en, random_memes_hashes_en, user_id)
        random_memes_ids_en = random_memes_ids_en[new_memes_indices_en]
        random_memes_embeddings_en = random_memes_embeddings_en[new_memes_indices_en]
        random_memes_visual_embeddings_en = random_memes_visual_embeddings_en[new_memes_indices_en]
        random_memes_text_embeddings_en = random_memes_text_embeddings_en[new_memes_indices_en]

        if len(random_memes_ids_rus) == 0 and len(random_memes_ids_en) == 0:
            return np.empty(0)
        # здесь будут эмбединги и id выбранных мемов
        filtered_memes_embeddings = np.zeros([n_last_liked_memes_from_user * n_memes_from_our_meme, self.embedding_size])
        filtered_memes_ids = np.zeros([n_last_liked_memes_from_user * n_memes_from_our_meme], dtype=int)
        i1 = 0
        logger_text = ""
        for counter in range(len(user_n_last_liked_memes_embeds)):
            lang = user_n_last_liked_memes_langs[counter]
            visual_embedding = user_n_last_liked_memes_visual[counter]
            text_embedding = user_n_last_liked_memes_text[counter]
            if lang == 'rus':
                random_memes_embeddings = random_memes_embeddings_rus
                random_memes_visual = random_memes_visual_embeddings_rus
                random_memes_text = random_memes_text_embeddings_rus
                random_memes_ids = random_memes_ids_rus
            elif lang == 'en':
                random_memes_embeddings = random_memes_embeddings_en
                random_memes_visual = random_memes_visual_embeddings_en
                random_memes_text = random_memes_text_embeddings_en
                random_memes_ids = random_memes_ids_en
            else:
                raise ValueError('Encountered illegal lang: {}'.format(lang))
            # similarity = cosine_similarity(meme_embed, random_memes_embeddings) # считаем расстояние
            distance = self.context_distance(visual_embedding, text_embedding, random_memes_visual, random_memes_text, lang)
            # выбираем самые близкие к данному мему юзера мемы из пула с помощью k-ой статистики
            closest_to_liked_ids, closest_to_liked_embeddings = self.get_k_largest_by_marks(
                                                            random_memes_ids,
                                                            n_memes_from_our_meme,
                                                            -distance,
                                                            extra=random_memes_embeddings)

            if len(closest_to_liked_embeddings) == 0:
                closest_to_liked_embeddings = np.zeros((0, settings.DIMENSION))
            else:
                logger_text += "|{} {}|".format(user_n_last_liked_memes_ids[counter], closest_to_liked_ids[0]) 
            i2 = i1 + len(closest_to_liked_ids)
            filtered_memes_embeddings[i1:i2, :] = closest_to_liked_embeddings
            filtered_memes_ids[i1:i2] = closest_to_liked_ids
            i1 = i2
        logger.info(logger_text)

        memes_to_check_ids, unique_indices = np.unique(filtered_memes_ids[:i1], return_index=True)
        memes_to_check_embeddings = filtered_memes_embeddings[:i1, :][unique_indices]

        # если в целом взяли по юзерам мемов очень мало, лучше возьмем в итог меньше мемов, но зато хороших
        n_memes_to_get = int(min(np.floor(len(memes_to_check_ids) * 0.1) + 1, max_memes_to_get))

        ratings = np.dot(memes_to_check_embeddings, user_embedding)
        return self.get_k_largest_by_marks(memes_to_check_ids, n_memes_to_get, ratings)


    def origin_based_inference(self,
                             user_id,
                             user_embedding,
                             n_last_memes_to_look,
                             n_last_memes_from_origin,
                             max_memes_to_get):
        start_time = time.time()
        # выбираем последние мемы юзера и их origins
        user_n_last_memes_ids, user_n_last_memes_scores, user_n_last_memes_origins = get_user_origins_history(user_id,
                                                                                            n_last_memes_to_look)

        # выбираем лучший origin пропорционально лайкам мемов из них, но не свой же
        origins = []
        probas = []
        this_origin = get_user_origin(user_id)

        user_likes = get_user_likes(user_id)
        user_views = get_user_views(user_id)
        binom_test_prob = user_likes / user_views
        for origin in np.unique(user_n_last_memes_origins):
            if (origin == this_origin or origin == 'start'):
                continue
            this_origin_scores = user_n_last_memes_scores[user_n_last_memes_origins == origin]
            origins.append(origin)
            probas.append(1 - binom_test(this_origin_scores.sum(), len(this_origin_scores), binom_test_prob, 'greater'))
        probas = np.array(probas)
        origins_indexes = np.arange(len(origins))
        origin_choice_index = -1
        while time.time() - start_time < 1:
            if origin_choice_index != -1:
                probas[origin_choice_index] = 0
            normalization = np.sum(probas)
            if normalization == 0 or len(probas) == 0:
                return np.empty(0)
            origin_choice_index = np.random.choice(origins_indexes, p=probas/normalization)
            origin_choice = origins[origin_choice_index]
            # выбираем последние мемы из этого источника
            memes_to_check_ids, memes_to_check_embeddings = get_last_memes_from_origin(origin_choice, n_last_memes_from_origin)

            # фильтруем те, которые мы уже видели
            memes_to_check_hashes = get_memes_hashes(memes_to_check_ids)
            memes_to_check_likes, memes_to_check_views = get_memes_stats(memes_to_check_ids)
            new_origin_based_memes_ids, probabilities = self.filter_repetitions_and_get_probs(user_id,
                                                                                              memes_to_check_ids,
                                                                                              memes_to_check_hashes,
                                                                                              memes_to_check_likes,
                                                                                              memes_to_check_views)
            # из оставшихся выбираем лучший по алс(алр, и тд)
            if new_origin_based_memes_ids is not None:
                logger.info("origin_choice {} {}".format(user_id, origin_choice))
                new_origin_based_memes_ids = np.random.choice(new_origin_based_memes_ids, max_memes_to_get, p=probabilities)
                return new_origin_based_memes_ids
        return np.empty(0)


    def top_day_based_inference(self, n_memes_pool_size, n_memes_to_select_top, n_memes_to_get, user_id):
        # берем  мемы за последний день
        today_memes_ids, today_memes_likes, today_memes_views, today_memes_hashes = get_random_memes(n_memes_pool_size,
                                                                                                     from_user=True,
                                                                                                     checked=APPROVED,
                                                                                                     n_last_days=1,
                                                                                                     stats=True,
                                                                                                     hashes=True)
        # те мемы, которые много дизлайкают рекомендуем с меньшей вероятностью
        if len(today_memes_ids) > 0:
            new_memes_indices = self.filter_repetitions(today_memes_ids,
                                                          today_memes_hashes,
                                                          user_id)

            if today_memes_ids is not None and len(today_memes_ids) > 0:
                new_memes_indices = np.random.choice(new_memes_indices, min(n_memes_to_select_top, len(new_memes_indices)))

            today_memes_ids = today_memes_ids[new_memes_indices]
            today_memes_likes = today_memes_likes[new_memes_indices]
            today_memes_views = today_memes_views[new_memes_indices]

            ratings = np.zeros(len(today_memes_ids))
            for i in range(len(today_memes_ids)):
                p_value = binom_test(today_memes_likes[i], today_memes_views[i], 0.5, 'greater')
                ratings[i] = 1 - p_value
            return self.get_k_largest_by_marks(today_memes_ids, n_memes_to_get, ratings)
        return np.empty(0)


    def random_based_inference(self, n_memes_to_try, n_memes_to_get, user_id):
        # берем рандомные новые
        random_memes_ids, random_memes_likes, random_memes_views, random_memes_hashes = get_random_memes(n_memes_to_try,
                                                                                                         from_user=True,
                                                                                                         checked=APPROVED,
                                                                                                         stats=True,
                                                                                                         hashes=True)
        # те мемы, которые много дизлайкают рекомендуем с меньшей вероятностью
        if len(random_memes_ids) > 0:
            new_random_based_memes_ids, probabilities = self.filter_repetitions_and_get_probs(user_id,
                                                                                              random_memes_ids,
                                                                                              random_memes_hashes,
                                                                                              random_memes_likes,
                                                                                              random_memes_views)
            if new_random_based_memes_ids is not None:
                random_based_memes_ids = np.random.choice(new_random_based_memes_ids, n_memes_to_get, p=probabilities)
                return random_based_memes_ids
        new_random_based_memes_idexes = np.empty(0)
        for i in range(self.n_chances_to_find_new_memes):
            random_memes_ids, random_memes_likes, random_memes_views, random_memes_hashes = get_random_memes(
                n_memes_to_try, from_user=False, checked=APPROVED, stats=True, hashes=True)
            new_random_based_memes_ids, probabilities = self.filter_repetitions_and_get_probs(user_id,
                                                                                              random_memes_ids,
                                                                                              random_memes_hashes,
                                                                                              random_memes_likes,
                                                                                              random_memes_views)
            if new_random_based_memes_ids is not None:
                random_based_memes_ids = np.random.choice(new_random_based_memes_ids, n_memes_to_get, p=probabilities)
                return random_based_memes_ids
        return np.empty(0)


    def n_last_days_random_based_inference(self, n_memes_to_try, n_memes_to_get, n_last_days, priority_power, user_id):
        # берем рандомные новые
        random_memes_ids, random_memes_likes, random_memes_views, random_memes_hashes, random_memes_date = get_random_memes(
            n_memes_to_try, from_user=True, checked=APPROVED, n_last_days=n_last_days, stats=True, hashes=True,
            published_on=True)
        # те мемы, которые юзеры загружали недавно выбираются с большей вероятностью
        if len(random_memes_ids) > 0:
            new_random_based_memes_ids, probabilities = self.filter_repetitions_and_get_probs(user_id,
                                                                                              random_memes_ids,
                                                                                              random_memes_hashes,
                                                                                              memes_dates=random_memes_date,
                                                                                              date_power=priority_power,
                                                                                              n_last_days=n_last_days,
                                                                                              method='dates')
            if new_random_based_memes_ids is not None:
                random_based_memes_ids = np.random.choice(new_random_based_memes_ids, n_memes_to_get, p=probabilities)
                return random_based_memes_ids
        return np.empty(0)
