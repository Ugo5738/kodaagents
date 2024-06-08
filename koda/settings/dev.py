from .base import *

DEBUG = True
ALLOWED_HOSTS = ["*"]


# ================================ SUPERUSER =======================================
ADMIN_USERNAME = config("ADMIN_USERNAME")
ADMIN_EMAIL = config("ADMIN_EMAIL")
ADMIN_PASSWORD = config("ADMIN_PASSWORD")
# ================================ SUPERUSER =======================================

# ================================ DATABASES =======================================
# DATABASES = {
#     "default": dj_database_url.config(
#         default="postgres://aiagency_dan:ai_@1st@postgres:5432/aiagency_db",
#         conn_max_age=600,
#     ),
# }

DATABASES = {
    "default": dj_database_url.config(default="sqlite:///db.sqlite3", conn_max_age=600)
}

# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }
# ================================ DATABASES =======================================


# ================================ STORAGES =======================================
# ==> STATIC FILE UPLOADS
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]

# ==> MEDIA FILE UPLOADS
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"
# ================================ STORAGES =======================================


# ================================ EMAIL =======================================
# EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# EMAIL_HOST = 'smtp.office365.com'  # 'smtp.outlook.office365.com'
# EMAIL_PORT = 587  # 465  # TLS port
# EMAIL_USE_TLS = True
# # EMAIL_USE_SSL = True
# EMAIL_HOST_USER = config("EMAIL")
# EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD")
# DEFAULT_FROM_EMAIL = config("EMAIL")
# ================================ EMAIL =======================================


# ================================ REDIS/CHANNELS =======================================
# ==> REDIS
REDIS_IP = "redis"
REDIS_PORT = 6379

# ==> CHANNELS
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#     }
# }
CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
# ================================ REDIS =======================================


# ================================ CELERY =======================================
# Use the actual IP address and port of your Redis server
CELERY_BROKER_URL = f"redis://{REDIS_IP}:{REDIS_PORT}/0"
CELERY_RESULT_BACKEND = f"redis://{REDIS_IP}:{REDIS_PORT}/0"
CELERY_TIMEZONE = "UTC"

# List of modules to import when the Celery worker starts.
CELERY_IMPORTS = ("koda.tasks",)

# If using JSON as the serialization format
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
# ================================ CELERY =======================================


# ================================ PAYSTACK =======================================
# PAYSTACK_PUBLIC_KEY=config("PAYSTACK_TEST_PUBLIC_KEY")
# PAYSTACK_SECRET_KEY=config("PAYSTACK_TEST_SECRET_KEY")
# ================================ PAYSTACK =======================================
