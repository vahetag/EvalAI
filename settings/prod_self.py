from .common import *  # noqa: ignore=F405

import warnings

# Database
# https://docs.djangoproject.com/en/1.10.2/ref/settings/#databases

AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_DEFAULT_REGION = os.environ.get("AWS_DEFAULT_REGION")

AWS_SES_REGION_NAME = os.environ.get("AWS_SES_REGION_NAME", "us-west-2")
AWS_SES_REGION_ENDPOINT = os.environ.get("AWS_SES_REGION_ENDPOINT", "temp.com")

AWS_STORAGE_BUCKET_NAME = os.environ.get("AWS_STORAGE_BUCKET_NAME")


DEBUG = False

CORS_ORIGIN_ALLOW_ALL = False
IS_STAGING_FLAG = os.environ.get("IS_STAGING", True)

IS_STAGING = True if IS_STAGING_FLAG == "True" else False 

if not IS_STAGING:
    ALLOWED_HOSTS = ["bpc.opencv.org", "35.85.190.203"]
    CORS_ORIGIN_WHITELIST = (
        "http://bpc.opencv.org",
        "https://bpc.opencv.org",
        "https://opencv-bpc-comp-2025.s3-us-west-2.amazonaws.com",
        "https://opencv-bpc-comp-2025.s3.amazonaws.com",
        "http://localhost:8000",  # Django development server
        "http://127.0.0.1:8000",  # Django development server (IPv4)
    )
else:
    ALLOWED_HOSTS = ["bpcstaging.opencv.org", "34.212.81.232", "ec2-34-212-81-232.us-west-2.compute.amazonaws.com"]
    CORS_ORIGIN_WHITELIST = (
        "http://bpcstaging.opencv.org",
        "https://bpcstaging.opencv.org",
        "https://opencv-bpc-comp-2025.s3-us-west-2.amazonaws.com",
        "https://opencv-bpc-comp-2025.s3.amazonaws.com",
        # "http://localhost:8000",  # Django development server
        # "http://127.0.0.1:8000",  # Django development server (IPv4)
        # "http://django:8000",  # Django development server (IPv4)
    )
    

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


print("RDS_DB_NAME", DATABASES["default"]["NAME"])
print("RDS_HOSTNAME", DATABASES["default"]["HOST"])
# print("RDS_PASSWORD", DATABASES["default"]["PASSWORD"])
print("RDS_USERNAME", DATABASES["default"]["USER"])
print("RDS_PORT", DATABASES["default"]["PORT"])

INSTALLED_APPS += ("storages",)  # noqa

USE_S3_FOR_DJANGO_STATIC_AND_MEDIA = os.getenv('USE_S3_FOR_DJANGO_STATIC_AND_MEDIA') == 'True'

if USE_S3_FOR_DJANGO_STATIC_AND_MEDIA:
    ##################### For via AWS S3 
    # Amazon S3 Configurations
    AWS_S3_CUSTOM_DOMAIN = "%s.s3-%s.amazonaws.com" % (AWS_STORAGE_BUCKET_NAME, AWS_DEFAULT_REGION)

    # static files configuration on S3
    if not IS_STAGING:
        STATICFILES_LOCATION = "static"
    else:
        STATICFILES_LOCATION = "staging_static"

    STATICFILES_STORAGE = "settings.custom_storages_2.StaticStorage"
    STATIC_URL = "https://%s/%s/" % (AWS_S3_CUSTOM_DOMAIN, STATICFILES_LOCATION)

    # Media files configuration on S3
    if not IS_STAGING:
        MEDIAFILES_LOCATION = "media"
    else:
        MEDIAFILES_LOCATION = "staging_media"

    MEDIA_URL = "http://%s.s3-%s.amazonaws.com/%s/" % (
        AWS_STORAGE_BUCKET_NAME,
        AWS_DEFAULT_REGION,
        MEDIAFILES_LOCATION,
    )
    DEFAULT_FILE_STORAGE = "settings.custom_storages_2.MediaStorage"
    print("STATIC_URL", STATIC_URL)
    print("MEDIA_URL", MEDIA_URL)
else:
    ##################### For local serving of staticfiles and media 
    STATIC_URL = "/api/static/"
    MEDIA_URL = "/api/media/"

    STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')  # Ensure this line is present
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')  # Optional: Define MEDIA_ROOT if you handle media files
    DEFAULT_FILE_STORAGE = 'django.core.files.storage.FileSystemStorage'
    
    print(f"BASE_DIR: {BASE_DIR}")
    print(f"STATIC_ROOT: {STATIC_ROOT}")
    print(f"MEDIA_ROOT: {MEDIA_ROOT}")



# E-Mail Settings
DEFAULT_FROM_EMAIL = "competition@opencv.org"
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.sendgrid.net"
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD")
# print("EMAIL_HOST_PASSWORD", EMAIL_HOST_PASSWORD)
EMAIL_HOST_USER = "apikey"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
SENDGRID_API_KEY = os.environ.get("EMAIL_HOST_PASSWORD")

# Hide API Docs on production environment
REST_FRAMEWORK_DOCS = {"HIDE_DOCS": True}


CACHES["throttling"] = {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}
CACHES["default"]["LOCATION"] = os.environ.get("MEMCACHED_LOCATION", None)
print('CACHES["default"]["LOCATION"]', CACHES["default"]["LOCATION"])

# https://docs.djangoproject.com/en/1.10/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")


# Prevents Datetime warning by showing errors
warnings.filterwarnings(
    "error",
    r"DateTimeField .* received a naive datetime",
    RuntimeWarning,
    r"django\.db\.models\.fields",
)

print("CELERY_QUEUE_NAME", os.environ.get("CELERY_QUEUE_NAME", None))