from django.conf import settings
from django.core.checks import Error, Tags, Warning, register

from notificaciones.graph import faltantes

BACKEND_GRAPH = "notificaciones.graph.GraphEmailBackend"


@register(Tags.security)
def comprobar_correo(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    if settings.EMAIL_BACKEND == BACKEND_GRAPH:
        faltan = faltantes()
        if faltan:
            return [
                Error(
                    "Faltan variables de Microsoft Graph: " + ", ".join(faltan),
                    hint="Defínelas en el entorno del servidor.",
                    id="notificaciones.E001",
                )
            ]
        return []
    return [
        Warning(
            "El correo de producción no usa Microsoft Graph.",
            hint=f"Define EMAIL_BACKEND={BACKEND_GRAPH}.",
            id="notificaciones.W001",
        )
    ]
