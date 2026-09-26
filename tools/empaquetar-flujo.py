#!/usr/bin/env python3
"""
Empaqueta cualquiera de los flujos de power-automate/ como .zip importable.

Reemplaza a Build-Package.ps1 para quien no tiene PowerShell. La estructura del
paquete esta calcada de uno exportado por Power Automate; deducirla no funciona
(ver power-automate/90-crear-listas/README.md).

Uso:
    python3 tools/empaquetar-flujo.py 05-numeracion-contrato \\
        --sitio https://TU-TENANT.sharepoint.com/sites/Contratos
    python3 tools/empaquetar-flujo.py --todos --sitio https://...
"""
import argparse
import json
import re
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
BUILD = RAIZ / "power-automate" / "build"
MARCADOR = "https://CONTOSO.sharepoint.com/sites/Contratos"

NOMBRES = {
    "01-solicitud-aprobacion": "Contratos - Solicitud de aprobacion",
    "02-docusign-envio": "Contratos - Envio a firma DocuSign",
    "03-docusign-retorno": "Contratos - Retorno del documento firmado",
    "04-alertas-vencimiento": "Contratos - Alertas de vencimiento",
    "05-numeracion-contrato": "Contratos - Numeracion de contratos",
    "06-custodia-prestamos": "Contratos - Control de prestamos",
}

CONECTORES = {
    "shared_sharepointonline": ("SharePoint", "sharepointonline"),
    "shared_office365": ("Office 365 Outlook", "office365"),
    "shared_approvals": ("Approvals", "approvals"),
    "shared_docusign": ("DocuSign", "docusign"),
}


def empaquetar(carpeta: str, sitio: str) -> Path:
    origen = RAIZ / "power-automate" / carpeta / "definition.json"
    if not origen.exists():
        raise SystemExit(f"No existe {origen}")

    texto = origen.read_text(encoding="utf-8")
    # El sitio va incrustado en cada accion (parametro 'dataset') y en los
    # enlaces de los correos. Build-Package.ps1 hacia lo mismo.
    texto = texto.replace(MARCADOR, sitio.rstrip("/"))
    if "CONTOSO" in texto:
        restantes = set(re.findall(r"CONTOSO[^\"',]*", texto))
        raise SystemExit(f"Quedaron marcadores sin reemplazar: {restantes}")

    definicion = json.loads(texto)
    usados = sorted(set(re.findall(r'"connectionName":\s*"(shared_\w+)"', texto)))
    desconocidos = [c for c in usados if c not in CONECTORES]
    if desconocidos:
        raise SystemExit(f"Conector sin nombre visible definido: {desconocidos}")

    nombre = NOMBRES.get(carpeta, carpeta)
    flow_id = str(uuid.uuid4())
    ahora = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f0Z")

    recursos, depende, apis, conns = {}, [], {}, {}
    for conector in usados:
        visible, api_name = CONECTORES[conector]
        api_id, conn_id = str(uuid.uuid4()), str(uuid.uuid4())
        apis[conector], conns[conector] = api_id, conn_id
        depende += [api_id, conn_id]
        recursos[api_id] = {
            "id": f"/providers/Microsoft.PowerApps/apis/{conector}",
            "name": conector, "type": "Microsoft.PowerApps/apis",
            "suggestedCreationType": "Existing",
            "details": {"displayName": visible},
            "configurableBy": "System", "hierarchy": "Child", "dependsOn": []}
        recursos[conn_id] = {
            "type": "Microsoft.PowerApps/apis/connections",
            "suggestedCreationType": "Existing", "creationType": "Existing",
            "details": {"displayName": visible},
            "configurableBy": "User", "hierarchy": "Child",
            "dependsOn": [api_id]}

    recursos[flow_id] = {
        "type": "Microsoft.Flow/flows", "suggestedCreationType": "New",
        "creationType": "Existing, New, Update",
        "details": {"displayName": nombre},
        "configurableBy": "User", "hierarchy": "Root", "dependsOn": depende}

    manifiesto = {
        "schema": "1.0",
        "details": {"displayName": nombre,
                    "description": f"Sistema de Contratos - {nombre}",
                    "createdTime": ahora,
                    "packageTelemetryId": str(uuid.uuid4()),
                    "creator": "N/A", "sourceEnvironment": ""},
        "resources": recursos}

    def_flujo = {
        "name": flow_id, "id": f"/providers/Microsoft.Flow/flows/{flow_id}",
        "type": "Microsoft.Flow/flows",
        "properties": {
            "apiId": "/providers/Microsoft.PowerApps/apis/shared_logicflows",
            "displayName": nombre, "definition": definicion,
            "connectionReferences": {
                c: {"connectionName": c, "source": "Embedded",
                    "id": f"/providers/Microsoft.PowerApps/apis/{c}",
                    "tier": "NotSpecified", "apiName": CONECTORES[c][1],
                    "isProcessSimpleApiReferenceConversionAlreadyDone": False}
                for c in usados},
            "flowFailureAlertSubscribed": False, "isManaged": False}}

    BUILD.mkdir(parents=True, exist_ok=True)
    destino = BUILD / f"{carpeta}.zip"
    base = f"Microsoft.Flow/flows/{flow_id}"
    with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("manifest.json", json.dumps(manifiesto, ensure_ascii=False, indent=2))
        z.writestr("Microsoft.Flow/flows/manifest.json", json.dumps(
            {"packageSchemaVersion": "1.0", "flowAssets": {"assetPaths": [flow_id]}}))
        z.writestr(f"{base}/apisMap.json", json.dumps(apis))
        z.writestr(f"{base}/connectionsMap.json", json.dumps(conns))
        z.writestr(f"{base}/definition.json",
                   json.dumps(def_flujo, ensure_ascii=False, indent=2))

    print(f"{destino.name:32s} {destino.stat().st_size/1024:5.0f} KB   "
          f"conectores: {', '.join(CONECTORES[c][0] for c in usados)}")
    return destino


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("carpeta", nargs="?")
    p.add_argument("--todos", action="store_true")
    p.add_argument("--sitio", required=True)
    args = p.parse_args()

    if args.todos:
        for c in sorted(NOMBRES):
            empaquetar(c, args.sitio)
    elif args.carpeta:
        empaquetar(args.carpeta, args.sitio)
    else:
        p.error("indica una carpeta o --todos")
