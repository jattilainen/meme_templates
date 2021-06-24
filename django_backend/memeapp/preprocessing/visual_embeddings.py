import skimage
from skimage import transform, io
import torch
from memeapp.preprocessing.embedding_utils import mobilenet
import numpy as np
from django.conf import settings


def default_visual_embedding():
    return np.zeros(settings.VISUAL_EMBEDDING_SIZE).tolist()


def get_visual_embedding(path):
    img = skimage.img_as_float32(io.imread(path))
    if len(img.shape) == 2:
        img = np.concatenate([np.expand_dims(img, axis=0)] * 3, axis=0).transpose(1, 2, 0)
    if img.shape[2] == 4:
        img = img[:, :, :3]
    img_resized = transform.resize(img, (224, 224))
    img_tensor = torch.from_numpy(img_resized).permute(2, 0, 1).unsqueeze(0)
    img_embedding = mobilenet(img_tensor).detach().numpy()[0]
    return img_embedding
