import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse

from cuentas.roles import ADMINISTRADOR
from cuentas.servicios import sincronizar_acceso_panel

pytestmark = pytest.mark.django_db


@pytest.fixture
def cliente_admin(client):
    administrador = get_user_model().objects.create_user(
        email="admin@ejemplo.local", password="Clave-de-prueba-123"
    )
    administrador.groups.add(Group.objects.get(name=ADMINISTRADOR))
    sincronizar_acceso_panel(administrador)
    client.force_login(administrador)
    client.administrador = administrador
    return client


def test_el_panel_no_carga_recursos_de_internet(cliente_admin):
    for url in (
        reverse("admin:index"),
        reverse("admin:cuentas_usuario_changelist"),
        reverse("admin:cuentas_usuario_change", args=[cliente_admin.administrador.pk]),
    ):
        respuesta = cliente_admin.get(url)
        assert respuesta.status_code == 200
        contenido = respuesta.content.decode()
        assert "googleapis" not in contenido
        assert "cdn." not in contenido


def test_los_botones_dicen_guardar(cliente_admin):
    contenido = cliente_admin.get(reverse("admin:cuentas_area_add")).content.decode()
    assert "Guardar" in contenido
    assert "Grabar" not in contenido
