from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from cuentas.models import Area


class Prioridad(models.TextChoices):
    BAJA = "BAJA", "Baja"
    MEDIA = "MEDIA", "Media"
    ALTA = "ALTA", "Alta"


class EstadoAvance(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    EN_PROCESO = "EN_PROCESO", "En proceso"
    COMPLETADA = "COMPLETADA", "Completada"


class NivelSensibilidad(models.IntegerChoices):
    INTERNA = 1, "Nivel 1 - Interna"
    CONFIDENCIAL = 2, "Nivel 2 - Confidencial"
    ALTAMENTE_SENSIBLE = 3, "Nivel 3 - Altamente sensible"


class Cumplimiento(models.TextChoices):
    DENTRO_DEL_PLAZO = "DENTRO", "Dentro del plazo"
    FUERA_DEL_PLAZO = "FUERA", "Fuera del plazo"


class Tarea(models.Model):
    nombre = models.CharField("nombre", max_length=200)
    descripcion = models.TextField("descripción")
    prioridad = models.CharField(
        "prioridad", max_length=10, choices=Prioridad.choices, default=Prioridad.MEDIA
    )
    estado = models.CharField(
        "estado de avance",
        max_length=12,
        choices=EstadoAvance.choices,
        default=EstadoAvance.PENDIENTE,
    )
    nivel_sensibilidad = models.PositiveSmallIntegerField(
        "nivel de sensibilidad",
        choices=NivelSensibilidad.choices,
        default=NivelSensibilidad.CONFIDENCIAL,
    )
    fecha_asignacion = models.DateField(
        "fecha de asignación", default=timezone.localdate
    )
    fecha_limite = models.DateField("fecha límite")
    fecha_finalizacion = models.DateField(
        "fecha de finalización", null=True, blank=True
    )
    cumplimiento = models.CharField(
        "cumplimiento",
        max_length=6,
        choices=Cumplimiento.choices,
        null=True,
        blank=True,
    )
    responsables = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="ResponsableTarea",
        related_name="tareas_asignadas",
        verbose_name="responsables",
    )
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="tareas_creadas",
        verbose_name="creada por",
    )
    completada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tareas_completadas",
        verbose_name="completada por",
    )
    eliminada_en = models.DateTimeField("eliminada en", null=True, blank=True)
    eliminada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="tareas_eliminadas",
        verbose_name="eliminada por",
    )
    version = models.PositiveIntegerField("versión", default=1)
    creada_en = models.DateTimeField("creada en", auto_now_add=True)
    actualizada_en = models.DateTimeField("actualizada en", auto_now=True)

    class Meta:
        verbose_name = "tarea"
        verbose_name_plural = "tareas"
        ordering = ["fecha_limite", "id"]
        permissions = [
            ("ver_todas_las_tareas", "Puede ver las tareas de todas las áreas"),
            ("cambiar_estado", "Puede cambiar el estado de avance"),
            ("completar_tareas", "Puede completar tareas"),
            ("eliminar_recuperar_tareas", "Puede eliminar y recuperar tareas"),
            ("conceder_nivel3", "Puede conceder acceso a nivel 3"),
            (
                "reclasificar_sensibilidad",
                "Puede reclasificar el nivel de sensibilidad",
            ),
        ]
        indexes = [
            models.Index(
                fields=["eliminada_en", "estado", "fecha_limite"],
                name="tarea_elim_estado_limite_idx",
            )
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(prioridad__in=Prioridad.values),
                name="tarea_prioridad_valida",
            ),
            models.CheckConstraint(
                condition=Q(estado__in=EstadoAvance.values),
                name="tarea_estado_valido",
            ),
            models.CheckConstraint(
                condition=Q(nivel_sensibilidad__in=NivelSensibilidad.values),
                name="tarea_nivel_valido",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        estado=EstadoAvance.COMPLETADA,
                        fecha_finalizacion__isnull=False,
                        cumplimiento__isnull=False,
                        completada_por__isnull=False,
                    )
                    | (
                        ~Q(estado=EstadoAvance.COMPLETADA)
                        & Q(
                            fecha_finalizacion__isnull=True,
                            cumplimiento__isnull=True,
                            completada_por__isnull=True,
                        )
                    )
                ),
                name="tarea_datos_finalizacion_coherentes",
            ),
        ]

    def __str__(self):
        return self.nombre

    @property
    def eliminada(self):
        return self.eliminada_en is not None

    def areas(self):
        return Area.objects.filter(responsabilidades__tarea=self).distinct()


class ResponsableTarea(models.Model):
    """Asignación de una tarea a un líder.

    Crear siempre con ResponsableTarea.objects.create(...), no con
    tarea.responsables.add(...), porque add() no ejecuta save() y no
    guarda el área del líder.
    """

    tarea = models.ForeignKey(
        Tarea, on_delete=models.CASCADE, related_name="asignaciones"
    )
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="responsabilidades",
        verbose_name="responsable",
    )
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        related_name="responsabilidades",
        verbose_name="área al asignar",
    )
    asignado_en = models.DateTimeField("asignado en", auto_now_add=True)

    class Meta:
        verbose_name = "responsable de tarea"
        verbose_name_plural = "responsables de tarea"
        indexes = [
            models.Index(fields=["usuario", "tarea"], name="resp_usuario_tarea_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tarea", "usuario"], name="responsable_unico_por_tarea"
            )
        ]

    def save(self, *args, **kwargs):
        if self.area_id is None and self.usuario_id is not None:
            self.area_id = self.usuario.area_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.usuario} - {self.tarea}"
