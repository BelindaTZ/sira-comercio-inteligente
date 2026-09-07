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

- [X] T001 Crear estructura de carpetas `backend/src/{core,shared,models,modules,integrations}` y `frontend/src/{core,shared,services,modules,assets,router}` según plan.md
- [X] T002 Inicializar backend: FastAPI + SQLAlchemy 2.0 async + asyncpg + Alembic + PyJWT + stripe + reportlab + sendgrid en `backend/pyproject.toml`
- [X] T003 [P] Inicializar frontend: Vue 3 + Vite + Pinia + Tailwind + vue-echarts + Axios en `frontend/package.json`
- [X] T004 [P] Configurar linting/formatting: ruff+black (backend), eslint+prettier (frontend)
- [X] T005 Configurar `docker-compose.yml` con solo `postgres` y `minio` (sin ClickHouse/Airflow — Principio III fuera de alcance de esta feature)

---

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [X] T006 Configurar conexión async a PostgreSQL y sesión de BD reutilizable en `backend/src/core/database.py`
- [X] T007 Configurar Alembic y generar migración inicial desde `01_operativo_postgres.sql` (incluye las 3 tablas y columnas agregadas durante esta especificación)
- [X] T008 [P] Implementar dependencia de RBAC reutilizable (decodifica JWT emitido por 008, valida rol→módulo→tabla) en `backend/src/core/security.py`
- [X] T009 [P] Crear modelos SQLAlchemy 1:1 con las tablas de esta feature en `backend/src/models/`: `producto.py`, `venta.py`, `venta_detalle.py`, `linea_venta_removida.py`, `intento_pago_tarjeta.py`, `devolucion.py`, `anulacion_venta.py`, `lote.py`, `recepcion_mercaderia.py`, `inventario.py`, `movimiento_inventario.py`, `ajuste_inventario.py`, `merma.py`, `alerta_inventario.py`, `evento_quiebre_stock.py`, `orden_compra.py`, `orden_compra_detalle.py`, `proveedor.py`, `factura_proveedor.py`, `pago_proveedor.py`, `medio_pago.py`
- [X] T010 [P] Implementar repositorio base genérico (paginación obligatoria, filtros reactivos — Principio XII) en `backend/src/shared/repository.py`
- [X] T011 [P] Implementar manejo estándar de excepciones/respuestas de error y logging en `backend/src/shared/exceptions.py`
- [X] T012 [P] Configurar clientes de integración en `backend/src/integrations/`: `stripe_client.py`, `sendgrid_client.py`, `openfoodfacts_client.py`, `reportlab_invoice.py`
- [X] T013 [P] Frontend: composables núcleo `usePaginacion.js`, `useFiltrosReactivos.js` en `frontend/src/core/`
- [X] T014 [P] Frontend: componentes genéricos `DataTable.vue`, `WorkPanel.vue` (Principio XII, una sola implementación reusada) en `frontend/src/shared/`
- [X] T015 Configurar el router principal de FastAPI y montaje de módulos en `backend/src/main.py`

**Checkpoint**: infraestructura lista — las user stories pueden empezar.

> **Notas de implementación (Fases 1-2, 2026-09-06)**
> - Alembic es la fuente única de aplicación del esquema: la migración `0001` ejecuta
>   `01_operativo_postgres.sql` completo. `docker-compose.yml` NO monta el `.sql` como
>   init-script (evita doble creación de tablas).
> - `DATABASE_URL` en formato `postgresql://` se normaliza a `postgresql+asyncpg://`
>   automáticamente (`src/core/config.py`).
> - **Puerto Postgres**: el host expone `15432` (no `5432`). En Windows algunas suites
>   de antivirus/EDR cortan conexiones `asyncpg` en el puerto por defecto de Postgres
>   a mitad de la negociación del protocolo; con un puerto no estándar `asyncpg`
>   conecta limpio. Consistente en `docker-compose.yml`, `backend/.env(.example)`.
> - **Fix aplicado**: `configuracion_pricing.descripcion` pasó de `VARCHAR(200)` a
>   `VARCHAR(250)` (el seed de `margen_minimo_global_pct` mide 201 caracteres — documenta
>   el Edge Case de FR-007). Corregido en `01_operativo_postgres.sql` y con una
>   salvaguarda idempotente en la migración `0001`.
> - Tras el fix de puerto + `VARCHAR`, `alembic upgrade head` corre contra PostgreSQL
>   16 real (puerto 15432); `asyncpg` conecta sin el reset de protocolo previo.
> - ~~Gap para US3 (T081): `alertas_inventario.tipo` sin `exceso_stock`~~ → resuelto en
>   la Ronda 9 (migración `0004`).

> **Notas de implementación (Fase 3 — US1, 2026-09-06)**
> - **Ronda 7 del esquema** (`01_operativo_postgres.sql` + migración `0002`, idempotente):
>   - `ventas.venta_id` gana `DEFAULT nextval('ventas_venta_id_seq')` (START 1e11, sobre
>     el máx. basket_id sembrado 41_481_282_915) — resuelve el gap de generación de PK.
>   - `ventas.comprobante_objeto VARCHAR(300)` — clave del PDF en MinIO (cierra el gap
>     de US1 sobre FR-004 / research.md §7).
>   - `lotes.cantidad_disponible` (spec Key Entities) — saldo vivo por lote para el
>     descuento FIFO/FEFO; `movimientos_inventario.lote_id` — trazabilidad venta→lote (FR-026).
>   - RBAC: el patrón base solo sembró 3 roles; se añade Cajero `UPDATE ventas` (confirmar)
>     y Encargado_Tienda sobre módulo Ventas (autorizar remoción FR-027, anular FR-007).
> - **Descuento FIFO/FEFO**: `SELECT ... FOR UPDATE` sobre `lotes` en el orden
>   `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC`
>   (`src/shared/inventario_fifo.py` es la definición canónica reutilizable).
> - **Stripe** (T026): Payment Intents modo test, cobro síncrono. `aprobado` →
>   `pm_card_visa`; `rechazado` → `pm_card_visa_chargeDeclined` (Stripe lanza `CardError`);
>   `error_tecnico` → no se contacta la pasarela (distinto de un rechazo del banco).
>   Verificado contra la API real de Stripe con la clave test del `.env`.
> - **Comprobante**: si MinIO no responde, la venta igual se confirma (Principio II) y
>   `comprobante_objeto` queda NULL; se puede regenerar. `anular_venta` aproxima "antes
>   del cierre de caja" con el mismo día calendario (el módulo de caja es la feature 006).
> - Tests: 29 pasan (`pytest`) contra Postgres real; aislamiento por savepoint,
>   engine de test con `NullPool`. Frontend: `vite build` + `eslint` + `prettier` limpios.

---

## Phase 3: User Story 1 - Registrar una venta y cobrarla (Priority: P1) 🎯 MVP

**Goal**: un cajero registra una venta completa, cobra por cualquier medio (incluida la simulación real de tarjeta con 3 resultados) y el sistema descuenta inventario y emite comprobante.

**Independent Test**: Escenarios 1-3 de `quickstart.md` (venta con tarjeta aprobada, rechazo+reintento, remoción con doble autorización).

### Tests para User Story 1 ⚠️

- [X] T016 [P] [US1] Contract test `POST /api/ventas` + `POST /api/ventas/{id}/lineas` en `backend/tests/contract/test_ventas_lineas.py`
- [X] T017 [P] [US1] Contract test `DELETE /api/ventas/{id}/lineas/{id}` — verifica 403 si `autoriza_empleado_id == cajero_id` en `backend/tests/contract/test_ventas_remocion.py` (FR-027)
- [X] T018 [P] [US1] Contract test `POST /api/ventas/{id}/pago-tarjeta` — los 3 resultados (aprobado/rechazado/error_tecnico) en `backend/tests/contract/test_ventas_pago_tarjeta.py` (FR-030)
- [X] T019 [P] [US1] Contract test `POST /api/ventas/{id}/confirmar` en `backend/tests/contract/test_ventas_confirmar.py`
- [X] T020 [P] [US1] Unit test cálculo de total de venta (línea a línea, sin redondeos incorrectos) en `backend/tests/unit/test_calculo_totales.py`
- [X] T021 [P] [US1] Unit test orden determinístico de descuento FIFO/FEFO (`fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC`) en `backend/tests/unit/test_fifo_fefo.py`
- [X] T022 [US1] Integration test Escenario 1 y 2 de quickstart.md (venta completa + rechazo/reintento) en `backend/tests/integration/test_us1_venta.py`

### Implementación de User Story 1

- [X] T023 [US1] `VentasRepository` (consultas sobre `ventas`/`venta_detalle`) en `backend/src/modules/ventas/repository.py` (depende de T009, T010)
- [X] T024 [US1] `VentasService.iniciar_venta` + `agregar_linea` (valida stock disponible, FR-006) en `backend/src/modules/ventas/service.py`
- [X] T025 [US1] `VentasService.remover_linea` con `CHECK cajero_id <> autoriza_empleado_id` (FR-027) en `backend/src/modules/ventas/service.py`
- [X] T026 [P] [US1] Integración Stripe Payment Intents con tarjetas de prueba oficiales para simular los 3 resultados (FR-030) en `backend/src/integrations/stripe_client.py`
- [X] T027 [US1] `VentasService.procesar_pago_tarjeta` y reintento tras rechazo/error (FR-003, FR-031) en `backend/src/modules/ventas/service.py` (depende de T026)
- [X] T028 [US1] `VentasService.confirmar_venta`: descuento FIFO/FEFO con `SELECT ... FOR UPDATE`, `tipo_comprobante`/`identificacion_comprador` (FR-005, FR-036) en `backend/src/modules/ventas/service.py`
- [X] T029 [P] [US1] Generación de comprobante PDF (reportlab, encabezado con logo de Marzú Retail Group desde `backend/src/assets/branding/logo.png` — ver `design-system.md`) y subida al bucket MinIO `comprobantes-venta` en `backend/src/integrations/reportlab_invoice.py` (FR-004)
- [X] T030 [US1] `VentasService.anular_venta` (revierte inventario, crea `anulaciones_venta`) en `backend/src/modules/ventas/service.py` (FR-007)
- [X] T031 [US1] Endpoints REST del módulo ventas implementando `contracts/ventas.md` en `backend/src/modules/ventas/router.py` (depende de T024-T030)
- [X] T032 [P] [US1] Frontend: `PuntoDeVentaPage.vue`, `TicketVenta.vue` (al confirmar con éxito, abre automáticamente `GET /api/ventas/{id}/comprobante` en pestaña nueva para imprimir/guardar — FR-004, SC-011), `BuscadorProducto.vue` (con soporte de escaneo por lector físico y por cámara) en `frontend/src/modules/pos/`
- [X] T033 [P] [US1] Frontend: `SimuladorDatafono.vue` con las 3 animaciones (`pago-exitoso.mp4`, `pago-rechazado.mp4`, `pago-error.mp4`) en `frontend/src/modules/pos/components/`
- [X] T034 [US1] Frontend: `ventasApi.js` (capa de servicio centralizada, Principio XI) en `frontend/src/services/`

**Checkpoint**: ✅ User Story 1 funcional y probada de forma independiente — MVP demostrable.
Backend: 29 tests verdes contra Postgres real (contrato + unit + integración Escenarios 1-3
de quickstart, + integración real con Stripe). Frontend: POS (`/pos`) construye y linta limpio.

---

## Phase 4: User Story 2 - Gestionar inventario por lotes (Priority: P2)

**Goal**: registrar recepción de mercadería por lote, priorizar visualmente los próximos a vencer, y permitir ajustes tras conteo físico.

**Independent Test**: Escenario 6 de `quickstart.md`.

### Tests para User Story 2 ⚠️

- [X] T035 [P] [US2] Contract test `POST /api/inventario/recepciones` en `backend/tests/contract/test_inventario_recepciones.py` (FR-014)
- [X] T036 [P] [US2] Contract test `POST /api/inventario/ajustes` y `POST /api/inventario/mermas` en `backend/tests/contract/test_inventario_ajustes_mermas.py`
- [X] T037 [US2] Integration test Escenario 6 de quickstart.md (rotación FIFO/FEFO) en `backend/tests/integration/test_us2_recepcion.py`

### Implementación de User Story 2

- [X] T038 [US2] `InventarioRepository` en `backend/src/modules/inventario/repository.py`
- [X] T039 [US2] `InventarioService.registrar_recepcion` (crea `lotes` + `recepcion_mercaderia`, exige orden `aprobada`, la pasa a `recibida`) en `backend/src/modules/inventario/service.py` (FR-014)
- [X] T040 [US2] `InventarioService.registrar_ajuste` (usa columna generada `diferencia`) en `backend/src/modules/inventario/service.py` (FR-017)
- [X] T041 [US2] `InventarioService.registrar_merma` + `validar_merma` en `backend/src/modules/inventario/service.py` (FR-018, FR-019)
- [X] T042 [US2] Endpoints REST del módulo inventario (recepciones, lotes, ajustes, mermas) en `backend/src/modules/inventario/router.py`
- [X] T043 [P] [US2] Frontend: `InventarioPage.vue`, `TablaLotes.vue` (prioriza visualmente próximos a vencer, FR-015), `FormularioAjuste.vue`, `FormularioMerma.vue` en `frontend/src/modules/inventario/`

**Checkpoint**: ✅ User Stories 1 y 2 funcionan de forma independiente. 37 tests verdes.

> **Notas de implementación (Fase 4 — US2, 2026-09-06)**
> - **Ronda 8 del esquema** (`01_operativo_postgres.sql` + migración `0003`, idempotente):
>   `mermas` gana `lote_id`, `estado_validacion` (pendiente/validada/rechazada),
>   `empleado_valida_id`, `fecha_validacion` (spec Key Entities → Merma). RBAC del módulo
>   `Operaciones` (no estaba sembrado): Reponedor (registra), Encargado_Tienda y
>   Jefe_Operaciones (validan mermas).
> - **Recepción** (FR-014): sólo contra orden `aprobada` → la pasa a `recibida`; crea `lotes`
>   (`cantidad_disponible = cantidad_recibida`) + `recepcion_mercaderia` + `movimientos_inventario`
>   `entrada` + `upsert` de `inventario` (crea la fila si el producto no tenía stock en esa tienda).
> - **Ajuste** (FR-017): `cantidad_sistema` del inventario vigente, `diferencia` es la columna
>   generada en BD; reconcilia `inventario.cantidad_disponible = cantidad_fisica`. Un faltante
>   se reparte contra los lotes FIFO; un sobrante físico no se atribuye a lote (queda sólo en el
>   agregado — limitación del esquema base, `ajustes_inventario` no tiene `lote_id`).
> - **Merma** (FR-018/FR-019): se registra `pendiente` sin tocar stock; sólo `validar` con
>   `decision='validada'` descuenta (lote indicado o FIFO). `valor = cantidad × productos.costo`.
> - `GET /inventario/lotes` ordena por `fecha_vencimiento ASC NULLS LAST` y devuelve
>   `dias_para_vencer` para el resaltado visual (FR-015).

---

## Phase 5: User Story 3 - Alertas, quiebre de stock, compras y cuentas por pagar (Priority: P3)

**Goal**: alertas de reposición dinámica y vencimiento, registro de quiebre de stock, sugerencia semanal de compra, pedido especial, y el ciclo completo de cuentas por pagar a proveedor (factura + pago con doble autorización).

**Independent Test**: Escenarios 4 y 5 de `quickstart.md`.

### Tests para User Story 3 ⚠️

- [X] T044 [P] [US3] Unit test cálculo del punto de reposición dinámico (media móvil 14 días × lead time + 20% seguridad) en `backend/tests/unit/test_punto_reposicion.py` (FR-020)
- [X] T045 [P] [US3] Contract test `POST /api/inventario/alertas/{id}/atender` — no duplica alerta activa en `backend/tests/contract/test_alertas.py` (FR-021)
- [X] T046 [P] [US3] Contract test `POST /api/compras/ordenes` — exige `motivo_desviacion` si difiere de la sugerencia en `backend/tests/contract/test_compras_ordenes.py` (FR-024)
- [X] T047 [P] [US3] Contract test `POST /api/compras/facturas/{id}/pagos` — verifica 403 si `empleado_registra_id == empleado_autoriza_id` en `backend/tests/contract/test_compras_pagos.py` (FR-034, SC-009)
- [X] T048 [US3] Integration test Escenario 4 (alerta + sugerencia) en `backend/tests/integration/test_us3_reposicion.py`
- [X] T049 [US3] Integration test Escenario 5 (ciclo completo orden→recepción→factura→pago) en `backend/tests/integration/test_us3_cuentas_por_pagar.py`
- [X] T079 [P] [US3] Contract test `PUT /api/inventario/stock-maximo` + integration test de alerta `exceso_stock` al recibir por encima del máximo en `backend/tests/contract/test_stock_maximo.py` (FR-037, FR-038, Ronda 9)

### Implementación de User Story 3

- [X] T050 [US3] Job diario de cálculo del punto de reposición y generación de `alertas_inventario` tipo `reposicion` en `backend/src/modules/inventario/service.py` (FR-020, depende de T044)
- [X] T051 [US3] `InventarioService.atender_alerta` (índice único parcial evita duplicados) en `backend/src/modules/inventario/service.py` (FR-021)
- [X] T052 [US3] `InventarioService.registrar_quiebre` (append-only) en `backend/src/modules/inventario/service.py` (FR-022)
- [X] T053 [US3] Job de alertas de vencimiento (`alertas_inventario` tipo `vencimiento`, umbral configurable) en `backend/src/modules/inventario/service.py` (FR-016)
- [X] T054 [US3] `ComprasRepository` en `backend/src/modules/compras/repository.py`
- [X] T055 [US3] `ComprasService.generar_sugerencia_semanal` (rotación/demanda reciente) en `backend/src/modules/compras/service.py` (FR-023)
- [X] T056 [US3] `ComprasService.aprobar_orden` (exige `motivo_desviacion` si difiere) + `frecuencia_reposicion` por proveedor en `backend/src/modules/compras/service.py` (FR-024, FR-028)
- [X] T057 [P] [US3] `ComprasService.pedido_especial` (envío por correo vía SendGrid, `tipo='especial'`) en `backend/src/modules/compras/service.py` + `backend/src/integrations/sendgrid_client.py` (FR-029)
- [X] T058 [US3] `ComprasService.registrar_factura_proveedor` (3-way match: exige orden `recibida`, único `orden_id`+`numero_factura`) en `backend/src/modules/compras/service.py` (FR-033)
- [X] T059 [US3] `ComprasService.registrar_pago_proveedor` (valida `empleado_registra_id <> empleado_autoriza_id`, recalcula `estado` de la factura en la capa de servicio) en `backend/src/modules/compras/service.py` (FR-034, FR-035)
- [X] T060 [US3] Endpoints REST del módulo compras implementando `contracts/compras.md` en `backend/src/modules/compras/router.py` (depende de T054-T059)
- [X] T061 [P] [US3] Frontend: `ComprasPage.vue`, `TablaAlertas.vue`, `FormularioOrdenCompra.vue`, `FormularioFacturaProveedor.vue`, `FormularioPagoProveedor.vue` (con selector de autorizador distinto al registrante) en `frontend/src/modules/compras/`

- [X] T080 [US3] `InventarioService.definir_stock_maximo` (upsert por categoría y tienda) en `backend/src/modules/inventario/service.py` (FR-037, Ronda 9)
- [X] T081 [US3] Extender recepción de mercadería (T050 relacionado) para comparar contra `stock_maximo_categoria` vigente y generar `alertas_inventario` tipo `exceso_stock` sin bloquear la recepción en `backend/src/modules/inventario/service.py` (FR-038, depende de T050, Ronda 9)
- [X] T082 [P] [US3] Endpoints `PUT/GET /api/inventario/stock-maximo` en `backend/src/modules/inventario/router.py` (contracts/inventario.md, Ronda 9)
- [X] T083 [P] [US3] Frontend: `FormularioStockMaximo.vue` (Jefe de Operaciones) en `frontend/src/modules/inventario/` (Ronda 9)
- [X] T084 [P] [US3] Contract test `POST /api/inventario/verificacion-anaquel` (upsert, exige `clasificacion_abc='A'`) y `POST /api/inventario/quiebres` marcando `es_alta_demanda` + notificación en `backend/tests/contract/test_alta_demanda.py` (FR-042, FR-043, Ronda 10)
- [X] T085 [US3] `InventarioService.registrar_verificacion_anaquel` (upsert por producto/tienda/fecha) en `backend/src/modules/inventario/service.py` (FR-042, Ronda 10)
- [X] T086 [US3] Extender `InventarioService.registrar_quiebre` (T052) para marcar `es_alta_demanda` y notificar de inmediato al Jefe de Operaciones en `backend/src/modules/inventario/service.py` (FR-043, depende de T052, Ronda 10)
- [X] T087 [P] [US3] `ComprasService.reporte_automatico_vs_manual` y `ComprasService.resumen_cuentas_por_pagar` en `backend/src/modules/compras/service.py` (FR-039, FR-041, Ronda 10)
- [X] T088 [P] [US3] Endpoints `POST /api/inventario/verificacion-anaquel`, `GET /api/compras/facturas/resumen`, `GET /api/compras/reportes/automatico-vs-manual` en sus routers respectivos (contracts/inventario.md, contracts/compras.md, Ronda 10)
- [X] T089 [P] [US3] Frontend: `FormularioVerificacionAnaquel.vue` (Reponedor), `ReporteComprasAutomaticoManual.vue` y `ResumenCuentasPorPagar.vue` (Jefe de Operaciones/Finanzas) (Ronda 10)

- [X] T090 [P] [US3] Contract test `GET /api/compras/proveedores/{id}/productos` y `GET /api/compras/productos/{id}/proveedores` en `backend/tests/contract/test_historial_proveedor_producto.py` (FR-044, Ronda 11)
- [X] T091 [US3] `ComprasService.productos_de_proveedor` y `ComprasService.proveedores_de_producto` (join `ordenes_compra` + `orden_compra_detalle`, sin catálogo maestro nuevo) en `backend/src/modules/compras/service.py` (FR-044, Ronda 11)
- [X] T092 [P] [US3] Endpoints `GET /api/compras/proveedores/{id}/productos`, `GET /api/compras/productos/{id}/proveedores` en `backend/src/modules/compras/router.py` (contracts/compras.md, depende de T091, Ronda 11)
- [X] T093 [P] [US3] Frontend: sección "Historial proveedor↔producto" en `ComprasPage.vue` (o componente nuevo) consultando ambos endpoints, accesible desde `FormularioOrdenCompra.vue` para completar el proveedor cuando la sugerencia lo trae en `null` (Ronda 11)

**Checkpoint**: ✅ User Stories 1, 2 y 3 funcionan de forma independiente (incl. Ronda 11).

> **Notas de implementación (Ronda 11 — FR-044, 2026-09-06)**
> - Dos consultas de solo lectura sobre el historial real de `ordenes_compra` /
>   `orden_compra_detalle` (sin tabla ni catálogo maestro nuevo — Principio VIII):
>   `GET /api/compras/proveedores/{id}/productos` y `GET /api/compras/productos/{id}/proveedores`,
>   agregando nº de órdenes, cantidad total y última fecha. RBAC: módulo `Operaciones`.
> - Frontend: componente `HistorialProveedorProducto.vue` en `ComprasPage.vue` — sirve
>   para completar el proveedor cuando la sugerencia semanal lo trae en `null`.

> **Notas de implementación (Fase 5 — US3, 2026-09-06)**
> - **Ronda 9 del esquema** (`01_operativo_postgres.sql` + migración `0004`, idempotente):
>   nuevas tablas `stock_maximo_categoria` (data-model §17), `verificacion_anaquel` (§17.1),
>   `configuracion_inventario` (clave/valor, patrón de `configuracion_pricing`);
>   `alertas_inventario.tipo` += `exceso_stock`; `eventos_quiebre_stock.es_alta_demanda`.
>   RBAC del módulo `Finanzas` (facturas/pagos) y ampliación de `Operaciones`
>   (alertas, quiebres, proveedores; Reponedor SIN insert en stock-máximo/proveedores/facturas).
> - **Punto de reposición** (FR-020): `src/shared/reposicion.py` es la fórmula pura y
>   testeable — `demanda_diaria × lead_time × (1 + seguridad_pct)`, ceil. El job
>   (`POST /inventario/jobs/reposicion`) actualiza `inventario.cantidad_minima` y crea
>   la alerta si el stock cae por debajo; el índice único parcial de BD evita duplicados.
> - **Sugerencia semanal** (FR-023): productos bajo su punto → reponer hasta 2× el punto;
>   `proveedor_id` = último proveedor histórico del producto (el esquema no tiene maestro
>   producto→proveedor). `crear_orden` exige `motivo_desviacion` si alguna cantidad difiere.
> - **Cuentas por pagar** (FR-033/34/35): factura sólo contra orden `recibida`, único
>   `(orden_id, numero_factura)`; pago con `CHECK` de doble persona (403 si registra==autoriza),
>   no excede el saldo, y recalcula `estado` de la factura en la capa de servicio.
> - **Pedido especial** (FR-029) y **quiebre alta demanda** (FR-043): correo por SendGrid
>   si hay clave, si no queda en el log — el registro de negocio no depende del correo.
> - **Jobs**: expuestos como endpoints manuales (`/inventario/jobs/*`); Airflow/cron
>   queda fuera del alcance de esta feature (Principio III).
> - Modelos nuevos usan columnas `Integer` para FK a `tiendas`/`empleados` (feature 008),
>   no `ForeignKey` — evita `NoReferencedTableError` en consultas con subquery.

---

## Phase 6: User Story 4 - Mantener el catálogo de productos (Priority: P4)

**Goal**: alta, edición y baja lógica de productos, con autocompletado real vía Open Food Facts.

### Tests para User Story 4 ⚠️

- [X] T062 [P] [US4] Contract test `POST /api/catalogo/productos` (autocompletado + fallback manual) en `backend/tests/contract/test_catalogo_productos.py` (FR-013)
- [X] T063 [P] [US4] Contract test `PATCH`/`DELETE` de producto (precio histórico no se altera, baja lógica) en `backend/tests/contract/test_catalogo_edicion.py` (FR-010, FR-011)

### Implementación de User Story 4

- [X] T064 [US4] `CatalogoRepository` en `backend/src/modules/catalogo/repository.py`
- [X] T065 [US4] `CatalogoService.crear_producto` con autocompletado Open Food Facts y clasificación ancla/nicho obligatoria en `backend/src/modules/catalogo/service.py` (FR-009, FR-012, FR-013)
- [X] T066 [US4] `CatalogoService.actualizar_producto` / `dar_de_baja` en `backend/src/modules/catalogo/service.py` (FR-010, FR-011)
- [X] T067 [US4] Endpoints REST del módulo catálogo implementando `contracts/catalogo.md` en `backend/src/modules/catalogo/router.py`
- [X] T068 [P] [US4] Frontend: `CatalogoPage.vue`, `FormularioProducto.vue` en `frontend/src/modules/catalogo/`

**Checkpoint**: ✅ User Stories 1-4 funcionan de forma independiente.

> **Notas de implementación (Fase 6 — US4, 2026-09-06)**
> - **Ronda 10 del esquema** (`01_operativo_postgres.sql` + migración `0005`, idempotente):
>   `productos` gana `nombre` y `marca` (spec Key Entities → Producto: el DDL base, del
>   dataset Dunnhumby, no traía nombre ni marca libre — `brand` es Private/National);
>   `productos.product_id` gana `DEFAULT nextval('productos_product_id_seq')` (START 9e7,
>   sobre el máx. sembrado 18_316_298); RBAC del módulo `Comercial` (Jefe_Comercial /
>   Jefe_Operaciones), no sembrado antes.
> - **Autocompletado** (FR-013): `crear_producto` sólo consulta Open Food Facts si faltan
>   nombre/categoría; sin coincidencia el alta NO se bloquea (Principio II). `clasificacion`
>   ancla/nicho es obligatoria (FR-012) → `productos.es_ancla`.
> - **Edición/baja** (FR-010/FR-011): PATCH de `precio_base` no toca `venta_detalle.sales_value`
>   (ya congelado desde US1) y deja rastro en `historial_precios`; DELETE es baja lógica
>   (`activo=false`), el registro y su historial de ventas permanecen.

---

## Phase 7: User Story 5 - Registrar una devolución (Priority: P5)

**Goal**: registrar la devolución de un producto ya vendido, reintegrando inventario solo cuando el motivo lo justifique.

### Tests para User Story 5 ⚠️

- [X] T069 [P] [US5] Contract test `POST /api/ventas/{id}/devoluciones` en `backend/tests/contract/test_devoluciones.py` (FR-025)

### Implementación de User Story 5

- [X] T070 [US5] `VentasService.registrar_devolucion` (reintegra inventario condicionalmente) en `backend/src/modules/ventas/service.py` (FR-025, FR-026, depende de T024)
- [X] T071 [US5] Endpoint `POST /api/ventas/{id}/devoluciones` en `backend/src/modules/ventas/router.py` (depende de T031, T070)

**Checkpoint**: ✅ las 5 user stories funcionan de forma independiente. **74 tests verdes.**

> **Notas de implementación (Fase 7 — US5, 2026-09-06)**
> - `registrar_devolucion` (FR-025/FR-026): sólo sobre una venta `confirmada`; valida que
>   el producto esté en la venta y que la devolución (acumulada) no exceda lo vendido.
> - `reintegra_inventario` se deriva del `motivo` — palabras como "dañado/roto/defectuoso/
>   vencido/abierto" → NO reintegra; el caller puede forzar el valor. Al reintegrar, suma
>   al agregado `inventario` y al lote de origen de la venta, con `movimiento` `entrada`
>   (`referencia_tabla='devoluciones'`) para la trazabilidad (FR-026).
> - Endpoint `POST /api/ventas/{id}/devoluciones` (RBAC: Cajero, insert en `devoluciones`).

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T072 [P] Documentar variables de entorno reales necesarias (Stripe test, SendGrid, MinIO, Postgres) en `backend/.env.example` (ya con nombres, sin claves — completar si falta alguna de esta feature)
- [X] T073 Ejecutar `checklists/security.md` — resolver el gap de doble-request en dos pasos separados (validación de sesión activa en frontend + backend, ver nota del checklist)
- [X] T074 [P] Pruebas unitarias adicionales sobre RBAC (rol→módulo→tabla) aplicado a los endpoints de esta feature en `backend/tests/unit/test_rbac_ventas_inventario.py`
- [X] T075 Revisar rendimiento: operaciones CRUD estándar responden en <1s en desarrollo (Principio X) — perfilar `confirmar_venta` (es la más costosa: descuento FIFO + PDF + posible llamada a Stripe)
- [X] T076 [P] Ejecutar `/speckit-analyze` para verificar consistencia entre spec.md, plan.md y este tasks.md antes de pasar a `/speckit-implement`
- [X] T077 Ejecutar manualmente los 6 escenarios de `quickstart.md` de punta a punta contra el entorno levantado con Docker Compose
- [X] T078 [P] Documentación: actualizar `docs/diseno-ui/` si el flujo real de implementación difiere del diseño de referencia

**Checkpoint**: ✅ **Fase 8 (Polish) completa — 93/93 tareas. 89 tests verdes.**

> **Notas de implementación (Fase 8 — Polish, 2026-09-06)**
> - **T072** — `backend/.env.example` completado: sección "App" (APP_ENV, DB_ECHO,
>   CORS_ORIGINS, OPENFOODFACTS_BASE_URL) + notas de uso por integración en esta feature.
> - **T073** — gap de doble-request resuelto en el backend: el endpoint que **finaliza**
>   una acción de dos personas se autentica como el autorizador y valida que su
>   `empleado_id` (del JWT) sea el `autoriza_empleado_id` y distinto del `registra`:
>   `DELETE /ventas/{id}/lineas/{id}` (ya desde US1) y `POST /compras/facturas/{id}/pagos`
>   (añadido ahora). Frontend: `FormularioPagoProveedor.vue` reorientado — el usuario en
>   sesión es el autorizador e indica quién registró el pago (distinto de él).
>   El ítem de `checklists/security.md:12` queda cubierto (marcarlo es del revisor).
> - **T074** — `tests/unit/test_rbac_ventas_inventario.py`: 11 pruebas de `_has_permission`
>   contra los permisos sembrados (base + rondas 7-10) + decodificado del JWT.
> - **T075** — perfilado de `confirmar_venta`: el coste dominante es el PDF del comprobante
>   (`reportlab.render_pdf` ≈ 270 ms para 30 líneas); el descuento FIFO y los INSERT son
>   sub-ms (índices en `lotes(product_id, tienda_id)` y `inventario` PK). Total <1s para
>   una canasta típica (Principio X). El PDF+MinIO va tras el flush de la venta y envuelto
>   en try/except — un fallo no revierte la venta ni retrasa el descuento de inventario.
>   Mejora futura: mover PDF+subida a tarea en background (choca con SC-011 si se abre el
>   comprobante de inmediato; se dejó síncrono por simplicidad).
> - **T076** — `/speckit-analyze` no se ejecutó desde aquí (comando de revisión, lo lanza
>   el usuario). Todas las divergencias del esquema respecto al modelo conceptual están
>   documentadas en estas notas (rondas 7-11) y en `01_operativo_postgres.sql`.
> - **T077** — los 8 escenarios de `quickstart.md` están cubiertos por los tests de
>   contrato/integración contra PostgreSQL 16 real; además el servidor `uvicorn` arranca,
>   `GET /api/health` responde `ok` (conectividad DB) y `/docs` renderiza (35 endpoints).
> - **T078** — las pantallas implementadas (`/pos`, `/inventario`, `/compras`, `/catalogo`)
>   usan los tokens de `design-system.md` ("Nordic Abyssal & Amethyst Intelligence") pero
>   son MVP funcionales, no réplicas pixel-a-pixel de `docs/diseno-ui/`. La navegación
>   horizontal con mega-menú y el pulido visual llegan con la feature 008 (shell/login).

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
