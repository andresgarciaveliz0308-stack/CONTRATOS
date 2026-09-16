# 02 — Modelo de datos

Todo vive en un único sitio de SharePoint Online (`/sites/Contratos`): **9 listas** y
**1 biblioteca de documentos**.

> **Regla de oro:** los *nombres internos* de las columnas (columna «Interno» en las
> tablas) son los que usan Power Fx y Power Automate. Nunca los cambies. Los nombres
> visibles sí se pueden renombrar libremente desde la interfaz.

```
                          ┌──────────────┐
                          │    Areas     │
                          └──────┬───────┘
                                 │ 1:N
┌──────────────┐          ┌──────▼───────┐          ┌──────────────────────┐
│MatrizAprobac.│ ───────▶ │  CONTRATOS   │ ◀─────── │ DocumentosContratos  │
│ (reglas)     │  aplica  │  (maestro)   │   1:N    │ (biblioteca)         │
└──────────────┘          └──────┬───────┘          └──────────────────────┘
                                 │ 1:N
        ┌────────────┬───────────┼───────────┬────────────┐
        ▼            ▼           ▼           ▼            ▼
  ┌──────────┐ ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌──────────┐
  │Aprobacion│ │ Adendas │ │Movimient.│ │ Alertas │ │ Bitacora │
  │    es    │ │         │ │ Custodia │ │         │ │          │
  └──────────┘ └─────────┘ └──────────┘ └─────────┘ └──────────┘

  ┌────────────┐
  │ Parametros │  (configuración global: tipo de cambio, correos, SLA)
  └────────────┘
```

---

## 1. `Contratos` — maestro de contratos

Lista principal. Una fila = un contrato.

### Identificación

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Código | `Title` | Texto | `CTR-AAAA-NNNN`. Lo genera el flujo 05, no se escribe a mano. |
| Nombre del contrato | `NombreContrato` | Texto (255) | Obligatorio. |
| Tipo de contrato | `TipoContrato` | Elección | Obligatorio. Ver catálogo abajo. |
| Objeto del contrato | `ObjetoContrato` | Nota | Descripción del alcance. |
| Contrato relacionado | `ContratoPadre` | Búsqueda → `Contratos` | Se usa al renovar: apunta al contrato original. |

### Contraparte

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Contraparte | `Contraparte` | Texto (255) | Razón social. Obligatorio. |
| RUC / Doc. identidad | `ContraparteRUC` | Texto (20) | |
| Tipo de contraparte | `TipoContraparte` | Elección | Proveedor · Cliente · Empleado · Socio comercial · Entidad pública · Otro |
| Contacto de la contraparte | `ContraparteContacto` | Texto | Nombre del firmante. |
| Correo de la contraparte | `ContraparteCorreo` | Texto | **Obligatorio si se firma con DocuSign** — es el destinatario del sobre. |

### Organización interna

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Área solicitante | `AreaSolicitante` | Búsqueda → `Areas` | Obligatorio. Determina la ruta de aprobación. |
| Solicitante | `Solicitante` | Persona | Se autocompleta con el usuario que registra. |
| Responsable del contrato | `ResponsableContrato` | Persona | Dueño funcional; recibe las alertas de vencimiento. |

### Económicos

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Moneda | `Moneda` | Elección | PEN · USD · EUR |
| Monto | `Monto` | Número (2 dec.) | Monto en la moneda original. |
| Monto en PEN | `MontoPEN` | Número (2 dec.) | **Calculado por flujo.** Es el valor contra el que se evalúa la matriz de aprobación. |
| Tipo de cambio aplicado | `TipoCambio` | Número (4 dec.) | Se congela al momento del envío a aprobación. |
| Monto no determinado | `SinMontoDeterminado` | Sí/No | Para contratos a demanda. Fuerza el nivel máximo de aprobación. |

> El monto se normaliza a PEN porque la matriz de aprobación trabaja con un único
> tramo de montos. Si trabajas en otra moneda base, cambia el parámetro
> `MONEDA_BASE` en la lista `Parametros`.

### Vigencia

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Fecha de inicio | `FechaInicio` | Fecha | Obligatorio. |
| Fecha de fin | `FechaFin` | Fecha | Obligatorio salvo vigencia indefinida. |
| Vigencia indefinida | `VigenciaIndefinida` | Sí/No | Si es Sí, se excluye de las alertas de vencimiento. |
| Renovación automática | `RenovacionAutomatica` | Sí/No | Cambia el texto de la alerta: el aviso es para **no** renovar. |
| Días de preaviso | `DiasPreaviso` | Número | Predeterminado 30. |
| Fecha de preaviso | `FechaPreaviso` | Fecha | **Calculada por flujo** = `FechaFin - DiasPreaviso`. Indexada. |

### Estado y aprobación

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Estado | `Estado` | Elección | Ver máquina de estados abajo. Indexada. |
| Nivel requerido | `NivelAprobacionRequerido` | Número | Cuántos niveles resolvió la matriz. |
| Nivel actual | `NivelAprobacionActual` | Número | Nivel que está pendiente en este momento. |
| Ciclo de aprobación | `CicloAprobacion` | Número | Se incrementa en cada reenvío tras un rechazo. |
| Fecha de envío a aprobación | `FechaEnvioAprobacion` | Fecha y hora | |
| Fecha de aprobación final | `FechaAprobacionFinal` | Fecha y hora | |
| Motivo de rechazo | `MotivoRechazo` | Nota | Último comentario de rechazo. |

### Firma electrónica

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Sobre DocuSign | `DocuSignEnvelopeId` | Texto (100) | ID del *envelope*. |
| Estado DocuSign | `DocuSignEstado` | Elección | No enviado · Enviado · Entregado · Firmado · Completado · Rechazado · Anulado |
| Fecha de firma | `FechaFirma` | Fecha y hora | |

### Custodia del original

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Estado de custodia | `EstadoCustodia` | Elección | Pendiente de recepción · En custodia · Prestado · Solo digital · Dado de baja |
| Custodio | `Custodio` | Persona | Responsable del original físico. |
| Ubicación física | `UbicacionFisica` | Texto | Formato sugerido: `Archivador 03 / Caja 12 / Folio 245`. |
| Fecha de recepción del original | `FechaRecepcionOriginal` | Fecha | |

### Riesgo y cumplimiento

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Clasificación | `Clasificacion` | Elección | Público · Interno · Confidencial · Restringido. Controla la visibilidad. |
| Obligaciones clave | `ObligacionesClave` | Nota | Entregables, SLA, hitos. |
| Penalidades | `Penalidades` | Nota | |
| Tiene garantía | `TieneGarantia` | Sí/No | |
| Tipo de garantía | `TipoGarantia` | Elección | Carta fianza · Retención · Depósito en garantía · Póliza de caución · Otra |
| Monto de garantía | `MontoGarantia` | Número | |
| Vencimiento de garantía | `VencimientoGarantia` | Fecha | Genera su propia alerta (flujo 04). |
| Notas | `Notas` | Nota | Con historial de versiones activado. |

### Catálogo `TipoContrato`

`Servicios` · `Suministro de bienes` · `Obra` · `Arrendamiento` · `Confidencialidad (NDA)` ·
`Licencia de software` · `Distribución` · `Agencia / Representación` · `Laboral` ·
`Seguros` · `Financiero` · `Convenio / Addendum marco` · `Otro`

### Máquina de estados

```
  Borrador
     │  (enviar)
     ▼
  En revisión legal ──────► Rechazado ──► (corregir) ──► Borrador
     │  (visto bueno)
     ▼
  En aprobación  ◀──── reenvío (ciclo +1)
     │                        ▲
     │ (todos los niveles)    │ rechazo
     ▼                        │
  Aprobado ───────────────────┘
     │  (flujo 02)
     ▼
  En firma ──► (DocuSign rechazado) ──► Rechazado
     │  (sobre completado)
     ▼
  Vigente ──► Por vencer ──► Vencido
     │             │
     │             └──► Renovado ──► (nuevo contrato hijo)
     ▼
  Terminado / Anulado
```

`Por vencer` y `Vencido` los asigna automáticamente el flujo 04. El resto son
transiciones de la app o de los flujos de aprobación y firma.

---

## 2. `DocumentosContratos` — biblioteca de custodia digital

Biblioteca de documentos con **control de versiones mayor y menor activado** y
**exigir desprotección desactivado**.

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Nombre | `FileLeafRef` | Archivo | Convención: `CTR-AAAA-NNNN_TipoDoc_vN.pdf` |
| Contrato | `Contrato` | Búsqueda → `Contratos` | Obligatorio. |
| Tipo de documento | `TipoDocumento` | Elección | Contrato original · Adenda · Anexo · Cotización · Orden de compra · Carta fianza · Acta de recepción · Sustento de aprobación · Sobre firmado · Otro |
| Versión del documento | `VersionDocumento` | Texto | Versión de negocio (`v1`, `v2 final`), distinta del versionado de SharePoint. |
| Fecha del documento | `FechaDocumento` | Fecha | |
| Es documento principal | `EsPrincipal` | Sí/No | Marca el PDF que se envía a DocuSign. **Solo uno por contrato.** |
| Está firmado | `EstaFirmado` | Sí/No | Lo marca el flujo 03. |
| Confidencial | `EsConfidencial` | Sí/No | |

---

## 3. `MatrizAprobacion` — reglas de aprobación

El corazón configurable del workflow. Cambiar quién aprueba **no requiere tocar el
flujo**: se edita esta lista.

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Regla | `Title` | Texto | Etiqueta descriptiva, p. ej. `Servicios 0–50k · Nivel 1`. |
| Tipo de contrato | `TipoContrato` | Elección | Mismo catálogo que `Contratos`, más `Todos`. |
| Monto desde (PEN) | `MontoDesdePEN` | Número | Inclusivo. |
| Monto hasta (PEN) | `MontoHastaPEN` | Número | Exclusivo. Usa `999999999` para «sin tope». |
| Nivel | `Nivel` | Número | 1, 2, 3… Se ejecutan en orden ascendente. |
| Rol del aprobador | `RolAprobador` | Elección | Jefe de área · Gerente de área · Legal · Finanzas · Compras · Gerencia General · Directorio · Usuario específico |
| Aprobador (usuario) | `AprobadorUsuario` | Persona | Obligatorio si el rol es `Usuario específico`. |
| Aprobador (grupo) | `AprobadorGrupo` | Texto | Correo del grupo. Si se llena, **cualquiera** del grupo puede aprobar. |
| Obligatorio | `Obligatorio` | Sí/No | Si es No y no se resuelve el aprobador, el nivel se marca `Omitido`. |
| SLA (horas) | `SLAHoras` | Número | Horas antes del recordatorio automático. |
| Activo | `Activo` | Sí/No | Permite desactivar una regla sin borrarla. |

**Resolución de reglas:** el flujo filtra por `Activo = Sí`, `TipoContrato = <el del
contrato> o Todos`, y `MontoDesdePEN ≤ MontoPEN < MontoHastaPEN`; luego ordena por
`Nivel`. Las reglas con `TipoContrato` específico **ganan** sobre las de `Todos` en el
mismo nivel.

---

## 4. `Aprobaciones` — historial (solo lectura para el usuario)

Un registro por cada nivel de cada ciclo. Nunca se borra: es la evidencia de auditoría.

| Visible | Interno | Tipo |
|---|---|---|
| Referencia | `Title` | Texto (`CTR-2026-0042 · N1 · C1`) |
| Contrato | `Contrato` | Búsqueda → `Contratos` |
| Nivel | `Nivel` | Número |
| Ciclo | `Ciclo` | Número |
| Rol del aprobador | `RolAprobador` | Texto |
| Aprobador asignado | `AprobadorAsignado` | Persona |
| Resuelto por | `ResueltoPor` | Persona |
| Decisión | `Decision` | Elección: Pendiente · Aprobado · Rechazado · Devuelto · Delegado · Omitido · Vencido |
| Comentarios | `Comentarios` | Nota |
| Fecha de solicitud | `FechaSolicitud` | Fecha y hora |
| Fecha de decisión | `FechaDecision` | Fecha y hora |
| Horas transcurridas | `HorasTranscurridas` | Número |
| Instancia del flujo | `InstanciaFlujo` | Texto (GUID del run) |

---

## 5. `Adendas`

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Código | `Title` | Texto | `CTR-2026-0042-AD01` |
| Contrato | `Contrato` | Búsqueda → `Contratos` | |
| Número de adenda | `NumeroAdenda` | Número | |
| Tipo de adenda | `TipoAdenda` | Elección | Prórroga de plazo · Ampliación de monto · Reducción de monto · Cambio de alcance · Cesión de posición · Resolución anticipada · Otro |
| Fecha de la adenda | `FechaAdenda` | Fecha | |
| Variación de monto | `MontoDelta` | Número | Puede ser negativa. |
| Nueva fecha de fin | `NuevaFechaFin` | Fecha | Al aprobarse, actualiza `FechaFin` del contrato. |
| Descripción | `Descripcion` | Nota | |
| Estado | `Estado` | Elección | Borrador · En aprobación · Aprobada · Rechazada |

Una adenda que modifica monto o plazo **vuelve a pasar por la matriz de aprobación**,
evaluada sobre el monto acumulado (`MontoPEN + ΣMontoDelta`).

---

## 6. `MovimientosCustodia` — cadena de custodia del original

| Visible | Interno | Tipo | Notas |
|---|---|---|---|
| Referencia | `Title` | Texto | `MOV-AAAA-NNNN` |
| Contrato | `Contrato` | Búsqueda → `Contratos` | |
| Tipo de movimiento | `TipoMovimiento` | Elección | Recepción de original · Préstamo · Devolución · Traslado · Digitalización · Baja / Destrucción |
| Fecha del movimiento | `FechaMovimiento` | Fecha y hora | |
| Solicitado por | `SolicitadoPor` | Persona | Quien se lleva el documento. |
| Entregado por | `EntregadoPor` | Persona | El custodio. |
| Ubicación origen | `UbicacionOrigen` | Texto | |
| Ubicación destino | `UbicacionDestino` | Texto | |
| Compromiso de devolución | `FechaCompromisoDevolucion` | Fecha | Alimenta el flujo 06. |
| Devolución real | `FechaDevolucionReal` | Fecha | Vacío = préstamo abierto. |
| Acta firmada | `ActaFirmada` | Sí/No | |
| Observaciones | `Observaciones` | Nota | Estado físico del documento. |

---

## 7. `Areas`

| Visible | Interno | Tipo |
|---|---|---|
| Área | `Title` | Texto |
| Código | `CodigoArea` | Texto |
| Responsable | `Responsable` | Persona |
| Gerente | `Gerente` | Persona |
| Centro de costo | `CentroCosto` | Texto |
| Activo | `Activo` | Sí/No |

`Responsable` y `Gerente` son los que resuelven los roles `Jefe de área` y
`Gerente de área` de la matriz de aprobación.

---

## 8. `Parametros` — configuración global

| Clave (`Title`) | Ejemplo de valor | Para qué sirve |
|---|---|---|
| `MONEDA_BASE` | `PEN` | Moneda en la que se evalúa la matriz. |
| `TC_USD` | `3.75` | Tipo de cambio USD → moneda base. |
| `TC_EUR` | `4.05` | Tipo de cambio EUR → moneda base. |
| `DIAS_PREAVISO_DEFAULT` | `30` | Preaviso por defecto de contratos nuevos. |
| `DIAS_ALERTA_ESCALONADA` | `90,60,30,15,7,1` | Hitos de alerta antes del vencimiento. |
| `CORREO_LEGAL` | `legal@empresa.com` | Buzón de revisión legal. |
| `CORREO_ADMIN_CONTRATOS` | `contratos@empresa.com` | Buzón del administrador. |
| `TEAMS_CANAL_ALERTAS` | `<id del canal>` | Canal de Teams para las alertas. |
| `SLA_APROBACION_HORAS` | `48` | SLA por defecto si la regla no lo define. |
| `DOCUSIGN_HABILITADO` | `true` | Interruptor general de la firma electrónica. |
| `DOCUSIGN_TEMPLATE_ID` | `<guid>` | Plantilla opcional de DocuSign. |
| `RETENCION_ANIOS` | `10` | Años de retención tras la terminación. |

Columnas: `Title` (clave), `Valor` (texto), `Descripcion` (nota), `Tipo` (elección).

---

## 9. `Alertas` — bitácora de notificaciones

Evita alertas duplicadas: antes de notificar, el flujo 04 verifica que no exista ya un
registro con el mismo `Contrato` + `TipoAlerta` + `DiasAnticipacion`.

| Visible | Interno | Tipo |
|---|---|---|
| Referencia | `Title` | Texto |
| Contrato | `Contrato` | Búsqueda → `Contratos` |
| Tipo de alerta | `TipoAlerta` | Elección: Preaviso de vencimiento · Vencimiento · Renovación automática · Vencimiento de garantía · Préstamo vencido · Aprobación pendiente · SLA vencido |
| Días de anticipación | `DiasAnticipacion` | Número |
| Fecha de envío | `FechaEnvio` | Fecha y hora |
| Destinatarios | `Destinatarios` | Texto |
| Canal | `Canal` | Elección: Correo · Teams · Ambos |

---

## 10. `Bitacora` — auditoría funcional

Registra las acciones de la app que no quedan en el historial de versiones.

| Visible | Interno | Tipo |
|---|---|---|
| Referencia | `Title` | Texto |
| Contrato | `Contrato` | Búsqueda → `Contratos` |
| Acción | `Accion` | Texto (`Creación`, `Cambio de estado`, `Descarga de documento`, `Préstamo`…) |
| Usuario | `Usuario` | Persona |
| Fecha | `Fecha` | Fecha y hora |
| Detalle | `Detalle` | Nota |

---

## Índices y delegación

SharePoint solo delega consultas eficientes sobre **columnas indexadas** y el umbral de
vista de lista es de **5 000 elementos**. El script de despliegue crea estos índices:

| Lista | Columnas indexadas |
|---|---|
| `Contratos` | `Estado`, `FechaFin`, `FechaPreaviso`, `TipoContrato`, `Contraparte`, `EstadoCustodia` |
| `Aprobaciones` | `Contrato`, `Decision` |
| `DocumentosContratos` | `Contrato` |
| `MovimientosCustodia` | `Contrato`, `FechaDevolucionReal` |
| `Alertas` | `Contrato` |

**Funciones delegables** que usa la app sobre estas columnas: `Filter`, `Search`,
`LookUp`, `SortByColumns` con `=`, `<>`, `<`, `>`, `StartsWith`, `And`, `Or`.
**No delegables** (evitadas en el código): `Sum`, `CountRows` sobre la lista completa,
`in` sobre texto, `Search` en columnas Nota. La app carga los indicadores del tablero
con colecciones pre-filtradas para no chocar con el límite.
