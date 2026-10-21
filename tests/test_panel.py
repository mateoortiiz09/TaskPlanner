import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Area
from cuentas.roles import LIDER_AREA, SUBGERENTE
from tareas.models import (
    Cumplimiento,
    EstadoAvance,
    Prioridad,
    ResponsableTarea,
    Tarea,
)

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"


def dia(desplazamiento):
    return timezone.localdate() + datetime.timedelta(days=desplazamiento)


def crear_usuario(email, grupo, area=None):
    usuario = get_user_model().objects.create_user(
        email=email, password=CLAVE, area=area
    )
    usuario.groups.add(Group.objects.get(name=grupo))
    return get_user_model().objects.get(pk=usuario.pk)


def completada(usuario):
    return {
        "estado": EstadoAvance.COMPLETADA,
        "fecha_finalizacion": dia(0),
        "cumplimiento": Cumplimiento.DENTRO_DEL_PLAZO,
        "completada_por": usuario,
    }


@pytest.fixture
def compras():
    return Area.objects.create(nombre="Compras")


@pytest.fixture
def calidad():
    return Area.objects.create(nombre="Calidad")


@pytest.fixture
def subgerente():
    return crear_usuario("subgerente@ejemplo.local", SUBGERENTE)


@pytest.fixture
def lider_compras(compras):
    return crear_usuario("compras@ejemplo.local", LIDER_AREA, compras)


@pytest.fixture
def lider_calidad(calidad):
    return crear_usuario("calidad@ejemplo.local", LIDER_AREA, calidad)


@pytest.fixture
def crear_tarea(subgerente):
    def _crear(nombre, desplazamiento, responsables, **campos):
        datos = {
            "nombre": nombre,
            "descripcion": "Prueba",
            "fecha_limite": dia(desplazamiento),
            "creada_por": subgerente,
        }
        datos.update(campos)
        tarea = Tarea.objects.create(**datos)
        for usuario in responsables:
            ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
        return tarea

    return _crear


def ver_panel(client, usuario, **parametros):
    client.force_login(usuario)
    return client.get(reverse("tareas:lista"), parametros)


def nombres(respuesta):
    return [tarea.nombre for tarea in respuesta.context["pagina"]]


def test_la_pagina_de_inicio_muestra_el_panel(client, subgerente):
    client.force_login(subgerente)
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 200
    assert "Atrasadas" in respuesta.content.decode()


def test_orden_por_urgencia(client, subgerente, lider_compras, crear_tarea):
    crear_tarea("En tiempo", 10, [lider_compras])
    crear_tarea("En riesgo", 1, [lider_compras])
    crear_tarea("Atrasada", -2, [lider_compras])
    crear_tarea("Muy atrasada", -5, [lider_compras])
    assert nombres(ver_panel(client, subgerente)) == [
        "Muy atrasada",
        "Atrasada",
        "En riesgo",
        "En tiempo",
    ]


def test_completadas_ocultas_por_defecto(
    client, subgerente, lider_compras, crear_tarea
):
    crear_tarea("Activa", 3, [lider_compras])
    crear_tarea("Terminada", 3, [lider_compras], **completada(subgerente))
    assert nombres(ver_panel(client, subgerente)) == ["Activa"]
    assert sorted(nombres(ver_panel(client, subgerente, completadas="on"))) == [
        "Activa",
        "Terminada",
    ]


def test_filtro_por_situacion(client, subgerente, lider_compras, crear_tarea):
    crear_tarea("Atrasada", -1, [lider_compras])
    crear_tarea("En tiempo", 10, [lider_compras])
    assert nombres(ver_panel(client, subgerente, situacion="ATRASADA")) == ["Atrasada"]


def test_filtro_por_area_y_responsable(
    client, subgerente, lider_compras, lider_calidad, compras, crear_tarea
):
    crear_tarea("De compras", 5, [lider_compras])
    crear_tarea("De calidad", 5, [lider_calidad])
    crear_tarea("Compartida", 5, [lider_compras, lider_calidad])
    assert sorted(nombres(ver_panel(client, subgerente, area=compras.pk))) == [
        "Compartida",
        "De compras",
    ]
    assert sorted(
        nombres(ver_panel(client, subgerente, responsable=lider_calidad.pk))
    ) == ["Compartida", "De calidad"]


def test_filtro_por_prioridad_y_estado(client, subgerente, lider_compras, crear_tarea):
    crear_tarea("Alta pendiente", 5, [lider_compras], prioridad=Prioridad.ALTA)
    crear_tarea(
        "Alta en proceso",
        5,
        [lider_compras],
        prioridad=Prioridad.ALTA,
        estado=EstadoAvance.EN_PROCESO,
    )
    crear_tarea("Baja pendiente", 5, [lider_compras], prioridad=Prioridad.BAJA)
    respuesta = ver_panel(client, subgerente, prioridad="ALTA", estado="PENDIENTE")
    assert nombres(respuesta) == ["Alta pendiente"]


def test_filtro_vencen_hoy(client, subgerente, lider_compras, crear_tarea):
    crear_tarea("Hoy", 0, [lider_compras])
    crear_tarea("Mañana", 1, [lider_compras])
    assert nombres(ver_panel(client, subgerente, vence="hoy")) == ["Hoy"]


def test_contadores(client, subgerente, lider_compras, crear_tarea):
    crear_tarea("Atrasada", -1, [lider_compras])
    crear_tarea("Hoy", 0, [lider_compras])
    crear_tarea("Mañana", 1, [lider_compras], estado=EstadoAvance.EN_PROCESO)
    crear_tarea("Lejos", 10, [lider_compras])
    assert ver_panel(client, subgerente).context["contadores"] == {
        "atrasadas": 1,
        "vencen_hoy": 1,
        "en_riesgo": 2,
        "pendientes": 3,
    }


def test_paginacion_de_25(client, subgerente, lider_compras, crear_tarea):
    for indice in range(30):
        crear_tarea(f"Tarea {indice:02d}", 5, [lider_compras])
    assert len(ver_panel(client, subgerente).context["pagina"]) == 25
    segunda = client.get(reverse("tareas:lista"), {"page": 2})
    assert len(segunda.context["pagina"]) == 5


def test_peticion_htmx_devuelve_solo_la_tabla(
    client, subgerente, lider_compras, crear_tarea
):
    crear_tarea("Visible", 5, [lider_compras])
    client.force_login(subgerente)
    respuesta = client.get(reverse("tareas:lista"), headers={"HX-Request": "true"})
    contenido = respuesta.content.decode()
    assert "Visible" in contenido
    assert "navbar" not in contenido


def test_lider_ve_solo_sus_tareas_sin_filtros_de_area(
    client, lider_compras, lider_calidad, crear_tarea
):
    crear_tarea("Mía", 5, [lider_compras])
    crear_tarea("Ajena", 5, [lider_calidad])
    respuesta = ver_panel(client, lider_compras)
    assert nombres(respuesta) == ["Mía"]
    assert "area" not in respuesta.context["form"].fields
    assert "responsable" not in respuesta.context["form"].fields


def test_las_consultas_no_crecen_con_las_filas(
    client, subgerente, lider_compras, lider_calidad, crear_tarea
):
    client.force_login(subgerente)
    client.get(reverse("tareas:lista"))

    def contar_consultas():
        with CaptureQueriesContext(connection) as contexto:
            client.get(reverse("tareas:lista"))
        return len(contexto.captured_queries)

    for indice in range(3):
        crear_tarea(f"A{indice}", 5, [lider_compras, lider_calidad])
    pocas_filas = contar_consultas()
    for indice in range(12):
        crear_tarea(f"B{indice}", 5, [lider_compras, lider_calidad])
    assert contar_consultas() == pocas_filas
