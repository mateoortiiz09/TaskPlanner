from django.contrib.auth.management import create_permissions
from django.db import migrations

PERMISOS_POR_GRUPO = {
    "Administrador": [
        "cuentas.add_usuario",
        "cuentas.change_usuario",
        "cuentas.view_usuario",
        "cuentas.gestionar_usuarios",
        "cuentas.restablecer_contrasenas",
        "cuentas.configurar_parametros",
        "cuentas.add_area",
        "cuentas.change_area",
        "cuentas.view_area",
        "cuentas.gestionar_areas",
        "tareas.add_tarea",
        "tareas.change_tarea",
        "tareas.view_tarea",
        "tareas.ver_todas_las_tareas",
        "tareas.eliminar_recuperar_tareas",
        "adjuntos.add_adjunto",
        "adjuntos.view_adjunto",
        "auditoria.ver_auditoria_tecnica",
    ],
    "Subgerente": [
        "cuentas.view_usuario",
        "cuentas.view_area",
        "tareas.add_tarea",
        "tareas.change_tarea",
        "tareas.view_tarea",
        "tareas.ver_todas_las_tareas",
        "tareas.cambiar_estado",
        "tareas.completar_tareas",
        "tareas.eliminar_recuperar_tareas",
        "tareas.conceder_nivel3",
        "tareas.reclasificar_sensibilidad",
        "adjuntos.add_adjunto",
        "adjuntos.view_adjunto",
        "auditoria.ver_auditoria_tareas",
    ],
    "Líder de área": [
        "tareas.view_tarea",
        "adjuntos.view_adjunto",
    ],
}

APPS_CON_PERMISOS = ["cuentas", "tareas", "adjuntos", "auditoria"]


def crear_permisos(apps):
    for etiqueta in APPS_CON_PERMISOS:
        app_config = apps.get_app_config(etiqueta)
        app_config.models_module = True
        create_permissions(app_config, apps=apps, verbosity=0)
        app_config.models_module = None


def crear_grupos(apps, schema_editor):
    crear_permisos(apps)
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    for nombre, permisos in PERMISOS_POR_GRUPO.items():
        grupo, _ = Group.objects.get_or_create(name=nombre)
        objetos = []
        for permiso in permisos:
            app_label, codename = permiso.split(".")
            objetos.append(
                Permission.objects.get(
                    content_type__app_label=app_label, codename=codename
                )
            )
        grupo.permissions.set(objetos)


def eliminar_grupos(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name__in=PERMISOS_POR_GRUPO).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("cuentas", "0002_alter_area_options_alter_usuario_options"),
        ("tareas", "0002_alter_tarea_options"),
        ("adjuntos", "0001_initial"),
        ("auditoria", "0002_alter_eventoauditoria_options"),
    ]

    operations = [migrations.RunPython(crear_grupos, eliminar_grupos)]
