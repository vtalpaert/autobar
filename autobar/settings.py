"""
Django settings for autobar project.

Generated by 'django-admin startproject' using Django 2.1.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '8e7f2hb2p!ihm!u!&27mq+do-8ek!suao9=$%oywwu!!e6s8zd'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # when True, runserver serves the staticfiles

ALLOWED_HOSTS = ['localhost', 'raspberrypi', 'autobar', '0.0.0.0']  # accept all incoming connections (from local network)


# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'solo',  # config is unique
    'bootstrap',  # add bootstrap to staticfiles
    'widget_tweaks',
    'bootstrap_modal_forms',
    'recipes',  # our models
    #'django_extensions',  # for graph_models
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

ROOT_URLCONF = 'autobar.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
            ],
        },
    },
]

WSGI_APPLICATION = 'autobar.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# Logging for Django
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            'datefmt': "%d/%b/%Y %H:%M:%S"
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': 'autobar.log',  # TODO
            'formatter': 'verbose',
            'when': 'midnight',
            'backupCount': '15',
        },
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
            'level': 'DEBUG',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'ERROR',
        },
        'autobar': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators
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
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en'
TIME_ZONE = 'Europe/Paris'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = 'static'
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'staticfiles'),
)
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
UPLOAD_FOR_MIX = 'mixes'


# Settings for UX behaviour
# moved to recipes.models.Configuration

# PINS in BCM numbering
GPIO_PUMPS = [27, 22, 23, 24, 25, 5, 6, 12, 16, 26]
GPIO_DT = 17
GPIO_SCK = 18
GPIO_RED_BUTTON = 7
GPIO_GREEN_BUTTON = 8
GPIO_GREEN_BUTTON_LED = 13

# WEIGHT MODULE
# moved to recipes.models.Configuration
MAX_MEASURABLE_WEIGHT = 1000  # [g]

# DELAYS and TIMEOUTS
# moved to recipes.models.Configuration

# Handling of units for mass and volume
UNIT_DENSITY = 'g/L'
UNIT_DENSITY_DEFAULT = 1000  # default density for liquids in [UNIT_DENSITY]
UNIT_VOLUME = 'cL'
UNIT_VOLUME_VERBOSE = 'centiliter'
UNIT_MASS = 'g'
FACTOR_VOLUME_TO_MASS = 10  # 1 cL is 10 g

# states
SERVING_STATES_CHOICES = (
    (0, 'Init'),
    (1, 'Press button or place glass to start'),
    (2, 'Serving'),
    (3, 'Finished'),
    (4, 'Abandon'),
)
