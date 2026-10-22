"""Reglas de acceso a las tareas: única fuente de verdad para permisos por tarea.

- La Subgerente ve todas las tareas y su contenido, incluidas las restringidas.
- El Administrador ve todas las tareas, pero las restringidas solo enmascaradas:
  no ve su nombre, descripción, responsables ni archivos.
- Los líderes solo ven las tareas donde son responsables, restringidas o no.
"""

from tareas.models import EstadoAvance, Tarea


def ve_todas_las_tareas(usuario):
    return usuario.has_perm("tareas.ver_todas_las_tareas")


def tareas_visibles(usuario, eliminadas=False):
    tareas = Tarea.objects.filter(eliminada_en__isnull=not eliminadas)
    if ve_todas_las_tareas(usuario):
        return tareas
    return tareas.filter(responsables=usuario).distinct()


def es_responsable(usuario, tarea):
    return any(
        asignacion.usuario_id == usuario.pk for asignacion in tarea.asignaciones.all()
    )


def puede_ver_tarea(usuario, tarea):
    return ve_todas_las_tareas(usuario) or es_responsable(usuario, tarea)


def puede_ver_contenido(usuario, tarea):
    if not puede_ver_tarea(usuario, tarea):
        return False
    if not tarea.restringida:
        return True
    if ve_todas_las_tareas(usuario):
        return usuario.has_perm("tareas.ver_restringidas")
    return es_responsable(usuario, tarea)


def puede_editar(usuario, tarea):
    if tarea.eliminada or tarea.estado == EstadoAvance.COMPLETADA:
        return False
    if not usuario.has_perm("tareas.change_tarea"):
        return False
    return puede_ver_contenido(usuario, tarea)
