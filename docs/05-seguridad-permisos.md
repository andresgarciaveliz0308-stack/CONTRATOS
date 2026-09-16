# 05 — Seguridad y permisos

## Principio

Un sistema de contratos tiene dos requisitos que van más allá del control de
acceso habitual:

1. **Nadie destruye un expediente.** Ni por error ni a propósito.
2. **El historial de aprobaciones es evidencia.** Si quien aprobó puede reescribir
   lo que aprobó, deja de servir para lo que existe.

Los permisos de este sistema están construidos alrededor de eso, no solo de quién
ve qué.

---

## Niveles de permiso personalizados

`Set-Permissions.ps1` crea dos que SharePoint no trae:

| Nivel | Basado en | Se le quita | Para qué |
|---|---|---|---|
| **Aportar sin eliminar** | Contribuir | `DeleteListItems`, `DeleteVersions` | Agregar y editar contratos y documentos, pero **no** borrarlos |
| **Solo agregar** | Contribuir | `EditListItems`, `DeleteListItems`, `DeleteVersions` | Crear registros nuevos y leerlos, **nunca** modificarlos |

*Solo agregar* es lo que hace inmutables `Aprobaciones` y `Bitacora`.

---

## Grupos

| Grupo | Quiénes | Qué puede hacer |
|---|---|---|
| `Contratos - Administradores` | Responsables del sistema **y la cuenta de servicio de los flujos** | Todo, incluida la matriz de aprobación |
| `Contratos - Legal` | Área legal | Revisar, editar contratos, dar visto bueno |
| `Contratos - Aprobadores` | Todos los de la matriz | Leer contratos; aprobar desde las tarjetas |
| `Contratos - Custodios` | Archivo / gestión documental | Registrar recepciones, préstamos y devoluciones |
| `Contratos - Solicitantes` | Quienes registran contratos | Crear y editar; no borrar |
| `Contratos - Consulta` | Consulta general | Solo lectura |

---

## Matriz de permisos por lista

| Lista | Admin | Legal | Solicitantes | Custodios | Aprobadores | Consulta |
|---|---|---|---|---|---|---|
| `Contratos` | Control total | Aportar s/e | Aportar s/e | Aportar s/e | Lectura | Lectura |
| `DocumentosContratos` | Control total | Aportar s/e | Aportar s/e | Aportar s/e | Lectura | Lectura |
| `Aprobaciones` | Control total | Lectura | Lectura | — | Lectura | Lectura |
| `Bitacora` | Control total | Solo agregar | Solo agregar | Solo agregar | Solo agregar | — |
| `MatrizAprobacion` | Control total | Lectura | Lectura | — | Lectura | Lectura |
| `Parametros` | Control total | Lectura | Lectura | Lectura | Lectura | Lectura |
| `Areas` | Control total | Lectura | Lectura | Lectura | Lectura | Lectura |
| `MovimientosCustodia` | Control total | Lectura | Lectura | **Aportar s/e** | — | Lectura |
| `Adendas` | Control total | Aportar s/e | Aportar s/e | — | Lectura | Lectura |
| `Alertas` | Control total | Lectura | Lectura | — | — | Lectura |
| `Categorias` | Control total | Lectura | Lectura | Lectura | Lectura | Lectura |
| `CamposPersonalizados` | Control total | Lectura | Lectura | Lectura | Lectura | Lectura |
| `ContratosCamposValor` | Control total | Aportar s/e | Aportar s/e | Aportar s/e | Lectura | Lectura |

*Aportar s/e* = Aportar sin eliminar.

> **`Aprobaciones` no es escribible por nadie salvo el administrador.** Los flujos
> escriben ahí, y por eso la cuenta dueña de los flujos **debe** estar en
> `Contratos - Administradores`. Es el error de despliegue más frecuente: sin eso,
> el flujo 01 falla con 403 justo al registrar una decisión, después de que el
> aprobador ya respondió.

---

## La app no es una barrera de seguridad

Las variables `gblEsAdmin`, `gblEsCustodio` y `gblEsLegal` deciden **qué se
muestra**, no qué se puede hacer. Salen de la lista `Parametros`, que es de
lectura para todos.

Quien conozca la URL de SharePoint puede saltarse la app por completo. Lo que le
impide hacer daño son los permisos de la lista, no la interfaz.

**Consecuencia práctica:** si alguien debe dejar de poder registrar préstamos, hay
que sacarlo del grupo `Contratos - Custodios`, no solo de la clave `CUSTODIOS` de
`Parametros`. Quitarlo de `CUSTODIOS` únicamente le oculta los botones.

---

## Contratos con clasificación «Restringido»

El modelo anterior da a todo el mundo al menos lectura sobre `Contratos`. Para
contratos verdaderamente reservados —compraventas de empresa, acuerdos con
directivos, litigios— hace falta permiso **a nivel de elemento**.

SharePoint lo soporta, pero tiene un costo real: cada elemento con permisos
únicos es una entrada más en el árbol de seguridad, y **por encima de unos 5 000
permisos únicos por lista el rendimiento se degrada de forma notoria**. No es una
función para usar por defecto.

### Cómo aplicarlo

Un flujo que rompa la herencia cuando `Clasificacion = "Restringido"`:

```
Disparador: SharePoint · Cuando se crea o modifica un elemento (Contratos)
Condición:  Clasificacion = 'Restringido'
Acciones:
  1. Enviar solicitud HTTP a SharePoint
     POST _api/lists/getbytitle('Contratos')/items(<id>)/breakroleinheritance(copyRoleAssignments=false,clearSubscopes=true)
  2. Conceder permiso al Solicitante, al ResponsableContrato y al grupo Administradores
     POST _api/lists/getbytitle('Contratos')/items(<id>)/roleassignments/addroleassignment(principalid=<id>,roledefid=<id>)
```

### Antes de activarlo, decidir

- **Qué pasa con los aprobadores.** Si el contrato es restringido pero su ruta de
  aprobación incluye a Finanzas, hay que concederles permiso sobre ese elemento
  o la tarjeta de aprobación les mostrará un enlace que no pueden abrir.
- **Qué pasa con los documentos.** Romper la herencia en `Contratos` no protege
  la biblioteca. Hay que hacer lo mismo con los archivos de ese contrato.
- **Cuántos se espera que haya.** Si «restringido» va a ser el 40 % de los
  contratos, la respuesta correcta no es el permiso por elemento: es un **sitio
  aparte** con su propia membresía.

**La recomendación es empezar sin esto.** Que `Clasificacion` sea informativa y
que los contratos realmente reservados vivan en otro sitio. Agregar permisos por
elemento es fácil; quitarlos de 8 000 elementos, no.

---

## Auditoría

Tres capas, que responden preguntas distintas:

| Capa | Responde | Se puede alterar |
|---|---|---|
| Historial de versiones de SharePoint | Qué campo cambió y a qué valor | Solo el administrador puede purgarlo |
| `Aprobaciones` | Quién aprobó qué, cuándo y con qué comentario | No (*Solo agregar*) |
| `Bitacora` | Qué acciones se hicieron desde la app | No (*Solo agregar*) |

Para auditoría formal de tenant (accesos, descargas, intentos de eliminación),
activar el **registro de auditoría unificado** de Microsoft Purview. Cubre lo que
el historial de versiones no ve: quién *leyó* o *descargó* un documento.

---

## Retención

El parámetro `RETENCION_ANIOS` (10 por defecto) documenta la política, pero **no
la aplica**. Para que se aplique de verdad hay que crear una etiqueta de retención
en Microsoft Purview y publicarla sobre el sitio.

Recomendación mínima:

| Elemento | Retención | Al vencer |
|---|---|---|
| Contratos y sus documentos | 10 años desde la terminación | Revisión antes de eliminar |
| `Aprobaciones`, `Bitacora` | Igual que el contrato | Revisión |
| `Alertas` | 2 años | Eliminar |

Sin una etiqueta de Purview, el valor de `RETENCION_ANIOS` es solo una nota para
quien opere el sistema.

---

## Cuenta de servicio de los flujos

| Requisito | Por qué |
|---|---|
| Cuenta dedicada, no personal | Si el dueño de los flujos se va, los flujos se desactivan sin aviso claro |
| Licencia de Power Automate (Premium si hay DocuSign) | Sin ella los flujos no se ejecutan |
| Miembro de `Contratos - Administradores` | Escribe en `Aprobaciones` y `Bitacora` |
| Contraseña en un almacén de secretos | Nunca en este repositorio |
| Conexiones creadas con esa cuenta | SharePoint, Outlook, Approvals, DocuSign |

> Revisa cada trimestre que las conexiones siguen autenticadas. Una conexión
> caducada detiene los flujos de forma silenciosa: no hay error visible hasta que
> alguien nota que sus contratos no avanzan. Ver [`08-operacion.md`](08-operacion.md).
