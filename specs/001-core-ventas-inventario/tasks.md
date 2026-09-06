# Tasks: Core de Ventas e Inventario (001-core-ventas-inventario)

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: incluidos — Principio X de la constitución exige cobertura obligatoria en lógica de negocio crítica (FIFO/FEFO, punto de reposición, cálculo de totales, RBAC/doble autorización); no se exige 100% del proyecto, solo estos puntos.
**Organización**: por módulo de negocio (no por feature), según decisión de `plan.md` — cada tarea referencia su archivo exacto dentro de `modules/` y el FR que resuelve.

## Format: `[ID] [P?] [Story] Descripción`
- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencias)
- **[Story]**: US1-US5 según prioridad de spec.md

---

## Phase 1: Setup

- [ ] T001 Crear estructura de carpetas `backend/src/{core,shared,models,modules,integrations}` y `frontend/src/{core,shared,services,modules,assets,router}` según plan.md
- [ ] T002 Inicializar backend: FastAPI + SQLAlchemy 2.0 async + asyncpg + Alembic + PyJWT + stripe + reportlab + sendgrid en `backend/pyproject.toml`
- [ ] T003 [P] Inicializar frontend: Vue 3 + Vite + Pinia + Tailwind + vue-echarts + Axios en `frontend/package.json`
- [ ] T004 [P] Configurar linting/formatting: ruff+black (backend), eslint+prettier (frontend)
- [ ] T005 Configurar `docker-compose.yml` con solo `postgres` y `minio` (sin ClickHouse/Airflow — Principio III fuera de alcance de esta feature)

---

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [ ] T006 Configurar conexión async a PostgreSQL y sesión de BD reutilizable en `backend/src/core/database.py`
- [ ] T007 Configurar Alembic y generar migración inicial desde `01_operativo_postgres.sql` (incluye las 3 tablas y columnas agregadas durante esta especificación)
- [ ] T008 [P] Implementar dependencia de RBAC reutilizable (decodifica JWT emitido por 008, valida rol→módulo→tabla) en `backend/src/core/security.py`
- [ ] T009 [P] Crear modelos SQLAlchemy 1:1 con las tablas de esta feature en `backend/src/models/`: `producto.py`, `venta.py`, `venta_detalle.py`, `linea_venta_removida.py`, `intento_pago_tarjeta.py`, `devolucion.py`, `anulacion_venta.py`, `lote.py`, `recepcion_mercaderia.py`, `inventario.py`, `movimiento_inventario.py`, `ajuste_inventario.py`, `merma.py`, `alerta_inventario.py`, `evento_quiebre_stock.py`, `orden_compra.py`, `orden_compra_detalle.py`, `proveedor.py`, `factura_proveedor.py`, `pago_proveedor.py`, `medio_pago.py`
- [ ] T010 [P] Implementar repositorio base genérico (paginación obligatoria, filtros reactivos — Principio XII) en `backend/src/shared/repository.py`
- [ ] T011 [P] Implementar manejo estándar de excepciones/respuestas de error y logging en `backend/src/shared/exceptions.py`
- [ ] T012 [P] Configurar clientes de integración en `backend/src/integrations/`: `stripe_client.py`, `sendgrid_client.py`, `openfoodfacts_client.py`, `reportlab_invoice.py`
- [ ] T013 [P] Frontend: composables núcleo `usePaginacion.js`, `useFiltrosReactivos.js` en `frontend/src/core/`
- [ ] T014 [P] Frontend: componentes genéricos `DataTable.vue`, `WorkPanel.vue` (Principio XII, una sola implementación reusada) en `frontend/src/shared/`
- [ ] T015 Configurar el router principal de FastAPI y montaje de módulos en `backend/src/main.py`

**Checkpoint**: infraestructura lista — las user stories pueden empezar.

---

## Phase 3: User Story 1 - Registrar una venta y cobrarla (Priority: P1) 🎯 MVP

**Goal**: un cajero registra una venta completa, cobra por cualquier medio (incluida la simulación real de tarjeta con 3 resultados) y el sistema descuenta inventario y emite comprobante.

**Independent Test**: Escenarios 1-3 de `quickstart.md` (venta con tarjeta aprobada, rechazo+reintento, remoción con doble autorización).

### Tests para User Story 1 ⚠️

- [ ] T016 [P] [US1] Contract test `POST /api/ventas` + `POST /api/ventas/{id}/lineas` en `backend/tests/contract/test_ventas_lineas.py`
- [ ] T017 [P] [US1] Contract test `DELETE /api/ventas/{id}/lineas/{id}` — verifica 403 si `autoriza_empleado_id == cajero_id` en `backend/tests/contract/test_ventas_remocion.py` (FR-027)
- [ ] T018 [P] [US1] Contract test `POST /api/ventas/{id}/pago-tarjeta` — los 3 resultados (aprobado/rechazado/error_tecnico) en `backend/tests/contract/test_ventas_pago_tarjeta.py` (FR-030)
- [ ] T019 [P] [US1] Contract test `POST /api/ventas/{id}/confirmar` en `backend/tests/contract/test_ventas_confirmar.py`
- [ ] T020 [P] [US1] Unit test cálculo de total de venta (línea a línea, sin redondeos incorrectos) en `backend/tests/unit/test_calculo_totales.py`
- [ ] T021 [P] [US1] Unit test orden determinístico de descuento FIFO/FEFO (`fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC`) en `backend/tests/unit/test_fifo_fefo.py`
- [ ] T022 [US1] Integration test Escenario 1 y 2 de quickstart.md (venta completa + rechazo/reintento) en `backend/tests/integration/test_us1_venta.py`

### Implementación de User Story 1

- [ ] T023 [US1] `VentasRepository` (consultas sobre `ventas`/`venta_detalle`) en `backend/src/modules/ventas/repository.py` (depende de T009, T010)
- [ ] T024 [US1] `VentasService.iniciar_venta` + `agregar_linea` (valida stock disponible, FR-006) en `backend/src/modules/ventas/service.py`
- [ ] T025 [US1] `VentasService.remover_linea` con `CHECK cajero_id <> autoriza_empleado_id` (FR-027) en `backend/src/modules/ventas/service.py`
- [ ] T026 [P] [US1] Integración Stripe Payment Intents con tarjetas de prueba oficiales para simular los 3 resultados (FR-030) en `backend/src/integrations/stripe_client.py`
- [ ] T027 [US1] `VentasService.procesar_pago_tarjeta` y reintento tras rechazo/error (FR-003, FR-031) en `backend/src/modules/ventas/service.py` (depende de T026)
- [ ] T028 [US1] `VentasService.confirmar_venta`: descuento FIFO/FEFO con `SELECT ... FOR UPDATE`, `tipo_comprobante`/`identificacion_comprador` (FR-005, FR-036) en `backend/src/modules/ventas/service.py`
- [ ] T029 [P] [US1] Generación de comprobante PDF (reportlab, encabezado con logo de Marzú Retail Group desde `backend/src/assets/branding/logo.png` — ver `design-system.md`) y subida al bucket MinIO `comprobantes-venta` en `backend/src/integrations/reportlab_invoice.py` (FR-004)
- [ ] T030 [US1] `VentasService.anular_venta` (revierte inventario, crea `anulaciones_venta`) en `backend/src/modules/ventas/service.py` (FR-007)
- [ ] T031 [US1] Endpoints REST del módulo ventas implementando `contracts/ventas.md` en `backend/src/modules/ventas/router.py` (depende de T024-T030)
- [ ] T032 [P] [US1] Frontend: `PuntoDeVentaPage.vue`, `TicketVenta.vue` (al confirmar con éxito, abre automáticamente `GET /api/ventas/{id}/comprobante` en pestaña nueva para imprimir/guardar — FR-004, SC-011), `BuscadorProducto.vue` (con soporte de escaneo por lector físico y por cámara) en `frontend/src/modules/pos/`
- [ ] T033 [P] [US1] Frontend: `SimuladorDatafono.vue` con las 3 animaciones (`pago-exitoso.mp4`, `pago-rechazado.mp4`, `pago-error.mp4`) en `frontend/src/modules/pos/components/`
- [ ] T034 [US1] Frontend: `ventasApi.js` (capa de servicio centralizada, Principio XI) en `frontend/src/services/`

**Checkpoint**: User Story 1 funcional y probable de forma independiente — MVP demostrable.

---

## Phase 4: User Story 2 - Gestionar inventario por lotes (Priority: P2)

**Goal**: registrar recepción de mercadería por lote, priorizar visualmente los próximos a vencer, y permitir ajustes tras conteo físico.

**Independent Test**: Escenario 6 de `quickstart.md`.

### Tests para User Story 2 ⚠️

- [ ] T035 [P] [US2] Contract test `POST /api/inventario/recepciones` en `backend/tests/contract/test_inventario_recepciones.py` (FR-014)
- [ ] T036 [P] [US2] Contract test `POST /api/inventario/ajustes` y `POST /api/inventario/mermas` en `backend/tests/contract/test_inventario_ajustes_mermas.py`
- [ ] T037 [US2] Integration test Escenario 6 de quickstart.md (rotación FIFO/FEFO) en `backend/tests/integration/test_us2_recepcion.py`

### Implementación de User Story 2

- [ ] T038 [US2] `InventarioRepository` en `backend/src/modules/inventario/repository.py`
- [ ] T039 [US2] `InventarioService.registrar_recepcion` (crea `lotes` + `recepcion_mercaderia`, exige orden `aprobada`, la pasa a `recibida`) en `backend/src/modules/inventario/service.py` (FR-014)
- [ ] T040 [US2] `InventarioService.registrar_ajuste` (usa columna generada `diferencia`) en `backend/src/modules/inventario/service.py` (FR-017)
- [ ] T041 [US2] `InventarioService.registrar_merma` + `validar_merma` en `backend/src/modules/inventario/service.py` (FR-018, FR-019)
- [ ] T042 [US2] Endpoints REST del módulo inventario (recepciones, lotes, ajustes, mermas) en `backend/src/modules/inventario/router.py`
- [ ] T043 [P] [US2] Frontend: `InventarioPage.vue`, `TablaLotes.vue` (prioriza visualmente próximos a vencer, FR-015), `FormularioAjuste.vue`, `FormularioMerma.vue` en `frontend/src/modules/inventario/`

**Checkpoint**: User Stories 1 y 2 funcionan de forma independiente.

---

## Phase 5: User Story 3 - Alertas, quiebre de stock, compras y cuentas por pagar (Priority: P3)

**Goal**: alertas de reposición dinámica y vencimiento, registro de quiebre de stock, sugerencia semanal de compra, pedido especial, y el ciclo completo de cuentas por pagar a proveedor (factura + pago con doble autorización).

**Independent Test**: Escenarios 4 y 5 de `quickstart.md`.

### Tests para User Story 3 ⚠️

- [ ] T044 [P] [US3] Unit test cálculo del punto de reposición dinámico (media móvil 14 días × lead time + 20% seguridad) en `backend/tests/unit/test_punto_reposicion.py` (FR-020)
- [ ] T045 [P] [US3] Contract test `POST /api/inventario/alertas/{id}/atender` — no duplica alerta activa en `backend/tests/contract/test_alertas.py` (FR-021)
- [ ] T046 [P] [US3] Contract test `POST /api/compras/ordenes` — exige `motivo_desviacion` si difiere de la sugerencia en `backend/tests/contract/test_compras_ordenes.py` (FR-024)
- [ ] T047 [P] [US3] Contract test `POST /api/compras/facturas/{id}/pagos` — verifica 403 si `empleado_registra_id == empleado_autoriza_id` en `backend/tests/contract/test_compras_pagos.py` (FR-034, SC-009)
- [ ] T048 [US3] Integration test Escenario 4 (alerta + sugerencia) en `backend/tests/integration/test_us3_reposicion.py`
- [ ] T049 [US3] Integration test Escenario 5 (ciclo completo orden→recepción→factura→pago) en `backend/tests/integration/test_us3_cuentas_por_pagar.py`
- [ ] T079 [P] [US3] Contract test `PUT /api/inventario/stock-maximo` + integration test de alerta `exceso_stock` al recibir por encima del máximo en `backend/tests/contract/test_stock_maximo.py` (FR-037, FR-038, Ronda 9)

### Implementación de User Story 3

- [ ] T050 [US3] Job diario de cálculo del punto de reposición y generación de `alertas_inventario` tipo `reposicion` en `backend/src/modules/inventario/service.py` (FR-020, depende de T044)
- [ ] T051 [US3] `InventarioService.atender_alerta` (índice único parcial evita duplicados) en `backend/src/modules/inventario/service.py` (FR-021)
- [ ] T052 [US3] `InventarioService.registrar_quiebre` (append-only) en `backend/src/modules/inventario/service.py` (FR-022)
- [ ] T053 [US3] Job de alertas de vencimiento (`alertas_inventario` tipo `vencimiento`, umbral configurable) en `backend/src/modules/inventario/service.py` (FR-016)
- [ ] T054 [US3] `ComprasRepository` en `backend/src/modules/compras/repository.py`
- [ ] T055 [US3] `ComprasService.generar_sugerencia_semanal` (rotación/demanda reciente) en `backend/src/modules/compras/service.py` (FR-023)
- [ ] T056 [US3] `ComprasService.aprobar_orden` (exige `motivo_desviacion` si difiere) + `frecuencia_reposicion` por proveedor en `backend/src/modules/compras/service.py` (FR-024, FR-028)
- [ ] T057 [P] [US3] `ComprasService.pedido_especial` (envío por correo vía SendGrid, `tipo='especial'`) en `backend/src/modules/compras/service.py` + `backend/src/integrations/sendgrid_client.py` (FR-029)
- [ ] T058 [US3] `ComprasService.registrar_factura_proveedor` (3-way match: exige orden `recibida`, único `orden_id`+`numero_factura`) en `backend/src/modules/compras/service.py` (FR-033)
- [ ] T059 [US3] `ComprasService.registrar_pago_proveedor` (valida `empleado_registra_id <> empleado_autoriza_id`, recalcula `estado` de la factura en la capa de servicio) en `backend/src/modules/compras/service.py` (FR-034, FR-035)
- [ ] T060 [US3] Endpoints REST del módulo compras implementando `contracts/compras.md` en `backend/src/modules/compras/router.py` (depende de T054-T059)
- [ ] T061 [P] [US3] Frontend: `ComprasPage.vue`, `TablaAlertas.vue`, `FormularioOrdenCompra.vue`, `FormularioFacturaProveedor.vue`, `FormularioPagoProveedor.vue` (con selector de autorizador distinto al registrante) en `frontend/src/modules/compras/`

- [ ] T080 [US3] `InventarioService.definir_stock_maximo` (upsert por categoría y tienda) en `backend/src/modules/inventario/service.py` (FR-037, Ronda 9)
- [ ] T081 [US3] Extender recepción de mercadería (T050 relacionado) para comparar contra `stock_maximo_categoria` vigente y generar `alertas_inventario` tipo `exceso_stock` sin bloquear la recepción en `backend/src/modules/inventario/service.py` (FR-038, depende de T050, Ronda 9)
- [ ] T082 [P] [US3] Endpoints `PUT/GET /api/inventario/stock-maximo` en `backend/src/modules/inventario/router.py` (contracts/inventario.md, Ronda 9)
- [ ] T083 [P] [US3] Frontend: `FormularioStockMaximo.vue` (Jefe de Operaciones) en `frontend/src/modules/inventario/` (Ronda 9)
- [ ] T084 [P] [US3] Contract test `POST /api/inventario/verificacion-anaquel` (upsert, exige `clasificacion_abc='A'`) y `POST /api/inventario/quiebres` marcando `es_alta_demanda` + notificación en `backend/tests/contract/test_alta_demanda.py` (FR-042, FR-043, Ronda 10)
- [ ] T085 [US3] `InventarioService.registrar_verificacion_anaquel` (upsert por producto/tienda/fecha) en `backend/src/modules/inventario/service.py` (FR-042, Ronda 10)
- [ ] T086 [US3] Extender `InventarioService.registrar_quiebre` (T052) para marcar `es_alta_demanda` y notificar de inmediato al Jefe de Operaciones en `backend/src/modules/inventario/service.py` (FR-043, depende de T052, Ronda 10)
- [ ] T087 [P] [US3] `ComprasService.reporte_automatico_vs_manual` y `ComprasService.resumen_cuentas_por_pagar` en `backend/src/modules/compras/service.py` (FR-039, FR-041, Ronda 10)
- [ ] T088 [P] [US3] Endpoints `POST /api/inventario/verificacion-anaquel`, `GET /api/compras/facturas/resumen`, `GET /api/compras/reportes/automatico-vs-manual` en sus routers respectivos (contracts/inventario.md, contracts/compras.md, Ronda 10)
- [ ] T089 [P] [US3] Frontend: `FormularioVerificacionAnaquel.vue` (Reponedor), `ReporteComprasAutomaticoManual.vue` y `ResumenCuentasPorPagar.vue` (Jefe de Operaciones/Finanzas) (Ronda 10)

**Checkpoint**: User Stories 1, 2 y 3 funcionan de forma independiente.

---

## Phase 6: User Story 4 - Mantener el catálogo de productos (Priority: P4)

**Goal**: alta, edición y baja lógica de productos, con autocompletado real vía Open Food Facts.

### Tests para User Story 4 ⚠️

- [ ] T062 [P] [US4] Contract test `POST /api/catalogo/productos` (autocompletado + fallback manual) en `backend/tests/contract/test_catalogo_productos.py` (FR-013)
- [ ] T063 [P] [US4] Contract test `PATCH`/`DELETE` de producto (precio histórico no se altera, baja lógica) en `backend/tests/contract/test_catalogo_edicion.py` (FR-010, FR-011)

### Implementación de User Story 4

- [ ] T064 [US4] `CatalogoRepository` en `backend/src/modules/catalogo/repository.py`
- [ ] T065 [US4] `CatalogoService.crear_producto` con autocompletado Open Food Facts y clasificación ancla/nicho obligatoria en `backend/src/modules/catalogo/service.py` (FR-009, FR-012, FR-013)
- [ ] T066 [US4] `CatalogoService.actualizar_producto` / `dar_de_baja` en `backend/src/modules/catalogo/service.py` (FR-010, FR-011)
- [ ] T067 [US4] Endpoints REST del módulo catálogo implementando `contracts/catalogo.md` en `backend/src/modules/catalogo/router.py`
- [ ] T068 [P] [US4] Frontend: `CatalogoPage.vue`, `FormularioProducto.vue` en `frontend/src/modules/catalogo/`

**Checkpoint**: User Stories 1-4 funcionan de forma independiente.

---

## Phase 7: User Story 5 - Registrar una devolución (Priority: P5)

**Goal**: registrar la devolución de un producto ya vendido, reintegrando inventario solo cuando el motivo lo justifique.

### Tests para User Story 5 ⚠️

- [ ] T069 [P] [US5] Contract test `POST /api/ventas/{id}/devoluciones` en `backend/tests/contract/test_devoluciones.py` (FR-025)

### Implementación de User Story 5

- [ ] T070 [US5] `VentasService.registrar_devolucion` (reintegra inventario condicionalmente) en `backend/src/modules/ventas/service.py` (FR-025, FR-026, depende de T024)
- [ ] T071 [US5] Endpoint `POST /api/ventas/{id}/devoluciones` en `backend/src/modules/ventas/router.py` (depende de T031, T070)

**Checkpoint**: las 5 user stories funcionan de forma independiente.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [ ] T072 [P] Documentar variables de entorno reales necesarias (Stripe test, SendGrid, MinIO, Postgres) en `backend/.env.example` (ya con nombres, sin claves — completar si falta alguna de esta feature)
- [ ] T073 Ejecutar `checklists/security.md` — resolver el gap de doble-request en dos pasos separados (validación de sesión activa en frontend + backend, ver nota del checklist)
- [ ] T074 [P] Pruebas unitarias adicionales sobre RBAC (rol→módulo→tabla) aplicado a los endpoints de esta feature en `backend/tests/unit/test_rbac_ventas_inventario.py`
- [ ] T075 Revisar rendimiento: operaciones CRUD estándar responden en <1s en desarrollo (Principio X) — perfilar `confirmar_venta` (es la más costosa: descuento FIFO + PDF + posible llamada a Stripe)
- [ ] T076 [P] Ejecutar `/speckit-analyze` para verificar consistencia entre spec.md, plan.md y este tasks.md antes de pasar a `/speckit-implement`
- [ ] T077 Ejecutar manualmente los 6 escenarios de `quickstart.md` de punta a punta contra el entorno levantado con Docker Compose
- [ ] T078 [P] Documentación: actualizar `docs/diseno-ui/` si el flujo real de implementación difiere del diseño de referencia

---

## Dependencies & Execution Order

- **Setup (Fase 1)**: sin dependencias.
- **Foundational (Fase 2)**: depende de Setup — bloquea TODAS las user stories.
- **US1 (P1)**: depende solo de Foundational — es el MVP.
- **US2 (P2)**: depende de Foundational; comparte `Producto`/`Lote` con US1 pero es probable de forma independiente.
- **US3 (P3)**: depende de Foundational y de que existan `Lote`/`Orden de Compra` (US2 y su propia base) — usa el mismo modelo de `Producto` de US1/US2, no los reimplementa (DRY).
- **US4 (P4)**: depende solo de Foundational — puede desarrollarse en paralelo a US1-US3.
- **US5 (P5)**: depende de US1 (reutiliza `VentasService`).
- **Polish (Fase 8)**: depende de que las user stories deseadas para el MVP/entrega estén completas.

## Implementation Strategy

**MVP primero**: Fase 1 → Fase 2 → Fase 3 (US1) → validar con Escenarios 1-3 de quickstart.md → demo.
**Entrega incremental**: agregar US2 → US3 → US4 → US5, validando cada una con su escenario de quickstart.md antes de avanzar a la siguiente, sin romper las anteriores.
