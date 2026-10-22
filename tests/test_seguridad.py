from urllib.parse import urlencode

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from adjuntos import servicios as servicios_adjuntos
from cuentas.models import Usuario
from tareas.models import ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
CONTRASENA = "Demo.Local.2026#"


# --- ADAPTABLE ---
def crear_tarea(creador, responsables=(), restringida=False, nombre=None):
    from datetime import timedelta

    from django.utils import timezone

    tarea = Tarea.objects.create(
        nombre=nombre or "Tarea de prueba",
        descripcion="Descripción de prueba",
        fecha_limite=timezone.localdate() + timedelta(days=5),
        creada_por=creador,
        restringida=restringida,
    )
    for usuario in responsables:
        ResponsableTarea.objects.create(tarea=tarea, usuario=usuario)
    return tarea


def ingresar(client, email, contrasena, siguiente=None):
    url = reverse("login")
    if siguiente is not None:
        url = f"{url}?{urlencode({'next': siguiente})}"
    return client.post(url, {"username": email, "password": contrasena})


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def usuarios(settings, tmp_path):
    settings.DEBUG = True
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ANTIVIRUS_ACTIVO = False
    call_command("crear_datos_demo")
    return {
        clave: Usuario.objects.get(email=f"{clave}@ejemplo.local")
        for clave in ("admin", "subgerente", "lider.compras", "lider.calidad")
    }


def test_post_sin_token_csrf_es_rechazado(usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    cliente = Client(enforce_csrf_checks=True)
    cliente.force_login(usuarios["subgerente"])
    respuesta = cliente.post(reverse("tareas:eliminar", args=[tarea.pk]))
    assert respuesta.status_code == 403
    tarea.refresh_from_db()
    assert tarea.eliminada_en is None


def test_cabeceras_de_seguridad(client, usuarios):
    client.force_login(usuarios["subgerente"])
    respuesta = client.get(reverse("tareas:lista"))
    assert respuesta["X-Frame-Options"] == "DENY"
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert respuesta["Referrer-Policy"] == "same-origin"
    assert respuesta["Cross-Origin-Opener-Policy"] == "same-origin"


def test_inicio_de_sesion_no_redirige_a_sitios_externos(client, usuarios):
    respuesta = ingresar(
        client,
        "subgerente@ejemplo.local",
        CONTRASENA,
        siguiente="https://malicioso.example/",
    )
    assert "malicioso.example" not in respuesta.get("Location", "")


def test_usuario_inactivo_no_puede_ingresar(client, usuarios):
    usuario = usuarios["subgerente"]
    usuario.is_active = False
    usuario.save()
    ingresar(client, usuario.email, CONTRASENA)
    assert "_auth_user_id" not in client.session


def test_tabla_htmx_enmascara_restringidas_al_administrador(client, usuarios):
    tarea = crear_tarea(
        usuarios["subgerente"],
        [usuarios["lider.compras"]],
        restringida=True,
        nombre="Proyecto secreto X",
    )
    client.force_login(usuarios["admin"])
    html = client.get(reverse("tareas:lista"), HTTP_HX_REQUEST="true").content.decode()
    assert tarea.nombre not in html


def test_las_tareas_no_se_administran_desde_el_panel(client, usuarios):
    client.force_login(usuarios["admin"])
    assert client.get("/gestion-interna/tareas/tarea/").status_code == 404


def test_el_nombre_del_archivo_no_conserva_rutas(usuarios):
    tarea = crear_tarea(usuarios["subgerente"], [usuarios["lider.compras"]])
    adjunto = servicios_adjuntos.subir_adjunto(
        tarea=tarea,
        archivo=SimpleUploadedFile("../../malicioso.pdf", PDF),
        usuario=usuarios["subgerente"],
    )
    assert adjunto.nombre_original == "malicioso.pdf"


def test_el_contenido_de_las_tareas_se_escapa(client, usuarios):
    crear_tarea(
        usuarios["subgerente"],
        [usuarios["lider.compras"]],
        nombre="<script>alert(1)</script>",
    )
    client.force_login(usuarios["subgerente"])
    html = client.get(reverse("tareas:lista")).content.decode()
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_cookies_de_sesion_protegidas(settings):
    assert settings.SESSION_COOKIE_HTTPONLY is True
    assert settings.SESSION_COOKIE_SAMESITE in ("Lax", "Strict")
