from datetime import date

from django.core.management.base import BaseCommand

from notificaciones.recordatorios import generar_recordatorios


class Command(BaseCommand):
    help = "Genera los recordatorios de vencimiento del día."

    def add_arguments(self, parser):
        parser.add_argument(
            "--forzar", action="store_true", help="Ignora la hora de inicio."
        )
        parser.add_argument(
            "--fecha", type=date.fromisoformat, help="Fecha a simular (AAAA-MM-DD)."
        )

    def handle(self, *args, **opciones):
        creadas = generar_recordatorios(
            hoy=opciones["fecha"], forzar=opciones["forzar"]
        )
        self.stdout.write(f"Recordatorios generados: {creadas}")
