from django.contrib.auth.models import Group
from django.db.models.signals import m2m_changed
from django.dispatch import receiver
from django.utils import timezone

from auditoria.contexto import peticion_actual
from cuentas.models import Usuario
from notificaciones.models import TipoNotificacion
from notificaciones.servicios import encolar

GRUPOS_PRIVILEGIADOS = {"Administrador", "Subgerente"}


@receiver(m2m_changed, sender=Usuario.groups.through)
def avisar_cambio_de_rol(sender, instance, action, reverse, pk_set, **kwargs):
    if reverse or action not in {"post_add", "post_remove"} or not pk_set:
        return
    grupos = sorted(
        Group.objects.filter(pk__in=pk_set, name__in=GRUPOS_PRIVILEGIADOS).values_list(
            "name", flat=True
        )
    )
    if not grupos:
        return
    request = peticion_actual()
    actor = getattr(request, "user", None)
    por = actor.email if actor is not None and actor.is_authenticated else "Sistema"
    marca = timezone.now().strftime("%Y%m%d%H%M%S%f")
    contexto = {
        "usuario": instance.email,
        "operacion": "agregado a" if action == "post_add" else "retirado de",
        "grupos": ", ".join(grupos),
        "por": por,
    }
    administradores = Usuario.objects.filter(
        groups__name="Administrador", is_active=True
    ).exclude(pk=instance.pk)
    for administrador in administradores.distinct():
        encolar(
            tipo=TipoNotificacion.CAMBIO_ROL,
            destinatario=administrador,
            clave_unica=f"rol:{instance.pk}:{marca}:{administrador.pk}",
            contexto=contexto,
        )
