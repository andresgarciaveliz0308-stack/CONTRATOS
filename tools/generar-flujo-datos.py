#!/usr/bin/env python3
"""
Genera el flujo de Power Automate que carga los datos iniciales, y lo
empaqueta como .zip importable.

Hermano de generar-flujo-listas.py: aquel crea la estructura, este la llena.
Evita tener que pegar 45 filas a mano en la vista de cuadricula.

Carga Parametros, Categorias, las clausulas corporativas, la matriz de
aprobacion y un area de arranque. Lo que NO carga es lo que depende de
personas concretas de la organizacion -quien aprueba, quien es responsable-,
porque es una decision de negocio y no se puede adivinar.

Uso:
    python3 tools/generar-flujo-datos.py
    -> power-automate/91-cargar-datos/definition.json
    -> power-automate/build/91-cargar-datos.zip
"""
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "power-automate" / "91-cargar-datos"
BUILD = RAIZ / "power-automate" / "build"

CORREO = "__CORREO__"          # lo sustituye el flujo con lo que escriba el usuario
SIN_TOPE = 999999999

filas = []   # (lista, dict con las columnas)

# --------------------------------------------------------------- Parametros
for clave, valor in [
    ("MONEDA_BASE", "PEN"), ("TC_USD", "3.75"), ("TC_EUR", "4.05"),
    ("DIAS_PREAVISO_DEFAULT", "30"),
    ("DIAS_ALERTA_ESCALONADA", "90,60,30,15,7,1"),
    ("SLA_APROBACION_HORAS", "48"), ("DOCUSIGN_HABILITADO", "false"),
    ("RETENCION_ANIOS", "10"), ("PREFIJO_CODIGO", "CTR"),
    ("CORREO_LEGAL", CORREO), ("CORREO_ADMIN_CONTRATOS", CORREO),
    ("ADMINS", CORREO), ("CUSTODIOS", CORREO), ("LEGAL", CORREO),
]:
    filas.append(("Parametros", {"Title": clave, "Valor": valor}))

# --------------------------------------------------------------- Categorias
for nombre, color, orden in [
    ("Logistica", "#a8692b", 1), ("Comercial", "#ff9906", 2),
    ("Administrativo", "#681029", 3), ("Recursos Humanos", "#375623", 4),
    ("Legal", "#4e0c1f", 5),
]:
    filas.append(("Categorias", {"Title": nombre, "Color": color,
                                 "Orden": orden, "Activo": True}))

# ----------------------------------------------- Clausulas corporativas
# Sin Categoria: un campo sin categoria aplica a TODAS. Asi las clausulas se
# definen una sola vez. Los campos propios de cada carpeta se agregan despues
# desde la pantalla de administracion, que es justo para lo que existe.
for orden, (tecnico, etiqueta) in enumerate([
    ("ClausulaProteccionDatos", "Incluye clausula de proteccion de datos"),
    ("ClausulaAntisoborno", "Incluye clausula antisoborno y anticorrupcion"),
    ("ClausulaSalida", "Incluye clausula de salida / resolucion anticipada"),
    ("ClausulaConfidencialidad", "Incluye clausula de confidencialidad"),
], start=1):
    filas.append(("CamposPersonalizados", {
        "Title": tecnico, "Etiqueta": etiqueta, "TipoDato": "Booleano",
        "Seccion": "Clausulas corporativas", "Obligatorio": False,
        "Orden": orden, "Activo": True}))

# --------------------------------------------------------- MatrizAprobacion
TRAMOS = [
    ("0-20k", 0, 20000, [(1, "Jefe de area", 48)]),
    ("20k-100k", 20000, 100000,
     [(1, "Jefe de area", 48), (2, "Gerente de area", 48), (3, "Legal", 72)]),
    ("100k-500k", 100000, 500000,
     [(1, "Jefe de area", 48), (2, "Gerente de area", 48), (3, "Legal", 72),
      (4, "Finanzas", 48), (5, "Gerencia General", 72)]),
    ("500k+", 500000, SIN_TOPE,
     [(1, "Jefe de area", 48), (2, "Gerente de area", 48), (3, "Legal", 72),
      (4, "Finanzas", 48), (5, "Gerencia General", 72), (6, "Directorio", 120)]),
]

def regla(titulo, tipo, desde, hasta, nivel, rol, sla):
    return ("MatrizAprobacion", {
        "Title": titulo, "TipoContrato": tipo,
        "MontoDesdePEN": desde, "MontoHastaPEN": hasta,
        "Nivel": nivel, "RolAprobador": rol,
        "Obligatorio": True, "SLAHoras": sla, "Activo": True})

for etiqueta, desde, hasta, niveles in TRAMOS:
    for n, rol, sla in niveles:
        filas.append(regla(f"Todos {etiqueta} - N{n} {rol}", "Todos",
                           desde, hasta, n, rol, sla))

filas.append(regla("NDA - N1 Legal", "Confidencialidad (NDA)",
                   0, SIN_TOPE, 1, "Legal", 48))
for n, rol, sla in [(1, "Jefe de area", 48), (2, "Gerente de area", 48),
                    (3, "Gerencia General", 72)]:
    filas.append(regla(f"Laboral - N{n} {rol}", "Laboral",
                       0, SIN_TOPE, n, rol, sla))
for tipo in ("Suministro de bienes", "Obra"):
    filas.append(regla(f"{tipo} - N2 Compras", tipo,
                       20000, SIN_TOPE, 2, "Compras", 48))

# -------------------------------------------------------------------- Areas
# Una sola, de arranque. Responsable y Gerente quedan vacios a proposito: son
# columnas de Persona y decidir quien aprueba no es algo que se pueda generar.
filas.append(("Areas", {"Title": "General", "CodigoArea": "GEN", "Activo": True}))

# Cada cuerpo se serializa aqui, con los numeros y booleanos literales. Si se
# armara con expresiones dentro del flujo, el campo Body -que es texto- los
# convertiria en cadenas y SharePoint rechazaria los numericos con Edm.Int32.
datos = [{"l": lista, "b": json.dumps(cols, ensure_ascii=False)}
         for lista, cols in filas]

SITIO = "@{triggerBody()['text']}"

def http(nombre, metodo, uri, cuerpo=None, run_after=None, headers=None):
    par = {"dataset": SITIO, "parameters/method": metodo, "parameters/uri": uri,
           "parameters/headers": headers or {
               "Accept": "application/json;odata=nometadata",
               "Content-Type": "application/json;odata=nometadata"}}
    if cuerpo is not None:
        par["parameters/body"] = cuerpo
    return nombre, {
        "type": "OpenApiConnection",
        "inputs": {"host": {"connectionName": "shared_sharepointonline",
                            "operationId": "HttpRequest",
                            "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"},
                   "parameters": par},
        "runAfter": run_after or {}}

acciones = {}
acciones["Las_filas"] = {
    "type": "Compose", "inputs": datos, "runAfter": {},
    "description": "45 filas ya serializadas. Generado: no editar a mano."}

# odata=nometadata evita tener que declarar el tipo de entidad de cada lista
# (SP.Data.<algo>ListItem), que se deriva de la URL y no del titulo.
n, a = http("Crear_fila", "POST",
            "@{concat('_api/web/lists/getbytitle(''', items('Cargar_las_filas')['l'], "
            "''')/items')}",
            "@replace(items('Cargar_las_filas')['b'], '__CORREO__', "
            "triggerBody()['text_1'])")

acciones["Cargar_las_filas"] = {
    "type": "Foreach", "foreach": "@outputs('Las_filas')",
    "actions": {n: a, "Siguiente": {
        "type": "Compose",
        "inputs": "@concat('procesada: ', string(item()))",
        "runAfter": {n: ["Succeeded", "Failed"]}}},
    "runAfter": {"Las_filas": ["Succeeded"]},
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "description": "Una fila que falla no detiene el resto: el Compose de "
                   "cierre acepta Failed. Repetir el flujo duplicaria filas, "
                   "asi que se ejecuta una sola vez."}

definicion = {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "description": "Carga los datos iniciales del sistema de Contratos: "
                   "parametros, categorias, clausulas y matriz de aprobacion.",
    "parameters": {"$connections": {"defaultValue": {}, "type": "Object"},
                   "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
    "triggers": {"Ejecutar_manualmente": {
        "type": "Request", "kind": "Button",
        "inputs": {"schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string",
                         "title": "URL del sitio de SharePoint",
                         "description": "https://TU-TENANT.sharepoint.com/sites/Contratos",
                         "x-ms-dynamically-added": True},
                "text_1": {"type": "string",
                           "title": "Tu correo de administrador",
                           "description": "Queda en ADMINS, CUSTODIOS y LEGAL",
                           "x-ms-dynamically-added": True}},
            "required": ["text", "text_1"]}}}},
    "actions": acciones,
    "outputs": {},
}

SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "definition.json").write_text(
    json.dumps(definicion, ensure_ascii=False, indent=2), encoding="utf-8")

# --------------------------------------------------------------- paquete zip
NOMBRE = "Contratos - Cargar datos iniciales"
CONECTOR = "shared_sharepointonline"
flow_id, api_id, conn_id = (str(uuid.uuid4()) for _ in range(3))
ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")

manifiesto = {
    "schema": "1.0",
    "details": {"displayName": NOMBRE,
                "description": "Sistema de Contratos - datos iniciales",
                "createdTime": ahora,
                "packageTelemetryId": str(uuid.uuid4()),
                "creator": "N/A", "sourceEnvironment": ""},
    "resources": {
        flow_id: {"type": "Microsoft.Flow/flows", "suggestedCreationType": "New",
                  "creationType": "Existing, New, Update",
                  "details": {"displayName": NOMBRE},
                  "configurableBy": "User", "hierarchy": "Root",
                  "dependsOn": [api_id, conn_id]},
        api_id: {"id": f"/providers/Microsoft.PowerApps/apis/{CONECTOR}",
                 "name": CONECTOR, "type": "Microsoft.PowerApps/apis",
                 "suggestedCreationType": "Existing",
                 "details": {"displayName": "SharePoint"},
                 "configurableBy": "System", "hierarchy": "Child", "dependsOn": []},
        conn_id: {"type": "Microsoft.PowerApps/apis/connections",
                  "suggestedCreationType": "Existing", "creationType": "Existing",
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
                   "flowFailureAlertSubscribed": False, "isManaged": False},
}

BUILD.mkdir(parents=True, exist_ok=True)
zip_path = BUILD / "91-cargar-datos.zip"
base = f"Microsoft.Flow/flows/{flow_id}"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
    z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps(
        {"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [flow_id]}}))
    z.writestr(f"{base}/apisMap.json", json.dumps({CONECTOR: api_id}))
    z.writestr(f"{base}/connectionsMap.json", json.dumps({CONECTOR: conn_id}))
    z.writestr(f"{base}/definition.json",
               json.dumps(def_flujo, ensure_ascii=False, indent=2))

from collections import Counter
print(f"definicion : {SALIDA / 'definition.json'}")
print(f"paquete    : {zip_path}  ({zip_path.stat().st_size/1024:.0f} KB)")
for lista, n in Counter(l for l, _ in filas).most_common():
    print(f"   {n:3d} filas  {lista}")
print(f"   {len(filas):3d} filas  TOTAL")
