# Tasks: Traslados de Stock entre Tiendas

**Feature**: 012-traslados-stock-entre-tiendas | **Input**: plan.md, research.md, data-model.md, contracts/traslados-stock-entre-tiendas.md, quickstart.md

**Tests**: este proyecto exige tests de contrato e integración (Principio X) — cada endpoint de contracts/ tiene su test antes de la implementación (TDD por historia de usuario).

## Phase 1: Setup

- [X] T001 Crear rama `012-traslados-stock-entre-tiendas` y confirmar que `.specify/feature.json` apunta a esta feature.
- [X] T002 [P] Crear paquete `backend/modules/operaciones/traslados/` con `__init__.py`, `router.py`, `service.py`, `repository.py`, `schemas.py` vacíos.
- [X] T003 [P] Crear stub de tests `backend/tests/contract/test_traslados_stock.py` y `backend/tests/integration/test_ciclo_traslado.py`.
- [X] T004 [P] Crear `frontend/src/stores/traslados.ts` (Pinia store vacío) y carpeta `frontend/src/modules/operaciones/` para los 4 componentes nuevos (data-model.md, plan.md §Project Structure).

## Phase 2: Foundational (bloqueante para todas las historias)

- [X] T005 Migración Alembic: extender el CHECK de `traslados_stock.estado` para incluir `'rechazado'` (data-model.md).
- [X] T006 Migración Alembic: agregar columnas `resuelto_por`, `fecha_resolucion`, `recibido_por`, `fecha_recepcion`, `fecha_cancelacion` a `traslados_stock`, con sus CHECK de consistencia (data-model.md).
- [X] T007 Migración Alembic: crear los 3 índices de `traslados_stock` (`idx_traslados_stock_estado`, `idx_traslados_stock_tienda_origen`, `idx_traslados_stock_tienda_destino`).
- [X] T008 Seed: agregar filas de `role_permisos_tabla` para `traslados_stock` (Jefe_Operaciones CRUD completo, Encargado_Tienda select/insert/update) bajo el módulo `Operaciones` ya reservado (data-model.md §RBAC).
- [X] T009 [P] Definir schemas Pydantic base (`TrasladoCreate`, `TrasladoOut`, `TrasladoResolucion`) en `schemas.py`.

**Checkpoint**: schema y RBAC listos — cualquier historia de usuario puede implementarse desde aquí en cualquier orden.

## Phase 3: User Story 1 - Consultar stock de otras sucursales antes de comprar (P1) 🎯 MVP

### Tests

- [X] T010 [P] [US1] Contract test `GET /productos/{product_id}/disponibilidad-sucursales` (200 con disponibilidad por tienda).
- [X] T011 [P] [US1] Contract test de la extensión de `GET /ordenes-compra/sugerencias` (campo `disponibilidad_otras_tiendas` presente en cada ítem).
- [X] T012 [US1] Integration test: producto sembrado en ≥2 tiendas, verificar que ambos valores llegan juntos en una sola respuesta (Independent Test de spec.md).

### Implementation

- [X] T013 [US1] Implementar `repository.py`: consulta de `inventario` agrupada por `product_id` con join a `tiendas` para el nombre.
- [X] T014 [US1] Implementar `service.py` y `router.py` para `GET /productos/{product_id}/disponibilidad-sucursales` (contracts/traslados-stock-entre-tiendas.md #1).
- [X] T015 [US1] Extender el endpoint ya existente de sugerencias de compra (001) para incluir `disponibilidad_otras_tiendas` (contracts #2, research.md Decisión 5).
- [X] T016 [P] [US1] Componente `DisponibilidadSucursales.vue` (tabla por tienda) y su integración en la pantalla de sugerencias de compra existente.
- [X] T017 [US1] Acción Pinia `fetchDisponibilidad(productId)` en `stores/traslados.ts`.

**Checkpoint**: US1 funciona de forma independiente y es demostrable — MVP entregable.

## Phase 4: User Story 2 - Solicitar y aprobar un traslado entre tiendas (P2)

### Tests

- [X] T018 [P] [US2] Contract test `POST /traslados` (201 en éxito, 422 con `tienda_origen_id == tienda_destino_id` o `cantidad <= 0`).
- [X] T019 [P] [US2] Contract test `GET /traslados?estado=solicitado&tienda_origen_id=...` con alcance restringido a la tienda del `Encargado_Tienda`.
- [X] T020 [P] [US2] Contract test `PATCH /traslados/{id}/resolucion` (aprobar → 200 `en_transito`; rechazar → 200 `rechazado`; 409 si excede stock disponible).
- [X] T021 [US2] Integration test: ciclo solicitud → aprobación → verificar `inventario.cantidad_disponible` de origen decrementado y fila nueva en `movimientos_inventario` (`traslado_salida`).
- [X] T022 [US2] Integration test: solicitud por cantidad mayor al stock disponible al momento de aprobar → 409 con stock real informado (Edge Case, FR-005).
- [X] T023 [US2] Integration test: rechazo de una solicitud → estado `rechazado`, sin ningún efecto sobre inventario.

### Implementation

- [X] T024 [US2] Implementar alta de solicitud en `repository.py`/`service.py` (`estado='solicitado'`) — contracts #3.
- [X] T025 [US2] Implementar listado filtrado por estado/tienda con restricción de alcance para `Encargado_Tienda` (capa de servicio) — contracts #4.
- [X] T026 [US2] Implementar resolución (aprobar/rechazar) en `service.py`: revalidación autoritativa de stock disponible dentro de la misma transacción, descuento de `inventario`, decremento FIFO de `lotes` de origen, inserción en `movimientos_inventario` (`traslado_salida`) — research.md Decisión 3, contracts #5.
- [X] T027 [US2] Validar en capa de servicio que solo el `Encargado_Tienda` de la tienda origen (o `Jefe_Operaciones`) puede resolver la solicitud.
- [X] T028 [P] [US2] Componentes `SolicitarTraslado.vue` y `AprobarTraslados.vue`.
- [X] T029 [P] [US2] Acciones Pinia `solicitarTraslado`, `listarPendientes`, `resolverTraslado` en `stores/traslados.ts`.

**Checkpoint**: US2 funciona sobre la base de US1 (o de forma independiente si US1 no está desplegado) — el flujo de coordinación de stock es real y auditable.

## Phase 5: User Story 3 - Confirmar recepción del traslado en la tienda destino (P3)

### Tests

- [X] T030 [P] [US3] Contract test `PATCH /traslados/{id}/recepcion` (200 `recibido`; 409 si el traslado no está `en_transito`).
- [X] T031 [P] [US3] Contract test `PATCH /traslados/{id}/cancelacion` (200 `cancelado`; 409 si ya no está `solicitado`).
- [X] T032 [P] [US3] Contract test `GET /traslados/reporte-semanal` (incluye `pendiente_confirmacion: true` para los `en_transito`).
- [X] T033 [US3] Integration test: despachar (US2) y luego confirmar recepción — verificar `inventario.cantidad_disponible` de destino incrementado y fila nueva en `movimientos_inventario` (`traslado_entrada`).
- [X] T034 [US3] Integration test: recepción de un producto perecedero — el lote nuevo de destino conserva `fecha_vencimiento` del lote de origen consumido (Edge Case, FR-010).
- [X] T035 [US3] Integration test: cancelación de una solicitud aún `solicitado` — sin ningún efecto sobre inventario (Edge Case, FR-009).

### Implementation

- [X] T036 [US3] Implementar confirmación de recepción en `service.py`: alta de `inventario` en destino, creación de lote heredando `fecha_vencimiento`, inserción en `movimientos_inventario` (`traslado_entrada`) — research.md Decisión 4, contracts #6.
- [X] T037 [US3] Implementar cancelación en `service.py`, restringida al empleado solicitante o `Jefe_Operaciones` — contracts #7.
- [X] T038 [US3] Implementar `GET /traslados/reporte-semanal` con bandera `pendiente_confirmacion` — contracts #8, FR-012.
- [X] T039 [P] [US3] Componente `ConfirmarRecepcion.vue` y vista de listado semanal para `Jefe_Operaciones`.
- [X] T040 [P] [US3] Acciones Pinia `confirmarRecepcion`, `cancelarTraslado`, `fetchReporteSemanal` en `stores/traslados.ts`.

**Checkpoint**: el ciclo completo (solicitado → en_transito → recibido, o rechazado/cancelado) queda cerrado y auditable de punta a punta.

## Phase 6: Polish

- [X] T041 [P] Revisar que los 12 FR de spec.md tengan al menos un test de contrato o integración que los cubra (tabla de trazabilidad, data-model.md).
- [X] T042 [P] Ejecutar `EXPLAIN ANALYZE` sobre la consulta de US1 y el listado semanal (FR-012) para confirmar que los índices de T007 son suficientes con el volumen de datos ya sembrado.
- [X] T043 Ejecutar quickstart.md end-to-end (5 escenarios) contra un entorno con la migración de Foundational aplicada.
- [X] T044 Re-chequeo de la tabla de Constitution Check de plan.md tras la implementación completa — confirmar que sigue en PASS en los 12 principios.

## Dependencias clave

- Foundational (T005-T009) bloquea las tres historias de usuario — ninguna puede implementarse sin el schema extendido y el RBAC de tabla seedeado.
- US1 (P1) es independiente y es el MVP — no depende de US2 ni US3.
- US2 (P2) depende de Foundational únicamente; puede desarrollarse en paralelo a US1, pero su Checkpoint de demostración end-to-end requiere que `inventario`/`movimientos_inventario` ya reflejen el descuento (no requiere que US1 esté desplegado en frontend).
- US3 (P3) depende funcionalmente de que exista al menos un traslado en `en_transito` (producido por US2) para poder probarse — se implementa después de US2 en la práctica, aunque su código no importa nada de la capa US1/US2 más allá del modelo compartido de Foundational.
- Polish (T041-T044) va después de que las tres historias tengan su Checkpoint cerrado.
