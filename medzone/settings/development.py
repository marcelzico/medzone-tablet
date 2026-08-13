from .base import *
from decouple import config, Csv

DEBUG = True
ALLOWED_HOSTS = ['*', '127.0.0.1']  # convenient for local network testing

# Use console email in dev
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
# FOR PRODUCTION


# FOR DEVELOPMENT
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.mysql',
#         'NAME': 'medzone_simple',
#         'USER': 'root',
#         'PASSWORD': 'ocizzi13',
#         'HOST': 'localhost',
#         'PORT': '3306',
#         'OPTIONS': {
#             'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
#             'charset': 'utf8mb4',
#         },
#         'TIME_ZONE': 'UTC',
#     }
# }


BASE_DIR = Path(__file__).resolve().parent.parent

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
