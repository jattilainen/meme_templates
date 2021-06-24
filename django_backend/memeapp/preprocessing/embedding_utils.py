import torch
from navec import Navec
from torch import nn
from django.conf import settings
import os
import numpy as np
import easyocr
import string
import re
from symspellpy import SymSpell
import pkg_resources
from scipy.stats import binom_test
import spacy
from pymystem3 import Mystem
import nltk
from nltk.corpus import stopwords


# consts
EMB_INF = 1e9

filename_navec_data = 'navec_hudlit_v1_12B_500K_300d_100q.tar'
filename_glove_data = 'glove.6B.300d.txt'
filename_rus_dictionary = 'ru-100k.txt'
filename_en_dictionary = pkg_resources.resource_filename('symspellpy', 'frequency_dictionary_en_82_765.txt')

# Load MobileNet
mobilenet = torch.hub.load('pytorch/vision:v0.9.0', 'mobilenet_v2', pretrained=True)
mobilenet.classifier = nn.Sequential(*list(mobilenet.classifier.children())[:-1])
mobilenet.eval()

# Load embeddings
russian_embeddings = Navec.load(os.path.join(settings.MODEL_DATA_PATH, filename_navec_data))
english_embeddings = {}
with open(os.path.join(settings.MODEL_DATA_PATH, filename_glove_data)) as f:
    for line in f:
        values = line.split()
        word = values[0]
        coefs = np.asarray(values[1:], dtype='float32')
        english_embeddings[word] = coefs

# Load easyocr reader
easyocr_reader = easyocr.Reader(['ru', 'en'])

# Load punctuation dict
punctuation_dict = {c : None for c in string.punctuation}

# Load spelling and segmentation
symspell_rus = SymSpell()
symspell_rus.load_dictionary(os.path.join(settings.MODEL_DATA_PATH, filename_rus_dictionary), 0, 1)
symspell_en = SymSpell()
symspell_en.load_dictionary(filename_en_dictionary, 0, 1)

# Load lemmatizers
russian_lemmatizer = Mystem()
english_lemmatizer = spacy.load('en_core_web_sm')

# Load stopwords
nltk.download('stopwords')
russian_stopwords = set(stopwords.words("russian"))
russian_stopwords.add(' ')
english_stopwords = set(stopwords.words('english'))
english_stopwords.add(' ')


# Functions
def clean_punctuation(s):
    table = s.maketrans(punctuation_dict)
    s = s.translate(table)
    return s.strip()


def has_english(text):
    return bool(re.search('[a-zA-Z]', text))


def has_russian(text):
    return bool(re.search('[а-яА-Я]', text))


def get_rid_of_numbers(s):
    new_s = ''
    s = s.split()
    for i in range(len(s)):
        word = s[i]
        if word.isalpha():
            new_s += word
            if i + 1 != len(s):
                new_s += ' '
    return new_s.strip()


def get_right_language(s):
    en_words = ''
    ru_words = ''
    s = s.split()
    for i in range(len(s)):
        word = s[i].lower()
        en, rus = False, False
        if has_english(word):
            en = True
        if has_russian(word):
            rus = True
        if (en and rus) or (not en and not rus):
            continue
        if en:
            en_words += word
            if i + 1 != len(s):
                en_words += ' '
        elif rus:
            ru_words += word
            if i + 1 != len(s):
                ru_words += ' '
    if len(en_words.split()) <= len(ru_words.split()):
        return ru_words.strip(), 'rus'
    else:
        return en_words.strip(), 'en'


def get_clean_text(s):
    s_cleaned = clean_punctuation(s)
    s_cleaned = get_rid_of_numbers(s_cleaned)
    s_cleaned, lang = get_right_language(s_cleaned)
    if len(s_cleaned) == 0:
        return '', None, None
    if lang == 'en':
        try:
            result = symspell_en.word_segmentation(s_cleaned)
        except:
            return '', None, None
    elif lang == 'rus':
        try:
            result = symspell_rus.word_segmentation(s_cleaned)
        except:
            return '', None, None
    return result.corrected_string.strip(), result.distance_sum, lang


def binom_confidence(seq_distance, seq_length):
    return binom_test(seq_distance, seq_distance + seq_length, 0.5, 'greater')


def preprocess_text(text, lang):
    if lang == 'rus':
        tokens = russian_lemmatizer.lemmatize(text)
        tokens = [token for token in tokens if token not in russian_stopwords]
        text = ' '.join(tokens).strip()
    elif lang == 'en':
        tokens = english_lemmatizer(text)
        tokens = [word.lemma_ for word in tokens if word.text not in english_stopwords]
        text = ' '.join(tokens).strip()
    return text

def get_best_fmeasure(lengths, confidences):
    lengths = 0.5 * lengths / lengths.max()
    confidences = 1 - 0.5 * confidences / confidences.max()
    fs = lengths * confidences / (lengths + confidences)
    best_index = fs.argmax()
    return best_index
