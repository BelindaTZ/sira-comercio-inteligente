# Tasks: Recursos Humanos

**Input**: Design documents from `/specs/011-recursos-humanos/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/recursos-humanos.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: el fan-out de una capacitación programada hacia todos los empleados con cuenta activa en los roles objetivo (y la exclusión de empleados sin cuenta), la restricción del Encargado de Tienda al cumplimiento de su propio personal, el cálculo de la tasa de rotación por tienda/periodo (incluyendo el caso sin datos), y la señalización de puestos críticos sin candidato de sucesión — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: Esta feature no crea módulo backend nuevo — extiende `modules/rrhh/` (008). Reutiliza infraestructura transversal ya construida en 001-008: FastAPI, SQLAlchemy async, Alembic, RBAC, `DataTable.vue`/`WorkPanel.vue`.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US4), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- **T001** [P] Migración Alembic: `ALTER TABLE roles_puesto ADD COLUMN es_critico BOOLEAN NOT NULL DEFAULT false` (`data-model.md`).
- **T002** [P] Migración Alembic: crear `acciones_retencion` (`data-model.md`).
- **T003** [P] Seed de `role_permisos_tabla`: `Jefe_RRHH` (UPDATE `roles_puesto`, INSERT/SELECT `acciones_retencion`, INSERT `capacitaciones`, INSERT/UPDATE `empleado_capacitacion`, INSERT/SELECT `clima_laboral`, INSERT/SELECT `plan_sucesion`), `Encargado_Tienda` (SELECT `empleado_capacitacion` — nuevo acceso concedido de solo lectura al módulo `RRHH`) (`data-model.md`, Extensión RBAC).
- **T004** [P] Frontend: crear páginas vacías `frontend/src/modules/rrhh/pages/PuestosCriticosPage.vue`, `RetencionPage.vue`, `CapacitacionesPage.vue`, `ClimaLaboralPage.vue`, `PlanSucesionPage.vue`.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- **T005** [P] Modelos SQLAlchemy: `AccionRetencion` en `models/`; extender `RolPuesto` (T001); exponer `Capacitacion`, `EmpleadoCapacitacion`, `ClimaLaboral`, `PlanSucesion` (ya existentes como modelos de 001) a través del repositorio de esta feature.
- **T006** Utilidad de parseo de `periodo` (`'AAAA-Sn'` → rango de fechas) usada por el cálculo de rotación (research.md Decisión 3).
- **T007** Montar las rutas nuevas en `rrhh.router` en `main.py`; verificar en RBAC que los accesos concedidos de T003 quedan activos.

**Checkpoint**: Migraciones aplicadas, modelos disponibles, router extendido — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Retención de roles críticos (Priority: P1) 🎯 MVP

**Goal**: El Jefe de RRHH marca puestos críticos y registra acciones de retención para empleados que los ocupan.

**Independent Test**: marcar un puesto como crítico y registrar una acción de retención para un empleado que lo ocupa, verificando que queda visible en el listado de retención.

### Tests para User Story 1 ⚠️

- **T008** [P] [US1] Unit test: registrar una acción de retención para un empleado en un puesto NO crítico se permite (Edge Case, FR-002).
- **T009** [US1] Contract test: `PATCH rrhh/puestos/{id}/critico`, `POST rrhh/acciones-retencion`, `GET rrhh/empleados/{id}/acciones-retencion`.
- **T010** [US1] Integration test: marcar puesto crítico → registrar acción de retención → consultar en cualquier momento (Escenario 1 de `quickstart.md`).

### Implementación de User Story 1

- **T011** [US1] `RRHHRepository` (extensión de 008): UPDATE de `roles_puesto.es_critico`; CRUD de `acciones_retencion`.
- **T012** [US1] `RRHHService.marcar_puesto_critico()` / `.registrar_accion_retencion()` (depende de T008).
- **T013** [US1] Endpoints: `PATCH rrhh/puestos/{id}/critico`, `POST rrhh/acciones-retencion`, `GET rrhh/empleados/{id}/acciones-retencion` — `contracts/recursos-humanos.md`.
- **T014** [US1] `frontend/.../PuestosCriticosPage.vue` y `RetencionPage.vue`.

**Checkpoint**: MVP — OO-8.1.1/8.1.2 completos, el Jefe de RRHH identifica puestos críticos y registra retención sin depender de una lista externa (SC-001).

---

## Phase 4: User Story 2 - Capacitación en el sistema (Priority: P2)

**Goal**: El Jefe de RRHH programa capacitaciones por rol con fan-out automático; el Encargado de Tienda confirma el cumplimiento de su propio personal.

**Independent Test**: programar una capacitación y marcar su cumplimiento para un empleado, verificando que el Encargado de Tienda ve el estado de cumplimiento de su personal.

### Tests para User Story 2 ⚠️

- **T015** [P] [US2] Unit test: el fan-out al programar una capacitación incluye solo empleados con cuenta activa (`usuarios`, 008) en los roles objetivo, excluyendo empleados sin cuenta (FR-003/FR-004, research.md Decisión 2).
- **T016** [P] [US2] Unit test: `GET tiendas/{id}/cumplimiento-capacitacion` restringe al Encargado de Tienda a su propia tienda (FR-005).
- **T017** [US2] Integration test: programar capacitación → fan-out → confirmar cumplimiento → Encargado de Tienda ve el estado de su personal (Escenario 2 de `quickstart.md`).

### Implementación de User Story 2

- **T018** [US2] `RRHHRepository`: consulta de solo lectura a `usuarios.role_id` (`modules/sistema/`, 008, boundary documentado en `plan.md`) para resolver empleados objetivo.
- **T019** [US2] `RRHHService.programar_capacitacion()`: INSERT en `capacitaciones` + fan-out hacia `empleado_capacitacion` (depende de T015, T018).
- **T020** [US2] `RRHHService.confirmar_cumplimiento()` / `.consultar_cumplimiento_tienda()` (depende de T016).
- **T021** [US2] Endpoints: `POST rrhh/capacitaciones`, `PATCH rrhh/empleado-capacitacion/{empleado_id}/{capacitacion_id}/completar`, `GET rrhh/tiendas/{id}/cumplimiento-capacitacion`.
- **T022** [US2] `frontend/.../CapacitacionesPage.vue`.

**Checkpoint**: OO-8.2.1/8.2.2 completos — el Encargado de Tienda ve el cumplimiento de su personal sin preguntar uno por uno (SC-002).

---

## Phase 5: User Story 3 - Clima laboral semestral y su cruce con rotación (Priority: P3)

**Goal**: El Jefe de RRHH registra el resultado de clima laboral por tienda/periodo y ve la tasa de rotación del mismo periodo cruzada automáticamente.

**Independent Test**: registrar un resultado de encuesta para una tienda y un periodo, verificando que el sistema muestra junto a él la tasa de rotación de esa misma tienda en ese periodo.

### Tests para User Story 3 ⚠️

- **T023** [P] [US3] Unit test: cálculo de la tasa de rotación por tienda/periodo a partir de `empleados.fecha_baja` (research.md Decisión 3).
- **T024** [P] [US3] Unit test: un periodo sin encuesta registrada devuelve "sin datos", nunca un indicador inventado (FR-010, Edge Case).
- **T025** [US3] Integration test: registrar clima → verificar cruce con rotación → periodo sin encuesta devuelve 404 (Escenario 3 de `quickstart.md`).

### Implementación de User Story 3

- **T026** [US3] `RRHHRepository`: CRUD de `clima_laboral`; consulta de `empleados.fecha_baja` por tienda/rango de fechas (depende de T006).
- **T027** [US3] `RRHHService.registrar_clima()` / `.consultar_clima_rotacion()` (depende de T023, T024).
- **T028** [US3] Endpoints: `POST rrhh/clima-laboral`, `GET rrhh/tiendas/{id}/clima-rotacion`.
- **T029** [US3] `frontend/.../ClimaLaboralPage.vue`: resultado de clima junto a la rotación cruzada.

**Checkpoint**: OO-8.3.1/8.3.2 completos — el Jefe de RRHH ve clima y rotación cruzados sin hacerlo a mano (SC-003).

---

## Phase 6: User Story 4 - Plan de sucesión (Priority: P4)

**Goal**: El Jefe de RRHH identifica candidatos internos para puestos críticos; el sistema señala explícitamente los puestos críticos sin cobertura.

**Independent Test**: registrar un candidato interno para un puesto crítico y verificar que aparece en el plan de sucesión de ese puesto; y que un puesto crítico sin candidato se señala explícitamente.

### Tests para User Story 4 ⚠️

- **T030** [P] [US4] Unit test: `GET plan-sucesion/cobertura` señala `sin_cobertura: true` para todo puesto crítico sin ninguna fila en `plan_sucesion` (FR-009).

### Implementación de User Story 4

- **T031** [US4] `RRHHRepository`: CRUD de `plan_sucesion`; consulta de cobertura (`roles_puesto.es_critico=true` LEFT JOIN `plan_sucesion`) (depende de T030).
- **T032** [US4] Endpoints: `POST rrhh/plan-sucesion`, `GET rrhh/plan-sucesion/cobertura`.
- **T033** [US4] `frontend/.../PlanSucesionPage.vue`: badge de alerta no bloqueante para puestos sin cobertura.

**Checkpoint**: OO-8.4.1/8.4.2 completos — ningún puesto crítico queda sin cobertura sin que el sistema lo señale (SC-004).

---

## Phase 7: Polish

- **T034** Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- **T035** Correr los 4 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- **T036** Revisar cobertura de Principio X: confirmar que el fan-out de capacitación (T015), la restricción por tienda (T016), el cálculo de rotación (T023) y la señalización de cobertura (T030) tienen test unitario antes de cerrar la feature.
- **T037** Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final.

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias.
- US1 (T008-T014) no depende de ninguna otra historia de esta feature.
- US2 (T015-T022) depende de que 008 ya tenga cuentas de usuario creadas para poder resolver el fan-out (T018, boundary documentado) — no depende de US1.
- US3 (T023-T029) no depende de ninguna otra historia de esta feature — reutiliza `empleados.fecha_baja` ya existente desde 001.
- US4 (T030-T033) depende de US1 en el sentido de que "puesto crítico" (T012) debe existir para que la consulta de cobertura tenga sentido, aunque no bloquea su implementación de código.
- La consulta de solo lectura de US2 a `usuarios.role_id` (T018, boundary `rrhh`→`sistema`) no requiere ningún cambio en `modules/sistema/` más allá de lo ya expuesto por 008.
