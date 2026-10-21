from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path
from django.views.generic import TemplateView

from cuentas.views import CambiarContrasenaView

urlpatterns = [
    path("admin/", admin.site.urls),
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
    path("", TemplateView.as_view(template_name="inicio.html"), name="inicio"),
]
