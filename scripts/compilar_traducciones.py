"""Compila los archivos .po del proyecto a .mo sin depender de GNU gettext.

Uso: python scripts/compilar_traducciones.py
"""

import ast
import struct
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def leer_po(ruta):
    mensajes = {}
    msgid = msgstr = seccion = None

    def guardar():
        if msgid is not None and msgstr is not None and (msgstr or msgid == ""):
            mensajes[msgid] = msgstr

    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        if linea.startswith("msgid "):
            guardar()
            msgid, msgstr, seccion = ast.literal_eval(linea[6:]), None, "msgid"
        elif linea.startswith("msgstr "):
            msgstr, seccion = ast.literal_eval(linea[7:]), "msgstr"
        elif linea.startswith('"'):
            texto = ast.literal_eval(linea)
            if seccion == "msgid":
                msgid += texto
            elif seccion == "msgstr":
                msgstr += texto
    guardar()
    return mensajes


def escribir_mo(mensajes, ruta):
    claves = sorted(mensajes)
    ids = b""
    textos = b""
    posiciones = []
    for clave in claves:
        clave_b = clave.encode("utf-8")
        texto_b = mensajes[clave].encode("utf-8")
        posiciones.append((len(ids), len(clave_b), len(textos), len(texto_b)))
        ids += clave_b + b"\0"
        textos += texto_b + b"\0"

    cantidad = len(claves)
    inicio_claves = 7 * 4 + 16 * cantidad
    inicio_textos = inicio_claves + len(ids)
    tabla = []
    for pos_id, largo_id, _, _ in posiciones:
        tabla += [largo_id, pos_id + inicio_claves]
    for _, _, pos_texto, largo_texto in posiciones:
        tabla += [largo_texto, pos_texto + inicio_textos]

    encabezado = struct.pack(
        "Iiiiiii", 0x950412DE, 0, cantidad, 7 * 4, 7 * 4 + cantidad * 8, 0, 0
    )
    ruta.write_bytes(encabezado + struct.pack(f"{len(tabla)}i", *tabla) + ids + textos)


def main():
    archivos = sorted((RAIZ / "locale").glob("*/LC_MESSAGES/*.po"))
    if not archivos:
        print("No se encontraron archivos .po en locale/.")
    for po in archivos:
        mo = po.with_suffix(".mo")
        escribir_mo(leer_po(po), mo)
        print(f"Compilado: {mo.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
