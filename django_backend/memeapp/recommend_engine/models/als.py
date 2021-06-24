from memeapp.getters import get_users_embeddings, get_memes_embeddings, get_meme_interact_history, get_user_interact_history
from memeapp.setters import set_user_embedding, set_meme_embedding
import numpy as np

import logging
logger = logging.getLogger('memerecommend')

class ALS:
    def __init__(self, regularization):
        self.reg_param = regularization

    def learning_iteration(self, user_id, meme_id, rating):
        user_vector = get_users_embeddings([user_id])[0]
        meme_vector = get_memes_embeddings([meme_id])[0]
        logger.info("als_iter_start {} {} {} {}".format(user_id, meme_id, rating, np.dot(meme_vector, user_vector)))
        _, user_to_memes_embeddings, user_to_memes_real_ratings = get_user_interact_history(user_id)
        if len(user_to_memes_embeddings) == 0:
            user_to_memes_embeddings = np.zeros((0, settings.DIMENSION))
        user_to_memes_pred_ratings = np.dot(user_to_memes_embeddings, user_vector)

        meme_to_users_ids, meme_to_users_embeddings, meme_to_users_real_ratings = get_meme_interact_history(meme_id)
        if len(meme_to_users_embeddings) == 0:
            meme_to_users_embeddings = np.zeros((0, settings.DIMENSION))
        user_id_index = np.arange(len(meme_to_users_ids))
        user_id_index = user_id_index[meme_to_users_ids == user_id]

        for i in range(len(user_vector)):
            p_i = user_vector[i]
            q_i_vector = user_to_memes_embeddings[:, i]
            r_f = user_to_memes_pred_ratings - np.dot(q_i_vector, p_i)
            numerator = np.dot((user_to_memes_real_ratings - r_f), q_i_vector)
            denominator = (np.sum(q_i_vector ** 2) + self.reg_param)
            user_vector[i] = numerator / denominator
            user_to_memes_pred_ratings = r_f + np.dot(q_i_vector , user_vector[i])
        meme_to_users_embeddings[user_id_index] = user_vector
        meme_to_users_pred_ratings = np.dot(meme_to_users_embeddings, meme_vector)
        for i in range(len(meme_vector)):
            q_i = meme_vector[i]
            p_i_vector = meme_to_users_embeddings[:, i]
            r_f = meme_to_users_pred_ratings - np.dot(p_i_vector, q_i)
            numerator = np.dot((meme_to_users_real_ratings - r_f), p_i_vector)
            denominator = (np.sum(p_i_vector ** 2) + self.reg_param)
            meme_vector[i] = numerator / denominator
            meme_to_users_pred_ratings = r_f + np.dot(p_i_vector , meme_vector[i])
        set_user_embedding(user_id, user_vector)
        set_meme_embedding(meme_id, meme_vector)
        logger.info("als_iter_finish {} {} {} {}".format(user_id, meme_id, rating, np.dot(meme_vector, user_vector)))
        logger.info("user_embedding {} {}".format(user_id, user_vector))
        logger.info("meme_embedding {} {}".format(meme_id, meme_vector))
