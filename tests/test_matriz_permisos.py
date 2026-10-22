from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from adjuntos import servicios as servicios_adjuntos
from cuentas.models import Usuario
from tareas.models import EstadoAvance, ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
NOMBRE_CAMBIO_CONTRASENA = "cambiar_contrasena"

OK = "OK"
DENEGADO = "DENEGADO"
LOGIN = "LOGIN"


# --- ADAPTABLE ---
def crear_tarea(creador, responsables=(), restringida=False):
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


def eliminar_tarea(tarea, usuario):
    tarea.eliminada_en = timezone.now()
    tarea.eliminada_por = usuario
    tarea.save(update_fields=["eliminada_en", "eliminada_por", "actualizada_en"])
    return tarea


# --- FIN DE LO ADAPTABLE ---


@pytest.fixture
def escenario(settings, tmp_path):
    settings.DEBUG = True
    settings.PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
    settings.ADJUNTOS_DIR = tmp_path / "adjuntos"
    settings.ANTIVIRUS_ACTIVO = False
    call_command("crear_datos_demo")
    usuarios = {
        "admin": Usuario.objects.get(email="admin@ejemplo.local"),
        "subgerente": Usuario.objects.get(email="subgerente@ejemplo.local"),
        "lider_resp": Usuario.objects.get(email="lider.compras@ejemplo.local"),
        "lider_otro": Usuario.objects.get(email="lider.calidad@ejemplo.local"),
    }
    sub = usuarios["subgerente"]
    responsable = usuarios["lider_resp"]
    normal = crear_tarea(sub, [responsable])
    restringida = crear_tarea(sub, [responsable], restringida=True)
    eliminada = crear_tarea(sub, [responsable])
    eliminar_tarea(eliminada, sub)
    adjunto_normal = servicios_adjuntos.subir_adjunto(
        tarea=normal,
        archivo=SimpleUploadedFile("a.pdf", PDF),
        usuario=sub,
    )
    adjunto_restringida = servicios_adjuntos.subir_adjunto(
        tarea=restringida,
        archivo=SimpleUploadedFile("b.pdf", PDF),
        usuario=sub,
    )
    return {
        "usuarios": usuarios,
        "T": normal,
        "R": restringida,
        "D": eliminada,
        "AT": adjunto_normal,
        "AR": adjunto_restringida,
    }


def otro_estado(tarea):
    return [
        valor
        for valor in EstadoAvance.values
        if valor not in (tarea.estado, EstadoAvance.COMPLETADA)
    ][0]


FILAS = {
    "inicio": ("get", lambda e: reverse("inicio"), None),
    "lista": ("get", lambda e: reverse("tareas:lista"), None),
    "nueva": ("get", lambda e: reverse("tareas:crear"), None),
    "detalle_T": ("get", lambda e: reverse("tareas:detalle", args=[e["T"].pk]), None),
    "detalle_R": ("get", lambda e: reverse("tareas:detalle", args=[e["R"].pk]), None),
    "editar_T": ("get", lambda e: reverse("tareas:editar", args=[e["T"].pk]), None),
    "editar_R": ("get", lambda e: reverse("tareas:editar", args=[e["R"].pk]), None),
    "estado_T": (
        "post",
        lambda e: reverse("tareas:cambiar_estado", args=[e["T"].pk]),
        lambda e: {"estado": otro_estado(e["T"])},
    ),
    "completar_T": (
        "get",
        lambda e: reverse("tareas:completar", args=[e["T"].pk]),
        None,
    ),
    "eliminar_T": (
        "get",
        lambda e: reverse("tareas:eliminar", args=[e["T"].pk]),
        None,
    ),
    "eliminar_R": (
        "get",
        lambda e: reverse("tareas:eliminar", args=[e["R"].pk]),
        None,
    ),
    "papelera": ("get", lambda e: reverse("tareas:papelera"), None),
    "recuperar_D": (
        "post",
        lambda e: reverse("tareas:recuperar", args=[e["D"].pk]),
        lambda e: {},
    ),
    "adjuntar_T": (
        "post",
        lambda e: reverse("tareas:adjunto_subir", args=[e["T"].pk]),
        lambda e: {"archivo": SimpleUploadedFile("c.pdf", PDF)},
    ),
    "descargar_AT": (
        "get",
        lambda e: reverse("tareas:adjunto_descargar", args=[e["T"].pk, e["AT"].pk]),
        None,
    ),
    "descargar_AR": (
        "get",
        lambda e: reverse("tareas:adjunto_descargar", args=[e["R"].pk, e["AR"].pk]),
        None,
    ),
    "auditoria": ("get", lambda e: reverse("auditoria:lista"), None),
    "panel_admin": ("get", lambda e: reverse("admin:index"), None),
    "cambiar_contrasena": (
        "get",
        lambda e: reverse(NOMBRE_CAMBIO_CONTRASENA),
        None,
    ),
}

ESPERADO = {
    "inicio": (LOGIN, OK, OK, OK, OK),
    "lista": (LOGIN, OK, OK, OK, OK),
    "nueva": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "detalle_T": (LOGIN, OK, OK, OK, DENEGADO),
    "detalle_R": (LOGIN, OK, OK, OK, DENEGADO),
    "editar_T": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "editar_R": (LOGIN, DENEGADO, OK, DENEGADO, DENEGADO),
    "estado_T": (LOGIN, DENEGADO, OK, DENEGADO, DENEGADO),
    "completar_T": (LOGIN, DENEGADO, OK, DENEGADO, DENEGADO),
    "eliminar_T": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "eliminar_R": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "papelera": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "recuperar_D": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "adjuntar_T": (LOGIN, DENEGADO, OK, DENEGADO, DENEGADO),
    "descargar_AT": (LOGIN, OK, OK, OK, DENEGADO),
    "descargar_AR": (LOGIN, DENEGADO, OK, OK, DENEGADO),
    "auditoria": (LOGIN, OK, OK, DENEGADO, DENEGADO),
    "panel_admin": (LOGIN, OK, DENEGADO, DENEGADO, DENEGADO),
    "cambiar_contrasena": (LOGIN, OK, OK, OK, OK),
}
ROLES = ("anonimo", "admin", "subgerente", "lider_resp", "lider_otro")
CASOS = [
    pytest.param(fila, rol, ESPERADO[fila][indice], id=f"{fila}-{rol}")
    for fila in FILAS
    for indice, rol in enumerate(ROLES)
]


def clasificar(respuesta):
    codigo = respuesta.status_code
    if codigo in (403, 404):
        return DENEGADO
    if codigo in (301, 302):
        destino = respuesta["Location"]
        return LOGIN if ("ingresar" in destino or "login" in destino) else OK
    if 200 <= codigo < 300:
        return OK
    return f"HTTP {codigo}"


@pytest.mark.parametrize(("fila", "rol", "esperado"), CASOS)
def test_matriz_de_permisos(client, escenario, fila, rol, esperado):
    if rol != "anonimo":
        client.force_login(escenario["usuarios"][rol])
    metodo, construir_url, construir_datos = FILAS[fila]
    url = construir_url(escenario)
    if metodo == "get":
        respuesta = client.get(url)
    else:
        respuesta = client.post(url, construir_datos(escenario))
    obtenido = clasificar(respuesta)
    if esperado == DENEGADO and obtenido == LOGIN:
        obtenido = DENEGADO
    assert obtenido == esperado, (
        f"{fila} / {rol}: esperado {esperado}, obtenido {obtenido} "
        f"(HTTP {respuesta.status_code})"
    )
