# scrInicio y scrBandeja

---

# scrInicio — tablero

Vista de entrada. Cuatro indicadores, accesos rápidos y las dos listas que
exigen acción: lo que el usuario debe aprobar y lo que está por vencer.

## scrInicio.OnVisible

```powerfx
// Los indicadores se calculan sobre colecciones ya filtradas por el servidor:
// CountRows() y Sum() no se delegan a SharePoint, así que nunca se ejecutan
// contra la lista completa.
Concurrent(
    // Contratos por vencer: FechaPreaviso está indexada.
    ClearCollect(colPorVencer,
        Filter(Contratos,
            Estado.Value <> "Terminado",
            Estado.Value <> "Anulado",
            Estado.Value <> "Rechazado",
            VigenciaIndefinida <> true,
            FechaPreaviso <= gblHoy,
            FechaFin >= gblHoy
        )
    ),

    // Contratos ya vencidos que nadie cerró.
    ClearCollect(colVencidos,
        Filter(Contratos,
            Estado.Value = "Vencido"
        )
    ),

    // Mis aprobaciones pendientes. Decision está indexada.
    ClearCollect(colMisAprobaciones,
        Filter(Aprobaciones,
            Decision.Value = "Pendiente",
            AprobadorAsignado.Email = gblUsuario.Email
        )
    ),

    // Lo que yo registré y sigue en curso.
    ClearCollect(colMisEnCurso,
        Filter(Contratos,
            Estado.Value = "En aprobacion"
        )
    ),

    // Originales prestados sin devolver.
    ClearCollect(colPrestamosAbiertos,
        Filter(MovimientosCustodia,
            TipoMovimiento.Value = "Prestamo",
            IsBlank(FechaDevolucionReal)
        )
    )
);

// El recuento de vigentes se resuelve en el servidor.
Set(gblTotalVigentes, CountRows(Filter(Contratos, Estado.Value = "Vigente")));
```

## Indicadores (tarjetas)

Cuatro `Rectangle` + `Label`, o un contenedor horizontal.

| Tarjeta | `Text` | `Color` del número |
|---|---|---|
| Vigentes | `gblTotalVigentes` | `gblTema.Exito` |
| Por vencer | `CountRows(colPorVencer)` | `gblTema.Advertencia` |
| Vencidos | `CountRows(colVencidos)` | `gblTema.Error` |
| Me toca aprobar | `CountRows(colMisAprobaciones)` | `gblTema.Info` |

`OnSelect` de la tarjeta «Por vencer»:

```powerfx
Set(gblFiltroEntrada, "PorVencer");
Navigate(scrBandeja, ScreenTransition.Fade)
```

`OnSelect` de «Me toca aprobar»:

```powerfx
Navigate(scrAprobaciones, ScreenTransition.Fade)
```

## galPendientesAprobacion

```powerfx
// Items
SortByColumns(colMisAprobaciones, "FechaSolicitud", SortOrder.Ascending)
```

Plantilla:

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblCodigo` | `Text` | `ThisItem.Contrato.Value` |
| `lblNivel` | `Text` | `"Nivel " & ThisItem.Nivel & " · " & ThisItem.RolAprobador` |
| `lblEspera` | `Text` | `"Esperando hace " & DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Days) & " día(s)"` |
| `lblEspera` | `Color` | `If(DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Hours) > 48, gblTema.Error, gblTema.TextoSuave)` |

`OnSelect` del elemento:

```powerfx
Set(gblContrato, LookUp(Contratos, ID = ThisItem.Contrato.Id));
Navigate(scrDetalle, ScreenTransition.Fade)
```

## galPorVencer

```powerfx
// Items
SortByColumns(colPorVencer, "FechaFin", SortOrder.Ascending)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblNombre` | `Text` | `ThisItem.Title & " · " & ThisItem.NombreContrato` |
| `lblContraparte` | `Text` | `ThisItem.Contraparte` |
| `lblDias` | `Text` | `DateDiff(gblHoy, ThisItem.FechaFin, TimeUnit.Days) & " días"` |
| `lblDias` | `Color` | `If(DateDiff(gblHoy, ThisItem.FechaFin, TimeUnit.Days) <= 7, gblTema.Error, gblTema.Advertencia)` |
| `icoRenueva` | `Visible` | `ThisItem.RenovacionAutomatica` |
| `icoRenueva` | `Tooltip` | `"Renovación automática: si no deseas renovar, avisa antes del vencimiento"` |

## Botón «Registrar contrato»

```powerfx
// OnSelect
Set(gblContrato, Blank());
Set(gblModoEdicion, "Nuevo");
Navigate(scrEditar, ScreenTransition.Cover)
```

---

# scrBandeja — búsqueda y listado

## scrBandeja.OnVisible

```powerfx
// gblFiltroEntrada permite que el tablero abra esta pantalla ya filtrada.
UpdateContext({
    locEstado:  If(gblFiltroEntrada = "PorVencer", "Por vencer", "(Todos)"),
    locTipo:    "(Todos)",
    locSoloMios: false
});
Set(gblFiltroEntrada, Blank());
Reset(txtBuscar)
```

## Controles de filtro

| Control | Propiedad | Fórmula |
|---|---|---|
| `txtBuscar` | `HintText` | `"Buscar por código, nombre o contraparte"` |
| `cmbEstado` | `Items` | `colEstadosFiltro` |
| `cmbEstado` | `DefaultSelectedItems` | `LookUp(colEstadosFiltro, Valor = locEstado)` |
| `cmbTipo` | `Items` | `Ungroup(Table({v: ["(Todos)"]}, {v: Choices(Contratos.TipoContrato).Value}), "v")` |
| `chkSoloMios` | `Text` | `"Solo los míos"` |

> `cmbEstado.OnChange`: `UpdateContext({locEstado: cmbEstado.Selected.Valor})`
> `cmbTipo.OnChange`: `UpdateContext({locTipo: cmbTipo.Selected.Value})`
> `chkSoloMios.OnCheck` / `OnUncheck`: `UpdateContext({locSoloMios: chkSoloMios.Value})`

## galContratos.Items

La consulta se construye en ramas para que **cada una se delegue entera**. Mezclar
la comparación con `"(Todos)"` dentro del `Filter` rompería la delegación, porque
esa condición no depende de la fila (ver la nota de delegación en
`00-app-y-tema.md`).

```powerfx
SortByColumns(
    With(
        {
            // StartsWith con texto vacío devuelve verdadero para toda fila,
            // así que no hace falta un IsBlank() extra (que sí rompería la
            // delegación).
            _buscar: Trim(txtBuscar.Text)
        },
        Switch(
            // Cuatro combinaciones posibles de los dos filtros de catálogo.
            (locEstado <> "(Todos)") & "|" & (locTipo <> "(Todos)"),

            "true|true",
                Filter(Contratos,
                    Estado.Value = locEstado,
                    TipoContrato.Value = locTipo,
                    StartsWith(Title, _buscar)
                        || StartsWith(NombreContrato, _buscar)
                        || StartsWith(Contraparte, _buscar)
                ),

            "true|false",
                Filter(Contratos,
                    Estado.Value = locEstado,
                    StartsWith(Title, _buscar)
                        || StartsWith(NombreContrato, _buscar)
                        || StartsWith(Contraparte, _buscar)
                ),

            "false|true",
                Filter(Contratos,
                    TipoContrato.Value = locTipo,
                    StartsWith(Title, _buscar)
                        || StartsWith(NombreContrato, _buscar)
                        || StartsWith(Contraparte, _buscar)
                ),

            Filter(Contratos,
                StartsWith(Title, _buscar)
                    || StartsWith(NombreContrato, _buscar)
                    || StartsWith(Contraparte, _buscar)
            )
        )
    ),
    "FechaFin", SortOrder.Ascending
)
```

> **«Solo los míos»** se aplica aparte, porque `ResponsableContrato.Email` es una
> columna de persona y SharePoint no la delega. Se resuelve filtrando la galería
> ya delegada, y el checkbox muestra el aviso «filtrado sobre los primeros
> resultados» cuando hay más de 500 filas. Si este filtro es de uso frecuente,
> la solución limpia es agregar a la lista una columna de texto
> `ResponsableEmail` (indexada) que mantenga el flujo 05.

```powerfx
// Si se usa el checkbox, envolver el resultado anterior en:
If(locSoloMios,
    Filter(<consulta anterior>, ResponsableContrato.Email = gblUsuario.Email),
    <consulta anterior>
)
```

## Plantilla de la galería

| Control | Propiedad | Fórmula |
|---|---|---|
| `recEstado` | `Fill` | La expresión *Color según el estado* de `00-app-y-tema.md` |
| `lblCodigo` | `Text` | `Coalesce(ThisItem.Title, "(sin código)")` |
| `lblNombre` | `Text` | `ThisItem.NombreContrato` |
| `lblContraparte` | `Text` | `ThisItem.Contraparte & If(IsBlank(ThisItem.ContraparteRUC), "", " · RUC " & ThisItem.ContraparteRUC)` |
| `lblMonto` | `Text` | `If(ThisItem.SinMontoDeterminado, "Monto no determinado", ThisItem.Moneda.Value & " " & Text(ThisItem.Monto, "#,##0.00"))` |
| `lblVigencia` | `Text` | `Text(ThisItem.FechaInicio, "dd/mm/yyyy") & " → " & If(ThisItem.VigenciaIndefinida, "indefinida", Text(ThisItem.FechaFin, "dd/mm/yyyy"))` |
| `lblEstado` | `Text` | `ThisItem.Estado.Value` |
| `icoCustodia` | `Icon` | `Switch(ThisItem.EstadoCustodia.Value, "En custodia", Icon.Lock, "Prestado", Icon.Clock, "Solo digital", Icon.Document, Icon.Warning)` |
| `icoCustodia` | `Tooltip` | `"Custodia: " & ThisItem.EstadoCustodia.Value` |

`OnSelect` del elemento:

```powerfx
Set(gblContrato, ThisItem);
Navigate(scrDetalle, ScreenTransition.Fade)
```

## Estado vacío

`lblSinResultados.Visible`:

```powerfx
CountRows(galContratos.AllItems) = 0
```

`lblSinResultados.Text`:

```powerfx
If(
    IsBlank(Trim(txtBuscar.Text)) && locEstado = "(Todos)" && locTipo = "(Todos)",
    "Todavía no hay contratos registrados.",
    "Ningún contrato coincide con la búsqueda. Prueba con menos filtros."
)
```

> `StartsWith` busca por el **inicio** del texto, no por contenido: es la única
> forma de que SharePoint delegue la búsqueda. Conviene que la etiqueta del campo
> lo diga («empieza por…») para que nadie crea que la búsqueda está fallando.
