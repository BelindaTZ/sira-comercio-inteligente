# Tasks: Precios Dinámicos, Márgenes y Comparación de Competencia (003-precios-margenes)

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: incluidos — Principio X exige cobertura obligatoria en: cálculo de margen real por línea, cálculo del margen objetivo efectivo por ancla/nicho, y el control de doble autorización del descuento manual (`empleado_aplica_id <> empleado_autoriza_id`, más el rol de quien autoriza). No se exige 100% del resto de la feature.
**Organización**: por módulo de negocio. La mayor parte vive en `modules/pricing/` (nuevo, ya reservado desde el `plan.md` de 001); el descuento manual (FR-009/FR-010) extiende `modules/ventas/` en vez de vivir en `pricing/` (decisión explícita de `plan.md`, Project Structure — es una acción sobre una venta en curso, Principio VIII/DRY). La infraestructura transversal de 001/002 (FastAPI, SQLAlchemy async, Alembic, RBAC, `APScheduler`/`scheduler.py`, `DataTable.vue`/`WorkPanel.vue`, composables núcleo, cliente de Open Food Facts) ya existe y se reutiliza sin repetirla aquí (DRY).

## Format: `[ID] [P?] [Story] Descripción`
- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencias)
- **[Story]**: US1-US5 según prioridad de `spec.md`

---

## Phase 1: Setup

- [ ] T001 Crear el módulo `backend/src/modules/pricing/` (`router.py`, `service.py`, `repository.py`, `schemas.py`) — mismo patrón por capas de `modules/clientes/` y `modules/catalogo/` (Principio XI); el resto del stack transversal ya está inicializado desde 001/002, no se repite aquí
- [ ] T002 [P] Migración Alembic con las extensiones DDL ya aplicadas en `01_operativo_postgres.sql` para esta feature: `margenes_objetivo.factor_sensibilidad`, tabla `propuesta_ajuste_precio`, extensión de `venta_detalle` (`motivo_descuento`, `empleado_aplica_id`, `empleado_autoriza_id`, `margen_real`, `margen_bajo_minimo` + `CHECK` de doble autorización), tabla `revision_margen_bajo`, tabla `competidores`, tabla `precio_competencia`, tabla `configuracion_pricing` (con sus 3 filas iniciales)
- [ ] T003 [P] Crear el esqueleto frontend `frontend/src/modules/pricing/` (`pages/`, `components/`) y `frontend/src/services/pricingApi.js` (capa de servicio centralizada, Principio XI); agregar el nuevo endpoint de descuento a `frontend/src/services/ventasApi.js` (ya existente)

---

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [ ] T004 [P] Modelos SQLAlchemy en `backend/src/models/`: extender `margen_objetivo.py` (`factor_sensibilidad`), crear `propuesta_ajuste_precio.py`, extender `venta_detalle.py` (campos de descuento/margen), crear `revision_margen_bajo.py`, crear `competidor.py`, crear `precio_competencia.py`, crear `configuracion_pricing.py`
- [ ] T005 Registrar los 2 jobs semanales nuevos de esta feature (propuestas de ajuste — US2; alertas de competencia — US5) en el `APScheduler` ya configurado en `backend/src/jobs/scheduler.py` desde 002 — un único mecanismo de jobs periódicos en todo el backend, sin crear uno nuevo (`research.md` §6, Principio VIII)
- [ ] T006 [P] Extender el endpoint interno solo-desarrollo de "forzar corrida" (ya creado en 002 para sus jobs) para incluir los 2 jobs nuevos de esta feature — usado por `quickstart.md`, no expuesto en producción
- [ ] T007 Montar el router del módulo `pricing` en `backend/src/main.py`; agregar el nuevo endpoint de descuento al router ya existente de `modules/ventas/` (no se recrea el módulo, se extiende)
- [ ] T008 [P] Seed/verificación de `rol_modulo`/`rol_modulo_tabla` para que el módulo `Comercial` cubra las tablas nuevas de esta feature, y que `Cajero`/`Encargado_Tienda` tengan acceso al módulo `Ventas` sobre la extensión de `venta_detalle` (RBAC, Principio IV)

**Checkpoint**: infraestructura lista — las user stories pueden empezar.

---

## Phase 3: User Story 1 - Definir margen objetivo y calcular el margen real de cada venta (Priority: P1) 🎯 MVP

**Goal**: Jefe_Comercial define el margen objetivo (%) de cada categoría; el sistema calcula el margen real de toda venta confirmada con el precio ya descontado (nunca el de catálogo) y lo deja consultable por categoría y rango de fechas.

**Independent Test**: definir el margen objetivo de una categoría y verificar que el margen real de una venta ya confirmada en esa categoría se calcula con el precio post-descuento y queda disponible en `GET /api/pricing/reportes/margen` (Acceptance Scenarios de US1 en `spec.md`; Escenario 7 de `quickstart.md` cubre la consulta agregada).

### Tests para User Story 1 ⚠️

- [ ] T009 [P] [US1] Unit test del cálculo de margen real por línea: usa el precio ya descontado (no el de catálogo) y el costo vigente al momento de la venta, para TODA línea confirmada (no solo las que tuvieron descuento manual) en `backend/tests/unit/test_calculo_margen_real.py` (FR-002, Principio X)
- [ ] T010 [P] [US1] Contract test `GET`/`PATCH /api/pricing/margenes` en `backend/tests/contract/test_margenes_objetivo.py`
- [ ] T011 [US1] Integration test: margen objetivo definido + margen real de una venta confirmada calculado con precio post-descuento y consultable por categoría en `backend/tests/integration/test_us1_margen_real.py`

### Implementación de User Story 1

- [ ] T012 [US1] `PricingRepository` (CRUD de `margenes_objetivo`; agregación de margen real por categoría/rango de fechas contra `venta_detalle`) en `backend/src/modules/pricing/repository.py` (depende de T004)
- [ ] T013 [US1] `PricingService.definir_margen_objetivo` (FR-001) en `backend/src/modules/pricing/service.py`
- [ ] T014 [US1] Cálculo y persistencia de `venta_detalle.margen_real` al confirmar una venta — extiende `VentasService.confirmar` ya existente de 001 (no se reescribe la ruta, Principio VI) para TODA línea, con el precio ya descontado y el costo vigente (FR-002) en `backend/src/modules/ventas/service.py`
- [ ] T015 [US1] `PricingService.reporte_margen` — margen real acumulado vs. margen objetivo vigente por categoría y rango de fechas (FR-003) en `backend/src/modules/pricing/service.py`
- [ ] T016 [P] [US1] Endpoints `GET`/`PATCH /api/pricing/margenes` y `GET /api/pricing/reportes/margen` según `contracts/pricing.md` en `backend/src/modules/pricing/router.py` (depende de T013, T015)
- [ ] T017 [P] [US1] Frontend: `MargenesPage.vue` (definir/editar margen objetivo por categoría) en `frontend/src/modules/pricing/pages/`

**Checkpoint**: US1 entregable de forma independiente — margen objetivo y margen real funcionando de punta a punta.

---

## Phase 4: User Story 2 - Motor de pricing dinámico con política diferenciada ancla/nicho (Priority: P2)

**Goal**: regla de ajuste por categoría (factor de sensibilidad), propuestas de ajuste generadas por el sistema y aprobadas por Jefe_Comercial antes de publicarse, margen objetivo efectivo siempre distinto entre ancla y nicho de una misma categoría.

**Independent Test**: Escenario 1 (margen objetivo efectivo ancla/nicho) y Escenario 2 (propuesta nunca se publica sin aprobación) de `quickstart.md`.

### Tests para User Story 2 ⚠️

- [ ] T018 [P] [US2] Unit test del margen objetivo efectivo: un producto ancla y uno nicho de la misma categoría nunca reciben el mismo valor; el piso global de respaldo nunca se cruza en `backend/tests/unit/test_margen_efectivo_ancla_nicho.py` (FR-007, Principio X)
- [ ] T019 [P] [US2] Unit test de la fórmula de propuesta de ajuste: respeta la tolerancia mínima configurable y nunca propone bajo `costo × 1.01` en `backend/tests/unit/test_formula_ajuste_precio.py` (FR-004, FR-005)
- [ ] T020 [P] [US2] Contract test `POST /api/pricing/propuestas/{id}/aprobar` (actualiza `precio_base` + `historial_precios`) y `.../rechazar` (no cambia nada) en `backend/tests/contract/test_propuestas_ajuste.py` (FR-006, SC-002)
- [ ] T021 [US2] Integration test Escenarios 1 y 2 de `quickstart.md` en `backend/tests/integration/test_us2_pricing_dinamico.py`

### Implementación de User Story 2

- [ ] T022 [US2] `PricingService.margen_objetivo_efectivo(product_id)` — aplica el modificador fijo ancla/nicho (`-5pp`/`+3pp`) sobre el margen objetivo de la categoría, con piso en `configuracion_pricing.margen_minimo_global_pct`, sin persistir (`research.md` §3, `data-model.md` entidad 2) en `backend/src/modules/pricing/service.py` — función compartida, la usarán también US3 y US5
- [ ] T023 [US2] Job semanal `generar_propuestas_ajuste_job.py` — recorre categorías con `factor_sensibilidad` no nulo, calcula la desviación de margen y genera `propuesta_ajuste_precio` según la fórmula de `research.md` §2 (FR-005) en `backend/src/jobs/`
- [ ] T024 [US2] `PricingService.aprobar_propuesta` — transacción de `research.md` §1: cierra vigencia anterior en `historial_precios`, inserta la nueva, actualiza `productos.precio_base` (FR-006) en `backend/src/modules/pricing/service.py`
- [ ] T025 [US2] `PricingService.rechazar_propuesta` (FR-005) en `backend/src/modules/pricing/service.py`
- [ ] T026 [P] [US2] Endpoints de propuestas (`GET`, `GET /{id}`, `POST .../aprobar`, `POST .../rechazar`) y `GET /api/pricing/productos/{id}/margen-efectivo` según `contracts/pricing.md` en `backend/src/modules/pricing/router.py` (depende de T022, T024, T025)
- [ ] T027 [US2] Extender el schema Pydantic de `PATCH /api/catalogo/productos/{id}` (`modules/catalogo/schemas.py`, ya existente de 001) para aceptar `clasificacion?` opcional (FR-008) — reutiliza el endpoint genérico, no se crea uno nuevo (Principio VIII, DRY)
- [ ] T028 [P] [US2] Frontend: `PropuestasPrecioPage.vue`, `FormularioReglaAjuste.vue` (factor de sensibilidad por categoría) en `frontend/src/modules/pricing/`

**Checkpoint**: US2 entregable de forma independiente sobre US1.

---

## Phase 5: User Story 3 - Descuento manual en punto de venta con autorización obligatoria y detección de margen bajo mínimo (Priority: P3)

**Goal**: ningún descuento manual se aplica sin autorización de un Encargado_Tienda (o superior) distinto del cajero, sin excepción por monto, con motivo obligatorio; si el margen real resultante cae bajo el margen objetivo efectivo, la línea se marca para revisión, sin bloquear la venta.

**Independent Test**: Escenario 3 (autorización obligatoria, sin excepción por monto), Escenario 4 (marca de margen bajo sin bloquear la venta) y Escenario 5 (cierre del ciclo de revisión) de `quickstart.md`.

### Tests para User Story 3 ⚠️

- [ ] T029 [P] [US3] Unit test del control de doble autorización: `empleado_aplica_id <> empleado_autoriza_id` (mismo patrón que FR-027/FR-034 de 001) y el rol de `empleado_autoriza_id` contra la lista fija `{Encargado_Tienda, Jefe_Comercial, Jefe_Operaciones, Jefe_Finanzas, Gerente_General}` en `backend/tests/unit/test_autorizacion_descuento.py` (FR-009, `research.md` §4, Principio X)
- [ ] T030 [P] [US3] Contract test `POST /api/ventas/{id}/lineas/{id}/descuento` — 403 por mismo empleado, 403 por rol no habilitado, 200 sin importar el monto en `backend/tests/contract/test_descuento_manual.py`
- [ ] T031 [P] [US3] Contract test `GET /api/pricing/margen-bajo` (con y sin `tienda_id`) y `POST .../revision` en `backend/tests/contract/test_margen_bajo.py`
- [ ] T032 [US3] Integration test Escenarios 3, 4 y 5 de `quickstart.md` en `backend/tests/integration/test_us3_descuento_manual.py`

### Implementación de User Story 3

- [ ] T033 [US3] `VentasService.aplicar_descuento_manual` — valida empleados distintos, rol de `empleado_autoriza_id` (lista fija) y motivo obligatorio; aplica el descuento sobre `venta_detalle.retail_disc` (FR-009) en `backend/src/modules/ventas/service.py`
- [ ] T034 [US3] Recalcular `margen_real` con el precio ya descontado y marcar `margen_bajo_minimo = true` si queda bajo `PricingService.margen_objetivo_efectivo` (T022) del producto, sin bloquear la venta (FR-010) en `backend/src/modules/ventas/service.py` (depende de T022)
- [ ] T035 [US3] Endpoint `POST /api/ventas/{id}/lineas/{id}/descuento` según `contracts/pricing.md` en `backend/src/modules/ventas/router.py` (depende de T033, T034)
- [ ] T036 [US3] `PricingService.listar_margen_bajo` (filtro `tienda_id`/`revisado`) y `PricingService.registrar_revision` (crea o actualiza `revision_margen_bajo` vía `UPDATE`, nunca fila nueva) (FR-011, FR-012) en `backend/src/modules/pricing/service.py`
- [ ] T037 [P] [US3] Endpoints `GET /api/pricing/margen-bajo` y `POST .../revision` en `backend/src/modules/pricing/router.py` (depende de T036)
- [ ] T038 [P] [US3] Frontend: extender `TicketVenta.vue` de 001 con botón "Aplicar descuento" + modal de autorización que re-autentica (PIN/contraseña) al Encargado_Tienda — nunca un campo de texto libre con el ID (`research.md` §4) en `frontend/src/modules/pos/`
- [ ] T039 [P] [US3] Frontend: `TablaMargenBajo.vue` (listado diario de una tienda y consolidado semanal de Jefe_Comercial, con formulario de acción correctiva) en `frontend/src/modules/pricing/components/`

**Checkpoint**: US3 entregable de forma independiente sobre US1 y US2 (usa `margen_objetivo_efectivo` de T022).

---

## Phase 6: User Story 4 - Reporte mensual de margen real vs. objetivo a Dirección General (Priority: P4)

**Goal**: Jefe_Comercial genera mensualmente el reporte de margen real vs. objetivo por categoría, listo para presentar a Dirección General.

**Independent Test**: Escenario 7 de `quickstart.md`.

### Tests para User Story 4 ⚠️

- [ ] T040 [US4] Integration test Escenario 7 de `quickstart.md`, invocando `GET /api/pricing/reportes/margen` (T015/T016 de US1) con el rango de un mes completo en `backend/tests/integration/test_us4_reporte_mensual.py` (FR-013)

### Implementación de User Story 4

- [ ] T041 [US4] Frontend: `ReporteMargenPage.vue` (selector de mes, tabla por categoría) en `frontend/src/modules/pricing/pages/` — reutiliza íntegramente `GET /api/pricing/reportes/margen` de US1 con el rango del mes; no se crea un endpoint backend nuevo (Principio VIII, DRY, `contracts/pricing.md`)

**Checkpoint**: US4 entregable de forma independiente sobre US1 (sin depender de US2/US3).

---

## Phase 7: User Story 5 - Comparar precio propio vs. precio de referencia de la competencia (Priority: P5)

**Goal**: captura manual de precio de competencia por competidor nombrado (con relevancia geográfica y flag promocional), automática vía Open Prices para productos en vivo con barcode real, y semilla sintética de demostración; alertas semanales de desviación sobre el umbral configurable.

**Independent Test**: Escenario 6 de `quickstart.md` (las tres fuentes: manual, Open Prices, sintética).

### Tests para User Story 5 ⚠️

- [ ] T042 [P] [US5] Unit test de la desviación de competencia: siempre usa la fila con `fecha_captura` más reciente por producto sin importar `fuente_captura`; un producto sin ninguna fila no genera alerta en `backend/tests/unit/test_desviacion_competencia.py` (FR-015, FR-016, Edge Case de `spec.md`)
- [ ] T043 [P] [US5] Contract test `POST`/`GET /api/pricing/competidores` y `POST`/`GET .../precio-competencia` (fuerza `fuente_captura = "manual"` desde el servidor, nunca del body) en `backend/tests/contract/test_competencia.py` (FR-014)
- [ ] T044 [P] [US5] Contract test `GET /api/pricing/competencia/alertas` en `backend/tests/contract/test_alertas_competencia.py`
- [ ] T045 [US5] Integration test Escenario 6 de `quickstart.md` (manual sobre sembrado, Open Prices sobre producto en vivo con y sin dato disponible, ausencia total no genera alerta) en `backend/tests/integration/test_us5_competencia.py`

### Implementación de User Story 5

- [ ] T046 [US5] `PricingService.registrar_competidor` y `.registrar_precio_competencia_manual` (siempre `fuente_captura = "manual"`, `registrado_por` = usuario autenticado) (FR-014) en `backend/src/modules/pricing/service.py`
- [ ] T047 [US5] Cliente `backend/src/integrations/open_prices_client.py` — consulta `prices.openfoodfacts.org` por código de barras real, sin API key para lectura, best-effort (mismo patrón que el cliente de Open Food Facts ya usado en 001, `research.md` §5)
- [ ] T048 [US5] Extender `POST /api/catalogo/productos` de 001 (alta en vivo) para, cuando el barcode es real, además intentar una primera captura de Open Prices al momento del alta (`fuente_captura = "open_prices"`, `competidor_id = null`) — no bloquea el alta si falla o no hay dato (FR-014) en `backend/src/modules/catalogo/service.py` (depende de T047)
- [ ] T049 [US5] Job semanal `calcular_alertas_competencia_job.py` — refresca Open Prices (best-effort) para productos en vivo con barcode real, recalcula la desviación de todos los productos con al menos una fila en `precio_competencia` y genera las alertas (FR-015, FR-016) en `backend/src/jobs/` (depende de T047)
- [ ] T050 [US5] Semilla sintética inicial de `precio_competencia` para productos con `clasificacion_abc = 'A'` (`fuente_captura = "sintetico"`, `research.md` §5) — script de carga en `backend/scripts/` o incorporado a la migración de T002
- [ ] T051 [P] [US5] Endpoints de competidores, precio-competencia y alertas según `contracts/pricing.md` en `backend/src/modules/pricing/router.py` (depende de T046, T049)
- [ ] T052 [P] [US5] Frontend: `CompetenciaPage.vue` (alta de competidor, registro manual de precio con tienda/promoción, listado de alertas) en `frontend/src/modules/pricing/pages/`

**Checkpoint**: todas las user stories quedan independientemente funcionales.

---

## Phase 8: Polish

- [ ] T053 [P] Ejecutar `/speckit-analyze` sobre `spec.md`/`plan.md`/`tasks.md` de 003 antes de pasar a `/speckit-implement`
- [ ] T054 [P] Ejecutar manualmente los 7 escenarios de `quickstart.md` de punta a punta
- [ ] T055 Revisar cobertura de Principio X (margen real, margen objetivo efectivo ancla/nicho, doble autorización + rol del descuento manual) — no se exige 100% del resto de la feature
- [ ] T056 [P] Actualizar `checklists/requirements.md` con cualquier hallazgo de `/speckit-analyze`
