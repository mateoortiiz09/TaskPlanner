"""Cifrado AES-256-GCM: una clave por archivo, protegida por la clave maestra.

El nombre interno del adjunto se usa como dato asociado, de modo que un
archivo cifrado no puede intercambiarse por otro sin que falle el descifrado.
"""

import base64
import binascii
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

_TAMANO_NONCE = 12


def validar_clave_maestra():
    valor = settings.ADJUNTOS_CLAVE_MAESTRA
    if not valor:
        raise ImproperlyConfigured("Falta ADJUNTOS_CLAVE_MAESTRA.")
    try:
        clave = base64.urlsafe_b64decode(valor)
    except (binascii.Error, ValueError) as error:
        raise ImproperlyConfigured(
            "ADJUNTOS_CLAVE_MAESTRA no es base64 válido."
        ) from error
    if len(clave) != 32:
        raise ImproperlyConfigured("ADJUNTOS_CLAVE_MAESTRA debe tener 32 bytes.")
    return clave


def cifrar(datos, asociado):
    clave_archivo = AESGCM.generate_key(bit_length=256)
    nonce = os.urandom(_TAMANO_NONCE)
    contenido = nonce + AESGCM(clave_archivo).encrypt(nonce, datos, asociado)
    nonce_clave = os.urandom(_TAMANO_NONCE)
    clave_cifrada = nonce_clave + AESGCM(validar_clave_maestra()).encrypt(
        nonce_clave, clave_archivo, asociado
    )
    return contenido, clave_cifrada


def descifrar(contenido, clave_cifrada, asociado):
    clave_archivo = AESGCM(validar_clave_maestra()).decrypt(
        clave_cifrada[:_TAMANO_NONCE], clave_cifrada[_TAMANO_NONCE:], asociado
    )
    return AESGCM(clave_archivo).decrypt(
        contenido[:_TAMANO_NONCE], contenido[_TAMANO_NONCE:], asociado
    )
