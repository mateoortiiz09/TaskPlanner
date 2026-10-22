from django.conf import settings
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from cuentas.models import Area, Usuario
from cuentas.roles import ADMINISTRADOR, LIDER_AREA, SUBGERENTE


class Command(BaseCommand):
    help = "Crea o actualiza cuentas y tareas de demostración para desarrollo local."

    def add_arguments(self, parser):
        parser.add_argument("--contrasena", default="Demo.Local.2026#")

    @transaction.atomic
    def handle(self, *args, contrasena, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo puede usarse en desarrollo local.")

        areas = {}
        for nombre in ("Compras", "Calidad", "Gerencia"):
            area, _ = Area.objects.update_or_create(
                nombre=nombre, defaults={"activa": True}
            )
            areas[nombre] = area

        datos_usuarios = (
            ("admin@ejemplo.local", ADMINISTRADOR, None, True),
            ("subgerente@ejemplo.local", SUBGERENTE, None, False),
            ("lider.compras@ejemplo.local", LIDER_AREA, areas["Compras"], False),
            ("lider.calidad@ejemplo.local", LIDER_AREA, areas["Calidad"], False),
        )
        for email, nombre_grupo, area, es_administrador in datos_usuarios:
            usuario, _ = Usuario.objects.get_or_create(email=email)
            usuario.is_active = True
            usuario.is_staff = es_administrador
            usuario.is_superuser = False
            usuario.debe_cambiar_contrasena = False
            usuario.area = area
            usuario.set_password(contrasena)
            usuario.save()
            usuario.groups.set([Group.objects.get(name=nombre_grupo)])

        call_command("axes_reset")
        correos = [email for email, _, _, _ in datos_usuarios]
        self.stdout.write("Usuarios de demostración:")
        for email in correos:
            self.stdout.write(f"- {email}")
        self.stdout.write(f"Contraseña: {contrasena}")
