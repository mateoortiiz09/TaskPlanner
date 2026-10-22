"""Registro de eventos de auditoría.

Regla: nunca se guardan nombres de tareas, descripciones, nombres de archivos
ni contraseñas. Solo identificadores numéricos y datos técnicos.
"""

from django.http import Http404

from auditoria.contexto import peticion_actual
from auditoria.models import EventoAuditoria

TAREAS = "tareas"
TECNICA = "tecnica"

ACCIONES = {
    "tarea.creada": (TAREAS, "Tarea creada"),
    "tarea.editada": (TAREAS, "Tarea editada"),
    "tarea.estado_cambiado": (TAREAS, "Estado cambiado"),
    "tarea.completada": (TAREAS, "Tarea completada"),
    "tarea.eliminada": (TAREAS, "Tarea eliminada"),
    "tarea.recuperada": (TAREAS, "Tarea recuperada"),
    "adjunto.subido": (TAREAS, "Adjunto subido"),
    "adjunto.descargado": (TAREAS, "Adjunto descargado"),
    "sesion.iniciada": (TECNICA, "Inicio de sesión"),
    "sesion.fallida": (TECNICA, "Inicio de sesión fallido"),
    "sesion.cerrada": (TECNICA, "Cierre de sesión"),
    "sesion.bloqueada": (TECNICA, "Cuenta bloqueada por intentos"),
    "usuario.creado": (TECNICA, "Usuario creado"),
    "usuario.rol_cambiado": (TECNICA, "Cambio de rol"),
    "usuario.contrasena_restablecida": (TECNICA, "Contraseña restablecida"),
    "usuario.contrasena_cambiada": (TECNICA, "Contraseña cambiada"),
    "acceso.denegado": (TECNICA, "Acceso denegado"),
    "cuentas.recuperar_admin": (TECNICA, "Recuperación administrativa"),
}

_TIPOS_SIMPLES = (str, int, float, bool, type(None), list, dict)


def acciones_de(categoria):
    return [accion for accion, (cat, _) in ACCIONES.items() if cat == categoria]


def etiqueta(accion):
    return ACCIONES.get(accion, (None, accion))[1]


def _ip(request):
    if request is None:
        return None
    return request.META.get("REMOTE_ADDR") or None


def _actor(request):
    usuario = getattr(request, "user", None)
    if usuario is not None and usuario.is_authenticated:
        return usuario
    return None


def registrar_evento(accion, *, actor=None, recurso_tipo="", recurso_id="", **datos):
    if accion not in ACCIONES:
        raise ValueError(f"Acción de auditoría desconocida: {accion}")
    request = peticion_actual()
    if actor is None:
        actor = _actor(request)
    datos = {
        clave: valor if isinstance(valor, _TIPOS_SIMPLES) else str(valor)
        for clave, valor in datos.items()
    }
    return EventoAuditoria.objects.create(
        accion=accion,
        actor=actor,
        ip=_ip(request),
        cambios=datos,
        tipo_recurso=recurso_tipo,
        recurso_id=str(recurso_id) if recurso_id != "" else "",
    )


def denegar(**datos):
    """Registra un acceso denegado y responde 404 (no revela si la tarea existe)."""
    request = peticion_actual()
    if request is not None:
        datos.setdefault("ruta", request.path)
    registrar_evento("acceso.denegado", **datos)
    raise Http404
