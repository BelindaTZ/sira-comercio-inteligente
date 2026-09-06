# Tasks: Caja, Mermas y Fraude

**Input**: Design documents from `/specs/006-caja-mermas-fraude/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/caja-mermas-fraude.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: el cálculo automático de la diferencia de cuadre (incluyendo ventana con cero ventas), el marcado automático para revisión, la identificación automática de datáfonos no conformes, el cálculo del porcentaje de merma semanal, y que un incidente de fraude sobre un empleado dado de baja no quede bloqueado — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: `modules/caja/` es el módulo nuevo de esta feature (módulo RBAC `Finanzas` ya sembrado desde 001, sin uso hasta ahora); `modules/inventario/` (001) se consulta de solo lectura para el reporte de patrones, sin recrearse. Reutiliza infraestructura transversal ya construida en 001-005: FastAPI, SQLAlchemy async, Alembic, RBAC, `DataTable.vue`/`WorkPanel.vue`.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US5), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- **T001** Crear el esqueleto de `backend/src/modules/caja/` (`router.py`, `service.py`, `repository.py`, `schemas.py`), calcado de la estructura de capas ya usada en `pricing/` (003) y `promociones/` (005).
- **T002** [P] Migración Alembic: crear `configuracion_seguridad_pagos`, `protocolo_escalamiento`, `umbral_merma_categoria`; `ALTER TABLE incidentes_fraude` (`cierre_id` pasa a nullable, se agregan `ajuste_id`, `acciones_tomadas`, `resultado`, `actualizado_por`, `fecha_actualizacion` — `data-model.md` completo).
- **T003** [P] Seed de `role_permisos_tabla` para `Encargado_Tienda`, `Jefe_Finanzas`, `Jefe_TI`, `Jefe_Operaciones` sobre las tablas de esta feature (`data-model.md`, Extensión RBAC) — sin rol ni módulo nuevo, reutiliza `Finanzas` ya sembrado.
- **T004** [P] Frontend: crear `frontend/src/modules/caja/` (`pages/CuadreCajaPage.vue`, `DatafonosPage.vue`, `ReporteDiferenciasPage.vue`, `IncidentesFraudePage.vue`, `ProtocoloEscalamientoPage.vue`, `SeguimientoMermaPage.vue` vacíos) y `frontend/src/services/cajaApi.js`.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- **T005** [P] Modelos SQLAlchemy: `ConfiguracionSeguridadPagos`, `ProtocoloEscalamiento`, `UmbralMermaCategoria` en `models/`; extender `IncidenteFraude` con las columnas de T002.
- **T006** `CajaRepository`: helper compartido para resolver la apertura de caja vigente de un cuadre (`research.md` Decisión 2 y 3) — usado tanto por el cuadre horario (US1) como por el reporte mensual (US3).
- **T007** [P] Seed inicial de `configuracion_seguridad_pagos` (una versión mínima de firmware por defecto) y `protocolo_escalamiento` (un texto inicial), para que US2/US4 tengan un estado vigente desde el arranque.
- **T008** Montar `caja.router` en `main.py`; verificar en RBAC que el módulo `Finanzas` (ya sembrado) cubre los endpoints de esta feature, incluido el acceso concedido a `Jefe_TI` (`research.md` Decisión 10) — sin rol ni módulo nuevo.

**Checkpoint**: Migraciones aplicadas, modelos disponibles, router montado — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Cuadre de caja horario con detección automática de diferencias (Priority: P1) 🎯 MVP

**Goal**: El cajero cuadra su caja cada hora sin calcular nada a mano; el sistema calcula la diferencia y la marca para revisión automáticamente; el Encargado de Tienda valida todas las cajas de su tienda en una sola consulta.

**Independent Test**: abrir una caja, registrar ventas, cerrar el cuadre con un total físico distinto del esperado, y verificar que la diferencia se calcula sola y que el Encargado de Tienda la ve.

### Tests para User Story 1 ⚠️

- **T009** [P] [US1] Unit test: cálculo de `total_esperado` por cajero sobre la ventana horaria (`research.md` Decisión 1 y 2), incluyendo el caso de una ventana sin ninguna venta.
- **T010** [P] [US1] Unit test: marcado automático para revisión cuando `diferencia <> 0`, y ausencia de marca cuando `diferencia = 0` (FR-004, Edge Case).
- **T011** [US1] Contract test: `POST caja/apertura`, `POST caja/cierre`, `GET caja/cierres` — verificar que `total_esperado` nunca se acepta del cliente (Principio V).
- **T012** [US1] Integration test: apertura → ventas → cierre con diferencia → el Encargado de Tienda ve todas las cajas de su tienda en una sola consulta (Escenarios 1 y 2 de `quickstart.md`).

### Implementación de User Story 1

- **T013** [US1] `CajaRepository`: insert de `apertura_caja`; insert de `cierre_caja` con `total_esperado` calculado server-side.
- **T014** [US1] `CajaService.calcular_total_esperado()`: ventana horaria por cajero (depende de T009, T006).
- **T015** [US1] `CajaService.registrar_apertura()` / `.registrar_cierre()`: orquesta T013+T014, determina `marcado_para_revision` (depende de T010).
- **T016** [US1] `CajaService.listar_cierres_tienda()`: todas las cajas de una tienda en una sola consulta (FR-005).
- **T017** [US1] Endpoints: `POST caja/apertura`, `POST caja/cierre`, `GET caja/cierres` — `contracts/caja-mermas-fraude.md`.
- **T018** [US1] `frontend/.../CuadreCajaPage.vue`: formulario de apertura/cuadre para el Cajero, vista consolidada de cajas para el Encargado de Tienda.
- **T019** [US1] Frontend: badge visual de diferencia (positiva/negativa/cero), sin ningún cálculo en el cliente (Principio V).

**Checkpoint**: MVP — un cajero cuadra su caja y el Encargado de Tienda valida todas las cajas de su tienda, de punta a punta.

---

## Phase 4: User Story 2 - Certificación y actualización de datáfonos (Priority: P2)

**Goal**: Mantener el inventario de datáfonos, identificar automáticamente los no conformes frente al estándar de seguridad vigente, y registrar su actualización o reemplazo.

**Independent Test**: registrar un datáfono con firmware desactualizado, verificar que aparece como no conforme, actualizarlo y verificar que deja de aparecer.

### Tests para User Story 2 ⚠️

- **T020** [P] [US2] Unit test: identificación de un datáfono no conforme comparando `version_firmware` contra la versión mínima vigente (`research.md` Decisión 4).
- **T021** [US2] Integration test: definir estándar → datáfono desactualizado aparece no conforme → se actualiza → deja de aparecer, con `fecha_ultima_actualizacion` registrada (Escenario 3 de `quickstart.md`).

### Implementación de User Story 2

- **T022** [US2] `CajaRepository`: CRUD de `datafonos`; insert de `configuracion_seguridad_pagos` (vigente = fila más reciente).
- **T023** [US2] `CajaService.evaluar_conformidad_datafonos()`: recorre `datafonos`, actualiza `estado` según T020 (depende de T020, T022).
- **T024** [US2] `CajaService.definir_estandar_seguridad()`: inserta nueva versión vigente y dispara T023 (efecto secundario documentado en `contracts/caja-mermas-fraude.md`).
- **T025** [US2] `CajaService.actualizar_datafono()`: `estado='activo'`, `fecha_ultima_actualizacion=hoy`.
- **T026** [US2] Endpoints: `GET datafonos`, `PATCH datafonos/{id}/actualizar`, `GET`/`PUT configuracion-seguridad-pagos`.
- **T027** [US2] `frontend/.../DatafonosPage.vue`: inventario con filtro por estado, acción de registrar actualización.

**Checkpoint**: OT-6.3 completo — un datáfono no conforme se identifica sin inventariar manualmente (SC-003).

---

## Phase 5: User Story 3 - Análisis mensual de patrones de diferencias y escalamiento (Priority: P3)

**Goal**: Reporte mensual de diferencias de cuadre agrupado por cajero y turno, extendido con los ajustes de inventario anómalos de 001, desde el cual el Jefe de Finanzas puede escalar un patrón sospechoso.

**Independent Test**: sembrar varios cuadres de un mismo cajero con diferencias repetidas, consultar el reporte mensual agrupado, y abrir un incidente de fraude directamente desde ahí.

### Tests para User Story 3 ⚠️

- **T028** [P] [US3] Unit test: agrupación del reporte mensual por `cajero_id` + `apertura_id` (`research.md` Decisión 3), no por el total agregado de la tienda.
- **T029** [P] [US3] Unit test: señalización de ajustes de inventario (001) con diferencia negativa sobre el umbral configurable (FR-010).
- **T030** [US3] Integration test: cuadres con diferencia repetida de un cajero + un ajuste de inventario anómalo → reporte mensual → apertura de incidente de fraude (Escenario 4 de `quickstart.md`).

### Implementación de User Story 3

- **T031** [US3] `CajaRepository`: consulta de solo lectura contra `ajustes_inventario` (001, `plan.md`) para el reporte (depende de T029).
- **T032** [US3] `CajaService.generar_reporte_diferencias(mes, anio)`: agrupación por cajero/turno (depende de T028, T006) + ajustes señalados (depende de T031).
- **T033** [US3] `CajaRepository`: insert sobre `incidentes_fraude` admitiendo `cierre_id`/`ajuste_id` opcionales (`data-model.md` Decisión 6).
- **T034** [US3] `CajaService.escalar_incidente()`: abre un incidente de fraude con la evidencia que lo originó (FR-011) (depende de T033).
- **T035** [US3] Endpoints: `GET reporte-diferencias`, `POST incidentes-fraude`.
- **T036** [US3] `frontend/.../ReporteDiferenciasPage.vue`: reporte agrupado por cajero/turno con ajustes señalados, acción de escalar a incidente.

**Checkpoint**: OT-6.2 completo — los datos generados por US1 (y los ajustes de 001) se convierten en una señal accionable.

---

## Phase 6: User Story 4 - Aplicación del protocolo de escalamiento sobre un incidente de fraude (Priority: P4)

**Goal**: El protocolo de escalamiento vigente es consultable por cualquier Encargado de Tienda, quien lo aplica sobre un incidente abierto hasta que el Jefe de Finanzas lo cierra.

**Independent Test**: con un incidente en estado abierto, consultar el protocolo vigente, registrar las acciones tomadas, y verificar que el incidente transiciona a en revisión y luego a cerrado.

### Tests para User Story 4 ⚠️

- **T037** [P] [US4] Unit test: transición `abierto` → `en_revision` → `cerrado`, y que un incidente sobre un empleado con `fecha_baja` no queda bloqueado (FR-016).
- **T038** [US4] Integration test: consultar protocolo vigente → aplicar sobre un incidente abierto → cerrar con resultado, sin acusar al empleado si no se confirma (Escenario 5 de `quickstart.md`).

### Implementación de User Story 4

- **T039** [US4] `CajaRepository`: CRUD de `protocolo_escalamiento` (insert de nueva versión, consulta de la vigente).
- **T040** [US4] `CajaService.aplicar_protocolo()`: registra `acciones_tomadas`, transiciona a `en_revision`, completa `actualizado_por`/`fecha_actualizacion` (depende de T037).
- **T041** [US4] `CajaService.cerrar_incidente()`: registra `resultado`, transiciona a `cerrado`, sin bloquear por empleado dado de baja (depende de T037).
- **T042** [US4] Endpoints: `GET`/`PUT protocolo-escalamiento`, `PATCH incidentes-fraude/{id}/aplicar-protocolo`, `PATCH .../cerrar`, `GET incidentes-fraude`.
- **T043** [US4] `frontend/.../IncidentesFraudePage.vue` y `ProtocoloEscalamientoPage.vue`: ciclo completo del incidente; texto del protocolo consultable por cualquier Encargado de Tienda.

**Checkpoint**: un incidente de fraude sigue su ciclo completo, consultable en cualquier momento (SC-005).

---

## Phase 7: User Story 5 - Umbral de merma aceptable y seguimiento semanal (Priority: P5)

**Goal**: El Jefe de Operaciones define el umbral de merma aceptable por categoría; el Encargado de Tienda ve el porcentaje acumulado de su tienda frente a ese umbral cada semana.

**Independent Test**: definir un umbral para una categoría, registrar mermas de esa categoría en una tienda, y verificar que el Encargado de Tienda ve el porcentaje acumulado esa semana.

### Tests para User Story 5 ⚠️

- **T044** [P] [US5] Unit test: cálculo del porcentaje de merma acumulada semanal por categoría/tienda (`research.md` Decisión 9).
- **T045** [US5] Integration test: definir umbral → mermas ya registradas de 001 → seguimiento semanal muestra el porcentaje frente al umbral, sin bloquear ninguna operación (Escenario 6 de `quickstart.md`).

### Implementación de User Story 5

- **T046** [US5] `CajaRepository`: CRUD (upsert) de `umbral_merma_categoria`.
- **T047** [US5] `CajaService.calcular_seguimiento_semanal(tienda_id, semana)`: join de `mermas` y `venta_detalle` por `product_category` (depende de T044).
- **T048** [US5] Endpoints: `GET`/`PUT umbral-merma`, `GET tiendas/{id}/seguimiento-merma-semanal`.
- **T049** [US5] `frontend/.../SeguimientoMermaPage.vue`: porcentaje acumulado por categoría frente al umbral, presentado como alerta no bloqueante.

**Checkpoint**: OT-5.5 completo — el Encargado de Tienda ve el porcentaje sin calcularlo manualmente (SC-006).

---

## Phase 8: Polish

- **T050** Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- **T051** Correr los 6 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- **T052** Revisar cobertura de Principio X: confirmar que el cálculo de diferencia de cuadre (T009), la identificación de datáfono no conforme (T020), el cálculo de % de merma (T044) y la no obstrucción por empleado dado de baja (T037) tienen test unitario antes de cerrar la feature.
- **T053** Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final (nueva "Ronda" si aplica).

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias.
- US1 (T013-T019) es prerrequisito real de US3 (T028-T036) — el reporte mensual de patrones no tiene datos sobre los cuales operar hasta que existan cuadres generados por US1.
- US2 (datáfonos, T020-T027) no depende de ninguna otra historia de esta feature — puede implementarse en paralelo a US1 una vez cerrada la Phase 2.
- US3 es prerrequisito habitual, no estricto, de US4 (T037-T043): un incidente de fraude suele originarse en un patrón detectado por US3, pero US4 también admite un incidente registrado directamente sin ese patrón previo.
- US5 (umbral de merma, T044-T049) no depende de ninguna otra historia de esta feature — reutiliza datos ya sembrados por 001 (`mermas`, `venta_detalle`) y puede implementarse en cualquier momento.
- La consulta de solo lectura a `ajustes_inventario` (T031, boundary con 001) no requiere ningún cambio en `modules/inventario/`, solo una consulta nueva desde `finanzas/`.
