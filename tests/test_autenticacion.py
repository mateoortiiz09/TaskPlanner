import time

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.urls import reverse

from cuentas.middleware import CLAVE_INICIO_SESION

pytestmark = pytest.mark.django_db

CORREO = "lider@ejemplo.local"
CLAVE = "Clave-de-prueba-123"
CLAVE_INCORRECTA = "Clave-incorrecta-999"


@pytest.fixture
def usuario():
    return get_user_model().objects.create_user(email=CORREO, password=CLAVE)


def ingresar(client, correo, clave):
    return client.post(reverse("login"), {"username": correo, "password": clave})


def test_pagina_sin_sesion_redirige_al_login(client):
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("login"))


def test_pagina_de_ingreso_es_publica(client):
    assert client.get(reverse("login")).status_code == 200


def test_ingreso_con_correo_y_clave_correctos(client, usuario):
    respuesta = ingresar(client, CORREO, CLAVE)
    assert respuesta.status_code == 302
    assert respuesta.url == reverse("inicio")
    assert client.session["_auth_user_id"] == str(usuario.pk)


def test_ingreso_no_distingue_mayusculas_en_el_correo(client, usuario):
    ingresar(client, CORREO.upper(), CLAVE)
    assert client.session["_auth_user_id"] == str(usuario.pk)


def test_ingreso_con_clave_incorrecta_es_rechazado(client, usuario):
    respuesta = ingresar(client, CORREO, CLAVE_INCORRECTA)
    assert respuesta.status_code == 200
    assert "_auth_user_id" not in client.session


def test_cerrar_sesion(client, usuario):
    client.force_login(usuario)
    respuesta = client.post(reverse("logout"))
    assert respuesta.status_code == 302
    assert "_auth_user_id" not in client.session


def test_contrasena_guardada_con_argon2(usuario):
    assert usuario.password.startswith("argon2")


def test_contrasena_corta_es_rechazada():
    with pytest.raises(ValidationError):
        validate_password("Corta-123")
    validate_password("Una-clave-larga-y-segura-2026")


def test_bloqueo_tras_cinco_intentos_fallidos(client, usuario):
    for _ in range(5):
        ingresar(client, CORREO, CLAVE_INCORRECTA)
    ingresar(client, CORREO, CLAVE)
    assert "_auth_user_id" not in client.session


def test_bloqueo_no_se_evita_cambiando_mayusculas(client, usuario):
    for _ in range(5):
        ingresar(client, CORREO.upper(), CLAVE_INCORRECTA)
    ingresar(client, CORREO, CLAVE)
    assert "_auth_user_id" not in client.session


def test_configuracion_de_sesion():
    assert settings.SESSION_COOKIE_AGE == 15 * 60
    assert settings.SESSION_SAVE_EVERY_REQUEST is True
    assert settings.SESSION_COOKIE_HTTPONLY is True


def test_sesion_expira_al_superar_la_duracion_maxima(client, usuario):
    client.force_login(usuario)
    sesion = client.session
    sesion[CLAVE_INICIO_SESION] = (
        int(time.time()) - settings.SESION_DURACION_MAXIMA_SEGUNDOS - 1
    )
    sesion.save()
    respuesta = client.get(reverse("inicio"))
    assert respuesta.status_code == 302
    assert respuesta.url.startswith(reverse("login"))
    assert "_auth_user_id" not in client.session
