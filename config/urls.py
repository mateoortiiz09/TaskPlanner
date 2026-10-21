from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from cuentas.views import CambiarContrasenaView
from tareas import views as tareas_views

urlpatterns = [
    path("gestion-interna/", admin.site.urls),
    path(
        "ingresar/",
        auth_views.LoginView.as_view(
            template_name="cuentas/ingresar.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("salir/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "cuenta/cambiar-contrasena/",
        CambiarContrasenaView.as_view(),
        name="cambiar_contrasena",
    ),
    path("tareas/", include("tareas.urls")),
    path("", tareas_views.lista, name="inicio"),
]
