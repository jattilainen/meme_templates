from django.conf import settings
import numpy as np
import skimage
from memeapp.preprocessing.embedding_utils import russian_embeddings, english_embeddings, easyocr_reader, get_clean_text, binom_confidence, get_right_language, preprocess_text, get_best_fmeasure, EMB_INF
import pytesseract
from skimage import transform, io



def default_text_embedding():
    return np.zeros(settings.TEXT_EMBEDDING_SIZE).tolist()


def embedding_by_text(text, lang):
    if len(text) == 0:
        return np.zeros(settings.TEXT_EMBEDDING_SIZE)
    if lang == 'rus':
        embedding = np.zeros(settings.TEXT_EMBEDDING_SIZE)
        for word in text.split():
            embedding += russian_embeddings.get(word, np.zeros(settings.TEXT_EMBEDDING_SIZE))
        return embedding / len(text.split())
    elif lang == 'en':
        embedding = np.zeros(settings.TEXT_EMBEDDING_SIZE)
        for word in text.split():
            embedding += english_embeddings.get(word, np.zeros(settings.TEXT_EMBEDDING_SIZE))
        return embedding / len(text.split())


def get_lobster_text_from(crop):
    texts = []
    lengths = []
    confidences = []
    for scale in [4, 2, 1, 0.5]:
        crop_scaled = skimage.img_as_ubyte(transform.rescale(crop, scale, multichannel=True))
        rulob_crop_scaled_text = pytesseract.image_to_string(crop_scaled, lang='rulobster', config=r'--psm 7').strip('\x0c')

        if rulob_crop_scaled_text == '':
            continue
        rulob_text_cleaned, rulob_text_cleaned_dist, rulob_text_lang = get_clean_text(rulob_crop_scaled_text)
        if rulob_text_lang is None or rulob_text_lang == 'en':
            continue
        rulob_distance_confidence = rulob_text_cleaned_dist / len(rulob_text_cleaned.split())
        texts.append(rulob_text_cleaned)
        lengths.append(len(rulob_text_cleaned))
        confidences.append(rulob_distance_confidence)
    if len(lengths) == 0:
        return '', EMB_INF
    best_text_index = get_best_fmeasure(np.array(lengths), np.array(confidences))
    best_text = texts[best_text_index]
    best_dist = int(confidences[best_text_index] * len(best_text.split()))
    return best_text, best_dist


def get_text_from_img(img, path):
    reader_result = easyocr_reader.readtext(path)
    result_text = ''
    for i in range(len(reader_result)):
        res = reader_result[i]
        bbox = res[0]
        bottom, top, left, right = int(bbox[0][1]), int(bbox[3][1]), int(bbox[0][0]), int(bbox[1][0])
        bbox = np.array([bottom, top, left, right], dtype=int)

        reader_text = res[1]
        if len(reader_text) == 0:
            continue

        reader_text_cleaned, reader_text_cleaned_dist, reader_text_lang = get_clean_text(reader_text)

        if reader_text_lang is None or len(reader_text_cleaned) == 0:
            continue

        reader_distance_confidence = binom_confidence(reader_text_cleaned_dist, len(reader_text_cleaned.split()))

        final_crop_text = reader_text_cleaned
        if reader_text_lang == 'rus':
            if reader_distance_confidence < 0.5:
                bbox[bbox < 0] = 0
                crop = img[bottom:top, left:right, :]
                lobster_text_cleaned, lobster_text_cleaned_dist = get_lobster_text_from(crop)
                if len(lobster_text_cleaned) == 0:
                    continue
                lobster_distance_confidence = binom_confidence(lobster_text_cleaned_dist, len(lobster_text_cleaned.split()))
                if lobster_distance_confidence >= 0.3:
                    final_crop_text = lobster_text_cleaned
                else:
                    continue
        elif reader_text_lang  == 'en':
            if reader_distance_confidence < 0.5:
                continue
        final_crop_text = final_crop_text.strip()
        result_text += final_crop_text + ' '
    result_text = result_text.strip()
    if len(result_text) == 0:
        return result_text, 'rus'
    result_text_cleaned, result_lang = get_right_language(result_text)
    result_text_stemmed = preprocess_text(result_text_cleaned, result_lang)
    return result_text_stemmed, result_lang


def get_text_and_embedding(path):
    img = skimage.img_as_float32(io.imread(path))
    if len(img.shape) == 2:
        img = np.concatenate([np.expand_dims(img, axis=0)] * 3, axis=0).transpose(1, 2, 0)
    result_text_stemmed, result_lang = get_text_from_img(img, path)
    text_embedding = embedding_by_text(result_text_stemmed, result_lang)
    return result_text_stemmed, result_lang, text_embedding
