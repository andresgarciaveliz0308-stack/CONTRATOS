# 01 — Arquitectura

## Componentes

| Capa | Tecnología | Papel |
|---|---|---|
| Interfaz | Power Apps — aplicación de lienzo | Registro, consulta, custodia y administración |
| Datos | SharePoint Online (13 listas + 1 biblioteca) | Maestro de contratos, custodia documental y esquema configurable por categoría |
| Proceso | Power Automate (6 flujos) | Numeración, aprobación, firma, alertas, control de préstamos |
| Aprobación | Approvals (Power Automate) | Tarjetas de decisión en Teams y Outlook |
| Firma | DocuSign | Firma electrónica y devolución del sobre firmado |
| Notificación | Office 365 Outlook | Correos de alerta, rechazo y cargos de entrega |

## Flujo de un contrato de punta a punta

```
  Usuario registra en Power Apps
              │
              ▼
  [Flujo 05] asigna CTR-AAAA-NNNN y calcula la fecha de preaviso
              │
              ▼
  Se sube el PDF y se marca como documento principal
              │
              ▼
  Usuario pulsa "Enviar a aprobación"
              │
              ▼
  [Flujo 01] lee MatrizAprobacion ──► resuelve N niveles
              │                        (tipo de contrato + monto en moneda base)
              ▼
  Aprobación nivel 1 ──► nivel 2 ──► … ──► nivel N   (secuencial)
              │                │
         rechazo ◄─────────────┘
              │                          todos aprueban
              ▼                                │
  Estado = Rechazado                           ▼
  (corregir y reenviar: ciclo +1)      Estado = Aprobado
                                               │
                                               ▼
                                 [Flujo 02] crea y envía el sobre DocuSign
                                               │
                                               ▼
                                        Estado = En firma
                                               │
                                  firman todas las partes
                                               ▼
                                 [Flujo 03] archiva el PDF firmado
                                               │
                                               ▼
                                        Estado = Vigente
                                               │
                        ┌──────────────────────┴───────────────────┐
                        ▼                                          ▼
      [Flujo 04] preaviso · vencimiento · garantías    Custodia del original:
      Por vencer ──► Vencido ──► Renovado              recepción, préstamo,
                                                        devolución [Flujo 06]
```

---

## Por qué SharePoint y no Dataverse

Ambas opciones resuelven el problema. La diferencia decide el costo y el tipo
de trabajo posterior.

| | SharePoint Online | Dataverse |
|---|---|---|
| **Licencia** | Incluida en Microsoft 365 | Power Apps Premium por usuario (~20 USD/usuario/mes) |
| **Custodia documental** | Nativa: versionado, retención, coautoría, búsqueda de texto en PDF | Requiere almacenamiento de archivos aparte o integración con SharePoint |
| **Modelo relacional** | Búsquedas simples, sin integridad referencial real | Relaciones reales, cascadas, claves alternativas |
| **Seguridad** | Por lista y por elemento; se degrada con muchos permisos únicos | Roles por fila y por columna, unidades de negocio |
| **Auditoría** | Historial de versiones por elemento | Auditoría nativa configurable |
| **Escala cómoda** | Decenas de miles de elementos con columnas indexadas | Millones |

**La decisión aquí fue SharePoint** porque el peso del problema está en la
*custodia documental* —versionar PDF, retenerlos, buscarlos— que es justo lo que
SharePoint hace de forma nativa, y porque evita una licencia premium por cada
usuario que solo consulta contratos.

**Cuándo conviene migrar a Dataverse:** si aparece alguno de estos, el costo de
la licencia deja de ser el factor dominante.

- Más de ~50 000 contratos, o varias listas rozando el umbral de 5 000 por vista.
- Necesidad de seguridad **por columna** (p. ej. que el monto solo lo vean
  Finanzas y Gerencia).
- Integración con ERP o con procesos que exijan transacciones.
- Requisito de auditoría formal a nivel de campo.

El modelo de datos de `docs/02-modelo-datos.md` se traduce a tablas de Dataverse
casi uno a uno; lo que habría que reescribir son los flujos (conector distinto) y
las consultas de la app.

---

## Licenciamiento

| Componente | Requiere premium |
|---|---|
| Power Apps sobre SharePoint | **No** — incluido en M365 |
| SharePoint Online | **No** |
| Power Automate con SharePoint, Outlook, Approvals | **No** |
| **Conector de DocuSign** | **Sí** — Power Automate Premium para el propietario de los flujos 02 y 03 |

La firma electrónica es la única pieza que obliga a una licencia adicional. Si se
apaga (`DOCUSIGN_HABILITADO = false` en `Parametros`), el resto del sistema
funciona completo sin ninguna licencia premium: los contratos aprobados pasan a
firma manual y el PDF firmado se sube a la biblioteca.

> Además de la licencia, DocuSign requiere su propia suscripción y una cuenta de
> servicio. Ver [`07-docusign.md`](07-docusign.md).

---

## Límites que condicionan el diseño

| Límite | Valor | Cómo se sortea |
|---|---|---|
| Umbral de vista de lista de SharePoint | 5 000 elementos | Columnas indexadas y vistas siempre filtradas |
| Delegación en Power Apps | 500 (2 000 configurable) | Consultas delegables; `Sum`/`CountRows` solo sobre colecciones ya filtradas |
| Llamada a un flujo desde Power Apps | ~120 s | El flujo 01 responde **antes** de esperar las aprobaciones |
| Ejecuciones de Power Automate | Según plan | Los disparadores llevan condiciones que cortan temprano |
| Adjuntos de Power Apps | Solo datos adjuntos de elemento | La biblioteca se alimenta desde SharePoint o desde un flujo |

---

## Decisiones de diseño

**La matriz de aprobación es datos, no código.** Quién aprueba vive en la lista
`MatrizAprobacion`. Cambiar el umbral de un tramo o el aprobador de un nivel no
requiere abrir Power Automate ni volver a publicar nada. Es la diferencia entre
que el proceso lo mantenga Administración o que dependa de quien sepa editar
flujos.

**Los niveles se congelan al enviar.** El flujo resuelve la ruta en el momento
del envío y la escribe en `Aprobaciones`. Si después se cambia la matriz, los
contratos que ya están circulando conservan su ruta. Mover la ruta bajo los pies
de quienes ya la están recorriendo produciría aprobaciones huérfanas y niveles
duplicados.

**El historial de aprobaciones es inmutable.** `Aprobaciones` y `Bitacora` se
crean con el nivel de permiso *Solo agregar*: ni quien aprobó puede reescribir lo
que aprobó. Es lo que las convierte en evidencia y no en un registro más.

**Un rechazo no borra nada.** Abre un ciclo nuevo (`CicloAprobacion + 1`). El
historial completo de intentos queda visible en la ficha del contrato.

**Nadie elimina expedientes.** `Contratos` y `DocumentosContratos` usan el nivel
*Aportar sin eliminar*. Solo un administrador puede borrar, y el historial de
versiones de SharePoint conserva el resto.

**La custodia física se modela como movimientos, no como estado.** Un campo
«dónde está» se pierde en cuanto alguien se olvida de actualizarlo. La lista
`MovimientosCustodia` registra cada entrega y cada devolución, de modo que el
estado actual es *derivable* y el flujo 06 puede reclamar lo que no volvió.

**El antiduplicado de alertas vive en datos.** Antes de notificar, el flujo 04
verifica que no exista ya un registro en `Alertas` con la misma combinación de
contrato, tipo y días de anticipación. Sin eso, una ejecución repetida o un
reintento llenaría los buzones y la gente dejaría de leer las alertas.
