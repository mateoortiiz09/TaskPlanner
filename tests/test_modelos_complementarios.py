import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.utils import timezone

from adjuntos.models import Adjunto, EstadoAnalisis
from auditoria.models import EventoAuditoria, RegistroInmutableError
from notificaciones.models import EstadoNotificacion, Notificacion, TipoNotificacion
from tareas.models import Tarea

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"


@pytest.fixture
def subgerente():
    return get_user_model().objects.create_user(
        email="subgerente@ejemplo.local", password=CLAVE
    )


@pytest.fixture
def otro_usuario():
    return get_user_model().objects.create_user(
        email="otro@ejemplo.local", password=CLAVE
    )


@pytest.fixture
def tarea(subgerente):
    return Tarea.objects.create(
        nombre="Tarea de prueba",
        descripcion="Descripción de prueba",
        fecha_limite=timezone.localdate(),
        creada_por=subgerente,
    )


def crear_adjunto(tarea, usuario, **campos):
    datos = {
        "tarea": tarea,
        "nombre_original": "documento.pdf",
        "tipo_contenido": "application/pdf",
        "tamano_bytes": 1024,
        "sha256": "0" * 64,
        "subido_por": usuario,
    }
    datos.update(campos)
    return Adjunto.objects.create(**datos)


def test_adjunto_valores_por_defecto(tarea, subgerente):
    primero = crear_adjunto(tarea, subgerente)
    segundo = crear_adjunto(tarea, subgerente)
    assert primero.estado_analisis == EstadoAnalisis.SIN_ANALIZAR
    assert not hasattr(primero, "nivel_sensibilidad")
    assert primero.nombre_interno != segundo.nombre_interno


def test_adjunto_cifrado_sin_clave_es_rechazado(tarea, subgerente):
    with pytest.raises(IntegrityError):
        crear_adjunto(tarea, subgerente, cifrado=True)


def test_notificacion_valores_por_defecto(tarea, otro_usuario):
    notificacion = Notificacion.objects.create(
        tipo=TipoNotificacion.ASIGNACION,
        tarea=tarea,
        destinatario=otro_usuario,
        clave_unica="asignacion-1",
    )
    assert notificacion.estado == EstadoNotificacion.PENDIENTE
    assert notificacion.intentos == 0


def test_notificacion_con_clave_repetida_es_rechazada(tarea, otro_usuario):
    datos = {
        "tipo": TipoNotificacion.ASIGNACION,
        "tarea": tarea,
        "destinatario": otro_usuario,
        "clave_unica": "asignacion-repetida",
    }
    Notificacion.objects.create(**datos)
    with pytest.raises(IntegrityError):
        Notificacion.objects.create(**datos)


def crear_evento(actor):
    return EventoAuditoria.objects.create(
        actor=actor, accion="tarea.creada", tipo_recurso="tarea", recurso_id="1"
    )


def test_evento_de_auditoria_se_registra(subgerente):
    evento = crear_evento(subgerente)
    assert evento.pk is not None


def test_evento_de_auditoria_no_se_puede_modificar(subgerente):
    evento = crear_evento(subgerente)
    evento.accion = "otra.accion"
    with pytest.raises(RegistroInmutableError):
        evento.save()


def test_evento_de_auditoria_no_se_puede_borrar(subgerente):
    evento = crear_evento(subgerente)
    with pytest.raises(RegistroInmutableError):
        evento.delete()


def test_eventos_de_auditoria_no_admiten_update_ni_delete_masivo(subgerente):
    crear_evento(subgerente)
    with pytest.raises(RegistroInmutableError):
        EventoAuditoria.objects.all().update(accion="otra.accion")
    with pytest.raises(RegistroInmutableError):
        EventoAuditoria.objects.all().delete()
