import io

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import Client
from django.urls import reverse

from auditoria.models import EventoAuditoria
from cuentas.roles import ADMINISTRADOR, SUBGERENTE
from cuentas.servicios import (
    sincronizar_acceso_panel,
    validar_que_no_es_el_ultimo_administrador,
)

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"
CLAVE_NUEVA = "Clave-restablecida-segura-2026"


def crear_usuario(email, grupo=None, **campos):
    usuario = get_user_model().objects.create_user(
        email=email, password=CLAVE, **campos
    )
    if grupo:
        usuario.groups.add(Group.objects.get(name=grupo))
        sincronizar_acceso_panel(usuario)
    return usuario


def url_cambio(usuario):
    return reverse("admin:cuentas_usuario_change", args=[usuario.pk])


@pytest.fixture
def administrador():
    return crear_usuario("admin@ejemplo.local", ADMINISTRADOR)


@pytest.fixture
def cliente_admin(client, administrador):
    client.force_login(administrador)
    return client


def test_la_ruta_admin_predeterminada_no_existe(cliente_admin):
    assert cliente_admin.get("/admin/").status_code == 404


def test_el_administrador_entra_al_panel(cliente_admin):
    assert cliente_admin.get(reverse("admin:index")).status_code == 200


def test_un_lider_no_entra_al_panel(client):
    client.force_login(crear_usuario("lider@ejemplo.local"))
    assert client.get(reverse("admin:index")).status_code == 302


def test_formulario_sin_superusuario_ni_permisos_individuales(cliente_admin):
    otro = crear_usuario("otro@ejemplo.local")
    respuesta = cliente_admin.get(url_cambio(otro))
    contenido = respuesta.content.decode()
    assert respuesta.status_code == 200
    assert 'name="is_superuser"' not in contenido
    assert 'name="user_permissions"' not in contenido
    assert 'name="is_staff"' not in contenido


def test_no_se_pueden_eliminar_usuarios(cliente_admin):
    otro = crear_usuario("otro@ejemplo.local")
    url = reverse("admin:cuentas_usuario_delete", args=[otro.pk])
    assert cliente_admin.get(url).status_code == 403


def test_el_administrador_no_cambia_sus_propios_grupos(cliente_admin, administrador):
    contenido = cliente_admin.get(url_cambio(administrador)).content.decode()
    assert 'name="groups"' not in contenido
    assert 'name="is_active"' not in contenido


def test_usuario_creado_desde_el_panel_debe_cambiar_su_clave(cliente_admin):
    respuesta = cliente_admin.post(
        reverse("admin:cuentas_usuario_add"),
        {
            "email": "Nuevo@Ejemplo.local",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "area": "",
            "password1": CLAVE_NUEVA,
            "password2": CLAVE_NUEVA,
            "_save": "Guardar",
        },
    )
    assert respuesta.status_code == 302
    nuevo = get_user_model().objects.get(email="nuevo@ejemplo.local")
    assert nuevo.debe_cambiar_contrasena is True
    assert nuevo.is_superuser is False
    assert nuevo.is_staff is False


def test_restablecer_clave_obliga_a_cambiarla_y_cierra_sesiones(cliente_admin):
    otro = crear_usuario("otro@ejemplo.local")
    sesion_del_otro = Client()
    sesion_del_otro.force_login(otro)

    url = url_cambio(otro).replace("change/", "password/")
    respuesta = cliente_admin.post(
        url,
        {"password1": CLAVE_NUEVA, "password2": CLAVE_NUEVA, "usable_password": "true"},
    )
    assert respuesta.status_code == 302

    otro.refresh_from_db()
    assert otro.check_password(CLAVE_NUEVA)
    assert otro.debe_cambiar_contrasena is True

    respuesta = sesion_del_otro.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("login"))


def test_el_unico_administrador_no_queda_sin_rol_ni_desactivado(administrador):
    with pytest.raises(ValidationError):
        validar_que_no_es_el_ultimo_administrador(
            administrador, seguira_activo=False, seguira_siendo_admin=True
        )
    with pytest.raises(ValidationError):
        validar_que_no_es_el_ultimo_administrador(
            administrador, seguira_activo=True, seguira_siendo_admin=False
        )


def test_con_otro_administrador_activo_si_se_permite(administrador):
    crear_usuario("admin2@ejemplo.local", ADMINISTRADOR)
    validar_que_no_es_el_ultimo_administrador(
        administrador, seguira_activo=False, seguira_siendo_admin=True
    )


def test_solo_los_administradores_tienen_acceso_al_panel():
    subgerente = crear_usuario("sub@ejemplo.local", SUBGERENTE)
    administrador = crear_usuario("adm@ejemplo.local", ADMINISTRADOR)
    assert administrador.is_staff and not administrador.is_superuser
    assert not subgerente.is_staff


def test_recuperar_admin_crea_un_administrador_sin_superusuario():
    call_command(
        "recuperar_admin",
        email="Rescate@Ejemplo.local",
        motivo="Prueba de recuperación",
        stdout=io.StringIO(),
    )
    usuario = get_user_model().objects.get(email="rescate@ejemplo.local")
    assert usuario.groups.filter(name=ADMINISTRADOR).exists()
    assert usuario.is_staff and not usuario.is_superuser
    assert usuario.debe_cambiar_contrasena is True
    assert EventoAuditoria.objects.filter(
        accion="cuentas.recuperar_admin", recurso_id=str(usuario.pk)
    ).exists()


def test_recuperar_admin_exige_motivo():
    with pytest.raises(CommandError):
        call_command(
            "recuperar_admin",
            email="x@ejemplo.local",
            motivo="   ",
            stdout=io.StringIO(),
        )
