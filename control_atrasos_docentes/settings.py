from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent

# =========================================================
# SEGURIDAD
# =========================================================

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-cambiar-esto-en-produccion"
)

# En local debe estar en True para facilitar carga de static y depuración.
# En PythonAnywhere / producción lo puedes volver a False.
DEBUG = True

ALLOWED_HOSTS = [
    "127.0.0.1",
    "localhost",
    "cmoscoso.pythonanywhere.com",
]

# =========================================================
# APLICACIONES
# =========================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "atrasos",
]

# =========================================================
# MIDDLEWARE
# =========================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    # WhiteNoise
    "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "control_atrasos_docentes.urls"

# =========================================================
# TEMPLATES
# =========================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "control_atrasos_docentes.wsgi.application"

# =========================================================
# BASE DE DATOS
# =========================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# =========================================================
# PASSWORDS
# =========================================================

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# =========================================================
# LOCALIZACIÓN
# =========================================================

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"

USE_I18N = True
USE_TZ = True

# =========================================================
# ARCHIVOS ESTÁTICOS
# =========================================================

STATIC_URL = "/static/"

# Django buscará estáticos dentro de las apps, por ejemplo:
# atrasos/static/atrasos/css/login.css
STATIC_ROOT = BASE_DIR / "staticfiles"

# Esto ayuda en local y mantiene clara la búsqueda de estáticos del proyecto
STATICFILES_DIRS = []

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# =========================================================
# MEDIA
# =========================================================

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =========================================================
# AUTENTICACIÓN
# =========================================================

LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"

# =========================================================
# SESIONES
# =========================================================

SESSION_COOKIE_AGE = 600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True

# =========================================================
# SSO INTERNO
# =========================================================

SSO_CLAVE_COMPARTIDA = "INACAP_ARICA_SSO_2026_ACCESO_INTERNO"

# =========================================================
# DEFAULT
# =========================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"