from django import template

from auditoria.servicios import etiqueta

register = template.Library()


@register.filter
def etiqueta_accion(accion):
    return etiqueta(accion)


@register.filter
def detalle_evento(datos):
    if not datos:
        return ""
    return "; ".join(f"{clave}: {valor}" for clave, valor in datos.items())
