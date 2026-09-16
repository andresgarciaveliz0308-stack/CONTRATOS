# 03 — Despliegue paso a paso

Tiempo estimado: **2–3 horas** la primera vez, sin contar la construcción de la
app en Studio si se elige ese camino.

---

## 0. Requisitos previos

| Requisito | Detalle |
|---|---|
| PowerShell 7+ | `pwsh --version` |
| Módulo PnP.PowerShell | `Install-Module PnP.PowerShell -Scope CurrentUser` |
| Permisos | Administrador de la colección de sitios (o de SharePoint si se crea el sitio) |
| Licencia | Power Automate Premium **solo** si se usará DocuSign |
| Cuenta de servicio | Recomendada para ser dueña de los flujos (ver paso 4) |
| Power Platform CLI | Opcional, solo para el camino A de la app |

### Registro de la aplicación de Entra ID (PnP)

Desde PnP.PowerShell 2.x la conexión interactiva exige un `ClientId` propio. Una
sola vez por tenant:

```powershell
Register-PnPEntraIDAppForInteractiveLogin `
    -ApplicationName "PnP PowerShell - Contratos" `
    -Tenant "contoso.onmicrosoft.com" `
    -Interactive
```

Guarda el `ClientId` que devuelve: se pasa a los tres scripts con `-ClientId`.

---

## 1. Crear el sitio y las listas

```powershell
cd sharepoint

./Deploy-Contratos.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
    -CreateSite `
    -Owner "admin@contoso.com" `
    -ClientId "<tu-client-id>"
```

Si el sitio ya existe, omite `-CreateSite` y `-Owner`.

El script es idempotente: si algo falla a mitad, se vuelve a ejecutar y continúa
donde estaba. Al terminar informa cuántos elementos creó y cuántos ya existían.

**Verificación.** Abre el sitio y comprueba que existen las 10 listas y que
`Contratos` tiene ~45 columnas. Si alguna columna aparece con `[!]` en la salida
del script, revísala a mano antes de seguir.

---

## 2. Configurar permisos

```powershell
./Set-Permissions.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
    -ClientId "<tu-client-id>"
```

Crea seis grupos y dos niveles de permiso personalizados. **No agrega usuarios**:
eso se hace a mano porque depende de decidir quién es quién.

Después, en **Configuración del sitio → Permisos del sitio**, agrega las personas
a cada grupo:

| Grupo | Quiénes |
|---|---|
| `Contratos - Administradores` | Responsables del sistema **y la cuenta de servicio de los flujos** |
| `Contratos - Legal` | Área legal |
| `Contratos - Aprobadores` | Todos los que aparecen en la matriz de aprobación |
| `Contratos - Custodios` | Archivo / gestión documental |
| `Contratos - Solicitantes` | Quienes registran contratos |
| `Contratos - Consulta` | Consulta de solo lectura |

> **Crítico:** la cuenta que será dueña de los flujos debe estar en
> `Contratos - Administradores`. Los flujos escriben en `Aprobaciones` y
> `Bitacora`, que son de solo lectura para todos los demás. Si se omite, los
> flujos fallarán con error 403 al registrar una decisión.

Detalle del modelo de permisos en [`05-seguridad-permisos.md`](05-seguridad-permisos.md).

---

## 3. Cargar los datos iniciales

```powershell
./Seed-DemoData.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
    -ClientId "<tu-client-id>"
```

Agrega `-IncluirContratosDemo` para cargar 5 contratos de prueba (dos de ellos
dentro del periodo de preaviso, útiles para probar el flujo 04). **No lo uses en
producción.**

### Ajustes obligatorios después de cargar

1. **`Areas`** — asigna `Responsable` y `Gerente` en cada área. De ahí salen los
   aprobadores de los roles *Jefe de área* y *Gerente de área*. Un área sin
   responsable detiene cualquier contrato de esa área.

2. **`MatrizAprobacion`** — revisa los tramos de monto (el ejemplo usa
   0–20k / 20k–100k / 100k–500k / 500k+) y completa
   `Aprobador (usuario)` o `Aprobador (grupo)` en las reglas de los roles
   *Legal*, *Finanzas*, *Compras*, *Gerencia General* y *Directorio*. Los roles
   *Jefe de área* y *Gerente de área* se resuelven solos.

3. **`Parametros`** — completa como mínimo:

   | Clave | Qué poner |
   |---|---|
   | `CORREO_ADMIN_CONTRATOS` | Buzón real del administrador |
   | `CORREO_LEGAL` | Buzón real del área legal |
   | `TC_USD`, `TC_EUR` | Tipos de cambio vigentes |
   | `ADMINS` | Correos de administradores, separados por `;` |
   | `CUSTODIOS` | Correos del archivo, separados por `;` |
   | `LEGAL` | Correos de legal, separados por `;` |
   | `DOCUSIGN_HABILITADO` | `false` si aún no vas a usar firma electrónica |

   `ADMINS`, `CUSTODIOS` y `LEGAL` se crean **vacíos**. Mientras lo estén, la app
   oculta la administración y los botones de custodia para todos.

---

## 4. Importar los flujos

### Elegir el dueño

Los flujos deberían pertenecer a una **cuenta de servicio**, no a una persona.
Si pertenecen a alguien que se va de la empresa, se desactivan y el sistema se
detiene sin aviso claro.

La cuenta de servicio necesita:
- Licencia de Power Automate (Premium si se usa DocuSign).
- Pertenecer a `Contratos - Administradores`.
- Conexiones creadas a SharePoint, Office 365 Outlook, Approvals y DocuSign.

### Preparar las definiciones

```powershell
cd ../power-automate

./Build-Package.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
    -DocuSignAccountId "<id-de-cuenta-docusign>" `
    -Empaquetar
```

Reemplaza los marcadores por los valores reales y deja en `build/` las
definiciones sustituidas y los `.zip` de importación.

### Importar

Por cada `.zip`: **Power Automate → Mis flujos → Importar → Paquete de
importación (heredado)**, seleccionar el archivo, asignar cada conexión y
*Importar*.

> El formato de paquete heredado no es un contrato público de Microsoft y cambia
> entre versiones del servicio. **Si la importación es rechazada, no insistas:**
> crea el flujo en el diseñador siguiendo [`../power-automate/README.md`](../power-automate/README.md),
> que lista acción por acción y expresión por expresión, y usa el
> `build/<flujo>/definition.json` como referencia de las fórmulas.

### Orden recomendado

| Orden | Flujo | Probar con |
|---|---|---|
| 1 | 05 Numeración | Crear un contrato: debe recibir `CTR-AAAA-0001` |
| 2 | 01 Solicitud de aprobación | Enviar ese contrato a aprobación |
| 3 | 04 Alertas de vencimiento | Ejecución manual con datos demo |
| 4 | 06 Control de préstamos | Registrar un préstamo con fecha pasada |
| 5 | 02 y 03 DocuSign | Solo cuando DocuSign esté configurado |

Deja los flujos 02 y 03 **desactivados** hasta terminar
[`07-docusign.md`](07-docusign.md).

### Validar antes de importar

```bash
python3 ../tools/validate-flows.py --site-url=definida power-automate/build/*/definition.json
```

Debe informar 0 errores y 0 avisos. Un aviso de marcador pendiente significa que
faltó pasar `-DocuSignAccountId`.

---

## 5. Construir la aplicación

Dos caminos, detallados en [`../canvas-app/README.md`](../canvas-app/README.md):

- **A** — `pac canvas pack` sobre `canvas-app/src`. Rápido, pero depende de la
  versión de Power Platform CLI y **no está verificado contra un entorno real**.
- **B** — construirla en Power Apps Studio con las fórmulas de
  `canvas-app/formulas/`. Más trabajo, sin sorpresas.

Cualquiera de los dos requiere después:

1. Conectar las 10 listas de SharePoint.
2. Agregar los conectores `Office365Users` y `Office365Outlook`.
3. Agregar el flujo *Contratos - Solicitud de aprobación* y **verificar el
   nombre interno** que Power Apps le asigna; ajustar la llamada en `scrDetalle`
   si no coincide con `'Contratos-SolicitudDeAprobacion'.Run(...)`.
4. Ejecutar `OnStart` una vez (*⋯ → Ejecutar OnStart*).
5. Decidir cómo se suben los documentos a la biblioteca (tres opciones evaluadas
   en el README de la app).

---

## 6. Prueba de extremo a extremo

Antes de dar el sistema por operativo, recorre este camino completo:

- [ ] Registrar un contrato de **25 000** en moneda base, tipo *Servicios*.
- [ ] Verificar que recibe código `CTR-AAAA-NNNN` en menos de un minuto.
- [ ] Verificar que `FechaPreaviso` = `FechaFin` − 30 días.
- [ ] Subir un PDF y marcarlo como **documento principal**.
- [ ] Enviar a aprobación. Con el tramo 20k–100k deben resolverse **3 niveles**
      (Jefe de área, Gerente de área, Legal).
- [ ] Comprobar que el nivel 1 recibe la tarjeta de aprobación en Teams o correo.
- [ ] **Rechazar** en el nivel 1. El contrato debe quedar `Rechazado` con el
      motivo, y el solicitante debe recibir el correo.
- [ ] Reenviar. Debe abrirse el **ciclo 2** conservando el historial del ciclo 1.
- [ ] Aprobar los tres niveles. El contrato debe quedar `Aprobado`.
- [ ] Con DocuSign activo: verificar que llega el sobre y que al firmarlo el
      contrato pasa a `Vigente` con el PDF firmado en la biblioteca.
- [ ] Registrar la **recepción del original** y verificar el cambio a *En custodia*.
- [ ] Registrar un **préstamo** con compromiso a 7 días; comprobar que llega el
      cargo por correo.
- [ ] Ejecutar el flujo 04 a mano y verificar que avisa de los contratos dentro
      del preaviso y **no** repite el aviso en una segunda ejecución.

El último punto es el que más veces se pasa por alto y el que más ruido genera
en producción.

---

## Problemas frecuentes

| Síntoma | Causa habitual | Solución |
|---|---|---|
| El contrato no recibe código | Flujo 05 desactivado, o `Title` ya venía informado | Revisar el historial de ejecuciones del flujo 05 |
| «No hay reglas de aprobación configuradas» | Ningún tramo de `MatrizAprobacion` cubre ese monto y tipo | Usar el simulador de `scrAdmin` para reproducirlo |
| El flujo se detiene en un nivel | Regla sin aprobador, o área sin `Responsable`/`Gerente` | El aviso de `scrAdmin` las lista |
| Error 403 al escribir en `Aprobaciones` | La cuenta dueña de los flujos no está en `Contratos - Administradores` | Agregarla al grupo |
| La app avisa de delegación | Se agregó un filtro sobre columna no indexada | Ver las reglas en `canvas-app/formulas/00-app-y-tema.md` |
| Los montos se leen mal (3.75 → 375) | `Value()` sin `"en-US"` en un equipo en español | Ya contemplado en `OnStart`; revisar fórmulas agregadas después |
| Alertas duplicadas | La lista `Alertas` se vació a mano | El antiduplicado depende de esa lista: no borrarla |
