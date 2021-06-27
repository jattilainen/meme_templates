"""
Django settings for memerecommend project.

Generated by 'django-admin startproject' using Django 3.0.2.

For more information on this file, see
https://docs.djangoproject.com/en/3.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.0/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_AUTO_FIELD='django.db.models.AutoField'


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ['DJANGO_SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = (os.environ['DJANGO_MODE'].lower() == "debug")

ALLOWED_HOSTS = [os.environ["CURRENT_HOST"]]
print(ALLOWED_HOSTS)


# Application definition

INSTALLED_APPS = [
    'memeapp.apps.MemeappConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'import_export',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'memerecommend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'memerecommend.wsgi.application'

#  Media and static

MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'


# Database
# https://docs.djangoproject.com/en/3.0/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': os.environ['MEMERECOMMEND_DBNAME'],
        'USER': os.environ['MEMERECOMMEND_DBUSER'],
        'PASSWORD': os.environ['MEMERECOMMEND_DBPASSWORD'],
        'HOST': 'localhost',
        'PORT': '',
    }
}


# Password validation
# https://docs.djangoproject.com/en/3.0/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.0/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.0/howto/static-files/

STATIC_ROOT = os.path.join(BASE_DIR, 'static')
STATIC_URL = '/static/'

# Bot Settings

TG_TOKEN = os.environ['MEMERECOMMEND_TGTOKEN']

# Image upload settings

N_START_MEMES = 0
MEMES_FOLDER = "memes"
TEMPLATES_FOLDER = "templates"
TEMP_PATH = os.path.join(MEDIA_ROOT, "temp")
ORIGINS_PATH = os.path.join(BASE_DIR, "memeapp", "origins.json")
MAX_WIDTH_PROPORTION = 4
MAX_HEIGHT_PROPORTION = 3
MAX_IMAGE_SIZE = 1024 * 1024 # IN BYTES
# errors must be negative to avoid conflict with meme.pk
UNKNOWN_UPLOAD_ERROR = -1
TOO_WIDE_ERROR = -2
TOO_HIGH_ERROR = -3
TOO_LARGE_ERROR = -4

# Image registration settings
RANDOM_MODE = 'bias'
RANDOM_NORMAL_MODE = (0, 1)
DIMENSION = 20

# Moderation access

BOT_ADMINS = [
    'Pmolodyk',
    'art591',
    'jattilainen',
    'Sedashov',
]

DEVELOPER_CHAT_ID = -460313219

BOT_MODE = os.getenv("MEMERECOMMEND_BOT_MODE")

# Config
CONFIG = ''

# RECOMMEND MAT' VASHU ENGINE
recommend_engine = ''

# DATA EXTRACTION SETTINGS

DATA_DUMP_DIR = os.path.join(BASE_DIR, 'data_dump')

# MEME_EMBEDDINGS_SETTINGS
TEXT_MAX_LEN = 5000
TEXT_EMBEDDING_SIZE = 300
VISUAL_EMBEDDING_SIZE = 1280  # POTENTIALLY DANGEROUS TO HARDCODE AS TRUE SIZE IS DEFINED IN MOBILENET
VISUAL_PCA_SIZE = 50
TEXT_PCA_SIZE = 50
MODEL_DATA_PATH = os.path.join(BASE_DIR, 'test_models_data')
PCA_DATA_PATH = os.path.join(BASE_DIR, 'pca_models')
TEXT_PCA_PATH_RUS = os.path.join(PCA_DATA_PATH, 'text_pca_rus.pkl')
TEXT_PCA_PATH_EN = os.path.join(PCA_DATA_PATH, 'text_pca_en.pkl')
VIS_PCA_PATH = os.path.join(PCA_DATA_PATH, 'vis_pca.pkl')
QUANT_FIT_NUM = 2000

# QT MODELS SETTINGS
PATH_QT = os.path.join(BASE_DIR, 'qt_models')

PATH_TO_VIS_QT = os.path.join(PATH_QT, 'visual_quantile_transformer.pkl')
PATH_TO_TEXT_RUS_QT = os.path.join(PATH_QT, 'rus_text_quantile_transformer.pkl')
PATH_TO_TEXT_EN_QT = os.path.join(PATH_QT, 'en_text_quantile_transformer.pkl')
