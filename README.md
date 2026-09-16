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
| **Custodia documental** | Biblioteca versionada para el digital + trazabilidad del **original físico** (ubicación, custodio, préstamos y devoluciones). |
| **Workflow de aprobaciones** | Matriz de aprobación **configurable por tipo de contrato y monto**, multinivel y secuencial, con historial completo e inmutable. |
| **Firma electrónica** | Envío automático a DocuSign al aprobarse; el sobre firmado regresa solo al expediente. |
| **Control de vencimientos** | Alertas por correo y Teams con N días de preaviso, incluyendo renovaciones automáticas y cartas fianza. |

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
│  9 listas de negocio + 1 biblioteca documental versionada     │
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

docs/                Documentación funcional y técnica (español)
```

---

## Despliegue rápido

Requisitos: PowerShell 7+, `PnP.PowerShell`, permisos de administrador del sitio y
licencia de Power Automate con conector premium (DocuSign).

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
| [01 — Arquitectura](docs/01-arquitectura.md) | Componentes, licenciamiento, límites y decisiones de diseño |
| [02 — Modelo de datos](docs/02-modelo-datos.md) | Las 10 listas, cada columna, tipos, opciones y relaciones |
| [03 — Despliegue](docs/03-despliegue.md) | Instalación paso a paso de extremo a extremo |
| [04 — Workflow de aprobaciones](docs/04-flujos-aprobacion.md) | Matriz configurable, niveles, SLA, delegación y reproceso |
| [05 — Seguridad y permisos](docs/05-seguridad-permisos.md) | Grupos, roles, confidencialidad y permisos a nivel de elemento |
| [06 — Manual de usuario](docs/06-manual-usuario.md) | Guía para solicitantes, aprobadores y custodios |
| [07 — Integración DocuSign](docs/07-docusign.md) | Cuenta, conector, plantillas y mapeo de firmantes |
| [08 — Operación y soporte](docs/08-operacion.md) | Monitoreo, errores comunes, respaldo y retención |
