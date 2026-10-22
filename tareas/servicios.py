from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from auditoria.servicios import registrar_evento
from autorizacion.reglas import puede_editar  # noqa: F401
from tareas.models import (
    Cumplimiento,
    EstadoAvance,
    ResponsableTarea,
    Tarea,
)


class OperacionNoPermitida(Exception):
    """La operación no es válida para el estado actual de la tarea."""


class ConflictoDeVersion(Exception):
    """Otra persona modificó la tarea después de abrir el formulario."""


def _exigir(usuario, permiso):
    if not usuario.has_perm(permiso):
        raise PermissionDenied


def _sincronizar_responsables(tarea, responsables):
    nuevos = {usuario.pk: usuario for usuario in responsables}
    tarea.asignaciones.exclude(usuario_id__in=nuevos).delete()
    existentes = set(tarea.asignaciones.values_list("usuario_id", flat=True))
    for pk, usuario in nuevos.items():
        if pk not in existentes:
            ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
            from notificaciones.servicios import notificar_asignacion

            notificar_asignacion(tarea, usuario)


@transaction.atomic
def crear_tarea(usuario, datos, responsables):
    _exigir(usuario, "tareas.add_tarea")
    if datos.get("restringida"):
        _exigir(usuario, "tareas.reclasificar_sensibilidad")
    tarea = Tarea.objects.create(creada_por=usuario, **datos)
    _sincronizar_responsables(tarea, responsables)
    registrar_evento(
        "tarea.creada",
        actor=usuario,
        tarea_id=tarea.pk,
        restringida=tarea.restringida,
    )
    return tarea


@transaction.atomic
def actualizar_tarea(usuario, tarea_id, datos, responsables, version):
    tarea = Tarea.objects.select_for_update().get(pk=tarea_id)
    era_restringida = tarea.restringida
    if not puede_editar(usuario, tarea):
        raise PermissionDenied
    if tarea.version != version:
        raise ConflictoDeVersion
    if datos.get("restringida", tarea.restringida) != tarea.restringida:
        _exigir(usuario, "tareas.reclasificar_sensibilidad")
    for campo, valor in datos.items():
        setattr(tarea, campo, valor)
    tarea.version += 1
    tarea.save()
    _sincronizar_responsables(tarea, responsables)
    if tarea.restringida and not era_restringida:
        from adjuntos.servicios import cifrar_adjuntos_de_tarea

        cifrar_adjuntos_de_tarea(tarea)
    registrar_evento(
        "tarea.editada",
        actor=usuario,
        tarea_id=tarea.pk,
        restringida=tarea.restringida,
    )
    return tarea


@transaction.atomic
def cambiar_estado(usuario, tarea_id, nuevo_estado):
    _exigir(usuario, "tareas.cambiar_estado")
    tarea = Tarea.objects.select_for_update().get(pk=tarea_id)
    if tarea.eliminada:
        raise OperacionNoPermitida("La tarea está eliminada.")
    if tarea.estado == EstadoAvance.COMPLETADA:
        raise OperacionNoPermitida("Una tarea completada no puede cambiar de estado.")
    if nuevo_estado == EstadoAvance.COMPLETADA:
        return completar_tarea(usuario, tarea_id)
    if nuevo_estado not in (EstadoAvance.PENDIENTE, EstadoAvance.EN_PROCESO):
        raise OperacionNoPermitida("Estado no válido.")
    estado_anterior = tarea.estado
    tarea.estado = nuevo_estado
    tarea.version += 1
    tarea.save(update_fields=["estado", "version", "actualizada_en"])
    registrar_evento(
        "tarea.estado_cambiado",
        actor=usuario,
        tarea_id=tarea.pk,
        estado_anterior=estado_anterior,
        estado_nuevo=tarea.estado,
    )
    return tarea


@transaction.atomic
def completar_tarea(usuario, tarea_id, hoy=None):
    _exigir(usuario, "tareas.completar_tareas")
    tarea = Tarea.objects.select_for_update().get(pk=tarea_id)
    if tarea.eliminada:
        raise OperacionNoPermitida("La tarea está eliminada.")
    if tarea.estado == EstadoAvance.COMPLETADA:
        raise OperacionNoPermitida("La tarea ya está completada.")
    hoy = hoy or timezone.localdate()
    tarea.estado = EstadoAvance.COMPLETADA
    tarea.fecha_finalizacion = hoy
    tarea.completada_por = usuario
    tarea.cumplimiento = (
        Cumplimiento.DENTRO_DEL_PLAZO
        if hoy <= tarea.fecha_limite
        else Cumplimiento.FUERA_DEL_PLAZO
    )
    tarea.version += 1
    tarea.save()
    registrar_evento("tarea.completada", actor=usuario, tarea_id=tarea.pk)
    return tarea


@transaction.atomic
def eliminar_tarea(usuario, tarea_id):
    _exigir(usuario, "tareas.eliminar_recuperar_tareas")
    tarea = Tarea.objects.select_for_update().get(pk=tarea_id)
    if tarea.eliminada:
        raise OperacionNoPermitida("La tarea ya está eliminada.")
    tarea.eliminada_en = timezone.now()
    tarea.eliminada_por = usuario
    tarea.version += 1
    tarea.save()
    registrar_evento("tarea.eliminada", actor=usuario, tarea_id=tarea.pk)
    return tarea


@transaction.atomic
def recuperar_tarea(usuario, tarea_id):
    _exigir(usuario, "tareas.eliminar_recuperar_tareas")
    tarea = Tarea.objects.select_for_update().get(pk=tarea_id)
    if not tarea.eliminada:
        raise OperacionNoPermitida("La tarea no está eliminada.")
    tarea.eliminada_en = None
    tarea.eliminada_por = None
    tarea.version += 1
    tarea.save()
    registrar_evento("tarea.recuperada", actor=usuario, tarea_id=tarea.pk)
    return tarea
