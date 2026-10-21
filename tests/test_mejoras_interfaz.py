import datetime

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.urls import reverse
from django.utils import timezone

from cuentas.models import Area
from cuentas.roles import LIDER_AREA, SUBGERENTE
from tareas.models import ResponsableTarea, Tarea

pytestmark = pytest.mark.django_db

CLAVE = "Clave-de-prueba-123"


def crear_usuario(email, grupo, area=None):
    usuario = get_user_model().objects.create_user(
        email=email, password=CLAVE, area=area
    )
    usuario.groups.add(Group.objects.get(name=grupo))
    return get_user_model().objects.get(pk=usuario.pk)


def test_login_tiene_boton_para_mostrar_la_contrasena(client):
    contenido = client.get(reverse("login")).content.decode()
    assert "data-alternar-contrasena" in contenido
    assert "/static/js/app.js" in contenido


def test_filas_de_la_lista_llevan_al_detalle(client):
    subgerente = crear_usuario("subgerente@ejemplo.local", SUBGERENTE)
    lider = crear_usuario(
        "lider@ejemplo.local", LIDER_AREA, Area.objects.create(nombre="Compras")
    )
    tarea = Tarea.objects.create(
        nombre="Tarea",
        descripcion="Descripción",
        fecha_limite=timezone.localdate() + datetime.timedelta(days=3),
        creada_por=subgerente,
    )
    ResponsableTarea.objects.create(tarea=tarea, usuario=lider)
    client.force_login(subgerente)
    contenido = client.get(reverse("tareas:lista")).content.decode()
    assert f'data-href="{reverse("tareas:detalle", args=[tarea.pk])}"' in contenido


def test_el_lider_ve_tareas_asignadas_en_el_menu(client):
    lider = crear_usuario(
        "lider@ejemplo.local", LIDER_AREA, Area.objects.create(nombre="Compras")
    )
    client.force_login(lider)
    assert "Tareas asignadas" in client.get(reverse("tareas:lista")).content.decode()


def test_el_formulario_avisa_si_no_hay_lideres(client):
    client.force_login(crear_usuario("subgerente@ejemplo.local", SUBGERENTE))
    contenido = client.get(reverse("tareas:crear")).content.decode()
    assert "No hay líderes disponibles" in contenido
