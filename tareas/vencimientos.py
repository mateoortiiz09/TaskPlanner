"""Única fuente de verdad para la situación temporal de las tareas.

Los plazos se cuentan en días calendario y en la zona horaria del proyecto
(America/Bogota). La fecha límite cuenta completa: una tarea que vence hoy
está en riesgo todo el día y pasa a atrasada al día siguiente.
"""

import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from tareas.models import EstadoAvance


class SituacionTemporal(models.TextChoices):
    EN_TIEMPO = "EN_TIEMPO", "En tiempo"
    EN_RIESGO = "EN_RIESGO", "En riesgo"
    ATRASADA = "ATRASADA", "Atrasada"
    COMPLETADA = "COMPLETADA", "Completada"


def hoy_local():
    return timezone.localdate()


def dias_en_riesgo():
    return settings.DIAS_EN_RIESGO


def dias_restantes(tarea, hoy=None):
    """Días hasta la fecha límite; negativo si ya venció."""
    hoy = hoy or hoy_local()
    return (tarea.fecha_limite - hoy).days


def calcular_situacion(tarea, hoy=None):
    if tarea.estado == EstadoAvance.COMPLETADA:
        return SituacionTemporal.COMPLETADA
    restantes = dias_restantes(tarea, hoy)
    if restantes < 0:
        return SituacionTemporal.ATRASADA
    if restantes <= dias_en_riesgo():
        return SituacionTemporal.EN_RIESGO
    return SituacionTemporal.EN_TIEMPO


def filtro_situacion(situacion, hoy=None):
    """Condición de base de datos equivalente a calcular_situacion."""
    hoy = hoy or hoy_local()
    limite_riesgo = hoy + datetime.timedelta(days=dias_en_riesgo())
    no_completada = ~Q(estado=EstadoAvance.COMPLETADA)
    if situacion == SituacionTemporal.COMPLETADA:
        return Q(estado=EstadoAvance.COMPLETADA)
    if situacion == SituacionTemporal.ATRASADA:
        return no_completada & Q(fecha_limite__lt=hoy)
    if situacion == SituacionTemporal.EN_RIESGO:
        return no_completada & Q(fecha_limite__gte=hoy, fecha_limite__lte=limite_riesgo)
    if situacion == SituacionTemporal.EN_TIEMPO:
        return no_completada & Q(fecha_limite__gt=limite_riesgo)
    raise ValueError(f"Situación desconocida: {situacion}")
