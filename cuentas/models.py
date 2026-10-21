from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class Area(models.Model):
    nombre = models.CharField("nombre", max_length=100, unique=True)
    activa = models.BooleanField("activa", default=True)

    class Meta:
        verbose_name = "área"
        verbose_name_plural = "áreas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **campos):
        if not email:
            raise ValueError("El correo es obligatorio.")
        usuario = self.model(email=self.normalize_email(email).lower(), **campos)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password, **campos):
        campos.setdefault("is_staff", False)
        campos.setdefault("is_superuser", False)
        return self._crear(email, password, **campos)

    def create_superuser(self, email, password, **campos):
        # Requerido por Django; el proyecto no usa superusuarios en operación.
        campos.setdefault("is_staff", True)
        campos.setdefault("is_superuser", True)
        return self._crear(email, password, **campos)


class Usuario(AbstractUser):
    username = None
    email = models.EmailField("correo electrónico", unique=True)
    area = models.ForeignKey(
        Area,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="usuarios",
        verbose_name="área",
    )
    debe_cambiar_contrasena = models.BooleanField(
        "debe cambiar contraseña", default=False
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = UsuarioManager()

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        constraints = [
            models.UniqueConstraint(
                Lower("email"), name="usuario_email_unico_sin_mayusculas"
            )
        ]

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name() or self.email
