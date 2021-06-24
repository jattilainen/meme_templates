from memeapp.getters import get_users_embeddings, get_memes_embeddings, get_meme_interact_history, get_user_interact_history
from memeapp.setters import set_user_embedding, set_meme_embedding
import numpy as np
import logging
logger = logging.getLogger('memerecommend')

class ALR:
    def __init__(self, reg, tolerance, n_memes_for_user=1000, n_users_for_meme=1000):
        self.sigmoid = lambda x : 1 / (1 + np.exp(-x))
        self.meme_reg = reg
        self.user_reg = reg
        self.tolerance = tolerance
        self.n_memes_for_user = n_memes_for_user
        self.n_users_for_meme = n_users_for_meme
        s0 = 1
        p = 0.5
        lambda_ = 1
        self.eta = lambda k: lambda_ * (s0 / (s0 + k)) ** p


    def learning_iteration(self, user_id, meme_id, rating):
        user_vector = get_users_embeddings([user_id])[0]
        meme_vector = get_memes_embeddings([meme_id])[0]
        logger.info("alr_iter_start {} {} {} {}".format(user_id, meme_id, rating, np.dot(meme_vector, user_vector)))
        _, user_to_memes_embeddings, user_to_memes_real_ratings = get_user_interact_history(user_id, n=self.n_memes_for_user)

        if len(user_to_memes_embeddings) == 0:
            user_to_memes_embeddings = np.zeros((0, settings.DIMENSION))
        meme_to_users_ids, meme_to_users_embeddings, meme_to_users_real_ratings = get_meme_interact_history(meme_id, n=self.n_users_for_meme)
        if len(meme_to_users_embeddings) == 0:
            meme_to_users_embeddings = np.zeros((0, settings.DIMENSION))
        user_id_index = np.arange(len(meme_to_users_ids))
        user_id_index = user_id_index[meme_to_users_ids == user_id]
        
        for i in range(1000):
            user_to_memes_pred_ratings = np.dot(user_to_memes_embeddings, user_vector)
            likes_weight = user_to_memes_real_ratings + 1
            ru = (self.sigmoid(user_to_memes_pred_ratings) - user_to_memes_real_ratings) * likes_weight
            grad = (user_to_memes_embeddings * ru[:, None]).sum(axis=0) * 1 / user_to_memes_real_ratings.shape[0] + self.user_reg * user_vector
            user_vector -= self.eta(i) * grad
            if np.sqrt(np.sum(np.square(grad))) < self.tolerance:
                break
        meme_to_users_embeddings[user_id_index] = user_vector

        for i in range(1000):
            meme_to_users_pred_ratings = np.dot(meme_to_users_embeddings, meme_vector)
            likes_weight = meme_to_users_real_ratings + 1
            ri = (self.sigmoid(meme_to_users_pred_ratings) - meme_to_users_real_ratings) * likes_weight
            grad = (meme_to_users_embeddings * ri[:, None]).sum(axis=0) * 1 / meme_to_users_real_ratings.shape[0] + self.meme_reg * meme_vector
            meme_vector -= self.eta(i) * grad
            if np.sqrt(np.sum(np.square(grad))) < self.tolerance:
                break

        set_user_embedding(user_id, user_vector)
        set_meme_embedding(meme_id, meme_vector)
        logger.info("alr_iter_finish {} {} {} {}".format(user_id, meme_id, rating, np.dot(meme_vector, user_vector)))


