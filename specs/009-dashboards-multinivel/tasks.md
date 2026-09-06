# Tasks: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel | **Input**: plan.md, research.md, data-model.md, contracts/dashboards-multinivel.md, quickstart.md

**Estado**: en espera de 010-plataforma-datos-tactico-estrategico — las tareas de esta feature pueden implementarse y probarse con fixtures (sin ClickHouse/Airflow reales), pero el job diario de publicación en producción no se activa hasta que 010 esté construida (constitution.md).

**Tests**: contract e integration antes de la implementación (Principio X, TDD por historia de usuario).

## Phase 1: Setup

- T001 Crear rama `009-dashboards-multinivel` y confirmar que `.specify/feature.json` apunta a esta feature.
- T002 [P] Crear paquete `backend/modules/direccion/` (router, service, repository, jobs/) — primer uso real del módulo.
- T003 [P] Crear subpaquete `backend/modules/ti/dashboards/` (router, service, repository, jobs/) dentro del módulo TI ya existente.
- T004 [P] Crear stubs de tests `backend/tests/contract/test_dashboards_multinivel.py` y `backend/tests/integration/test_publicacion_dashboards.py`.
- T005 [P] Crear componentes frontend vacíos: `DashboardEstrategico.vue`, `DashboardTactico.vue`, `VerificacionDashboardsOperativos.vue`.

## Phase 2: Foundational (bloqueante para todas las historias)

- T006 Migración Alembic: crear `registro_publicacion_dashboard` (data-model.md).
- T007 Migración Alembic: crear `dashboard_kpi` con sus índices.
- T008 Migración Alembic: crear `dashboard_operativo_estado` con sus índices, incluido el parcial sobre `disponible = false`.
- T009 Seed: agregar filas de `role_permisos_tabla` para las 3 tablas nuevas, por cada rol de data-model.md §RBAC (`Gerente_General`, los 6 `Jefe_*`, con alcance validado en capa de servicio por `dimension`/módulo propio).
- T010 [P] Definir schemas Pydantic base (`DashboardKpiOut`, `PublicacionOut`, `DashboardOperativoEstadoOut`) en ambos módulos.
- T011 Implementar la consulta de solo lectura `MAX(fecha_hora)` por tienda contra las tablas fuente de 001-007 usadas por `dashboard_operativo_estado` (research.md Decisión 3) — sin escribir en ninguna de esas tablas.

**Checkpoint**: schema y RBAC listos; cualquier historia de usuario puede implementarse desde aquí en cualquier orden (todas dependen del mismo par registro/kpi, pero no entre sí).

## Phase 3: User Story 1 - Dashboard estratégico consolidado (P1) 🎯 MVP

### Tests

- T012 [P] [US1] Contract test `GET /direccion/dashboard-estrategico` (200 con KPIs y fecha de publicación).
- T013 [US1] Integration test: KPI de OE-4 siempre `disponible: false, valor: null`; KPI de OE-8 (fixture con fuente 011) siempre `disponible: true` con valor real (Acceptance Scenario 2, corrección de esta ronda).
- T014 [US1] Integration test: dos publicaciones sucesivas — el endpoint siempre devuelve la más reciente con su `fecha_publicacion` correcta (Acceptance Scenario 3).

### Implementation

- T015 [US1] Implementar `repository.py`/`service.py` de `modules/direccion` para leer la última publicación exitosa y sus KPIs.
- T016 [US1] Implementar `GET /direccion/dashboard-estrategico` (contracts #1).
- T017 [US1] Implementar el job `publicar_dashboard_estrategico.py`: lee agregaciones de ClickHouse (010, vía Airflow), inserta una fila en `registro_publicacion_dashboard` y sus `dashboard_kpi` asociados, marcando OE-4 como no disponible y OE-8 con el valor real de 011.
- T018 [P] [US1] Componente `DashboardEstrategico.vue` con fecha de última actualización visible junto a los valores (Principio XII).

**Checkpoint**: US1 funciona de forma independiente con fixtures — MVP entregable en cuanto 010 esté lista para producción.

## Phase 4: User Story 2 - Dashboards tácticos por departamento (P2)

### Tests

- T019 [P] [US2] Contract test `GET /ti/dashboards/tactico/{modulo_nombre}` (200 filtrado a la dimensión correcta).
- T020 [US2] Integration test: un `Jefe_Comercial` no puede leer el dashboard de `Finanzas` (403); `Gerente_General` sí puede leer cualquiera (Acceptance Scenario 2).
- T021 [US2] Integration test: un KPI marcado `disponible: false` por datos insuficientes no bloquea el resto del dashboard del mismo módulo (Acceptance Scenario 3).

### Implementation

- T022 [US2] Implementar `repository.py`/`service.py` de `modules/ti/dashboards` con el filtro de alcance por `dimension`/módulo propio del rol autenticado.
- T023 [US2] Implementar `GET /ti/dashboards/tactico/{modulo_nombre}` (contracts #2).
- T024 [US2] Implementar el job `publicar_dashboards_tacticos.py`: una corrida por cada uno de los 6 módulos de research.md Decisión 4, cada una con su propia fila en `registro_publicacion_dashboard`.
- T025 [P] [US2] Componente `DashboardTactico.vue`, reutilizado por los 6 roles de Jefe, parametrizado por su propio módulo.

**Checkpoint**: US2 funciona de forma independiente — cada Jefe consulta su propio dashboard sin depender de que otro departamento ya tenga el suyo publicado.

## Phase 5: User Story 3 - Verificación de disponibilidad de dashboards operativos (P3)

### Tests

- T026 [P] [US3] Contract test `GET /ti/dashboards/operativos/verificacion` (200 con estado por tienda/dashboard).
- T027 [P] [US3] Contract test `GET /ti/dashboards/operativos/alertas` (200, solo filas `disponible: false`).
- T028 [US3] Integration test: un dashboard operativo sin actualizarse por más de un día aparece señalado (Acceptance Scenario 2).

### Implementation

- T029 [US3] Implementar el job `verificar_dashboards_operativos.py`: `MAX(fecha_hora)` por tienda contra cada tabla fuente de 001-007 (T011), inserta filas en `dashboard_operativo_estado` y una fila en `registro_publicacion_dashboard` (`tipo_dashboard='operativo'`).
- T030 [US3] Implementar `GET /ti/dashboards/operativos/verificacion` y `GET /ti/dashboards/operativos/alertas` (contracts #3, #4).
- T031 [P] [US3] Componente `VerificacionDashboardsOperativos.vue` con las alertas resaltadas para `Jefe_TI`.

**Checkpoint**: el Jefe de TI puede revisar diariamente el estado de toda la red sin visitar cada tienda.

## Phase 6: Polish

- T032 Implementar el trigger manual de desarrollo `POST /ti/dashboards/{tipo}/forzar-publicacion` (contracts #5, FR-010) y su bloqueo en producción.
- T033 [P] Revisar que los 10 FR de spec.md tengan al menos un test de contrato o integración que los cubra (tabla de trazabilidad, data-model.md).
- T034 [P] Confirmar que ningún endpoint de lectura de esta feature consulta ClickHouse directamente (Principio III) — revisión de código dirigida.
- T035 Ejecutar quickstart.md end-to-end (4 escenarios) contra un entorno con fixtures.
- T036 Re-chequeo de la tabla de Constitution Check de plan.md tras la implementación completa.

## Dependencias clave

- Foundational (T006-T011) bloquea las tres historias de usuario.
- US1 (P1) es el MVP y es independiente de US2/US3.
- US2 (P2) es independiente de US1/US3 — su único requisito común es Foundational.
- US3 (P3) es independiente de US1/US2 en código, aunque conceptualmente se apoya en que 001-007 ya tengan datos operativos reales (ya cerradas, siempre cierto).
- Esta feature completa permanece en espera de producción hasta que 010-plataforma-datos-tactico-estrategico esté implementada (jobs T017/T024/T029 dependen de ClickHouse/Airflow reales); todo lo demás puede desarrollarse y probarse con fixtures desde ahora.
