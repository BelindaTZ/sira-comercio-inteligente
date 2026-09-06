# Research: Pagos y Seguridad

**Feature**: `007-pagos-seguridad` | **Date**: 2026-09-06

## Decisión 1: Disponibilidad diaria de datáfono reutiliza el enum ya reservado (`fuera_servicio`)

**Decisión**: Marcar un datáfono "fuera de servicio" (FR-001) y "restablecido" (FR-002) actualiza `datafonos.estado` al valor `'fuera_servicio'` (o de vuelta a `'activo'`/`'requiere_actualizacion'` según Decisión 2), valor ya incluido en el `CHECK` de `datafonos.estado` desde 001, sin usarse hasta ahora (006 solo usó `activo`/`requiere_actualizacion`).

**Razón**: El esquema de 001 ya anticipó este caso de uso con ese valor de enum, exactamente igual que 006 reutilizó `requiere_actualizacion` (006, Decisión 4) para la no conformidad de seguridad. Agregar una columna booleana separada (`disponible_hoy`) sería redundante y violaría Principio VIII.

**Alternativas consideradas**: Columna booleana `disponible` separada de `estado` — rechazada porque permitiría estados contradictorios (`estado='requiere_actualizacion'` y `disponible=true` a la vez), cuando el edge case de esta feature exige explícitamente que ambos problemas (no conformidad y falta de funcionamiento físico) puedan coexistir de forma clara en un único campo de estado.

## Decisión 2: Restablecer un datáfono reevalúa conformidad reutilizando la lógica de 006, sin duplicarla

**Decisión**: Al marcar un datáfono `fuera_servicio` como restablecido (FR-002), el sistema no lo pasa directo a `'activo'` — invoca la misma función de evaluación de conformidad ya implementada en 006 (`CajaService.evaluar_conformidad_datafonos`, aplicada aquí a un único datáfono) contra `configuracion_seguridad_pagos` vigente (006); si su `version_firmware` no cumple el estándar, el resultado es `'requiere_actualizacion'` en vez de `'activo'` (FR-003, Edge Case).

**Razón**: 006 ya resolvió exactamente este cálculo (comparar `version_firmware` contra la versión mínima vigente); reimplementarlo aquí violaría DRY (Principio VIII) y crearía dos criterios de conformidad que podrían divergir con el tiempo.

**Alternativas consideradas**: Restablecer siempre a `'activo'` y dejar que el próximo ciclo de certificación de 006 lo corrija — rechazada porque el propio FR-003 exige la reevaluación inmediata al restablecer, no que quede operativo un datáfono que ya se sabe no conforme.

## Decisión 3: Extensión aditiva de `medios_pago`

**Decisión**: Se agregan a `medios_pago` (ya sembrada desde 001 como catálogo mínimo `medio_pago_id`/`nombre`) las columnas `aprobado` (BOOLEAN NOT NULL DEFAULT true), `aprobado_por` (FK nullable a `empleados`), `fecha_aprobacion` (TIMESTAMP nullable) y `fecha_baja` (TIMESTAMP nullable).

**Razón**: El catálogo de 001 solo modelaba el nombre del medio de pago para poder registrarlo en `ventas`, sin ningún control de aprobación — esta feature necesita "dejar constancia de su aprobación" (FR-005) y de la baja (FR-006) sin borrar ni desasociar ningún registro histórico de `ventas.medio_pago_id` (Principio II, no se puede perder trazabilidad de ventas ya registradas).

**Alternativas consideradas**: Tabla `medios_pago_aprobaciones` separada (uno-a-muchos, historial completo de cambios de aprobación) — rechazada por sobre-ingeniería frente a lo que pide el spec: FR-006 solo exige que la baja no afecte ventas ya registradas, no un historial completo de reaprobaciones; se prefiere la extensión aditiva simple (Principio VIII), consistente con el criterio de 006 (Decisión 8) para configuración sin valor de auditoría histórica extendida.

## Decisión 4: `incidente_seguridad_pago` como entidad nueva e independiente de `incidentes_fraude`

**Decisión**: Se crea la tabla nueva `incidente_seguridad_pago` (no se reutiliza ni se extiende `incidentes_fraude` de 006). Campos: `incidente_seguridad_id`, `datafono_id` (FK nullable — Edge Case, un reporte genérico de banco puede no identificar un datáfono), `registrado_por` (FK NOT NULL a `empleados`, quien lo registra — `Jefe_TI`), `descripcion` (TEXT NOT NULL), `estado` (`abierto`/`en_investigacion`/`cerrado`), `actualizado_por`/`fecha_actualizacion` (última transición), `fecha_hora` (apertura).

**Razón**: `incidentes_fraude` exige `empleado_id NOT NULL` (el empleado implicado en el fraude) — un incidente de seguridad de pago (ej. sospecha de clonación de tarjeta) no necesariamente implica a ningún empleado (FR-010, spec.md Assumptions), por lo que forzar ese campo produciría datos falsos (violaría Principio II) o exigiría relajar una tabla ya cerrada por 006 para un concepto de negocio distinto. FR-010 exige explícitamente que ambos incidentes puedan coexistir de forma independiente sobre el mismo datáfono — dos filas en la misma tabla con causas raíz distintas serían más difíciles de distinguir en reportes que dos tablas separadas con su propio significado.

**Alternativas consideradas**: Extender `incidentes_fraude` con `empleado_id` nullable y un campo `tipo` (`fraude_interno`/`seguridad_pago`) — rechazada porque mezclaría dos conceptos de negocio con ciclos de vida y responsables distintos (Jefe_Finanzas cierra fraude; Jefe_TI investiga seguridad de pago) en una sola tabla, complicando el RBAC de tabla (Principio IV exige permisos por tabla, no por "tipo de fila").

## Decisión 5: `politica_seguridad_pagos` como tabla append-only de versiones de texto

**Decisión**: Mismo criterio que `protocolo_escalamiento` (006, Decisión 7) y `configuracion_seguridad_pagos` (006, Decisión 5) — cada actualización de la política inserta una fila nueva (`politica_id`, `texto`, `definido_por` FK `empleados`, `fecha_creacion`); la vigente es la fila más reciente por `fecha_creacion`.

**Razón**: FR-014 exige explícitamente conservar las versiones anteriores para saber cuál estaba vigente cuando se abrió un incidente en curso — el mismo razonamiento de auditoría que ya justificó append-only para el estándar de seguridad y el protocolo de escalamiento en 006.

**Alternativas consideradas**: Ninguna nueva — decisión idéntica a un patrón ya validado dos veces en 006, sin motivo para desviarse (Principio VIII).

## Decisión 6: `fecha_inicio_cobro` como columna nueva y nullable en `ventas`, sin tocar `fecha_hora`

**Decisión**: Se agrega `fecha_inicio_cobro` (TIMESTAMP, nullable) a `ventas` (001). La columna ya existente `fecha_hora` no se renombra ni cambia de semántica — sigue siendo el momento de confirmación de la venta, tal como la usan 001-006. La duración de cobro (FR-015) se calcula como `fecha_hora - fecha_inicio_cobro` solo cuando `fecha_inicio_cobro IS NOT NULL`.

**Razón**: Renombrar o reinterpretar `fecha_hora` rompería silenciosamente el significado que 001-006 ya le dieron (Principio IX — no se reescribe aditivamente el significado de un campo ya usado por 5 features cerradas). Una columna nueva y estrictamente nullable es la extensión más simple que no reinterpreta nada existente (Principio VIII).

**Alternativas consideradas**: Tabla `duracion_cobro` separada (uno-a-uno con `ventas`) — rechazada por ser una relación 1:1 sin motivo de negocio para vivir aparte (no tiene ciclo de vida propio ni entidad relacionada adicional), violaría Principio VIII sin ningún beneficio sobre una columna adicional.

## Decisión 7: Cold start del tiempo de cobro — solo prospectivo, mismo criterio que 004

**Decisión**: `fecha_inicio_cobro` se completa únicamente en ventas registradas en vivo a partir de esta feature; las ~1.47M ventas ya sembradas de Dunnhumby, y cualquier venta registrada por 001-006 antes de esta feature, quedan con `fecha_inicio_cobro = NULL` y se excluyen automáticamente de los reportes de tiempo de cobro (FR-015 Edge Case).

**Razón**: El dataset no trae un momento de inicio de venta distinto del de confirmación — fabricarlo violaría Principio VII. Es el mismo criterio de "cold start" ya usado en 004 (pronóstico de demanda) para datos que el sistema empieza a producir desde que una capacidad nueva está disponible.

**Alternativas consideradas**: Aproximar `fecha_inicio_cobro` como `fecha_hora` menos un promedio estimado — rechazada por fabricar un dato que el Principio VII prohíbe explícitamente presentar como real.

## Decisión 8: Advertencia de datáfono fuera de servicio — consulta cruzada de solo lectura `ventas` → `finanzas`

**Decisión**: El flujo de cobro con tarjeta (`modules/ventas/`, 001) consulta de solo lectura `datafonos.estado` de la caja (`modules/finanzas/`, 006) antes de intentar el cobro (FR-004); no se duplica la tabla `datafonos` ni su estado en `modules/ventas/`.

**Razón**: Mismo patrón ya establecido en 006 (consulta de solo lectura de `finanzas`→`inventario` para el reporte de patrones) y en 001 (Ronda 9/10, consultas cruzadas entre módulos del mismo backend) — evita duplicar el dato de estado del datáfono en dos lugares que podrían divergir.

**Alternativas consideradas**: Replicar `estado` del datáfono como columna en `cajas` — rechazada por duplicar un dato que ya vive en `datafonos`, violando DRY (Principio VIII).

## Decisión 9: Resumen de cambios de BSC y RBAC

- **Cambio de BSC — nueva OO-6.3.3**: bajo el OT-6.3 ya existente (mismo criterio que OO-3.5.3 en 005 y OT-6.5 en 001: extender un OT ya existente en vez de crear uno nuevo cuando el objetivo estratégico padre ya lo cubre). Ya reflejada en `domain-context.md` §8 y en el documento de proyecto `oo-objetivos-operativos.txt`.
- **OT-4.2 incorporado a pedido explícito del usuario**: sin feature dueña previa, mismo OE-4 ("experiencia de cobro en el punto de venta") que OT-4.1 — ver `spec.md` Assumptions para el detalle completo de por qué OO-4.2.1 no requiere FR nuevo.
- **Sin gap de rol RBAC nuevo**: los actores de esta feature (`Encargado_Tienda`, `Jefe_TI`, `Jefe_Finanzas`, `Jefe_Comercial`) ya tienen rol propio sembrado.
- **Dos accesos concedidos entre módulos, ambos siguiendo el patrón ya usado en 005/006**: `Jefe_TI` extiende su acceso ya concedido a `Finanzas` (006, Decisión 10) y recibe uno nuevo a `Ventas` (solo para `medios_pago`); `Jefe_Comercial` recibe acceso de solo lectura a `Ventas` (mismo patrón exacto que `Jefe_Marketing`→`Ventas` en 005) para el reporte mensual de tiempo de cobro por tienda (FR-017).
- **Tabla `role_permisos_tabla` no tenía filas para `incidente_seguridad_pago` ni `politica_seguridad_pagos`** (tablas nuevas) — se agregan en el seed de esta feature (data-model.md, Extensión RBAC).
