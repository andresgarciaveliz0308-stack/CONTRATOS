#!/usr/bin/env python3
"""
Validador de definiciones de flujo de Power Automate.

Comprueba la consistencia interna de los archivos definition.json antes de
importarlos, porque el disenador solo reporta estos errores en tiempo de
ejecucion y despues de haber creado el flujo.

Verifica:
  1. JSON bien formado y con la estructura minima (triggers / actions).
  2. Nombres de accion unicos en todo el flujo (Logic Apps lo exige).
  3. Cada clave de runAfter apunta a una accion hermana del mismo ambito.
  4. Cada referencia body('X') / outputs('X') apunta a una accion o disparador existente.
  5. Cada items('X') / foreach apunta a un bucle Foreach existente.
  6. Cada variables('X') fue inicializada con un InitializeVariable previo.
  7. No quedan marcadores de posicion sin reemplazar en el entorno destino.

Uso:
    python3 tools/validate-flows.py                     # valida power-automate/**/definition.json
    python3 tools/validate-flows.py ruta/definition.json
    python3 tools/validate-flows.py --site-url https://real.sharepoint.com/sites/Contratos
"""

import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

# Ambitos que contienen sub-acciones y como llegar a ellas.
CONTENEDORES = ("actions", "else", "default")

RE_BODY = re.compile(r"\bbody\('([^']+)'\)")
RE_OUTPUTS = re.compile(r"\boutputs\('([^']+)'\)")
RE_ITEMS = re.compile(r"\bitems\('([^']+)'\)")
RE_VARIABLES = re.compile(r"\bvariables\('([^']+)'\)")
RE_ACTION_FN = re.compile(r"\bactions\('([^']+)'\)")

# Funciones de expresion que NO son referencias a acciones aunque lo parezcan.
NO_ES_ACCION = {"value", "item", "iterationIndexes"}


class Resultado:
    def __init__(self):
        self.errores = []
        self.avisos = []

    def error(self, ruta, msg):
        self.errores.append(f"  [ERROR] {ruta}: {msg}")

    def aviso(self, ruta, msg):
        self.avisos.append(f"  [aviso] {ruta}: {msg}")

    @property
    def ok(self):
        return not self.errores


def recorrer_acciones(acciones, camino=""):
    """Devuelve (nombre, definicion, ambito_hermanos, camino) de cada accion, recursivamente."""
    for nombre, definicion in acciones.items():
        yield nombre, definicion, acciones, camino
        if not isinstance(definicion, dict):
            continue

        for clave in CONTENEDORES:
            sub = definicion.get(clave)
            if not isinstance(sub, dict):
                continue
            # "else" y "default" envuelven las acciones en otra capa.
            interior = sub.get("actions") if clave in ("else", "default") else sub
            if isinstance(interior, dict):
                yield from recorrer_acciones(interior, f"{camino}/{nombre}/{clave}")

        # Un Switch guarda cada rama bajo cases/<nombre>/actions.
        casos = definicion.get("cases")
        if isinstance(casos, dict):
            for nombre_caso, caso in casos.items():
                interior = caso.get("actions") if isinstance(caso, dict) else None
                if isinstance(interior, dict):
                    yield from recorrer_acciones(interior, f"{camino}/{nombre}/cases/{nombre_caso}")


def texto_completo(obj):
    """Aplana cualquier estructura a una sola cadena, para buscar expresiones."""
    return json.dumps(obj, ensure_ascii=False)


def etiqueta_de(ruta):
    """Ruta relativa al repositorio cuando se puede; si no, la ruta tal cual."""
    try:
        return ruta.relative_to(RAIZ)
    except ValueError:
        return ruta


def validar(ruta, site_url_esperada=None):
    res = Resultado()
    etiqueta = etiqueta_de(ruta)

    try:
        definicion = json.loads(ruta.read_text(encoding="utf-8"))
    except FileNotFoundError:
        res.error(etiqueta, "el archivo no existe")
        return res
    except json.JSONDecodeError as e:
        res.error(etiqueta, f"JSON invalido en linea {e.lineno}, columna {e.colno}: {e.msg}")
        return res

    if "triggers" not in definicion or not definicion["triggers"]:
        res.error(etiqueta, "no define ningun disparador (triggers)")
        return res
    if "actions" not in definicion:
        res.error(etiqueta, "no define acciones (actions)")
        return res

    disparadores = set(definicion["triggers"].keys())
    acciones = list(recorrer_acciones(definicion["actions"]))

    # --- 2. Nombres unicos en todo el flujo
    vistos = {}
    for nombre, _, _, camino in acciones:
        if nombre in vistos:
            res.error(etiqueta,
                      f"nombre de accion duplicado '{nombre}' (en '{vistos[nombre] or '/'}' y en '{camino or '/'}'). "
                      "Logic Apps exige nombres unicos en todo el flujo.")
        vistos[nombre] = camino

    nombres_accion = set(vistos.keys())
    foreach_existentes = {n for n, d, _, _ in acciones
                          if isinstance(d, dict) and d.get("type") == "Foreach"}

    # --- 3. runAfter dentro del mismo ambito
    for nombre, definicion_accion, hermanos, camino in acciones:
        if not isinstance(definicion_accion, dict):
            continue
        for objetivo in (definicion_accion.get("runAfter") or {}):
            if objetivo not in hermanos:
                res.error(etiqueta,
                          f"'{nombre}' tiene runAfter -> '{objetivo}', que no es una accion hermana "
                          f"en el ambito '{camino or '/'}'")

    # --- 4/5/6. Referencias en expresiones
    variables_declaradas = set()
    for nombre, d, _, _ in acciones:
        if isinstance(d, dict) and d.get("type") == "InitializeVariable":
            for v in d.get("inputs", {}).get("variables", []):
                if "name" in v:
                    variables_declaradas.add(v["name"])

    blob = texto_completo(definicion)

    for ref in set(RE_BODY.findall(blob)) | set(RE_OUTPUTS.findall(blob)) | set(RE_ACTION_FN.findall(blob)):
        if ref in NO_ES_ACCION:
            continue
        if ref not in nombres_accion and ref not in disparadores:
            res.error(etiqueta, f"se referencia body/outputs('{ref}') pero no existe esa accion ni ese disparador")

    for ref in set(RE_ITEMS.findall(blob)):
        if ref not in foreach_existentes:
            res.error(etiqueta, f"se referencia items('{ref}') pero '{ref}' no es un bucle Foreach de este flujo")

    for ref in set(RE_VARIABLES.findall(blob)):
        if ref not in variables_declaradas:
            res.error(etiqueta, f"se usa variables('{ref}') pero nunca se inicializa con InitializeVariable")

    # Un Foreach debe declarar sobre que itera y un Switch sobre que conmuta.
    for nombre, d, _, _ in acciones:
        if not isinstance(d, dict):
            continue
        if d.get("type") == "Foreach" and not d.get("foreach"):
            res.error(etiqueta, f"el bucle '{nombre}' no declara la propiedad 'foreach'")
        if d.get("type") == "Switch":
            if not d.get("expression"):
                res.error(etiqueta, f"el switch '{nombre}' no declara la propiedad 'expression'")
            for nombre_caso, caso in (d.get("cases") or {}).items():
                if isinstance(caso, dict) and "case" in caso:
                    continue
                res.error(etiqueta, f"la rama '{nombre_caso}' del switch '{nombre}' no declara su valor 'case'")

    # --- 7. Marcadores de posicion
    for marcador, explicacion in (
        ("CONTOSO.sharepoint.com", "sitio de ejemplo"),
        ("DOCUSIGN_ACCOUNT_ID", "id de cuenta de DocuSign"),
    ):
        n = blob.count(marcador)
        if not n:
            continue
        if site_url_esperada:
            res.error(etiqueta, f"quedan {n} referencias al marcador {marcador} sin reemplazar")
        else:
            res.aviso(etiqueta, f"{n} referencias al marcador {marcador} ({explicacion}); "
                                "las reemplaza Build-Package.ps1")

    # appsetting() solo existe en Logic Apps Standard, no en flujos de nube.
    if "appsetting(" in blob:
        res.error(etiqueta, "usa appsetting(), que no esta disponible en los flujos de nube de Power Automate")

    return res


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    site_url = None
    for a in sys.argv[1:]:
        if a.startswith("--site-url"):
            site_url = a.split("=", 1)[1] if "=" in a else "definida"

    if args:
        rutas = [Path(a).resolve() for a in args]
    else:
        rutas = sorted((RAIZ / "power-automate").glob("*/definition.json"))

    if not rutas:
        print("No se encontro ninguna definicion de flujo.")
        return 1

    print(f"Validando {len(rutas)} definicion(es) de flujo\n")

    total_err = 0
    total_avi = 0
    for ruta in rutas:
        res = validar(ruta, site_url)
        estado = "OK  " if res.ok else "FALLA"
        print(f"{estado}  {etiqueta_de(ruta)}")
        for linea in res.errores:
            print(linea)
        for linea in res.avisos:
            print(linea)
        total_err += len(res.errores)
        total_avi += len(res.avisos)

    print(f"\n{'-' * 60}")
    print(f"Errores: {total_err}   Avisos: {total_avi}")
    return 1 if total_err else 0


if __name__ == "__main__":
    sys.exit(main())
