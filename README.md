# Sistema de Contratos — Administración, Custodia y Aprobaciones

Aplicación de **Power Apps (Canvas)** sobre **SharePoint Online**, con workflow de
aprobaciones en **Power Automate**, firma electrónica con **DocuSign** y alertas
automáticas de vencimiento.

Este repositorio contiene **todo lo necesario para desplegar la solución desde cero**:
el aprovisionamiento del sitio de SharePoint, las definiciones de los flujos, el código
fuente de la app de Power Apps y la documentación funcional y técnica.

---

## Qué resuelve

| Necesidad | Cómo se cubre |
|---|---|
| **Administración** | Maestro único de contratos con ficha completa: contraparte, económicos, vigencia, obligaciones, garantías, renovación automática. |
| **Organización por carpetas** | Categorías administrables (Logística, Comercial, RRHH, Legal...) con búsqueda por código, nombre o contraparte. |
| **Esquema configurable por categoría** | Campos adicionales y checklist de cláusulas corporativas (protección de datos, antisoborno, salida) que el administrador define por carpeta, sin tocar SharePoint. |
| **Custodia documental** | Biblioteca versionada para el digital, con vista previa de PDF en pantalla, + trazabilidad del **original físico** (ubicación, custodio, préstamos y devoluciones). |
| **Workflow de aprobaciones** | Matriz de aprobación **configurable por tipo de contrato y monto**, multinivel y secuencial, con historial completo e inmutable, vía tarjetas de Teams/Outlook. |
| **Firma electrónica** | Envío automático a DocuSign al aprobarse; el sobre firmado regresa solo al expediente. |
| **Control de vencimientos** | Alertas por correo con N días de preaviso al responsable, al administrador **y** al responsable adicional de la categoría (p. ej. Compras), incluyendo renovaciones automáticas y cartas fianza. |

---

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│  Power Apps — Canvas App "Contratos"  (web + móvil)          │
│  Registro · Bandeja · Ficha · Aprobaciones · Custodia · Admin │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│  SharePoint Online — sitio "Contratos"                        │
│  13 listas de negocio + 1 biblioteca documental versionada    │
└───────────────┬──────────────────────────────────────────────┘
                │
┌───────────────▼──────────────────────────────────────────────┐
│  Power Automate — 6 flujos                                    │
│  Numeración · Aprobación · DocuSign envío/retorno ·           │
│  Alertas de vencimiento · Control de préstamos                │
└───────────────┬──────────────────────────────────────────────┘
                │
        ┌───────┴────────┬──────────────┐
        ▼                ▼              ▼
   Approvals          DocuSign      Outlook / Teams
```

Detalle completo en [`docs/01-arquitectura.md`](docs/01-arquitectura.md).

---

## Contenido del repositorio

```
sharepoint/          Aprovisionamiento del sitio (PnP PowerShell)
  Deploy-Contratos.ps1      Script maestro: crea listas, columnas, vistas, índices
  Seed-DemoData.ps1         Datos de ejemplo y matriz de aprobación inicial
  Set-Permissions.ps1       Grupos, permisos y seguridad a nivel de elemento
  schema/                   Plantilla PnP + diccionario de datos en JSON

power-automate/      Definiciones de los 6 flujos (importables)
  01-solicitud-aprobacion/  Workflow multinivel según matriz
  02-docusign-envio/        Creación y envío del sobre de firma
  03-docusign-retorno/      Retorno del documento firmado al expediente
  04-alertas-vencimiento/   Preaviso de vencimiento, renovación y fianzas
  05-numeracion-contrato/   Código correlativo CTR-AAAA-NNNN
  06-custodia-prestamos/    Alerta de originales prestados no devueltos

canvas-app/          Código fuente de la app
  src/                      Power Fx en YAML (pac canvas pack)
  formulas/                 Fórmulas por pantalla, listas para copiar/pegar
  README.md                 Cómo empaquetar o reconstruir la app

tools/               Validadores (Python 3, sin dependencias salvo PyYAML)
  validate-flows.py         Consistencia interna de los definition.json
  validate-canvas-yaml.py   Estructura y fórmulas del código fuente de la app
  check-consistency.py      Nombres de listas y columnas entre las tres capas
  fix-canvas-yaml.py        Corrige las propiedades que YAML no lee como escalar plano

docs/                Documentación funcional y técnica (español)
```

### Validar antes de desplegar

```bash
python3 tools/check-consistency.py      # ¿existe cada lista y columna referenciada?
python3 tools/validate-flows.py         # ¿los flujos son coherentes?
python3 tools/validate-canvas-yaml.py   # ¿la app está bien formada?
```

`check-consistency.py` es el que más trabajo ahorra: extrae el esquema real del
script de aprovisionamiento y comprueba que **cada lista y cada columna** que
usan los flujos y las fórmulas existe de verdad. SharePoint no falla al leer una
columna inexistente — devuelve vacío — así que una errata de este tipo no se
descubre hasta que un contrato real se detiene en producción.

---

## Despliegue rápido

**¿Primera vez? Empieza por [`docs/00-inicio-rapido.md`](docs/00-inicio-rapido.md)** —
10 pasos con comandos listos para copiar y pegar, pensados para ver un
contrato real recorriendo el circuito de aprobación en unas 2 horas, incluso
sin tenant corporativo todavía (usando el Microsoft 365 Developer Program,
gratis). Lo que sigue aquí es el resumen; la guía completa, con todos los
matices, está en [`docs/03-despliegue.md`](docs/03-despliegue.md).

Requisitos: PowerShell 7+, `PnP.PowerShell`, permisos de administrador del sitio y
licencia de Power Automate con conector premium (DocuSign).

> **¿Sin acceso a PowerShell?** Todo el sistema se puede construir únicamente
> desde el navegador: [`docs/09-sin-powershell.md`](docs/09-sin-powershell.md).
> Toma más tiempo (2–4 horas de trabajo manual en vez de 4 minutos de script),
> pero no requiere instalar nada.

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser

./sharepoint/Deploy-Contratos.ps1 `
    -SiteUrl "https://TUTENANT.sharepoint.com/sites/Contratos" `
    -CreateSite

./sharepoint/Set-Permissions.ps1 -SiteUrl "https://TUTENANT.sharepoint.com/sites/Contratos"
./sharepoint/Seed-DemoData.ps1   -SiteUrl "https://TUTENANT.sharepoint.com/sites/Contratos"
```

Luego se importan los flujos y se conecta la app. El procedimiento completo, paso a
paso y con capturas de los puntos críticos, está en
[`docs/03-despliegue.md`](docs/03-despliegue.md).

---

## Documentación

| Documento | Contenido |
|---|---|
| [00 — Inicio rápido](docs/00-inicio-rapido.md) | **10 pasos, copiar y pegar.** La forma más corta de ver la app funcionando |
| [01 — Arquitectura](docs/01-arquitectura.md) | Componentes, licenciamiento, límites y decisiones de diseño |
| [02 — Modelo de datos](docs/02-modelo-datos.md) | Las 13 listas, cada columna, tipos, opciones y relaciones |
| [03 — Despliegue](docs/03-despliegue.md) | Instalación paso a paso de extremo a extremo |
| [04 — Workflow de aprobaciones](docs/04-flujos-aprobacion.md) | Matriz configurable, niveles, SLA, delegación y reproceso |
| [05 — Seguridad y permisos](docs/05-seguridad-permisos.md) | Grupos, roles, confidencialidad y permisos a nivel de elemento |
| [06 — Manual de usuario](docs/06-manual-usuario.md) | Guía para solicitantes, aprobadores y custodios |
| [07 — Integración DocuSign](docs/07-docusign.md) | Cuenta, conector, plantillas y mapeo de firmantes |
| [08 — Operación y soporte](docs/08-operacion.md) | Monitoreo, errores comunes, respaldo y retención |
| [09 — Implementación sin PowerShell](docs/09-sin-powershell.md) | **Todo desde el navegador**, sin instalar nada ni ejecutar scripts |
| [Flujos](power-automate/README.md) | Cada flujo acción por acción, para construirlo en el diseñador |
| [Aplicación](canvas-app/README.md) | Cómo empaquetar o reconstruir la app, y qué queda pendiente |

---

## Estado de lo entregado

| Componente | Verificación |
|---|---|
| Scripts de SharePoint | Sintaxis validada con el parser de PowerShell 7.4 |
| Definiciones de flujos | 0 errores en `validate-flows.py`; probado con defectos inyectados |
| Empaquetador de flujos | Ejecutado de extremo a extremo; salida verificada |
| Código fuente de la app | 0 errores y 0 avisos en `validate-canvas-yaml.py` |
| Coherencia entre capas | 0 discrepancias en `check-consistency.py` |

**Nada de esto se ha ejecutado contra un tenant real de Microsoft 365**, porque
no había uno disponible. Dos puntos concretos que hay que verificar al desplegar,
ambos señalados en su documentación:

- Los `operationId` del **conector de DocuSign** cambian entre versiones
  ([`docs/07-docusign.md`](docs/07-docusign.md)). El resto de los flujos 02 y 03
  no depende de ello.
- El formato **YAML del código fuente de las apps de lienzo** sigue evolucionando
  y `pac canvas pack` es sensible a la versión del CLI
  ([`canvas-app/README.md`](canvas-app/README.md)). Hay un camino alternativo
  documentado.
