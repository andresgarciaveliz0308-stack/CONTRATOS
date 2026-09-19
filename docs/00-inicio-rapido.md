# 00 — Inicio rápido: 10 pasos para ver la app funcionando

Esta es la versión corta. Cada paso trae el comando o el texto exacto para
copiar y pegar. El objetivo es que en unas 2 horas tengas un contrato real
recorriendo el circuito de aprobación.

> **Esta guía no reemplaza [`03-despliegue.md`](03-despliegue.md).** Es el
> camino rápido para *ver* el sistema funcionando con lo mínimo. Antes de
> usarlo con contratos reales de la empresa, revisa esa guía completa —
> especialmente la sección de permisos y la prueba de extremo a extremo.

> **¿No tienes acceso a PowerShell?** Los pasos 2, 4, 5, 6, 7 y 8 de esta guía
> tienen su equivalente completo en el navegador en
> [`09-sin-powershell.md`](09-sin-powershell.md). Los pasos 9 y 10 —construir la
> app y probarla— no cambian: siempre fueron navegador puro.

Antes de empezar, reemplaza estos tres valores en tu cabeza (o pégalos en un
bloc de notas) — van a repetirse en casi todos los comandos:

| Marcador | Tu valor | Ejemplo |
|---|---|---|
| `TU-TENANT` | El nombre de tu organización en Microsoft 365 | `abmauriperu` |
| `TU-CORREO` | Tu correo de administrador de ese tenant | `admin@abmauriperu.onmicrosoft.com` |
| `TU-CLIENT-ID` | Lo obtienes en el **paso 4** — solo se saca una vez | `a1b2c3d4-...` |

---

## Paso 1 — Consigue un tenant de prueba (gratis, sin tarjeta)

Si ya tienes acceso al tenant corporativo con permisos de administrador,
sáltate este paso. Si no, pide el tuyo propio:

👉 **[developer.microsoft.com/microsoft-365/dev-program](https://developer.microsoft.com/microsoft-365/dev-program)**
→ *Join now* → sigue el registro con cualquier correo. En unos minutos te da
un tenant de prueba (`TU-TENANT.onmicrosoft.com`) con SharePoint, Power Apps y
Power Automate reales, gratis mientras lo uses activamente.

---

## Paso 2 — Instala las herramientas en tu computadora

Necesitas **PowerShell 7** y el módulo de conexión a SharePoint. Si usas
Windows, PowerShell 7 se instala desde
[aka.ms/powershell-release?tag=stable](https://aka.ms/powershell-release?tag=stable).
Luego, en una ventana de PowerShell, copia y pega:

```powershell
Install-Module PnP.PowerShell -Scope CurrentUser
```

Si te pregunta por un repositorio no confiable, responde `S` (Sí).

---

## Paso 3 — Descarga el código

Sin Git instalado, lo más simple es descargar el ZIP:

👉 **[github.com/andresgarciaveliz0308-stack/CONTRATOS/archive/refs/heads/claude/contracts-approvals-app-8bkb1m.zip](https://github.com/andresgarciaveliz0308-stack/CONTRATOS/archive/refs/heads/claude/contracts-approvals-app-8bkb1m.zip)**

Descomprímelo en una carpeta fácil de encontrar, por ejemplo `C:\Contratos`.

Si prefieres Git:

```powershell
git clone --branch claude/contracts-approvals-app-8bkb1m https://github.com/andresgarciaveliz0308-stack/CONTRATOS.git
cd CONTRATOS
```

---

## Paso 4 — Autoriza la conexión (una sola vez por tenant)

Abre PowerShell **dentro de la carpeta del código** (`cd C:\Contratos\...`) y
pega:

```powershell
Register-PnPEntraIDAppForInteractiveLogin -ApplicationName "PnP - Contratos" -Tenant "TU-TENANT.onmicrosoft.com" -Interactive
```

Se abrirá el navegador pidiéndote iniciar sesión con `TU-CORREO`. Al terminar,
la consola imprime un **ClientId** — cópialo, es el que usarás en todos los
comandos siguientes como `TU-CLIENT-ID`.

---

## Paso 5 — Crea el sitio y las 13 listas de SharePoint

```powershell
cd sharepoint

./Deploy-Contratos.ps1 -SiteUrl "https://TU-TENANT.sharepoint.com/sites/Contratos" -CreateSite -Owner "TU-CORREO" -ClientId "TU-CLIENT-ID"
```

Tarda 3–5 minutos. Al final debe decir «Aprovisionamiento terminado». Si algo
falla a mitad de camino, vuelve a correr el mismo comando: es seguro
repetirlo, retoma donde se quedó.

---

## Paso 6 — Configura los permisos

```powershell
./Set-Permissions.ps1 -SiteUrl "https://TU-TENANT.sharepoint.com/sites/Contratos" -ClientId "TU-CLIENT-ID"
```

Crea los grupos de seguridad. Como estás probando solo, no hace falta agregar
gente todavía — sáltate esa parte por ahora.

---

## Paso 7 — Carga datos de ejemplo

```powershell
./Seed-DemoData.ps1 -SiteUrl "https://TU-TENANT.sharepoint.com/sites/Contratos" -ClientId "TU-CLIENT-ID" -IncluirContratosDemo
```

Esto deja 5 contratos de prueba, categorías (Logística, Comercial, RRHH...) y
una matriz de aprobación de ejemplo. **Antes de continuar**, ve al sitio de
SharePoint → lista **Parametros** y completa estas tres filas con tu propio
correo (para que la app te reconozca como administrador):

| Fila | Valor a escribir |
|---|---|
| `ADMINS` | `TU-CORREO` |
| `CUSTODIOS` | `TU-CORREO` |
| `LEGAL` | `TU-CORREO` |

---

## Paso 8 — Prepara e importa los flujos de Power Automate

```powershell
cd ../power-automate
./Build-Package.ps1 -SiteUrl "https://TU-TENANT.sharepoint.com/sites/Contratos" -Empaquetar
```

Esto deja listos 6 archivos `.zip` en `power-automate/build/`. Para empezar,
importa solo estos dos (los demás se agregan después, ver
`docs/03-despliegue.md`):

1. Entra a **[make.powerautomate.com](https://make.powerautomate.com)** con
   `TU-CORREO`.
2. **Mis flujos → Importar → Paquete de importación (heredado)**.
3. Selecciona `05-numeracion-contrato.zip` → asigna la conexión de
   SharePoint que te pida → **Importar**.
4. Repite con `01-solicitud-aprobacion.zip` (esta vez también te pedirá la
   conexión de **Approvals** y de **Office 365 Outlook**).
5. Abre cada flujo importado y actívalo (interruptor arriba a la derecha).

> Si la importación del `.zip` falla (el formato de paquete no está
> garantizado por Microsoft), no te frenes: en `power-automate/README.md`
> está cada flujo descrito acción por acción para armarlo a mano en el
> diseñador — toma más tiempo pero funciona siempre.

---

## Paso 9 — Construye la app en Power Apps (web)

Entra a **[make.powerapps.com](https://make.powerapps.com)** con `TU-CORREO`
— **usa el navegador, no la app de escritorio**.

1. **Crear → Aplicación en blanco → formato Tableta.** Nómbrala `Contratos`.
2. **Datos → Agregar datos → SharePoint** → pega la URL de tu sitio → marca
   las 13 listas (`Contratos`, `DocumentosContratos`, `MatrizAprobacion`,
   `Aprobaciones`, `Adendas`, `MovimientosCustodia`, `Areas`, `Parametros`,
   `Alertas`, `Bitacora`, `Categorias`, `CamposPersonalizados`,
   `ContratosCamposValor`) → **Conectar**.
3. **Datos → Agregar datos** de nuevo → busca y agrega `Office 365 Users` y
   `Office 365 Outlook`.
4. **Power Automate** (menú izquierdo) → agrega el flujo que importaste en
   el paso 8 (*Contratos - Solicitud de aprobación*).
5. Clic en **App** (el árbol de la izquierda) → propiedad **OnStart** → pega
   exactamente esto:

   ```powerfx
   Set(gblUsuario, User());
   Set(gblHoy, Today());

   ClearCollect(colParametros, Parametros);

   Set(gblTCUSD, Coalesce(Value(LookUp(colParametros, Title = "TC_USD", Valor), "en-US"), 1));
   Set(gblTCEUR, Coalesce(Value(LookUp(colParametros, Title = "TC_EUR", Valor), "en-US"), 1));
   Set(gblMonedaBase, Coalesce(LookUp(colParametros, Title = "MONEDA_BASE", Valor), "PEN"));
   Set(gblDiasPreavisoDefault, Coalesce(Value(LookUp(colParametros, Title = "DIAS_PREAVISO_DEFAULT", Valor), "en-US"), 30));
   Set(gblDocuSignHabilitado, Lower(Coalesce(LookUp(colParametros, Title = "DOCUSIGN_HABILITADO", Valor), "false")) = "true");

   Set(gblEsAdmin, gblUsuario.Email in Split(Coalesce(LookUp(colParametros, Title = "ADMINS", Valor), ""), ";").Value);
   Set(gblEsCustodio, gblEsAdmin || gblUsuario.Email in Split(Coalesce(LookUp(colParametros, Title = "CUSTODIOS", Valor), ""), ";").Value);
   Set(gblEsLegal, gblEsAdmin || gblUsuario.Email in Split(Coalesce(LookUp(colParametros, Title = "LEGAL", Valor), ""), ";").Value);

   ClearCollect(colAreas, Filter(Areas, Activo = true));
   ClearCollect(colCategorias, Filter(Categorias, Activo = true));

   ClearCollect(colEstadosFiltro,
       {Valor: "(Todos)"}, {Valor: "Borrador"}, {Valor: "En revision legal"},
       {Valor: "En aprobacion"}, {Valor: "Aprobado"}, {Valor: "En firma"},
       {Valor: "Vigente"}, {Valor: "Por vencer"}, {Valor: "Vencido"},
       {Valor: "Renovado"}, {Valor: "Terminado"}, {Valor: "Rechazado"},
       {Valor: "Anulado"});

   Set(gblTema, {
       Primario:        RGBA(104, 16, 41, 1),
       PrimarioOscuro:  RGBA(78, 12, 31, 1),
       PrimarioSuave:   RGBA(255, 244, 230, 1),
       Acento:          RGBA(255, 153, 6, 1),
       Fondo:           RGBA(242, 237, 232, 1),
       Tarjeta:         RGBA(255, 255, 255, 1),
       Borde:           RGBA(230, 221, 213, 1),
       Texto:           RGBA(44, 26, 14, 1),
       TextoSuave:      RGBA(122, 106, 95, 1),
       TextoClaro:      RGBA(255, 255, 255, 1),
       Exito:           RGBA(55, 86, 35, 1),
       Advertencia:     RGBA(201, 138, 0, 1),
       Error:           RGBA(192, 0, 0, 1),
       Info:            RGBA(168, 105, 43, 1),
       Fuente:          "'Segoe UI', Arial, sans-serif",
       Radio:           8,
       Espaciado:       16,
       FuenteTitulo:    20,
       FuenteBase:      14,
       FuenteMenor:     12
   })
   ```

6. Arriba a la izquierda, en la barra de fórmulas, hay un botón **▷** junto al
   nombre de la propiedad — o usa el menú **⋯ → Ver → Ejecutar OnStart**.
   Ejecútalo una vez para que las variables se carguen.
7. Crea una pantalla nueva, ponle el nombre exacto `scrInicio`, y copia ahí
   las fórmulas de
   [`canvas-app/formulas/01-inicio-y-bandeja.md`](../canvas-app/formulas/01-inicio-y-bandeja.md)
   (sección *scrInicio*). Con esa única pantalla ya puedes ver los
   indicadores con datos reales de tu sitio.

> Construir las 7 pantallas completas lleva más de un paso — es intencional.
> El resto de las pantallas y el orden recomendado para armarlas están en
> [`canvas-app/README.md`](../canvas-app/README.md), *Camino B*.

---

## Paso 10 — Prueba de punta a punta

1. En SharePoint (o ya en la app cuando la termines), abre la lista
   **Contratos** y crea un registro nuevo: nombre, tipo `Servicios`, monto
   `25000`, moneda `PEN`, fecha de inicio hoy, fecha de fin en un año.
2. Espera un minuto y refresca: debe aparecer un código `CTR-2026-0006` (el
   flujo 05 se lo asignó solo).
3. Cambia su **Estado** a `Aprobado`... en realidad no: para probar el
   circuito real, hazlo desde la app con el botón **Enviar a aprobación** una
   vez que tengas `scrDetalle` construida — o, para probar el flujo ya
   mismo sin esperar a terminar la app, ve a **Power Automate → tu flujo 01 →
   Probar → Probar manualmente**, y pásale el `ID` de este contrato.
4. Revisa que llegue una tarjeta de aprobación a tu correo o a
   [Aprobaciones de Power Automate](https://make.powerautomate.com/environments/~default/approvals/received).
5. Apruébala. El contrato debe pasar a estado `Aprobado`.

Si llegaste hasta aquí con el contrato aprobado, **el sistema funciona de
punta a punta**. Lo que sigue —firma con DocuSign, alertas de vencimiento,
custodia, las pantallas restantes de la app— está en
[`03-despliegue.md`](03-despliegue.md) y no bloquea nada de lo ya probado.

---

## Si algo falla

| Síntoma | Revisa |
|---|---|
| `Deploy-Contratos.ps1` da error de conexión | ¿Usaste el `ClientId` del paso 4, no lo inventaste? |
| El contrato no recibe código | ¿Activaste el flujo 05 (interruptor arriba a la derecha)? |
| La app dice «No tienes acceso a la administración» | ¿Completaste `ADMINS` en `Parametros` con tu correo exacto (el paso 7)? |
| No llega la tarjeta de aprobación | ¿El área del contrato tiene `Responsable` asignado en la lista `Areas`? |

Para cualquier otra cosa, la tabla de diagnóstico completa está en
[`08-operacion.md`](08-operacion.md).
