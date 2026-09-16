# Aplicación de lienzo «Contratos»

Siete pantallas sobre las listas de SharePoint, con el workflow de aprobación
disparado desde la ficha del contrato.

```
scrInicio        Tablero: indicadores, mis aprobaciones, próximos vencimientos
scrBandeja       Búsqueda y listado con filtros delegados
scrDetalle       Ficha del contrato con seis pestañas
scrEditar        Alta y edición, con validaciones previas al guardado
scrAprobaciones  Seguimiento de lo pendiente y control de SLA
scrCustodia      Cadena de custodia del original: recepción, préstamo, devolución
scrAdmin         Matriz de aprobación, parámetros, áreas y simulador de ruta
```

---

## Qué hay en esta carpeta

| Ruta | Contenido |
|---|---|
| `src/App.fx.yaml` | Objeto App: `OnStart`, tema y variables globales |
| `src/Screens/*.fx.yaml` | Una pantalla por archivo: controles, posiciones y fórmulas |
| `formulas/` | **Las fórmulas comentadas, agrupadas por pantalla.** Es la referencia de trabajo |

`formulas/` y `src/` describen lo mismo. La diferencia es para qué sirve cada
uno: el YAML es el código fuente versionable, y `formulas/` explica **por qué**
cada fórmula está escrita así — sobre todo dónde y cómo se preserva la
delegación a SharePoint, que es lo que decide si la app sigue funcionando cuando
haya 8 000 contratos en lugar de 80.

| Documento | Cubre |
|---|---|
| [`formulas/00-app-y-tema.md`](formulas/00-app-y-tema.md) | `OnStart`, tema, roles, fórmulas reutilizables y **las reglas de delegación** |
| [`formulas/01-inicio-y-bandeja.md`](formulas/01-inicio-y-bandeja.md) | Tablero y listado con filtros |
| [`formulas/02-detalle-y-edicion.md`](formulas/02-detalle-y-edicion.md) | Ficha, barra de acciones, envío a aprobación, renovación y formulario |
| [`formulas/03-aprobaciones-y-custodia.md`](formulas/03-aprobaciones-y-custodia.md) | Seguimiento de aprobaciones y movimientos de custodia |
| [`formulas/04-administracion.md`](formulas/04-administracion.md) | Matriz, parámetros, áreas y simulador de ruta |

---

## Cómo construir la app

Hay dos caminos. **El segundo es el recomendado** para la primera vez.

### Camino A · Empaquetar el código fuente

```bash
pac canvas pack --sources ./src --msapp ./Contratos.msapp
```

Luego, en Power Apps: **Aplicaciones → Importar aplicación de lienzo →
`Contratos.msapp`**, y reconectar los orígenes de datos.

> **Antes de intentarlo, lee esto.** El formato YAML del código fuente de las
> aplicaciones de lienzo **sigue evolucionando** y `pac canvas pack` es
> sensible a la versión de Power Platform CLI. Este código fuente **no se ha
> empaquetado contra un entorno real**: se validó su estructura, no su
> compatibilidad con tu versión de `pac`.
>
> Comprueba tu versión con `pac help` y, si el empaquetado falla, no pierdas
> tiempo peleando con el formato: usa el camino B y aprovecha el YAML como
> especificación de la interfaz (qué control, dónde, con qué fórmula).

Validación previa recomendada:

```bash
python3 ../tools/validate-canvas-yaml.py
```

Comprueba que el YAML es válido, que toda fórmula empieza por `=`, que los
paréntesis están balanceados, que no hay controles duplicados y que ninguna
pantalla queda inalcanzable.

### Camino B · Construir en Power Apps Studio

Es más trabajo la primera vez, pero no depende de la versión del CLI y deja la
app en el estado que Studio espera.

1. **Crear la app**: Power Apps → *Crear* → *Aplicación en blanco* → formato
   *Tableta*. Nómbrala `Contratos`.

2. **Conectar los datos**: *Datos* → *Agregar datos* → *SharePoint* → el sitio →
   selecciona las 10 listas
   (`Contratos`, `DocumentosContratos`, `MatrizAprobacion`, `Aprobaciones`,
   `Adendas`, `MovimientosCustodia`, `Areas`, `Parametros`, `Alertas`,
   `Bitacora`).

3. **Conectar los conectores**: `Office365Users` y `Office365Outlook`.

4. **Agregar el flujo**: *Power Automate* → *Contratos - Solicitud de
   aprobación*. Al agregarlo, Power Apps le da un nombre interno; comprueba cuál
   es y ajusta la llamada en `scrDetalle` si no coincide con
   `'Contratos-SolicitudDeAprobacion'.Run(...)`.

5. **Pegar el `OnStart`** de `formulas/00-app-y-tema.md` en la propiedad
   `OnStart` de la App, y ejecutarlo una vez (*⋯ → Ejecutar OnStart*).

6. **Crear las siete pantallas** con los nombres exactos de arriba, y para cada
   una copiar las fórmulas de su archivo en `formulas/`. Empieza por `scrInicio`
   y `scrBandeja`: con esas dos ya se puede probar contra datos reales.

7. **`scrEditar`**: agrega un control *Formulario de edición*, asígnale
   `Contratos` como origen y `gblContrato` como elemento, y elige los campos.
   Las tarjetas de datos las genera Studio; solo hay que aplicarles los
   `Default` y `Visible` de `formulas/02-detalle-y-edicion.md`.

---

## Qué hace falta decidir antes de usarla

| Punto | Por qué |
|---|---|
| `ADMINS`, `CUSTODIOS`, `LEGAL` en la lista `Parametros` | Están **vacíos** tras el despliegue. Sin ellos la app oculta la administración y los botones de custodia para todos. |
| Colores de `gblTema` | Los tres primeros (`Primario`, `PrimarioOscuro`, `PrimarioSuave`) son un azul neutro de ejemplo. |
| Nombre interno del flujo | Power Apps lo deriva del nombre visible; verifica el que te asigna. |

---

## Subida de documentos: la decisión pendiente

El control **Adjuntar archivo** de Power Apps solo escribe en los *datos
adjuntos* de un elemento de lista. **No** puede subir a una biblioteca de
documentos con metadatos, que es lo que necesita `DocumentosContratos`.

Tres opciones, de menor a mayor esfuerzo:

1. **Control «Vista de lista de SharePoint»** incrustado en la pestaña
   Documentos, apuntando a la biblioteca filtrada por el contrato. El usuario
   sube y edita los metadatos con la interfaz nativa de SharePoint. Es lo más
   rápido y lo que menos puede romperse.

2. **Botón que abre la biblioteca** en una pestaña nueva con
   `Launch("…/DocumentosContratos?viewid=…")`. Más simple todavía, pero saca al
   usuario de la app.

3. **Flujo instantáneo de subida**: un control *Adjuntar archivo* que pasa el
   contenido en base64 a un flujo que lo escribe en la biblioteca y le pone los
   metadatos. Es la experiencia más integrada y la de más mantenimiento.

Esta decisión no está tomada en el código porque depende de cuánto pesa la
comodidad frente al mantenimiento en tu caso. La opción 1 es la recomendada
para arrancar.

---

## Pendiente

- **`scrAdenda`** (alta y edición de adendas) está especificada en
  `formulas/02-detalle-y-edicion.md` pero **no** implementada en el YAML. La
  pestaña Adendas de `scrDetalle` lista las existentes; crearlas requiere esa
  pantalla, o hacerlo desde SharePoint mientras tanto.
- El filtro **«Solo los míos»** de la bandeja no se delega (`ResponsableContrato`
  es columna de persona). En `formulas/01-inicio-y-bandeja.md` está explicado el
  arreglo limpio: una columna de texto `ResponsableEmail` indexada, mantenida por
  el flujo.
