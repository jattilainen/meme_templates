import numpy as np

from django.conf import settings


def default_user_embedding():
    embedding = None
    if settings.RANDOM_MODE == "normal":
        embedding = np.random.normal(settings.RANDOM_NORMAL_MODE[0], settings.RANDOM_NORMAL_MODE[1],
                                     settings.DIMENSION).tolist()
    elif settings.RANDOM_MODE == "bias":
        embedding = np.ones(settings.DIMENSION).tolist()
    else:
        raise ValueError("Random mode invalid or not specified")
    return embedding


def default_meme_embedding():
    embedding = None
    if settings.RANDOM_MODE == "normal":
        embedding = np.random.normal(settings.RANDOM_NORMAL_MODE[0], settings.RANDOM_NORMAL_MODE[1],
                                     settings.DIMENSION).tolist()
    elif settings.RANDOM_MODE == 'bias':
        embedding = np.ones(settings.DIMENSION).tolist()
    else:
        raise ValueError("Random mode invalid or not specified")
    return embedding


def default_visual_pca():
    return np.ones(settings.VISUAL_PCA_SIZE).tolist()


def default_text_pca():
    return np.ones(settings.TEXT_PCA_SIZE).tolist()
