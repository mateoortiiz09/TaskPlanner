from django.core.management.base import BaseCommand

from notificaciones.servicios import enviar_pendientes


class Command(BaseCommand):
    help = "Envía los correos pendientes de la bandeja de salida."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=50)

    def handle(self, *args, **opciones):
        enviadas = enviar_pendientes(limite=opciones["limite"])
        self.stdout.write(f"Correos enviados: {enviadas}")
