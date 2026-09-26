# 91 · Cargar datos iniciales

Hermano de [`90-crear-listas`](../90-crear-listas/): aquel crea la estructura,
este la llena. Carga **45 filas** por la API REST, para no pegarlas a mano en la
vista de cuadrícula.

> No se genera a mano:
> ```bash
> python3 tools/generar-flujo-datos.py
> ```

---

## Ejecútalo una sola vez

```
1. make.powerautomate.com → Mis flujos → Importar → Paquete heredado
2. Sube power-automate/build/91-cargar-datos.zip
3. Asigna la conexión de SharePoint (la llave 🔧, hasta que pase a verde)
4. Importar → abre el flujo → Ejecutar
5. Te pide dos datos: la URL del sitio y tu correo
```

> **No lo repitas.** A diferencia del flujo 90, este **no** es idempotente:
> crear un elemento siempre crea uno nuevo, así que una segunda ejecución
> duplica las 45 filas. Si necesitas rehacerlo, vacía antes las listas.

## Qué carga

| Lista | Filas | Qué queda |
|---|---|---|
| `Parametros` | 14 | Tipos de cambio, días de preaviso, prefijo `CTR`, y tu correo en `ADMINS`, `CUSTODIOS` y `LEGAL` |
| `MatrizAprobacion` | 21 | Los 4 tramos de monto más las reglas de NDA, Laboral, Suministro y Obra |
| `Categorias` | 5 | Logística, Comercial, Administrativo, RRHH, Legal |
| `CamposPersonalizados` | 4 | Las cláusulas corporativas |
| `Areas` | 1 | Un área «General» de arranque |

El correo que escribes al ejecutar sustituye un marcador en 5 filas de
`Parametros`. Es lo que hace que la app te reconozca como administrador.

## Qué NO carga, y por qué

**Lo que depende de personas concretas.** No es una limitación técnica: es que
decidir quién aprueba no se puede generar.

| Pendiente | Dónde | Por qué |
|---|---|---|
| `Responsable` y `Gerente` del área | Lista `Areas` | De ahí salen los roles *Jefe de área* y *Gerente de área*. Un área sin responsable **detiene** la aprobación |
| `AprobadorUsuario` o `AprobadorGrupo` | `MatrizAprobacion` | Sólo en las reglas de `Legal`, `Finanzas`, `Compras`, `Gerencia General` y `Directorio`. Una regla obligatoria sin aprobador detiene el contrato |

Ambas son columnas de Persona: se completan con el selector de personas, que ya
es cómodo en la interfaz.

**Los campos propios de cada carpeta** (número de orden de compra, incoterm,
jurisdicción) tampoco se cargan. Las cláusulas sí, porque aplican a todas las
categorías y no necesitan apuntar a ninguna. Los demás se agregan desde la
pantalla de administración de la app, que existe exactamente para eso.

---

## Cómo está armado

**Un solo bucle sobre 45 filas.** Cada una lleva su lista de destino y su
cuerpo ya serializado, así que la acción HTTP es siempre la misma.

**`odata=nometadata` en las cabeceras.** Crear un elemento con `odata=verbose`
obliga a declarar el tipo de entidad de la lista (`SP.Data.<algo>ListItem`),
que se deriva de la URL y no del título, y habría que consultarlo lista por
lista. Con `nometadata` basta el JSON de las columnas.

**Los cuerpos se serializan al generar, no en el flujo.** El campo *Body* es
texto: construirlo con expresiones convierte los números en cadenas y
SharePoint responde `Edm.Int32`. Es el mismo motivo que en el flujo 90.

**El fallo de una fila no detiene el resto**, por el `Compose` de cierre que
acepta `Failed`.

## Verificación

Las 45 filas se comprobaron contra el esquema real extraído de
`Deploy-Contratos.ps1`: toda columna referenciada existe, todo valor de Elección
está entre las opciones válidas de su columna, y los números y booleanos llegan
con su tipo.

**No se ha ejecutado contra un tenant real**, igual que el resto del repositorio.
