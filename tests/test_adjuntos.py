import base64
import io
import secrets
import zipfile

import pytest
from cryptography.exceptions import InvalidTag
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from adjuntos import almacen, cifrado, servicios, validacion
from adjuntos.checks import comprobar_adjuntos
from adjuntos.models import Adjunto, EstadoAnalisis
from tareas.models import Tarea

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def office(carpeta, macros=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archivo_zip:
        archivo_zip.writestr("[Content_Types].xml", "<Types/>")
        archivo_zip.writestr(f"{carpeta}documento.xml", "<x/>")
        if macros:
            archivo_zip.writestr(f"{carpeta}vbaProject.bin", b"\x00")
    return buffer.getvalue()


# --- ADAPTABLE: solo el cuerpo de estas dos funciones ---
def crear_usuario(email, grupo):
    """Crea un usuario activo en el grupo indicado.

    Si el grupo es "Líder de área", asígnale un área (créala si hace falta).
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import Group

    from cuentas.models import Area
    from cuentas.roles import LIDER_AREA

    area = Area.objects.create(nombre=f"Área {email}") if grupo == LIDER_AREA else None
    usuario = get_user_model().objects.create_user(
        email=email,
        password="Clave-de-prueba-123",
        area=area,
        debe_cambiar_contrasena=False,
    )
    usuario.groups.add(Group.objects.get(name=grupo))
    return get_user_model().objects.get(pk=usuario.pk)


def crear_tarea(creador, responsables=(), restringida=False):
    """Crea una tarea activa con esos responsables y la devuelve."""
    import datetime

    from django.utils import timezone

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


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture(autouse=True)
def configuracion_adjuntos(settings, tmp_path):
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ADJUNTOS_CLAVE_MAESTRA = base64.urlsafe_b64encode(
        secrets.token_bytes(32)
    ).decode()
    settings.ADJUNTOS_TAMANO_MAX_MB = 1
    settings.ANTIVIRUS_ACTIVO = False


@pytest.fixture
def subgerente():
    return crear_usuario("subgerente@ejemplo.local", "Subgerente")


@pytest.fixture
def administrador():
    return crear_usuario("admin@ejemplo.local", "Administrador")


@pytest.fixture
def lider():
    return crear_usuario("lider@ejemplo.local", "Líder de área")


@pytest.fixture
def otro_lider():
    return crear_usuario("otro.lider@ejemplo.local", "Líder de área")


def subir(client, tarea, nombre, contenido):
    return client.post(
        reverse("tareas:adjunto_subir", args=[tarea.pk]),
        {"archivo": SimpleUploadedFile(nombre, contenido)},
    )


def adjuntar(tarea, usuario, nombre="acta.pdf", contenido=PDF):
    return servicios.subir_adjunto(
        tarea=tarea, archivo=SimpleUploadedFile(nombre, contenido), usuario=usuario
    )


def url_descarga(adjunto):
    return reverse("tareas:adjunto_descargar", args=[adjunto.tarea_id, adjunto.pk])


@pytest.mark.parametrize(
    ("nombre", "contenido"),
    [
        ("a.pdf", PDF),
        ("a.docx", office("word/")),
        ("a.xlsx", office("xl/")),
        ("a.png", PNG),
        ("a.jpg", JPG),
    ],
)
def test_acepta_los_formatos_permitidos(nombre, contenido):
    assert validacion.validar(nombre, contenido)


def test_rechaza_svg():
    with pytest.raises(ValidationError):
        validacion.validar("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'/>")


def test_rechaza_contenido_que_no_coincide_con_la_extension():
    with pytest.raises(ValidationError):
        validacion.validar("factura.pdf", b"MZ\x90\x00" + b"\x00" * 32)


def test_rechaza_documentos_con_macros():
    with pytest.raises(ValidationError, match="macros"):
        validacion.validar("informe.docx", office("word/", macros=True))


def test_rechaza_archivos_demasiado_grandes():
    with pytest.raises(ValidationError):
        validacion.validar("grande.pdf", PDF + b"0" * (1024 * 1024))


def test_cifrado_ida_y_vuelta_con_dato_asociado():
    contenido, clave = cifrado.cifrar(b"secreto", b"nombre-a")
    assert b"secreto" not in contenido
    assert cifrado.descifrar(contenido, clave, b"nombre-a") == b"secreto"
    with pytest.raises(InvalidTag):
        cifrado.descifrar(contenido, clave, b"nombre-b")


def test_subgerente_adjunta_archivo_en_tarea_normal(client, subgerente, lider):
    tarea = crear_tarea(subgerente, [lider])
    client.force_login(subgerente)
    respuesta = subir(client, tarea, "acta.pdf", PDF)
    assert respuesta.status_code == 302
    adjunto = Adjunto.objects.get(tarea=tarea)
    assert adjunto.nombre_original == "acta.pdf"
    assert adjunto.cifrado is False
    assert adjunto.estado_analisis == EstadoAnalisis.SIN_ANALIZAR
    assert almacen.leer(adjunto.nombre_interno) == PDF


def test_adjunto_de_tarea_restringida_se_guarda_cifrado(client, subgerente, lider):
    tarea = crear_tarea(subgerente, [lider], restringida=True)
    client.force_login(subgerente)
    subir(client, tarea, "acta.pdf", PDF)
    adjunto = Adjunto.objects.get(tarea=tarea)
    assert adjunto.cifrado is True
    assert almacen.leer(adjunto.nombre_interno) != PDF
    assert client.get(url_descarga(adjunto)).content == PDF


def test_marcar_restringida_cifra_los_adjuntos_existentes(
    subgerente, lider, django_capture_on_commit_callbacks
):
    tarea = crear_tarea(subgerente, [lider])
    adjunto = adjuntar(tarea, subgerente)
    nombre_anterior = adjunto.nombre_interno
    Tarea.objects.filter(pk=tarea.pk).update(restringida=True)
    tarea.refresh_from_db()
    with django_capture_on_commit_callbacks(execute=True):
        servicios.cifrar_adjuntos_de_tarea(tarea)
    adjunto.refresh_from_db()
    assert adjunto.cifrado is True
    assert almacen.leer(adjunto.nombre_interno) != PDF
    assert not almacen.ruta_de(nombre_anterior).exists()
    assert servicios.leer_contenido(adjunto) == PDF


def test_descarga_con_cabeceras_seguras(client, subgerente, lider):
    tarea = crear_tarea(subgerente, [lider])
    adjunto = adjuntar(tarea, subgerente)
    client.force_login(lider)
    respuesta = client.get(url_descarga(adjunto))
    assert respuesta.status_code == 200
    assert respuesta["X-Content-Type-Options"] == "nosniff"
    assert "no-store" in respuesta["Cache-Control"]
    assert respuesta["Content-Disposition"].startswith("attachment")
    assert respuesta.content == PDF


def test_administrador_no_descarga_adjuntos_de_tareas_restringidas(
    client, subgerente, administrador, lider
):
    tarea = crear_tarea(subgerente, [lider], restringida=True)
    adjunto = adjuntar(tarea, subgerente)
    client.force_login(administrador)
    assert client.get(url_descarga(adjunto)).status_code == 404
    detalle = client.get(reverse("tareas:detalle", args=[tarea.pk]))
    assert "acta.pdf" not in detalle.content.decode()


def test_lider_no_responsable_recibe_404(client, subgerente, lider, otro_lider):
    tarea = crear_tarea(subgerente, [lider])
    adjunto = adjuntar(tarea, subgerente)
    client.force_login(otro_lider)
    assert client.get(url_descarga(adjunto)).status_code == 404


def test_solo_la_subgerente_puede_adjuntar(client, subgerente, administrador, lider):
    tarea = crear_tarea(subgerente, [lider])
    for usuario in (administrador, lider):
        client.force_login(usuario)
        assert subir(client, tarea, "acta.pdf", PDF).status_code in (403, 404)
    assert not Adjunto.objects.filter(tarea=tarea).exists()


def test_produccion_exige_antivirus_y_clave_maestra(settings):
    settings.DEBUG = False
    settings.ANTIVIRUS_ACTIVO = False
    settings.ADJUNTOS_CLAVE_MAESTRA = ""
    ids = {error.id for error in comprobar_adjuntos(None)}
    assert ids == {"adjuntos.E001", "adjuntos.E002"}


def datos_edicion(tarea, responsable, restringida):
    return {
        "nombre": tarea.nombre,
        "descripcion": tarea.descripcion,
        "fecha_limite": tarea.fecha_limite.isoformat(),
        "prioridad": tarea.prioridad,
        "restringida": "on" if restringida else "",
        "responsables": [responsable.pk],
        "version": tarea.version,
    }


def test_editar_tarea_a_restringida_cifra_sus_adjuntos(client, subgerente, lider):
    tarea = crear_tarea(subgerente, [lider])
    adjunto = adjuntar(tarea, subgerente)
    client.force_login(subgerente)
    respuesta = client.post(
        reverse("tareas:editar", args=[tarea.pk]),
        datos_edicion(tarea, lider, restringida=True),
    )
    assert respuesta.status_code == 302
    adjunto.refresh_from_db()
    assert adjunto.cifrado is True
    assert almacen.leer(adjunto.nombre_interno) != PDF
    assert client.get(url_descarga(adjunto)).content == PDF
