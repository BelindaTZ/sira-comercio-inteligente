# Research: Traslados de Stock entre Tiendas

**Feature**: 012-traslados-stock-entre-tiendas | **Fecha**: 2026-09-06

## Decisión 1: reconciliación de `estado` en `traslados_stock` (ya reservada)

**Decisión**: la tabla ya reservada define `estado VARCHAR(20) CHECK (estado IN ('solicitado','en_transito','recibido','cancelado'))`. Se extiende de forma aditiva agregando `'rechazado'` al CHECK (los otros cuatro valores ya cubren el ciclo). "Despachado", el término usado en spec.md para el momento en que el stock sale de la tienda origen, se mapea al valor ya reservado `en_transito` — no se agrega un valor nuevo para el mismo hecho. "Aprobado" no se persiste como valor de `estado`: FR-006 exige que aprobar y descontar/despachar ocurran en la misma operación, así que el estado salta directamente de `solicitado` a `en_transito`; el hecho de la aprobación se registra en las columnas `resuelto_por`/`fecha_resolucion` (Decisión 2), no en un estado transitorio separado.

**Alternativas consideradas**: (a) agregar `'aprobado'` y `'despachado'` como dos valores nuevos distintos de `en_transito` — rechazada por Principio VIII (duplicaría el significado de un valor ya reservado sin ganar expresividad, ya que FR-006 los colapsa en la misma operación); (b) reescribir el CHECK completo con nombres nuevos — rechazada porque rompería la reserva original sin necesidad, cuando una extensión aditiva de un solo valor (`'rechazado'`) basta.

## Decisión 2: columnas de trazabilidad por transición (aditivo sobre `traslados_stock`)

**Decisión**: la tabla reservada solo tiene `empleado_id` (solicitante) y `fecha_hora` (fecha de la solicitud) — no alcanza para registrar quién resolvió (aprobó/rechazó) ni quién recibió, como exige FR-011. Se agregan cuatro columnas aditivas: `resuelto_por` (FK a `empleados`, nullable — Encargado de la tienda origen que aprueba o rechaza), `fecha_resolucion` (TIMESTAMP, nullable), `recibido_por` (FK a `empleados`, nullable — Encargado de la tienda destino que confirma recepción) y `fecha_recepcion` (TIMESTAMP, nullable). La cancelación (FR-009) reutiliza `empleado_id` y agrega solo `fecha_cancelacion` (TIMESTAMP, nullable), porque solo el propio solicitante puede cancelar su solicitud mientras siga en estado `solicitado` (mismo empleado, no hace falta una columna de "quién" adicional).

**Alternativas consideradas**: una tabla de historial de transiciones (`traslado_transicion_log`) que registre cada cambio de estado en una fila separada — rechazada por Principio VIII: el ciclo de este flujo es lineal y de un solo camino por transición (nunca se revierte un estado), así que columnas nullable en la misma fila capturan toda la trazabilidad exigida por FR-011 sin el costo de una tabla y sus joins.

## Decisión 3: recálculo de stock disponible al momento de aprobar (FR-005, Edge Case)

**Decisión**: la validación de que la cantidad solicitada no exceda el stock disponible se ejecuta dos veces: una validación optimista al registrar la solicitud (US2, informativa) y una validación autoritativa e inmediatamente antes del `UPDATE` de `inventario.cantidad_disponible`, dentro de la misma transacción que marca el traslado como `en_transito` — así se cierra la ventana de condición de carrera descrita en el Edge Case (ventas concurrentes entre la solicitud y la aprobación).

**Alternativas consideradas**: bloqueo pesimista de la fila de `inventario` desde que se registra la solicitud — rechazada porque dejaría el stock de la tienda origen inutilizable para ventas mientras la solicitud espera aprobación (que puede tardar días), contradiciendo el flujo real de una tienda que sigue vendiendo mientras decide si aprueba el traslado.

## Decisión 4: preservación de fecha de vencimiento al recibir (FR-010, Edge Case)

**Decisión**: al confirmar la recepción (US3) de un producto perecedero, el servicio crea una nueva fila en `lotes` para la tienda destino, copiando `fecha_vencimiento` del lote de origen consumido por el despacho (FIFO/FEFO, mismo criterio de 001) en vez de usar la fecha de recepción. El lote de origen se decrementa (o se cierra si llega a cero) en el momento del despacho (`en_transito`), no en la recepción, para que el stock de la tienda origen deje de contar ese producto tan pronto como sale físicamente.

**Alternativas consideradas**: registrar la fecha de vencimiento en `traslados_stock` en vez de en un nuevo `lotes` de destino — rechazada porque duplicaría un dato que `lotes` ya modela correctamente por tienda, y porque el resto del sistema (alertas de vencimiento de 001) ya consulta `lotes` por `tienda_id`; un traslado sin lote propio en destino quedaría invisible para esas alertas.

## Decisión 5: disponibilidad por sucursal embebida en la sugerencia de compra (FR-002)

**Decisión**: el endpoint de sugerencia de orden de compra ya existente de 001 se extiende (contrato, no schema) para incluir un campo adicional `disponibilidad_otras_tiendas` por producto sugerido, calculado con la misma consulta de US1. No se crea un endpoint ni una pantalla separada para este caso — es el mismo dato de US1, solo incrustado donde ya lo necesita el Jefe de Operaciones.

**Alternativas consideradas**: pantalla de reporte aparte con un enlace desde la sugerencia de compra — rechazada explícitamente por el propio FR-002 ("sin requerir navegación a un reporte aparte").

## Decisión 6: BSC / RBAC — resumen

Todos los FR trazan a OT-2.5 (OO-2.5.1: consulta de disponibilidad; OO-2.5.2: solicitud de traslado), bajo OE-2 Operaciones/Compras. Sin módulo RBAC nuevo: `Operaciones` ya es el módulo de 001; `Jefe_Operaciones` y `Encargado_Tienda` ya existen como roles seedeados. Esta feature documenta, por primera vez, el nivel de tabla (`role_permisos_tabla`) para `traslados_stock` dentro de ese módulo ya reservado — ver data-model.md §RBAC.
