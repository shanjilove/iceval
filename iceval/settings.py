"""
Django settings for iceval project.

Generated by 'django-admin startproject' using Django 4.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.2/ref/settings/
"""

import os
import contextlib
from dotenv import load_dotenv
from pathlib import Path


# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Build paths inside the project like this: BASE_DIR / 'subdir'.

ENV_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 根据运行环境加载不同的 .env 文件
if os.environ.get('ENV') == 'prod':
    dotenv_path = os.path.join(ENV_BASE_DIR, '.env.prod')
else:
    dotenv_path = os.path.join(ENV_BASE_DIR, '.env.local')

load_dotenv(dotenv_path)

# 自定义的User Model
AUTH_USER_MODEL = 'user.User'

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    # 'rest_framework.authtoken',
    'corsheaders',
    'django_extensions',
    'django_filters',
    'django_celery_beat',
    'user.apps.UserConfig',
    'iceval_app.apps.IcevalConfig',
    'service',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    "corsheaders.middleware.CorsMiddleware",
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'iceval.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'iceval.wsgi.application'


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

#iceval_app
DIANCHACHA_POSTGRES_HOST = os.environ.get('DIANCHACHA_POSTGRES_HOST')
DIANCHACHA_POSTGRES_PORT = os.environ.get('DIANCHACHA_POSTGRES_PORT')
DIANCHACHA_POSTGRES_PASSWORD = os.environ.get('DIANCHACHA_POSTGRES_PASSWORD')
DIANCHACHA_POSTGRES_USER = os.environ.get('DIANCHACHA_POSTGRES_USER')
DIANCHACHA_POSTGRES_DB_NAME = os.environ.get('DIANCHACHA_POSTGRES_DB_NAME')

# 这些本来也最好放在local_settings.py里的，不过太难写了，干脆作为默认写在这里吧
DB_NAME = os.getenv('DB_NAME', 'iceval')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', 5432)
DB_USER = os.getenv('DB_USER', 'iceval')
DB_PASS = os.getenv('DB_PASS', '********')

pgpass_fname = os.path.expanduser('~/.pgpass')
if os.path.exists(pgpass_fname):
    import re

    with open(pgpass_fname) as pgpass_f:
        for line in pgpass_f:
            line = line.strip()
            m = re.match(r'.*:.*:.*:{}:(.*)'.format(DB_USER), line)
            if m:
                DB_PASS = m.group(1)
                break

DATABASES = {
    'default': {
        'ENGINE': 'django.contrib.gis.db.backends.postgis',
        'NAME': DB_NAME,
        'HOST': DB_HOST,
        'PORT': DB_PORT,
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

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

# DRF

REST_FRAMEWORK = {
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "DATETIME_INPUT_FORMATS": ["%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", 'iso-8601'],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        # 'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}

# CELERY

REDIS_DB = int(os.getenv(f'REDIS_DB', 1))

CELERY_TIMEZONE = "Asia/Shanghai"

CELERY_TASK_DEFAULT_QUEUE = os.getenv(f'CELERY_TASK_DEFAULT_QUEUE', 'iceval')
CELERY_RESULT_BACKEND = os.getenv(f'CELERY_RESULT_BACKEND', f'redis://localhost/{REDIS_DB}')
if not CELERY_RESULT_BACKEND or CELERY_RESULT_BACKEND.upper() == 'NONE':
    CELERY_RESULT_BACKEND = None

CELERY_BROKER_URL = os.getenv(f'CELERY_BROKER_URL', f'redis://localhost/{REDIS_DB}')
# CELERY_BROKER_POOL_LIMIT = int(os.getenv(f'{PROJECT_NAME_UPPER}_BROKER_POOL_LIMIT', 100))
# CELERY_BROKER_TRANSPORT_OPTIONS = {
#     "visibility_timeout": int(os.getenv(f'{PROJECT_NAME_UPPER}_BROKER_VISIBILITY_TIMEOUT', 86400))
# }


# CORS HEADERS

CORS_ALLOW_ALL_ORIGINS = True

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = 'static/'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

PROJECT_RUNDIR = os.getenv(f'PROJECT_RUNDIR', '/home/shanji/vol/iceval')

STATIC_ROOT = os.path.join(PROJECT_RUNDIR, 'http/static')

# Local Settings
try:
    from .local_settings import *
except ImportError:
    pass