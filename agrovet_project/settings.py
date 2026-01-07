import os
from pathlib import Path
import environ

# Initialize environment variables
env = environ.Env(
    DEBUG=(bool, False),
    DJANGO_CORS_ALLOW_ALL=(bool, False),
    EMAIL_USE_TLS=(bool, True),
    EMAIL_PORT=(int, 587)
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Read .env file from the root directory
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# --- CORE SETTINGS ---
SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=['localhost', '127.0.0.1'])

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=["https://11dadfaaa3c2.ngrok-free.app"])

# --- APP DEFINITION ---
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "rest_framework",
    "corsheaders",
    "inventory",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "agrovet_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "agrovet_project.wsgi.application"

# --- DATABASE ---
DATABASES = {
    "default": env.db("DATABASE_URL", default=f"postgres://{env('POSTGRES_USER', default='agrovet')}:{env('POSTGRES_PASSWORD', default='agrovet')}@{env('POSTGRES_HOST', default='db')}:{env('POSTGRES_PORT', default='5432')}/{env('POSTGRES_DB', default='agrovet')}")
}

# --- AUTHENTICATION ---
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Africa/Nairobi"
USE_I18N = True
USE_TZ = True

# --- STATIC & MEDIA FILES ---
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- CORS & REST FRAMEWORK ---
CORS_ALLOW_ALL_ORIGINS = env("DJANGO_CORS_ALLOW_ALL")
if not CORS_ALLOW_ALL_ORIGINS:
    CORS_ALLOWED_ORIGINS = env.list("DJANGO_CORS_ORIGINS", default=["http://localhost:8080"])

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
}

# --- MPESA DARAJA SETTINGS ---
MPESA_CONSUMER_KEY = env('MPESA_CONSUMER_KEY', default='')
MPESA_CONSUMER_SECRET = env('MPESA_CONSUMER_SECRET', default='')
MPESA_PASSKEY = env('MPESA_PASSKEY', default='')
MPESA_SHORTCODE = env('MPESA_SHORTCODE', default='174379')
MPESA_CALLBACK_URL = env('MPESA_CALLBACK_URL', default='')

# --- EMAIL SETTINGS ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = env('EMAIL_HOST', default='smtp.gmail.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=587)
EMAIL_USE_TLS = env.bool('EMAIL_USE_TLS', default=True)
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = f"Agrovet Store <{EMAIL_HOST_USER}>"

# --- AUTH REDIRECTS ---
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/login-redirect/' 
LOGOUT_REDIRECT_URL = '/'