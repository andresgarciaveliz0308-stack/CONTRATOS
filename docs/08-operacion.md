# 08 — Operación y soporte

## Rutina de mantenimiento

| Frecuencia | Tarea | Por qué |
|---|---|---|
| **Diaria** | Revisar ejecuciones fallidas de los 6 flujos | Un flujo caído no avisa: los contratos simplemente dejan de avanzar |
| **Semanal** | Revisar aprobaciones con SLA vencido | Un contrato detenido rara vez se reclama solo |
| **Semanal** | Revisar préstamos de originales sin devolver | |
| **Mensual** | Actualizar `TC_USD` y `TC_EUR` | Un tipo de cambio viejo manda contratos por el tramo de aprobación equivocado |
| **Mensual** | Revisar contratos vencidos sin cerrar | Higiene del maestro |
| **Trimestral** | Verificar que las conexiones de los flujos siguen autenticadas | **Una conexión caducada detiene todo en silencio** |
| **Trimestral** | Revisar la matriz de aprobación contra la realidad de la organización | La gente cambia de puesto |
| **Trimestral** | Revisar `Areas`: responsables y gerentes al día | Un área sin responsable detiene sus contratos |
| **Anual** | Revisar `ADMINS`, `CUSTODIOS`, `LEGAL` y los grupos de SharePoint | |
| **Anual** | Purgar `Alertas` con más de 2 años | Es la lista que más crece |

### Las dos que más duelen si se omiten

**Conexiones caducadas.** No producen un error visible para el usuario. Los
contratos se envían, nadie recibe nada, y el problema se descubre semanas después
cuando alguien pregunta por qué su contrato sigue «en aprobación». Revisa en
*Power Automate → Conexiones* que ninguna diga *Se requiere corregir*.

**Tipos de cambio desactualizados.** Un contrato de 30 000 USD con `TC_USD = 3.20`
en lugar de `3.75` se evalúa en 96 000 en vez de 112 500. Si el tramo corta en
100 000, se salta dos niveles de aprobación sin que nadie lo note.

---

## Monitoreo de los flujos

**Power Automate → Mis flujos → [flujo] → Historial de ejecución.**

| Flujo | Frecuencia esperada | Señal de alarma |
|---|---|---|
| 05 Numeración | Una por contrato creado | Contratos sin código |
| 01 Solicitud de aprobación | Una por envío | Ejecuciones «En ejecución» durante días — normal: está esperando al aprobador |
| 02 DocuSign envío | Una por contrato aprobado | Más de una por contrato = las guardas del disparador se rompieron |
| 03 DocuSign retorno | Una por cambio de estado de sobre | Ninguna tras enviar un sobre = flujo o conexión caída |
| 04 Alertas | Una al día a las 08:00 | Ninguna hoy |
| 06 Préstamos | Una al día a las 09:00 | Ninguna hoy |

> Una ejecución del flujo 01 marcada **«En ejecución»** durante días es **normal**:
> está suspendida en *Iniciar y esperar una aprobación*. No la canceles: cancelarla
> deja el contrato en `En aprobación` para siempre, sin tarea viva que lo resuelva.

### Alerta sobre los propios flujos

Power Automate puede avisar cuando un flujo falla:
*Configuración del flujo → Analítica → Notificaciones de error*. Actívalo al menos
en los flujos 01, 04 y 05, y dirígelo a un buzón que alguien lea.

---

## Diagnóstico

### Un contrato se quedó en «En aprobación»

1. Abre la pestaña **Aprobaciones** de la ficha: el último registro `Pendiente`
   dice en qué nivel está y a quién se asignó.
2. Si el aprobador es correcto pero nunca recibió nada, revisa el historial del
   flujo 01. Busca esa ejecución: si está *En ejecución*, la tarea existe y el
   problema es de notificación (revisa la bandeja de Approvals del aprobador
   directamente).
3. Si la ejecución **falló**, el error suele ser uno de estos tres:

   | Error | Causa | Solución |
   |---|---|---|
   | 403 al escribir en `Aprobaciones` | La cuenta dueña del flujo no está en `Contratos - Administradores` | Agregarla al grupo y reenviar el contrato |
   | «El destinatario no es válido» | El aprobador resuelto no tiene correo válido | Revisar la regla en `MatrizAprobacion` o el responsable del área |
   | Conexión caducada | Credenciales expiradas | Reautenticar y reenviar |

4. Si la ejecución se **canceló**, no hay forma de reanudarla. Vuelve a poner el
   contrato en `Borrador` y reenvíalo: se abrirá un ciclo nuevo.

### «No hay reglas de aprobación configuradas»

Ningún tramo de `MatrizAprobacion` cubre ese monto para ese tipo de contrato.

Usa el **simulador** de la pantalla de administración con los mismos datos: te
dirá si el problema es un hueco entre tramos o un tramo que no llega hasta ese
monto. Recuerda que los tramos usan `≥ desde` y `< hasta`, así que el `hasta` de
uno debe ser exactamente el `desde` del siguiente.

### Un nivel se detiene siempre

La pantalla de administración lista las **reglas activas sin aprobador** y las
**áreas sin responsable**. Casi siempre es una de las dos.

### Alertas duplicadas

El antiduplicado es la lista `Alertas`: antes de notificar, el flujo comprueba que
no exista ya un registro con el mismo contrato, tipo y días de anticipación. Si se
vació esa lista, volverá a notificar todo.

Si hay duplicados **sin** haber tocado `Alertas`, revisa que el flujo 04 no se haya
importado dos veces.

### La app avisa de delegación

Se agregó un filtro sobre una columna no indexada, o se mezcló una condición
constante con una de fila dentro del mismo `Filter`. Las reglas y el patrón
correcto están en `canvas-app/formulas/00-app-y-tema.md`.

### Los montos se leen mal (3.75 se convierte en 375)

`Value()` sin el parámetro `"en-US"` en un equipo con configuración regional en
español, donde el separador decimal es la coma. El `OnStart` ya lo contempla;
revisa cualquier fórmula agregada después.

---

## Crecimiento y umbrales

| Lista | Crece con | Umbral a vigilar |
|---|---|---|
| `Contratos` | Contratos nuevos | 5 000 (vista de SharePoint) |
| `DocumentosContratos` | ~3–5 por contrato | 5 000 |
| `Aprobaciones` | Niveles × ciclos | El que más crece: 5 niveles = 5 filas por envío |
| `Alertas` | ~6 por contrato y año | Purgar anualmente |
| `Bitacora` | Acciones de la app | Purgar cada 2–3 años |

Las columnas indexadas hacen que las consultas sigan funcionando por encima del
umbral, pero **las vistas de SharePoint sin filtro dejarán de abrirse**. Las vistas
que crea el script ya vienen filtradas; si alguien crea una vista nueva sin filtro,
fallará.

### Señales de que conviene migrar a Dataverse

- `Contratos` supera los ~50 000 elementos.
- Se necesita seguridad **por columna** (que el monto solo lo vea Finanzas).
- Hace falta integración transaccional con un ERP.
- Se requiere auditoría formal a nivel de campo.

Ver la comparación en [`01-arquitectura.md`](01-arquitectura.md#por-qué-sharepoint-y-no-dataverse).

---

## Respaldo

SharePoint Online **ya conserva**:

- Papelera de reciclaje: 93 días en dos niveles.
- Historial de versiones de cada elemento y documento.
- Retención del servicio de Microsoft.

**Esto no es un respaldo.** No protege contra un borrado masivo descubierto tarde,
ni contra un error de configuración que corrompa datos progresivamente.

Para respaldo real:

| Alcance | Herramienta |
|---|---|
| Listas y biblioteca completas | Solución de backup de terceros para M365 |
| Exportación periódica | `Get-PnPListItem` + `Export-Csv` programado |
| Definición del sitio | `Get-PnPSiteTemplate` — permite recrear la estructura |
| Definiciones de flujos | **Este repositorio** |
| Código de la app | **Este repositorio**, más *Exportar paquete* de Power Apps |

Exportación mínima recomendada, mensual:

```powershell
Connect-PnPOnline -Url $SiteUrl -Interactive -ClientId $ClientId
$fecha = Get-Date -Format 'yyyyMMdd'
foreach ($lista in @('Contratos','Aprobaciones','MatrizAprobacion',
                     'MovimientosCustodia','Adendas','Areas','Parametros')) {
    Get-PnPListItem -List $lista -PageSize 2000 |
        ForEach-Object { $_.FieldValues } |
        Export-Csv "./backup/$fecha-$lista.csv" -NoTypeInformation -Encoding UTF8
}
```

---

## Control de cambios

Todo cambio en flujos o en la app debería pasar por este repositorio:

1. Editar el `definition.json` o el `.fx.yaml` correspondiente.
2. Validar:
   ```bash
   python3 tools/validate-flows.py
   python3 tools/validate-canvas-yaml.py
   ```
3. Confirmar los cambios con un mensaje que explique **por qué**, no solo qué.
4. Desplegar en el entorno.

Los cambios hechos directamente en el diseñador se pierden como conocimiento: seis
meses después nadie recuerda por qué una condición está donde está. Si hay que
hacer un cambio urgente en caliente, tráelo de vuelta al repositorio después.

### Cambios que no requieren tocar nada de esto

Por diseño, estos se hacen editando datos:

- Quién aprueba, en qué nivel y en qué tramo de monto → `MatrizAprobacion`
- Responsables y gerentes de área → `Areas`
- Tipos de cambio, correos, hitos de alerta, SLA → `Parametros`
- Activar o desactivar la firma electrónica → `DOCUSIGN_HABILITADO`

Que estos cambios no requieran un despliegue es el punto: el proceso lo mantiene
quien lo entiende, no quien sabe editar flujos.
