# 09 — Implementación sin PowerShell (todo desde el navegador)

Esta guía reemplaza los pasos 5, 6, 7 y 8 de
[`00-inicio-rapido.md`](00-inicio-rapido.md) por su equivalente **100 % en el
navegador**. No necesitas instalar nada, ni permisos de administrador de tu
computadora, ni consola.

> **Navegador sí; tablet no del todo.** Las secciones A–E (todo SharePoint) se
> pueden hacer desde una tablet. Construir la app en Power Apps Studio exige
> Windows o macOS: Microsoft no admite el diseñador en Android ni iOS. El
> detalle y las alternativas están en la [sección G](#g--la-app).

---

## El atajo: crear las 13 listas con un script en el navegador

Las secciones B y C de esta guía son 134 columnas creadas a mano: entre dos y
cuatro horas. **Hay una forma de hacerlo en un par de minutos sin instalar
nada**, y de paso elimina por completo el riesgo de escribir mal un nombre
interno.

SharePoint tiene una API REST que responde a la sesión que ya tienes abierta en
el navegador. El script [`sharepoint/crear-listas.js`](../sharepoint/crear-listas.js)
la usa para crear las 13 listas y sus 134 columnas.

```
1. Abre tu sitio en Chrome o Edge, con sesión ya iniciada
2. F12 → pestaña Consola
3. Si el navegador lo pide, escribe:  allow pasting
4. Pega el contenido de crear-listas.js y pulsa Enter
```

### Por qué esto sí respeta el nombre interno

Es la parte que hace que valga la pena. Al crear una columna desde la interfaz,
SharePoint deriva el nombre interno del visible y lo codifica. La API acepta un
parámetro, `Options = 8` (`AddFieldInternalNameHint`), que **obliga a respetar el
nombre interno declarado en el XML**. Sin ese parámetro, la propia API ignoraría
el nombre interno y usaría el visible — el mismo problema.

Dicho de otro modo: el script no es solo más rápido, es el único camino del
navegador que garantiza los nombres correctos.

### Antes de pegarlo, léelo

Los navegadores advierten de no pegar código en la consola, y tienen razón: es
una vía conocida de robo de sesión. Esa advertencia también aplica aquí, así que
no lo pegues por confiar en mí:

- Está en el repositorio, comentado en español, y son unas 200 líneas.
- Solo llama a `TU-SITIO/_api/...`. No hay ninguna otra dirección en el archivo
  — búscala con Ctrl+F si quieres comprobarlo.
- No lee datos ni los envía a ningún lado: crea listas y columnas.
- Es idempotente: comprueba antes de crear y no toca lo que ya existe, así que
  puedes ejecutarlo de nuevo sin miedo si algo falla a mitad.

### Lo que este script no hace

Cubre las secciones B y C —listas, columnas e índices—, que es el grueso del
trabajo manual. **Los permisos (D), los datos iniciales (E), los flujos (F) y la
app (G) siguen como están descritos.** Los datos iniciales se pegan igual de
rápido desde la vista de cuadrícula.

### Su estado de verificación

Se probó contra un SharePoint simulado (`tools/simular-crear-listas.js`): crea
las 13 listas y las 134 columnas, resuelve los lookups —incluida la
autorreferencia de `Categorias`—, no duplica nada al repetirlo y retoma bien
tras un fallo. **No se ha ejecutado contra un tenant real de Microsoft 365**,
igual que el resto del repositorio.

Por eso: **pruébalo primero en un sitio de prueba**, no directamente en el
definitivo. Crea un sitio `/sites/ContratosPrueba`, ejecútalo ahí, comprueba un
par de nombres internos, y recién entonces hazlo en el bueno.

### Desde una tablet, donde no hay consola

Chrome y Edge para Android no tienen herramientas de desarrollador: **F12 no
existe ahí**. Para ese caso está el mismo trabajo empaquetado como flujo de
Power Automate, que hace idénticas llamadas REST desde la interfaz web:

**[`power-automate/90-crear-listas/`](../power-automate/90-crear-listas/)** —
se importa el `.zip`, se asigna la conexión de SharePoint y se ejecuta pasando
la URL del sitio. Todo desde el navegador de la tablet.

Usa la acción *Enviar una solicitud HTTP a SharePoint*, que es **conector
estándar**: no requiere licencia premium y resuelve la autenticación sola.

> En una computadora prefiere el script de consola: menos piezas que puedan
> fallar. El flujo existe para cuando la consola no es una opción.

### Si cambias el esquema

El script se genera desde `Deploy-Contratos.ps1`, no se edita a mano:

```bash
python3 tools/generar-script-listas.py     # regenera sharepoint/crear-listas.js
node tools/simular-crear-listas.js         # lo prueba contra el SharePoint simulado
```

---

## El acompañante de construcción

Esta guía explica **el porqué** de cada paso. Para hacerlo con las manos hay una
página compañera con las **134 columnas listas para copiar**, los valores de
opción exactos, los bloques de datos para pegar en la vista de cuadrícula y el
`OnStart` completo, con el avance guardado entre sesiones:

👉 **[Constructor de Contratos](https://claude.ai/artifact/BvBgscU5inUqC8JvhBcAww)**

Todos sus valores se extraen automáticamente de `sharepoint/Deploy-Contratos.ps1`,
así que no pueden desviarse de lo que el sistema espera de verdad. Úsala para
copiar; usa este documento para entender.

> Si regeneras el esquema tras cambiar el script de despliegue, vuelve a generar
> la página: es una copia, no una vista en vivo.

---

## Aclaración previa: PowerShell no se paga

Vale la pena despejarlo antes de seguir, porque genera confusión:

| | ¿Cuesta? | Qué es |
|---|---|---|
| **PowerShell** | **Gratis** | Software libre de Microsoft. En Windows ya viene instalado (busca «PowerShell» en el menú Inicio). PowerShell 7 es una descarga gratuita. |
| **PnP.PowerShell** | **Gratis** | Módulo de código abierto. Se instala con `Install-Module`. |
| **Azure Cloud Shell** | **Requiere suscripción de Azure** | Una consola *por navegador*. Es un servicio de Azure, no es PowerShell. |

Si algo te pidió una suscripción, fue **Cloud Shell**, no PowerShell.

Entonces, las razones reales por las que alguien no puede usar PowerShell son
solo tres, y ninguna se resuelve pagando:

1. **La política de TI de la empresa impide instalar programas** en el equipo de
   trabajo. Es lo más común.
2. **El dispositivo no lo soporta** — una tablet Android o un iPad no ejecutan
   PowerShell de forma nativa.
3. **No hay permisos de administrador local** para instalar.

En los tres casos, esta guía es la salida. Y si tu caso es el 1, considera
también pedirle a alguien de TI que ejecute los scripts una sola vez: para
ellos son 4 minutos, y te ahorra las 2–4 horas de trabajo manual.

---

## Lo primero: qué parte realmente necesitaba PowerShell

Mucho menos de lo que parece. De los 10 pasos de la guía rápida, **la app y los
flujos nunca necesitaron PowerShell** — siempre se construyeron en el navegador:

| Paso de la guía rápida | ¿Necesita PowerShell? | Alternativa |
|---|---|---|
| 1 · Conseguir tenant | No | — |
| 2 · Instalar PowerShell | **Sí** | Se elimina por completo |
| 3 · Descargar el código | No | Solo para leer las fórmulas; puedes verlo en GitHub |
| 4 · Autorizar conexión | **Sí** | Se elimina (era solo para los scripts) |
| 5 · Crear sitio y 13 listas | **Sí** | **Sección A y B de esta guía** |
| 6 · Permisos | **Sí** | **Sección D** |
| 7 · Datos de ejemplo | **Sí** | **Sección E** |
| 8 · Empaquetar e importar flujos | **Sí**, solo para el `.zip` | **Sección F**: construirlos en el diseñador |
| 9 · Construir la app | **No** | Sin cambios — ya era navegador puro |
| 10 · Prueba de punta a punta | No | Sin cambios |

**El costo honesto:** lo que el script hacía en 4 minutos, a mano toma entre 2 y
4 horas de clics — casi todo en crear las columnas de la lista `Contratos`, que
tiene 40. No es difícil, es repetitivo. El resto (permisos, datos, flujos) va
mucho más rápido.

> Si en algún momento consigues que alguien de TI con acceso a PowerShell corra
> los scripts una sola vez contra el sitio, ese camino sigue disponible y es
> preferible. Esta guía existe para cuando eso no es una opción.

---

## ⚠️ La regla que no puedes romper: el nombre interno

**Esto es lo más importante de toda la guía.** Si te saltas esto, la app y los
flujos van a leer columnas vacías y nada va a funcionar — y el error no aparece
en ningún lado, simplemente no pasa nada.

SharePoint tiene dos nombres por columna:

- El **nombre visible** (el que ves en pantalla): «Nombre del contrato»
- El **nombre interno** (el que usan las fórmulas): `NombreContrato`

Cuando creas una columna desde el navegador, **SharePoint genera el nombre
interno a partir del visible, y lo codifica**: si la creas como
«Nombre del contrato», el nombre interno queda
`Nombre_x0020_del_x0020_contrato` — con las tildes y espacios convertidos en
basura. Ese nombre no coincide con el que esperan las fórmulas y los flujos.

### El procedimiento correcto, en dos tiempos

Para cada columna:

1. **Créala escribiendo el nombre interno exacto** de la tabla de
   [`02-modelo-datos.md`](02-modelo-datos.md) — sin espacios, sin tildes:
   `NombreContrato`
2. **Después de crearla**, entra a *Configuración de la lista → esa columna* y
   cámbiale el **nombre visible** a lo que quieras: «Nombre del contrato»

El nombre interno se congela al crearse y **ya no cambia** cuando renombras. Eso
es exactamente lo que necesitamos.

> **Verifica el nombre interno cuando dudes:** abre la columna desde
> *Configuración de la lista* y mira la URL del navegador. Al final dice
> `&Field=NombreContrato`. Ese es el nombre interno real.

El paso 2 es opcional — puedes dejar los nombres técnicos visibles y la app
funciona igual, porque la app pinta sus propias etiquetas. Renombrar es solo
para que la lista se vea bien cuando alguien la abre directo en SharePoint.

---

## A · Crear el sitio

1. Entra a **[office.com](https://office.com)** → **SharePoint**
2. **+ Crear sitio → Sitio de grupo**
3. Nombre: `Contratos` — verifica que la dirección quede
   `https://TU-TENANT.sharepoint.com/sites/Contratos`
4. Idioma **Español**, privacidad **Privado**
5. **Siguiente → Finalizar** (no agregues miembros todavía; eso es la sección D)

---

## B · Crear las 13 listas

> **Antes de empezar a mano, mira
> [el atajo con script](#el-atajo-crear-las-13-listas-con-un-script-en-el-navegador).**
> Esta sección y la C son las que ese script hace en un par de minutos. Lo que
> sigue es el procedimiento manual, que sirve igual si prefieres no pegar código
> en la consola o si necesitas corregir una columna suelta.

### El orden importa

Varias listas se apuntan entre sí con columnas de tipo **Búsqueda** (*Lookup*), y
SharePoint no te deja apuntar a una lista que todavía no existe. Créalas en este
orden:

```
Ronda 1 (sin dependencias):     Areas · Parametros · Categorias
Ronda 2 (apunta a la ronda 1):  Contratos · CamposPersonalizados
Ronda 3 (apunta a Contratos):   Aprobaciones · Adendas · MovimientosCustodia
                                Alertas · Bitacora · MatrizAprobacion
                                ContratosCamposValor
Ronda 4 (biblioteca):           DocumentosContratos
```

Dos columnas son **autorreferencias** y hay que dejarlas para el final de su
propia lista:

- `Contratos.ContratoPadre` → apunta a `Contratos` (créala cuando la lista ya exista)
- `Categorias.CategoriaPadre` → apunta a `Categorias` (igual)

### Crear cada lista

**Contenido del sitio → + Nuevo → Lista → Lista en blanco.** El nombre debe ser
**exacto** (sin tildes, tal cual): `Areas`, `Parametros`, `Categorias`,
`Contratos`, `CamposPersonalizados`, `MatrizAprobacion`, `Aprobaciones`,
`Adendas`, `MovimientosCustodia`, `Alertas`, `Bitacora`,
`ContratosCamposValor`.

Para `DocumentosContratos`: **+ Nuevo → Biblioteca de documentos**.

### Crear las columnas

Las columnas de cada lista, con su nombre interno, tipo y opciones, están en
**[`02-modelo-datos.md`](02-modelo-datos.md)** — esa es la fuente de verdad, no
la repito aquí para que no existan dos versiones que puedan discrepar.

En la lista abierta: **+ Agregar columna →** elige el tipo → escribe el nombre
**interno** → **Guardar**.

Equivalencias entre lo que dice el modelo de datos y lo que ofrece el menú:

| En `02-modelo-datos.md` | En el menú de SharePoint |
|---|---|
| Texto | Texto de una sola línea |
| Texto (255) / (100) / (20) | Texto de una sola línea → *Más opciones* → longitud máxima |
| Nota | Varias líneas de texto |
| Número | Número |
| Número (2 dec.) | Número → *Más opciones* → posiciones decimales = 2 |
| Fecha | Fecha y hora → formato **Solo fecha** |
| Fecha y hora | Fecha y hora → formato **Fecha y hora** |
| Sí/No | Sí/No |
| Elección | Opción → escribe cada valor en su renglón |
| Persona | Persona |
| Búsqueda → `Lista` | Búsqueda → elige la lista de destino y la columna `Título` |

Tres detalles que se pasan por alto:

- **La columna `Title` ya existe** en toda lista nueva — no la crees. En varias
  listas el modelo de datos la usa con otro significado (en `Contratos` es el
  código `CTR-AAAA-NNNN`, en `Parametros` es la clave). Solo renómbrala.
- **Las columnas de tipo Elección: los valores van SIN TILDES.** El sistema real
  usa `En aprobacion`, `Renovacion automatica`, `Entidad publica` — sin acentos.
  Las tablas de [`02-modelo-datos.md`](02-modelo-datos.md) los muestran
  acentuados porque son prosa legible, pero **los literales verdaderos no
  llevan tilde**, y los flujos comparan texto exacto: `En aprobación` y
  `En aprobacion` son dos valores distintos y el contrato se detiene.
  Cópialos del [acompañante de construcción](#el-acompañante-de-construcción),
  que los extrae del script de despliegue, o de
  `sharepoint/Deploy-Contratos.ps1` directamente. Ojo también con
  `Convenio / Adendum marco` (una sola `d`).
- **Desactiva «Agregar a todos los tipos de contenido»** si aparece — no hace
  daño, pero ensucia la lista.

### Configuración extra de la biblioteca `DocumentosContratos`

*Configuración de la biblioteca → Configuración de versiones:*

- Control de versiones: **mayores y menores** (1.0, 1.1, 2.0…)
- Exigir desprotección: **No**

---

## C · Índices (no es opcional si esperas crecer)

SharePoint deja de responder consultas filtradas cuando una lista pasa de 5 000
elementos, salvo sobre **columnas indexadas**. Es barato hacerlo ahora y caro
descubrirlo después.

*Configuración de la lista → Columnas indexadas → Crear un índice nuevo.*

| Lista | Indexa estas columnas |
|---|---|
| `Contratos` | `Estado`, `FechaFin`, `FechaPreaviso`, `TipoContrato`, `Contraparte`, `EstadoCustodia`, `Categoria` |
| `Aprobaciones` | `Contrato`, `Decision` |
| `DocumentosContratos` | `Contrato` |
| `MovimientosCustodia` | `Contrato`, `FechaDevolucionReal` |
| `Alertas` | `Contrato` |
| `CamposPersonalizados` | `Categoria` |
| `ContratosCamposValor` | `Contrato`, `Campo` |

> Crea los índices **antes** de cargar datos. Sobre una lista con muchos
> elementos, SharePoint a veces rechaza la creación del índice.

---

## D · Permisos

Todo esto es navegador. La matriz completa de quién puede qué está en
[`05-seguridad-permisos.md`](05-seguridad-permisos.md); aquí va el cómo.

### D.1 · Los dos niveles de permiso personalizados

Son los que impiden que alguien borre un expediente o reescriba una aprobación.
SharePoint no los trae de fábrica.

**Configuración del sitio** (engranaje → *Configuración del sitio*) **→ Niveles
de permiso → Agregar un nivel de permiso.**

| Nivel a crear | Cómo |
|---|---|
| **Aportar sin eliminar** | Copia *Contribuir* → desmarca `Eliminar elementos` y `Eliminar versiones` |
| **Solo agregar** | Copia *Contribuir* → desmarca `Editar elementos`, `Eliminar elementos` y `Eliminar versiones` |

Para copiar: abre *Contribuir* → abajo del todo **Copiar nivel de permiso** →
ponle el nombre nuevo → ajusta las casillas → **Crear**.

### D.2 · Los seis grupos

**Configuración del sitio → Personas y grupos → Nuevo → Grupo.** Crea:

`Contratos - Administradores` · `Contratos - Legal` · `Contratos - Aprobadores` ·
`Contratos - Custodios` · `Contratos - Solicitantes` · `Contratos - Consulta`

### D.3 · Aplicar los permisos por lista

Para cada lista: *Configuración de la lista → Permisos para esta lista →*
**Dejar de heredar permisos** → quita los grupos que trae por herencia → **Conceder
permisos** a cada grupo con el nivel que corresponda según la matriz de
[`05-seguridad-permisos.md`](05-seguridad-permisos.md).

> **El error de despliegue más frecuente:** la cuenta que va a ser dueña de los
> flujos **tiene que estar** en `Contratos - Administradores`. Si no, el flujo 01
> falla con error 403 justo al registrar la decisión, *después* de que el
> aprobador ya respondió — y parece un problema de aprobación cuando es de
> permisos.

Si estás probando tú solo, puedes saltarte D.2 y D.3 por ahora y volver antes de
usar el sistema con contratos reales. D.1 **no** te lo saltes: crear los niveles
después, con datos cargados, es más incómodo.

---

## E · Datos iniciales (sin script)

Aquí hay un atajo que ahorra mucho tiempo: **la vista de cuadrícula permite pegar
desde Excel.**

En cualquier lista → **Editar en vista de cuadrícula** (o *Edición rápida*) →
te queda una hoja de cálculo → **copias un bloque de celdas desde Excel y lo
pegas directo**. Así cargas 20 reglas de la matriz en un minuto en vez de abrir
20 formularios.

> La cuadrícula no acepta pegado en columnas de tipo **Persona** ni **Búsqueda**
> de forma confiable. Pega primero las columnas de texto y número, y completa
> las de persona/búsqueda a mano después.

### E.1 · `Parametros` — obligatorio

Sin esto la app arranca sin configuración. Una fila por clave, `Title` = clave,
`Valor` = valor:

| Title | Valor |
|---|---|
| `MONEDA_BASE` | `PEN` |
| `TC_USD` | `3.75` |
| `TC_EUR` | `4.05` |
| `DIAS_PREAVISO_DEFAULT` | `30` |
| `DIAS_ALERTA_ESCALONADA` | `90,60,30,15,7,1` |
| `SLA_APROBACION_HORAS` | `48` |
| `DOCUSIGN_HABILITADO` | `false` |
| `RETENCION_ANIOS` | `10` |
| `PREFIJO_CODIGO` | `CTR` |
| `CORREO_LEGAL` | *tu correo* |
| `CORREO_ADMIN_CONTRATOS` | *tu correo* |
| `ADMINS` | *tu correo* |
| `CUSTODIOS` | *tu correo* |
| `LEGAL` | *tu correo* |

Las tres últimas son las que hacen que la app te reconozca como administrador.
Varios correos van separados por `;`.

> Deja `DOCUSIGN_HABILITADO` en `false` hasta que tengas la cuenta de DocuSign
> conectada. Con el interruptor en `true` y sin conector, el flujo 02 falla en
> cada contrato aprobado.

### E.2 · `Areas` — obligatorio

Al menos un área, con `Responsable` y `Gerente` (columnas de tipo Persona) —
**de ahí salen los aprobadores** de los roles «Jefe de área» y «Gerente de
área». Un área sin responsable detiene la aprobación.

### E.3 · `Categorias` — las carpetas

| Title | Color | Orden | Activo |
|---|---|---|---|
| `Logística` | `#a8692b` | 1 | Sí |
| `Comercial` | `#ff9906` | 2 | Sí |
| `Administrativo` | `#681029` | 3 | Sí |
| `Recursos Humanos` | `#375623` | 4 | Sí |
| `Legal` | `#4e0c1f` | 5 | Sí |

`ResponsableAdicional` (Persona) es quien recibe copia de las alertas de esa
carpeta — por ejemplo, alguien de Compras en «Logística».

### E.4 · `CamposPersonalizados` — el esquema dinámico

La tabla de ejemplo está en
[`02-modelo-datos.md`, sección 12](02-modelo-datos.md#12-campospersonalizados--esquema-por-categoría).
Recuerda: **un campo con `Categoria` en blanco aplica a todas las categorías** —
así las cláusulas corporativas se definen una sola vez.

### E.5 · `MatrizAprobacion` — quién aprueba qué

Esta es la que conviene pegar desde Excel. Reglas genéricas (`TipoContrato` =
`Todos`), todas con `Obligatorio` = Sí y `Activo` = Sí:

| MontoDesdePEN | MontoHastaPEN | Nivel | RolAprobador | SLAHoras |
|---|---|---|---|---|
| 0 | 20000 | 1 | Jefe de area | 48 |
| 20000 | 100000 | 1 | Jefe de area | 48 |
| 20000 | 100000 | 2 | Gerente de area | 48 |
| 20000 | 100000 | 3 | Legal | 72 |
| 100000 | 500000 | 1 | Jefe de area | 48 |
| 100000 | 500000 | 2 | Gerente de area | 48 |
| 100000 | 500000 | 3 | Legal | 72 |
| 100000 | 500000 | 4 | Finanzas | 48 |
| 100000 | 500000 | 5 | Gerencia General | 72 |
| 500000 | 999999999 | 1 | Jefe de area | 48 |
| 500000 | 999999999 | 2 | Gerente de area | 48 |
| 500000 | 999999999 | 3 | Legal | 72 |
| 500000 | 999999999 | 4 | Finanzas | 48 |
| 500000 | 999999999 | 5 | Gerencia General | 72 |
| 500000 | 999999999 | 6 | Directorio | 120 |

Reglas específicas por tipo — **ganan sobre las genéricas en el mismo nivel**:

| TipoContrato | MontoDesdePEN | MontoHastaPEN | Nivel | RolAprobador | SLAHoras |
|---|---|---|---|---|---|
| Confidencialidad (NDA) | 0 | 999999999 | 1 | Legal | 48 |
| Laboral | 0 | 999999999 | 1 | Jefe de area | 48 |
| Laboral | 0 | 999999999 | 2 | Gerente de area | 48 |
| Laboral | 0 | 999999999 | 3 | Gerencia General | 72 |
| Suministro de bienes | 20000 | 999999999 | 2 | Compras | 48 |
| Obra | 20000 | 999999999 | 2 | Compras | 48 |

`Title` es solo una etiqueta legible; usa algo como `Todos 20k-100k - N2 Gerente`.

> **Los roles `Legal`, `Finanzas`, `Compras`, `Gerencia General` y `Directorio`
> no se resuelven solos.** En cada una de esas reglas tienes que completar
> `AprobadorUsuario` (una persona) o `AprobadorGrupo` (el correo de un grupo).
> Solo `Jefe de area` y `Gerente de area` salen automáticamente de la lista
> `Areas`. Una regla sin aprobador y con `Obligatorio` = Sí **detiene** el
> contrato.

**Para ver esta matriz funcionando antes de cargarla**, usa el simulador de la
demo web (*Administración → Simulador*): escribes un monto y un tipo, y te dice
exactamente qué niveles y qué aprobadores saldrían. Es la misma lógica que
resuelve el flujo 01.

---

## F · Los flujos, en el diseñador

Sin `Build-Package.ps1` no hay `.zip` que importar, así que los flujos se
construyen a mano en **[make.powerautomate.com](https://make.powerautomate.com)**
→ *Crear → Flujo de nube automatizado / instantáneo / programado* según el
disparador.

**[`power-automate/README.md`](../power-automate/README.md) describe cada flujo
acción por acción** — está escrito exactamente para esto.

> Los `definition.json` del repositorio traen `CONTOSO.sharepoint.com` como
> marcador (lo reemplazaba `Build-Package.ps1`). Construyendo en el diseñador
> eso deja de importar: el sitio y la lista se eligen de un desplegable en cada
> acción. Usa los `definition.json` solo como referencia de las **expresiones**
> —los `formatDateTime`, `div(ticks(...))` y demás— que sí conviene copiar tal
> cual.

Empieza por el **flujo 05 (Numeración)**: es el más corto (12 acciones) y sirve
de prueba de que la conexión a SharePoint funciona. Si al crear un contrato
aparece solo el código `CTR-2026-0001`, todo lo de la sección B quedó bien.

Después, el **flujo 01 (Solicitud de aprobación)**. Es largo —48 acciones— pero
es el que hace funcionar el sistema. Los tres errores clásicos al construirlo
están documentados en ese README: *Responder a Power Apps va en medio y no al
final*, *la concurrencia del bucle debe ser 1*, y *un rechazo no corta el bucle
con Terminar*.

Los flujos 02, 03, 04 y 06 se pueden dejar para después: alertas, DocuSign y
préstamos no bloquean el circuito de aprobación.

---

## G · La app

**Sin cambios.** Sigue el [paso 9 de la guía rápida](00-inicio-rapido.md#paso-9--construye-la-app-en-power-apps-web)
tal cual está escrito — siempre fue navegador puro: se construye en
[make.powerapps.com](https://make.powerapps.com), pegando las fórmulas de
[`canvas-app/formulas/`](../canvas-app/formulas/) pantalla por pantalla.

El orden recomendado de construcción de las 7 pantallas está en
[`canvas-app/README.md`](../canvas-app/README.md), *Camino B*.

### ⚠️ «Navegador» aquí significa navegador de escritorio

Esta es la única parte de la guía que **no** se puede hacer desde una tablet o
un teléfono. Microsoft solo admite Power Apps Studio —el diseñador— en
**Windows 10+ o macOS 10.13+**, con **Chrome o Edge**. Android e iOS aparecen
en la documentación únicamente para *ejecutar* aplicaciones, nunca para
construirlas
([requisitos de sistema de Power Apps](https://learn.microsoft.com/en-us/power-apps/limits-and-config)).

El diseñador de Power Automate tiene el mismo problema en la práctica: es un
lienzo de arrastrar y soltar pensado para mouse y teclado.

**Qué sí se puede hacer desde una tablet:** las secciones A a E completas —o
sea, todo SharePoint, que es el 80 % del trabajo manual. La interfaz moderna de
SharePoint funciona bien en tablet; las pantallas clásicas de *Configuración del
sitio* (niveles de permiso) no son adaptables y exigen hacer zoom, pero
funcionan.

**Si la tablet es tu único equipo**, en orden de preferencia:

1. **Escritorio remoto** hacia cualquier PC con Windows a la que tengas acceso
   (Chrome Remote Desktop es gratis). Te da un escritorio real desde la tablet
   y resuelve todo.
2. **Haz SharePoint en la tablet** y pide prestada una computadora solo para
   las secciones F y G.
3. **Teclado y mouse Bluetooth + «Versión para computadora» en el navegador.**
   No está soportado, pero *no soportado* no es lo mismo que *bloqueado*:
   significa que Microsoft no lo prueba ni corrige errores ahí. Puede cargar y
   funcionar a medias. La prueba de 20 minutos de abajo lo resuelve.
4. **Replantea si necesitas Power Apps.** Una aplicación web equivalente corre
   perfecto en la tablet, sin tenant, sin Studio y sin escritorio. Si el
   dispositivo principal de quien administra el sistema es una tablet, esta
   deja de ser la opción de respaldo y pasa a ser la decisión sensata.

### La prueba de 20 minutos antes de apostar horas

No hay forma de saber de antemano si tu tablet concreta aguanta el diseñador.
Averígualo con un experimento corto, **antes** de invertir las horas de
SharePoint pensando en terminar ahí:

1. Conecta **teclado y mouse Bluetooth**. Pon la tablet en horizontal.
2. En Edge o Chrome: menú ⋮ → **Versión para computadora**.
3. Entra a [make.powerapps.com](https://make.powerapps.com) → **Crear →
   Aplicación en blanco → formato Tableta**.
4. Comprueba estas cuatro cosas, en este orden:

| # | Prueba | Si falla |
|---|---|---|
| 1 | ¿Se ven los **tres paneles** (árbol, lienzo, propiedades)? | Pantalla insuficiente: descarta |
| 2 | **Insertar → Botón**: ¿aparece y puedes seleccionarlo? | Descarta |
| 3 | ¿Puedes **arrastrarlo** por el lienzo y redimensionarlo? | Descarta |
| 4 | ¿Puedes **pegar una fórmula larga** en la barra de fórmulas? | Descarta |

Las cuatro tienen que pasar. La 4 es la decisiva: construir esta app son
cientos de líneas de Power Fx pegadas en esa barra; si ahí se pelea, el resto
no importa.

**Si las cuatro pasan**, sigue adelante con cuidado y guarda seguido. **Si
alguna falla**, no insistas: haz las secciones A–E en la tablet —que sí
funcionan— y resuelve F y G por escritorio remoto o equipo prestado.

---

## Verificación: ¿quedó bien hecho?

Antes de dar por terminada la parte de SharePoint, comprueba estas cuatro cosas.
Las cuatro fallan en silencio si están mal.

| Comprobación | Cómo | Si falla |
|---|---|---|
| Los nombres internos | Con la URL de abajo, todos de golpe | Aparece `_x0020_` → recrea esa columna con el nombre sin espacios |
| Las listas están completas | Cuenta: deben ser **13 listas + 1 biblioteca** | Falta alguna → revisa el orden de la sección B |
| Los valores de Elección | Compara letra por letra con el catálogo de `02-modelo-datos.md` | Un acento distinto → el flujo no encuentra la regla |
| La matriz resuelve | Simulador de la demo web, o crea un contrato de prueba de S/ 25 000 | 0 niveles → revisa los tramos `MontoDesde`/`MontoHasta` |

El error más caro es el primero, porque no da ningún síntoma hasta que la app
muestra campos vacíos sin explicar por qué.

### Ver todos los nombres internos de una vez

No hace falta abrir columna por columna ni tener consola. Pega esto en la barra
de direcciones, con sesión ya iniciada, cambiando el sitio y la lista:

```
https://TU-TENANT.sharepoint.com/sites/Contratos/_api/web/lists/getbytitle('Contratos')/fields?$select=InternalName&$filter=Hidden eq false
```

El navegador muestra la respuesta como texto. Busca con Ctrl+F un par de
nombres que sepas que deben estar —`NombreContrato`, `MontoPEN`,
`EstadoCustodia`— y comprueba que aparecen tal cual.

**La señal de alarma es `_x0020_`.** Si algún nombre lo lleva, esa columna se
creó desde la interfaz en vez de por la API, y las fórmulas no la van a
encontrar.

Funciona igual en tablet: es una dirección web, no una herramienta de
desarrollador.

---

## Si algo falla

| Síntoma | Causa más probable |
|---|---|
| La app muestra los campos en blanco aunque la lista tiene datos | Nombre interno con `_x0020_` — el más común de todos |
| No se puede crear una columna de Búsqueda | La lista de destino todavía no existe → revisa el orden de la sección B |
| El contrato no recibe código | El flujo 05 no está activado (interruptor arriba a la derecha) |
| «No tienes acceso a la administración» | Falta tu correo en la fila `ADMINS` de `Parametros` |
| El flujo 01 falla con 403 al registrar la decisión | La cuenta dueña del flujo no está en `Contratos - Administradores` |
| La aprobación no llega a nadie | El área del contrato no tiene `Responsable`, o la regla usa un rol sin `AprobadorUsuario` |
| El contrato se detiene sin aprobadores | Ningún tramo de la matriz cubre ese monto — verifica en el simulador |

El resto de diagnósticos está en [`08-operacion.md`](08-operacion.md).
