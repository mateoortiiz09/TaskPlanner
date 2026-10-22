"""Validación de adjuntos por extensión y firma del contenido."""

import io
import zipfile
from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError

TIPOS = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
LIMITE_DESCOMPRIMIDO = 200 * 1024 * 1024
MAXIMO_ENTRADAS_ZIP = 2000
_NO_COINCIDE = "El contenido del archivo no corresponde a su extensión."


def tamano_maximo():
    return settings.ADJUNTOS_TAMANO_MAX_MB * 1024 * 1024


def validar_tamano(tamano):
    if tamano <= 0:
        raise ValidationError("El archivo está vacío.")
    if tamano > tamano_maximo():
        raise ValidationError(
            f"El archivo supera el máximo de {settings.ADJUNTOS_TAMANO_MAX_MB} MB."
        )


def validar(nombre, datos):
    extension = Path(nombre).suffix.lower()
    tipo = TIPOS.get(extension)
    if tipo is None:
        raise ValidationError(
            "Tipo de archivo no permitido. Solo se aceptan PDF, DOCX, XLSX, PNG y JPG."
        )
    validar_tamano(len(datos))
    if extension == ".pdf":
        correcto = datos.startswith(b"%PDF-")
    elif extension == ".png":
        correcto = datos.startswith(b"\x89PNG\r\n\x1a\n")
    elif extension in (".jpg", ".jpeg"):
        correcto = datos.startswith(b"\xff\xd8\xff")
    else:
        _validar_office(datos, "word/" if extension == ".docx" else "xl/")
        correcto = True
    if not correcto:
        raise ValidationError(_NO_COINCIDE)
    return tipo


def _validar_office(datos, carpeta):
    if not datos.startswith(b"PK\x03\x04"):
        raise ValidationError(_NO_COINCIDE)
    try:
        with zipfile.ZipFile(io.BytesIO(datos)) as archivo_zip:
            entradas = archivo_zip.infolist()
    except zipfile.BadZipFile as error:
        raise ValidationError("El documento está dañado o no es válido.") from error
    if len(entradas) > MAXIMO_ENTRADAS_ZIP or (
        sum(entrada.file_size for entrada in entradas) > LIMITE_DESCOMPRIMIDO
    ):
        raise ValidationError("El documento es demasiado grande al descomprimirse.")
    nombres = [entrada.filename for entrada in entradas]
    if "[Content_Types].xml" not in nombres or not any(
        nombre.startswith(carpeta) for nombre in nombres
    ):
        raise ValidationError(_NO_COINCIDE)
    if any(nombre.lower().endswith("vbaproject.bin") for nombre in nombres):
        raise ValidationError("No se permiten documentos con macros.")
