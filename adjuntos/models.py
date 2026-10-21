import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q

from tareas.models import NivelSensibilidad


def generar_nombre_interno():
    return uuid.uuid4().hex


class EstadoAnalisis(models.TextChoices):
    SIN_ANALIZAR = "SIN_ANALIZAR", "Sin analizar"
    LIMPIO = "LIMPIO", "Limpio"
    INFECTADO = "INFECTADO", "Infectado"
    ERROR = "ERROR", "Error de análisis"


class Adjunto(models.Model):
    tarea = models.ForeignKey(
        "tareas.Tarea", on_delete=models.CASCADE, related_name="adjuntos"
    )
    nombre_original = models.CharField("nombre original", max_length=255)
    nombre_interno = models.CharField(
        "nombre interno",
        max_length=64,
        unique=True,
        default=generar_nombre_interno,
        editable=False,
    )
    tipo_contenido = models.CharField("tipo de contenido verificado", max_length=100)
    tamano_bytes = models.PositiveBigIntegerField("tamaño en bytes")
    sha256 = models.CharField("huella SHA-256", max_length=64)
    nivel_sensibilidad = models.PositiveSmallIntegerField(
        "nivel de sensibilidad",
        choices=NivelSensibilidad.choices,
        default=NivelSensibilidad.CONFIDENCIAL,
    )
    cifrado = models.BooleanField("cifrado", default=False)
    clave_cifrada = models.BinaryField(
        "clave de archivo cifrada", null=True, blank=True, editable=False
    )
    estado_analisis = models.CharField(
        "estado del análisis antivirus",
        max_length=12,
        choices=EstadoAnalisis.choices,
        default=EstadoAnalisis.SIN_ANALIZAR,
    )
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="adjuntos_subidos",
        verbose_name="subido por",
    )
    subido_en = models.DateTimeField("subido en", auto_now_add=True)

    class Meta:
        verbose_name = "adjunto"
        verbose_name_plural = "adjuntos"
        ordering = ["-subido_en"]
        constraints = [
            models.CheckConstraint(
                condition=Q(nivel_sensibilidad__in=NivelSensibilidad.values),
                name="adjunto_nivel_valido",
            ),
            models.CheckConstraint(
                condition=Q(estado_analisis__in=EstadoAnalisis.values),
                name="adjunto_estado_analisis_valido",
            ),
            models.CheckConstraint(
                condition=~Q(nivel_sensibilidad=NivelSensibilidad.ALTAMENTE_SENSIBLE)
                | Q(cifrado=True),
                name="adjunto_nivel3_siempre_cifrado",
            ),
            models.CheckConstraint(
                condition=Q(cifrado=False) | Q(clave_cifrada__isnull=False),
                name="adjunto_cifrado_con_clave",
            ),
        ]

    def __str__(self):
        return self.nombre_original
