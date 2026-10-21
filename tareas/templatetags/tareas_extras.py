from django import template

from tareas.models import EstadoAvance
from tareas.vencimientos import SituacionTemporal, calcular_situacion, dias_restantes

register = template.Library()

CLASES_SITUACION = {
    SituacionTemporal.EN_TIEMPO: "text-bg-success",
    SituacionTemporal.EN_RIESGO: "text-bg-warning",
    SituacionTemporal.ATRASADA: "text-bg-danger",
    SituacionTemporal.COMPLETADA: "text-bg-secondary",
}


@register.filter
def situacion(tarea):
    return calcular_situacion(tarea).label


@register.filter
def situacion_clase(tarea):
    return CLASES_SITUACION[calcular_situacion(tarea)]


@register.filter
def texto_vencimiento(tarea):
    if tarea.estado == EstadoAvance.COMPLETADA:
        return ""
    dias = dias_restantes(tarea)
    if dias < -1:
        return f"Venció hace {-dias} días"
    if dias == -1:
        return "Venció ayer"
    if dias == 0:
        return "Vence hoy"
    if dias == 1:
        return "Vence mañana"
    return f"Faltan {dias} días"


@register.filter
def areas_de(tarea):
    areas = []
    for asignacion in tarea.asignaciones.all():
        if asignacion.area not in areas:
            areas.append(asignacion.area)
    return ", ".join(str(area) for area in areas)
