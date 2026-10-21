import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from cuentas.roles import SUBGERENTE
from tareas.models import Cumplimiento, EstadoAvance, Tarea
from tareas.vencimientos import (
    SituacionTemporal,
    calcular_situacion,
    dias_restantes,
    filtro_situacion,
)

HOY = datetime.date(2026, 10, 15)


def dia(desplazamiento):
    return HOY + datetime.timedelta(days=desplazamiento)


@pytest.mark.parametrize(
    ("desplazamiento", "esperado"),
    [
        (5, SituacionTemporal.EN_TIEMPO),
        (3, SituacionTemporal.EN_TIEMPO),
        (2, SituacionTemporal.EN_RIESGO),
        (1, SituacionTemporal.EN_RIESGO),
        (0, SituacionTemporal.EN_RIESGO),
        (-1, SituacionTemporal.ATRASADA),
        (-10, SituacionTemporal.ATRASADA),
    ],
)
def test_situacion_segun_la_fecha_limite(desplazamiento, esperado):
    tarea = Tarea(fecha_limite=dia(desplazamiento), estado=EstadoAvance.EN_PROCESO)
    assert calcular_situacion(tarea, hoy=HOY) == esperado


def test_una_tarea_completada_no_aparece_atrasada():
    tarea = Tarea(fecha_limite=dia(-5), estado=EstadoAvance.COMPLETADA)
    assert calcular_situacion(tarea, hoy=HOY) == SituacionTemporal.COMPLETADA


def test_cambiar_la_fecha_limite_cambia_la_situacion():
    tarea = Tarea(fecha_limite=dia(-1), estado=EstadoAvance.PENDIENTE)
    assert calcular_situacion(tarea, hoy=HOY) == SituacionTemporal.ATRASADA
    tarea.fecha_limite = dia(10)
    assert calcular_situacion(tarea, hoy=HOY) == SituacionTemporal.EN_TIEMPO


def test_dias_restantes():
    assert dias_restantes(Tarea(fecha_limite=dia(3)), hoy=HOY) == 3
    assert dias_restantes(Tarea(fecha_limite=dia(-2)), hoy=HOY) == -2


def test_el_umbral_de_riesgo_es_configurable(settings):
    settings.DIAS_EN_RIESGO = 3
    tarea = Tarea(fecha_limite=dia(3), estado=EstadoAvance.PENDIENTE)
    assert calcular_situacion(tarea, hoy=HOY) == SituacionTemporal.EN_RIESGO


@pytest.mark.django_db
def test_los_filtros_coinciden_con_el_calculo():
    creador = get_user_model().objects.create_user(
        email="subgerente@ejemplo.local", password="Clave-de-prueba-123"
    )
    for desplazamiento in (5, 3, 2, 1, 0, -1, -10):
        for estado in (EstadoAvance.PENDIENTE, EstadoAvance.EN_PROCESO):
            Tarea.objects.create(
                nombre=f"Tarea {desplazamiento} {estado}",
                descripcion="Prueba",
                fecha_limite=dia(desplazamiento),
                estado=estado,
                creada_por=creador,
            )
    Tarea.objects.create(
        nombre="Completada",
        descripcion="Prueba",
        fecha_limite=dia(-3),
        estado=EstadoAvance.COMPLETADA,
        fecha_finalizacion=dia(-4),
        cumplimiento=Cumplimiento.DENTRO_DEL_PLAZO,
        completada_por=creador,
        creada_por=creador,
    )

    for situacion in SituacionTemporal:
        por_filtro = set(
            Tarea.objects.filter(filtro_situacion(situacion, hoy=HOY)).values_list(
                "pk", flat=True
            )
        )
        por_calculo = {
            tarea.pk
            for tarea in Tarea.objects.all()
            if calcular_situacion(tarea, hoy=HOY) == situacion
        }
        assert por_filtro == por_calculo, situacion


@pytest.mark.django_db
def test_el_listado_muestra_la_situacion(client):
    subgerente = get_user_model().objects.create_user(
        email="subgerente@ejemplo.local", password="Clave-de-prueba-123"
    )
    subgerente.groups.add(Group.objects.get(name=SUBGERENTE))
    Tarea.objects.create(
        nombre="Tarea vencida",
        descripcion="Prueba",
        fecha_limite=timezone.localdate() - datetime.timedelta(days=2),
        creada_por=subgerente,
    )
    client.force_login(subgerente)
    contenido = client.get(reverse("tareas:lista")).content.decode()
    assert "Atrasada" in contenido
    assert "text-bg-danger" in contenido
