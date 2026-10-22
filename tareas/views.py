from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from tareas import servicios
from tareas.consultas import tareas_visibles
from tareas.forms import TareaForm
from tareas.models import EstadoAvance
from tareas.panel import (
    FiltroPanelForm,
    aplicar_filtros,
    contar_por_situacion,
    ordenar_por_urgencia,
)
from tareas.vencimientos import hoy_local

ESTADOS_EDITABLES = [
    (estado.value, estado.label)
    for estado in (EstadoAvance.PENDIENTE, EstadoAvance.EN_PROCESO)
]
TAREAS_POR_PAGINA = 25


def lista(request):
    hoy = hoy_local()
    visibles = tareas_visibles(request.user)
    form = FiltroPanelForm(request.GET or None, usuario=request.user)
    filtros = form.cleaned_data if form.is_valid() else {}
    tareas = ordenar_por_urgencia(
        aplicar_filtros(visibles, filtros, hoy), hoy
    ).prefetch_related("asignaciones__usuario", "asignaciones__area")
    pagina = Paginator(tareas, TAREAS_POR_PAGINA).get_page(request.GET.get("page"))
    contexto = {
        "form": form,
        "pagina": pagina,
        "contadores": contar_por_situacion(visibles, hoy),
    }
    if request.headers.get("HX-Request") == "true":
        return render(request, "tareas/_tabla.html", contexto)
    return render(request, "tareas/lista.html", contexto)


@permission_required("tareas.add_tarea", raise_exception=True)
def crear(request):
    form = TareaForm(request.POST or None, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        tarea = servicios.crear_tarea(
            request.user, form.datos_tarea(), form.cleaned_data["responsables"]
        )
        messages.success(request, "Tarea creada.")
        return redirect("tareas:detalle", pk=tarea.pk)
    return render(
        request, "tareas/formulario.html", {"form": form, "titulo": "Nueva tarea"}
    )


def detalle(request, pk):
    tarea = get_object_or_404(
        tareas_visibles(request.user)
        .select_related("creada_por", "completada_por")
        .prefetch_related("asignaciones__usuario", "asignaciones__area"),
        pk=pk,
    )
    contexto = {
        "tarea": tarea,
        "puede_editar": servicios.puede_editar(request.user, tarea),
        "estados": ESTADOS_EDITABLES,
    }
    return render(request, "tareas/detalle.html", contexto)


@permission_required("tareas.change_tarea", raise_exception=True)
def editar(request, pk):
    tarea = get_object_or_404(
        tareas_visibles(request.user).prefetch_related("asignaciones"), pk=pk
    )
    if not servicios.puede_editar(request.user, tarea):
        raise PermissionDenied
    form = TareaForm(request.POST or None, instance=tarea, usuario=request.user)
    if request.method == "POST" and form.is_valid():
        try:
            servicios.actualizar_tarea(
                request.user,
                tarea.pk,
                form.datos_tarea(),
                form.cleaned_data["responsables"],
                form.cleaned_data["version"],
            )
        except servicios.ConflictoDeVersion:
            form.add_error(
                None,
                "Otra persona modificó esta tarea mientras la editabas. "
                "Recarga la página para ver los cambios.",
            )
        else:
            messages.success(request, "Tarea actualizada.")
            return redirect("tareas:detalle", pk=tarea.pk)
    return render(
        request, "tareas/formulario.html", {"form": form, "titulo": "Editar tarea"}
    )


@require_POST
@permission_required("tareas.cambiar_estado", raise_exception=True)
def cambiar_estado(request, pk):
    tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
    try:
        servicios.cambiar_estado(request.user, tarea.pk, request.POST.get("estado"))
    except servicios.OperacionNoPermitida as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Estado actualizado.")
    return redirect("tareas:detalle", pk=tarea.pk)


def _confirmar(request, tarea, titulo, mensaje, boton, clase_boton):
    contexto = {
        "tarea": tarea,
        "titulo": titulo,
        "mensaje": mensaje,
        "boton": boton,
        "clase_boton": clase_boton,
    }
    return render(request, "tareas/confirmar.html", contexto)


@permission_required("tareas.completar_tareas", raise_exception=True)
def completar(request, pk):
    tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
    if request.method == "POST":
        try:
            servicios.completar_tarea(request.user, tarea.pk)
        except servicios.OperacionNoPermitida as error:
            messages.error(request, str(error))
        else:
            messages.success(request, "Tarea completada.")
        return redirect("tareas:detalle", pk=tarea.pk)
    return _confirmar(
        request,
        tarea,
        "Completar tarea",
        "Se registrará la fecha de hoy como fecha de finalización y el "
        "cumplimiento frente a la fecha límite. Esta acción no se puede deshacer.",
        "Completar",
        "btn-success",
    )


@permission_required("tareas.eliminar_recuperar_tareas", raise_exception=True)
def eliminar(request, pk):
    tarea = get_object_or_404(tareas_visibles(request.user), pk=pk)
    if request.method == "POST":
        try:
            servicios.eliminar_tarea(request.user, tarea.pk)
        except servicios.OperacionNoPermitida as error:
            messages.error(request, str(error))
            return redirect("tareas:detalle", pk=tarea.pk)
        messages.success(request, "Tarea enviada a la papelera.")
        return redirect("tareas:lista")
    return _confirmar(
        request,
        tarea,
        "Eliminar tarea",
        "La tarea pasará a la papelera y dejará de generar recordatorios. "
        "Podrás recuperarla desde la papelera.",
        "Eliminar",
        "btn-danger",
    )


@permission_required("tareas.eliminar_recuperar_tareas", raise_exception=True)
def papelera(request):
    tareas = tareas_visibles(request.user, eliminadas=True).select_related(
        "eliminada_por"
    )
    return render(request, "tareas/papelera.html", {"tareas": tareas})


@require_POST
@permission_required("tareas.eliminar_recuperar_tareas", raise_exception=True)
def recuperar(request, pk):
    tarea = get_object_or_404(tareas_visibles(request.user, eliminadas=True), pk=pk)
    try:
        servicios.recuperar_tarea(request.user, tarea.pk)
    except servicios.OperacionNoPermitida as error:
        messages.error(request, str(error))
        return redirect("tareas:papelera")
    messages.success(request, "Tarea recuperada.")
    return redirect("tareas:detalle", pk=tarea.pk)
