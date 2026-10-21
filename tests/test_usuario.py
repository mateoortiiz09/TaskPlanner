import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, connection

pytestmark = pytest.mark.django_db


def test_se_usa_el_modelo_de_usuario_propio():
    assert get_user_model()._meta.label == "cuentas.Usuario"


def test_el_correo_se_guarda_en_minusculas():
    usuario = get_user_model().objects.create_user(
        email="Ana.Perez@Ejemplo.LOCAL", password="Clave-de-prueba-123"
    )
    assert usuario.email == "ana.perez@ejemplo.local"
    assert usuario.check_password("Clave-de-prueba-123")
    assert not usuario.is_superuser


def test_no_se_repite_el_correo_aunque_cambien_mayusculas():
    usuarios = get_user_model().objects
    usuarios.create_user(email="ana@ejemplo.local", password="Clave-de-prueba-123")
    with pytest.raises(IntegrityError):
        usuarios.create_user(email="ANA@ejemplo.local", password="Clave-de-prueba-123")


def test_no_existe_la_tabla_auth_user():
    assert "auth_user" not in connection.introspection.table_names()
