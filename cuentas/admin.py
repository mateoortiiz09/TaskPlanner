from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import (
    AdminPasswordChangeForm,
    BaseUserCreationForm,
    UserChangeForm,
)
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied

from cuentas.models import Area, Usuario
from cuentas.roles import ADMINISTRADOR
from cuentas.servicios import (
    sincronizar_acceso_panel,
    validar_que_no_es_el_ultimo_administrador,
)

admin.site.site_header = "TaskPlanner · Administración"
admin.site.site_title = "TaskPlanner"
admin.site.index_title = "Gestión de usuarios y áreas"
admin.site.unregister(Group)


class UsuarioCreacionForm(BaseUserCreationForm):
    class Meta:
        model = Usuario
        fields = ("email", "first_name", "last_name", "area")


class UsuarioCambioForm(UserChangeForm):
    class Meta:
        model = Usuario
        fields = "__all__"

    def clean(self):
        datos = super().clean()
        if self.instance.pk:
            if "is_active" in self.fields:
                seguira_activo = bool(datos.get("is_active"))
            else:
                seguira_activo = self.instance.is_active
            if "groups" in self.fields:
                grupos = datos.get("groups")
                seguira_siendo_admin = (
                    grupos is not None and grupos.filter(name=ADMINISTRADOR).exists()
                )
            else:
                seguira_siendo_admin = True
            validar_que_no_es_el_ultimo_administrador(
                self.instance, seguira_activo, seguira_siendo_admin
            )
        return datos


class RestablecerContrasenaForm(AdminPasswordChangeForm):
    def save(self, commit=True):
        self.user.debe_cambiar_contrasena = True
        return super().save(commit=commit)


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioCambioForm
    add_form = UsuarioCreacionForm
    change_password_form = RestablecerContrasenaForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "area", "is_active")
    list_filter = ("is_active", "groups", "area")
    search_fields = ("email", "first_name", "last_name")
    filter_horizontal = ("groups",)
    readonly_fields = ("last_login", "date_joined")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("first_name", "last_name", "area")}),
        ("Acceso", {"fields": ("is_active", "groups", "debe_cambiar_contrasena")}),
        ("Fechas", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "area",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if obj is not None and obj.pk == request.user.pk:
            campos += ["is_active", "groups"]
        return campos

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        if not change:
            obj.debe_cambiar_contrasena = True
            obj.is_superuser = False
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        sincronizar_acceso_panel(form.instance)

    def user_change_password(self, request, id, form_url=""):
        if not request.user.has_perm("cuentas.restablecer_contrasenas"):
            raise PermissionDenied
        return super().user_change_password(request, id, form_url)


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "activa")
    list_filter = ("activa",)
    search_fields = ("nombre",)

    def has_delete_permission(self, request, obj=None):
        return False
