import pytest
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse

from adjuntos import servicios as servicios_adjuntos
from auditoria.models import EventoAuditoria
from auditoria.servicios import registrar_evento
from cuentas.models import Usuario
from tareas.models import EstadoAvance, ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

CONTRASENA = "Demo.Local.2026#"
PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


# --- ADAPTABLE ---
def crear_tarea(creador, responsables=(), restringida=False):
    import datetime

    from django.utils import timezone

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


def ingresar(client, email, contrasena):
    return client.post(reverse("login"), {"username": email, "password": contrasena})


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def usuarios(settings, tmp_path):
    settings.DEBUG = True
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ANTIVIRUS_ACTIVO = False
    call_command("crear_datos_demo")
    return {
        clave: Usuario.objects.get(email=f"{clave}@ejemplo.local")
        for clave in ("admin", "subgerente", "lider.compras", "lider.calidad")
    }


def eventos(accion):
    return EventoAuditoria.objects.filter(accion=accion)


def test_registrar_evento_guarda_actor_y_datos(usuarios):
    evento = registrar_evento("tarea.creada", actor=usuarios["subgerente"], tarea_id=7)
    assert evento.actor == usuarios["subgerente"]
    assert evento.cambios == {"tarea_id": 7}


def test_accion_desconocida_falla(usuarios):
    with pytest.raises(ValueError):
        registrar_evento("accion.inventada")


def test_inicio_de_sesion_se_registra_con_ip(client, usuarios):
    ingresar(client, "subgerente@ejemplo.local", CONTRASENA)
    evento = (
        eventos("sesion.iniciada").filter(actor=usuarios["subgerente"]).latest("pk")
    )
    assert evento.ip == "127.0.0.1"


def test_inicio_fallido_se_registra_sin_contrasena(client, usuarios):
    ingresar(client, "subgerente@ejemplo.local", "clave-incorrecta-123")
    evento = eventos("sesion.fallida").latest("pk")
    assert evento.cambios["correo"] == "subgerente@ejemplo.local"
    assert "clave-incorrecta-123" not in str(evento.cambios)


def test_cierre_de_sesion_se_registra(client, usuarios):
    client.force_login(usuarios["subgerente"])
    client.post(reverse("logout"))
    assert eventos("sesion.cerrada").filter(actor=usuarios["subgerente"]).exists()


def test_cambio_de_grupo_se_registra(usuarios):
    lider = usuarios["lider.compras"]
    lider.groups.add(Group.objects.get(name="Subgerente"))
    evento = eventos("usuario.rol_cambiado").latest("pk")
    assert evento.cambios["usuario_id"] == lider.pk
    assert "Subgerente" in evento.cambios["grupos"]


def test_eliminar_y_recuperar_se_registran_sin_nombre(client, usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    client.force_login(usuarios["subgerente"])
    client.post(reverse("tareas:eliminar", args=[tarea.pk]))
    client.post(reverse("tareas:recuperar", args=[tarea.pk]))
    for accion in ("tarea.eliminada", "tarea.recuperada"):
        evento = eventos(accion).get()
        assert evento.cambios["tarea_id"] == tarea.pk
        assert evento.actor == usuarios["subgerente"]
        assert tarea.nombre not in str(evento.cambios)


def test_cambio_de_estado_registra_anterior_y_nuevo(client, usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    anterior = tarea.estado
    nuevo = [
        valor
        for valor in EstadoAvance.values
        if valor not in (anterior, EstadoAvance.COMPLETADA)
    ][0]
    client.force_login(usuarios["subgerente"])
    client.post(reverse("tareas:cambiar_estado", args=[tarea.pk]), {"estado": nuevo})
    evento = eventos("tarea.estado_cambiado").get()
    assert evento.cambios["estado_anterior"] == anterior
    assert evento.cambios["estado_nuevo"] == nuevo


def test_descarga_de_adjunto_se_registra(client, usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    adjunto = servicios_adjuntos.subir_adjunto(
        tarea=tarea,
        archivo=SimpleUploadedFile("acta.pdf", PDF),
        usuario=usuarios["subgerente"],
    )
    client.force_login(usuarios["lider.compras"])
    client.get(reverse("tareas:adjunto_descargar", args=[tarea.pk, adjunto.pk]))
    evento = eventos("adjunto.descargado").get()
    assert evento.actor == usuarios["lider.compras"]
    assert evento.cambios["adjunto_id"] == adjunto.pk
    assert "acta.pdf" not in str(evento.cambios)


def test_404_por_falta_de_permiso_se_registra(client, usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    client.force_login(usuarios["lider.calidad"])
    respuesta = client.get(reverse("tareas:detalle", args=[tarea.pk]))
    assert respuesta.status_code == 404
    evento = eventos("acceso.denegado").get()
    assert evento.actor == usuarios["lider.calidad"]
    assert evento.cambios["tarea_id"] == tarea.pk


def test_403_se_registra(client, usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    client.force_login(usuarios["lider.compras"])
    respuesta = client.post(
        reverse("tareas:adjunto_subir", args=[tarea.pk]),
        {"archivo": SimpleUploadedFile("acta.pdf", PDF)},
    )
    assert respuesta.status_code == 403
    assert eventos("acceso.denegado").filter(actor=usuarios["lider.compras"]).exists()


def test_recuperar_admin_se_registra(usuarios):
    call_command("recuperar_admin", email="nuevo.admin@ejemplo.local", motivo="Prueba")
    evento = eventos("cuentas.recuperar_admin").get()
    assert evento.cambios["correo"] == "nuevo.admin@ejemplo.local"
    assert evento.cambios["motivo"] == "Prueba"


def test_subgerente_ve_la_auditoria_de_tareas_y_no_la_tecnica(client, usuarios):
    registrar_evento("tarea.creada", tarea_id=987654)
    registrar_evento("sesion.fallida", correo="intruso.prueba@ejemplo.local")
    client.force_login(usuarios["subgerente"])
    html = client.get(reverse("auditoria:lista")).content.decode()
    assert "987654" in html
    assert "intruso.prueba@ejemplo.local" not in html


def test_administrador_ve_la_auditoria_tecnica_y_no_la_de_tareas(client, usuarios):
    registrar_evento("tarea.creada", tarea_id=987654)
    registrar_evento("sesion.fallida", correo="intruso.prueba@ejemplo.local")
    client.force_login(usuarios["admin"])
    html = client.get(reverse("auditoria:lista")).content.decode()
    assert "intruso.prueba@ejemplo.local" in html
    assert "987654" not in html


def test_lider_no_accede_a_la_auditoria(client, usuarios):
    client.force_login(usuarios["lider.compras"])
    assert client.get(reverse("auditoria:lista")).status_code == 403
