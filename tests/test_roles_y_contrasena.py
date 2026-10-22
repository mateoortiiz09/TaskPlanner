import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from cuentas.roles import ADMINISTRADOR, LIDER_AREA, SUBGERENTE

pytestmark = pytest.mark.django_db

CLAVE_TEMPORAL = "Clave-temporal-2026"
CLAVE_NUEVA = "Clave-definitiva-segura-2026"


def permisos_del_grupo(nombre):
    grupo = Group.objects.get(name=nombre)
    return {f"{p.content_type.app_label}.{p.codename}" for p in grupo.permissions.all()}


def test_existen_los_tres_grupos():
    nombres = set(Group.objects.values_list("name", flat=True))
    assert {ADMINISTRADOR, SUBGERENTE, LIDER_AREA} <= nombres


def test_administrador_gestiona_usuarios_pero_no_completa_tareas():
    permisos = permisos_del_grupo(ADMINISTRADOR)
    assert "cuentas.gestionar_usuarios" in permisos
    assert "tareas.completar_tareas" not in permisos
    assert "tareas.cambiar_estado" not in permisos
    assert "tareas.ver_restringidas" not in permisos
    assert "tareas.conceder_nivel3" not in permisos


def test_subgerente_completa_tareas_pero_no_gestiona_usuarios():
    permisos = permisos_del_grupo(SUBGERENTE)
    assert "tareas.completar_tareas" in permisos
    assert "tareas.ver_restringidas" in permisos
    assert "tareas.conceder_nivel3" not in permisos
    assert "cuentas.gestionar_usuarios" not in permisos


def test_lider_solo_consulta():
    assert permisos_del_grupo(LIDER_AREA) == {
        "tareas.view_tarea",
        "adjuntos.view_adjunto",
    }


def test_usuario_hereda_los_permisos_de_su_grupo():
    usuario = get_user_model().objects.create_user(
        email="subgerente@ejemplo.local", password=CLAVE_TEMPORAL
    )
    usuario.groups.add(Group.objects.get(name=SUBGERENTE))
    usuario = get_user_model().objects.get(pk=usuario.pk)
    assert usuario.has_perm("tareas.completar_tareas")
    assert not usuario.has_perm("cuentas.gestionar_usuarios")


@pytest.fixture
def usuario_con_clave_temporal():
    return get_user_model().objects.create_user(
        email="nuevo@ejemplo.local",
        password=CLAVE_TEMPORAL,
        debe_cambiar_contrasena=True,
    )


def test_clave_temporal_obliga_a_cambiarla(client, usuario_con_clave_temporal):
    client.force_login(usuario_con_clave_temporal)
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("cambiar_contrasena")


def test_puede_cerrar_sesion_sin_cambiar_la_clave(client, usuario_con_clave_temporal):
    client.force_login(usuario_con_clave_temporal)
    respuesta = client.post(reverse("logout"))
    assert respuesta.status_code == 302
    assert "_auth_user_id" not in client.session


def test_tras_cambiar_la_clave_puede_usar_el_sistema(
    client, usuario_con_clave_temporal
):
    client.force_login(usuario_con_clave_temporal)
    respuesta = client.post(
        reverse("cambiar_contrasena"),
        {
            "old_password": CLAVE_TEMPORAL,
            "new_password1": CLAVE_NUEVA,
            "new_password2": CLAVE_NUEVA,
        },
    )
    assert respuesta.status_code == 302
    usuario_con_clave_temporal.refresh_from_db()
    assert usuario_con_clave_temporal.debe_cambiar_contrasena is False
    assert usuario_con_clave_temporal.check_password(CLAVE_NUEVA)
    assert client.get(reverse("inicio")).status_code == 200
