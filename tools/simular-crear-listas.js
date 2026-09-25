/* Simula un SharePoint para probar la logica de crear-listas.js sin tenant. */
const fs = require('fs');

const SITIO = 'https://falso.sharepoint.com/sites/Contratos';
const INTEGRADAS = ['ID', 'Title', 'Created', 'Modified', 'Author', 'Editor'];

function nuevoServidor() {
  return { listas: new Map(), llamadas: { contextinfo: 0, crearLista: 0, crearCampo: 0, renombrar: 0 } };
}

function instalar(srv, opciones = {}) {
  let guid = 0;
  globalThis._spPageContextInfo = { webAbsoluteUrl: SITIO };
  globalThis.location = { origin: 'https://falso.sharepoint.com', pathname: '/sites/Contratos/SitePages/Home.aspx' };

  globalThis.fetch = async (url, init = {}) => {
    const ruta = url.replace(SITIO, '');
    const metodo = (init.method || 'GET').toUpperCase();
    const ok = (obj) => ({ ok: true, status: 200, json: async () => obj, text: async () => JSON.stringify(obj) });
    const no = (status, msg) => ({
      ok: false, status,
      text: async () => JSON.stringify({ error: { message: { value: msg } } }),
      json: async () => ({ error: { message: { value: msg } } })
    });

    if (ruta === '/_api/contextinfo' && metodo === 'POST') {
      srv.llamadas.contextinfo++;
      return ok({ d: { GetContextWebInformation: { FormDigestValue: 'DIGESTO' } } });
    }

    let m = ruta.match(/^\/_api\/web\/lists\/getbytitle\('([^']+)'\)\?\$select=Id,Title$/);
    if (m) {
      const L = srv.listas.get(m[1]);
      return L ? ok({ d: { Id: L.id, Title: m[1] } }) : no(404, 'List does not exist.');
    }

    if (ruta === '/_api/web/lists' && metodo === 'POST') {
      const b = JSON.parse(init.body);
      if (srv.listas.has(b.Title)) return no(400, 'A list with that name already exists.');
      const id = 'guid-' + (++guid).toString().padStart(4, '0');
      srv.listas.set(b.Title, {
        id, plantilla: b.BaseTemplate, campos: new Set(INTEGRADAS),
        xml: new Map(), versionado: !!b.EnableVersioning, tituloTitle: null
      });
      srv.llamadas.crearLista++;
      return ok({ d: { Id: id } });
    }

    m = ruta.match(/^\/_api\/web\/lists\/getbytitle\('([^']+)'\)\/fields\?\$select=InternalName/);
    if (m) {
      const L = srv.listas.get(m[1]);
      if (!L) return no(404, 'List does not exist.');
      return ok({ d: { results: [...L.campos].map((n) => ({ InternalName: n })) } });
    }

    m = ruta.match(/^\/_api\/web\/lists\/getbytitle\('([^']+)'\)\/fields\/createfieldasxml$/);
    if (m) {
      const L = srv.listas.get(m[1]);
      if (!L) return no(404, 'List does not exist.');
      const p = JSON.parse(init.body).parameters;

      if (p.Options !== 8) return no(400, 'Options no incluye AddFieldInternalNameHint');
      const nom = /Name="([^"]+)"/.exec(p.SchemaXml);
      if (!nom) return no(400, 'El XML no declara Name');
      if (L.campos.has(nom[1])) return no(400, 'Ya existe un campo con ese nombre.');

      // Un Lookup sin List= es rechazado por SharePoint
      if (/Type="Lookup"/.test(p.SchemaXml)) {
        const lst = /List="\{([^}]+)\}"/.exec(p.SchemaXml);
        if (!lst) return no(400, 'Lookup sin atributo List');
        const existe = [...srv.listas.values()].some((x) => x.id === lst[1]);
        if (!existe) return no(400, 'La lista destino del Lookup no existe: ' + lst[1]);
      }
      if (opciones.fallarEn && opciones.fallarEn(m[1], nom[1])) return no(500, 'Fallo simulado');

      L.campos.add(nom[1]);
      L.xml.set(nom[1], p.SchemaXml);
      srv.llamadas.crearCampo++;
      return ok({ d: {} });
    }

    m = ruta.match(/^\/_api\/web\/lists\/getbytitle\('([^']+)'\)\/fields\/getbytitle\('Title'\)$/);
    if (m) {
      const L = srv.listas.get(m[1]);
      if (!L) return no(404, 'List does not exist.');
      L.tituloTitle = JSON.parse(init.body).Title;
      srv.llamadas.renombrar++;
      return { ok: true, status: 204, json: async () => null, text: async () => '' };
    }

    return no(404, 'Ruta no simulada: ' + metodo + ' ' + ruta);
  };
}

async function correr(srv, opciones) {
  instalar(srv, opciones);
  const codigo = fs.readFileSync(__dirname + '/../sharepoint/crear-listas.js', 'utf8');
  const salida = [];
  const real = { log: console.log, warn: console.warn, error: console.error };
  console.log = (...a) => salida.push(['log', a.join(' ')]);
  console.warn = (...a) => salida.push(['warn', a.join(' ')]);
  console.error = (...a) => salida.push(['error', a.join(' ')]);
  try {
    await eval('(async()=>{' + codigo + '})()');
    await new Promise((r) => setTimeout(r, 60));
  } finally {
    Object.assign(console, real);
  }
  return salida;
}

(async () => {
  const esperadas = JSON.parse(fs.readFileSync(process.env.ESQUEMA || __dirname + '/../sharepoint/.esquema.json', 'utf8')).listas;
  const totalCols = esperadas.reduce((n, l) => n + l.columnas.length, 0);

  console.log('=== PASADA 1: sitio vacio ===');
  const srv = nuevoServidor();
  let out = await correr(srv);
  out.filter(([t]) => t !== 'log').forEach(([t, m]) => console.log('  [' + t + '] ' + m));
  console.log('  listas creadas  :', srv.llamadas.crearLista, '/', esperadas.length);
  console.log('  campos creados  :', srv.llamadas.crearCampo, '/', totalCols);
  console.log('  Title renombrado:', srv.llamadas.renombrar);

  let faltan = [];
  for (const L of esperadas) {
    const real = srv.listas.get(L.nombre);
    if (!real) { faltan.push('LISTA ' + L.nombre); continue; }
    for (const c of L.columnas) if (!real.campos.has(c.name)) faltan.push(L.nombre + '.' + c.name);
  }
  console.log('  faltantes       :', faltan.length ? faltan : 'ninguna');

  const lk = srv.listas.get('Contratos').xml.get('Categoria');
  console.log('  lookup resuelto :', /List="\{guid-\d+\}"/.test(lk) ? 'si' : 'NO -> ' + lk);
  const auto = srv.listas.get('Categorias').xml.get('CategoriaPadre');
  const idCat = srv.listas.get('Categorias').id;
  console.log('  autorreferencia :', auto.includes('{' + idCat + '}') ? 'apunta a si misma, correcto' : 'MAL');

  console.log('\n=== PASADA 2: repetir sobre lo ya creado (idempotencia) ===');
  const antes = { ...srv.llamadas };
  out = await correr(srv);
  console.log('  listas creadas  :', srv.llamadas.crearLista - antes.crearLista, '(debe ser 0)');
  console.log('  campos creados  :', srv.llamadas.crearCampo - antes.crearCampo, '(debe ser 0)');
  const errores2 = out.filter(([t]) => t !== 'log');
  console.log('  avisos/errores  :', errores2.length ? errores2.map(([, m]) => m) : 'ninguno');

  console.log('\n=== PASADA 3: un campo falla, se reintenta ===');
  const srv3 = nuevoServidor();
  await correr(srv3, { fallarEn: (l, c) => l === 'Contratos' && c === 'Monto' });
  console.log('  Monto tras fallo:', srv3.listas.get('Contratos').campos.has('Monto') ? 'creado' : 'ausente (esperado)');
  const antes3 = srv3.llamadas.crearCampo;
  await correr(srv3);
  console.log('  tras reintento  :', srv3.listas.get('Contratos').campos.has('Monto') ? 'creado' : 'SIGUE AUSENTE');
  console.log('  campos nuevos   :', srv3.llamadas.crearCampo - antes3, '(debe ser 1)');
})();
