from .common import *  # noqa: ignore=F405

import warnings

# Database
# https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

DEBUG = True

ALLOWED_HOSTS = ["*"]


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


# DJANGO-SPAGHETTI-AND-MEATBALLS SETTINGS
INSTALLED_APPS += [  # noqa: ignore=F405
    "django_spaghetti",
    "autofixture",
    "debug_toolbar",
    "django_extensions",
    "silk",
]

SPAGHETTI_SAUCE = {
    "apps": [
        "auth",
        "accounts",
        "analytics",
        "base",
        "challenges",
        "hosts",
        "jobs",
        "participants",
        "web",
    ],
    "show_fields": True,
}

# CACHES = {
#     # "default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"},
#     # "throttling": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"},
# }
CACHES["throttling"] = {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
CACHES["default"]["LOCATION"] = os.environ.get("MEMCACHED_LOCATION", None)

STATIC_URL = "/api/static/"
MEDIA_URL = "/api/media/"

MIDDLEWARE += [  # noqa: ignore=F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "silk.middleware.SilkyMiddleware",
]

SILKY_PYTHON_PROFILER = True

# Prevents Datetime warning by showing errors
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"


# E-Mail Settings
DEFAULT_FROM_EMAIL = "competition@opencv.org"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
# print("EMAIL_HOST_PASSWORD", EMAIL_HOST_PASSWORD)
EMAIL_HOST_USER = "apikey"
EMAIL_PORT = 587
EMAIL_USE_TLS = True

STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Ensure this line is present
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Optional: Define MEDIA_ROOT if you handle media files
print(f"BASE_DIR: {BASE_DIR}")
print(f"STATIC_ROOT: {STATIC_ROOT}")
print(f"MEDIA_ROOT: {MEDIA_ROOT}")

# from .common import *  # noqa: ignore=F405

# import warnings

# # Database
# # https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

# DEBUG = False

# ALLOWED_HOSTS = ["*"]


# DATABASES = {
#     "default": {
#         "ENGINE": "django.db.backends.postgresql_psycopg2",
#         "NAME": os.environ.get("POSTGRES_NAME", "evalai"),  # noqa: ignore=F405
#         "USER": os.environ.get(  # noqa: ignore=F405
#             "POSTGRES_USER", "postgres"
#         ),  # noqa: ignore=F405
#         "PASSWORD": os.environ.get(  # noqa: ignore=F405
#             "POSTGRES_PASSWORD", "postgres"
#         ),  # noqa: ignore=F405
#         "HOST": os.environ.get(  # noqa: ignore=F405
#             "POSTGRES_HOST", "localhost"
#         ),  # noqa: ignore=F405
#         "PORT": os.environ.get("POSTGRES_PORT", 5432),  # noqa: ignore=F405
#     }
# }

# # E-Mail Settings
# DEFAULT_FROM_EMAIL = "competition@opencv.org"
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
# EMAIL_HOST = "smtp.sendgrid.net"
# EMAIL_HOST_PASSWORD = "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"
# EMAIL_HOST_USER = "apikey"
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True

# ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"

# # Static files (CSS, JavaScript, Images)
# STATIC_URL = "/api/static/"
# MEDIA_URL = "/api/media/"
# STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Ensure this line is present
# MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Optional: Define MEDIA_ROOT if you handle media files
# print(f"BASE_DIR: {BASE_DIR}")
# print(f"STATIC_ROOT: {STATIC_ROOT}")

# # Prevents Datetime warning by showing errors
# warnings.filterwarnings(
#     "error",
#     r"DateTimeField .* received a naive datetime",
#     RuntimeWarning,
#     r"django\.db\.models\.fields",
# )

# # =----------------------------------------------------------------

# CORS_ORIGIN_ALLOW_ALL = False

# CORS_ORIGIN_WHITELIST = (
#     "http://bpc.opencv.org",
#     "https://bpc.opencv.org",
#     "http://localhost:8000",  # Django development server
#     "http://127.0.0.1:8000",  # Django development server (IPv4)
# )

# ACCOUNT_DEFAULT_HTTP_PROTOCOL = "http"



# # Creates issue with normal work
# CACHES["default"]["LOCATION"] = os.environ.get("MEMCACHED_LOCATION", None)
# print('CACHES["default"]["LOCATION"]', CACHES["default"]["LOCATION"])


# # Use local storage
# STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.StaticFilesStorage'
# # STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.CompressedManifestStaticFilesStorage'
# DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'


# # Hide API Docs on production environment
# REST_FRAMEWORK_DOCS = {"HIDE_DOCS": True}

# # # # https://docs.djangoproject.com/en/1.10/ref/settings/#secure-proxy-ssl-header
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")