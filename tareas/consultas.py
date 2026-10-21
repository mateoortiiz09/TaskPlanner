from tareas.models import Tarea


def tareas_visibles(usuario, eliminadas=False):
    """Tareas que el usuario puede consultar.

    Provisional hasta la fase 10: todavía no aplica las reglas de nivel 3.
    """
    tareas = Tarea.objects.filter(eliminada_en__isnull=not eliminadas)
    if usuario.has_perm("tareas.ver_todas_las_tareas"):
        return tareas
    return tareas.filter(responsables=usuario).distinct()
