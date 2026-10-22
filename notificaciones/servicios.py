"""Bandeja de salida de correos.

Los correos se encolan en la misma transacción que el cambio que los origina y
se envían después, con reintentos. El texto se compone al enviar: si la tarea
es restringida en ese momento, el correo es genérico y no revela su contenido.
"""

from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import IntegrityError, transaction
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone

from notificaciones.models import EstadoNotificacion, Notificacion, TipoNotificacion
from tareas.models import EstadoAvance

PLANTILLAS = {
    TipoNotificacion.ASIGNACION: ("asignacion", "Nueva tarea asignada"),
    TipoNotificacion.DIA_ANTERIOR: ("recordatorio_previo", "Una tarea vence mañana"),
    TipoNotificacion.VENCIMIENTO: ("vence_hoy", "Una tarea vence hoy"),
    TipoNotificacion.ATRASO: ("atraso", "Una tarea está atrasada"),
    TipoNotificacion.ATRASO_SEMANAL: (
        "atraso_semanal",
        "Recordatorio: tarea atrasada",
    ),
    TipoNotificacion.CAMBIO_ROL: (
        "cambio_rol",
        "Cambio de rol privilegiado en TaskPlanner",
    ),
}
RECORDATORIOS = {
    TipoNotificacion.DIA_ANTERIOR,
    TipoNotificacion.VENCIMIENTO,
    TipoNotificacion.ATRASO,
    TipoNotificacion.ATRASO_SEMANAL,
}
ASUNTO_RESTRINGIDA = "Actualización en una tarea restringida"


def encolar(*, tipo, destinatario, clave_unica, tarea=None, contexto=None):
    if not destinatario.is_active or not destinatario.email:
        return None
    try:
        with transaction.atomic():
            return Notificacion.objects.create(
                tipo=tipo,
                destinatario=destinatario,
                tarea=tarea,
                clave_unica=clave_unica,
                contexto=contexto or {},
                estado=EstadoNotificacion.PENDIENTE,
                intentos=0,
                proximo_intento=timezone.now(),
            )
    except IntegrityError:
        return None


def _url(nombre, *args):
    return settings.TASKPLANNER_URL_BASE.rstrip("/") + reverse(nombre, args=args)


def _componer(notificacion):
    plantilla, asunto = PLANTILLAS[notificacion.tipo]
    tarea = notificacion.tarea
    contexto = {
        **notificacion.contexto,
        "destinatario": notificacion.destinatario,
        "url_inicio": _url("inicio"),
    }
    if tarea is not None:
        contexto["url_tarea"] = _url("tareas:detalle", tarea.pk)
        if tarea.restringida:
            plantilla, asunto = "restringida", ASUNTO_RESTRINGIDA
        else:
            contexto["tarea"] = tarea
            asunto = f"{asunto}: {tarea.nombre}"
    asunto = " ".join(asunto.split())[:200]
    texto = render_to_string(f"correos/{plantilla}.txt", contexto)
    html = render_to_string(f"correos/{plantilla}.html", contexto)
    return asunto, texto, html


def _debe_cancelarse(notificacion):
    if not notificacion.destinatario.is_active:
        return True
    tarea = notificacion.tarea
    if tarea is None:
        return False
    if tarea.eliminada_en is not None:
        return True
    return (
        notificacion.tipo in RECORDATORIOS and tarea.estado == EstadoAvance.COMPLETADA
    )


def enviar_pendientes(limite=50):
    enviadas = 0
    with transaction.atomic():
        lote = list(
            Notificacion.objects.select_for_update(skip_locked=True, of=("self",))
            .select_related("tarea", "destinatario")
            .filter(
                estado=EstadoNotificacion.PENDIENTE,
                proximo_intento__lte=timezone.now(),
            )
            .order_by("proximo_intento", "pk")[:limite]
        )
        for notificacion in lote:
            if _debe_cancelarse(notificacion):
                notificacion.estado = EstadoNotificacion.CANCELADA
                notificacion.save(update_fields=["estado"])
                continue
            try:
                asunto, texto, html = _componer(notificacion)
                correo = EmailMultiAlternatives(
                    asunto,
                    texto,
                    settings.DEFAULT_FROM_EMAIL,
                    [notificacion.destinatario.email],
                )
                correo.attach_alternative(html, "text/html")
                correo.send()
            except Exception as error:  # noqa: BLE001
                notificacion.intentos += 1
                notificacion.ultimo_error = str(error)[:1000]
                if notificacion.intentos >= settings.NOTIFICACIONES_MAX_INTENTOS:
                    notificacion.estado = EstadoNotificacion.FALLIDA
                else:
                    notificacion.proximo_intento = timezone.now() + timedelta(
                        minutes=2**notificacion.intentos
                    )
                notificacion.save(
                    update_fields=[
                        "intentos",
                        "ultimo_error",
                        "estado",
                        "proximo_intento",
                    ]
                )
            else:
                notificacion.intentos += 1
                notificacion.ultimo_error = ""
                notificacion.estado = EstadoNotificacion.ENVIADA
                notificacion.save(update_fields=["intentos", "ultimo_error", "estado"])
                enviadas += 1
    return enviadas


def notificar_asignacion(tarea, usuario):
    return encolar(
        tipo=TipoNotificacion.ASIGNACION,
        destinatario=usuario,
        tarea=tarea,
        clave_unica=f"asignacion:{tarea.pk}:{usuario.pk}",
    )
