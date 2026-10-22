from django.apps import AppConfig


class NotificacionesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "notificaciones"

    def ready(self):
        from notificaciones import (
            checks,  # noqa: F401
            senales,  # noqa: F401
        )
