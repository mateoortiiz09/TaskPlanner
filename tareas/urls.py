from django.urls import path

from adjuntos import views as adjuntos_views
from tareas import views

app_name = "tareas"

urlpatterns = [
    path("", views.lista, name="lista"),
    path("nueva/", views.crear, name="crear"),
    path("papelera/", views.papelera, name="papelera"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/editar/", views.editar, name="editar"),
    path("<int:pk>/estado/", views.cambiar_estado, name="cambiar_estado"),
    path("<int:pk>/completar/", views.completar, name="completar"),
    path("<int:pk>/eliminar/", views.eliminar, name="eliminar"),
    path("<int:pk>/recuperar/", views.recuperar, name="recuperar"),
    path("<int:pk>/adjuntos/subir/", adjuntos_views.subir, name="adjunto_subir"),
    path(
        "<int:pk>/adjuntos/<int:adjunto_id>/",
        adjuntos_views.descargar,
        name="adjunto_descargar",
    ),
]
