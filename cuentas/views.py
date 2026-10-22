from django.contrib import messages
from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

from auditoria.servicios import registrar_evento


class CambiarContrasenaView(PasswordChangeView):
    template_name = "cuentas/cambiar_contrasena.html"
    success_url = reverse_lazy("inicio")

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        for campo in form.fields.values():
            campo.widget.attrs["class"] = "form-control"
        return form

    def form_valid(self, form):
        respuesta = super().form_valid(form)
        usuario = form.user
        if usuario.debe_cambiar_contrasena:
            usuario.debe_cambiar_contrasena = False
            usuario.save(update_fields=["debe_cambiar_contrasena"])
        registrar_evento(
            "usuario.contrasena_cambiada", actor=usuario, usuario_id=usuario.pk
        )
        messages.success(self.request, "Tu contraseña se actualizó correctamente.")
        return respuesta
