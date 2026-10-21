import pytest
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.urls import reverse

RECURSOS_LOCALES = [
    "vendor/bootstrap/bootstrap.min.css",
    "vendor/bootstrap/bootstrap.bundle.min.js",
    "vendor/htmx/htmx.min.js",
]


def test_recursos_estaticos_locales_existen():
    for ruta in RECURSOS_LOCALES:
        assert finders.find(ruta), f"No se encontró {ruta}"


@pytest.mark.django_db
def test_inicio_usa_recursos_locales_sin_cdn(client):
    usuario = get_user_model().objects.create_user(
        email="ana@ejemplo.local", password="Clave-de-prueba-123"
    )
    client.force_login(usuario)
    respuesta = client.get(reverse("inicio"))

    assert respuesta.status_code == 200
    contenido = respuesta.content.decode()
    assert "/static/vendor/bootstrap/bootstrap.min.css" in contenido
    assert "/static/vendor/htmx/htmx.min.js" in contenido
    assert "cdn." not in contenido
