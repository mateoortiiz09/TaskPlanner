from django.core.management.base import BaseCommand
from django.utils import timezone
from django_q.models import Schedule

TAREAS = [
    {
        "name": "Enviar correos pendientes",
        "func": "notificaciones.servicios.enviar_pendientes",
        "schedule_type": Schedule.MINUTES,
        "minutes": 1,
    },
    {
        "name": "Generar recordatorios",
        "func": "notificaciones.recordatorios.generar_recordatorios",
        "schedule_type": Schedule.HOURLY,
        "minutes": None,
    },
]


class Command(BaseCommand):
    help = "Crea o actualiza las tareas programadas del sistema (idempotente)."

    def handle(self, *args, **opciones):
        for tarea in TAREAS:
            datos = {clave: valor for clave, valor in tarea.items() if clave != "name"}
            Schedule.objects.update_or_create(
                name=tarea["name"],
                defaults={**datos, "repeats": -1, "next_run": timezone.now()},
            )
            self.stdout.write(f"Programada: {tarea['name']}")
