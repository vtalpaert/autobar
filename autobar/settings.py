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
DEBUG = True

ALLOWED_HOSTS = ['localhost', '0.0.0.0']


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'solo',
    'bootstrap',
    'widget_tweaks',
    'bootstrap_modal_forms',
    'recipes',
    'hardware.apps.HardwareConfig',
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
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'propagate': True,
            'level': 'INFO',
        },
        'autobar': {
            'handlers': ['console'],
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


# Settings for the bar configuration
INTERFACE_USE_DUMMY = False
IGNORE_EMPTY_DISPENSER = False

JOYSTICK_NAME = 'DragonRise Inc.   Generic   USB  Joystick  '
BUTTONS_TO_PUMP_MAPPING = {
    2: 0,
    3: 1,
    4: 2,
    5: 3,
    6: 4,
    7: 5,
    8: 6,
    9: 7,
    10: 8,
    11: 9,
}

# PINS
GPIO_INHIBIT1 = 5
GPIO_INHIBIT2 = 16
GPIO_A1 = 6
GPIO_B1 = 12
GPIO_C1 = 13
GPIO_A2 = 26
GPIO_DT = 17
GPIO_SCK = 18

# PINOUT
DEMUX = (
    {
        'inh': GPIO_INHIBIT1,
        'logic': (
            GPIO_A1,
            GPIO_B1,
            GPIO_C1
        ),
    },
    {
        'inh': GPIO_INHIBIT2,
        'logic': (
            GPIO_A2,
        ),
    }
)

PUMPS_NB = sum([2**len(d['logic']) for d in DEMUX])

WEIGHT_CELL_DEFAULT = {
    'A': {
        128: {
            'offset': -125596.5,
            'ratio': -0.0003936631806248245,
        },
        64: {
            'offset': 0,
            'ratio': 1,
        },
    },
    'B': {
        32: {
            'offset': 0,
            'ratio': 1,
        },
    },
}

WEIGHT_CELL_GLASS_DETECTION_VALUE = 10  # value for scale (unit depends on WEIGHT_CELL_DEFAULT)
WEIGHT_CELL_GLASS_DETECTION_TIMEOUT = 10  # [s] abandon glass detection
ALLOW_NO_GLASS_DETECTION = False  # continue if glass not detected
WEIGHT_CELL_SERVING_TIMEOUT = 10  # [s] anomaly while serving threshold
DELAY_BEFORE_SERVING = 2  # [s] delay between glass detection and starting to serve
DELAY_BETWEEN_SERVINGS = 1  # [s] delay between one pump activating and the next one
WEIGHT_CELL_MINIMUM_DETECTION = 1  # smallest detection (unit depends on WEIGHT_CELL_DEFAULT)

# Database settings and parameters
UNIT_DENSITY = 'g/L'
UNIT_DENSITY_DEFAULT = 1000  # default density for liquids in [UNIT_DENSITY]
UNIT_VOLUME = 'cL'
UNIT_VOLUME_VERBOSE = 'centiliter'
UNIT_MASS = 'g'
UNIT_CONVERSION_VOLUME_SI = 1e-2  # from UNIT_VOLUME to SI
UNIT_MASS_TO_VOLUME = UNIT_DENSITY_DEFAULT / UNIT_CONVERSION_VOLUME_SI  # 1 cL is 10 g

# hardware states
INTERFACE_STATES = {
    0: 'Ready to serve',
    1: 'Manual control',
    2: 'Mixing',
}

SERVING_STATES_CHOICES = (
    (0, 'Empty'),
    (1, 'Waiting for glass'),
    (2, 'Serving'),
    (3, 'Done'),
)
DONE_SERVING_VALUE = SERVING_STATES_CHOICES[-1][0]
