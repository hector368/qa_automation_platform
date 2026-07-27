import os

from .base import *  # noqa: F403


DEBUG = False

SECURE_SSL_REDIRECT = (
    os.getenv("DJANGO_SECURE_SSL_REDIRECT", "1") == "1"
)
SESSION_COOKIE_SECURE = (
    os.getenv("DJANGO_SESSION_COOKIE_SECURE", "1") == "1"
)
CSRF_COOKIE_SECURE = (
    os.getenv("DJANGO_CSRF_COOKIE_SECURE", "1") == "1"
)