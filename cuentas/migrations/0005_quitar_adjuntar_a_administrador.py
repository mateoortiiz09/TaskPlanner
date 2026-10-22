from django.db import migrations


def quitar_permiso(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    grupo = Group.objects.filter(name="Administrador").first()
    if grupo is None:
        return
    permisos = Permission.objects.filter(
        content_type__app_label="adjuntos", codename="add_adjunto"
    )
    grupo.permissions.remove(*permisos)


class Migration(migrations.Migration):
    dependencies = [
        ("cuentas", "0004_permisos_restringidas"),
        ("adjuntos", "0002_remove_adjunto_adjunto_nivel_valido_and_more"),
    ]

    operations = [migrations.RunPython(quitar_permiso, migrations.RunPython.noop)]
