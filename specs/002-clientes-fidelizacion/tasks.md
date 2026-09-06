# Tasks: Clientes y Fidelización (002-clientes-fidelizacion)

**Input**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`
**Prerequisites**: plan.md (required), spec.md (required)
**Tests**: incluidos — Principio X exige cobertura obligatoria en: cálculo del CLV compuesto (nunca gasto bruto puro), cálculo del ciclo de compra individual y su severidad (nunca umbral fijo), y el gating de consentimiento de datos. No se exige 100% del resto de la feature.
**Organización**: por módulo de negocio (`modules/clientes/`, ya reservado desde el `plan.md` de 001), más `jobs/` para los 2 jobs periódicos nuevos. La infraestructura transversal de 001 (FastAPI, SQLAlchemy async, Alembic, repositorio base, RBAC, `sendgrid_client.py`, `DataTable.vue`/`WorkPanel.vue`, composables núcleo) ya existe y se reutiliza sin repetirla aquí (DRY).

## Format: `[ID] [P?] [Story] Descripción`
- **[P]**: puede ejecutarse en paralelo (archivo distinto, sin dependencias)
- **[Story]**: US1-US5 según prioridad de spec.md

---

## Phase 1: Setup

- [ ] T001 Agregar `APScheduler` a `backend/pyproject.toml`; crear `backend/src/jobs/__init__.py` (el resto del stack ya está inicializado desde 001, no se repite)
- [ ] T002 [P] Migración Alembic con las extensiones de esta feature: `clientes.consentimiento_datos`/`fecha_consentimiento_datos`, `churn_score.severidad`, `campanas.categoria_sira`, `campana_cliente.grupo`, tabla `campana_resultado`, tabla `cupon_enviado`, secuencia `campanas_campaign_id_seq`

---

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [ ] T003 [P] Modelos SQLAlchemy nuevos/extendidos en `backend/src/models/`: `cliente.py` (extender), `cliente_demografico.py`, `nivel_fidelizacion.py`, `cliente_clv.py`, `churn_score.py` (extender), `campana.py` (extender), `campana_cliente.py` (extender), `campana_resultado.py`, `cupon.py`, `cupon_enviado.py`, `cupon_redimido.py`, `evento_cliente.py`
- [ ] T004 Configurar `APScheduler` en `backend/src/jobs/scheduler.py`: registra el job semanal (CLV/churn) y el diario (hitos), arranque/apagado en el ciclo de vida de FastAPI (`backend/src/main.py`) — research.md §3
- [ ] T005 [P] Endpoint interno solo-desarrollo para forzar manualmente cada job (usado por `quickstart.md`, no expuesto en producción)
- [ ] T006 Montar el router del módulo `clientes` en `backend/src/main.py`

**Checkpoint**: infraestructura lista — las user stories pueden empezar.

---

## Phase 3: User Story 1 - Registrar y mantener el perfil del cliente (Priority: P1) 🎯 MVP

**Goal**: alta de cliente con captura de consentimiento de tratamiento de datos, actualización sin perder historial, baja con anonimización real.

**Independent Test**: Escenarios 1-2 de `quickstart.md` (consentimiento rechazado, baja con anonimización).

### Tests para User Story 1 ⚠️

- [ ] T007 [P] [US1] Contract test `POST /api/clientes` (rechaza email duplicado; acepta `consentimiento_datos: false` sin bloquear el alta) en `backend/tests/contract/test_clientes_alta.py`
- [ ] T008 [P] [US1] Contract test `PATCH /api/clientes/{id}` (no altera CLV/churn previos; revocar `consentimiento_datos` no anonimiza nada) en `backend/tests/contract/test_clientes_actualizar.py`
- [ ] T009 [P] [US1] Contract test `DELETE /api/clientes/{id}` (verifica anonimización real de nombre/email/teléfono/fecha_nacimiento, `household_id` intacto) en `backend/tests/contract/test_clientes_baja.py`
- [ ] T010 [P] [US1] Unit test del gating de consentimiento: un cliente con `consentimiento_datos=false` nunca aparece en el resultado del repository de CLV/churn/campañas en `backend/tests/unit/test_gating_consentimiento.py` (Principio X)
- [ ] T011 [US1] Integration test Escenarios 1 y 2 de `quickstart.md` en `backend/tests/integration/test_us1_perfil_cliente.py`

### Implementación de User Story 1

- [ ] T012 [US1] `ClientesRepository` (CRUD + filtro `consentimiento_datos=true` reutilizable por los jobs) en `backend/src/modules/clientes/repository.py` (depende de T003)
- [ ] T013 [US1] `ClientesService.registrar_cliente` — captura consentimiento + fecha, valida email único (FR-001) en `backend/src/modules/clientes/service.py`
- [ ] T014 [US1] `ClientesService.actualizar_cliente` — incluye revocar/otorgar `consentimiento_datos` (actualiza `fecha_consentimiento_datos`, sin anonimizar) (FR-002) en `backend/src/modules/clientes/service.py`
- [ ] T015 [US1] `ClientesService.dar_de_baja` — UPDATE de anonimización real, conserva `household_id` (FR-003, research.md §5) en `backend/src/modules/clientes/service.py`
- [ ] T016 [P] [US1] Endpoints REST de perfil (`POST`/`PATCH`/`DELETE`/`GET /api/clientes`) según `contracts/clientes.md` en `backend/src/modules/clientes/router.py` (depende de T013-T015)
- [ ] T017 [P] [US1] Frontend: `ClientesPage.vue`, `FormularioCliente.vue` (captura el consentimiento en el alta y permite revocarlo/otorgarlo después desde el mismo formulario de edición) en `frontend/src/modules/clientes/`
- [ ] T018 [P] [US1] Frontend: `clientesApi.js` (capa de servicio centralizada, Principio XI) en `frontend/src/services/`

**Checkpoint**: US1 entregable de forma independiente — alta/actualización/baja de cliente funcionando de punta a punta.

---

## Phase 4: User Story 2 - Calcular CLV compuesto y niveles de fidelización (Priority: P2)

**Goal**: CLV semanal que combina frecuencia y margen real (nunca gasto bruto), con reclasificación automática de nivel.

**Independent Test**: Escenario 3 de `quickstart.md`.

### Tests para User Story 2 ⚠️

- [ ] T019 [P] [US2] Unit test de la fórmula de CLV: verifica que un cliente de compra frecuente/margen bajo y otro de compra única/margen alto no se ordenan solo por gasto acumulado en `backend/tests/unit/test_calculo_clv.py` (FR-005, Principio X)
- [ ] T020 [P] [US2] Contract test `GET`/`PATCH /api/clientes/niveles-fidelizacion` en `backend/tests/contract/test_niveles_fidelizacion.py`
- [ ] T021 [US2] Integration test Escenario 3 de `quickstart.md` en `backend/tests/integration/test_us2_clv.py`

### Implementación de User Story 2

- [ ] T022 [US2] Job semanal `calcular_clv_job.py` — implementa la fórmula de `research.md` §1 (ventana 180 días, normalización percentil 95, gating de consentimiento) en `backend/src/jobs/`
- [ ] T023 [US2] `ClientesService.reclasificar_nivel` — compara `clv_score` contra umbrales vigentes (FR-006, FR-008) en `backend/src/modules/clientes/service.py`
- [ ] T024 [US2] Endpoints `GET`/`PATCH /api/clientes/niveles-fidelizacion` (FR-007) en `backend/src/modules/clientes/router.py`
- [ ] T025 [P] [US2] Frontend: mostrar CLV/nivel actual en el detalle de `ClientesPage.vue`

**Checkpoint**: US2 entregable de forma independiente sobre US1.

---

## Phase 5: User Story 3 - Detectar riesgo de fuga con severidad (Priority: P3)

**Goal**: ciclo de compra individual por cliente, con dos niveles de severidad (`en_riesgo`/`inactivo`), nunca un umbral fijo de días.

**Independent Test**: Escenario 4 de `quickstart.md`.

### Tests para User Story 3 ⚠️

- [ ] T026 [P] [US3] Unit test de ciclo de compra individual + clasificación de severidad (1.5x/3x sobre el ciclo propio, nunca un umbral fijo de días) en `backend/tests/unit/test_calculo_churn.py` (FR-009, FR-010, Principio X)
- [ ] T027 [P] [US3] Contract test `GET /api/clientes/riesgo-fuga?severidad=` en `backend/tests/contract/test_riesgo_fuga.py`
- [ ] T028 [US3] Integration test Escenario 4 de `quickstart.md` en `backend/tests/integration/test_us3_churn.py`

### Implementación de User Story 3

- [ ] T029 [US3] Job semanal `calcular_churn_job.py` — ciclo individual + severidad (research.md §2, gating de consentimiento) en `backend/src/jobs/`
- [ ] T030 [US3] Endpoint `GET /api/clientes/riesgo-fuga` (filtro por severidad, paginado, sin cálculo manual — SC-005) en `backend/src/modules/clientes/router.py` (FR-011)
- [ ] T031 [P] [US3] Frontend: `RiesgoFugaPage.vue`, `TablaClientesRiesgo.vue` (filtro reactivo por severidad) en `frontend/src/modules/clientes/`

**Checkpoint**: US3 entregable de forma independiente sobre US1 (no depende de US2).

---

## Phase 6: User Story 4 - Campañas automáticas por hito (Priority: P4)

**Goal**: evento diario de cumpleaños/aniversario con cupón automático por correo, y tasa de redención consultable.

**Independent Test**: Escenario 5 de `quickstart.md`.

### Tests para User Story 4 ⚠️

- [ ] T032 [P] [US4] Unit test de selección del producto ancla del cupón (`es_ancla=true`, mayor margen vigente) en `backend/tests/unit/test_seleccion_cupon_hito.py`
- [ ] T033 [P] [US4] Contract test `GET /api/clientes/cupones/tasa-redencion` (agrupado por `tipo_evento`) en `backend/tests/contract/test_tasa_redencion.py`
- [ ] T034 [US4] Integration test Escenario 5 de `quickstart.md` en `backend/tests/integration/test_us4_cupon_hito.py`

### Implementación de User Story 4

- [ ] T035 [US4] Job diario `eventos_hito_job.py` — genera `eventos_cliente` + `cupon_enviado`, dispara SendGrid (reutiliza `sendgrid_client.py` de 001, sin duplicar) (FR-012, FR-013) en `backend/src/jobs/`
- [ ] T036 [US4] `ClientesService.registrar_redencion` — `POST /api/clientes/cupones/{upc}/redimir` (FR-015) en `backend/src/modules/clientes/service.py`
- [ ] T037 [US4] Endpoint `GET /api/clientes/cupones/tasa-redencion` (FR-014) en `backend/src/modules/clientes/router.py`
- [ ] T038 [P] [US4] Frontend: panel de tasa de redención por hito en `frontend/src/modules/clientes/pages/CampanasPage.vue`

**Checkpoint**: US4 entregable de forma independiente sobre US1.

---

## Phase 7: User Story 5 - Campañas de reactivación con grupo de control y uplift (Priority: P5)

**Goal**: campaña de reactivación que exige grupo de control antes de enviarse, con uplift real medido al cierre.

**Independent Test**: Escenario 6 de `quickstart.md`.

### Tests para User Story 5 ⚠️

- [ ] T039 [P] [US5] Contract test `POST /api/clientes/campanas` + `POST /.../enviar` — 422 si no hay ningún miembro `grupo=control` en `backend/tests/contract/test_campana_reactivacion.py` (FR-017)
- [ ] T040 [P] [US5] Unit test de cálculo de uplift: compara `tasa_retorno_tratado` vs `tasa_retorno_control`, nunca solo la tasa de redención en `backend/tests/unit/test_calculo_uplift.py` (FR-018, Principio X)
- [ ] T041 [US5] Integration test Escenario 6 de `quickstart.md` en `backend/tests/integration/test_us5_reactivacion.py`

### Implementación de User Story 5

- [ ] T042 [US5] `CampanasService.crear_campana_reactivacion` — crea campaña (`campanas_campaign_id_seq`) y miembros con grupo (FR-016) en `backend/src/modules/clientes/service.py`
- [ ] T043 [US5] `CampanasService.enviar` — valida grupo de control, envía solo al grupo tratado (FR-017) en `backend/src/modules/clientes/service.py` (depende de T042)
- [ ] T044 [US5] `CampanasService.cerrar` — calcula tasas de retorno + `uplift`, inserta `campana_resultado` (FR-018) en `backend/src/modules/clientes/service.py`
- [ ] T045 [US5] Endpoint `POST /api/clientes/campanas/{id}/decision` (Jefe_Marketing, FR-019) en `backend/src/modules/clientes/router.py`
- [ ] T046 [P] [US5] Frontend: `CampanasPage.vue`, `FormularioCampana.vue` (asignación de grupo tratado/control) en `frontend/src/modules/clientes/`

**Checkpoint**: US5 entregable de forma independiente sobre US3 (consume `riesgo-fuga` para elegir miembros).

---

## Phase 8: Polish

- [ ] T047 [P] Ejecutar `/speckit-analyze` sobre spec.md/plan.md/tasks.md de 002 antes de pasar a `/speckit-implement`
- [ ] T048 [P] Ejecutar manualmente los 6 escenarios de `quickstart.md` de punta a punta
- [ ] T049 Revisar cobertura de Principio X (cálculo de CLV, cálculo de churn+severidad, gating de consentimiento) — no se exige 100% del resto de la feature
- [ ] T050 [P] Actualizar `checklists/requirements.md` con cualquier hallazgo de `/speckit-analyze`
