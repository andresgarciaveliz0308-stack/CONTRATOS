#!/usr/bin/env python3
"""Genera crear-listas.js desde el esquema extraido de Deploy-Contratos.ps1."""
import json
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape as xesc

RAIZ = Path(__file__).resolve().parent.parent
esquema = json.loads(
    subprocess.run([sys.executable, str(RAIZ / "tools" / "extraer-esquema.py")],
                   capture_output=True, text=True, check=True).stdout)

DESCRIPCIONES = {
    "Areas": "Areas de la organizacion. Resuelven los roles Jefe de area y Gerente de area.",
    "Parametros": "Configuracion global del sistema.",
    "Categorias": "Carpetas administrables que determinan que campos y clausulas se piden.",
    "CamposPersonalizados": "Esquema de campos adicionales por categoria.",
    "Contratos": "Maestro de contratos. Una fila = un contrato.",
    "DocumentosContratos": "Biblioteca de custodia digital.",
    "MatrizAprobacion": "Reglas de aprobacion por tipo de contrato y monto.",
    "Aprobaciones": "Historial inmutable de decisiones.",
    "Adendas": "Modificaciones a contratos vigentes.",
    "MovimientosCustodia": "Cadena de custodia del original fisico.",
    "Alertas": "Bitacora de notificaciones, evita duplicados.",
    "Bitacora": "Auditoria funcional de acciones de la app.",
    "ContratosCamposValor": "Valor de cada campo personalizado (patron EAV).",
}

# Listas cuyo Title se renombra, tomado del esquema
def field_xml(col):
    """Construye el Field XML. El atributo Name es el nombre interno."""
    a = [f'Type="{col["type"]}"',
         f'Name="{xesc(col["name"])}"',
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
        a.append(f'NumLines="{col.get("num_lines", 6)}"')
        a.append('RichText="FALSE"')
    elif t == "Number":
        if col.get("decimals") is not None:
            a.append(f'Decimals="{col["decimals"]}"')
    elif t == "DateTime":
        a.append(f'Format="{"DateOnly" if col.get("date_only") else "DateTime"}"')
    elif t == "User":
        a.append('UserSelectionMode="PeopleOnly"')
    elif t == "Lookup":
        a.append(f'ShowField="{xesc(col.get("lookup_field", "Title"))}"')

    interno = ""
    if col.get("choices"):
        ops = "".join(f"<CHOICE>{xesc(c)}</CHOICE>" for c in col["choices"])
        interno += f"<CHOICES>{ops}</CHOICES>"
    if col.get("default") not in (None, ""):
        interno += f"<Default>{xesc(str(col['default']))}</Default>"

    abre = "<Field " + " ".join(a)
    return f"{abre}>{interno}</Field>" if interno else f"{abre} />"


listas_js = []
for l in esquema["listas"]:
    campos = []
    for c in l["columnas"]:
        e = {"n": c["name"], "xml": field_xml(c)}
        if c["type"] == "Lookup":
            e["lookup"] = c["lookup"]
        campos.append(e)

    listas_js.append({
        "titulo": l["nombre"],
        "plantilla": 101 if l["es_biblioteca"] else 100,
        "descripcion": DESCRIPCIONES.get(l["nombre"], ""),
        "versionado": l["nombre"] in ("Contratos", "DocumentosContratos"),
        "versionesMenores": l["es_biblioteca"],
        "tituloTitle": l["title_display"],
        "campos": campos,
    })

datos = json.dumps(listas_js, ensure_ascii=False, indent=1)

JS = '''/* =====================================================================
 * Contratos AB Mauri - creacion de las 13 listas y sus 134 columnas
 * ---------------------------------------------------------------------
 * COMO SE USA
 *   1. Abre tu sitio de SharePoint en Chrome o Edge, ya con sesion
 *      iniciada:  https://TU-TENANT.sharepoint.com/sites/Contratos
 *   2. F12 -> pestana "Consola"
 *   3. Si el navegador lo pide, escribe  allow pasting  y pulsa Enter
 *   4. Pega TODO este archivo y pulsa Enter
 *
 * QUE HACE
 *   Crea las listas que falten y, en cada una, las columnas que falten,
 *   usando la API REST de SharePoint con tu propia sesion. No envia nada
 *   a ningun otro sitio y no toca datos existentes.
 *
 * POR QUE NO BASTA CON CREARLAS A MANO
 *   Al crear una columna desde la interfaz, SharePoint deriva el nombre
 *   interno del visible y lo codifica ("Nombre del contrato" ->
 *   Nombre_x0020_del_x0020_contrato). Las formulas buscan
 *   NombreContrato, no lo encuentran, y SharePoint devuelve vacio sin
 *   error. Aqui se envia Options=8 (AddFieldInternalNameHint), que es lo
 *   que obliga a respetar el nombre interno del XML.
 *
 * ES SEGURO REPETIRLO
 *   Comprueba antes de crear: lo que ya existe lo deja intacto. Si algo
 *   falla a mitad, corrigelo y vuelve a ejecutar.
 * ===================================================================== */

(async function () {
  'use strict';

  var OPC_NOMBRE_INTERNO = 8;   // AddFieldInternalNameHint
  var LISTAS = __DATOS__;

  var sitio = _spPageContextInfo && _spPageContextInfo.webAbsoluteUrl
    ? _spPageContextInfo.webAbsoluteUrl
    : location.origin + location.pathname.split('/_layouts')[0]
        .split('/Lists')[0].replace(/\\/[^/]*\\.aspx$/, '').replace(/\\/$/, '');

  console.log('%cSitio: ' + sitio, 'font-weight:bold');

  var digest = null;
  async function obtenerDigest() {
    var r = await fetch(sitio + '/_api/contextinfo', {
      method: 'POST',
      headers: { 'Accept': 'application/json;odata=verbose' },
      credentials: 'include'
    });
    if (!r.ok) throw new Error('No se pudo obtener el digest (' + r.status + '). Verifica que la URL del sitio sea la correcta.');
    var j = await r.json();
    digest = j.d.GetContextWebInformation.FormDigestValue;
  }

  function cab(extra) {
    var h = {
      'Accept': 'application/json;odata=verbose',
      'Content-Type': 'application/json;odata=verbose',
      'X-RequestDigest': digest
    };
    for (var k in (extra || {})) h[k] = extra[k];
    return h;
  }

  async function pedir(url, opciones) {
    var r = await fetch(sitio + url, Object.assign({ credentials: 'include' }, opciones));
    if (!r.ok) {
      var t = await r.text();
      var m = t;
      try { m = JSON.parse(t).error.message.value; } catch (e) {}
      var err = new Error(m);
      err.status = r.status;
      throw err;
    }
    return r.status === 204 ? null : r.json();
  }

  async function existeLista(titulo) {
    try {
      var j = await pedir("/_api/web/lists/getbytitle('" + titulo + "')?$select=Id,Title", {
        headers: { 'Accept': 'application/json;odata=verbose' }
      });
      return j.d.Id;
    } catch (e) { return null; }
  }

  async function crearLista(L) {
    var cuerpo = {
      '__metadata': { 'type': 'SP.List' },
      'Title': L.titulo,
      'BaseTemplate': L.plantilla,
      'Description': L.descripcion,
      'AllowContentTypes': false,
      'ContentTypesEnabled': false
    };
    if (L.versionado) cuerpo.EnableVersioning = true;
    if (L.versionesMenores) cuerpo.EnableMinorVersions = true;
    var j = await pedir('/_api/web/lists', {
      method: 'POST', headers: cab(), body: JSON.stringify(cuerpo)
    });
    return j.d.Id;
  }

  async function columnasDe(titulo) {
    var j = await pedir("/_api/web/lists/getbytitle('" + titulo +
      "')/fields?$select=InternalName&$top=500", {
      headers: { 'Accept': 'application/json;odata=verbose' }
    });
    var s = {};
    j.d.results.forEach(function (f) { s[f.InternalName] = true; });
    return s;
  }

  async function crearColumna(titulo, xml) {
    return pedir("/_api/web/lists/getbytitle('" + titulo + "')/fields/createfieldasxml", {
      method: 'POST', headers: cab(),
      body: JSON.stringify({
        'parameters': {
          '__metadata': { 'type': 'SP.XmlSchemaFieldCreationInformation' },
          'SchemaXml': xml,
          'Options': OPC_NOMBRE_INTERNO
        }
      })
    });
  }

  async function renombrarTitle(titulo, nuevo) {
    return pedir("/_api/web/lists/getbytitle('" + titulo + "')/fields/getbytitle('Title')", {
      method: 'POST',
      headers: cab({ 'X-HTTP-Method': 'MERGE', 'IF-MATCH': '*' }),
      body: JSON.stringify({
        '__metadata': { 'type': 'SP.Field' }, 'Title': nuevo, 'Required': false
      })
    });
  }

  // ---------------------------------------------------------------- 1/3
  await obtenerDigest();
  console.log('%c1/3  Creando las listas', 'font-weight:bold;font-size:13px');

  var ids = {};
  for (var i = 0; i < LISTAS.length; i++) {
    var L = LISTAS[i];
    var id = await existeLista(L.titulo);
    if (id) {
      console.log('   ya existia   ' + L.titulo);
    } else {
      try {
        id = await crearLista(L);
        console.log('%c   creada       ' + L.titulo, 'color:#2f6b3f');
      } catch (e) {
        console.error('   FALLO        ' + L.titulo + ' -> ' + e.message);
        continue;
      }
    }
    ids[L.titulo] = id;
    if (L.tituloTitle) {
      try { await renombrarTitle(L.titulo, L.tituloTitle); } catch (e) {}
    }
  }

  // ---------------------------------------------------------------- 2/3
  console.log('%c2/3  Creando las columnas', 'font-weight:bold;font-size:13px');

  var creadas = 0, saltadas = 0, fallidas = [];
  for (var i = 0; i < LISTAS.length; i++) {
    var L = LISTAS[i];
    if (!ids[L.titulo]) { console.warn('   se omite ' + L.titulo + ' (la lista no existe)'); continue; }

    var ya = await columnasDe(L.titulo);
    var n = 0;
    for (var k = 0; k < L.campos.length; k++) {
      var c = L.campos[k];
      if (ya[c.n]) { saltadas++; continue; }

      var xml = c.xml;
      if (c.lookup) {
        var destino = ids[c.lookup];
        if (!destino) {
          fallidas.push(L.titulo + '.' + c.n + ' (falta la lista ' + c.lookup + ')');
          continue;
        }
        xml = xml.replace('<Field ', '<Field List="{' + destino + '}" ');
      }
      try {
        await crearColumna(L.titulo, xml);
        creadas++; n++;
      } catch (e) {
        fallidas.push(L.titulo + '.' + c.n + ' -> ' + e.message);
      }
    }
    console.log('   ' + L.titulo + ': ' + n + ' nuevas de ' + L.campos.length);
  }

  // ---------------------------------------------------------------- 3/3
  console.log('%c3/3  Resultado', 'font-weight:bold;font-size:13px');
  console.log('   columnas creadas     : ' + creadas);
  console.log('   ya existian          : ' + saltadas);
  if (fallidas.length) {
    console.warn('   con problemas (' + fallidas.length + '):');
    fallidas.forEach(function (f) { console.warn('     - ' + f); });
    console.warn('   Corrige y vuelve a ejecutar: lo ya creado se respeta.');
  } else {
    console.log('%c   Sin errores. Comprueba un par de nombres internos antes de seguir.',
      'color:#2f6b3f;font-weight:bold');
  }
  console.log('%cListo. Siguiente paso: permisos y datos iniciales.',
    'font-weight:bold;font-size:13px');
})();
'''

salida = RAIZ / "sharepoint" / "crear-listas.js"
salida.write_text(JS.replace("__DATOS__", datos), encoding="utf-8")
total = sum(len(l["campos"]) for l in listas_js)
print(f"escrito: {salida}")
print(f"listas: {len(listas_js)}  columnas: {total}  tamano: {salida.stat().st_size/1024:.0f} KB")
