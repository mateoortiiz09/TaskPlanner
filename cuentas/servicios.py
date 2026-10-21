from django.core.exceptions import ValidationError

from cuentas.models import Usuario
from cuentas.roles import ADMINISTRADOR

MENSAJE_ULTIMO_ADMIN = (
    "No se puede desactivar ni quitar el rol al último administrador activo."
)


def es_administrador(usuario):
    return usuario.groups.filter(name=ADMINISTRADOR).exists()


def validar_que_no_es_el_ultimo_administrador(
    usuario, seguira_activo, seguira_siendo_admin
):
    """Debe llamarse dentro de una transacción: bloquea a los demás administradores."""
    if not usuario.pk or not usuario.is_active or not es_administrador(usuario):
        return
    if seguira_activo and seguira_siendo_admin:
        return
    otros = (
        Usuario.objects.select_for_update()
        .filter(groups__name=ADMINISTRADOR, is_active=True)
        .exclude(pk=usuario.pk)
    )
    if not otros.exists():
        raise ValidationError(MENSAJE_ULTIMO_ADMIN)


def sincronizar_acceso_panel(usuario):
    """Solo los administradores activos entran al panel; nadie es superusuario."""
    debe_ser_staff = usuario.is_active and es_administrador(usuario)
    if usuario.is_staff != debe_ser_staff or usuario.is_superuser:
        usuario.is_staff = debe_ser_staff
        usuario.is_superuser = False
        usuario.save(update_fields=["is_staff", "is_superuser"])
