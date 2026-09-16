# 05 — Categorías, campos dinámicos y vista previa de documentos

Cubre tres piezas nuevas, todas derivadas de la misma decisión de diseño: las
**categorías** (carpetas administrables) llevan colgado un **esquema de campos
configurable**, y las **cláusulas corporativas** son ese mismo mecanismo, no
uno aparte. El razonamiento completo —por qué `Categoria` es independiente de
`TipoContrato`, y qué se puede filtrar rápido y qué no— está en
[`docs/02-modelo-datos.md`](../../docs/02-modelo-datos.md#categorías-campos-dinámicos-y-el-mecanismo-de-esquema-configurable).

> **Sobre esta pieza en particular.** Es la parte más elaborada de Power Fx de
> toda la app: un formulario dinámico que se arma en tiempo de ejecución según
> la categoría elegida, y que solo puede escribir sus valores **después** de
> que el contrato existe en SharePoint (necesita un `ID` real). Cuando la
> construyas en Studio, pruébala primero con un contrato de un solo campo
> dinámico antes de cargarle el esquema completo — es más fácil detectar un
> error de referencia con poco en juego.

---

## scrBandeja — navegación por carpetas

El panel lateral (`galCategorias`) lista `colCategorias` (cargada una vez en
`App.OnStart`, igual que `colAreas`: es pequeña y estable). Seleccionar una
carpeta o «Todas las categorías» solo cambia `locCategoriaId`; el filtrado
real ocurre en `galContratos.Items`.

### Por qué son 8 ramas y no un único `Filter`

La bandeja ya tenía dos filtros opcionales (Estado, Tipo). Categoría es un
tercero. Cada dimensión opcional duplica los casos: 2³ = 8. Es mecánico, pero
cada rama es un `Filter` con condiciones **ANDadas**, nunca una condición
constante mezclada con una de fila — es la única forma de que las ocho ramas
se sigan delegando al servidor. La alternativa (anidar `If` que decide qué
`Filter` aplicar en cada capa) es más corta de escribir, pero su delegación
depende de que Power Apps propague la delegabilidad a través de una variable
de `With`, algo que no se pudo verificar contra un entorno real; se prefirió
la versión más verbosa pero **probadamente** correcta.

```powerfx
// galContratos.Items (extracto: 2 de las 8 ramas)
Switch(
    (locCategoriaId <> 0) & "|" & (locEstado <> "(Todos)") & "|" & (locTipo <> "(Todos)"),

    "true|true|true",
        Filter(Contratos,
            Categoria.Id = locCategoriaId, Estado.Value = locEstado, TipoContrato.Value = locTipo,
            StartsWith(Title, _buscar) || StartsWith(NombreContrato, _buscar) || StartsWith(Contraparte, _buscar)),

    // ... seis ramas más, una por combinación ...

    Filter(Contratos, StartsWith(Title, _buscar) || StartsWith(NombreContrato, _buscar) || StartsWith(Contraparte, _buscar))
)
```

El texto completo de las 8 ramas está en `canvas-app/src/Screens/scrBandeja.fx.yaml`.

---

## scrEditar — formulario dinámico por categoría

### El problema del orden: no se puede guardar el valor antes de que exista el contrato

`ContratosCamposValor.Contrato` es una búsqueda que exige un `ID` real de
`Contratos`. Un contrato nuevo no tiene `ID` hasta que `SubmitForm(frmContrato)`
lo crea. Por eso el flujo es:

1. Mientras el usuario llena el formulario, sus respuestas a los campos
   dinámicos se guardan en una **colección local** (`colCamposDinamicos`), no
   en SharePoint todavía.
2. Al enviar el formulario principal, `frmContrato.OnSuccess` recibe
   `frmContrato.LastSubmit` — ahí sí hay un `ID`.
3. **Recién ahí** se escribe cada valor pendiente en `ContratosCamposValor`.

### Construir la colección

```powerfx
// scrEditar.OnVisible (además de NewForm/EditForm)
Set(gblCategoriaFormId, Coalesce(gblContrato.Categoria.Id, 0));
ClearCollect(colCamposDinamicos,
    AddColumns(
        Filter(CamposPersonalizados, Activo = true,
            IsBlank(Categoria) || Categoria.Id = gblCategoriaFormId),
        "ValorActual",
        Switch(TipoDato.Value,
            "Booleano", LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorBooleano,
            "Numero",   LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorNumero,
            "Fecha",    LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorFecha,
            LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorTexto
        )
    )
);
```

`IsBlank(Categoria)` incluye los campos globales (las cláusulas corporativas):
se muestran sin importar qué categoría se elija.

### `DataCardValue_Categoria.OnChange` — recalcular al cambiar de carpeta

Esta es la única tarjeta de datos del formulario principal que necesita una
fórmula agregada a mano en Studio (las demás siguen el patrón normal de
`02-detalle-y-edicion.md`). Al elegir o cambiar la categoría:

```powerfx
// DataCardValue_Categoria.OnChange
Set(gblCategoriaFormId, Coalesce(DataCardValue_Categoria.Selected.Id, 0));
ClearCollect(colCamposDinamicos,
    AddColumns(
        Filter(CamposPersonalizados, Activo = true,
            IsBlank(Categoria) || Categoria.Id = gblCategoriaFormId),
        "ValorActual",
        Switch(TipoDato.Value,
            "Booleano", LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorBooleano,
            "Numero",   LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorNumero,
            "Fecha",    LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorFecha,
            LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID).ValorTexto
        )
    )
)
```

> Cambiar de categoría a mitad de la edición de un contrato existente
> **relee** los valores desde `ContratosCamposValor` (no pierde nada: son los
> valores reales guardados). En un contrato nuevo, simplemente no hay nada que
> perder — todo estaba en blanco.

### El panel: un control por tipo de dato

`galCamposDinamicos` dibuja un control distinto según `ThisItem.TipoDato.Value`
y cada uno, en su `OnChange`, escribe **solo en la colección local**:

| `TipoDato` | Control | `OnChange` |
|---|---|---|
| `Texto` | `Classic/TextInput` | `Patch(colCamposDinamicos, ThisItem, {ValorActual: Self.Text})` |
| `Opcion` | `Classic/ComboBox` sobre `Split(ThisItem.Opciones, ";")` | `Patch(colCamposDinamicos, ThisItem, {ValorActual: Self.Selected.Value})` |
| `Numero` | `Classic/TextInput` (`Format: Number`) | `Patch(colCamposDinamicos, ThisItem, {ValorActual: Value(Self.Text)})` |
| `Fecha` | `Classic/DatePicker` | `Patch(colCamposDinamicos, ThisItem, {ValorActual: Self.SelectedDate})` |
| `Booleano` | `Classic/Toggle` | `Patch(colCamposDinamicos, ThisItem, {ValorActual: Self.Value})` |

`Patch` sobre una colección **local** (dos argumentos: colección + registro a
actualizar) no toca SharePoint; solo mantiene sincronizada la fila de
`colCamposDinamicos` que corresponde a ese control.

> **Por qué un campo `Booleano` nunca se guarda "sin querer" en un contrato
> nuevo.** El `Toggle` siempre muestra un valor (encendido o apagado nunca
> "en blanco"), pero eso es solo lo que se **ve**: `ThisItem.ValorActual` en la
> colección permanece `Blank()` hasta que el usuario efectivamente toca el
> control y dispara su `OnChange`. El guardado final filtra por
> `!IsBlank(_c.ValorActual)`, así que una cláusula que nadie marcó no genera
> una fila en `ContratosCamposValor` — queda, correctamente, como «sin
> responder» (ver la pestaña Campos de la ficha, más abajo).

### El guardado real: `frmContrato.OnSuccess`

```powerfx
Set(gblContrato, frmContrato.LastSubmit);
// ... notificaciones y bitácora, sin cambios ...
ForAll(colCamposDinamicos As _c,
    If(!IsBlank(_c.ValorActual),
        With({_existente: LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = _c.ID)},
            Patch(ContratosCamposValor,
                If(IsBlank(_existente), Defaults(ContratosCamposValor), _existente),
                {
                    Title: gblContrato.Title & "-" & _c.Title,
                    Contrato: {Id: gblContrato.ID, Value: gblContrato.Title},
                    Campo: {Id: _c.ID, Value: _c.Title},
                    ValorTexto:    If(_c.TipoDato.Value = "Texto" || _c.TipoDato.Value = "Opcion", Text(_c.ValorActual), Blank()),
                    ValorNumero:   If(_c.TipoDato.Value = "Numero", Value(_c.ValorActual), Blank()),
                    ValorFecha:    If(_c.TipoDato.Value = "Fecha", _c.ValorActual, Blank()),
                    ValorBooleano: If(_c.TipoDato.Value = "Booleano", _c.ValorActual, Blank())
                }
            )
        )
    )
);
Navigate(scrDetalle, ScreenTransition.UnCover)
```

`Patch(Lista, If(IsBlank(_existente), Defaults(Lista), _existente), {...})` es
el patrón «crear si no existe, actualizar si existe» en una sola línea: evita
un `If` separado con dos ramas casi idénticas.

---

## scrDetalle — pestaña «Campos» (solo lectura)

Misma consulta que en `scrEditar`, pero resolviendo directamente el texto a
mostrar en vez de dejar el control editable:

```powerfx
// scrDetalle.OnVisible (dentro del Concurrent)
ClearCollect(colCamposDinamicosD,
    AddColumns(
        Filter(CamposPersonalizados, Activo = true,
            IsBlank(Categoria) || Categoria.Id = Coalesce(gblContrato.Categoria.Id, 0)),
        "ValorMostrado",
        With({_v: LookUp(ContratosCamposValor, Contrato.Id = gblContrato.ID, Campo.Id = ID)},
            Switch(TipoDato.Value,
                "Booleano", If(IsBlank(_v), "Sin responder", If(_v.ValorBooleano, "Sí", "No")),
                "Numero",   If(IsBlank(_v), "-", Text(_v.ValorNumero, "#,##0.00")),
                "Fecha",    If(IsBlank(_v) || IsBlank(_v.ValorFecha), "-", Text(_v.ValorFecha, "dd/mm/yyyy")),
                If(IsBlank(_v) || IsBlank(_v.ValorTexto), "-", _v.ValorTexto)
            )
        )
    )
)
```

Las cláusulas booleanas se colorean con semáforo: **Sí** en verde, **No** en
rojo, **Sin responder** en ámbar — así un contrato con una cláusula
antisoborno sin marcar destaca a simple vista, en vez de perderse entre el
resto de la ficha.

---

## Vista previa de documentos en pantalla

El control nativo **Visor de PDF** de Power Apps (`Insertar → Medios → Visor
de PDF`) no se declara en el YAML del repositorio: su identificador exacto de
control no está verificado contra un entorno real (mismo criterio que las
tarjetas de datos — ver la nota correspondiente en `02-detalle-y-edicion.md`).
En su lugar, `scrDetalle.fx.yaml` deja armado el marco (`recPanelPreview`) y la
fórmula ya resuelta; solo falta:

1. En la pestaña Documentos, insertar el control **Visor de PDF** dentro del
   área de `recPanelPreview` (mismas coordenadas, con ~16 px de margen).
2. Asignarle:

   ```powerfx
   // Document
   =If(EndsWith(Lower(gblDocumentoSeleccionado.'Nombre del archivo con extensión'), ".pdf"),
       gblDocumentoSeleccionado.'Vínculo al elemento', "")

   // Visible
   =locPestana = "Documentos" && !IsBlank(gblDocumentoSeleccionado)
   ```

Seleccionar una fila de `galDocumentos` (o pulsar «Abrir») fija
`gblDocumentoSeleccionado`; el visor se actualiza solo. Para formatos que no
son PDF (Word, Excel), el visor no aplica — se mantiene el botón **Abrir**
como único camino, y `lblPreviewAviso` se lo dice al usuario en vez de dejarlo
adivinar por qué el panel quedó vacío.

---

## scrAdmin — sección «Categorías»

Administra las dos listas nuevas desde la app, sin tocar SharePoint.

### Columna izquierda: categorías

`galCategoriasAdmin` lista `colCategoriasAdmin`; seleccionar una fija
`locCategoriaAdminId`, que decide qué campos se muestran a la derecha.
`frmCategoria` (`DataSource: Categorias`) se abre con **Editar** o
**+ Nueva categoría**, siguiendo el mismo patrón de `frmContrato`:
`NewForm`/`EditForm` según corresponda, `SubmitForm` en el botón Guardar,
`OnSuccess` refresca `colCategoriasAdmin` **y** `colCategorias` (la copia
global que usa el panel de carpetas de `scrBandeja` — si no se refresca esa
también, una categoría recién creada no aparecería en la bandeja hasta la
siguiente sesión).

### Columna derecha: campos de la categoría seleccionada

`galCamposAdmin` filtra `colCamposAdmin` por
`locCategoriaAdminId = 0 || IsBlank(Categoria) || Categoria.Id = locCategoriaAdminId`
— con ninguna categoría elegida, se ven todos los campos de todas; con una
elegida, sus específicos más los globales. El interruptor **Activo** de cada
fila desactiva un campo sin borrar los valores ya cargados en contratos
existentes (coherente con la regla general del modelo de datos: desactivar,
no eliminar).

`frmCampo` (`DataSource: CamposPersonalizados`) sigue el mismo patrón. Al
crear un campo **nuevo** estando una categoría seleccionada, conviene que la
tarjeta de datos de `Categoria` la traiga precargada:

```powerfx
// DataCardValue_Categoria (del formulario frmCampo) · Default
=If(locCategoriaAdminId = 0, Blank(), LookUp(Categorias, ID = locCategoriaAdminId))
```

Así el administrador no tiene que volver a elegir la categoría que ya estaba
mirando.

---

## Pendiente conocido: `frmRegla` (matriz de aprobación)

Al construir esta sección se detectó que `canvas-app/formulas/04-administracion.md`
documenta un formulario `frmRegla` para el alta y edición de reglas de
`MatrizAprobacion` que **nunca se declaró** en `scrAdmin.fx.yaml` — hoy esa
sección es de solo lectura (activar/desactivar reglas existentes, más el
simulador). No es parte de este cambio: cambiar la matriz de aprobación es más
sensible que agregar un campo dinámico, y mezclar ambas cosas en la misma
edición habría hecho más difícil revisar cada una por separado. Queda anotado
para una próxima iteración, siguiendo exactamente el mismo patrón que
`frmCategoria`/`frmCampo` de este documento.
