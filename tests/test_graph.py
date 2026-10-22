import json

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.core.management import call_command

from cuentas.models import Usuario
from notificaciones import graph, servicios
from notificaciones.checks import comprobar_correo
from notificaciones.models import EstadoNotificacion, Notificacion, TipoNotificacion

BACKEND = "notificaciones.graph.GraphEmailBackend"


@pytest.fixture(autouse=True)
def configuracion_graph(settings):
    settings.EMAIL_BACKEND = BACKEND
    settings.GRAPH_TENANT_ID = "inquilino-prueba"
    settings.GRAPH_CLIENT_ID = "cliente-prueba"
    settings.GRAPH_CLIENT_SECRET = "secreto-prueba"
    settings.GRAPH_REMITENTE = "notificaciones@proscience.local"
    graph.olvidar_token()
    yield
    graph.olvidar_token()


class GraphFalso:
    """Simula Microsoft Graph y guarda las peticiones recibidas."""

    def __init__(self, respuestas_envio=None):
        self.peticiones = []
        self.respuestas_envio = list(respuestas_envio or [202])
        self.tokens = 0

    def __call__(self, url, cuerpo, cabeceras):
        self.peticiones.append((url, cuerpo, cabeceras))
        if "oauth2" in url:
            self.tokens += 1
            datos = {"access_token": f"token-{self.tokens}", "expires_in": 3600}
            return 200, json.dumps(datos).encode()
        codigo = self.respuestas_envio.pop(0) if self.respuestas_envio else 202
        if codigo >= 400:
            raise graph.ErrorGraph(f"Graph respondió {codigo}: error", codigo=codigo)
        return codigo, b""

    def envios(self):
        return [peticion for peticion in self.peticiones if "sendMail" in peticion[0]]


def correo_de_prueba():
    correo = EmailMultiAlternatives(
        "Asunto de prueba",
        "Texto plano",
        "notificaciones@proscience.local",
        ["lider@ejemplo.local"],
    )
    correo.attach_alternative("<p>Texto HTML</p>", "text/html")
    return correo


def test_envia_con_token_y_mensaje_correcto(monkeypatch):
    falso = GraphFalso()
    monkeypatch.setattr(graph, "_post", falso)
    assert graph.GraphEmailBackend().send_messages([correo_de_prueba()]) == 1
    url, cuerpo, cabeceras = falso.envios()[0]
    assert url.endswith("/users/notificaciones@proscience.local/sendMail")
    assert cabeceras["Authorization"] == "Bearer token-1"
    mensaje = json.loads(cuerpo)
    assert mensaje["saveToSentItems"] is False
    assert mensaje["message"]["subject"] == "Asunto de prueba"
    assert mensaje["message"]["body"] == {
        "contentType": "HTML",
        "content": "<p>Texto HTML</p>",
    }
    assert mensaje["message"]["toRecipients"] == [
        {"emailAddress": {"address": "lider@ejemplo.local"}}
    ]


def test_reutiliza_el_token(monkeypatch):
    falso = GraphFalso(respuestas_envio=[202, 202])
    monkeypatch.setattr(graph, "_post", falso)
    backend = graph.GraphEmailBackend()
    backend.send_messages([correo_de_prueba()])
    backend.send_messages([correo_de_prueba()])
    assert falso.tokens == 1


def test_un_401_renueva_el_token_y_reintenta(monkeypatch):
    falso = GraphFalso(respuestas_envio=[401, 202])
    monkeypatch.setattr(graph, "_post", falso)
    assert graph.GraphEmailBackend().send_messages([correo_de_prueba()]) == 1
    assert falso.tokens == 2
    assert falso.envios()[-1][2]["Authorization"] == "Bearer token-2"


def test_un_error_de_graph_se_propaga(monkeypatch):
    monkeypatch.setattr(graph, "_post", GraphFalso(respuestas_envio=[403]))
    with pytest.raises(graph.ErrorGraph):
        graph.GraphEmailBackend().send_messages([correo_de_prueba()])


def test_faltan_variables(settings):
    settings.GRAPH_CLIENT_SECRET = ""
    with pytest.raises(ImproperlyConfigured, match="GRAPH_CLIENT_SECRET"):
        graph.GraphEmailBackend().send_messages([correo_de_prueba()])


def test_produccion_exige_las_variables_de_graph(settings):
    settings.DEBUG = False
    settings.GRAPH_TENANT_ID = ""
    assert [error.id for error in comprobar_correo(None)] == ["notificaciones.E001"]


@pytest.mark.django_db
def test_la_bandeja_de_salida_envia_por_graph(monkeypatch, settings):
    settings.DEBUG = True
    call_command("crear_datos_demo")
    Notificacion.objects.all().delete()
    falso = GraphFalso()
    monkeypatch.setattr(graph, "_post", falso)
    admin = Usuario.objects.get(email="admin@ejemplo.local")
    notificacion = servicios.encolar(
        tipo=TipoNotificacion.CAMBIO_ROL,
        destinatario=admin,
        clave_unica="prueba-graph:1",
        contexto={
            "usuario": "x@ejemplo.local",
            "operacion": "agregado a",
            "grupos": "Administrador",
            "por": "Sistema",
        },
    )
    assert servicios.enviar_pendientes() == 1
    notificacion.refresh_from_db()
    assert notificacion.estado == EstadoNotificacion.ENVIADA
    destinos = [
        json.loads(cuerpo)["message"]["toRecipients"] for _, cuerpo, _ in falso.envios()
    ]
    assert [{"emailAddress": {"address": "admin@ejemplo.local"}}] in destinos
