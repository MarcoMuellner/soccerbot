import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# example) SQLite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

INSTALLED_APPS = (
    'api_v2.obj',
)

SECRET_KEY = 'REPLACE_ME'
USE_TZ=True