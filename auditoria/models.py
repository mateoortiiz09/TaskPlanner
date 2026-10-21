from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone


class RegistroInmutableError(Exception):
    """Se intentó modificar o borrar un evento de auditoría."""


class ResultadoEvento(models.TextChoices):
    PERMITIDO = "PERMITIDO", "Permitido"
    DENEGADO = "DENEGADO", "Denegado"


class EventoAuditoriaQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise RegistroInmutableError("Los eventos de auditoría no se modifican.")

    def delete(self):
        raise RegistroInmutableError("Los eventos de auditoría no se borran.")


class EventoAuditoria(models.Model):
    """Registro de solo inserción.

    La purga por plazo de conservación se implementará aparte, como mejora posterior.
    """

    fecha_hora = models.DateTimeField("fecha y hora", default=timezone.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="eventos_auditoria",
        verbose_name="actor",
    )
    actor_descripcion = models.CharField(
        "descripción del actor", max_length=255, blank=True
    )
    accion = models.CharField("acción", max_length=50)
    tipo_recurso = models.CharField("tipo de recurso", max_length=50, blank=True)
    recurso_id = models.CharField(
        "identificador del recurso", max_length=64, blank=True
    )
    cambios = models.JSONField("cambios", default=dict, blank=True)
    ip = models.GenericIPAddressField("dirección IP", null=True, blank=True)
    resultado = models.CharField(
        "resultado",
        max_length=10,
        choices=ResultadoEvento.choices,
        default=ResultadoEvento.PERMITIDO,
    )

    objects = EventoAuditoriaQuerySet.as_manager()

    class Meta:
        verbose_name = "evento de auditoría"
        verbose_name_plural = "eventos de auditoría"
        ordering = ["-fecha_hora", "-id"]
        permissions = [
            ("ver_auditoria_tecnica", "Puede ver la auditoría técnica"),
            ("ver_auditoria_tareas", "Puede ver la auditoría de tareas"),
        ]
        indexes = [
            models.Index(
                fields=["tipo_recurso", "recurso_id", "fecha_hora"],
                name="audit_recurso_fecha_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(resultado__in=ResultadoEvento.values),
                name="auditoria_resultado_valido",
            )
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise RegistroInmutableError("Los eventos de auditoría no se modifican.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RegistroInmutableError("Los eventos de auditoría no se borran.")

    def __str__(self):
        return f"{self.fecha_hora:%Y-%m-%d %H:%M} {self.accion}"
