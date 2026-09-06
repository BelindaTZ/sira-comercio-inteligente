# Feature Specification: Traslados de Stock entre Tiendas

**Feature Branch**: `012-traslados-stock-entre-tiendas`

**Created**: 2026-09-06

**Status**: Draft

**Input**: OT-2.5 completo (OE-2 Operaciones/Compras — OO-2.5.1 revisar stock de otras sucursales antes de comprar, semanal; OO-2.5.2 registrar solicitud de traslado entre sucursales, por evento), gap de BSC sin feature dueña desde el cierre de 006. Dividido de OT-2.4 por decisión explícita del usuario: OT-2.4 (límites de stock máximo) se incorporó como extensión de 001 (Ronda 9); OT-2.5, por tratarse de un flujo propio (solicitud → aprobación → despacho → recepción) y no de una alerta, se especifica aquí en una feature nueva y acotada.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Consultar stock de otras sucursales antes de comprar (Priority: P1) 🎯 MVP

El Jefe de Operaciones, antes de aprobar una orden de compra sugerida (001), consulta cuánto stock disponible tiene un producto en cada tienda de la red, para decidir si conviene trasladar desde una sucursal con exceso en vez de comprar más al proveedor.

**Why this priority**: Es la acción más simple (solo lectura) y la que hace evidente el problema narrado (stock muerto en una tienda mientras otra compra de más) — sin ella, ninguna decisión de traslado tiene información real detrás.

**Independent Test**: se puede probar consultando el stock de un producto ya sembrado en al menos dos tiendas distintas y verificando que ambos valores se muestran juntos, sin tener que entrar tienda por tienda.

**Acceptance Scenarios**:

1. **Given** un producto con stock registrado en varias tiendas, **When** el Jefe de Operaciones consulta su disponibilidad por sucursal, **Then** el sistema muestra el stock disponible de cada tienda en una sola vista.
2. **Given** una orden de compra sugerida para un producto que tiene exceso de stock en otra tienda, **When** el Jefe de Operaciones revisa esa sugerencia, **Then** puede ver la disponibilidad en otras sucursales desde la misma pantalla, sin navegar a un reporte aparte.

---

### User Story 2 - Solicitar y aprobar un traslado entre tiendas (Priority: P2)

Un Encargado de Tienda registra una solicitud de traslado de un producto desde otra sucursal que tiene stock disponible. El Encargado de la tienda origen aprueba o rechaza la solicitud; al aprobarla, el sistema descuenta el stock de su tienda y marca el traslado como despachado.

**Why this priority**: Es el corazón operativo de OO-2.5.2 — sin esto, la visibilidad de US1 no se traduce en ninguna acción real de coordinación de stock.

**Independent Test**: se puede probar registrando una solicitud de traslado, aprobándola desde la tienda origen, y verificando que el stock de esa tienda disminuye en la cantidad trasladada.

**Acceptance Scenarios**:

1. **Given** una tienda con stock disponible de un producto, **When** un Encargado de otra tienda registra una solicitud de traslado indicando producto, cantidad y tienda origen, **Then** la solicitud queda visible para el Encargado de la tienda origen en estado solicitado.
2. **Given** una solicitud de traslado pendiente, **When** el Encargado de la tienda origen la aprueba, **Then** el sistema descuenta la cantidad del stock disponible de esa tienda y la solicitud pasa a despachada.
3. **Given** una solicitud de traslado pendiente, **When** el Encargado de la tienda origen la rechaza, **Then** la solicitud queda como rechazada sin ningún efecto sobre el inventario.
4. **Given** una solicitud de traslado por una cantidad mayor al stock disponible de la tienda origen al momento de aprobarla, **When** el Encargado intenta aprobarla, **Then** el sistema lo impide e informa el stock real disponible (Edge Case).

---

### User Story 3 - Confirmar recepción del traslado en la tienda destino (Priority: P3)

El Encargado de la tienda destino confirma la recepción física de un traslado ya despachado; al confirmarla, el sistema agrega la cantidad recibida al stock disponible de esa tienda, cerrando el ciclo.

**Why this priority**: Cierra el flujo abierto por US2 — sin esta confirmación, el stock trasladado queda descontado del origen pero nunca disponible en el destino, dejando el traslado en el aire.

**Independent Test**: se puede probar despachando un traslado (US2) y luego confirmando su recepción, verificando que el stock disponible de la tienda destino aumenta en la cantidad recibida.

**Acceptance Scenarios**:

1. **Given** un traslado en estado despachado, **When** el Encargado de la tienda destino confirma su recepción, **Then** el sistema agrega la cantidad al stock disponible de esa tienda y el traslado pasa a recibido.
2. **Given** un traslado de un producto perecedero, **When** se confirma la recepción, **Then** el sistema conserva la fecha de vencimiento del lote de origen en el lote resultante de la tienda destino (Edge Case).

---

### Edge Cases

- ¿Qué pasa si, entre que se registra la solicitud y se aprueba, el stock de la tienda origen bajó por ventas concurrentes? El sistema recalcula el stock disponible al momento de la aprobación y no permite aprobar más de lo realmente disponible en ese instante.
- ¿Qué pasa si se solicita un traslado de un producto ya descontinuado? El sistema lo permite si aún tiene stock remanente en la tienda origen — mismo criterio que 001 para productos descontinuados con stock remanente.
- ¿Qué pasa si un traslado queda despachado y la tienda destino nunca confirma la recepción? El traslado permanece despachado indefinidamente (no hay una expiración automática); queda visible en el listado semanal del Jefe de Operaciones como pendiente de confirmar.
- ¿Qué pasa si se quiere cancelar una solicitud de traslado antes de que la tienda origen la apruebe? El sistema lo permite (estado cancelado) sin ningún efecto sobre el inventario, porque aún no se movió nada.
- ¿Qué pasa con la fecha de vencimiento de un lote perecedero al trasladarse? Se conserva la fecha de vencimiento original del lote de origen — un traslado no reinicia la vida útil del producto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Jefe de Operaciones DEBE poder consultar el stock disponible de un producto en todas las tiendas de la red en una sola vista (OO-2.5.1).
- **FR-002**: El sistema DEBE mostrar la disponibilidad por sucursal de un producto directamente desde su sugerencia de orden de compra (001), sin requerir navegación a un reporte aparte (OO-2.5.1).
- **FR-003**: Un Encargado de Tienda DEBE poder registrar una solicitud de traslado de un producto desde otra tienda, indicando producto, cantidad, tienda origen y tienda destino (OO-2.5.2).
- **FR-004**: El Encargado de la tienda origen DEBE poder aprobar o rechazar una solicitud de traslado dirigida a su tienda.
- **FR-005**: El sistema NO DEBE permitir aprobar un traslado por una cantidad mayor al stock disponible de la tienda origen en el momento de la aprobación, informando el stock real (Edge Case).
- **FR-006**: Al aprobar un traslado, el sistema DEBE descontar la cantidad trasladada del stock disponible de la tienda origen y marcar el traslado como despachado.
- **FR-007**: El Encargado de la tienda destino DEBE poder confirmar la recepción de un traslado despachado.
- **FR-008**: Al confirmar la recepción, el sistema DEBE agregar la cantidad recibida al stock disponible de la tienda destino y marcar el traslado como recibido.
- **FR-009**: El sistema DEBE permitir cancelar una solicitud de traslado mientras esté en estado solicitado, sin ningún efecto sobre el inventario de ninguna tienda (Edge Case).
- **FR-010**: El sistema DEBE conservar la fecha de vencimiento del lote de origen en el lote resultante de la tienda destino, cuando el producto trasladado sea perecedero (Edge Case).
- **FR-011**: El sistema DEBE mantener trazabilidad completa del ciclo de cada traslado (solicitado → aprobado/rechazado → despachado → recibido, o cancelado), con fecha y empleado responsable de cada transición.
- **FR-012**: El Jefe de Operaciones DEBE poder consultar semanalmente el listado de traslados entre tiendas de un periodo, incluyendo los que quedaron despachados sin confirmar (OO-2.5.1).

### Key Entities

- **Solicitud de Traslado**: producto, cantidad, tienda origen, tienda destino, estado (solicitado / en_transito — equivalente a "despachado" en el lenguaje de negocio / recibido / rechazado / cancelado), empleado solicitante, empleado que aprueba/rechaza, empleado que confirma la recepción, fecha de cada transición.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Jefe de Operaciones puede ver el stock de un producto en todas las tiendas de la red sin consultar tienda por tienda.
- **SC-002**: Una solicitud de traslado puede completarse de principio a fin (solicitado → recibido) sin que nadie ajuste el inventario manualmente fuera de este flujo.
- **SC-003**: Ningún traslado aprobado deja el stock disponible de la tienda origen en un valor negativo.
- **SC-004**: El 100% de los traslados completados o cancelados quedan con responsable y fecha registrados en cada transición de su ciclo.

## Assumptions

- **Split del gap OT-2.4/OT-2.5 (decisión del usuario)**: ambos quedaban sin feature dueña desde el cierre de 006. Se decidió, con el usuario, resolver OT-2.4 (límites de stock máximo) como una extensión mínima de 001 (Ronda 9, reutiliza `alertas_inventario`), y dejar OT-2.5 (este documento) como feature propia, por ser un flujo de varios pasos con su propio ciclo de vida y no una simple alerta.
- **Boundary con 001-core-ventas-inventario**: esta feature reutiliza los modelos ya existentes de `productos`, `inventario` y `lotes` de 001, sin duplicarlos (Principio VIII); el descuento/alta de stock por traslado se registra con el mismo mecanismo de `movimientos_inventario` ya existente, con un tipo de movimiento nuevo (`traslado_salida`/`traslado_entrada`) en vez de una tabla de movimientos paralela.
- **Sin relación con el stock máximo de 001 (Ronda 9)**: un traslado no dispara ni evita la alerta de exceso de stock de 001 (esa alerta solo aplica a recepción de mercadería de proveedor) — si un traslado deja a la tienda destino por encima de su stock máximo configurado, esta versión no genera alerta; se deja fuera de alcance por simplicidad, igual que otros límites no bloqueantes ya vistos en el proyecto (ej. dar de baja el único medio de pago aprobado en 007).
- **Aprobación de un solo nivel**: el Encargado de la tienda origen es la única autorización necesaria para despachar un traslado — no se modela una aprobación intermedia del Jefe de Operaciones, mismo nivel de autonomía operativa ya usado para otros eventos "por evento" de 001 (ej. ajuste de inventario por conteo físico).
- **Sin gap de rol RBAC**: `Jefe_Operaciones` y `Encargado_Tienda` ya están sembrados en el esquema — esta feature no reaplica el patrón de "convertir en job automático por falta de rol" usado en 002/003/004/009/010.
- **Tabla ya reservada, sin uso hasta ahora**: `traslados_stock` (módulo Inventario de `01_operativo_postgres.sql`) fue reservada desde el diseño original de la base de datos sin ninguna feature que la usara — esta feature es su primer y único consumidor.
- **Corrección de terminología schema/spec (detectada al diseñar data-model.md)**: la tabla ya reservada usa el CHECK `estado IN ('solicitado','en_transito','recibido','cancelado')`, sin un valor `despachado` independiente ni `aprobado`/`rechazado`. Se reconcilia así: "despachado" (lenguaje de negocio de este documento) es el mismo hecho que `en_transito` (nombre ya reservado en el schema, no se agrega un valor nuevo para lo mismo); "aprobado" no se persiste como estado propio — es transitorio, coincide con FR-006 (aprobar y despachar ocurren en la misma operación); `rechazado` sí es un estado nuevo, ausente del CHECK original, y se añade como extensión aditiva (ver data-model.md). Esta corrección no contradice ningún FR ni Acceptance Scenario de este documento, solo alinea el nombre del Key Entity con el schema real.
