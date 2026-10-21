from django.conf import settings
from django.db import models
from django.db.models import Q


class PermisoExplicito(models.Model):
    """Acceso a información de nivel 3, concedido por la Subgerente.

    Aplica a una tarea o a un adjunto, nunca a los dos a la vez.
    """

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="permisos_explicitos",
        verbose_name="usuario autorizado",
    )
    tarea = models.ForeignKey(
        "tareas.Tarea",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permisos_explicitos",
    )
    adjunto = models.ForeignKey(
        "adjuntos.Adjunto",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="permisos_explicitos",
    )
    otorgado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="permisos_otorgados",
        verbose_name="otorgado por",
    )
    motivo = models.TextField("motivo")
    otorgado_en = models.DateTimeField("otorgado en", auto_now_add=True)

    class Meta:
        verbose_name = "permiso explícito"
        verbose_name_plural = "permisos explícitos"
        constraints = [
            models.CheckConstraint(
                condition=Q(tarea__isnull=False, adjunto__isnull=True)
                | Q(tarea__isnull=True, adjunto__isnull=False),
                name="permiso_sobre_un_solo_recurso",
            ),
            models.UniqueConstraint(
                fields=["usuario", "tarea"],
                condition=Q(tarea__isnull=False),
                name="permiso_unico_usuario_tarea",
            ),
            models.UniqueConstraint(
                fields=["usuario", "adjunto"],
                condition=Q(adjunto__isnull=False),
                name="permiso_unico_usuario_adjunto",
            ),
        ]

    def __str__(self):
        return f"{self.usuario} - {self.tarea or self.adjunto}"
