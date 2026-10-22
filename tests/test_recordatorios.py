from datetime import date, timedelta

import pytest
from django.core.management import call_command
from django_q.models import Schedule

from cuentas.models import Usuario
from notificaciones.models import Notificacion, TipoNotificacion
from notificaciones.recordatorios import generar_recordatorios
from tareas.models import ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

HOY = date(2026, 10, 22)


# --- ADAPTABLE ---
def crear_tarea(creador, responsables=(), restringida=False):
    from django.utils import timezone

    tarea = Tarea.objects.create(
        nombre="Tarea de prueba",
        descripcion="Descripción de prueba",
        fecha_limite=timezone.localdate() + timedelta(days=5),
        creada_por=creador,
        restringida=restringida,
    )
    for usuario in responsables:
        ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
    return tarea


def completar(tarea, usuario):
    from tareas.servicios import completar_tarea

    return completar_tarea(usuario, tarea.pk)


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def usuarios(settings):
    settings.DEBUG = True
    call_command("crear_datos_demo")
    return {
        clave: Usuario.objects.get(email=f"{clave}@ejemplo.local")
        for clave in ("admin", "subgerente", "lider.compras", "lider.calidad")
    }


def tarea_con_vencimiento(usuarios, dias):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    Tarea.objects.filter(pk=tarea.pk).update(fecha_limite=HOY + timedelta(days=dias))
    tarea.refresh_from_db()
    Notificacion.objects.all().delete()
    return tarea


def destinatarios(tipo):
    return set(
        Notificacion.objects.filter(tipo=tipo).values_list(
            "destinatario__email", flat=True
        )
    )


def generar(hoy=HOY):
    return generar_recordatorios(hoy=hoy, forzar=True)


def test_recordatorio_el_dia_anterior(usuarios):
    tarea_con_vencimiento(usuarios, 1)
    generar()
    assert destinatarios(TipoNotificacion.DIA_ANTERIOR) == {
        "lider.compras@ejemplo.local"
    }


def test_recordatorio_el_dia_del_vencimiento(usuarios):
    tarea_con_vencimiento(usuarios, 0)
    generar()
    assert destinatarios(TipoNotificacion.VENCIMIENTO) == {
        "lider.compras@ejemplo.local"
    }


def test_aviso_de_atraso_el_dia_siguiente(usuarios):
    tarea_con_vencimiento(usuarios, -1)
    generar()
    assert destinatarios(TipoNotificacion.ATRASO) == {"lider.compras@ejemplo.local"}


def test_atraso_semanal_incluye_a_la_subgerente(usuarios):
    tarea_con_vencimiento(usuarios, -8)
    generar()
    assert destinatarios(TipoNotificacion.ATRASO_SEMANAL) == {
        "lider.compras@ejemplo.local",
        "subgerente@ejemplo.local",
    }


def test_sin_recordatorio_entre_semanas(usuarios):
    tarea_con_vencimiento(usuarios, -5)
    assert generar() == 0


def test_sin_recordatorio_para_tareas_lejanas(usuarios):
    tarea_con_vencimiento(usuarios, 5)
    assert generar() == 0


def test_tareas_completadas_no_generan_recordatorios(usuarios):
    tarea = tarea_con_vencimiento(usuarios, 0)
    completar(tarea, usuarios["subgerente"])
    Notificacion.objects.all().delete()
    assert generar() == 0


def test_tareas_eliminadas_no_generan_recordatorios(usuarios):
    from django.utils import timezone

    tarea = tarea_con_vencimiento(usuarios, 0)
    Tarea.objects.filter(pk=tarea.pk).update(eliminada_en=timezone.now())
    assert generar() == 0


def test_generar_es_idempotente(usuarios):
    tarea_con_vencimiento(usuarios, 1)
    assert generar() == 1
    assert generar() == 0
    assert Notificacion.objects.count() == 1


def test_no_genera_antes_de_la_hora_de_inicio(usuarios, settings):
    settings.NOTIFICACIONES_HORA_INICIO = 24
    tarea_con_vencimiento(usuarios, 1)
    assert generar_recordatorios(hoy=HOY) == 0


def test_cambiar_la_fecha_limite_genera_recordatorio_nuevo(usuarios):
    tarea = tarea_con_vencimiento(usuarios, 1)
    generar()
    Tarea.objects.filter(pk=tarea.pk).update(fecha_limite=HOY + timedelta(days=2))
    generar(hoy=HOY + timedelta(days=1))
    assert Notificacion.objects.filter(tipo=TipoNotificacion.DIA_ANTERIOR).count() == 2


def test_programar_tareas_es_idempotente():
    call_command("programar_tareas")
    call_command("programar_tareas")
    nombres = sorted(Schedule.objects.values_list("name", flat=True))
    assert nombres == ["Enviar correos pendientes", "Generar recordatorios"]
