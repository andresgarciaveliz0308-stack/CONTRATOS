# Flujos de Power Automate

Seis flujos. Cada carpeta contiene el `definition.json` completo; esta guía
explica qué hace cada uno y cómo construirlo en el diseñador si la importación
del paquete no funciona.

| Flujo | Disparador | Conectores |
|---|---|---|
| [01 Solicitud de aprobación](#01--solicitud-de-aprobación) | Power Apps (V2) | SharePoint, Approvals, Outlook |
| [02 Envío a firma DocuSign](#02--envío-a-firma-docusign) | Elemento modificado | SharePoint, DocuSign, Outlook |
| [03 Retorno del firmado](#03--retorno-del-documento-firmado) | Sobre DocuSign cambia de estado | SharePoint, DocuSign, Outlook |
| [04 Alertas de vencimiento](#04--alertas-de-vencimiento) | Diario 08:00 | SharePoint, Outlook |
| [05 Numeración](#05--numeración-de-contratos) | Elemento creado | SharePoint |
| [06 Control de préstamos](#06--control-de-préstamos) | Diario 09:00 | SharePoint, Outlook |

**Antes de importar o construir:**

```powershell
./Build-Package.ps1 -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" -Empaquetar
```

```bash
python3 ../tools/validate-flows.py
```

---

## 05 · Numeración de contratos

Asigna `CTR-AAAA-NNNN` y calcula `FechaPreaviso`. Es el más simple: constrúyelo
primero para verificar que la conexión a SharePoint funciona.

**Disparador:** *SharePoint — Cuando se crea un elemento*, lista `Contratos`.

> **Configura la concurrencia del disparador en 1** (⋯ → *Configuración* →
> *Control de simultaneidad* → Activado, *Grado de paralelismo* = 1). Sin esto,
> dos contratos creados a la vez leen el mismo último correlativo y reciben el
> mismo código.

**Acciones:**

1. **Condición** — `empty(coalesce(triggerOutputs()?['body/Title'], ''))` es
   `true`. Todo lo demás va dentro de la rama *Sí*, para no renumerar cargas
   masivas o migraciones que ya traen código.
2. **Redactar** `Anio_actual` →
   `formatDateTime(convertFromUtc(utcNow(), 'SA Pacific Standard Time'), 'yyyy')`
   — ajusta la zona horaria si no operas en Lima.
3. **Redactar** `Clave_del_correlativo` → `concat('ULTIMO_CORRELATIVO_', outputs('Anio_actual'))`
4. **Obtener elementos** de `Parametros`, filtro `Title eq 'PREFIJO_CODIGO'`, 1 fila.
5. **Redactar** `Prefijo` → si vacío, `'CTR'`; si no, `first(...)?['Valor']`.
6. **Obtener elementos** de `Parametros` con la clave del año.
7. **Redactar** `Siguiente_numero` → `1` si no existe, o el anterior `+ 1`.
8. **Condición** → crear o actualizar el parámetro del año.
9. **Redactar** `Codigo_del_contrato` → relleno a 4 dígitos con `substring`.
10. **Redactar** `Calcular_fecha_de_preaviso` → `FechaFin − DiasPreaviso`, o
    `null` si la vigencia es indefinida.
11. **Actualizar elemento** en `Contratos`: `Title` y `FechaPreaviso`.
12. **Crear elemento** en `Bitacora`.

Las expresiones exactas están en `05-numeracion-contrato/definition.json`.

---

## 01 · Solicitud de aprobación

El más importante y el más largo (48 acciones). Resuelve los niveles contra
`MatrizAprobacion` y los ejecuta en serie.

**Disparador:** *Power Apps (V2)* con una entrada **numérica** llamada
`ContratoId`.

**Estructura:**

```
Inicializar varRechazado (booleano, false)
Inicializar varMotivo (cadena, "")
Obtener elemento · Contratos · ContratoId
Obtener CORREO_ADMIN_CONTRATOS
Obtener TC_<moneda>              ← filtro dinámico: Title eq 'TC_@{...Moneda/Value}'
Redactar Tipo_de_cambio          ← 1 si no existe el parámetro (caso PEN)
Redactar Monto_en_moneda_base    ← 999999999 si SinMontoDeterminado
Obtener elementos · MatrizAprobacion
    filtro: Activo eq 1
            and MontoDesdePEN le <monto> and MontoHastaPEN gt <monto>
            and (TipoContrato eq '<tipo>' or TipoContrato eq 'Todos')
    orden:  Nivel asc
Filtrar matriz → Reglas_del_tipo        (TipoContrato = el del contrato)
Filtrar matriz → Reglas_genericas       (TipoContrato = 'Todos')
Seleccionar → Niveles_brutos            (solo la columna Nivel)
Redactar Niveles → sort(union(x, x))    ← union() quita duplicados, sort() ordena

SI hay niveles:
    Actualizar Contratos → En aprobación, monto base, nivel requerido, ciclo +1
    Obtener elemento · Areas · AreaSolicitante/Id
    Redactar Enlace_al_contrato, Ciclo_actual
    ► Responder a Power Apps                ← AQUÍ, no al final
    Para cada nivel  (concurrencia = 1):
        SI varRechazado = false:
            Filtrar Reglas_del_tipo por este nivel
            Filtrar Reglas_genericas por este nivel
            Redactar Regla → la específica gana sobre la genérica
            Redactar Aprobador → según el rol
            SI hay aprobador:
                Crear elemento en Aprobaciones (Pendiente)
                Actualizar Contratos → NivelAprobacionActual
                Redactar Detalle_de_la_solicitud
                ► Iniciar y esperar una aprobación
                Actualizar Aprobaciones con la decisión
                SI rechazado: varRechazado = true, varMotivo = …
            SI NO:
                SI el nivel es obligatorio: detener + avisar al administrador
                SI NO: registrar el nivel como Omitido
    SI varRechazado = false: Aprobado + bitácora + correo
    SI NO:                   Rechazado + bitácora + correo
SI NO:
    Avisar al administrador + responder error a Power Apps
```

**Los tres puntos donde se suele fallar al construirlo:**

1. **Responder a Power Apps va en medio, no al final.** Una llamada desde Power
   Apps expira a los ~2 minutos y el workflow puede durar días. Si la respuesta
   queda al final, la app muestra un error de tiempo agotado aunque el flujo
   siga corriendo correctamente.

2. **La concurrencia del bucle debe ser 1.** ⋯ → *Configuración* → *Control de
   simultaneidad* → *Grado de paralelismo* = 1. Por omisión Power Automate
   paraleliza hasta 20 iteraciones, lo que enviaría **todos** los niveles de
   golpe y convertiría una aprobación secuencial en una simultánea.

3. **Un rechazo no puede cortar el bucle con Terminar.** `Terminar` abortaría el
   flujo entero y se perdería el cierre (marcar el contrato, avisar al
   solicitante). Por eso el cuerpo del bucle está envuelto en
   `SI varRechazado = false`: los niveles restantes se recorren sin hacer nada.

**Resolución del aprobador** (acción *Redactar* `Aprobador`):

| Rol en la matriz | De dónde sale el correo |
|---|---|
| `Jefe de area` | `Areas.Responsable.Email` del área del contrato |
| `Gerente de area` | `Areas.Gerente.Email` |
| Cualquier otro | `AprobadorGrupo` si está informado; si no, `AprobadorUsuario.Email` |

---

## 04 · Alertas de vencimiento

**Disparador:** *Periodicidad*, diaria a las 08:00, zona `SA Pacific Standard Time`.

**Primer bucle — contratos:**

```
Obtener DIAS_ALERTA_ESCALONADA → Hitos = split(valor, ',')
Obtener CORREO_ADMIN_CONTRATOS
Obtener elementos · Contratos
    filtro: (Estado eq 'Vigente' or Estado eq 'Por vencer')
            and VigenciaIndefinida ne 1 and FechaFin ne null
Para cada contrato (concurrencia 4):
    Dias_restantes = div(ticks(startOfDay(FechaFin)) − ticks(startOfDay(utcNow())), 864000000000)
    Debe_alertar   = dias < 0  OR  contains(Hitos, string(dias))
    SI Debe_alertar:
        Tipo_de_alerta   = Vencimiento | Renovacion automatica | Preaviso de vencimiento
        Dias_a_registrar = 0 si ya venció, si no los días
        Buscar en Alertas: mismo contrato + tipo + días
        SI no existe:
            Actualizar Contratos → Vencido | Por vencer
            Enviar correo al responsable, con copia al administrador
            Crear registro en Alertas
```

**Segundo bucle — garantías:** mismo patrón sobre los contratos con
`TieneGarantia eq 1` y `VencimientoGarantia` dentro de 30 días, notificando en
los hitos 30, 15, 7, 1 y 0.

> **El antiduplicado es la lista `Alertas`, no el estado del contrato.** Si se
> vacía esa lista, el flujo volverá a notificar todo lo que ya había notificado.

---

## 06 · Control de préstamos

**Disparador:** *Periodicidad*, diaria a las 09:00.

```
Obtener elementos · MovimientosCustodia
    filtro: TipoMovimiento eq 'Prestamo'
            and FechaDevolucionReal eq null
            and FechaCompromisoDevolucion ne null
            and FechaCompromisoDevolucion lt '<hoy>'
Para cada préstamo:
    Dias_de_atraso = hoy − compromiso
    Toca_reiterar  = atraso = 1  OR  mod(atraso, 7) = 0
    SI toca reiterar y el atraso es positivo:
        Obtener el contrato
        Reclamar por correo a quien lo tiene, con copia al custodio
        Registrar en Alertas
```

El escalonado (día 1, luego cada 7) es deliberado: reclamar a diario consigue
que la gente filtre el remitente, y entonces el control deja de existir.

---

## 02 · Envío a firma DocuSign

**Disparador:** *SharePoint — Cuando se modifica un elemento*, lista `Contratos`.

**Condición de entrada** (las tres deben cumplirse):

```
Estado = 'Aprobado'
  AND  coalesce(DocuSignEstado, 'No enviado') = 'No enviado'
  AND  DOCUSIGN_HABILITADO = true
```

Las dos primeras son lo que **evita el bucle infinito**: el propio flujo escribe
en el contrato al terminar (`En firma` / `Enviado`), lo que vuelve a disparar el
disparador; con esas guardas, la segunda pasada sale por el `else` sin hacer nada.

```
Buscar en DocumentosContratos: ContratoId eq <id> and EsPrincipal eq 1
SI hay documento:
    Obtener contenido del archivo
    DocuSign · Crear sobre (estado 'created')
    DocuSign · Agregar documento al sobre
    DocuSign · Agregar destinatario  — contraparte  (orden 1)
    DocuSign · Agregar destinatario  — responsable interno (orden 2)
    DocuSign · Enviar sobre
    Actualizar Contratos → En firma, Enviado, DocuSignEnvelopeId
    Crear registro en Bitacora
SI NO:
    Avisar al solicitante de que falta el documento principal
```

---

## 03 · Retorno del documento firmado

**Disparador:** *DocuSign — Cuando cambia el estado de un sobre*.

```
Buscar en Contratos: DocuSignEnvelopeId eq '<id del sobre>'
SI existe (si no, es un sobre ajeno a esta app y se ignora):
    Según el estado del sobre:
        completed → descargar documento combinado
                    crear archivo en DocumentosContratos
                    etiquetarlo (contrato, tipo 'Sobre firmado', firmado = sí)
                    Contratos → Vigente, Completado, FechaFirma
                    bitácora + correo al responsable
        declined  → Contratos → Rechazado, DocuSign Rechazado + correo
        voided    → Contratos → Aprobado, DocuSign No enviado, vaciar EnvelopeId
                    (deja el contrato listo para reintentar el envío)
        delivered → solo actualizar DocuSignEstado
        otros     → sin acción
```

> **Etiquetar el archivo no es opcional.** *Crear archivo* solo sube el binario;
> sin la acción *Actualizar elemento* posterior, el PDF firmado queda en la
> biblioteca sin vínculo con su contrato y desaparece del expediente.

---

## Sobre los conectores de DocuSign

Las acciones de DocuSign en los flujos 02 y 03 usan estos identificadores:

| Acción | `operationId` en el JSON |
|---|---|
| Crear sobre | `CreateBlankEnvelope` |
| Agregar documento | `AddDocumentToEnvelope` |
| Agregar destinatario | `AddRecipientToEnvelope` |
| Enviar sobre | `SendEnvelope` |
| Obtener documento combinado | `GetCombinedDocument` |
| Disparador de cambio de estado | `OnEnvelopeStatusChange` |

**Verifícalos en tu entorno.** Los identificadores de operación del conector de
DocuSign cambian entre versiones, y el nombre visible en el diseñador no siempre
coincide con el del JSON. Si una acción no se resuelve al importar, reemplázala
por la equivalente desde el diseñador: **la lógica alrededor —las guardas del
disparador, el archivado, el etiquetado y las transiciones de estado— es la parte
que importa y no depende del conector.**

Más detalle en [`../docs/07-docusign.md`](../docs/07-docusign.md).
