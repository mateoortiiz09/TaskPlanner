from django import forms
from django.contrib.auth import get_user_model

from cuentas.roles import LIDER_AREA
from tareas.models import Tarea

CAMPOS_TAREA = ["nombre", "descripcion", "fecha_limite", "prioridad", "restringida"]


def lideres_disponibles():
    return (
        get_user_model()
        .objects.filter(
            is_active=True,
            groups__name=LIDER_AREA,
            area__isnull=False,
            area__activa=True,
        )
        .select_related("area")
        .order_by("area__nombre", "first_name", "email")
    )


class ResponsablesField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, usuario):
        nombre = usuario.get_full_name() or usuario.email
        return f"{usuario.area} — {nombre}"


class TareaForm(forms.ModelForm):
    responsables = ResponsablesField(
        queryset=get_user_model().objects.none(),
        label="Responsables",
        widget=forms.SelectMultiple(attrs={"class": "form-select", "size": 8}),
        help_text="Mantén presionada la tecla Ctrl para elegir varios líderes.",
    )
    version = forms.IntegerField(widget=forms.HiddenInput, required=False)

    class Meta:
        model = Tarea
        fields = CAMPOS_TAREA
        labels = {
            "nombre": "Nombre",
            "descripcion": "Descripción",
            "fecha_limite": "Fecha límite",
            "prioridad": "Prioridad",
            "restringida": "Información restringida",
        }
        help_texts = {
            "restringida": (
                "Márcala si la tarea contiene datos de clientes, nómina, "
                "información financiera, jurídica u otra información confidencial. "
                "El Administrador no verá su contenido."
            ),
        }
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control"}),
            "descripcion": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "fecha_limite": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}, format="%Y-%m-%d"
            ),
            "prioridad": forms.Select(attrs={"class": "form-select"}),
            "restringida": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args, usuario, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsables"].queryset = lideres_disponibles()
        if self.instance.pk:
            self.fields["responsables"].initial = list(
                self.instance.responsables.values_list("pk", flat=True)
            )
            self.fields["version"].initial = self.instance.version
        if not usuario.has_perm("tareas.reclasificar_sensibilidad"):
            del self.fields["restringida"]
        if not self.fields["responsables"].queryset.exists():
            self.fields["responsables"].help_text = (
                "No hay líderes disponibles. En Administración, el usuario debe "
                "estar activo, tener un área activa y el grupo «Líder de área»."
            )

    def datos_tarea(self):
        return {
            campo: self.cleaned_data[campo]
            for campo in CAMPOS_TAREA
            if campo in self.cleaned_data
        }
