# scrAdmin — administración

Solo visible para `gblEsAdmin`. Cuatro secciones: **matriz de aprobación**,
**parámetros**, **áreas** y **categorías** (esta última documentada en
`05-categorias-campos-dinamicos.md`). Es la pantalla que permite cambiar cómo
se aprueba y cómo se organiza el archivo, sin tocar Power Automate ni
SharePoint.

## scrAdmin.OnVisible

```powerfx
// Puerta de entrada. La barrera real está en los permisos de SharePoint
// (ver docs/05-seguridad-permisos.md); esto solo evita mostrar una pantalla
// que el usuario no podría guardar de todos modos.
If(!gblEsAdmin,
    Notify("No tienes acceso a la administración del sistema.", NotificationType.Error);
    Back()
);

Concurrent(
    ClearCollect(colMatriz,
        SortByColumns(
            SortByColumns(MatrizAprobacion, "Nivel", SortOrder.Ascending),
            "MontoDesdePEN", SortOrder.Ascending
        )
    ),
    ClearCollect(colParametros, Parametros),
    ClearCollect(colAreasAdmin, Areas)
);

UpdateContext({ locSeccion: "Matriz" })
```

---

## Sección Matriz de aprobación

### galMatriz.Items

```powerfx
Filter(colMatriz,
    cmbFiltroTipo.Selected.Value = "(Todos)"
        || TipoContrato.Value = cmbFiltroTipo.Selected.Value
)
```

> Aquí sí se puede mezclar la condición constante con la de fila: `colMatriz` es
> una colección **en memoria**, no un origen delegado. La matriz tiene decenas de
> filas, no miles.

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblRegla` | `Text` | `ThisItem.Title` |
| `lblTramo` | `Text` | `Text(ThisItem.MontoDesdePEN, "#,##0") & " – " & If(ThisItem.MontoHastaPEN >= 999999999, "sin tope", Text(ThisItem.MontoHastaPEN, "#,##0"))` |
| `lblNivelRol` | `Text` | `"N" & ThisItem.Nivel & " · " & ThisItem.RolAprobador.Value` |
| `lblAprobador` | `Text` | `Coalesce(ThisItem.AprobadorUsuario.DisplayName, ThisItem.AprobadorGrupo, If(ThisItem.RolAprobador.Value in ["Jefe de area", "Gerente de area"], "(se resuelve por el área del contrato)", "⚠ sin aprobador"))` |
| `lblAprobador` | `Color` | `If(IsBlank(ThisItem.AprobadorUsuario.DisplayName) && IsBlank(ThisItem.AprobadorGrupo) && !(ThisItem.RolAprobador.Value in ["Jefe de area", "Gerente de area"]), gblTema.Error, gblTema.Texto)` |
| `tglActivo` | `Default` | `ThisItem.Activo` |
| `tglActivo` | `OnChange` | `Patch(MatrizAprobacion, LookUp(MatrizAprobacion, ID = ThisItem.ID), { Activo: tglActivo.Value })` |

### Aviso de reglas incompletas

Una regla activa cuyo aprobador no se puede resolver **bloquea** el workflow al
llegar a ese nivel. Conviene verlo aquí y no descubrirlo en un contrato detenido.

```powerfx
// lblAvisoIncompletas.Text
With(
    {
        _malas: Filter(colMatriz,
            Activo = true,
            IsBlank(AprobadorUsuario.Email),
            IsBlank(AprobadorGrupo),
            !(RolAprobador.Value in ["Jefe de area", "Gerente de area"])
        )
    },
    If(CountRows(_malas) = 0,
       "",
       CountRows(_malas) & " regla(s) activa(s) sin aprobador asignado. " &
       "Un contrato que llegue a ese nivel se detendrá y se notificará al administrador."
    )
)

// lblAvisoIncompletas.Visible
!IsBlank(lblAvisoIncompletas.Text)
```

Lo mismo para las áreas sin responsable, que rompen los roles *Jefe* y *Gerente*:

```powerfx
// lblAvisoAreas.Text
With(
    { _sin: Filter(colAreasAdmin, Activo = true, IsBlank(Responsable.Email)) },
    If(CountRows(_sin) = 0, "",
       CountRows(_sin) & " área(s) activa(s) sin responsable: " &
       Concat(_sin, Title, ", ") & ". Los niveles 'Jefe de área' no se podrán resolver.")
)
```

### Simulador de la ruta de aprobación

Responde «¿quién aprueba un contrato así?» sin tener que crear uno. Reproduce en
Power Fx la misma resolución que hace el flujo 01: filtra por tramo y tipo, y en
cada nivel la regla específica gana sobre la genérica.

```powerfx
// btnSimular.OnSelect
With(
    {
        _monto: Coalesce(Value(txtSimMonto.Text), 0),
        _tipo:  cmbSimTipo.Selected.Value,
        _area:  cmbSimArea.Selected
    },
    ClearCollect(colSimAplicables,
        Filter(colMatriz,
            Activo = true,
            MontoDesdePEN <= _monto,
            MontoHastaPEN > _monto,
            TipoContrato.Value = _tipo || TipoContrato.Value = "Todos"
        )
    );

    // Un registro por nivel: la regla del tipo desplaza a la genérica.
    ClearCollect(colSimRuta,
        ForAll(
            Distinct(colSimAplicables, Nivel) As _n,
            With(
                {
                    _especifica: First(Filter(colSimAplicables,
                                       Nivel = _n.Value, TipoContrato.Value = _tipo)),
                    _generica:   First(Filter(colSimAplicables,
                                       Nivel = _n.Value, TipoContrato.Value = "Todos"))
                },
                With(
                    { _r: If(IsBlank(_especifica.ID), _generica, _especifica) },
                    {
                        Nivel: _n.Value,
                        Rol:   _r.RolAprobador.Value,
                        Aprobador:
                            Switch(_r.RolAprobador.Value,
                                "Jefe de area",    Coalesce(_area.Responsable.DisplayName, "⚠ área sin responsable"),
                                "Gerente de area", Coalesce(_area.Gerente.DisplayName,     "⚠ área sin gerente"),
                                Coalesce(_r.AprobadorUsuario.DisplayName, _r.AprobadorGrupo, "⚠ sin aprobador")
                            ),
                        SLA: _r.SLAHoras
                    }
                )
            )
        )
    )
);

UpdateContext({ locSimulado: true })
```

`galSimulacion.Items`: `SortByColumns(colSimRuta, "Nivel", SortOrder.Ascending)`

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblSimNivel` | `Text` | `"Nivel " & ThisItem.Nivel` |
| `lblSimRol` | `Text` | `ThisItem.Rol` |
| `lblSimAprobador` | `Text` | `ThisItem.Aprobador` |
| `lblSimAprobador` | `Color` | `If(StartsWith(ThisItem.Aprobador, "⚠"), gblTema.Error, gblTema.Texto)` |
| `lblSimSla` | `Text` | `ThisItem.SLA & " h"` |

Resumen:

```powerfx
// lblSimResumen.Text
If(
    CountRows(colSimRuta) = 0,
    "⚠ Ningún tramo de la matriz cubre ese monto para ese tipo de contrato. " &
    "Un contrato así quedaría detenido.",
    "Se requieren " & CountRows(colSimRuta) & " nivel(es) de aprobación. " &
    "SLA total estimado: " & Sum(colSimRuta, SLA) & " horas."
)
```

> **Cuidar la paridad.** Si algún día se cambia la lógica de resolución del flujo
> 01, hay que cambiar también este simulador. Un simulador que miente es peor que
> no tenerlo.

### Alta y edición de reglas

`frmRegla.DataSource`: `MatrizAprobacion` · `frmRegla.Item`: `gblReglaEnEdicion`.
Se usa una variable **global** (`Set`), no de pantalla, siguiendo la misma
convención que `gblCategoriaEnEdicion` / `gblCampoEnEdicion` de la sección
Categorías (`05-categorias-campos-dinamicos.md`): todos los formularios de
alta/edición de `scrAdmin` guardan su registro en edición del mismo modo.

Mientras el panel está abierto (`locPanelRegla = true`), **reemplaza** a
`galMatriz` en el mismo espacio de la pantalla — no aparecen los dos a la vez.

```powerfx
// btnNuevaRegla.OnSelect
Set(gblReglaEnEdicion, Blank());
NewForm(frmRegla);
UpdateContext({ locPanelRegla: true, locErrorRegla: "" })

// btnMatEditar.OnSelect (uno por fila de galMatriz)
Set(gblReglaEnEdicion, ThisItem);
EditForm(frmRegla);
UpdateContext({ locPanelRegla: true, locErrorRegla: "" })
```

Validación antes de guardar:

```powerfx
// btnReglaGuardar.OnSelect
With(
    {
        _desde: Value(DataCardValue_MontoDesde.Text),
        _hasta: Value(DataCardValue_MontoHasta.Text),
        _rol:   DataCardValue_Rol.Selected.Value,
        _usr:   DataCardValue_AprobadorUsuario.Selected,
        _grp:   Trim(DataCardValue_AprobadorGrupo.Text)
    },
    UpdateContext({
        locErrorRegla:
            If(
                _hasta <= _desde,
                "El monto 'hasta' debe ser mayor que el monto 'desde'.",

                !(_rol in ["Jefe de area", "Gerente de area"])
                    && IsBlank(_usr) && IsBlank(_grp),
                "Este rol no se resuelve solo: indica un aprobador (usuario o grupo).",

                !IsBlank(_grp) && !IsMatch(_grp, Match.Email),
                "El grupo debe ser una dirección de correo válida.",

                ""
            )
    })
);

If(IsBlank(locErrorRegla), SubmitForm(frmRegla))
```

```powerfx
// frmRegla.OnSuccess
ClearCollect(colMatriz,
    SortByColumns(
        SortByColumns(MatrizAprobacion, "Nivel", SortOrder.Ascending),
        "MontoDesdePEN", SortOrder.Ascending
    )
);
UpdateContext({ locPanelRegla: false });
Notify("Regla guardada. Aplica a los contratos que se envíen a aprobación desde ahora.",
       NotificationType.Success, 5000)
```

> Cambiar la matriz **no altera** los contratos que ya están circulando: sus
> niveles se resolvieron al enviarse. Es intencional — la ruta de aprobación de
> un contrato no debe moverse bajo los pies de quienes ya la están recorriendo.

---

## Sección Parámetros

```powerfx
// galParametros.Items
SortByColumns(colParametros, "Title", SortOrder.Ascending)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblClave` | `Text` | `ThisItem.Title` |
| `lblDescripcion` | `Text` | `ThisItem.Descripcion` |
| `txtValor` | `Default` | `ThisItem.Valor` |
| `btnGuardarParam` | `DisplayMode` | `If(txtValor.Text = ThisItem.Valor, DisplayMode.Disabled, DisplayMode.Edit)` |

```powerfx
// btnGuardarParam.OnSelect
Patch(Parametros, LookUp(Parametros, ID = ThisItem.ID), { Valor: Trim(txtValor.Text) });
ClearCollect(colParametros, Parametros);

// Los tipos de cambio y el interruptor de DocuSign están en variables globales
// cargadas en OnStart: hay que refrescarlas o la sesión seguiría con el valor viejo.
Set(gblTCUSD, Coalesce(Value(LookUp(colParametros, Title = "TC_USD", Valor), "en-US"), 1));
Set(gblTCEUR, Coalesce(Value(LookUp(colParametros, Title = "TC_EUR", Valor), "en-US"), 1));
Set(gblDocuSignHabilitado,
    Lower(Coalesce(LookUp(colParametros, Title = "DOCUSIGN_HABILITADO", Valor), "false")) = "true");

Notify("Parámetro actualizado.", NotificationType.Success)
```

> Los parámetros que leen los **flujos** (correos, hitos de alerta, prefijo) se
> leen en cada ejecución: el cambio surte efecto de inmediato. Los que lee la
> **app** viven en variables de sesión, y los demás usuarios los verán al volver
> a abrirla.

---

## Sección Áreas

```powerfx
// galAreas.Items
SortByColumns(colAreasAdmin, "Title", SortOrder.Ascending)
```

| Control | Propiedad | Fórmula |
|---|---|---|
| `lblArea` | `Text` | `ThisItem.Title & " (" & ThisItem.CodigoArea & ")"` |
| `lblResponsable` | `Text` | `Coalesce(ThisItem.Responsable.DisplayName, "⚠ sin responsable")` |
| `lblGerente` | `Text` | `Coalesce(ThisItem.Gerente.DisplayName, "⚠ sin gerente")` |
| `cmbResponsable` | `OnChange` | `Patch(Areas, LookUp(Areas, ID = ThisItem.ID), { Responsable: cmbResponsable.Selected }); ClearCollect(colAreasAdmin, Areas)` |
| `cmbGerente` | `OnChange` | `Patch(Areas, LookUp(Areas, ID = ThisItem.ID), { Gerente: cmbGerente.Selected }); ClearCollect(colAreasAdmin, Areas)` |

`cmbResponsable.Items` / `cmbGerente.Items`:
`Office365Users.SearchUser({searchTerm: Self.SearchText, top: 20})`

---

## Qué se mantiene desde aquí, y qué no

La pantalla cubre las cinco cosas que cambian con el negocio, para no depender
de abrir SharePoint:

| Sección | Qué se edita |
|---|---|
| Áreas | Responsable, Gerente y Vicepresidente de cada área |
| Matriz de aprobación | Tramos de monto, niveles, roles, aprobadores, activar y desactivar reglas |
| Parámetros | Tipos de cambio, días de preaviso, correos, interruptor de DocuSign |
| Categorías | Carpetas, color, orden, responsable adicional |
| Campos y cláusulas | El esquema que se pide en cada categoría |
| Simulador | Qué ruta saldría para un monto y un tipo dados |

### El límite: dato contra estructura

Lo que la pantalla edita son **filas**. Lo que no puede cambiar son las
**columnas y los catálogos**, porque de eso dependen las fórmulas y los flujos.

| Se hace desde la app | Hace falta tocar el esquema |
|---|---|
| Cambiar quién es el Gerente de un área | Inventar un **rol nuevo** de aprobador |
| Agregar un área, con sus tres personas | Agregar un **tipo de contrato** al catálogo |
| Mover el tramo de 375.000 a otro monto | Agregar un **estado** a la máquina de estados |
| Agregar un nivel a una regla | Agregar una **columna** a la ficha del contrato |
| Crear una categoría y sus campos | |

La regla para distinguirlos: **si el valor sale de una lista desplegable fija,
es estructura**. Un rol nuevo, por ejemplo, necesita tres cambios coordinados:
la opción en `RolAprobador`, la columna de persona en `Areas` si varía por
área, y la rama correspondiente en la resolución del aprobador del flujo 01.
Fue exactamente lo que hizo falta para agregar `Vicepresidencia de area`.

Es una frontera deliberada, no una carencia: el día que alguien renombre un rol
desde una pantalla, los flujos dejan de encontrarlo y los contratos se detienen
sin error visible.
