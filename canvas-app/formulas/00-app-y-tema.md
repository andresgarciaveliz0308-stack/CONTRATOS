# App · OnStart, tema y variables globales

Fórmulas del objeto **App** y convenciones que usan todas las pantallas.

> **Convención de nombres.** `gbl` = variable global (`Set`), `loc` = variable de
> pantalla (`UpdateContext`), `col` = colección, `scr` = pantalla, `cmp` =
> componente. Los controles llevan prefijo de tipo: `lbl`, `txt`, `btn`, `gal`,
> `cmb`, `dte`, `frm`, `ico`, `rec`.

---

## Orígenes de datos a conectar

Agrega la conexión de SharePoint al sitio y selecciona estas 10 tablas:

```
Contratos · DocumentosContratos · MatrizAprobacion · Aprobaciones
Adendas · MovimientosCustodia · Areas · Parametros · Alertas · Bitacora
```

Y estos flujos (pestaña *Power Automate*):

```
Contratos - Solicitud de aprobacion
```

---

## App.OnStart

> `OnStart` debe ser rápido: solo carga configuración, nunca el maestro de
> contratos. Los datos de cada pantalla se cargan en su propio `OnVisible`.

```powerfx
// ---------- Contexto del usuario ----------
Set(gblUsuario, User());
Set(gblHoy, Today());

// ---------- Configuración global ----------
// Parametros es una lista pequeña y estable: se cachea una vez por sesión.
ClearCollect(colParametros, Parametros);

// Value() interpreta el separador decimal según la configuración regional del
// usuario. Se fuerza "en-US" porque en la lista los tipos de cambio se guardan
// con punto: sin esto, "3.75" se leería como 375 en un equipo en español.
Set(gblTCUSD,
    Coalesce(Value(LookUp(colParametros, Title = "TC_USD", Valor), "en-US"), 1)
);
Set(gblTCEUR,
    Coalesce(Value(LookUp(colParametros, Title = "TC_EUR", Valor), "en-US"), 1)
);
Set(gblMonedaBase,
    Coalesce(LookUp(colParametros, Title = "MONEDA_BASE", Valor), "PEN")
);
Set(gblDiasPreavisoDefault,
    Coalesce(Value(LookUp(colParametros, Title = "DIAS_PREAVISO_DEFAULT", Valor), "en-US"), 30)
);
Set(gblDocuSignHabilitado,
    Lower(Coalesce(LookUp(colParametros, Title = "DOCUSIGN_HABILITADO", Valor), "false")) = "true"
);

// ---------- Roles ----------
// Los permisos reales los aplica SharePoint (ver docs/05-seguridad-permisos.md).
// Estas variables solo deciden qué se muestra: nunca son la única barrera.
Set(gblEsAdmin,
    gblUsuario.Email in Split(
        Coalesce(LookUp(colParametros, Title = "ADMINS", Valor), ""), ";"
    ).Value
);
Set(gblEsCustodio,
    gblEsAdmin ||
    gblUsuario.Email in Split(
        Coalesce(LookUp(colParametros, Title = "CUSTODIOS", Valor), ""), ";"
    ).Value
);
Set(gblEsLegal,
    gblEsAdmin ||
    gblUsuario.Email in Split(
        Coalesce(LookUp(colParametros, Title = "LEGAL", Valor), ""), ";"
    ).Value
);

// ---------- Catálogos ----------
ClearCollect(colAreas, Filter(Areas, Activo = true));

// Opción "(Todos)" al inicio de los filtros por estado.
ClearCollect(colEstadosFiltro,
    { Valor: "(Todos)" },
    { Valor: "Borrador" },
    { Valor: "En revision legal" },
    { Valor: "En aprobacion" },
    { Valor: "Aprobado" },
    { Valor: "En firma" },
    { Valor: "Vigente" },
    { Valor: "Por vencer" },
    { Valor: "Vencido" },
    { Valor: "Renovado" },
    { Valor: "Terminado" },
    { Valor: "Rechazado" },
    { Valor: "Anulado" }
);

// ---------- Tema ----------
Set(gblTema,
    {
        // Marca. Reemplaza estos tres valores por los colores corporativos.
        Primario:       RGBA(11,  76, 140, 1),
        PrimarioOscuro: RGBA( 8,  56, 104, 1),
        PrimarioSuave:  RGBA(232, 240, 248, 1),

        // Superficies
        Fondo:      RGBA(245, 247, 250, 1),
        Tarjeta:    RGBA(255, 255, 255, 1),
        Borde:      RGBA(222, 226, 231, 1),

        // Texto
        Texto:      RGBA( 32,  38,  46, 1),
        TextoSuave: RGBA(105, 114, 126, 1),
        TextoClaro: RGBA(255, 255, 255, 1),

        // Estados semánticos
        Exito:      RGBA( 16, 124,  65, 1),
        Advertencia:RGBA(176, 112,   0, 1),
        Error:      RGBA(168,  35,  35, 1),
        Info:       RGBA( 11,  76, 140, 1),

        // Métricas de diseño
        Radio:      8,
        Espaciado:  16,
        FuenteTitulo: 20,
        FuenteBase:   14,
        FuenteMenor:  12
    }
);

Navigate(scrInicio, ScreenTransition.None);
```

---

## Parámetros adicionales que usa la app

Estas tres claves **no** las crea `Seed-DemoData.ps1` con valores reales: hay que
completarlas en la lista `Parametros` con los correos separados por `;`.

| Clave | Ejemplo | Qué controla |
|---|---|---|
| `ADMINS` | `ana@empresa.com;luis@empresa.com` | Acceso a la pantalla de administración |
| `CUSTODIOS` | `archivo@empresa.com` | Botones de préstamo y devolución |
| `LEGAL` | `legal@empresa.com` | Botón de visto bueno legal |

---

## Fórmulas reutilizables

Power Apps no tiene funciones de usuario en todas las versiones, así que estas
expresiones se repiten. Si tu entorno tiene **fórmulas con nombre** habilitadas
(`App.Formulas`), conviene declararlas ahí una sola vez.

### Color según el estado del contrato

```powerfx
Switch(
    ThisItem.Estado.Value,
    "Vigente",        gblTema.Exito,
    "Aprobado",       gblTema.Exito,
    "Por vencer",     gblTema.Advertencia,
    "En aprobacion",  gblTema.Info,
    "En revision legal", gblTema.Info,
    "En firma",       gblTema.Info,
    "Vencido",        gblTema.Error,
    "Rechazado",      gblTema.Error,
    "Anulado",        gblTema.TextoSuave,
    "Terminado",      gblTema.TextoSuave,
    gblTema.TextoSuave
)
```

### Días que faltan para el vencimiento

```powerfx
If(
    ThisItem.VigenciaIndefinida || IsBlank(ThisItem.FechaFin),
    Blank(),
    DateDiff(gblHoy, ThisItem.FechaFin, TimeUnit.Days)
)
```

### Monto convertido a la moneda base

```powerfx
ThisItem.Monto *
Switch(ThisItem.Moneda.Value, "USD", gblTCUSD, "EUR", gblTCEUR, 1)
```

### `App.Formulas` (opcional, recomendado)

```powerfx
ColorEstado(Estado As Text):
    Switch(Estado,
        "Vigente", gblTema.Exito,
        "Por vencer", gblTema.Advertencia,
        "Vencido", gblTema.Error,
        "Rechazado", gblTema.Error,
        gblTema.TextoSuave);

DiasParaVencer(Fin As DateTime, Indefinida As Boolean):
    If(Indefinida || IsBlank(Fin), Blank(), DateDiff(Today(), Fin, TimeUnit.Days));

MontoBase(Monto As Number, Moneda As Text):
    Monto * Switch(Moneda, "USD", gblTCUSD, "EUR", gblTCEUR, 1);
```

---

## Nota sobre delegación

La lista `Contratos` supera fácilmente los 2 000 elementos (límite predeterminado
de la app) y los 5 000 de la vista de SharePoint. Todas las consultas de esta app
se escribieron para **delegarse al servidor**. Las dos reglas que hay que
respetar al modificarlas:

1. **Filtrar solo por columnas indexadas** con operadores delegables:
   `=`, `<>`, `<`, `>`, `<=`, `>=`, `StartsWith`, `And`, `Or`, `Not`.
   Indexadas: `Estado`, `FechaFin`, `FechaPreaviso`, `TipoContrato`,
   `Contraparte`, `EstadoCustodia`, `NombreContrato`.

2. **No mezclar una condición constante con una de fila dentro del mismo
   `Filter`.** Esto rompe la delegación:

   ```powerfx
   // MAL: la comparación con "(Todos)" no depende de la fila,
   //      y obliga a Power Apps a traerse los datos para evaluarla.
   Filter(Contratos, cmbEstado.Selected.Valor = "(Todos)" || Estado.Value = cmbEstado.Selected.Valor)
   ```

   La forma correcta es decidir **fuera** del `Filter` cuál de las dos consultas
   delegables se ejecuta:

   ```powerfx
   // BIEN: dos ramas, cada una delegable por separado.
   If(cmbEstado.Selected.Valor = "(Todos)",
       Filter(Contratos, StartsWith(NombreContrato, txtBuscar.Text)),
       Filter(Contratos, Estado.Value = cmbEstado.Selected.Valor,
                         StartsWith(NombreContrato, txtBuscar.Text))
   )
   ```

`Search()`, `Sum()` y `CountRows()` sobre la lista completa **no se delegan** en
SharePoint. Donde hacen falta totales, la app cuenta sobre una colección ya
filtrada por el servidor.
