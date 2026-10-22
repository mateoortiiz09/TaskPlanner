"""Guarda la petición en curso para que la auditoría conozca actor e IP."""

from contextvars import ContextVar

from django.core.exceptions import PermissionDenied

_peticion = ContextVar("peticion_auditoria", default=None)


def peticion_actual():
    return _peticion.get()


class ContextoAuditoriaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        token = _peticion.set(request)
        try:
            return self.get_response(request)
        finally:
            _peticion.reset(token)

    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            from auditoria.servicios import registrar_evento

            registrar_evento("acceso.denegado", ruta=request.path, motivo="sin_permiso")
        return None
