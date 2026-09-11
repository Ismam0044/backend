"""
Django settings for config project.
"""

from datetime import timedelta
from pathlib import Path

import dj_database_url
from decouple import Csv, config

BASE_DIR = Path(__file__).resolve().parent.parent

# --- Core / secrets -----------------------------------------------------
SECRET_KEY = config("SECRET_KEY")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())

# --- Error monitoring (Sentry) ---------------------------------------------
# Only active when SENTRY_DSN is actually set, so local dev stays silent by
# default. The `environment` tag still distinguishes dev from prod in the
# Sentry dashboard in case someone sets SENTRY_DSN locally to test.
SENTRY_DSN = config("SENTRY_DSN", default="")
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.django import DjangoIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        environment="production" if not DEBUG else "development",
        traces_sample_rate=0.0,  # error tracking only, no performance tracing
        send_default_pii=False,  # don't ship request headers/IPs to a third party
    )

# --- AI features (Gemini) --------------------------------------------------
# Blank by default so the app still runs (and the check below can give a
# clear error only when someone actually tries to use an AI feature) without
# requiring every environment to have a key.
GEMINI_API_KEY = config("GEMINI_API_KEY", default="")

# --- Applications ---------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "django_htmx",
    "simple_history",
    "axes",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    # local apps
    "core",
    "inventory",
    "parties",
    "sales",
    "purchase",
    "accounts",
    "reports",
    "assistant",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django_htmx.middleware.HtmxMiddleware",
    "simple_history.middleware.HistoryRequestMiddleware",
    "axes.middleware.AxesMiddleware",
]

AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"

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

WSGI_APPLICATION = "config.wsgi.application"

# --- Database ---------------------------------------------------------
# DATABASE_URL examples:
#   local (docker-compose): postgres://erp:erp@db:5432/erp
#   Neon (production):      postgresql://user:pass@ep-xxx.neon.tech/erp?sslmode=require
DATABASES = {
    "default": dj_database_url.config(
        default=config("DATABASE_URL"),
        # Neon's serverless Postgres can silently close idle connections on
        # its end. conn_max_age=0 "fixed" that by never reusing a connection,
        # but that meant a fresh TLS handshake to Neon (cross-region, slow)
        # on every single request - the real cost was reconnecting, not
        # reusing. Keep connections alive for a minute so most requests reuse
        # one, and lean on conn_health_checks to detect + transparently
        # reconnect if Neon closed it before that.
        conn_max_age=60,
        conn_health_checks=True,
        ssl_require=config("DB_SSL_REQUIRE", default=not DEBUG, cast=bool),
    )
}

AUTH_USER_MODEL = "core.User"

# --- Password validation -------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Internationalization -------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "Asia/Dhaka"
USE_I18N = True
USE_TZ = True

# --- Static files -------------------------------------------------
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    # Needed for any FileField/ImageField (e.g. scanned receipt uploads) -
    # Django's STORAGES setting requires an explicit "default" once you
    # override anything here, it doesn't fall back on its own.
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}

# --- Media files (user-uploaded, e.g. scanned receipts) -------------------
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth / login -------------------------------------------------
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "login"

# --- django-axes (brute-force login protection) ---------------------------
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # hours
AXES_LOCKOUT_PARAMETERS = [["ip_address", "username"]]

# --- Security hardening (applies automatically when DEBUG=False) ---------
if not DEBUG:
    SECURE_SSL_REDIRECT = config("SECURE_SSL_REDIRECT", default=True, cast=bool)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    CSRF_TRUSTED_ORIGINS = config("CSRF_TRUSTED_ORIGINS", default="", cast=Csv())

SESSION_COOKIE_AGE = 60 * 60 * 8  # 8 hours; POS terminals shouldn't stay logged in forever
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# --- REST API (mobile app) -------------------------------------------------
# Additive only - session auth above keeps serving the HTMX web app unchanged;
# JWT auth only ever applies under /api/v1/.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "api.pagination.StandardPagination",
    "PAGE_SIZE": 25,
    "EXCEPTION_HANDLER": "api.exceptions.api_exception_handler",
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    # Mirrors the SESSION_COOKIE_AGE reasoning above - POS-style devices
    # shouldn't stay logged in forever.
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=12),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
}
