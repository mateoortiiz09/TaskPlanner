from datetime import timedelta

import pytest
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.utils import timezone

from cuentas.models import Usuario
from notificaciones import servicios
from notificaciones.models import EstadoNotificacion, Notificacion, TipoNotificacion
from tareas.models import Tarea

pytestmark = pytest.mark.django_db


# --- ADAPTABLE ---
def crear_tarea(creador, responsables=(), restringida=False):
    import datetime

    from tareas.models import ResponsableTarea

    tarea = Tarea.objects.create(
        nombre="Tarea de prueba",
        descripcion="Descripción de prueba",
        fecha_limite=timezone.localdate() + datetime.timedelta(days=5),
        creada_por=creador,
        restringida=restringida,
    )
    for usuario in responsables:
        ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
    return tarea


def crear_tarea_con_servicio(creador, responsables=(), restringida=False):
    import datetime

    from tareas.servicios import crear_tarea as crear_con_servicio

    return crear_con_servicio(
        creador,
        {
            "nombre": "Tarea de prueba",
            "descripcion": "Descripción de prueba",
            "fecha_limite": timezone.localdate() + datetime.timedelta(days=5),
            "restringida": restringida,
        },
        responsables,
    )


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def usuarios(settings):
    settings.DEBUG = True
    call_command("crear_datos_demo")
    Notificacion.objects.all().delete()
    return {
        clave: Usuario.objects.get(email=f"{clave}@ejemplo.local")
        for clave in ("admin", "subgerente", "lider.compras", "lider.calidad")
    }


def encolar_asignacion(tarea, usuario):
    return servicios.notificar_asignacion(tarea, usuario)


def test_encolar_es_idempotente_por_clave(usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    assert encolar_asignacion(tarea, usuarios["lider.compras"]) is not None
    assert encolar_asignacion(tarea, usuarios["lider.compras"]) is None
    assert Notificacion.objects.count() == 1


def test_no_encola_para_usuarios_inactivos(usuarios):
    lider = usuarios["lider.compras"]
    lider.is_active = False
    lider.save()
    tarea = crear_tarea(usuarios["subgerente"], [lider])
    assert encolar_asignacion(tarea, lider) is None


def test_envia_y_marca_como_enviada(usuarios, mailoutbox):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    notificacion = encolar_asignacion(tarea, usuarios["lider.compras"])
    assert servicios.enviar_pendientes() == 1
    notificacion.refresh_from_db()
    assert notificacion.estado == EstadoNotificacion.ENVIADA
    assert mailoutbox[0].to == ["lider.compras@ejemplo.local"]


def test_correo_de_tarea_normal_incluye_nombre_y_enlace(usuarios, mailoutbox):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    encolar_asignacion(tarea, usuarios["lider.compras"])
    servicios.enviar_pendientes()
    correo = mailoutbox[0]
    assert tarea.nombre in correo.subject
    assert tarea.nombre in correo.body
    assert f"/tareas/{tarea.pk}/" in correo.body


def test_correo_de_tarea_restringida_es_generico(usuarios, mailoutbox):
    tarea = crear_tarea(
        usuarios["subgerente"], [usuarios["lider.compras"]], restringida=True
    )
    encolar_asignacion(tarea, usuarios["lider.compras"])
    servicios.enviar_pendientes()
    correo = mailoutbox[0]
    html = correo.alternatives[0][0]
    for texto in (correo.subject, correo.body, html):
        assert tarea.nombre not in texto
        if tarea.descripcion:
            assert tarea.descripcion not in texto
    assert correo.subject == servicios.ASUNTO_RESTRINGIDA


def test_fallo_de_envio_programa_reintento(usuarios, monkeypatch):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    notificacion = encolar_asignacion(tarea, usuarios["lider.compras"])

    def fallar(self, *args, **kwargs):
        raise OSError("servidor no disponible")

    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", fallar)
    assert servicios.enviar_pendientes() == 0
    notificacion.refresh_from_db()
    assert notificacion.estado == EstadoNotificacion.PENDIENTE
    assert notificacion.intentos == 1
    assert "servidor no disponible" in notificacion.ultimo_error
    assert notificacion.proximo_intento > timezone.now()


def test_queda_fallida_al_agotar_los_intentos(usuarios, monkeypatch, settings):
    settings.NOTIFICACIONES_MAX_INTENTOS = 1
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    notificacion = encolar_asignacion(tarea, usuarios["lider.compras"])

    def fallar(self, *args, **kwargs):
        raise OSError("servidor no disponible")

    monkeypatch.setattr("django.core.mail.EmailMultiAlternatives.send", fallar)
    servicios.enviar_pendientes()
    notificacion.refresh_from_db()
    assert notificacion.estado == EstadoNotificacion.FALLIDA


def test_tarea_eliminada_cancela_el_envio(usuarios, mailoutbox):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    notificacion = encolar_asignacion(tarea, usuarios["lider.compras"])
    Tarea.objects.filter(pk=tarea.pk).update(
        eliminada_en=timezone.now() - timedelta(minutes=1)
    )
    servicios.enviar_pendientes()
    notificacion.refresh_from_db()
    assert notificacion.estado == EstadoNotificacion.CANCELADA
    assert mailoutbox == []


def test_crear_tarea_avisa_a_cada_responsable(usuarios):
    lideres = [usuarios["lider.compras"], usuarios["lider.calidad"]]
    crear_tarea_con_servicio(usuarios["subgerente"], lideres)
    destinatarios = set(
        Notificacion.objects.filter(tipo=TipoNotificacion.ASIGNACION).values_list(
            "destinatario__email", flat=True
        )
    )
    assert destinatarios == {
        "lider.compras@ejemplo.local",
        "lider.calidad@ejemplo.local",
    }


def test_cambio_de_rol_privilegiado_avisa_solo_a_los_demas_administradores(usuarios):
    segundo = Usuario.objects.create_user(
        email="admin2@ejemplo.local",
        password="Clave-de-prueba-123",
        debe_cambiar_contrasena=False,
    )
    segundo.groups.add(Group.objects.get(name="Administrador"))
    Notificacion.objects.all().delete()
    lider = usuarios["lider.compras"]
    lider.groups.add(Group.objects.get(name="Administrador"))
    destinatarios = set(
        Notificacion.objects.filter(tipo=TipoNotificacion.CAMBIO_ROL).values_list(
            "destinatario__email", flat=True
        )
    )
    assert destinatarios == {"admin@ejemplo.local", "admin2@ejemplo.local"}


def test_cambio_a_grupo_no_privilegiado_no_avisa(usuarios):
    usuarios["subgerente"].groups.add(Group.objects.get(name="Líder de área"))
    assert not Notificacion.objects.filter(tipo=TipoNotificacion.CAMBIO_ROL).exists()


def test_comando_enviar_notificaciones(usuarios, mailoutbox):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    encolar_asignacion(tarea, usuarios["lider.compras"])
    call_command("enviar_notificaciones")
    assert len(mailoutbox) == 1
