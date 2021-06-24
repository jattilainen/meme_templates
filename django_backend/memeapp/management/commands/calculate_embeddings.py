from django.core.management.base import BaseCommand
from memeapp.models import Meme
from memeapp.preprocessing.visual_embeddings import get_visual_embedding
from memeapp.preprocessing.text_embeddings import get_text_and_embedding
from memeapp.setters import set_meme_text_data, set_meme_visual_embedding

import logging
import numpy as np


logger = logging.getLogger("memerecommend")


class Command(BaseCommand):
    log_start_text = "Embeddings calculation started"
    log_end_text = "Embeddings calculation finished"

    def handle(self, *args, **options):
        logger.info(self.log_start_text)
        memes = Meme.objects.all()
        i = 0
        for meme in memes:
            narr = np.array(meme.visual_embedding)
            if not (narr == 0).all():
                continue
            path = meme.image.path
            text, lang, text_embedding = get_text_and_embedding(path)
            visual_embedding = get_visual_embedding(path)
            set_meme_text_data(meme.pk, text, lang, text_embedding)
            set_meme_visual_embedding(meme.pk, visual_embedding)
            if i % 10 == 9:
                print('processed {} memes'.format(i))
            i += 1
        logger.info(self.log_end_text)
