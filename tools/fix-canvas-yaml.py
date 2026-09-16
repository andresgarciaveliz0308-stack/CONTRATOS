#!/usr/bin/env python3
"""
Convierte a escalar de bloque las propiedades de Power Fx que YAML no puede
leer como escalar plano.

Una linea como

    OnChange: =UpdateContext({locEstado: "x"})

es invalida: YAML ve los dos puntos seguidos de espacio dentro de "{locEstado: "
y cree que empieza otro mapa. La forma correcta es

    OnChange: |-
      =UpdateContext({locEstado: "x"})

Este script detecta esos casos y los reescribe. Es idempotente.

Uso:
    python3 tools/fix-canvas-yaml.py            # corrige canvas-app/src/**/*.fx.yaml
    python3 tools/fix-canvas-yaml.py --check    # solo informa, no escribe (para CI)
"""

import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RE_PROP = re.compile(r"^(?P<sangria>\s+)(?P<clave>[A-Za-z_][A-Za-z0-9_]*):\s(?P<valor>=.*)$")


def necesita_bloque(valor: str) -> bool:
    """Un escalar plano no puede contener ': ' ni terminar en ':'."""
    return ": " in valor or valor.rstrip().endswith(":")


def corregir(texto: str):
    salida = []
    cambios = []
    for n, linea in enumerate(texto.splitlines(), start=1):
        m = RE_PROP.match(linea)
        if not m or not necesita_bloque(m.group("valor")):
            salida.append(linea)
            continue

        sangria = m.group("sangria")
        clave = m.group("clave")
        valor = m.group("valor").rstrip()

        salida.append(f"{sangria}{clave}: |-")
        salida.append(f"{sangria}  {valor}")
        cambios.append((n, clave))

    return "\n".join(salida) + "\n", cambios


def main():
    solo_revisar = "--check" in sys.argv
    archivos = sorted((RAIZ / "canvas-app" / "src").rglob("*.fx.yaml"))

    if not archivos:
        print("No se encontro ningun archivo .fx.yaml")
        return 1

    total = 0
    for ruta in archivos:
        texto = ruta.read_text(encoding="utf-8")
        nuevo, cambios = corregir(texto)
        rel = ruta.relative_to(RAIZ)

        if not cambios:
            print(f"OK    {rel}")
            continue

        total += len(cambios)
        estado = "REQUIERE" if solo_revisar else "CORREGIDO"
        print(f"{estado}  {rel}  ({len(cambios)} propiedad(es))")
        for n, clave in cambios:
            print(f"    linea {n}: {clave}")
        if not solo_revisar:
            ruta.write_text(nuevo, encoding="utf-8")

    if solo_revisar and total:
        print(f"\n{total} propiedad(es) necesitan escalar de bloque. "
              "Ejecuta tools/fix-canvas-yaml.py sin --check.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
