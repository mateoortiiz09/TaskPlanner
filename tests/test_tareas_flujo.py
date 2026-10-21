import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Area
from cuentas.roles import ADMINISTRADOR, LIDER_AREA, SUBGERENTE
from tareas.consultas import tareas_visibles
from tareas.models import (
    Cumplimiento,
    EstadoAvance,
    NivelSensibilidad,
    ResponsableTarea,
    Tarea,
)

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"


def hoy():
    return timezone.localdate()


def crear_usuario(email, grupo, area=None):
    usuario = get_user_model().objects.create_user(
        email=email, password=CLAVE, area=area
    )
    usuario.groups.add(Group.objects.get(name=grupo))
    return get_user_model().objects.get(pk=usuario.pk)


def crear_tarea(creador, responsables, **campos):
    datos = {
        "nombre": "Tarea de prueba",
        "descripcion": "Descripción de prueba",
        "fecha_limite": hoy() + datetime.timedelta(days=5),
        "creada_por": creador,
    }
    datos.update(campos)
    tarea = Tarea.objects.create(**datos)
    for usuario in responsables:
        ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
    return tarea


def datos_formulario(responsables, **cambios):
    datos = {
        "nombre": "Revisar inventario",
        "descripcion": "Revisión mensual",
        "fecha_limite": (hoy() + datetime.timedelta(days=5)).isoformat(),
        "prioridad": "MEDIA",
        "nivel_sensibilidad": "2",
        "responsables": [usuario.pk for usuario in responsables],
    }
    datos.update(cambios)
    return datos


@pytest.fixture
def areas():
    return [
        Area.objects.create(nombre=nombre)
        for nombre in ("Compras", "Calidad", "Logística")
    ]


@pytest.fixture
def lideres(areas):
    return [
        crear_usuario(f"lider{indice}@ejemplo.local", LIDER_AREA, area)
        for indice, area in enumerate(areas, start=1)
    ]


@pytest.fixture
def subgerente():
    return crear_usuario("subgerente@ejemplo.local", SUBGERENTE)


@pytest.fixture
def administrador():
    return crear_usuario("admin@ejemplo.local", ADMINISTRADOR)


def test_las_paginas_de_tareas_requieren_sesion(client):
    respuesta = client.get(reverse("tareas:lista"))
    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("login"))


def test_subgerente_crea_tarea_con_lideres_de_tres_areas(
    client, subgerente, lideres, areas
):
    client.force_login(subgerente)
    respuesta = client.post(reverse("tareas:crear"), datos_formulario(lideres))
    assert respuesta.status_code == 302
    tarea = Tarea.objects.get()
    assert set(tarea.areas()) == set(areas)
    assert tarea.creada_por == subgerente
    assert tarea.estado == EstadoAvance.PENDIENTE
    assert tarea.fecha_asignacion == hoy()


def test_lider_no_puede_crear_tareas(client, lideres):
    client.force_login(lideres[0])
    assert client.get(reverse("tareas:crear")).status_code == 403


def test_el_formulario_exige_responsables(client, subgerente):
    client.force_login(subgerente)
    respuesta = client.post(reverse("tareas:crear"), datos_formulario([]))
    assert respuesta.status_code == 200
    assert not Tarea.objects.exists()


def test_administrador_no_puede_crear_tareas_de_nivel_3(client, administrador, lideres):
    client.force_login(administrador)
    respuesta = client.post(
        reverse("tareas:crear"), datos_formulario(lideres, nivel_sensibilidad="3")
    )
    assert respuesta.status_code == 200
    assert not Tarea.objects.exists()


def test_editar_tarea_actualiza_datos_y_version(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    client.force_login(subgerente)
    respuesta = client.post(
        reverse("tareas:editar", args=[tarea.pk]),
        datos_formulario(lideres[1:2], nombre="Nuevo nombre", version=tarea.version),
    )
    assert respuesta.status_code == 302
    tarea.refresh_from_db()
    assert tarea.nombre == "Nuevo nombre"
    assert tarea.version == 2
    assert set(tarea.responsables.all()) == {lideres[1]}


def test_edicion_con_version_desactualizada_no_sobrescribe(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    Tarea.objects.filter(pk=tarea.pk).update(version=2)
    client.force_login(subgerente)
    respuesta = client.post(
        reverse("tareas:editar", args=[tarea.pk]),
        datos_formulario(lideres[:1], nombre="Cambio perdido", version=1),
    )
    assert respuesta.status_code == 200
    tarea.refresh_from_db()
    assert tarea.nombre == "Tarea de prueba"


def test_subgerente_cambia_el_estado(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    client.force_login(subgerente)
    client.post(
        reverse("tareas:cambiar_estado", args=[tarea.pk]),
        {"estado": EstadoAvance.EN_PROCESO},
    )
    tarea.refresh_from_db()
    assert tarea.estado == EstadoAvance.EN_PROCESO


def test_lider_y_administrador_no_cambian_el_estado(
    client, subgerente, administrador, lideres
):
    tarea = crear_tarea(subgerente, lideres[:1])
    url = reverse("tareas:cambiar_estado", args=[tarea.pk])
    for usuario in (lideres[0], administrador):
        client.force_login(usuario)
        respuesta = client.post(url, {"estado": EstadoAvance.EN_PROCESO})
        assert respuesta.status_code == 403
    tarea.refresh_from_db()
    assert tarea.estado == EstadoAvance.PENDIENTE


def test_completar_dentro_del_plazo(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    client.force_login(subgerente)
    client.post(reverse("tareas:completar", args=[tarea.pk]))
    tarea.refresh_from_db()
    assert tarea.estado == EstadoAvance.COMPLETADA
    assert tarea.fecha_finalizacion == hoy()
    assert tarea.completada_por == subgerente
    assert tarea.cumplimiento == Cumplimiento.DENTRO_DEL_PLAZO


def test_completar_fuera_del_plazo(client, subgerente, lideres):
    tarea = crear_tarea(
        subgerente, lideres[:1], fecha_limite=hoy() - datetime.timedelta(days=1)
    )
    client.force_login(subgerente)
    client.post(reverse("tareas:completar", args=[tarea.pk]))
    tarea.refresh_from_db()
    assert tarea.cumplimiento == Cumplimiento.FUERA_DEL_PLAZO


def test_lider_no_puede_completar(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    client.force_login(lideres[0])
    respuesta = client.post(reverse("tareas:completar", args=[tarea.pk]))
    assert respuesta.status_code == 403


def test_tarea_completada_no_cambia_de_estado(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1])
    client.force_login(subgerente)
    client.post(reverse("tareas:completar", args=[tarea.pk]))
    client.post(
        reverse("tareas:cambiar_estado", args=[tarea.pk]),
        {"estado": EstadoAvance.PENDIENTE},
    )
    tarea.refresh_from_db()
    assert tarea.estado == EstadoAvance.COMPLETADA


def test_eliminar_y_recuperar(client, subgerente, lideres):
    tarea = crear_tarea(subgerente, lideres[:1], nombre="Tarea a eliminar")
    client.force_login(subgerente)

    client.post(reverse("tareas:eliminar", args=[tarea.pk]))
    tarea.refresh_from_db()
    assert tarea.eliminada
    assert tarea.eliminada_por == subgerente
    assert not tareas_visibles(subgerente).filter(pk=tarea.pk).exists()
    assert "Tarea a eliminar" in client.get(reverse("tareas:papelera")).content.decode()

    client.post(reverse("tareas:recuperar", args=[tarea.pk]))
    tarea.refresh_from_db()
    assert not tarea.eliminada
    assert tareas_visibles(subgerente).filter(pk=tarea.pk).exists()


def test_lider_solo_ve_sus_tareas(client, subgerente, lideres):
    propia = crear_tarea(subgerente, lideres[:1], nombre="Tarea de Compras")
    ajena = crear_tarea(subgerente, lideres[1:2], nombre="Tarea de Calidad")
    client.force_login(lideres[0])

    assert client.get(reverse("tareas:detalle", args=[propia.pk])).status_code == 200
    assert client.get(reverse("tareas:detalle", args=[ajena.pk])).status_code == 404

    contenido = client.get(reverse("tareas:lista")).content.decode()
    assert "Tarea de Compras" in contenido
    assert "Tarea de Calidad" not in contenido


def test_administrador_no_edita_tareas_de_nivel_3(
    client, subgerente, administrador, lideres
):
    tarea = crear_tarea(
        subgerente,
        lideres[:1],
        nivel_sensibilidad=NivelSensibilidad.ALTAMENTE_SENSIBLE,
    )
    client.force_login(administrador)
    respuesta = client.get(reverse("tareas:editar", args=[tarea.pk]))
    assert respuesta.status_code == 403
