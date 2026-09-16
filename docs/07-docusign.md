# 07 — Integración con DocuSign

> **Esto es opcional.** Con `DOCUSIGN_HABILITADO = false` en `Parametros`, el
> sistema funciona completo sin firma electrónica y sin ninguna licencia premium:
> los contratos aprobados se firman a mano y el PDF firmado se sube a la
> biblioteca. Puedes activarlo más adelante sin tocar nada más.

---

## Qué hace falta

| Requisito | Detalle |
|---|---|
| Cuenta de DocuSign | Plan que permita integraciones por API |
| Licencia Power Automate Premium | Para la cuenta **dueña** de los flujos 02 y 03. El conector de DocuSign es premium |
| `DOCUSIGN_ACCOUNT_ID` | El *API Account ID* de tu cuenta |
| Un usuario de DocuSign para la conexión | Preferiblemente la cuenta de servicio |

### Obtener el Account ID

En DocuSign: **Configuración → Aplicaciones y claves**. Es el campo
*API Account ID*, con formato GUID. **No** es el número de cuenta que aparece en
la factura.

---

## Configuración

### 1. Crear la conexión

En Power Automate, con la **cuenta de servicio**: *Conexiones → Nueva conexión →
DocuSign*. Autentícate con el usuario de DocuSign que enviará los sobres.

> Los sobres saldrán a nombre de ese usuario. Conviene que sea una identidad
> institucional (`contratos@empresa.com`) y no una persona.

### 2. Sustituir el Account ID en las definiciones

```powershell
./Build-Package.ps1 `
    -SiteUrl "https://contoso.sharepoint.com/sites/Contratos" `
    -DocuSignAccountId "12345678-aaaa-bbbb-cccc-1234567890ab" `
    -Empaquetar
```

Verifica que no quedó ningún marcador:

```bash
python3 tools/validate-flows.py --site-url=definida power-automate/build/*/definition.json
```

### 3. Importar y activar los flujos 02 y 03

Déjalos **desactivados** hasta terminar la prueba del punto 5.

### 4. Activar el interruptor

En la lista `Parametros`, `DOCUSIGN_HABILITADO = true`. En la app, quien tenga
sesión abierta debe reabrirla (el valor se lee en `OnStart`).

Al activarlo, el campo **Correo del firmante** pasa a ser obligatorio en el
formulario de contratos: sin él no hay a quién enviarle el sobre.

---

## Los identificadores de operación hay que verificarlos

Las acciones de DocuSign en los flujos 02 y 03 usan estos `operationId`:

| Acción | `operationId` | Flujo |
|---|---|---|
| Crear sobre | `CreateBlankEnvelope` | 02 |
| Agregar documento al sobre | `AddDocumentToEnvelope` | 02 |
| Agregar destinatario | `AddRecipientToEnvelope` | 02 |
| Enviar sobre | `SendEnvelope` | 02 |
| Obtener documento combinado | `GetCombinedDocument` | 03 |
| Cuando cambia el estado de un sobre | `OnEnvelopeStatusChange` | 03 (disparador) |

**El conector de DocuSign cambia sus identificadores entre versiones, y el nombre
visible en el diseñador no siempre coincide con el del JSON.** Estas definiciones
**no se han probado contra un tenant real**.

Si al importar una acción no se resuelve, o marca error de operación
desconocida:

1. Elimina esa acción concreta en el diseñador.
2. Agrégala de nuevo desde el panel de conectores buscando *DocuSign*.
3. Rellena sus parámetros con las mismas expresiones que tenía (están en el
   `definition.json`).

**Solo hay que rehacer las acciones de DocuSign.** La lógica que las rodea —las
guardas del disparador que evitan el bucle infinito, el archivado del PDF, el
etiquetado del documento y las transiciones de estado del contrato— es lo que
tiene valor y no depende del conector.

---

## Cómo funciona el envío (flujo 02)

Se dispara cuando un contrato se modifica y cumple las tres condiciones:

```
Estado = 'Aprobado'
  Y  DocuSignEstado = 'No enviado'
  Y  DOCUSIGN_HABILITADO = true
```

> Las dos primeras condiciones son lo que **evita el bucle infinito**. El flujo
> escribe en el contrato al terminar (`En firma` / `Enviado`), lo que vuelve a
> disparar el disparador de «elemento modificado»; en esa segunda pasada las
> guardas no se cumplen y el flujo sale sin hacer nada.

Después:

1. Busca en `DocumentosContratos` el documento con `EsPrincipal = Sí`.
   **Si no hay ninguno, avisa al solicitante y se detiene.**
2. Descarga su contenido.
3. Crea el sobre, adjunta el PDF y agrega dos destinatarios:

   | Orden | Quién | De dónde sale |
   |---|---|---|
   | 1 | La contraparte | `ContraparteCorreo` / `ContraparteContacto` |
   | 2 | El responsable interno | `ResponsableContrato` |

   La contraparte firma primero: la organización cierra el acto una vez la otra
   parte se comprometió.

4. Envía el sobre y deja el contrato en `En firma` con el `DocuSignEnvelopeId`.

### Cambiar el orden o los firmantes

Es lo que más se personaliza. Los puntos exactos:

- **Firma interna primero:** intercambia `routingOrder` 1 y 2.
- **Ambos a la vez:** pon `routingOrder = 1` en los dos.
- **Un tercer firmante** (p. ej. un aval): duplica la acción *Agregar
  destinatario* con `recipientId = 3` y su `routingOrder`.
- **Usar una plantilla de DocuSign** con posiciones de firma predefinidas:
  reemplaza *Crear sobre* + *Agregar documento* por *Crear sobre a partir de
  plantilla*, usando el GUID de `DOCUSIGN_TEMPLATE_ID`.

> **Sobre las posiciones de firma.** Sin plantilla, DocuSign usa el modo de
> firma libre: el firmante coloca su firma donde corresponda. Si el contrato
> tiene un formato fijo, una plantilla con las pestañas ya situadas evita errores
> y hace la firma mucho más rápida. Otra opción es usar *anchor tags* —texto
> como `\s1\` en el PDF— que DocuSign detecta y reemplaza por el campo de firma.

---

## Cómo funciona el retorno (flujo 03)

Escucha los cambios de estado de todos los sobres de la cuenta, busca el contrato
por `DocuSignEnvelopeId` y actúa según el estado. **Un sobre que no corresponde a
ningún contrato se ignora en silencio**, de modo que el flujo convive con otros
usos de la misma cuenta de DocuSign.

| Estado del sobre | Qué hace |
|---|---|
| `completed` | Descarga el PDF firmado, lo archiva en la biblioteca con tipo *Sobre firmado*, pasa el contrato a **Vigente** con `FechaFirma`, y avisa al responsable |
| `declined` | Contrato a **Rechazado**, `DocuSignEstado = Rechazado`, avisa al solicitante |
| `voided` | Contrato vuelve a **Aprobado** con `DocuSignEstado = No enviado` y `EnvelopeId` vacío: queda listo para reintentar el envío |
| `delivered` | Solo actualiza `DocuSignEstado` |
| otros | Sin acción |

El documento que se archiva es el **combinado**: todos los documentos del sobre
más el certificado de firma de DocuSign, que es la evidencia legal de quién firmó,
cuándo y desde dónde.

> **El etiquetado no es opcional.** *Crear archivo* sube el binario; sin la acción
> *Actualizar elemento* posterior, el PDF firmado queda en la biblioteca sin
> vínculo con su contrato y desaparece del expediente.

---

## Prueba antes de activar

Con los flujos activados pero usando el **entorno de pruebas de DocuSign**
(demo.docusign.net) o un contrato ficticio con tu propio correo como contraparte:

- [ ] Registrar un contrato de prueba con **tu correo** como firmante.
- [ ] Subir un PDF y marcarlo como principal.
- [ ] Aprobarlo por todos sus niveles.
- [ ] Verificar que el contrato pasa a **En firma** y que `DocuSignEnvelopeId` se
      llenó.
- [ ] Recibir el sobre y firmarlo.
- [ ] Verificar que el contrato pasa a **Vigente** con `FechaFirma`.
- [ ] Verificar que el PDF firmado está en `DocumentosContratos` **con su columna
      `Contrato` apuntando al contrato correcto** y `EstaFirmado = Sí`.
- [ ] Repetir **rechazando** el sobre: el contrato debe quedar `Rechazado`.
- [ ] Repetir **anulando** el sobre desde DocuSign: debe volver a `Aprobado` y
      poder reenviarse.

Los dos últimos son los que se omiten con más frecuencia y los que dejan
contratos atascados cuando ocurren de verdad.

---

## Problemas frecuentes

| Síntoma | Causa | Solución |
|---|---|---|
| El contrato queda en `Aprobado` y no pasa a `En firma` | No hay documento marcado como principal, o `DOCUSIGN_HABILITADO` es `false` | El solicitante recibe un correo explicándolo |
| «Account ID inválido» | Se usó el número de factura en vez del *API Account ID* | Configuración → Aplicaciones y claves |
| El sobre se envía pero nunca vuelve | El flujo 03 está desactivado, o su conexión caducó | Revisar el historial de ejecuciones del flujo 03 |
| El PDF firmado llega sin vincularse al contrato | Falló la acción de etiquetado posterior a *Crear archivo* | Revisar `Etiquetar_documento_firmado` en el flujo 03 |
| Se envían dos sobres del mismo contrato | Se editó la condición del disparador del flujo 02 | Las tres guardas deben estar intactas |
| El flujo 02 se dispara en bucle | Se quitó la guarda `DocuSignEstado = 'No enviado'` | Restaurarla |
