from axes.signals import user_locked_out
from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.db.models.signals import m2m_changed, post_save
from django.dispatch import receiver

from auditoria.servicios import registrar_evento
from cuentas.models import Usuario


@receiver(user_logged_in)
def al_iniciar_sesion(sender, request, user, **kwargs):
    registrar_evento("sesion.iniciada", actor=user)


@receiver(user_logged_out)
def al_cerrar_sesion(sender, request, user, **kwargs):
    if user is not None and user.is_authenticated:
        registrar_evento("sesion.cerrada", actor=user)


@receiver(user_login_failed)
def al_fallar_inicio(sender, credentials, request=None, **kwargs):
    correo = credentials.get("username") or credentials.get("email") or ""
    registrar_evento("sesion.fallida", correo=str(correo).strip().lower()[:254])


@receiver(user_locked_out)
def al_bloquear_cuenta(sender, request, username, ip_address, **kwargs):
    registrar_evento(
        "sesion.bloqueada", correo=str(username or "").strip().lower()[:254]
    )


@receiver(post_save, sender=Usuario)
def al_crear_usuario(sender, instance, created, **kwargs):
    if created:
        registrar_evento(
            "usuario.creado", usuario_id=instance.pk, correo=instance.email
        )


@receiver(m2m_changed, sender=Usuario.groups.through)
def al_cambiar_grupos(sender, instance, action, reverse, **kwargs):
    if reverse or action not in {"post_add", "post_remove", "post_clear"}:
        return
    registrar_evento(
        "usuario.rol_cambiado",
        usuario_id=instance.pk,
        correo=instance.email,
        operacion=action.removeprefix("post_"),
        grupos=sorted(instance.groups.values_list("name", flat=True)),
    )
