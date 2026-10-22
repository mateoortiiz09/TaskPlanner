import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Area
from cuentas.roles import ADMINISTRADOR, LIDER_AREA, SUBGERENTE
from tareas.models import ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"
NOMBRE_SECRETO = "Contrato confidencial con cliente"
DESCRIPCION_SECRETA = "Montos y datos bancarios del cliente"


def crear_usuario(email, grupo, area=None):
    usuario = get_user_model().objects.create_user(
        email=email, password=CLAVE, area=area
    )
    usuario.groups.add(Group.objects.get(name=grupo))
    return get_user_model().objects.get(pk=usuario.pk)


@pytest.fixture
def subgerente():
    return crear_usuario("subgerente@ejemplo.local", SUBGERENTE)


@pytest.fixture
def administrador():
    return crear_usuario("admin@ejemplo.local", ADMINISTRADOR)


@pytest.fixture
def lider_compras():
    return crear_usuario(
        "compras@ejemplo.local", LIDER_AREA, Area.objects.create(nombre="Compras")
    )


@pytest.fixture
def lider_calidad():
    return crear_usuario(
        "calidad@ejemplo.local", LIDER_AREA, Area.objects.create(nombre="Calidad")
    )


@pytest.fixture
def restringida(subgerente, lider_compras):
    tarea = Tarea.objects.create(
        nombre=NOMBRE_SECRETO,
        descripcion=DESCRIPCION_SECRETA,
        fecha_limite=timezone.localdate() + datetime.timedelta(days=5),
        creada_por=subgerente,
        restringida=True,
    )
    ResponsableTarea.objects.create(tarea=tarea, usuario=lider_compras)
    return tarea


def contenido(client, usuario, url):
    client.force_login(usuario)
    respuesta = client.get(url)
    return respuesta, respuesta.content.decode()


def test_subgerente_ve_el_contenido_de_una_restringida(client, subgerente, restringida):
    _, html = contenido(
        client, subgerente, reverse("tareas:detalle", args=[restringida.pk])
    )
    assert NOMBRE_SECRETO in html
    assert DESCRIPCION_SECRETA in html


def test_lider_responsable_ve_su_tarea_restringida(client, lider_compras, restringida):
    _, html = contenido(
        client, lider_compras, reverse("tareas:detalle", args=[restringida.pk])
    )
    assert DESCRIPCION_SECRETA in html


def test_lider_no_responsable_no_ve_la_restringida(client, lider_calidad, restringida):
    respuesta, _ = contenido(
        client, lider_calidad, reverse("tareas:detalle", args=[restringida.pk])
    )
    assert respuesta.status_code == 404


def test_administrador_ve_la_restringida_enmascarada_en_el_panel(
    client, administrador, restringida
):
    _, html = contenido(client, administrador, reverse("tareas:lista"))
    assert "Tarea restringida" in html
    assert NOMBRE_SECRETO not in html


def test_administrador_ve_el_detalle_enmascarado(client, administrador, restringida):
    respuesta, html = contenido(
        client, administrador, reverse("tareas:detalle", args=[restringida.pk])
    )
    assert respuesta.status_code == 200
    assert "Tarea restringida" in html
    assert NOMBRE_SECRETO not in html
    assert DESCRIPCION_SECRETA not in html


def test_administrador_puede_editar_una_tarea_general(
    client, administrador, subgerente, lider_compras
):
    tarea = Tarea.objects.create(
        nombre="Tarea general",
        descripcion="Sin información sensible",
        fecha_limite=timezone.localdate() + datetime.timedelta(days=5),
        creada_por=subgerente,
    )
    ResponsableTarea.objects.create(tarea=tarea, usuario=lider_compras)
    respuesta, _ = contenido(
        client, administrador, reverse("tareas:editar", args=[tarea.pk])
    )
    assert respuesta.status_code == 200


def test_administrador_no_tiene_la_casilla_restringida(client, administrador):
    _, html = contenido(client, administrador, reverse("tareas:crear"))
    assert 'name="restringida"' not in html


def test_subgerente_crea_una_tarea_restringida(client, subgerente, lider_compras):
    client.force_login(subgerente)
    respuesta = client.post(
        reverse("tareas:crear"),
        {
            "nombre": "Nómina de octubre",
            "descripcion": "Revisión de nómina",
            "fecha_limite": (
                timezone.localdate() + datetime.timedelta(days=5)
            ).isoformat(),
            "prioridad": "MEDIA",
            "restringida": "on",
            "responsables": [lider_compras.pk],
        },
    )
    assert respuesta.status_code == 302
    assert Tarea.objects.get(nombre="Nómina de octubre").restringida is True


def test_subgerente_desmarca_una_tarea_restringida(
    client, subgerente, lider_compras, restringida
):
    client.force_login(subgerente)
    respuesta = client.post(
        reverse("tareas:editar", args=[restringida.pk]),
        {
            "nombre": restringida.nombre,
            "descripcion": restringida.descripcion,
            "fecha_limite": restringida.fecha_limite.isoformat(),
            "prioridad": "MEDIA",
            "responsables": [lider_compras.pk],
            "version": restringida.version,
        },
    )
    assert respuesta.status_code == 302
    restringida.refresh_from_db()
    assert restringida.restringida is False


def test_papelera_enmascara_las_restringidas_al_administrador(
    client, administrador, restringida
):
    restringida.eliminada_en = timezone.now()
    restringida.save()
    _, html = contenido(client, administrador, reverse("tareas:papelera"))
    assert "Tarea restringida" in html
    assert NOMBRE_SECRETO not in html


def test_confirmacion_de_eliminar_enmascarada_al_administrador(
    client, administrador, restringida
):
    _, html = contenido(
        client, administrador, reverse("tareas:eliminar", args=[restringida.pk])
    )
    assert "Tarea restringida" in html
    assert NOMBRE_SECRETO not in html
