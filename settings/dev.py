from .common import *  # noqa: ignore=F405

import warnings

# Database
# https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

DEBUG = False

ALLOWED_HOSTS = ["bpc.opencv.org"]


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql_psycopg2",
        "NAME": os.environ.get("POSTGRES_NAME", "evalai"),  # noqa: ignore=F405
        "USER": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_USER", "postgres"
        ),  # noqa: ignore=F405
        "PASSWORD": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_PASSWORD", "postgres"
        ),  # noqa: ignore=F405
        "HOST": os.environ.get(  # noqa: ignore=F405
            "POSTGRES_HOST", "localhost"
        ),  # noqa: ignore=F405
        "PORT": os.environ.get("POSTGRES_PORT", 5432),  # noqa: ignore=F405
    }
}

# E-Mail Settings
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/api/static/"
MEDIA_URL = "/api/media/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Ensure this line is present
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Optional: Define MEDIA_ROOT if you handle media files
print(f"BASE_DIR: {BASE_DIR}")
print(f"STATIC_ROOT: {STATIC_ROOT}")

# Prevents Datetime warning by showing errors
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

# =----------------------------------------------------------------

CORS_ORIGIN_ALLOW_ALL = False

CORS_ORIGIN_WHITELIST = (
    "http://bpc.opencv.org",
    "https://bpc.opencv.org",
)
# E-Mail Settings
EMAIL_HOST = "localhost"
EMAIL_PORT = 1025
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"


# Creates issue with normal work
CACHES["default"]["LOCATION"] = os.environ.get("MEMCACHED_LOCATION", None)
print('CACHES["default"]["LOCATION"]', CACHES["default"]["LOCATION"])


# Use local storage
STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
# STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CompressedManifestStaticFilesStorage'
DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# Hide API Docs on production environment
REST_FRAMEWORK_DOCS = {"HIDE_DOCS": True}

# # # https://docs.djangoproject.com/en/1.10/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")