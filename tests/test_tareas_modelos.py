import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from cuentas.models import Area
from tareas.models import (
    Cumplimiento,
    EstadoAvance,
    Prioridad,
    ResponsableTarea,
    Tarea,
)

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"


@pytest.fixture
def area_compras():
    return Area.objects.create(nombre="Compras")


@pytest.fixture
def area_calidad():
    return Area.objects.create(nombre="Calidad")


@pytest.fixture
def subgerente():
    return get_user_model().objects.create_user(
        email="subgerente@ejemplo.local", password=CLAVE
    )


def crear_lider(email, area):
    return get_user_model().objects.create_user(email=email, password=CLAVE, area=area)


def crear_tarea(creador, **campos):
    datos = {
        "nombre": "Tarea de prueba",
        "descripcion": "Descripción de prueba",
        "fecha_limite": timezone.localdate(),
        "creada_por": creador,
    }
    datos.update(campos)
    return Tarea.objects.create(**datos)


def test_valores_por_defecto(subgerente):
    tarea = crear_tarea(subgerente)
    assert tarea.prioridad == Prioridad.MEDIA
    assert tarea.estado == EstadoAvance.PENDIENTE
    assert tarea.restringida is False
    assert tarea.version == 1
    assert tarea.fecha_asignacion == timezone.localdate()
    assert not tarea.eliminada


def test_responsable_guarda_el_area_del_lider(subgerente, area_compras):
    lider = crear_lider("lider.compras@ejemplo.local", area_compras)
    tarea = crear_tarea(subgerente)
    asignacion = ResponsableTarea.objects.create(tarea=tarea, usuario=lider)
    assert asignacion.area == area_compras


def test_areas_se_derivan_de_los_responsables(subgerente, area_compras, area_calidad):
    tarea = crear_tarea(subgerente)
    lideres = [
        ("a@ejemplo.local", area_compras),
        ("b@ejemplo.local", area_calidad),
        ("c@ejemplo.local", area_compras),
    ]
    for email, area in lideres:
        ResponsableTarea.objects.create(tarea=tarea, usuario=crear_lider(email, area))
    assert set(tarea.areas()) == {area_compras, area_calidad}
    assert tarea.responsables.count() == 3


def test_responsable_no_se_repite_en_la_misma_tarea(subgerente, area_compras):
    lider = crear_lider("lider@ejemplo.local", area_compras)
    tarea = crear_tarea(subgerente)
    ResponsableTarea.objects.create(tarea=tarea, usuario=lider)
    with pytest.raises(IntegrityError):
        ResponsableTarea.objects.create(tarea=tarea, usuario=lider)


def test_responsable_sin_area_es_rechazado(subgerente):
    tarea = crear_tarea(subgerente)
    with pytest.raises(IntegrityError):
        ResponsableTarea.objects.create(tarea=tarea, usuario=subgerente)


def test_completada_sin_datos_de_finalizacion_es_rechazada(subgerente):
    with pytest.raises(IntegrityError):
        crear_tarea(subgerente, estado=EstadoAvance.COMPLETADA)


def test_completada_con_datos_de_finalizacion_es_aceptada(subgerente):
    tarea = crear_tarea(
        subgerente,
        estado=EstadoAvance.COMPLETADA,
        fecha_finalizacion=timezone.localdate(),
        cumplimiento=Cumplimiento.DENTRO_DEL_PLAZO,
        completada_por=subgerente,
    )
    assert tarea.pk is not None
