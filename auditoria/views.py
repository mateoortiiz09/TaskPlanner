from datetime import date

from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.shortcuts import render

from auditoria.models import EventoAuditoria
from auditoria.servicios import TAREAS, TECNICA, acciones_de, etiqueta


def _fecha(valor):
    try:
        return date.fromisoformat(valor) if valor else None
    except ValueError:
        return None


def lista(request):
    categorias = []
    if request.user.has_perm("auditoria.ver_auditoria_tareas"):
        categorias.append(TAREAS)
    if request.user.has_perm("auditoria.ver_auditoria_tecnica"):
        categorias.append(TECNICA)
    if not categorias:
        raise PermissionDenied
    permitidas = [
        accion for categoria in categorias for accion in acciones_de(categoria)
    ]
    eventos = (
        EventoAuditoria.objects.filter(accion__in=permitidas)
        .select_related("actor")
        .order_by("-fecha_hora", "-pk")
    )
    accion = request.GET.get("accion", "")
    if accion in permitidas:
        eventos = eventos.filter(accion=accion)
    desde = _fecha(request.GET.get("desde"))
    hasta = _fecha(request.GET.get("hasta"))
    if desde:
        eventos = eventos.filter(fecha_hora__date__gte=desde)
    if hasta:
        eventos = eventos.filter(fecha_hora__date__lte=hasta)
    pagina = Paginator(eventos, 50).get_page(request.GET.get("page"))
    contexto = {
        "pagina": pagina,
        "opciones": [(valor, etiqueta(valor)) for valor in permitidas],
        "accion": accion,
        "desde": desde.isoformat() if desde else "",
        "hasta": hasta.isoformat() if hasta else "",
    }
    return render(request, "auditoria/lista.html", contexto)
