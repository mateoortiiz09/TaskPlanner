from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.utils.http import content_disposition_header
from django.views.decorators.http import require_GET, require_POST

from adjuntos import servicios
from adjuntos.forms import AdjuntoForm
from adjuntos.models import Adjunto
from autorizacion.reglas import puede_adjuntar, puede_ver_contenido, puede_ver_tarea
from tareas.models import Tarea


def _tarea_activa(pk):
    return get_object_or_404(Tarea, pk=pk, eliminada_en__isnull=True)


@require_POST
def subir(request, pk):
    tarea = _tarea_activa(pk)
    if not puede_ver_tarea(request.user, tarea):
        raise Http404
    if not puede_adjuntar(request.user, tarea):
        raise PermissionDenied
    formulario = AdjuntoForm(request.POST, request.FILES)
    if not formulario.is_valid():
        messages.error(request, "Seleccione un archivo para adjuntar.")
    else:
        try:
            servicios.subir_adjunto(
                tarea=tarea,
                archivo=formulario.cleaned_data["archivo"],
                usuario=request.user,
            )
        except ValidationError as error:
            messages.error(request, " ".join(error.messages))
        else:
            messages.success(request, "Archivo adjuntado.")
    return redirect("tareas:detalle", pk=tarea.pk)


@require_GET
def descargar(request, pk, adjunto_id):
    tarea = _tarea_activa(pk)
    if not puede_ver_contenido(request.user, tarea):
        raise Http404
    adjunto = get_object_or_404(Adjunto, pk=adjunto_id, tarea=tarea)
    datos = servicios.leer_contenido(adjunto)
    respuesta = HttpResponse(datos, content_type=adjunto.tipo_contenido)
    respuesta["Content-Disposition"] = content_disposition_header(
        True, adjunto.nombre_original
    )
    respuesta["Content-Length"] = str(len(datos))
    respuesta["X-Content-Type-Options"] = "nosniff"
    respuesta["Cache-Control"] = "no-store"
    respuesta["Content-Security-Policy"] = "sandbox"
    return respuesta
