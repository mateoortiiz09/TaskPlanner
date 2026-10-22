import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from cuentas.models import Usuario

pytestmark = pytest.mark.django_db


def test_crear_datos_demo_es_idempotente_y_permite_ingresar(settings):
    settings.DEBUG = True
    call_command("crear_datos_demo")
    call_command("crear_datos_demo")
    assert Usuario.objects.filter(email__endswith="@ejemplo.local").count() == 4
    lider = Usuario.objects.get(email="lider.compras@ejemplo.local")
    assert list(lider.groups.values_list("name", flat=True)) == ["Líder de área"]
    assert str(lider.area) == "Compras"
    assert not lider.debe_cambiar_contrasena
    assert lider.check_password("Demo.Local.2026#")


def test_crear_datos_demo_no_funciona_en_produccion(settings):
    settings.DEBUG = False
    with pytest.raises(CommandError):
        call_command("crear_datos_demo")
    assert not Usuario.objects.filter(email__endswith="@ejemplo.local").exists()
