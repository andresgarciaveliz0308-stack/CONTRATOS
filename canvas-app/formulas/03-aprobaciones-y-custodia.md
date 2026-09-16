# scrAprobaciones y scrCustodia

---

# scrAprobaciones — bandeja del aprobador

> **Dónde se aprueba de verdad.** La decisión se toma en las tarjetas de
> **Approvals** (Teams, Outlook o el portal de Power Automate), porque es ahí
> donde el flujo queda esperando. Esta pantalla es el **panel de seguimiento**:
> muestra qué está pendiente, hace cuánto y con qué contexto, y lleva al
> aprobador a la tarjeta o al contrato. No duplica el acto de aprobar, para que
> no existan dos verdades sobre la misma decisión.

## scrAprobaciones.OnVisible

```powerfx
Concurrent(
    // Lo que me toca resolver.
    ClearCollect(colPendientesMias,
        Filter(Aprobaciones,
            Decision.Value = "Pendiente",
            AprobadorAsignado.Email = gblUsuario.Email
        )
    ),
    // Lo que ya resolví, para consulta.
    ClearCollect(colResueltasMias,
        Filter(Aprobaciones,
            Decision.Value <> "Pendiente",
            ResueltoPor.Email = gblUsuario.Email
        )
    ),
    // Vista de administrador: todo lo pendiente del sistema.
    If(gblEsAdmin,
        ClearCollect(colPendientesTodas,
            Filter(Aprobaciones, Decision.Value = "Pendiente")
        )
    )
);

Set(gblSlaHoras,
    Coalesce(Value(LookUp(colParametros, Title = "SLA_APROBACION_HORAS", Valor), "en-US"), 48)
);
UpdateContext({ locVista: "Pendientes" })
```

## galPendientes.Items

```powerfx
SortByColumns(
    If(locVista = "Todas" && gblEsAdmin, colPendientesTodas, colPendientesMias),
    "FechaSolicitud", SortOrder.Ascending
)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblContrato` | `Text` | `ThisItem.Contrato.Value` |
| `lblNivel` | `Text` | `"Nivel " & ThisItem.Nivel & " · " & ThisItem.RolAprobador` |
| `lblAsignado` | `Text` | `ThisItem.AprobadorAsignado.DisplayName` |
| `lblAsignado` | `Visible` | `locVista = "Todas"` |
| `lblEspera` | `Text` | `"Pendiente hace " & DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Hours) & " h"` |
| `recSla` | `Fill` | `If(DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Hours) > gblSlaHoras, gblTema.Error, gblTema.Advertencia)` |
| `lblSla` | `Text` | `If(DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Hours) > gblSlaHoras, "SLA vencido", "Dentro del SLA")` |

`OnSelect` del elemento — abre el contrato con su contexto completo:

```powerfx
Set(gblContrato, LookUp(Contratos, ID = ThisItem.Contrato.Id));
Navigate(scrDetalle, ScreenTransition.Fade)
```

## btnAbrirTareaDeAprobacion

```powerfx
// OnSelect: lleva al centro de aprobaciones, donde está la tarjeta que decide.
Launch("https://make.powerautomate.com/environments/~default/approvals/received")
```

## Recordatorio manual (solo administrador)

```powerfx
// btnRecordar.Visible
gblEsAdmin && DateDiff(ThisItem.FechaSolicitud, Now(), TimeUnit.Hours) > gblSlaHoras

// btnRecordar.OnSelect
Office365Outlook.SendEmailV2(
    ThisItem.AprobadorAsignado.Email,
    "[Contratos] Recordatorio de aprobación pendiente · " & ThisItem.Contrato.Value,
    "<p>Tienes pendiente la aprobación de nivel " & ThisItem.Nivel &
    " del contrato <b>" & ThisItem.Contrato.Value & "</b>, solicitada el " &
    Text(ThisItem.FechaSolicitud, "dd/mm/yyyy") & ".</p>" &
    "<p>Resuélvela desde el centro de aprobaciones de Power Automate o desde Teams.</p>"
);
Patch(Alertas, Defaults(Alertas), {
    Title:       ThisItem.Contrato.Value & " - Recordatorio N" & ThisItem.Nivel,
    Contrato:    { Id: ThisItem.Contrato.Id, Value: ThisItem.Contrato.Value },
    TipoAlerta:  { Value: "SLA vencido" },
    FechaEnvio:  Now(),
    Destinatarios: ThisItem.AprobadorAsignado.Email,
    Canal:       { Value: "Correo" }
});
Notify("Recordatorio enviado a " & ThisItem.AprobadorAsignado.DisplayName,
       NotificationType.Success)
```

## Estado vacío

```powerfx
// lblSinPendientes.Text
If(locVista = "Todas",
   "No hay aprobaciones pendientes en el sistema.",
   "No tienes aprobaciones pendientes.")
```

---

# scrCustodia — cadena de custodia del original

Controla el documento **físico**: dónde está, quién lo tiene y desde cuándo.

## scrCustodia.OnVisible

```powerfx
ClearCollect(colMovimientos,
    SortByColumns(
        Filter(MovimientosCustodia, Contrato.Id = gblContrato.ID),
        "FechaMovimiento", SortOrder.Descending
    )
);

// Préstamo abierto: el último préstamo sin devolución registrada.
Set(gblPrestamoAbierto,
    First(
        Filter(colMovimientos,
            TipoMovimiento.Value = "Prestamo",
            IsBlank(FechaDevolucionReal)
        )
    )
);

UpdateContext({
    locAccion: "",
    locUbicacion: Coalesce(gblContrato.UbicacionFisica, ""),
    locCompromiso: DateAdd(gblHoy, 7, TimeUnit.Days),
    locObservaciones: ""
});
```

## Cabecera de estado

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblEstadoCustodia` | `Text` | `gblContrato.EstadoCustodia.Value` |
| `recEstadoCustodia` | `Fill` | `Switch(gblContrato.EstadoCustodia.Value, "En custodia", gblTema.Exito, "Prestado", gblTema.Advertencia, "Pendiente de recepcion", gblTema.Error, gblTema.TextoSuave)` |
| `lblUbicacion` | `Text` | `Coalesce(gblContrato.UbicacionFisica, "Sin ubicación registrada")` |
| `lblCustodio` | `Text` | `Coalesce(gblContrato.Custodio.DisplayName, "Sin custodio asignado")` |
| `lblQuienLoTiene` | `Text` | `"En poder de " & gblPrestamoAbierto.SolicitadoPor.DisplayName & " desde el " & Text(gblPrestamoAbierto.FechaMovimiento, "dd/mm/yyyy")` |
| `lblQuienLoTiene` | `Visible` | `!IsBlank(gblPrestamoAbierto)` |
| `lblAtraso` | `Text` | `"Devolución vencida hace " & DateDiff(gblPrestamoAbierto.FechaCompromisoDevolucion, gblHoy, TimeUnit.Days) & " día(s)"` |
| `lblAtraso` | `Visible` | `!IsBlank(gblPrestamoAbierto) && gblPrestamoAbierto.FechaCompromisoDevolucion < gblHoy` |
| `lblAtraso` | `Color` | `gblTema.Error` |

## Acciones

Cada botón abre el mismo panel con un `locAccion` distinto.

| Botón | `Visible` |
|---|---|
| `btnRecibir` | `gblEsCustodio && gblContrato.EstadoCustodia.Value = "Pendiente de recepcion"` |
| `btnPrestar` | `gblEsCustodio && gblContrato.EstadoCustodia.Value = "En custodia"` |
| `btnDevolver` | `gblEsCustodio && gblContrato.EstadoCustodia.Value = "Prestado"` |
| `btnTrasladar` | `gblEsCustodio && gblContrato.EstadoCustodia.Value = "En custodia"` |
| `btnDarDeBaja` | `gblEsAdmin && gblContrato.EstadoCustodia.Value in ["En custodia", "Solo digital"]` |

Ejemplo: `btnPrestar.OnSelect` → `UpdateContext({ locAccion: "Prestamo" })`

### Registrar recepción del original

```powerfx
// btnConfirmarRecepcion.OnSelect
If(
    IsBlank(Trim(txtUbicacion.Text)),
    Notify("Indica la ubicación física donde queda archivado el original.",
           NotificationType.Warning),

    Patch(MovimientosCustodia, Defaults(MovimientosCustodia), {
        Title:            "MOV-" & Text(Year(gblHoy)) & "-" & Text(gblContrato.ID, "0000") & "-R",
        Contrato:         { Id: gblContrato.ID, Value: gblContrato.Title },
        TipoMovimiento:   { Value: "Recepcion de original" },
        FechaMovimiento:  Now(),
        EntregadoPor:     gblUsuario,
        UbicacionDestino: Trim(txtUbicacion.Text),
        ActaFirmada:      chkActa.Value,
        Observaciones:    Trim(txtObservaciones.Text)
    });

    Patch(Contratos, gblContrato, {
        EstadoCustodia:         { Value: "En custodia" },
        UbicacionFisica:        Trim(txtUbicacion.Text),
        Custodio:               gblUsuario,
        FechaRecepcionOriginal: gblHoy
    });

    Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
    UpdateContext({ locAccion: "" });
    Notify("Recepción registrada. El original queda en custodia.",
           NotificationType.Success);
    ClearCollect(colMovimientos,
        SortByColumns(Filter(MovimientosCustodia, Contrato.Id = gblContrato.ID),
                      "FechaMovimiento", SortOrder.Descending))
)
```

### Registrar préstamo

```powerfx
// btnConfirmarPrestamo.OnSelect
If(
    IsBlank(cmbSolicitante.Selected),
    Notify("Indica a quién se entrega el documento original.", NotificationType.Warning),

    dteCompromiso.SelectedDate <= gblHoy,
    Notify("La fecha de compromiso de devolución debe ser posterior a hoy.",
           NotificationType.Warning),

    Patch(MovimientosCustodia, Defaults(MovimientosCustodia), {
        Title:            "MOV-" & Text(Year(gblHoy)) & "-" & Text(gblContrato.ID, "0000") & "-P",
        Contrato:         { Id: gblContrato.ID, Value: gblContrato.Title },
        TipoMovimiento:   { Value: "Prestamo" },
        FechaMovimiento:  Now(),
        SolicitadoPor:    cmbSolicitante.Selected,
        EntregadoPor:     gblUsuario,
        UbicacionOrigen:  gblContrato.UbicacionFisica,
        UbicacionDestino: Trim(txtDestino.Text),
        FechaCompromisoDevolucion: dteCompromiso.SelectedDate,
        ActaFirmada:      chkActa.Value,
        Observaciones:    Trim(txtObservaciones.Text)
    });

    Patch(Contratos, gblContrato, { EstadoCustodia: { Value: "Prestado" } });

    // Constancia para quien se lleva el documento.
    Office365Outlook.SendEmailV2(
        cmbSolicitante.Selected.Email,
        "[Contratos] Cargo de entrega del original " & gblContrato.Title,
        "<p>Recibiste el documento original del contrato <b>" & gblContrato.Title &
        "</b> - " & gblContrato.NombreContrato & ".</p>" &
        "<p>Comprometiste su devolución para el <b>" &
        Text(dteCompromiso.SelectedDate, "dd/mm/yyyy") & "</b>.</p>" &
        "<p>Entregado por " & gblUsuario.FullName & ".</p>"
    );

    Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
    UpdateContext({ locAccion: "" });
    Notify("Préstamo registrado y cargo enviado por correo.", NotificationType.Success);
    ClearCollect(colMovimientos,
        SortByColumns(Filter(MovimientosCustodia, Contrato.Id = gblContrato.ID),
                      "FechaMovimiento", SortOrder.Descending))
)
```

`cmbSolicitante.Items`: `Office365Users.SearchUser({searchTerm: cmbSolicitante.SearchText, top: 20})`

### Registrar devolución

Cierra el préstamo abierto en lugar de crear un movimiento suelto: así el par
préstamo/devolución queda emparejado y el flujo 06 deja de reclamarlo.

```powerfx
// btnConfirmarDevolucion.OnSelect
Patch(MovimientosCustodia,
      LookUp(MovimientosCustodia, ID = gblPrestamoAbierto.ID),
      {
          FechaDevolucionReal: gblHoy,
          Observaciones: Trim(
              Coalesce(gblPrestamoAbierto.Observaciones, "") &
              If(IsBlank(Trim(txtObservaciones.Text)), "",
                 Char(10) & "Devolución: " & Trim(txtObservaciones.Text))
          )
      }
);

Patch(MovimientosCustodia, Defaults(MovimientosCustodia), {
    Title:            "MOV-" & Text(Year(gblHoy)) & "-" & Text(gblContrato.ID, "0000") & "-D",
    Contrato:         { Id: gblContrato.ID, Value: gblContrato.Title },
    TipoMovimiento:   { Value: "Devolucion" },
    FechaMovimiento:  Now(),
    SolicitadoPor:    gblPrestamoAbierto.SolicitadoPor,
    EntregadoPor:     gblUsuario,
    UbicacionDestino: gblContrato.UbicacionFisica,
    Observaciones:    Trim(txtObservaciones.Text)
});

Patch(Contratos, gblContrato, { EstadoCustodia: { Value: "En custodia" } });
Set(gblContrato, LookUp(Contratos, ID = gblContrato.ID));
Set(gblPrestamoAbierto, Blank());
UpdateContext({ locAccion: "" });
Notify("Devolución registrada. El original vuelve al archivo.",
       NotificationType.Success);
ClearCollect(colMovimientos,
    SortByColumns(Filter(MovimientosCustodia, Contrato.Id = gblContrato.ID),
                  "FechaMovimiento", SortOrder.Descending))
```

## galMovimientos — historial

```powerfx
// Items
colMovimientos
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `icoTipo` | `Icon` | `Switch(ThisItem.TipoMovimiento.Value, "Recepcion de original", Icon.Add, "Prestamo", Icon.Send, "Devolucion", Icon.Undo, "Traslado", Icon.Redo, "Baja / Destruccion", Icon.Trash, Icon.Document)` |
| `lblTipo` | `Text` | `ThisItem.TipoMovimiento.Value` |
| `lblFecha` | `Text` | `Text(ThisItem.FechaMovimiento, "dd/mm/yyyy hh:mm")` |
| `lblQuien` | `Text` | `Coalesce(ThisItem.SolicitadoPor.DisplayName, ThisItem.EntregadoPor.DisplayName, "")` |
| `lblUbicaciones` | `Text` | `If(IsBlank(ThisItem.UbicacionOrigen), ThisItem.UbicacionDestino, ThisItem.UbicacionOrigen & " → " & ThisItem.UbicacionDestino)` |
| `lblPendiente` | `Visible` | `ThisItem.TipoMovimiento.Value = "Prestamo" && IsBlank(ThisItem.FechaDevolucionReal)` |
| `lblPendiente` | `Text` | `"Sin devolver"` |
| `icoActa` | `Visible` | `ThisItem.ActaFirmada` |
