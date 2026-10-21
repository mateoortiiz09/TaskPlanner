from .base import *  # noqa: F403
from .base import required_env

DEBUG = False

ALLOWED_HOSTS = [
    host.strip() for host in required_env("ALLOWED_HOSTS").split(",") if host.strip()
]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
