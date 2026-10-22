"""Análisis antivirus con un comando externo (ClamAV en producción)."""

import shlex
import subprocess
import tempfile
from pathlib import Path

from django.conf import settings

from adjuntos import almacen
from adjuntos.models import EstadoAnalisis


def analizar(datos):
    if not settings.ANTIVIRUS_ACTIVO:
        return EstadoAnalisis.SIN_ANALIZAR
    with tempfile.NamedTemporaryFile(
        dir=almacen.directorio_temporal(), delete=False
    ) as temporal:
        temporal.write(datos)
        ruta = Path(temporal.name)
    try:
        return _analizar_ruta(ruta)
    finally:
        ruta.unlink(missing_ok=True)


def _analizar_ruta(ruta):
    comando = [*shlex.split(settings.ANTIVIRUS_COMANDO), str(ruta)]
    try:
        resultado = subprocess.run(
            comando, capture_output=True, timeout=120, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return EstadoAnalisis.ERROR
    if resultado.returncode == 0:
        return EstadoAnalisis.LIMPIO
    if resultado.returncode == 1:
        return EstadoAnalisis.INFECTADO
    return EstadoAnalisis.ERROR
