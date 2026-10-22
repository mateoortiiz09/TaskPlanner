"""Almacenamiento de adjuntos en disco, fuera de static y media."""

import os
import re
import secrets
from pathlib import Path

from django.conf import settings

_PATRON_NOMBRE = re.compile(r"[0-9a-f]{32}")


def directorio():
    ruta = Path(settings.ADJUNTOS_DIR)
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def directorio_temporal():
    ruta = directorio() / "tmp"
    ruta.mkdir(parents=True, exist_ok=True)
    return ruta


def nuevo_nombre_interno():
    return secrets.token_hex(16)


def ruta_de(nombre_interno):
    if not _PATRON_NOMBRE.fullmatch(nombre_interno or ""):
        raise ValueError("Nombre interno de adjunto no válido.")
    return directorio() / nombre_interno


def guardar(nombre_interno, datos):
    destino = ruta_de(nombre_interno)
    temporal = destino.with_suffix(".parcial")
    temporal.write_bytes(datos)
    os.replace(temporal, destino)


def leer(nombre_interno):
    return ruta_de(nombre_interno).read_bytes()


def borrar(nombre_interno):
    ruta_de(nombre_interno).unlink(missing_ok=True)
