import base64
import secrets

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from adjuntos.models import Adjunto
from cuentas.models import Usuario
from tareas.models import EstadoAvance, Tarea

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def entorno(settings, tmp_path):
    settings.DEBUG = True
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ADJUNTOS_CLAVE_MAESTRA = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode()
    settings.ANTIVIRUS_ACTIVO = False


def demo():
    return Tarea.objects.filter(nombre__startswith="[DEMO]")


def test_carga_todos_los_escenarios():
    call_command("cargar_datos_demo")
    assert demo().count() == 13
    assert demo().filter(restringida=True).count() == 2
    assert demo().filter(estado=EstadoAvance.COMPLETADA).count() == 2
    assert demo().filter(eliminada_en__isnull=False).count() == 1
    assert Adjunto.objects.filter(tarea__nombre__startswith="[DEMO]").count() == 2


def test_reiniciar_no_duplica():
    call_command("cargar_datos_demo")
    call_command("cargar_datos_demo", "--reiniciar")
    assert demo().count() == 13


def test_no_funciona_en_produccion(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("cargar_datos_demo")
    assert not demo().exists()


def test_volumen():
    call_command("cargar_datos_demo", "--volumen", "30")
    assert Tarea.objects.filter(nombre__startswith="[DEMO-VOL]").count() == 30


def consultas_de_la_lista(client, usuario):
    client.force_login(usuario)
    with CaptureQueriesContext(connection) as contexto:
        respuesta = client.get(reverse("tareas:lista"))
    assert respuesta.status_code == 200
    return len(contexto.captured_queries)


@pytest.mark.parametrize(
    "correo",
    [
        "subgerente@ejemplo.local",
        "admin@ejemplo.local",
        "lider.compras@ejemplo.local",
    ],
)
def test_la_lista_no_hace_una_consulta_por_tarea(client, correo):
    call_command("cargar_datos_demo", "--volumen", "5")
    usuario = Usuario.objects.get(email=correo)
    pocas = consultas_de_la_lista(client, usuario)
    call_command("cargar_datos_demo", "--volumen", "20")
    muchas = consultas_de_la_lista(client, usuario)
    assert muchas - pocas <= 2, (
        f"{correo}: {pocas} consultas con pocas tareas, {muchas} con muchas"
    )
