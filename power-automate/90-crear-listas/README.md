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
4. En **Related resources**, la fila *SharePoint* sale **en rojo** con
   *«Select during import»*. Toca la **llave inglesa** 🔧 de esa fila, elige tu
   conexión de SharePoint y **Guardar**.
5. Recién ahí se habilita **Import**.

> **El botón Import está gris hasta que la fila de la conexión pasa de rojo a
> verde.** Es el paso que más confunde: el paquete ya subió bien, pero Power
> Automate no importa nada mientras falte asignar la conexión.
>
> Si en la lista no aparece ninguna conexión de SharePoint, créala primero en
> **Conexiones → + Nueva conexión → SharePoint**, y vuelve a empezar la
> importación.

## Ejecutarlo

**Ejecutar** → pide una sola cosa: la **URL del sitio**
(`https://TU-TENANT.sharepoint.com/sites/Contratos`). Tarda unos minutos: son
147 llamadas en serie.

> **Pruébalo primero en un sitio de prueba.** Crea `/sites/ContratosPrueba`,
> ejecútalo ahí y comprueba un par de nombres internos antes de hacerlo en el
> definitivo.

## Cómo saber si está avanzando

La pantalla de ejecución **no se refresca sola**: los círculos azules siguen
ahí aunque el flujo ya haya terminado. No la mires para medir progreso.

**La comprobación real está en SharePoint:** abre el sitio →
**Contenido del sitio**. Las listas van apareciendo a medida que se crean. Si
en dos refrescos seguidos hay más que antes, está avanzando.

Para el estado oficial: **Mis flujos → el flujo → Historial de ejecuciones**.
Ahí dice *En ejecución*, *Correcto* o *Error*, y se actualiza al recargar.

Tiempos esperables, con concurrencia 1:

| Fase | Llamadas | Aprox. |
|---|---|---|
| Las 13 listas | 13 | menos de 1 min |
| Las 134 columnas | 134 | 3 a 5 min |

Si pasan más de 10 minutos sin que aparezcan listas nuevas, **Cancelar** y
volver a ejecutar: no se pierde nada de lo ya creado.

## Volver a ejecutarlo es seguro

Lo que ya existe falla su llamada, y ese fallo **se absorbe**: dentro de cada
bucle, la acción HTTP va seguida de un `Compose` cuyo `runAfter` acepta
`Failed`, de modo que la iteración termina bien y el bucle sigue con la
siguiente.

> **Por qué hace falta.** Una iteración cuya última acción falla **aborta el
> resto del bucle**. Sin ese `Compose`, encontrar una sola lista ya existente
> detenía la creación de todas las demás.

En el historial verás en rojo las llamadas de lo que ya existía, con
*"already exists"*. Es lo esperado. Lo que importa es que no haya errores
**distintos** de ese.

---

## Por qué está armado así

**`Options = 8` (`AddFieldInternalNameHint`).** Sin ese parámetro, la propia API
descarta el nombre interno del XML y usa el visible, generando
`Nombre_x0020_del_x0020_contrato`. Es la razón de ser de todo el flujo: es lo
que garantiza que las fórmulas encuentren sus columnas.

**El cuerpo se arma completo al generar el flujo y viaja como texto.** El campo
*Body* de esta acción **es texto**. Si se le pasa un objeto, el motor lo
serializa y las expresiones de dentro pierden el tipo: `BaseTemplate` sale como
`"100"` y SharePoint responde

```
No se puede convertir un valor primitivo en el tipo esperado 'Edm.Int32'
```

Por eso `Las_listas` y `Los_campos` ya traen cada cuerpo serializado, con los
números y booleanos literales. El flujo solo los pasa. Tampoco sirve
concatenarlos con `concat` y `string()`: el Field XML está lleno de comillas y
`string()` no escapa nada, así que produciría JSON inválido en las 134
columnas.

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

## La estructura del paquete

Microsoft no documenta este formato. Está calcado de un paquete realmente
exportado desde Power Automate:

```
manifest.json
Microsoft.Flow/flows/manifest.json
Microsoft.Flow/flows/<flowId>/apisMap.json
Microsoft.Flow/flows/<flowId>/connectionsMap.json
Microsoft.Flow/flows/<flowId>/definition.json
```

Una primera versión dedujo la estructura y falló con `MissingPackageManifest`.
Faltaban tres archivos, y el más importante no era el que nombraba el error:
el `manifest.json` de la raíz declara **tres** recursos, no dos. Además del
flujo y del conector (`Microsoft.PowerApps/apis`) hace falta uno de tipo
`Microsoft.PowerApps/apis/connections` — **es la fila que se asigna al
importar**. Sin él, *Related resources* aparece vacío y no hay dónde elegir la
conexión. Los dos `*Map.json` son los que enlazan el flujo con esos recursos.

El `metadata` que traen los paquetes exportados lleva identificadores del
tenant y del usuario que exportó. Es estado del entorno, no estructura: aquí se
omite a propósito.

## Si la importación falla

Son 8 acciones: se arma a mano en el diseñador siguiendo la tabla de arriba,
con `definition.json` de esta carpeta como referencia de las expresiones
exactas.

## Verificación

Las expresiones se simularon sobre las 147 llamadas: todos los cuerpos
serializan como JSON válido, `BaseTemplate` llega como número,
`EnableVersioning` como booleano, y los 13 lookups reciben un GUID real.

**No se ha ejecutado contra un tenant real de Microsoft 365**, igual que el
resto del repositorio.
