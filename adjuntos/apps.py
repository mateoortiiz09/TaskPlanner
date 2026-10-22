from django.apps import AppConfig


class AdjuntosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "adjuntos"

    def ready(self):
        from adjuntos import checks  # noqa: F401
