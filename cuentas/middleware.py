import time

from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.views import redirect_to_login

CLAVE_INICIO_SESION = "inicio_sesion_ts"


class DuracionMaximaSesionMiddleware:
    """Cierra la sesión al superar la duración máxima, aunque haya actividad."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            ahora = int(time.time())
            inicio = request.session.setdefault(CLAVE_INICIO_SESION, ahora)
            if ahora - inicio > settings.SESION_DURACION_MAXIMA_SEGUNDOS:
                logout(request)
                return redirect_to_login(request.get_full_path())
        return self.get_response(request)
