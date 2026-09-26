#!/usr/bin/env python3
"""
Genera el flujo 92: adapta un sitio ya creado a la matriz real y lo deja
listo para probar.

Hace cuatro cosas que no se pueden hacer con los flujos 90 y 91, porque
modifican lo que ya existe en vez de crearlo:

  1. Agrega la columna Vicepresidente a Areas.
  2. Agrega 'Vicepresidencia de area' a las opciones de RolAprobador.
  3. Pone a una persona como Responsable, Gerente y Vicepresidente del area,
     y como aprobador de los roles que no salen del area.
  4. Reemplaza la matriz de ejemplo por la real, desactivando la anterior en
     vez de borrarla.

Uso:
    python3 tools/generar-flujo-ajustes.py
    -> power-automate/92-ajustes-matriz/definition.json
    -> power-automate/build/92-ajustes-matriz.zip
"""
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "power-automate" / "92-ajustes-matriz"
BUILD = RAIZ / "power-automate" / "build"

SIN_TOPE = 999999999
USUARIO = "__USUARIO__"     # id numerico del usuario, resuelto en ejecucion

ROLES = ['Jefe de area', 'Gerente de area', 'Vicepresidencia de area', 'Legal',
         'Finanzas', 'Compras', 'Gerencia General', 'Directorio',
         'Usuario especifico']

# ---------------------------------------------------------------- la matriz
# Los roles 'Gerente de area' y 'Vicepresidencia de area' NO llevan aprobador:
# el flujo los resuelve contra el area del contrato. Los demas si.
TRAMOS = [
    ("0-20k", 0, 20000, [
        (1, "Gerente de area", 48)]),
    ("20k-100k", 20000, 100000, [
        (1, "Gerente de area", 48), (2, "Legal", 72)]),
    ("100k-375k", 100000, 375000, [
        (1, "Gerente de area", 48), (2, "Legal", 72),
        (3, "Gerencia General", 72)]),
    ("375k+", 375000, SIN_TOPE, [
        (1, "Gerente de area", 48), (2, "Legal", 72),
        (3, "Gerencia General", 72), (4, "Vicepresidencia de area", 120)]),
]

POR_AREA = {"Gerente de area", "Jefe de area", "Vicepresidencia de area"}

reglas = []
def regla(titulo, tipo, desde, hasta, nivel, rol, sla):
    fila = {"Title": titulo, "TipoContrato": tipo,
            "MontoDesdePEN": desde, "MontoHastaPEN": hasta,
            "Nivel": nivel, "RolAprobador": rol,
            "Obligatorio": True, "SLAHoras": sla, "Activo": True}
    if rol not in POR_AREA:
        fila["AprobadorUsuarioId"] = USUARIO
    reglas.append(fila)

for etiqueta, desde, hasta, niveles in TRAMOS:
    for n, rol, sla in niveles:
        regla(f"{etiqueta} - N{n} {rol}", "Todos", desde, hasta, n, rol, sla)

# Un NDA no tiene monto: pedirle Gerencia General y Vicepresidencia no tendria
# sentido. La regla especifica del tipo gana sobre la generica del mismo nivel.
regla("NDA - N1 Legal", "Confidencialidad (NDA)", 0, SIN_TOPE, 1, "Legal", 48)

cuerpos = []
for r in reglas:
    # El Id de usuario es numerico: se desentrecomilla el marcador para que al
    # sustituirlo quede un numero y no una cadena.
    cuerpos.append(json.dumps(r, ensure_ascii=False)
                   .replace(f'"{USUARIO}"', USUARIO))

SITIO = "@{triggerBody()['text']}"
CORREO = "triggerBody()['text_1']"

def http(nombre, metodo, uri, cuerpo=None, run_after=None, verbose=False, extra=None):
    tipo = "verbose" if verbose else "nometadata"
    cab = {"Accept": f"application/json;odata={tipo}",
           "Content-Type": f"application/json;odata={tipo}"}
    cab.update(extra or {})
    par = {"dataset": SITIO, "parameters/method": metodo,
           "parameters/uri": uri, "parameters/headers": cab}
    if cuerpo is not None:
        par["parameters/body"] = cuerpo
    return nombre, {
        "type": "OpenApiConnection",
        "inputs": {"host": {"connectionName": "shared_sharepointonline",
                            "operationId": "HttpRequest",
                            "apiId": "/providers/Microsoft.PowerApps/apis/shared_sharepointonline"},
                   "parameters": par},
        "runAfter": run_after or {}}

MERGE = {"X-HTTP-Method": "MERGE", "IF-MATCH": "*"}
A = {}

# 1 ---------------------------------------------------- columna Vicepresidente
n, a = http("Columna_vicepresidente", "POST",
            "_api/web/lists/getbytitle('Areas')/fields/createfieldasxml",
            json.dumps({"parameters": {
                "__metadata": {"type": "SP.XmlSchemaFieldCreationInformation"},
                "SchemaXml": '<Field Type="User" Name="Vicepresidente" '
                             'StaticName="Vicepresidente" DisplayName="Vicepresidente" '
                             'UserSelectionMode="PeopleOnly" />',
                "Options": 8}}, ensure_ascii=False),
            verbose=True)
A[n] = a

# 2 ------------------------------------------------- nueva opcion de rol
n, a = http("Roles_de_la_matriz", "POST",
            "_api/web/lists/getbytitle('MatrizAprobacion')/fields/getbytitle('RolAprobador')",
            json.dumps({"__metadata": {"type": "SP.FieldChoice"},
                        "Choices": {"results": ROLES}}, ensure_ascii=False),
            run_after={"Columna_vicepresidente": ["Succeeded", "Failed"]},
            verbose=True, extra=MERGE)
A[n] = a

# 3 ------------------------------------------------------ resolver el usuario
n, a = http("Asegurar_usuario", "POST", "_api/web/ensureuser",
            "@{json(concat('{\"logonName\":\"i:0#.f|membership|', "
            + CORREO + ", '\"}'))}",
            run_after={"Roles_de_la_matriz": ["Succeeded", "Failed"]})
A[n] = a

n, a = http("Obtener_area", "GET",
            "_api/web/lists/getbytitle('Areas')/items?$select=Id&$top=1",
            run_after={"Asegurar_usuario": ["Succeeded"]})
A[n] = a

# 4 -------------------------------------------- personas del area de arranque
n, a = http("Personas_del_area", "POST",
            "@{concat('_api/web/lists/getbytitle(''Areas'')/items(', "
            "first(body('Obtener_area')['value'])['Id'], ')')}",
            "@{json(concat('{\"ResponsableId\":', string(body('Asegurar_usuario')['Id']), "
            "',\"GerenteId\":', string(body('Asegurar_usuario')['Id']), "
            "',\"VicepresidenteId\":', string(body('Asegurar_usuario')['Id']), '}'))}",
            run_after={"Obtener_area": ["Succeeded"]}, extra=MERGE)
A[n] = a

# 5 --------------------------------------------- desactivar la matriz anterior
n, a = http("Reglas_actuales", "GET",
            "_api/web/lists/getbytitle('MatrizAprobacion')/items?$select=Id&$top=500",
            run_after={"Personas_del_area": ["Succeeded", "Failed"]})
A[n] = a

n, a = http("Desactivar", "POST",
            "@{concat('_api/web/lists/getbytitle(''MatrizAprobacion'')/items(', "
            "items('Desactivar_las_anteriores')['Id'], ')')}",
            '{"Activo": false}', extra=MERGE)
A["Desactivar_las_anteriores"] = {
    "type": "Foreach", "foreach": "@body('Reglas_actuales')['value']",
    "actions": {n: a, "Siguiente_desactivada": {
        "type": "Compose", "inputs": "@item()['Id']",
        "runAfter": {n: ["Succeeded", "Failed"]}}},
    "runAfter": {"Reglas_actuales": ["Succeeded"]},
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}},
    "description": "Se desactivan, no se borran: la matriz tiene la columna "
                   "Activo justamente para poder volver atras."}

# 6 ------------------------------------------------------- crear la matriz real
A["Las_reglas"] = {
    "type": "Compose", "inputs": cuerpos,
    "runAfter": {"Desactivar_las_anteriores": ["Succeeded", "Failed"]},
    "description": "Generado: no editar a mano."}

n, a = http("Crear_regla", "POST",
            "_api/web/lists/getbytitle('MatrizAprobacion')/items",
            "@replace(items('Crear_las_reglas'), '__USUARIO__', "
            "string(body('Asegurar_usuario')['Id']))")
A["Crear_las_reglas"] = {
    "type": "Foreach", "foreach": "@outputs('Las_reglas')",
    "actions": {n: a, "Siguiente_regla": {
        "type": "Compose", "inputs": "@item()",
        "runAfter": {n: ["Succeeded", "Failed"]}}},
    "runAfter": {"Las_reglas": ["Succeeded"]},
    "runtimeConfiguration": {"concurrency": {"repetitions": 1}}}

definicion = {
    "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
    "contentVersion": "1.0.0.0",
    "description": "Adapta la matriz de aprobacion a la estructura real y deja "
                   "el sitio listo para probar con una sola persona.",
    "parameters": {"$connections": {"defaultValue": {}, "type": "Object"},
                   "$authentication": {"defaultValue": {}, "type": "SecureObject"}},
    "triggers": {"Ejecutar_manualmente": {
        "type": "Request", "kind": "Button",
        "inputs": {"schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "title": "URL del sitio de SharePoint",
                         "x-ms-dynamically-added": True},
                "text_1": {"type": "string", "title": "Correo de la persona de prueba",
                           "description": "Queda como responsable, gerente, vicepresidente y aprobador",
                           "x-ms-dynamically-added": True}},
            "required": ["text", "text_1"]}}}},
    "actions": A,
    "outputs": {},
}

SALIDA.mkdir(parents=True, exist_ok=True)
(SALIDA / "definition.json").write_text(
    json.dumps(definicion, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------- paquete zip
NOMBRE = "Contratos - Ajustar matriz y datos de prueba"
CONECTOR = "shared_sharepointonline"
flow_id, api_id, conn_id = (str(uuid.uuid4()) for _ in range(3))
ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")

manifiesto = {
    "schema": "1.0",
    "details": {"displayName": NOMBRE, "description": f"Sistema de Contratos - {NOMBRE}",
                "createdTime": ahora, "packageTelemetryId": str(uuid.uuid4()),
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
                  "configurableBy": "User", "hierarchy": "Child", "dependsOn": [api_id]}}}

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
                   "flowFailureAlertSubscribed": False, "isManaged": False}}

BUILD.mkdir(parents=True, exist_ok=True)
zip_path = BUILD / "92-ajustes-matriz.zip"
base = f"Microsoft.Flow/flows/{flow_id}"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("manifest.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
    z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps(
        {"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [flow_id]}}))
    z.writestr(f"{base}/apisMap.json", json.dumps({CONECTOR: api_id}))
    z.writestr(f"{base}/connectionsMap.json", json.dumps({CONECTOR: conn_id}))
    z.writestr(f"{base}/definition.json",
               json.dumps(def_flujo, ensure_ascii=False, indent=2))

print(f"paquete : {zip_path}  ({zip_path.stat().st_size/1024:.0f} KB)")
print(f"reglas  : {len(reglas)}")
for r in reglas:
    quien = "del area" if r["RolAprobador"] in POR_AREA else "persona fija"
    print(f"   N{r['Nivel']}  {r['MontoDesdePEN']:>7,}-{r['MontoHastaPEN']:>9,}  "
          f"{r['RolAprobador']:<24} {quien}")
