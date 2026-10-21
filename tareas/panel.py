from django import forms
from django.db.models import Case, Count, IntegerField, Q, Value, When

from cuentas.models import Area
from tareas.forms import lideres_disponibles
from tareas.models import EstadoAvance, Prioridad
from tareas.vencimientos import SituacionTemporal, filtro_situacion

SELECT = {"class": "form-select form-select-sm"}


class FiltroPanelForm(forms.Form):
    area = forms.ModelChoiceField(
        queryset=Area.objects.order_by("nombre"),
        required=False,
        empty_label="Todas",
        label="Área",
        widget=forms.Select(attrs=SELECT),
    )
    responsable = forms.ModelChoiceField(
        queryset=lideres_disponibles(),
        required=False,
        empty_label="Todos",
        label="Responsable",
        widget=forms.Select(attrs=SELECT),
    )
    prioridad = forms.ChoiceField(
        choices=[("", "Todas"), *Prioridad.choices],
        required=False,
        label="Prioridad",
        widget=forms.Select(attrs=SELECT),
    )
    estado = forms.ChoiceField(
        choices=[("", "Todos"), *EstadoAvance.choices],
        required=False,
        label="Estado",
        widget=forms.Select(attrs=SELECT),
    )
    situacion = forms.ChoiceField(
        choices=[("", "Todas"), *SituacionTemporal.choices],
        required=False,
        label="Situación",
        widget=forms.Select(attrs=SELECT),
    )
    completadas = forms.BooleanField(
        required=False,
        label="Mostrar completadas",
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )
    vence = forms.ChoiceField(
        choices=[("", ""), ("hoy", "Hoy")], required=False, widget=forms.HiddenInput
    )

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        if not usuario.has_perm("tareas.ver_todas_las_tareas"):
            del self.fields["area"]
            del self.fields["responsable"]


def aplicar_filtros(tareas, filtros, hoy):
    if filtros.get("area"):
        tareas = tareas.filter(asignaciones__area=filtros["area"])
    if filtros.get("responsable"):
        tareas = tareas.filter(asignaciones__usuario=filtros["responsable"])
    if filtros.get("prioridad"):
        tareas = tareas.filter(prioridad=filtros["prioridad"])
    estado = filtros.get("estado")
    if estado:
        tareas = tareas.filter(estado=estado)
    situacion = filtros.get("situacion")
    if situacion:
        tareas = tareas.filter(filtro_situacion(situacion, hoy))
    if filtros.get("vence") == "hoy":
        tareas = tareas.filter(fecha_limite=hoy).exclude(estado=EstadoAvance.COMPLETADA)
    ver_completadas = (
        filtros.get("completadas")
        or estado == EstadoAvance.COMPLETADA
        or situacion == SituacionTemporal.COMPLETADA
    )
    if not ver_completadas:
        tareas = tareas.exclude(estado=EstadoAvance.COMPLETADA)
    return tareas.distinct()


def ordenar_por_urgencia(tareas, hoy):
    return tareas.annotate(
        orden_situacion=Case(
            When(filtro_situacion(SituacionTemporal.ATRASADA, hoy), then=Value(0)),
            When(filtro_situacion(SituacionTemporal.EN_RIESGO, hoy), then=Value(1)),
            When(filtro_situacion(SituacionTemporal.EN_TIEMPO, hoy), then=Value(2)),
            default=Value(3),
            output_field=IntegerField(),
        )
    ).order_by("orden_situacion", "fecha_limite", "id")


def contar_por_situacion(tareas, hoy):
    return tareas.aggregate(
        atrasadas=Count(
            "pk",
            distinct=True,
            filter=filtro_situacion(SituacionTemporal.ATRASADA, hoy),
        ),
        vencen_hoy=Count(
            "pk",
            distinct=True,
            filter=Q(fecha_limite=hoy) & ~Q(estado=EstadoAvance.COMPLETADA),
        ),
        en_riesgo=Count(
            "pk",
            distinct=True,
            filter=filtro_situacion(SituacionTemporal.EN_RIESGO, hoy),
        ),
        pendientes=Count("pk", distinct=True, filter=Q(estado=EstadoAvance.PENDIENTE)),
    )
