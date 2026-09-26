#!/usr/bin/env python3
"""
Genera el flujo de Power Automate que crea las 13 listas y sus 134 columnas,
y lo empaqueta como .zip importable.

Existe para el caso en que no hay acceso a una consola de navegador (tablet):
hace exactamente las mismas llamadas REST que sharepoint/crear-listas.js, pero
desde la accion estandar "Enviar una solicitud HTTP a SharePoint", que resuelve
la autenticacion sola y no requiere licencia premium.

Uso:
    python3 tools/generar-flujo-listas.py
    -> power-automate/90-crear-listas/definition.json
    -> power-automate/build/90-crear-listas.zip
"""
import json
import subprocess
import sys
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "power-automate" / "90-crear-listas"
BUILD = RAIZ / "power-automate" / "build"

esquema = json.loads(
    subprocess.run([sys.executable, str(RAIZ / "tools" / "extraer-esquema.py")],
                   capture_output=True, text=True, check=True).stdout)

# Reutiliza el generador del XML de campos para no tener dos versiones.
sys.path.insert(0, str(RAIZ / "tools"))
from importlib import import_module
gen = import_module("generar-script-listas".replace("-", "_")) \
    if (RAIZ / "tools" / "generar_script_listas.py").exists() else None

# --- XML de cada campo (misma logica que generar-script-listas.py) -----------
from xml.sax.saxutils import escape as xesc

# Los lookups no pueden llevar el GUID todavia: se deja un token que el flujo
# reemplaza en ejecucion, cuando las listas ya existen y tienen Id.
TOKEN = {"Areas": "__ID_AREAS__", "Categorias": "__ID_CATEGORIAS__",
         "Contratos": "__ID_CONTRATOS__", "CamposPersonalizados": "__ID_CAMPOS__"}


def field_xml(col):
    a = [f'Type="{col["type"]}"', f'Name="{xesc(col["name"])}"',
         f'StaticName="{xesc(col["name"])}"',
         f'DisplayName="{xesc(col["display"])}"']
    if col.get("required"):
        a.append('Required="TRUE"')
    if col.get("indexed"):
        a.append('Indexed="TRUE"')
    t = col["type"]
    if t == "Text":
        a.append(f'MaxLength="{col.get("max_length", 255)}"')
    elif t == "Note":
        a.append(f'NumLines="{col.get("num_lines", 6)}"'); a.append('RichText="FALSE"')
    elif t == "Number" and col.get("decimals") is not None:
        a.append(f'Decimals="{col["decimals"]}"')
    elif t == "DateTime":
        a.append(f'Format="{"DateOnly" if col.get("date_only") else "DateTime"}"')
    elif t == "User":
        a.append('UserSelectionMode="PeopleOnly"')
    elif t == "Lookup":
        a.append(f'List="{{{TOKEN[col["lookup"]]}}}"')
        a.append(f'ShowField="{xesc(col.get("lookup_field", "Title"))}"')
    interno = ""
    if col.get("choices"):
        interno += "<CHOICES>" + "".join(
            f"<CHOICE>{xesc(c)}</CHOICE>" for c in col["choices"]) + "</CHOICES>"
    if col.get("default") not in (None, ""):
        interno += f"<Default>{xesc(str(col['default']))}</Default>"
    abre = "<Field " + " ".join(a)
    return f"{abre}>{interno}</Field>" if interno else f"{abre} />"


DESC = {
    "Areas": "Areas de la organizacion.",
    "Parametros": "Configuracion global.",
    "Categorias": "Carpetas administrables.",
    "CamposPersonalizados": "Esquema de campos por categoria.",
    "Contratos": "Maestro de contratos.",
    "DocumentosContratos": "Biblioteca de custodia digital.",
    "MatrizAprobacion": "Reglas de aprobacion.",
    "Aprobaciones": "Historial inmutable de decisiones.",
    "Adendas": "Modificaciones a contratos vigentes.",
    "MovimientosCustodia": "Cadena de custodia del original.",
    "Alertas": "Bitacora de notificaciones.",
    "Bitacora": "Auditoria funcional.",
    "ContratosCamposValor": "Valores del esquema dinamico (EAV).",
}

# El campo Body de "Enviar una solicitud HTTP a SharePoint" es TEXTO. Si se le
# pasa un objeto, el motor lo serializa y las expresiones pierden el tipo:
# BaseTemplate llega como "100" y SharePoint responde
#   "No se puede convertir un valor primitivo en el tipo esperado 'Edm.Int32'".
# Por eso el cuerpo se arma entero aqui, ya serializado, y el flujo solo lo pasa
# tal cual. Numeros y booleanos quedan literales en el texto.
listas, campos = [], []
for l in esquema["listas"]:
    cuerpo = {"__metadata": {"type": "SP.List"},
              "Title": l["nombre"],
              "BaseTemplate": 101 if l["es_biblioteca"] else 100,
              "Description": DESC.get(l["nombre"], ""),
              "AllowContentTypes": False,
              "ContentTypesEnabled": False,
              "EnableVersioning": l["nombre"] in ("Contratos", "DocumentosContratos")}
    if l["es_biblioteca"]:
        cuerpo["EnableMinorVersions"] = True
    listas.append({"t": l["nombre"],
                   "b": json.dumps(cuerpo, ensure_ascii=False)})

    for c in l["columnas"]:
        # El XML va dentro del JSON, escapado por json.dumps. Los lookups traen
        # un token que se sustituye en ejecucion; es alfanumerico, asi que
        # reemplazarlo dentro de la cadena ya escapada es seguro.
        cuerpo_c = {"parameters": {
            "__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
            "SchemaXml": field_xml(c),
            "Options": 8}}
        campos.append({"l": l["nombre"], "n": c["name"],
                       "b": json.dumps(cuerpo_c, ensure_ascii=False)})

SITIO = "@{triggerBody()['text']}"


def http(nombre, metodo, uri, cuerpo=None, run_after=None):
    par = {"dataset": SITIO, "parameters/method": metodo, "parameters/uri": uri,
           "parameters/headers": {"Accept": "application/json;odata=verbose",
                                  "Content-Type": "application/json;odata=verbose"}}
    if cuerpo is not None:
        par["parameters/body"] = cuerpo
    a = {"type": "OpenApiConnection",
         "inputs": {"host": {"connectionName": "shared_sharepointonline",
                             "operationId": "HttpRequest",
                             "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"},
                    "parameters": par},
         "runAfter": run_after or {}}
    return nombre, a


def tolerar(accion, que):
    """Absorbe el fallo de una iteracion para que el bucle siga.

    Una iteracion cuya ultima accion falla aborta el resto del Foreach. Como
    'ya existe' es un fallo esperado y normal aqui, se encadena un Compose que
    acepta Failed: la iteracion termina en verde y el bucle continua. El error
    real sigue visible en rojo dentro del historial, en la accion HTTP.
    """
    return {f"Siguiente_{que}": {
        "type": "Compose",
        "inputs": f"@concat('procesado: ', string(item()))",
        "runAfter": {accion: ["Succeeded", "Failed"]}}}


acciones = {}

acciones["Las_listas"] = {
    "type": "Compose", "inputs": listas, "runAfter": {},
    "description": "Las 13 listas. Generado desde Deploy-Contratos.ps1: no editar a mano."}

# El cuerpo ya viene serializado desde 'Las_listas': aqui solo se pasa.
n, a = http("Crear_lista", "POST", "_api/web/lists",
            "@items('Crear_las_listas')['b']")
acciones["Crear_las_listas"] = {
    "type": "Foreach", "foreach": "@outputs('Las_listas')",
    "actions": {n: a, **tolerar(n, "lista")},
    "runAfter": {"Las_listas": ["Succeeded"]},
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "description": "Lo que ya existe falla su iteracion y se absorbe, para que "
                   "el bucle siga con el resto. Ver la nota sobre 'tolerar'."}

anterior = "Crear_las_listas"
for lista, clave in [("Areas", "Id_Areas"), ("Categorias", "Id_Categorias"),
                     ("Contratos", "Id_Contratos"),
                     ("CamposPersonalizados", "Id_Campos")]:
    n, a = http(clave, "GET", f"_api/web/lists/getbytitle('{lista}')?$select=Id",
                run_after={anterior: ["Succeeded", "Failed"]})
    acciones[clave] = a
    anterior = clave

acciones["Los_campos"] = {
    "type": "Compose", "inputs": campos,
    "runAfter": {anterior: ["Succeeded"]},
    "description": "Las 134 columnas con su Field XML. Los lookups traen un token "
                   "que se reemplaza abajo por el Id real de la lista destino."}

# El cuerpo ya trae Options=8 (AddFieldInternalNameHint): sin eso SharePoint
# descarta el nombre interno del XML y usa el visible, que es el fallo que todo
# esto evita. Aqui solo se sustituyen los cuatro tokens de lookup por el Id real.
cuerpo_expr = ("replace(replace(replace(replace(items('Crear_las_columnas')['b'],"
               "'__ID_AREAS__',body('Id_Areas')['d']['Id']),"
               "'__ID_CATEGORIAS__',body('Id_Categorias')['d']['Id']),"
               "'__ID_CONTRATOS__',body('Id_Contratos')['d']['Id']),"
               "'__ID_CAMPOS__',body('Id_Campos')['d']['Id'])")

n, a = http("Crear_columna", "POST",
            "@{concat('_api/web/lists/getbytitle(''', items('Crear_las_columnas')['l'], "
            "''')/fields/createfieldasxml')}",
            "@" + cuerpo_expr)
acciones["Crear_las_columnas"] = {
    "type": "Foreach", "foreach": "@outputs('Los_campos')",
    "actions": {n: a, **tolerar(n, "columna")},
    "runAfter": {"Los_campos": ["Succeeded"]},
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "description": "Secuencial a proposito: en paralelo SharePoint rechaza "
                   "creaciones simultaneas de columnas sobre la misma lista. "
                   "Los fallos por columna ya existente se absorben."}

definicion = {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "description": "Crea las 13 listas y las 134 columnas del sistema de Contratos "
                   "via REST, sin PowerShell ni consola del navegador.",
    "parameters": {"$connections": {"defaultValue": {}, "type": "Object"},
                   "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
    "triggers": {"Ejecutar_manualmente": {
        "type": "Request", "kind": "Button",
        "inputs": {"schema": {"type": "object",
                              "properties": {"text": {
                                  "type": "string",
                                  "title": "URL del sitio de SharePoint",
                                  "description": "https://TU-TENANT.sharepoint.com/sites/Contratos",
                                  "x-ms-dynamically-added": True}},
                              "required": ["text"]}}}},
    "actions": acciones,
    "outputs": {},
}

SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "definition.json").write_text(
    json.dumps(definicion, ensure_ascii=False, indent=2), encoding="utf-8")

# --------------------------------------------------------------- paquete .zip
# La estructura esta calcada de un paquete exportado por Power Automate. Un
# intento previo la dedujo y fallo con MissingPackageManifest: faltaban
# Microsoft.Flow/flows/manifest.json, los dos mapas por flujo, y sobre todo el
# recurso de tipo apis/connections, que es la fila que se asigna al importar
# (sin el, "Related resources" sale vacio).
NOMBRE = "Contratos - Crear listas y columnas"
CONECTOR = "shared_sharepointonline"
flow_id = str(uuid.uuid4())
api_id = str(uuid.uuid4())      # el conector
conn_id = str(uuid.uuid4())     # la conexion concreta, que el usuario elige
ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")

manifiesto = {
    "schema": "1.0",
    "details": {"displayName": NOMBRE,
                "description": "Sistema de Contratos - aprovisionamiento de listas",
                "createdTime": ahora,
                "packageTelemetryId": str(uuid.uuid4()),
                "creator": "N/A", "sourceEnvironment": ""},
    "resources": {
        flow_id: {"type": "Microsoft.Flow/flows",
                  "suggestedCreationType": "New",
                  "creationType": "Existing, New, Update",
                  "details": {"displayName": NOMBRE},
                  "configurableBy": "User", "hierarchy": "Root",
                  "dependsOn": [api_id, conn_id]},
        api_id: {"id": f"/providers/Microsoft.PowerApps/apis/{CONECTOR}",
                 "name": CONECTOR,
                 "type": "Microsoft.PowerApps/apis",
                 "suggestedCreationType": "Existing",
                 "details": {"displayName": "SharePoint"},
                 "configurableBy": "System", "hierarchy": "Child", "dependsOn": []},
        conn_id: {"type": "Microsoft.PowerApps/apis/connections",
                  "suggestedCreationType": "Existing",
                  "creationType": "Existing",
                  "details": {"displayName": "SharePoint"},
                  "configurableBy": "User", "hierarchy": "Child",
                  "dependsOn": [api_id]},
    },
}

def_flujo = {
    "name": flow_id, "id": f"/providers/Microsoft.Flow/flows/{flow_id}",
    "type": "Microsoft.Flow/flows",
    "properties": {"apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
                   "displayName": NOMBRE, "definition": definicion,
                   "connectionReferences": {CONECTOR: {
                       "connectionName": CONECTOR, "source": "Embedded",
                       "id": f"/providers/Microsoft.PowerApps/apis/{CONECTOR}",
                       "tier": "NotSpecified", "apiName": "sharepointonline",
                       "isProcessSimpleApiReferenceConversionAlreadyDone": False}},
                   "flowFailureAlertSubscribed": False,
                   "isManaged": False},
}

BUILD.mkdir(parents=True, exist_ok=True)
zip_path = BUILD / "90-crear-listas.zip"
base = f"Microsoft.Flow/flows/{flow_id}"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
    z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps(
        {"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [flow_id]}}))
    z.writestr(f"{base}/apisMap.json", json.dumps({CONECTOR: api_id}))
    z.writestr(f"{base}/connectionsMap.json", json.dumps({CONECTOR: conn_id}))
    z.writestr(f"{base}/definition.json",
               json.dumps(def_flujo, ensure_ascii=False, indent=2))

print(f"definicion : {SALIDA / 'definition.json'}")
print(f"paquete    : {zip_path}  ({zip_path.stat().st_size/1024:.0f} KB)")
print(f"listas     : {len(listas)}   columnas: {len(campos)}")
