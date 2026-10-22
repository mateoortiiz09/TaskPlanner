"""Comprobaciones que impiden arrancar en producción sin antivirus ni clave."""

from django.conf import settings
from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured

from adjuntos import cifrado


@register(Tags.security)
def comprobar_adjuntos(app_configs, **kwargs):
    if settings.DEBUG:
        return []
    errores = []
    if not settings.ANTIVIRUS_ACTIVO:
        errores.append(
            Error(
                "El antivirus de adjuntos no está activo.",
                hint="Define ANTIVIRUS_ACTIVO=True y ANTIVIRUS_COMANDO.",
                id="adjuntos.E001",
            )
        )
    try:
        cifrado.validar_clave_maestra()
    except ImproperlyConfigured as error:
        errores.append(
            Error(
                str(error),
                hint="Define ADJUNTOS_CLAVE_MAESTRA: 32 bytes en base64 urlsafe.",
                id="adjuntos.E002",
            )
        )
    return errores
