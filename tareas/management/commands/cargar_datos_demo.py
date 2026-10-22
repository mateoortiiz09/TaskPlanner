import datetime
from importlib import import_module

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from adjuntos import almacen
from adjuntos.models import Adjunto
from adjuntos.servicios import subir_adjunto
from cuentas.models import Usuario
from tareas import servicios
from tareas.models import EstadoAvance, Prioridad, ResponsableTarea, Tarea

PDF_DEMO = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
CORREO_DEMO = "Demo.Local.2026#"


class Command(BaseCommand):
    help = "Carga escenarios de demostración para desarrollo local."

    def add_arguments(self, parser):
        parser.add_argument("--reiniciar", action="store_true")
        parser.add_argument("--volumen", type=int, default=0)

    def handle(self, *args, reiniciar=False, volumen=0, **options):
        if not settings.DEBUG:
            raise CommandError("Este comando solo puede usarse en desarrollo local.")
        if volumen < 0:
            raise CommandError("--volumen debe ser un entero igual o mayor que cero.")

        self._asegurar_usuarios_demo()
        hoy = timezone.localdate()
        demos_existentes = Tarea.objects.filter(nombre__startswith="[DEMO")
        if reiniciar:
            for nombre in Adjunto.objects.filter(
                tarea__nombre__startswith="[DEMO"
            ).values_list("nombre_interno", flat=True):
                almacen.borrar(nombre)
            demos_existentes.delete()
        elif Tarea.objects.filter(nombre__startswith="[DEMO]").exists():
            self.stdout.write(
                "Los escenarios [DEMO] ya existen; no se crearon de nuevo."
            )
            return self._crear_volumen(volumen, hoy)

        subgerente = Usuario.objects.get(email="subgerente@ejemplo.local")
        compras = Usuario.objects.get(email="lider.compras@ejemplo.local")
        calidad = Usuario.objects.get(email="lider.calidad@ejemplo.local")
        creadas = 0

        def crear(nombre, responsables, dias, descripcion, **campos):
            nonlocal creadas
            datos = {
                "nombre": nombre,
                "descripcion": descripcion,
                "fecha_limite": hoy + datetime.timedelta(days=dias),
                **campos,
            }
            tarea = servicios.crear_tarea(subgerente, datos, responsables)
            creadas += 1
            return tarea

        inventario = crear(
            "[DEMO] Auditoría de inventario",
            [compras],
            -10,
            "Verificar existencias y diferencias del inventario.",
            prioridad=Prioridad.ALTA,
        )
        subir_adjunto(
            tarea=inventario,
            archivo=SimpleUploadedFile("auditoria-inventario.pdf", PDF_DEMO),
            usuario=subgerente,
        )

        crear(
            "[DEMO] Revisión de certificados",
            [calidad],
            -1,
            "Revisar vigencia de certificados de calidad.",
        )
        crear(
            "[DEMO] Cotización de reactivos",
            [compras],
            0,
            "Solicitar cotizaciones actualizadas de reactivos.",
        )
        crear(
            "[DEMO] Calibración de balanzas",
            [calidad],
            1,
            "Coordinar la calibración de las balanzas.",
        )
        crear(
            "[DEMO] Orden de compra de insumos",
            [compras],
            2,
            "Preparar la orden de compra de insumos.",
        )
        crear(
            "[DEMO] Actualizar procedimiento POE-12",
            [calidad],
            10,
            "Actualizar el procedimiento operativo POE-12.",
        )
        en_proceso = crear(
            "[DEMO] Evaluación de proveedores",
            [compras],
            5,
            "Evaluar el desempeño de los proveedores.",
        )
        servicios.cambiar_estado(subgerente, en_proceso.pk, EstadoAvance.EN_PROCESO)

        dentro_plazo = crear(
            "[DEMO] Informe mensual de calidad",
            [calidad],
            1,
            "Consolidar el informe mensual de calidad.",
        )
        servicios.completar_tarea(subgerente, dentro_plazo.pk)

        fuera_plazo = crear(
            "[DEMO] Pago de facturas pendientes",
            [compras],
            -1,
            "Registrar el pago de facturas pendientes.",
        )
        servicios.completar_tarea(subgerente, fuera_plazo.pk)

        confidencial = crear(
            "[DEMO] Negociación confidencial proveedor",
            [compras],
            1,
            "Condiciones comerciales reservadas",
            restringida=True,
        )
        subir_adjunto(
            tarea=confidencial,
            archivo=SimpleUploadedFile("negociacion-confidencial.pdf", PDF_DEMO),
            usuario=subgerente,
        )
        crear(
            "[DEMO] Investigación interna de desviación",
            [calidad],
            -3,
            "Detalle reservado de la investigación",
            restringida=True,
        )

        descartada = crear(
            "[DEMO] Tarea descartada",
            [compras],
            7,
            "Tarea de demostración enviada a la papelera.",
        )
        servicios.eliminar_tarea(subgerente, descartada.pk)
        crear(
            "[DEMO] Plan de capacitación anual",
            [compras, calidad],
            15,
            "Planificar la capacitación anual de los equipos.",
        )

        self.stdout.write(f"Tareas de demostración creadas: {creadas}")
        return self._crear_volumen(volumen, hoy)

    def _crear_volumen(self, cantidad, hoy):
        if not cantidad:
            return
        creador = Usuario.objects.get(email="subgerente@ejemplo.local")
        responsable = Usuario.objects.get(email="lider.compras@ejemplo.local")
        existentes = Tarea.objects.filter(nombre__startswith="[DEMO-VOL]").count()
        tareas = [
            Tarea(
                nombre=f"[DEMO-VOL] Tarea {existentes + indice + 1}",
                descripcion="Tarea sintética para validar rendimiento.",
                fecha_limite=hoy
                + datetime.timedelta(days=((existentes + indice) % 61) - 30),
                creada_por=creador,
            )
            for indice in range(cantidad)
        ]
        Tarea.objects.bulk_create(tareas)
        ResponsableTarea.objects.bulk_create(
            [
                ResponsableTarea(
                    tarea=tarea,
                    usuario=responsable,
                    area=responsable.area,
                )
                for tarea in tareas
            ]
        )
        self.stdout.write(f"Tareas de volumen creadas: {cantidad}")

    def _asegurar_usuarios_demo(self):
        correos = (
            "admin@ejemplo.local",
            "subgerente@ejemplo.local",
            "lider.compras@ejemplo.local",
            "lider.calidad@ejemplo.local",
        )
        hashes_existentes = {
            usuario.pk: usuario.password
            for usuario in Usuario.objects.filter(email__in=correos)
            if usuario.check_password(CORREO_DEMO)
        }
        try:
            call_command("crear_datos_demo")
        except Group.DoesNotExist:
            self._recrear_grupos()
            call_command("crear_datos_demo")
        if hashes_existentes:
            for pk, password in hashes_existentes.items():
                Usuario.objects.filter(pk=pk).update(password=password)

    @staticmethod
    def _recrear_grupos():
        configuracion = import_module("cuentas.migrations.0003_grupos_y_permisos")
        for nombre, codenames in configuracion.PERMISOS_POR_GRUPO.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = []
            for etiqueta in codenames:
                app_label, codename = etiqueta.split(".")
                if nombre == "Administrador" and etiqueta == "adjuntos.add_adjunto":
                    continue
                permiso = Permission.objects.filter(
                    content_type__app_label=app_label,
                    codename=codename,
                ).first()
                if permiso is not None:
                    permisos.append(permiso)
            if nombre == "Subgerente":
                permiso_restringidas = Permission.objects.filter(
                    content_type__app_label="tareas",
                    codename="ver_restringidas",
                ).first()
                if permiso_restringidas is not None:
                    permisos.append(permiso_restringidas)
            grupo.permissions.set(permisos)
