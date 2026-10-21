from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class TipoNotificacion(models.TextChoices):
    ASIGNACION = "ASIGNACION", "Asignación"
    DIA_ANTERIOR = "DIA_ANTERIOR", "Recordatorio del día anterior"
    VENCIMIENTO = "VENCIMIENTO", "Vencimiento hoy"
    ATRASO = "ATRASO", "Atraso"
    ATRASO_SEMANAL = "ATRASO_SEMANAL", "Recordatorio semanal de atraso"
    COMPLETADA = "COMPLETADA", "Tarea completada"
    CAMBIO_ROL = "CAMBIO_ROL", "Cambio de rol privilegiado"


class EstadoNotificacion(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    ENVIANDO = "ENVIANDO", "Enviando"
    ENVIADA = "ENVIADA", "Enviada"
    FALLIDA = "FALLIDA", "Fallida"
    CANCELADA = "CANCELADA", "Cancelada"


class Notificacion(models.Model):
    tipo = models.CharField("tipo", max_length=20, choices=TipoNotificacion.choices)
    tarea = models.ForeignKey(
        "tareas.Tarea",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="notificaciones",
    )
    destinatario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="notificaciones",
        verbose_name="destinatario",
    )
    clave_unica = models.CharField("clave anti-duplicado", max_length=255, unique=True)
    contexto = models.JSONField("contexto", default=dict, blank=True)
    estado = models.CharField(
        "estado",
        max_length=10,
        choices=EstadoNotificacion.choices,
        default=EstadoNotificacion.PENDIENTE,
    )
    intentos = models.PositiveSmallIntegerField("intentos", default=0)
    proximo_intento = models.DateTimeField("próximo intento", default=timezone.now)
    ultimo_error = models.TextField("último error", blank=True)
    creada_en = models.DateTimeField("creada en", auto_now_add=True)
    enviada_en = models.DateTimeField("enviada en", null=True, blank=True)

    class Meta:
        verbose_name = "notificación"
        verbose_name_plural = "notificaciones"
        ordering = ["proximo_intento", "id"]
        indexes = [
            models.Index(
                fields=["estado", "proximo_intento"], name="notif_estado_proximo_idx"
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(tipo__in=TipoNotificacion.values),
                name="notificacion_tipo_valido",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoNotificacion.values),
                name="notificacion_estado_valido",
            ),
        ]

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.destinatario}"
