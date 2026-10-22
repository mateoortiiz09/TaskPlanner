"""Backend de correo con Microsoft Graph (OAuth 2.0, credenciales de cliente).

Usa solo la librería estándar. El token se guarda en memoria y se renueva
5 minutos antes de vencer; ante un 401 se pide uno nuevo y se reintenta una vez.
"""

import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend

URL_TOKEN = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
URL_ENVIO = "https://graph.microsoft.com/v1.0/users/{remitente}/sendMail"
VARIABLES = (
    "GRAPH_TENANT_ID",
    "GRAPH_CLIENT_ID",
    "GRAPH_CLIENT_SECRET",
    "GRAPH_REMITENTE",
)

_bloqueo = threading.Lock()
_cache = {"token": None, "expira": 0.0}


class ErrorGraph(Exception):
    def __init__(self, mensaje, codigo=None):
        super().__init__(mensaje)
        self.codigo = codigo


def faltantes():
    return [nombre for nombre in VARIABLES if not getattr(settings, nombre, "")]


def _configuracion():
    faltan = faltantes()
    if faltan:
        raise ImproperlyConfigured(
            "Faltan variables de Microsoft Graph: " + ", ".join(faltan)
        )
    return {nombre: getattr(settings, nombre) for nombre in VARIABLES}


def _post(url, cuerpo, cabeceras):
    peticion = urllib.request.Request(
        url, data=cuerpo, headers=cabeceras, method="POST"
    )
    try:
        with urllib.request.urlopen(
            peticion, timeout=settings.EMAIL_TIMEOUT
        ) as respuesta:
            return respuesta.status, respuesta.read()
    except urllib.error.HTTPError as error:
        detalle = error.read().decode("utf-8", "replace")[:500]
        raise ErrorGraph(
            f"Graph respondió {error.code}: {detalle}", codigo=error.code
        ) from error


def obtener_token():
    with _bloqueo:
        if _cache["token"] and time.monotonic() < _cache["expira"]:
            return _cache["token"]
        config = _configuracion()
        cuerpo = urllib.parse.urlencode(
            {
                "client_id": config["GRAPH_CLIENT_ID"],
                "client_secret": config["GRAPH_CLIENT_SECRET"],
                "scope": "https://graph.microsoft.com/.default",
                "grant_type": "client_credentials",
            }
        ).encode("utf-8")
        url = URL_TOKEN.format(
            tenant=urllib.parse.quote(config["GRAPH_TENANT_ID"], safe="")
        )
        _, datos = _post(
            url,
            cuerpo,
            {"Content-Type": "application/x-www-form-urlencoded"},
        )
        respuesta = json.loads(datos)
        _cache["token"] = respuesta["access_token"]
        _cache["expira"] = (
            time.monotonic() + int(respuesta.get("expires_in", 3600)) - 300
        )
        return _cache["token"]


def olvidar_token():
    with _bloqueo:
        _cache["token"] = None
        _cache["expira"] = 0.0


def _destinatarios(direcciones):
    return [{"emailAddress": {"address": direccion}} for direccion in direcciones]


def construir_mensaje(correo):
    html = next(
        (
            contenido
            for contenido, tipo in getattr(correo, "alternatives", [])
            if tipo == "text/html"
        ),
        None,
    )
    return {
        "message": {
            "subject": correo.subject,
            "body": {
                "contentType": "HTML" if html else "Text",
                "content": html or correo.body,
            },
            "toRecipients": _destinatarios(correo.to),
            "ccRecipients": _destinatarios(correo.cc),
            "bccRecipients": _destinatarios(correo.bcc),
        },
        "saveToSentItems": False,
    }


class GraphEmailBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        remitente = _configuracion()["GRAPH_REMITENTE"]
        url = URL_ENVIO.format(remitente=urllib.parse.quote(remitente, safe="@"))
        enviados = 0
        for correo in email_messages:
            try:
                self._enviar(url, correo)
            except Exception:
                if not self.fail_silently:
                    raise
            else:
                enviados += 1
        return enviados

    def _enviar(self, url, correo):
        cuerpo = json.dumps(construir_mensaje(correo)).encode("utf-8")
        for intento in (1, 2):
            cabeceras = {
                "Authorization": f"Bearer {obtener_token()}",
                "Content-Type": "application/json",
            }
            try:
                estado, _ = _post(url, cuerpo, cabeceras)
            except ErrorGraph as error:
                if intento == 1 and error.codigo == 401:
                    olvidar_token()
                    continue
                raise
            if estado != 202:
                raise ErrorGraph(
                    f"Respuesta inesperada de Graph: {estado}", codigo=estado
                )
            return
