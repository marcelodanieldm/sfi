import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

# ── Seguridad ────────────────────────────────────────────────────────────────
SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-insecure-key-cambiar-en-produccion')
DEBUG      = os.environ.get('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# ── Aplicaciones ─────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'skillsforit.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS':    [BASE_DIR / 'core' / 'templates'],
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

WSGI_APPLICATION = 'skillsforit.wsgi.application'

# ── Base de datos ─────────────────────────────────────────────────────────────
# En Railway se setea DATABASE_URL automáticamente al agregar PostgreSQL.
# En local usa SQLite.
DATABASE_URL = os.environ.get('DATABASE_URL', '')

if DATABASE_URL:
    import dj_database_url
    DATABASES = {'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME':   BASE_DIR / 'db.sqlite3',
        }
    }

# ── Auth ──────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = 'core.User'
LOGIN_URL       = '/login/'
LOGIN_REDIRECT_URL = '/mentoria/'

AUTHENTICATION_BACKENDS = [
    'core.controllers.auth_controller.EmailBackend',
    'django.contrib.auth.backends.ModelBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── Internacionalización ──────────────────────────────────────────────────────
LANGUAGE_CODE = 'es-ar'
TIME_ZONE     = 'America/Argentina/Buenos_Aires'
USE_I18N      = True
USE_TZ        = True

# ── Archivos estáticos ────────────────────────────────────────────────────────
STATIC_URL  = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── CSRF ──────────────────────────────────────────────────────────────────────
CSRF_TRUSTED_ORIGINS = os.environ.get(
    'CSRF_TRUSTED_ORIGINS',
    'https://skillsforit.online,https://*.railway.app',
).split(',')

# ── Seguridad en producción ───────────────────────────────────────────────────
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_COOKIE_SECURE   = True
    CSRF_COOKIE_SECURE      = True

# ── Claves de terceros (desde variables de entorno) ───────────────────────────
OPENAI_API_KEY      = os.environ.get('OPENAI_API_KEY', '')
RESEND_API_KEY      = os.environ.get('RESEND_API_KEY', '')
DEFAULT_FROM_EMAIL  = os.environ.get('DEFAULT_FROM_EMAIL', 'SkillsForIT <info@skillsforit.com>')
EBOOK_WELCOME_COUPON = os.environ.get('EBOOK_WELCOME_COUPON', 'SKILLS20')
SUPPORT_URL         = os.environ.get('SUPPORT_URL', 'https://skillsforit.online/soporte/')
SITE_URL            = os.environ.get('SITE_URL', 'https://skillsforit.online')

STRIPE_SECRET_KEY            = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_WEBHOOK_SECRET        = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_MENTORIA_PRICE_ID     = os.environ.get('STRIPE_MENTORIA_PRICE_ID', '')
STRIPE_MENTORIA_WEBHOOK_SECRET = os.environ.get('STRIPE_MENTORIA_WEBHOOK_SECRET', '')

MP_ACCESS_TOKEN          = os.environ.get('MP_ACCESS_TOKEN', '')
MP_WEBHOOK_SECRET        = os.environ.get('MP_WEBHOOK_SECRET', '')
MP_PREAPPROVAL_PLAN_ID   = os.environ.get('MP_PREAPPROVAL_PLAN_ID', '')
MP_SUBSCRIPTION_AMOUNT   = os.environ.get('MP_SUBSCRIPTION_AMOUNT', '9990')
MP_SUBSCRIPTION_CURRENCY = os.environ.get('MP_SUBSCRIPTION_CURRENCY', 'ARS')

HOTMART_WEBHOOK_TOKEN = os.environ.get('HOTMART_WEBHOOK_TOKEN', '')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
