# 06 — Manual de usuario

---

## Para quien registra contratos

### Registrar un contrato nuevo

1. **Contratos → Registrar contrato.**
2. Completa la ficha. Lo mínimo para poder enviarlo a aprobación:
   - Nombre del contrato y tipo
   - Contraparte y su RUC
   - Área solicitante
   - Monto y moneda — o marca **Monto no determinado** si es a demanda
   - Fecha de inicio y de fin — o marca **Vigencia indefinida**
3. **Guardar.** El código (`CTR-AAAA-NNNN`) se asigna solo en unos segundos.
   Si no aparece, refresca: lo genera un proceso en segundo plano.

> **El monto determina quién aprueba.** Si lo pones mal, el contrato recorre la
> ruta equivocada. Si no lo sabes con certeza, marca *Monto no determinado*: el
> sistema lo trata como el tramo más alto y lo hace revisar por más gente.

### Subir el documento

En la ficha del contrato, pestaña **Documentos**. Sube el PDF y **márcalo como
principal**: es el que se enviará a firma.

Solo puede haber un principal por contrato. Al marcar uno nuevo, el anterior deja
de serlo.

### Enviar a aprobación

Botón **Enviar a aprobación** en la ficha.

Si está deshabilitado, pasa el cursor por encima: el mensaje dice exactamente qué
falta (normalmente el documento principal o el monto).

Al enviarlo verás cuántos niveles tiene que recorrer. A partir de ahí es
automático: cada aprobador recibe su tarjeta cuando le toca.

### Seguir el avance

La cabecera de la ficha muestra *Nivel 2 de 5*. La pestaña **Aprobaciones**
muestra quién resolvió cada nivel, cuándo y con qué comentario.

### Si te lo rechazan

Recibes un correo con el motivo. El contrato queda en **Rechazado** y vuelve a ser
editable.

Corrige lo observado y vuelve a enviarlo. Se abre un **ciclo nuevo** y se recorren
todos los niveles otra vez, incluidos los que ya habían aprobado: si cambió el
monto o el alcance, lo que aprobaron antes era otra cosa.

El historial del intento anterior se conserva.

### Renovar un contrato

Botón **Renovar** en un contrato vigente, por vencer o vencido.

Crea un contrato nuevo en borrador con los mismos datos y la vigencia desplazada
un año, vinculado al original. El contrato anterior queda como **Renovado**.

**Revisa las fechas y el monto antes de enviarlo:** el año adicional es solo un
valor por defecto, casi nunca es lo pactado.

---

## Para quien aprueba

### Dónde se aprueba

En la **tarjeta de aprobación**, que te llega por tres vías (es la misma tarjeta):

- **Teams** — notificación de Approvals
- **Outlook** — correo con los botones Aprobar y Rechazar
- **Power Automate** — [Aprobaciones → Recibidas](https://make.powerautomate.com/environments/~default/approvals/received)

La app de Contratos **no** tiene botones de aprobar: es el panel de seguimiento.
Existe una sola vía de decisión para que no haya dos versiones de la verdad.

### Qué te muestra la tarjeta

Contrato, tipo, contraparte, monto (en su moneda y en la moneda base), vigencia,
área y objeto. Y un enlace para abrir el expediente completo con sus documentos.

**Abre el expediente antes de decidir.** La tarjeta resume; el contrato es lo que
estás aprobando.

### Rechazar

Escribe el motivo en el comentario. **No es un formalismo:** es lo que el
solicitante verá para saber qué corregir, y queda en el historial permanente.

Un rechazo detiene la cadena: los niveles siguientes no se solicitan.

### Ver lo que tienes pendiente

En la app, **Aprobaciones**. Muestra lo que está a tu nombre, hace cuánto tiempo y
si excedió el SLA. Desde ahí llegas al contrato o a tus tareas de aprobación.

### Si te vas de vacaciones

Configura la delegación en Power Automate: **Configuración → Delegación de
aprobaciones**. Las tarjetas se redirigen solas a quien designes, y el sistema
registra tanto a quién estaba asignada como quién la resolvió.

Para ausencias largas, pide al administrador que cambie el responsable de tu área
o que use un grupo en lugar de tu nombre en la matriz.

---

## Para quien custodia los originales

El módulo de custodia controla el documento **en papel**: dónde está, quién lo
tiene y desde cuándo. Se abre desde la ficha del contrato, botón
**Custodia del original**.

### Recibir un original

Cuando llega el contrato firmado en papel:

1. **Registrar recepción.**
2. Indica la **ubicación física**. Usa siempre el mismo formato, por ejemplo
   `Archivador 03 / Caja 12 / Folio 245`. De poco sirve saber que está «en el
   archivo».
3. Marca si hay acta de entrega firmada.

El contrato pasa a **En custodia** y tú quedas como custodio.

### Prestar un original

1. **Prestar original.**
2. Indica a quién se lo entregas y la fecha comprometida de devolución.
3. Confirma.

Quien se lo lleva recibe por correo un **cargo de entrega** con la fecha
comprometida. El contrato pasa a **Prestado**.

Si no lo devuelve, el sistema se lo reclama automáticamente: el primer día de
atraso y luego una vez por semana, con copia a ti.

### Registrar la devolución

**Registrar devolución.** Cierra el préstamo abierto, deja constancia y el
contrato vuelve a **En custodia**. Los reclamos se detienen.

### Consultar la trazabilidad

El historial de la pantalla de custodia muestra todos los movimientos en orden,
con fechas y personas. Es lo que responde «¿dónde está el original del contrato
X?» y «¿quién lo tuvo entre marzo y mayo?».

---

## Estados del contrato

| Estado | Significa | Quién lo cambia |
|---|---|---|
| **Borrador** | En preparación, editable | El solicitante |
| **En revisión legal** | Esperando visto bueno de Legal | Legal |
| **En aprobación** | Recorriendo la ruta de aprobación | El flujo |
| **Aprobado** | Todos los niveles aprobaron | El flujo |
| **En firma** | Sobre de DocuSign enviado | El flujo |
| **Vigente** | Firmado y en ejecución | El flujo |
| **Por vencer** | Dentro del periodo de preaviso | El flujo (diario) |
| **Vencido** | Pasó la fecha de fin | El flujo (diario) |
| **Renovado** | Se creó un contrato sucesor | El solicitante |
| **Terminado** | Cerrado antes o al vencer | El administrador |
| **Rechazado** | Rechazado en aprobación o en firma | El flujo |
| **Anulado** | Anulado sin llegar a ejecutarse | El administrador |

---

## Alertas que vas a recibir

| Alerta | Cuándo | A quién |
|---|---|---|
| Aprobación pendiente | Al llegar tu nivel | Al aprobador |
| Contrato aprobado | Al completar todos los niveles | Al solicitante |
| Contrato rechazado | Al rechazarse | Al solicitante |
| Preaviso de vencimiento | 90, 60, 30, 15, 7 y 1 días antes | Al responsable, copia al administrador |
| Renovación automática | En los mismos hitos, si el contrato se renueva solo | Al responsable |
| Garantía por vencer | 30, 15, 7, 1 y 0 días antes | Al responsable |
| Devolución pendiente | Día 1 de atraso y luego semanal | A quien tiene el original, copia al custodio |
| Firma completada | Al firmar todas las partes | Al responsable |

Cada alerta se envía **una sola vez** por hito. Si recibes la misma dos veces, hay
algo mal: avisa al administrador.

> **El aviso de renovación automática es el que más cuesta caro ignorar.** En un
> contrato que se renueva solo, el preaviso no es para renovar: es el plazo que
> tienes para decir que **no** quieres renovar. Si se pasa, el contrato se renueva
> por otro periodo completo.

---

## Preguntas frecuentes

**No aparece el código del contrato.**
Lo asigna un proceso en segundo plano, tarda unos segundos. Refresca. Si tras
unos minutos sigue vacío, avisa al administrador.

**El botón «Enviar a aprobación» está gris.**
Pasa el cursor por encima: el mensaje dice qué falta.

**Busqué un contrato y no lo encuentro.**
La búsqueda funciona **por el inicio** del texto, no por contenido. Para
*«Servicio de mantenimiento»* escribe `Servicio`, no `mantenimiento`.

**¿Puedo borrar un contrato que registré por error?**
No. Nadie puede borrar contratos ni documentos salvo el administrador. Márcalo
como **Anulado** o pídeselo a él. Es a propósito: un expediente perdido no se
recupera.

**Cambié el monto de un contrato que ya estaba aprobado.**
El cambio no reabre la aprobación. Si el monto cambia de verdad, lo correcto es
una **adenda**, que sí vuelve a pasar por la matriz sobre el monto acumulado.

**Aprobé por error.**
La decisión no se puede deshacer: el historial es inmutable. Avisa al
administrador para que anule el contrato, y vuelve a registrarlo corregido.
