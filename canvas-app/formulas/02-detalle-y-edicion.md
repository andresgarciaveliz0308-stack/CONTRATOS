# scrDetalle y scrEditar

---

# scrDetalle — ficha del contrato

Seis pestañas sobre el mismo registro: **General · Económico · Documentos ·
Aprobaciones · Custodia · Adendas**.

## scrDetalle.OnVisible

```powerfx
// gblContrato viene de la pantalla anterior. Se relee de la lista para no
// trabajar con una copia obsoleta: entre que se abrió la bandeja y se entró
// aquí, un flujo pudo haber cambiado el estado.
Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
UpdateContext({ locPestana: "General" });

Concurrent(
    ClearCollect(colDocumentos,
        Filter(DocumentosContratos, Contrato.Id = gblContrato.ID)
    ),
    ClearCollect(colAprobaciones,
        Filter(Aprobaciones, Contrato.Id = gblContrato.ID)
    ),
    ClearCollect(colMovimientos,
        Filter(MovimientosCustodia, Contrato.Id = gblContrato.ID)
    ),
    ClearCollect(colAdendas,
        Filter(Adendas, Contrato.Id = gblContrato.ID)
    )
);

// Monto acumulado: el original más las adendas ya aprobadas.
Set(gblMontoVigente,
    gblContrato.Monto +
    Sum(Filter(colAdendas, Estado.Value = "Aprobada"), MontoDelta)
);
```

## Cabecera

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblTitulo` | `Text` | `Coalesce(gblContrato.Title, "(sin código)") & " · " & gblContrato.NombreContrato` |
| `lblEstado` | `Text` | `gblContrato.Estado.Value` |
| `recEstado` | `Fill` | Expresión *Color según el estado*, con `gblContrato` en vez de `ThisItem` |
| `lblAvanceAprobacion` | `Text` | `If(gblContrato.NivelAprobacionRequerido > 0, "Nivel " & gblContrato.NivelAprobacionActual & " de " & gblContrato.NivelAprobacionRequerido, "")` |
| `lblAvanceAprobacion` | `Visible` | `gblContrato.Estado.Value = "En aprobacion"` |

## Barra de acciones

Cada botón se muestra solo cuando la acción es legal en el estado actual. Esa es
la máquina de estados de `docs/02-modelo-datos.md` traducida a `Visible`.

### btnEditar

```powerfx
// Visible
gblContrato.Estado.Value in ["Borrador", "Rechazado", "En revision legal"]

// OnSelect
Set(gblModoEdicion, "Editar");
Navigate(scrEditar, ScreenTransition.Cover)
```

### btnVistoBuenoLegal

```powerfx
// Visible
gblEsLegal && gblContrato.Estado.Value = "En revision legal"

// OnSelect
Patch(Contratos, gblContrato, { Estado: { Value: "Borrador" } });
Patch(Bitacora, Defaults(Bitacora), {
    Title:    gblContrato.Title & " - Visto bueno legal",
    Contrato: { Id: gblContrato.ID, Value: gblContrato.Title },
    Accion:   "Visto bueno legal",
    Usuario:  gblUsuario,
    Fecha:    Now(),
    Detalle:  "Legal dio conformidad. El contrato queda listo para enviarse a aprobación."
});
Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
Notify("Visto bueno registrado.", NotificationType.Success)
```

### btnEnviarAprobacion

Esta es la acción que dispara el workflow.

```powerfx
// Visible
gblContrato.Estado.Value in ["Borrador", "Rechazado"]

// DisplayMode
If(
    IsBlank(gblContrato.TipoContrato)
        || IsBlank(gblContrato.AreaSolicitante)
        || IsBlank(gblContrato.FechaInicio)
        || (!gblContrato.SinMontoDeterminado && IsBlank(gblContrato.Monto))
        || CountRows(Filter(colDocumentos, EsPrincipal = true)) = 0,
    DisplayMode.Disabled,
    DisplayMode.Edit
)

// Tooltip: explica por qué está deshabilitado en vez de dejar al usuario adivinando.
If(
    CountRows(Filter(colDocumentos, EsPrincipal = true)) = 0,
    "Falta subir el documento del contrato y marcarlo como principal",
    IsBlank(gblContrato.Monto) && !gblContrato.SinMontoDeterminado,
    "Falta indicar el monto, o marcar el contrato como de monto no determinado",
    "Enviar el contrato al circuito de aprobación"
)
```

```powerfx
// OnSelect
UpdateContext({ locEnviando: true });

With(
    {
        _resp: 'Contratos-SolicitudDeAprobacion'.Run(gblContrato.ID)
    },
    If(
        _resp.Resultado = "Enviado",
        Notify(_resp.Mensaje, NotificationType.Success, 4000),
        Notify(_resp.Mensaje, NotificationType.Error, 8000)
    )
);

// El flujo cambia el estado del contrato: hay que releerlo.
Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
ClearCollect(colAprobaciones, Filter(Aprobaciones, Contrato.Id = gblContrato.ID));
UpdateContext({ locEnviando: false })
```

> El flujo responde **antes** de esperar las aprobaciones (una llamada desde
> Power Apps expira a los ~2 minutos), así que esta fórmula devuelve el control
> enseguida. Lo que confirma es que el contrato *entró* al circuito, no que haya
> sido aprobado.

`lblEnviando.Visible` = `locEnviando` · texto: `"Enviando a aprobación…"`

### btnRenovar

```powerfx
// Visible
gblContrato.Estado.Value in ["Vigente", "Por vencer", "Vencido"]

// OnSelect: crea un contrato hijo con los datos heredados y un año más de vigencia.
With(
    {
        _nuevo: Patch(Contratos, Defaults(Contratos), {
            NombreContrato:  gblContrato.NombreContrato & " (renovación)",
            TipoContrato:    gblContrato.TipoContrato,
            ObjetoContrato:  gblContrato.ObjetoContrato,
            Contraparte:     gblContrato.Contraparte,
            ContraparteRUC:  gblContrato.ContraparteRUC,
            TipoContraparte: gblContrato.TipoContraparte,
            ContraparteContacto: gblContrato.ContraparteContacto,
            ContraparteCorreo:   gblContrato.ContraparteCorreo,
            AreaSolicitante: gblContrato.AreaSolicitante,
            Solicitante:     gblUsuario,
            ResponsableContrato: gblContrato.ResponsableContrato,
            Moneda:          gblContrato.Moneda,
            Monto:           gblContrato.Monto,
            FechaInicio:     DateAdd(gblContrato.FechaFin, 1, TimeUnit.Days),
            FechaFin:        DateAdd(gblContrato.FechaFin, 1, TimeUnit.Years),
            DiasPreaviso:    gblContrato.DiasPreaviso,
            Clasificacion:   gblContrato.Clasificacion,
            Estado:          { Value: "Borrador" },
            EstadoCustodia:  { Value: "Pendiente de recepcion" },
            ContratoPadre:   { Id: gblContrato.ID, Value: gblContrato.Title }
        })
    },
    Patch(Contratos, gblContrato, { Estado: { Value: "Renovado" } });
    Set(gblContrato, _nuevo);
    Set(gblModoEdicion, "Editar");
    Notify("Contrato de renovación creado en borrador. Revisa las fechas y el monto.",
           NotificationType.Success, 6000);
    Navigate(scrEditar, ScreenTransition.Cover)
)
```

### btnTerminar

```powerfx
// Visible
gblEsAdmin && gblContrato.Estado.Value in ["Vigente", "Por vencer", "Vencido"]

// OnSelect: pide confirmación antes de un cambio irreversible.
UpdateContext({ locConfirmarTerminar: true })
```

Diálogo de confirmación (`grpConfirmar.Visible = locConfirmarTerminar`), botón
*Sí, terminar*:

```powerfx
Patch(Contratos, gblContrato, { Estado: { Value: "Terminado" } });
Patch(Bitacora, Defaults(Bitacora), {
    Title:    gblContrato.Title & " - Terminacion",
    Contrato: { Id: gblContrato.ID, Value: gblContrato.Title },
    Accion:   "Terminación",
    Usuario:  gblUsuario,
    Fecha:    Now(),
    Detalle:  "Contrato dado por terminado desde la aplicación."
});
Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
UpdateContext({ locConfirmarTerminar: false });
Notify("Contrato terminado.", NotificationType.Success)
```

## Pestaña Documentos

`galDocumentos.Items`:

```powerfx
SortByColumns(colDocumentos, "FechaDocumento", SortOrder.Descending)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblNombreDoc` | `Text` | `ThisItem.'Nombre del archivo con extensión'` |
| `lblTipoDoc` | `Text` | `ThisItem.TipoDocumento.Value & If(IsBlank(ThisItem.VersionDocumento), "", " · " & ThisItem.VersionDocumento)` |
| `icoPrincipal` | `Visible` | `ThisItem.EsPrincipal` |
| `icoFirmado` | `Visible` | `ThisItem.EstaFirmado` |
| `btnAbrir` | `OnSelect` | `Launch(ThisItem.'Vínculo al elemento')` |

Marcar un documento como principal (solo uno puede serlo):

```powerfx
// btnMarcarPrincipal.OnSelect
ForAll(
    Filter(colDocumentos, EsPrincipal = true, ID <> ThisItem.ID) As _otro,
    Patch(DocumentosContratos, LookUp(DocumentosContratos, ID = _otro.ID),
          { EsPrincipal: false })
);
Patch(DocumentosContratos, LookUp(DocumentosContratos, ID = ThisItem.ID),
      { EsPrincipal: true });
ClearCollect(colDocumentos, Filter(DocumentosContratos, Contrato.Id = gblContrato.ID));
Notify("Documento marcado como principal. Es el que se enviará a firma.",
       NotificationType.Success)
```

> **Subida de archivos.** El control `Adjuntar archivo` de Power Apps solo escribe
> en los *datos adjuntos* de un elemento de lista, no en una biblioteca. Para que
> el PDF llegue a `DocumentosContratos` con sus metadatos hay dos caminos:
> incrustar la biblioteca con el control `Vista de lista de SharePoint`, o subir
> el archivo desde un flujo instantáneo que reciba el contenido en base64. En
> `docs/06-manual-usuario.md` se describe el camino recomendado según la versión
> de tu entorno.

## Pestaña Aprobaciones

`galAprobaciones.Items`:

```powerfx
SortByColumns(
    SortByColumns(colAprobaciones, "Nivel", SortOrder.Ascending),
    "Ciclo", SortOrder.Descending
)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblNivel` | `Text` | `"Nivel " & ThisItem.Nivel & " · " & ThisItem.RolAprobador` |
| `lblAprobador` | `Text` | `Coalesce(ThisItem.ResueltoPor.DisplayName, ThisItem.AprobadorAsignado.DisplayName, "(sin asignar)")` |
| `lblDecision` | `Text` | `ThisItem.Decision.Value` |
| `lblDecision` | `Color` | `Switch(ThisItem.Decision.Value, "Aprobado", gblTema.Exito, "Rechazado", gblTema.Error, "Pendiente", gblTema.Advertencia, gblTema.TextoSuave)` |
| `lblFecha` | `Text` | `If(IsBlank(ThisItem.FechaDecision), "Pendiente desde " & Text(ThisItem.FechaSolicitud, "dd/mm/yyyy hh:mm"), Text(ThisItem.FechaDecision, "dd/mm/yyyy hh:mm") & " (" & Text(ThisItem.HorasTranscurridas, "#,##0.0") & " h)")` |
| `lblComentarios` | `Text` | `ThisItem.Comentarios` |
| `lblCiclo` | `Text` | `"Ciclo " & ThisItem.Ciclo` |
| `lblCiclo` | `Visible` | `Max(colAprobaciones, Ciclo) > 1` |

## Pestaña Adendas

`galAdendas.Items`: `SortByColumns(colAdendas, "NumeroAdenda", SortOrder.Descending)`

`btnNuevaAdenda.Visible`: `gblContrato.Estado.Value in ["Vigente", "Por vencer"]`

```powerfx
// btnNuevaAdenda.OnSelect
Set(gblAdenda,
    Patch(Adendas, Defaults(Adendas), {
        Title:        gblContrato.Title & "-AD" & Text(CountRows(colAdendas) + 1, "00"),
        Contrato:     { Id: gblContrato.ID, Value: gblContrato.Title },
        NumeroAdenda: CountRows(colAdendas) + 1,
        FechaAdenda:  gblHoy,
        Estado:       { Value: "Borrador" }
    })
);
ClearCollect(colAdendas, Filter(Adendas, Contrato.Id = gblContrato.ID));
Navigate(scrAdenda, ScreenTransition.Cover)
```

---

# scrEditar — registro y edición

## scrEditar.OnVisible

```powerfx
If(
    gblModoEdicion = "Nuevo",
    NewForm(frmContrato),
    EditForm(frmContrato)
);
UpdateContext({ locError: "" })
```

`frmContrato.Item`: `gblContrato`
`frmContrato.DataSource`: `Contratos`

## Valores predeterminados de un contrato nuevo

| Tarjeta | `Default` |
|---|---|
| Solicitante | `gblUsuario` |
| ResponsableContrato | `gblUsuario` |
| Moneda | `{ Value: gblMonedaBase }` |
| Estado | `{ Value: "Borrador" }` |
| EstadoCustodia | `{ Value: "Pendiente de recepcion" }` |
| Clasificacion | `{ Value: "Interno" }` |
| DiasPreaviso | `gblDiasPreavisoDefault` |
| FechaInicio | `gblHoy` |
| FechaFin | `DateAdd(gblHoy, 1, TimeUnit.Years)` |
| TipoContrato | `{ Value: "Servicios" }` |

> El campo **Código** (`Title`) va en modo `View` y con el texto
> `Coalesce(Parent.Default, "Se asignará al guardar")`: lo genera el flujo 05.

## Visibilidad condicional

| Tarjeta | `Visible` |
|---|---|
| `FechaFin` | `!DataCardValue_VigenciaIndefinida.Value` |
| `DiasPreaviso` | `!DataCardValue_VigenciaIndefinida.Value` |
| `Monto` | `!DataCardValue_SinMonto.Value` |
| `TipoGarantia`, `MontoGarantia`, `VencimientoGarantia` | `DataCardValue_TieneGarantia.Value` |
| `UbicacionFisica`, `Custodio` | `DataCardValue_EstadoCustodia.Selected.Value <> "Solo digital"` |
| `ContraparteCorreo` | `gblDocuSignHabilitado` |

## Validaciones

`DataCard.Required` cubre lo obligatorio. Estas son las reglas que SharePoint no
puede expresar. Se evalúan **antes** de enviar el formulario, en el botón
Guardar: así el usuario ve el error sin haber generado un elemento a medias.

```powerfx
// btnGuardar.OnSelect
UpdateContext({ locError: "" });

With(
    {
        _inicio: DataCardValue_FechaInicio.SelectedDate,
        _fin:    DataCardValue_FechaFin.SelectedDate,
        _indef:  DataCardValue_VigenciaIndefinida.Value,
        _correo: Trim(DataCardValue_ContraparteCorreo.Text),
        _monto:  Value(DataCardValue_Monto.Text),
        _sinMonto: DataCardValue_SinMonto.Value
    },
    UpdateContext({
        locError:
            If(
                !_indef && IsBlank(_fin),
                "Indica la fecha de fin, o marca el contrato como de vigencia indefinida.",

                !_indef && _fin <= _inicio,
                "La fecha de fin debe ser posterior a la de inicio.",

                !_sinMonto && (IsBlank(_monto) || _monto <= 0),
                "El monto debe ser mayor que cero, o marca 'Monto no determinado'.",

                gblDocuSignHabilitado && !IsBlank(_correo) && !IsMatch(_correo, Match.Email),
                "El correo del firmante no tiene un formato válido.",

                gblDocuSignHabilitado && IsBlank(_correo),
                "Con la firma electrónica activa, el correo del firmante es obligatorio.",

                DataCardValue_TieneGarantia.Value && IsBlank(DataCardValue_VencimientoGarantia.SelectedDate),
                "Indica la fecha de vencimiento de la garantía.",

                ""
            )
    })
);

If(IsBlank(locError), SubmitForm(frmContrato))
```

`lblError.Text` = `locError` · `lblError.Visible` = `!IsBlank(locError)` ·
`lblError.Color` = `gblTema.Error`

## frmContrato.OnSuccess

```powerfx
Set(gblContrato, frmContrato.LastSubmit);

// El código lo asigna el flujo 05 unos segundos después de crear el elemento.
If(
    gblModoEdicion = "Nuevo",
    Notify("Contrato registrado. El código se asignará en unos segundos.",
           NotificationType.Success, 5000),
    Notify("Cambios guardados.", NotificationType.Success)
);

Patch(Bitacora, Defaults(Bitacora), {
    Title:    Coalesce(gblContrato.Title, "Nuevo") & " - " & gblModoEdicion,
    Contrato: { Id: gblContrato.ID, Value: Coalesce(gblContrato.Title, "") },
    Accion:   If(gblModoEdicion = "Nuevo", "Creación", "Modificación"),
    Usuario:  gblUsuario,
    Fecha:    Now(),
    Detalle:  "Registro guardado desde la aplicación."
});

Navigate(scrDetalle, ScreenTransition.UnCover)
```

## frmContrato.OnFailure

```powerfx
Notify(
    "No se pudo guardar: " & frmContrato.Error,
    NotificationType.Error,
    8000
)
```

## btnCancelar

```powerfx
ResetForm(frmContrato);
If(gblModoEdicion = "Nuevo", Navigate(scrBandeja, ScreenTransition.UnCover),
                             Navigate(scrDetalle, ScreenTransition.UnCover))
```
