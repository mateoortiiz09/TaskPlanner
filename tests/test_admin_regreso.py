import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_panel_de_administracion_tiene_enlace_de_regreso(client, settings):
    from django.core.management import call_command

    from cuentas.models import Usuario

    settings.DEBUG = True
    call_command("crear_datos_demo")
    client.force_login(Usuario.objects.get(email="admin@ejemplo.local"))
    respuesta = client.get(reverse("admin:index"))
    assert respuesta.status_code == 200
    html = respuesta.content.decode()
    assert "Volver a TaskPlanner" in html
    assert f'href="{reverse("inicio")}"' in html
