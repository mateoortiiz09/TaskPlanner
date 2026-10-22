"""Casos de uso de los adjuntos."""

import base64
import hashlib
from pathlib import Path

from django.core.exceptions import ValidationError
from django.db import transaction

from adjuntos import almacen, antivirus, cifrado, validacion
from adjuntos.models import Adjunto, EstadoAnalisis


def _guardar_clave(adjunto, clave):
    if Adjunto._meta.get_field("clave_cifrada").get_internal_type() == "BinaryField":
        adjunto.clave_cifrada = clave
    else:
        adjunto.clave_cifrada = base64.b64encode(clave).decode("ascii")


def _leer_clave(adjunto):
    valor = adjunto.clave_cifrada
    if isinstance(valor, (bytes, memoryview)):
        return bytes(valor)
    return base64.b64decode(valor)


def subir_adjunto(*, tarea, archivo, usuario):
    nombre = Path(archivo.name).name[:255]
    validacion.validar_tamano(archivo.size)
    datos = archivo.read()
    tipo = validacion.validar(nombre, datos)
    estado = antivirus.analizar(datos)
    if estado == EstadoAnalisis.INFECTADO:
        raise ValidationError(
            "El antivirus detectó una amenaza. El archivo no se guardó."
        )
    if estado == EstadoAnalisis.ERROR:
        raise ValidationError("No se pudo analizar el archivo. Intente de nuevo.")
    nombre_interno = almacen.nuevo_nombre_interno()
    adjunto = Adjunto(
        tarea=tarea,
        nombre_original=nombre,
        nombre_interno=nombre_interno,
        tipo_contenido=tipo,
        tamano_bytes=len(datos),
        sha256=hashlib.sha256(datos).hexdigest(),
        estado_analisis=estado,
        subido_por=usuario,
        cifrado=False,
    )
    contenido = datos
    if tarea.restringida:
        contenido, clave = cifrado.cifrar(datos, nombre_interno.encode())
        adjunto.cifrado = True
        _guardar_clave(adjunto, clave)
    almacen.guardar(nombre_interno, contenido)
    try:
        with transaction.atomic():
            adjunto.save()
    except Exception:
        almacen.borrar(nombre_interno)
        raise
    return adjunto


def leer_contenido(adjunto):
    datos = almacen.leer(adjunto.nombre_interno)
    if adjunto.cifrado:
        datos = cifrado.descifrar(
            datos, _leer_clave(adjunto), adjunto.nombre_interno.encode()
        )
    if hashlib.sha256(datos).hexdigest() != adjunto.sha256:
        raise ValueError("La integridad del adjunto no coincide.")
    return datos


def cifrar_adjuntos_de_tarea(tarea):
    """Cifra los adjuntos aún sin cifrar de una tarea que pasó a restringida.

    Cada archivo se escribe cifrado con un nombre interno nuevo; el archivo
    anterior se borra solo cuando la transacción se confirma.
    """
    with transaction.atomic():
        pendientes = Adjunto.objects.select_for_update().filter(
            tarea=tarea, cifrado=False
        )
        for adjunto in pendientes:
            datos = leer_contenido(adjunto)
            anterior = adjunto.nombre_interno
            nuevo = almacen.nuevo_nombre_interno()
            contenido, clave = cifrado.cifrar(datos, nuevo.encode())
            almacen.guardar(nuevo, contenido)
            adjunto.nombre_interno = nuevo
            adjunto.cifrado = True
            _guardar_clave(adjunto, clave)
            adjunto.save(update_fields=["nombre_interno", "cifrado", "clave_cifrada"])
            transaction.on_commit(lambda nombre=anterior: almacen.borrar(nombre))
