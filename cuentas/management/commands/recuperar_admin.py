import secrets

from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from auditoria.models import EventoAuditoria
from cuentas.models import Usuario
from cuentas.roles import ADMINISTRADOR


class Command(BaseCommand):
    help = (
        "Crea o reactiva un administrador (sin superusuario) con contraseña temporal."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", required=True)
        parser.add_argument("--motivo", required=True)

    @transaction.atomic
    def handle(self, *args, email, motivo, **options):
        motivo = motivo.strip()
        if not motivo:
            raise CommandError("Debes indicar un motivo.")
        email = email.strip().lower()
        clave = secrets.token_urlsafe(12)

        usuario, creado = Usuario.objects.get_or_create(email=email)
        usuario.is_active = True
        usuario.is_staff = True
        usuario.is_superuser = False
        usuario.debe_cambiar_contrasena = True
        usuario.set_password(clave)
        usuario.save()
        usuario.groups.add(Group.objects.get(name=ADMINISTRADOR))

        EventoAuditoria.objects.create(
            actor_descripcion="consola del servidor",
            accion="cuentas.recuperar_admin",
            tipo_recurso="usuario",
            recurso_id=str(usuario.pk),
            cambios={"motivo": motivo, "cuenta_creada": creado},
        )

        accion = "creado" if creado else "reactivado"
        self.stdout.write(self.style.SUCCESS(f"Administrador {accion}: {email}"))
        self.stdout.write(
            f"Contraseña temporal (se pedirá cambiarla al ingresar): {clave}"
        )
