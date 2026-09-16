#!/usr/bin/env python3
"""
Comprobacion cruzada entre las tres capas de la solucion.

El error mas caro de esta arquitectura es un nombre interno de columna que no
coincide: el script crea 'ResponsableContrato', el flujo escribe
'ResponsableDelContrato', y nadie se entera hasta que un contrato real se
detiene en produccion. SharePoint no falla al leer una columna inexistente:
devuelve vacio.

Este script extrae las listas y columnas que crea sharepoint/Deploy-Contratos.ps1
y verifica que todo lo que referencian los flujos de Power Automate y las
formulas de Power Fx exista de verdad.

Uso:
    python3 tools/check-consistency.py
"""

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DEPLOY = RAIZ / "sharepoint" / "Deploy-Contratos.ps1"

# Columnas que SharePoint crea por si mismo en toda lista.
COLUMNAS_INTEGRADAS = {
    "ID", "Id", "Title", "Created", "Modified", "Author", "Editor",
    "GUID", "ContentType", "Attachments", "FileLeafRef", "FileRef",
    "FileDirRef", "File", "Folder", "ItemInternalId",
    "{Identifier}", "{FilenameWithExtension}", "{Link}", "{Name}",
    "{Thumbnail}", "{IsFolder}", "{Path}", "{FullPath}", "{VersionNumber}",
}

# Propiedades de un valor devuelto por el conector, no columnas.
SUFIJOS_DE_VALOR = {"Value", "Id", "Email", "DisplayName", "Claims",
                    "Picture", "Department", "JobTitle", "Title"}

errores = []
avisos = []


def extraer_esquema():
    """Lee el script de aprovisionamiento y devuelve {lista: {columnas}}."""
    texto = DEPLOY.read_text(encoding="utf-8")
    esquema = {}

    # Cada bloque empieza en  New-ListaSiNoExiste -Title 'X'  y termina en el siguiente.
    bloques = re.split(r"New-ListaSiNoExiste\s+-Title\s+'([^']+)'", texto)
    # bloques = [preambulo, nombre1, cuerpo1, nombre2, cuerpo2, ...]
    for i in range(1, len(bloques), 2):
        nombre = bloques[i]
        cuerpo = bloques[i + 1] if i + 1 < len(bloques) else ""
        columnas = set(re.findall(r"Name\s*=\s*'([^']+)'", cuerpo))
        esquema[nombre] = columnas | COLUMNAS_INTEGRADAS

    return esquema


def revisar_flujos(esquema):
    """En cada accion de SharePoint, comprueba tabla y columnas de item/..."""
    for ruta in sorted((RAIZ / "power-automate").glob("*/definition.json")):
        rel = ruta.relative_to(RAIZ)
        blob = ruta.read_text(encoding="utf-8")
        definicion = json.loads(blob)

        # Tablas referenciadas
        for tabla in set(re.findall(r'"table":\s*"([^"]+)"', blob)):
            if tabla not in esquema:
                errores.append(f"  [ERROR] {rel}: usa la lista '{tabla}', que no existe en Deploy-Contratos.ps1")

        # Columnas escritas:  "item/<Columna>"  o  "item/<Columna>/<Sufijo>"
        for columna in set(re.findall(r'"item/([A-Za-z_][A-Za-z0-9_]*)(?:/[A-Za-z]+)?"', blob)):
            base = columna[:-2] if columna.endswith("Id") and len(columna) > 2 else columna
            if not any(columna in cols or base in cols for cols in esquema.values()):
                errores.append(f"  [ERROR] {rel}: escribe en 'item/{columna}', que no es columna de ninguna lista")

        # Columnas filtradas en OData
        for campo in set(re.findall(r"\$filter[\"']?:\s*\"([^\"]+)\"", blob)):
            for token in re.findall(r"\b([A-Z][A-Za-z0-9_]*)\s+(?:eq|ne|lt|gt|le|ge)\b", campo):
                base = token[:-2] if token.endswith("Id") and len(token) > 2 else token
                if not any(token in cols or base in cols for cols in esquema.values()):
                    errores.append(f"  [ERROR] {rel}: filtra por '{token}', que no es columna de ninguna lista")

        del definicion  # solo se cargo para validar que el JSON abre


def revisar_powerfx(esquema):
    """
    Revisa las referencias Lista.Columna y Filter(Lista, Columna ...) de las
    formulas y del codigo fuente YAML.
    """
    todas = set()
    for cols in esquema.values():
        todas |= cols

    archivos = sorted((RAIZ / "canvas-app").rglob("*.md")) + \
               sorted((RAIZ / "canvas-app").rglob("*.fx.yaml"))

    for ruta in archivos:
        rel = ruta.relative_to(RAIZ)
        texto = ruta.read_text(encoding="utf-8")

        # Filter(Lista, ...) / LookUp(Lista, ...) / ClearCollect(col, Lista)
        for lista in set(re.findall(r"\b(?:Filter|LookUp|SortByColumns)\(\s*([A-Z][A-Za-z0-9_]*)\s*,", texto)):
            # Las colecciones locales empiezan por col; no son listas.
            if lista.startswith("col") or lista in {"Table", "Choices"}:
                continue
            if lista not in esquema:
                avisos.append(f"  [aviso] {rel}: consulta '{lista}', que no es una lista del esquema "
                              "(puede ser una coleccion o una variable)")

        # SortByColumns(..., "Columna", ...)
        for columna in set(re.findall(r'SortByColumns\([^,]+,\s*"([A-Za-z_][A-Za-z0-9_]*)"', texto)):
            if columna not in todas:
                errores.append(f"  [ERROR] {rel}: ordena por \"{columna}\", que no es columna de ninguna lista")


def main():
    if not DEPLOY.exists():
        print(f"No se encontro {DEPLOY}")
        return 1

    esquema = extraer_esquema()
    if not esquema:
        print("No se pudo extraer el esquema de Deploy-Contratos.ps1")
        return 1

    print("Esquema extraido de sharepoint/Deploy-Contratos.ps1:\n")
    for lista, columnas in esquema.items():
        propias = len(columnas - COLUMNAS_INTEGRADAS)
        print(f"  {lista:<24} {propias} columna(s) propia(s)")

    print("\nComprobando referencias cruzadas...\n")
    revisar_flujos(esquema)
    revisar_powerfx(esquema)

    for linea in errores:
        print(linea)
    for linea in avisos:
        print(linea)

    print(f"\n{'-' * 64}")
    print(f"Listas: {len(esquema)}   Errores: {len(errores)}   Avisos: {len(avisos)}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
