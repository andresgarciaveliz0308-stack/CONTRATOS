# 90 · Crear listas y columnas

Flujo de aprovisionamiento. Crea las **13 listas** y las **134 columnas** del
sistema llamando a la API REST de SharePoint, sin PowerShell y sin la consola
del navegador.

Existe para un caso concreto: **construir todo desde una tablet**, donde no hay
F12. En una computadora es más simple usar
[`sharepoint/crear-listas.js`](../../sharepoint/crear-listas.js), que hace lo
mismo pegándolo en la consola.

> No se genera a mano. Sale de `Deploy-Contratos.ps1`:
> ```bash
> python3 tools/generar-flujo-listas.py
> ```

---

## Importarlo

1. [make.powerautomate.com](https://make.powerautomate.com) → **Mis flujos**
2. **Importar → Paquete de importación (heredado)**
3. Sube `power-automate/build/90-crear-listas.zip`
4. En *Configuración relacionada*, asigna tu conexión de **SharePoint**
5. **Importar**, y abre el flujo

## Ejecutarlo

**Ejecutar** → pide una sola cosa: la **URL del sitio**
(`https://TU-TENANT.sharepoint.com/sites/Contratos`). Tarda unos minutos: son
147 llamadas en serie.

> **Pruébalo primero en un sitio de prueba.** Crea `/sites/ContratosPrueba`,
> ejecútalo ahí y comprueba un par de nombres internos antes de hacerlo en el
> definitivo.

## Volver a ejecutarlo es seguro

Las listas y columnas que ya existen hacen fallar **su** iteración, no el flujo:
la siguiente acción corre igual porque su `runAfter` acepta `Failed`. En el
historial verás iteraciones en rojo con *"already exists"* — es lo esperado.

Lo que importa al terminar es que no haya errores **distintos** de ese.

---

## Por qué está armado así

**`Options = 8` (`AddFieldInternalNameHint`).** Sin ese parámetro, la propia API
descarta el nombre interno del XML y usa el visible, generando
`Nombre_x0020_del_x0020_contrato`. Es la razón de ser de todo el flujo: es lo
que garantiza que las fórmulas encuentren sus columnas.

**Los cuerpos van como objeto JSON, no como texto concatenado.** El Field XML
está lleno de comillas; construirlo con `concat` y `string()` produce JSON
inválido, porque `string()` no escapa nada. Pasándolo como objeto, el motor
serializa y escapa por nosotros.

**`"@expr"` y no `"@{expr}"` donde importa el tipo.** El primero conserva el
tipo; el segundo convierte a texto. `BaseTemplate` debe llegar como número y
`EnableVersioning` como booleano.

**Los lookups no pueden llevar el GUID de antemano.** El `List` de un campo de
búsqueda exige el GUID de la lista destino, que no existe hasta haberla creado.
Por eso el XML trae tokens (`__ID_CONTRATOS__`) y cuatro acciones `Id_*` leen
los GUID reales tras la creación; el `replace` los sustituye en ejecución.

**Concurrencia 1 en los dos bucles.** En paralelo, SharePoint rechaza
creaciones simultáneas de columnas sobre la misma lista.

---

## Estructura

| Acción | Qué hace |
|---|---|
| `Ejecutar_manualmente` | Pide la URL del sitio |
| `Las_listas` | Las 13 listas, como datos |
| `Crear_las_listas` | `POST _api/web/lists` por cada una |
| `Id_Areas` … `Id_Campos` | Leen el GUID de las 4 listas que reciben búsquedas |
| `Los_campos` | Las 134 columnas con su Field XML |
| `Crear_las_columnas` | `POST …/fields/createfieldasxml` con `Options=8` |

## Si la importación falla

El formato de paquete no está garantizado por Microsoft. Son 8 acciones: se
arma a mano en el diseñador siguiendo la tabla de arriba, con
`definition.json` de esta carpeta como referencia de las expresiones exactas.

## Verificación

Las expresiones se simularon sobre las 147 llamadas: todos los cuerpos
serializan como JSON válido, `BaseTemplate` llega como número,
`EnableVersioning` como booleano, y los 13 lookups reciben un GUID real.

**No se ha ejecutado contra un tenant real de Microsoft 365**, igual que el
resto del repositorio.
