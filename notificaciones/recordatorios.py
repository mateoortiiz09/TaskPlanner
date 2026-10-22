"""Generación de recordatorios de vencimiento.

Se ejecuta cada hora desde NOTIFICACIONES_HORA_INICIO. Es idempotente: la clave
única de cada recordatorio evita duplicados aunque se ejecute varias veces.
La clave incluye la fecha límite, así que cambiarla genera recordatorios nuevos.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

from notificaciones.models import TipoNotificacion
from notificaciones.servicios import encolar
from tareas.models import EstadoAvance, Tarea


def _tipo_y_clave(tarea, hoy):
    dias = (tarea.fecha_limite - hoy).days
    if dias == 1:
        return (
            TipoNotificacion.DIA_ANTERIOR,
            f"previo:{tarea.pk}:{tarea.fecha_limite}",
        )
    if dias == 0:
        return (
            TipoNotificacion.VENCIMIENTO,
            f"hoy:{tarea.pk}:{tarea.fecha_limite}",
        )
    if dias == -1:
        return (
            TipoNotificacion.ATRASO,
            f"atraso:{tarea.pk}:{tarea.fecha_limite}",
        )
    atraso = -dias
    if atraso > 1 and (atraso - 1) % 7 == 0:
        return (
            TipoNotificacion.ATRASO_SEMANAL,
            f"semanal:{tarea.pk}:{hoy.isoformat()}",
        )
    return None, None


def generar_recordatorios(hoy=None, forzar=False):
    ahora = timezone.localtime()
    if not forzar and ahora.hour < settings.NOTIFICACIONES_HORA_INICIO:
        return 0
    hoy = hoy or ahora.date()
    subgerentes = list(
        get_user_model()
        .objects.filter(groups__name="Subgerente", is_active=True)
        .distinct()
    )
    tareas = (
        Tarea.objects.filter(
            eliminada_en__isnull=True, fecha_limite__lte=hoy + timedelta(days=1)
        )
        .exclude(estado=EstadoAvance.COMPLETADA)
        .prefetch_related("asignaciones__usuario")
    )
    creadas = 0
    for tarea in tareas:
        tipo, base = _tipo_y_clave(tarea, hoy)
        if tipo is None:
            continue
        destinatarios = {asignacion.usuario for asignacion in tarea.asignaciones.all()}
        if tipo == TipoNotificacion.ATRASO_SEMANAL:
            destinatarios.update(subgerentes)
        for usuario in destinatarios:
            if encolar(
                tipo=tipo,
                destinatario=usuario,
                tarea=tarea,
                clave_unica=f"{base}:{usuario.pk}",
            ):
                creadas += 1
    return creadas
