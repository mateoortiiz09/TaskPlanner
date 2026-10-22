import re
import urllib.error
import urllib.parse
import urllib.request
from http.cookiejar import CookieJar

import pytest
from django.core.management import call_command

from tareas.models import Tarea

CONTRASENA = "Demo.Local.2026#"
CONFIDENCIALES = (
    "Negociación confidencial proveedor",
    "Condiciones comerciales reservadas",
)

pytestmark = pytest.mark.django_db


class Navegador:
    def __init__(self, base):
        self.base = base
        self.cookies = CookieJar()
        self.abridor = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookies)
        )

    def _csrf(self):
        for cookie in self.cookies:
            if cookie.name == "csrftoken":
                return cookie.value
        return ""

    def get(self, ruta):
        try:
            with self.abridor.open(self.base + ruta) as respuesta:
                return (
                    respuesta.status,
                    respuesta.read().decode("utf-8"),
                    respuesta.geturl(),
                )
        except urllib.error.HTTPError as error:
            return (
                error.code,
                error.read().decode("utf-8", "replace"),
                error.geturl(),
            )

    def post(self, ruta, datos):
        datos = {**datos, "csrfmiddlewaretoken": self._csrf()}
        peticion = urllib.request.Request(
            self.base + ruta,
            data=urllib.parse.urlencode(datos).encode(),
            headers={"Referer": self.base + ruta},
        )
        try:
            with self.abridor.open(peticion) as respuesta:
                return (
                    respuesta.status,
                    respuesta.read().decode("utf-8"),
                    respuesta.geturl(),
                )
        except urllib.error.HTTPError as error:
            return (
                error.code,
                error.read().decode("utf-8", "replace"),
                error.geturl(),
            )

    # --- ADAPTABLE: solo los nombres de los campos ---
    def ingresar(self, correo):
        self.get("/ingresar/")
        return self.post("/ingresar/", {"username": correo, "password": CONTRASENA})

    # --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def servidor(live_server, settings, tmp_path):
    import base64
    import secrets

    settings.DEBUG = True
    settings.ALLOWED_HOSTS = ["*"]
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ADJUNTOS_CLAVE_MAESTRA = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode()
    settings.ANTIVIRUS_ACTIVO = False
    call_command("cargar_datos_demo")
    return live_server.url


def pk(nombre):
    return Tarea.objects.get(nombre=nombre).pk


def test_anonimo_es_enviado_al_inicio_de_sesion(servidor):
    _, _, url = Navegador(servidor).get("/tareas/")
    assert "/ingresar/" in url


def test_recorrido_de_la_subgerente(servidor):
    nav = Navegador(servidor)
    nav.ingresar("subgerente@ejemplo.local")
    estado, html, _ = nav.get("/tareas/")
    assert estado == 200
    assert "[DEMO] Auditoría de inventario" in html
    assert "Negociación confidencial proveedor" in html
    hoja = re.search(r'href="([^"]*bootstrap[^"]*\.css)"', html)
    assert hoja, "no se encontró la hoja de estilos de Bootstrap"
    assert nav.get(hoja.group(1))[0] == 200
    estado, html, _ = nav.get(
        f"/tareas/{pk('[DEMO] Negociación confidencial proveedor')}/"
    )
    assert estado == 200
    assert "Condiciones comerciales reservadas" in html


def test_recorrido_del_administrador(servidor):
    nav = Navegador(servidor)
    nav.ingresar("admin@ejemplo.local")
    estado, html, _ = nav.get("/tareas/")
    assert estado == 200
    assert "Tarea restringida" in html
    for texto in CONFIDENCIALES:
        assert texto not in html
    estado, html, _ = nav.get(
        f"/tareas/{pk('[DEMO] Negociación confidencial proveedor')}/"
    )
    assert estado == 200
    for texto in CONFIDENCIALES:
        assert texto not in html
    estado, html, _ = nav.get("/auditoria/")
    assert estado == 200
    assert "[DEMO]" not in html


def test_recorrido_del_lider(servidor):
    nav = Navegador(servidor)
    nav.ingresar("lider.calidad@ejemplo.local")
    estado, html, _ = nav.get("/tareas/")
    assert estado == 200
    assert "[DEMO] Revisión de certificados" in html
    assert "[DEMO] Cotización de reactivos" not in html
    assert nav.get(f"/tareas/{pk('[DEMO] Cotización de reactivos')}/")[0] == 404
    _, _, url = nav.get("/gestion-interna/")
    assert "login" in url or "ingresar" in url
