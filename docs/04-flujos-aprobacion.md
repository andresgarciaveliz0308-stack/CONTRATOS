# 04 — Workflow de aprobaciones

## La idea central

**Quién aprueba es un dato, no código.** Vive en la lista `MatrizAprobacion`.
Cambiar un umbral o un aprobador se hace editando una fila, desde la pantalla de
administración de la app o desde SharePoint. No hay que abrir Power Automate ni
volver a publicar nada.

Eso significa que el proceso lo puede mantener quien lo entiende —Administración,
Legal— y no depende de quien sepa editar flujos.

---

## Cómo se resuelve la ruta

Cuando alguien pulsa **Enviar a aprobación**, el flujo 01 hace esto:

### 1. Normaliza el monto

Todo se evalúa en una sola moneda (`MONEDA_BASE`, por defecto PEN):

```
MontoPEN = Monto × tipo de cambio de la moneda del contrato
```

El tipo de cambio se lee de `Parametros` (`TC_USD`, `TC_EUR`) y **se congela** en
el contrato (`TipoCambio`). Si mañana cambia, la ruta que ya se recorrió no se
recalcula.

Un contrato marcado como **monto no determinado** se evalúa con `999999999`, es
decir, cae en el tramo más alto. Es deliberado: un contrato a demanda sin tope
conocido es más riesgoso que uno de monto cerrado, no menos.

### 2. Filtra las reglas aplicables

```
Activo = Sí
  Y  MontoDesdePEN ≤ MontoPEN < MontoHastaPEN
  Y  (TipoContrato = el del contrato  O  TipoContrato = "Todos")
```

### 3. Determina los niveles

Toma los `Nivel` distintos de todas las reglas que pasaron el filtro y los ordena
de menor a mayor. Un nivel que aparece en una regla específica y en una genérica
cuenta **una sola vez**.

### 4. Elige la regla de cada nivel

**En cada nivel, la regla del tipo de contrato gana sobre la genérica.**

Un ejemplo con las reglas del despliegue inicial. Contrato de *Suministro de
bienes* por 120 000:

| Regla | Tipo | Nivel | Rol |
|---|---|---|---|
| Todos 100k–500k · N1 | Todos | 1 | Jefe de área |
| Todos 100k–500k · N2 | Todos | 2 | Gerente de área |
| **Suministro de bienes · N2** | **Suministro** | **2** | **Compras** |
| Todos 100k–500k · N3 | Todos | 3 | Legal |
| Todos 100k–500k · N4 | Todos | 4 | Finanzas |
| Todos 100k–500k · N5 | Todos | 5 | Gerencia General |

Ruta resultante:

```
N1 Jefe de área → N2 Compras → N3 Legal → N4 Finanzas → N5 Gerencia General
```

El nivel 2 lo cubre **Compras**, no el Gerente de área: la regla específica lo
desplazó. Los demás niveles quedan como en la regla genérica.

> Este comportamiento se puede comprobar sin crear contratos, con el **simulador**
> de la pantalla de administración: se introduce monto, tipo y área, y muestra la
> ruta exacta con los nombres de los aprobadores.

### 5. Resuelve el aprobador de cada nivel

| Rol | De dónde sale |
|---|---|
| `Jefe de area` | `Areas.Responsable` del área solicitante del contrato |
| `Gerente de area` | `Areas.Gerente` |
| `Usuario especifico` | `AprobadorUsuario` de la regla |
| `Legal`, `Finanzas`, `Compras`, `Gerencia General`, `Directorio` | `AprobadorGrupo` si está informado; si no, `AprobadorUsuario` |

Los dos primeros se resuelven **por contrato**: el mismo nivel 1 lo aprueba una
persona distinta según de qué área venga el contrato. Los demás son fijos por
regla.

Si se informa `AprobadorGrupo`, **cualquiera** del grupo puede resolver: es la
forma de que una ausencia no bloquee el proceso.

---

## Ejecución

Los niveles se ejecutan **en serie**: el nivel 2 no se solicita hasta que el 1
está resuelto. Cada nivel genera:

1. Un registro en `Aprobaciones` con `Decision = Pendiente`.
2. Una tarjeta de aprobación en Teams, Outlook o el portal de Power Automate,
   con el resumen del contrato y el enlace al expediente.

Cuando el aprobador responde, el registro se actualiza con la decisión, el
comentario, quién resolvió y cuántas horas tardó.

### Si alguien aprueba

Pasa al siguiente nivel. Al terminar el último, el contrato queda `Aprobado`, se
registra en `Bitacora` y se avisa al solicitante. Si DocuSign está activo, el
flujo 02 toma el relevo.

### Si alguien rechaza

- Los niveles restantes **no se solicitan**.
- El contrato queda `Rechazado` con el motivo (quién rechazó, en qué nivel y con
  qué comentario) en `MotivoRechazo`.
- Se avisa al solicitante por correo.
- El historial de lo ya aprobado **se conserva**.

### Reenvío tras un rechazo

El solicitante corrige y vuelve a enviar. Se abre un **ciclo nuevo**
(`CicloAprobacion + 1`) y se recorren **todos** los niveles desde el principio.

Es a propósito: si cambió el monto o el alcance, quien ya había aprobado lo hizo
sobre otra cosa. Y la ficha del contrato muestra los dos ciclos, de modo que se
puede ver qué se aprobó en cada intento.

### Si un nivel no tiene aprobador

| `Obligatorio` | Qué pasa |
|---|---|
| Sí | El proceso **se detiene**, el contrato queda `Rechazado` con el motivo explicando qué falta, y se avisa al administrador |
| No | El nivel se registra como `Omitido` y se continúa |

Esto es lo que más se rompe en producción, y casi siempre por lo mismo: un área
sin `Responsable` o una regla de rol fijo sin aprobador. La pantalla de
administración **lo avisa antes de que ocurra**, listando las reglas activas sin
aprobador y las áreas sin responsable.

---

## SLA

Cada regla define `SLAHoras` (48 por defecto). No corta nada de forma automática:
sirve para medir y para reclamar.

- La bandeja de aprobaciones marca en rojo lo que excedió su SLA.
- El administrador puede enviar un recordatorio desde la app, que queda
  registrado en `Alertas` como `SLA vencido`.

**No hay escalamiento automático.** Es una decisión, no una omisión: escalar solo
por tiempo suele reasignar una aprobación a quien no tiene el contexto, y la
decisión resultante vale menos. Si se quiere, se agrega al flujo 01 un `Delay`
paralelo por nivel que reasigne al superior; el sitio exacto es después de
*Crear tarea de aprobación*.

---

## Delegación por ausencia

No está implementada en el flujo porque **Approvals ya la resuelve mejor**: quien
va a ausentarse configura la delegación en Power Automate
(*Configuración → Delegación de aprobaciones*) y las tarjetas se redirigen solas.
El registro en `Aprobaciones` conserva a quién se asignó y quién resolvió
realmente, que es lo que interesa para la auditoría.

Para ausencias largas, la alternativa limpia es cambiar el `Responsable` del área
o usar `AprobadorGrupo` en lugar de un usuario concreto.

---

## Modificar la matriz

### Cambiar un umbral

Edita `MontoDesdePEN` / `MontoHastaPEN` en las filas del tramo. **Cuida que los
tramos no dejen huecos ni se solapen**: el filtro usa `≥ desde` y `< hasta`, así
que el `hasta` de un tramo debe ser exactamente el `desde` del siguiente.

Un hueco deja contratos sin ninguna regla aplicable, y esos se detienen con el
aviso «no hay reglas de aprobación configuradas». El simulador lo detecta en
segundos.

### Agregar un nivel a un tipo de contrato

Crea una regla con ese `TipoContrato` y el `Nivel` que corresponda. Si el nivel ya
existe en las reglas genéricas, la específica lo **reemplaza**; si es un nivel
nuevo, **se suma** a la ruta.

### Desactivar una regla

Pon `Activo = No`. No la borres: el historial de `Aprobaciones` referencia el rol
por texto, pero conservar la regla ayuda a entender rutas antiguas.

### Qué pasa con los contratos en curso

**Nada.** Sus niveles se resolvieron y se escribieron en `Aprobaciones` al
enviarse. Un cambio en la matriz solo afecta a los contratos que se envíen desde
ese momento.
