from .settings import *

DEBUG = False

ALLOWED_HOSTS = [
    'wheat-chamois-361263.hostingersite.com',
    '.hostingersite.com',
    'localhost',
]

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'u901471736_punto_venta',
        'USER': 'u901471736_pventa_usuario',
        'PASSWORD': 'r$RUMpiou!5U',
        'HOST': 'srv1076.hstgr.io',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

STATIC_ROOT = BASE_DIR / "staticfiles"
