#!/usr/bin/env python3
"""
Validador del codigo fuente YAML de la aplicacion de lienzo.

Comprueba antes de intentar empaquetar con `pac canvas pack`:

  1. El YAML es sintacticamente valido.
  2. La raiz es 'App' (App.fx.yaml) o 'Screens' (pantallas).
  3. Cada pantalla declara Properties y Children.
  4. Cada control declara 'Control'.
  5. Los nombres de control son unicos dentro de su pantalla.
  6. Toda propiedad de Power Fx empieza por '=' (es la convencion del formato).
  7. Los parentesis, corchetes y llaves de cada formula estan balanceados,
     ignorando los que aparezcan dentro de literales de texto.
  8. Toda pantalla referenciada por Navigate() existe en el codigo fuente.

Uso:
    python3 tools/validate-canvas-yaml.py
"""

import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Falta PyYAML.  pip install pyyaml")
    sys.exit(2)

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "canvas-app" / "src"

# Propiedades que no son formulas de Power Fx.
NO_FORMULA = {"Control", "Variant"}

errores = []
avisos = []


def error(ruta, msg):
    errores.append(f"  [ERROR] {ruta}: {msg}")


def aviso(ruta, msg):
    avisos.append(f"  [aviso] {ruta}: {msg}")


def balanceado(formula: str):
    """
    Devuelve (ok, detalle). Ignora lo que este dentro de comillas dobles,
    tratando "" como comilla escapada, que es como Power Fx escapa.
    """
    pares = {")": "(", "]": "[", "}": "{"}
    pila = []
    en_texto = False
    i = 0
    while i < len(formula):
        c = formula[i]
        if c == '"':
            if en_texto and i + 1 < len(formula) and formula[i + 1] == '"':
                i += 2
                continue
            en_texto = not en_texto
            i += 1
            continue
        if not en_texto:
            if c in "([{":
                pila.append(c)
            elif c in pares:
                if not pila or pila[-1] != pares[c]:
                    return False, f"'{c}' sin apertura correspondiente"
                pila.pop()
        i += 1
    if en_texto:
        return False, "comilla doble sin cerrar"
    if pila:
        return False, f"falta cerrar {len(pila)} '{pila[-1]}'"
    return True, ""


def revisar_controles(ruta, controles, pantalla, vistos, destinos):
    for entrada in controles:
        if not isinstance(entrada, dict) or len(entrada) != 1:
            error(ruta, f"en '{pantalla}' hay un elemento de Children mal formado")
            continue

        nombre, cuerpo = next(iter(entrada.items()))

        if nombre in vistos:
            error(ruta, f"nombre de control duplicado '{nombre}' en la pantalla '{pantalla}'")
        vistos.add(nombre)

        if not isinstance(cuerpo, dict):
            error(ruta, f"el control '{nombre}' no tiene cuerpo")
            continue
        if "Control" not in cuerpo:
            error(ruta, f"el control '{nombre}' no declara la propiedad 'Control'")

        props = cuerpo.get("Properties") or {}
        if not isinstance(props, dict):
            error(ruta, f"'Properties' de '{nombre}' no es un mapa")
            props = {}

        revisar_propiedades(ruta, props, f"{pantalla}/{nombre}", destinos)

        hijos = cuerpo.get("Children")
        if isinstance(hijos, list):
            revisar_controles(ruta, hijos, f"{pantalla}/{nombre}", vistos, destinos)


def revisar_propiedades(ruta, props, contexto, destinos):
    for clave, valor in props.items():
        if clave in NO_FORMULA:
            continue
        if not isinstance(valor, str):
            error(ruta, f"{contexto}.{clave} no es texto (¿se interpreto como numero o booleano?)")
            continue
        if not valor.lstrip().startswith("="):
            error(ruta, f"{contexto}.{clave} no empieza por '=' (toda formula debe empezar por '=')")
            continue

        ok, detalle = balanceado(valor)
        if not ok:
            error(ruta, f"{contexto}.{clave}: formula desbalanceada -> {detalle}")

        # Pantallas referenciadas por Navigate(...)
        for trozo in valor.split("Navigate(")[1:]:
            destino = trozo.split(",")[0].split(")")[0].strip()
            if destino and destino[0].isalpha():
                destinos.add(destino)


def main():
    if not SRC.exists():
        print(f"No existe {SRC}")
        return 1

    archivos = sorted(SRC.rglob("*.fx.yaml"))
    if not archivos:
        print("No se encontro ningun archivo .fx.yaml")
        return 1

    pantallas_definidas = set()
    destinos = set()

    print(f"Validando {len(archivos)} archivo(s) de codigo fuente\n")

    for ruta in archivos:
        rel = ruta.relative_to(RAIZ)
        try:
            doc = yaml.safe_load(ruta.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            marca = getattr(e, "problem_mark", None)
            ubic = f" (linea {marca.line + 1}, columna {marca.column + 1})" if marca else ""
            error(rel, f"YAML invalido{ubic}: {getattr(e, 'problem', e)}")
            continue

        if not isinstance(doc, dict):
            error(rel, "el archivo no contiene un mapa en la raiz")
            continue

        if "App" in doc:
            revisar_propiedades(rel, (doc["App"] or {}).get("Properties") or {}, "App", destinos)

        elif "Screens" in doc:
            for pantalla, cuerpo in (doc["Screens"] or {}).items():
                pantallas_definidas.add(pantalla)
                if not isinstance(cuerpo, dict):
                    error(rel, f"la pantalla '{pantalla}' no tiene cuerpo")
                    continue
                revisar_propiedades(rel, cuerpo.get("Properties") or {}, pantalla, destinos)
                hijos = cuerpo.get("Children")
                if hijos is None:
                    aviso(rel, f"la pantalla '{pantalla}' no tiene controles (Children)")
                elif isinstance(hijos, list):
                    revisar_controles(rel, hijos, pantalla, set(), destinos)
                else:
                    error(rel, f"'Children' de '{pantalla}' no es una lista")
        else:
            error(rel, "la raiz no es 'App' ni 'Screens'")

    # StartScreen tambien cuenta como destino.
    app = SRC / "App.fx.yaml"
    if app.exists():
        doc = yaml.safe_load(app.read_text(encoding="utf-8")) or {}
        inicio = ((doc.get("App") or {}).get("Properties") or {}).get("StartScreen", "")
        if isinstance(inicio, str) and inicio.startswith("="):
            destinos.add(inicio[1:].strip())

    for destino in sorted(destinos - pantallas_definidas):
        aviso("(global)", f"se navega a '{destino}', que no esta definida en canvas-app/src/Screens/")

    # Una pantalla a la que nadie navega es inalcanzable para el usuario.
    for huerfana in sorted(pantallas_definidas - destinos):
        aviso("(global)", f"la pantalla '{huerfana}' esta definida pero ningun Navigate() "
                          "ni StartScreen lleva a ella: es inalcanzable")

    for linea in errores:
        print(linea)
    for linea in avisos:
        print(linea)

    print(f"\n{'-' * 60}")
    print(f"Pantallas definidas: {len(pantallas_definidas)}   "
          f"Errores: {len(errores)}   Avisos: {len(avisos)}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())
