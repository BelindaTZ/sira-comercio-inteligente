# Tasks: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel | **Input**: plan.md, research.md, data-model.md, contracts/dashboards-multinivel.md, quickstart.md

**Estado**: en espera de 010-plataforma-datos-tactico-estrategico — las tareas de esta feature pueden implementarse y probarse con fixtures (sin ClickHouse/Airflow reales), pero el job diario de publicación en producción no se activa hasta que 010 esté construida (constitution.md).

**Tests**: contract e integration antes de la implementación (Principio X, TDD por historia de usuario).

**Estado de implementación (2026-09-08)**: completada con fixtures. Ronda 1 de alineación a las convenciones reales del código (mismo criterio que 010/012):
- base path real `/api/...` (el contrato decía `/api/v1/...`);
- los paquetes viven bajo `backend/src/modules/` (`direccion/`, `ti/dashboards/`), no `backend/modules/`;
- los 3 jobs se registran en el scheduler APScheduler embebido (`src/jobs/scheduler.py`, cron 04:00 / 04:15 / 05:00) y el trigger manual de FR-010 los invoca directamente — en producción los orquesta Airflow (010);
- lógica de KPIs / verificación compartida en `src/shared/dashboards.py`; sin ClickHouse configurado lee de PostgreSQL en modo solo lectura (fallback documentado, igual que el cargador no-op de 010).

## Phase 1: Setup

- [X] T001 Crear rama `009-dashboards-multinivel` y confirmar que `.specify/feature.json` apunta a esta feature.
- [X] T002 [P] Crear paquete `backend/src/modules/direccion/` (router, service, repository, schemas, jobs/) — primer uso real del módulo.
- [X] T003 [P] Crear subpaquete `backend/src/modules/ti/dashboards/` (router, service, repository, schemas, jobs/) dentro del módulo TI ya existente.
- [X] T004 [P] Crear tests `backend/tests/contract/test_dashboards_multinivel.py` y `backend/tests/integration/test_publicacion_dashboards.py` (+ fixture `escenario_dashboards` en `conftest.py`).
- [X] T005 [P] Crear componentes frontend `DashboardEstrategico.vue`, `DashboardTactico.vue`, `VerificacionDashboardsOperativos.vue` (+ servicios `direccionApi.js`, `tiDashboardsApi.js`, rutas).

## Phase 2: Foundational (bloqueante para todas las historias)

- [X] T006 Migración Alembic `0019`: crear `registro_publicacion_dashboard` con sus CHECKs (data-model.md).
- [X] T007 Migración Alembic `0019`: crear `dashboard_kpi` con sus índices.
- [X] T008 Migración Alembic `0019`: crear `dashboard_operativo_estado` con sus índices, incluido el parcial sobre `disponible = false`.
- [X] T009 Migración `0019` + bloque "EXTENSIÓN — Feature 009" en `01_operativo_postgres.sql`: `role_permisos_modulo`/`role_permisos_tabla` para `Gerente_General` (módulo `Direccion` + los 6 tácticos), cada `Jefe_*` (su módulo) y `Jefe_TI` (`dashboard_operativo_estado` + insert en `registro_publicacion_dashboard`). Alcance fino revalidado en `TiDashboardsService._verificar_alcance`.
- [X] T010 [P] Schemas Pydantic base: `DashboardKpiOut` + `DashboardConsolidadoOut` (`modules/direccion/schemas.py`, reutilizados por el táctico), `DashboardOperativoEstadoOut` + `VerificacionOperativosOut` + `ForzarPublicacionOut` (`modules/ti/dashboards/schemas.py`).
- [X] T011 Consulta de solo lectura `MAX(fecha_hora)` por tienda contra las tablas fuente (`alertas_inventario`, `cierre_caja`+`cajas`, `mermas`) en `src/shared/dashboards.py::estado_operativo` — sin escribir en ninguna.

**Checkpoint**: schema y RBAC listos.

## Phase 3: User Story 1 - Dashboard estratégico consolidado (P1) 🎯 MVP

### Tests

- [X] T012 [P] [US1] Contract test `GET /api/direccion/dashboard-estrategico` (200 con KPIs y fecha; 404 sin publicación; 403 sin RBAC).
- [X] T013 [US1] Integration test: OE-4 siempre `disponible: false, valor: null`; OE-8 (fixture con fuente 011) `disponible: true` con valor real.
- [X] T014 [US1] Integration test: dos publicaciones sucesivas — el endpoint devuelve la más reciente.

### Implementation

- [X] T015 [US1] `DireccionRepository` / `DireccionService` — lee la última publicación exitosa y sus KPIs.
- [X] T016 [US1] `GET /api/direccion/dashboard-estrategico` (contracts #1).
- [X] T017 [US1] Job `publicar_dashboard_estrategico.py`: inserta una fila en `registro_publicacion_dashboard` y sus `dashboard_kpi`, OE-4 no disponible, OE-8 con el valor real de 011.
- [X] T018 [P] [US1] `DashboardEstrategico.vue` con la fecha de última actualización junto a los valores y los KPIs no disponibles atenuados (Principio XII).

## Phase 4: User Story 2 - Dashboards tácticos por departamento (P2)

### Tests

- [X] T019 [P] [US2] Contract test `GET /api/ti/dashboards/tactico/{modulo_nombre}` (200 filtrado a la dimensión; 404 módulo desconocido / sin publicación).
- [X] T020 [US2] Integration test: `Jefe_Comercial` no lee `Finanzas` (403); `Gerente_General` sí (200).
- [X] T021 [US2] Integration test: un KPI `disponible: false` convive con los que sí tienen valor en el mismo módulo.

### Implementation

- [X] T022 [US2] `TiDashboardsRepository` / `TiDashboardsService` con el filtro de alcance por módulo propio del rol autenticado.
- [X] T023 [US2] `GET /api/ti/dashboards/tactico/{modulo_nombre}` (contracts #2) + dependencia RBAC dinámica `_puede_ver_tactico`.
- [X] T024 [US2] Job `publicar_dashboards_tacticos.py`: una corrida por cada uno de los 6 módulos, cada una con su fila en `registro_publicacion_dashboard`.
- [X] T025 [P] [US2] `DashboardTactico.vue`, un componente para los 6 roles, parametrizado por su módulo.

## Phase 5: User Story 3 - Verificación de disponibilidad de dashboards operativos (P3)

### Tests

- [X] T026 [P] [US3] Contract test `GET /api/ti/dashboards/operativos/verificacion` (200 con estado por tienda/dashboard).
- [X] T027 [P] [US3] Contract test `GET /api/ti/dashboards/operativos/alertas` (200, solo filas `disponible: false`).
- [X] T028 [US3] Integration test: un dashboard operativo con más de un día de antigüedad aparece señalado y en las alertas.

### Implementation

- [X] T029 [US3] Job `verificar_dashboards_operativos.py`: `MAX(fecha_hora)` por tienda contra cada tabla fuente (T011), inserta `dashboard_operativo_estado` + una fila `registro_publicacion_dashboard` (`tipo_dashboard='operativo'`).
- [X] T030 [US3] `GET /api/ti/dashboards/operativos/verificacion` y `.../alertas` (contracts #3, #4).
- [X] T031 [P] [US3] `VerificacionDashboardsOperativos.vue` con las filas no disponibles resaltadas y filtro "sólo alertas".

## Phase 6: Polish

- [X] T032 Trigger manual de desarrollo `POST /api/ti/dashboards/{tipo}/forzar-publicacion` (contracts #5, FR-010) — sólo se monta cuando `app_env != "production"`.
- [X] T033 [P] Trazabilidad FR → test: FR-001/002/003/008 (contract+integration US1), FR-004/005 (US2), FR-006/007 (US3), FR-009 (job batch nocturno, snapshot pequeño — sin degradar OLTP), FR-010 (`test_forzar_publicacion_rbac_403_cajero` + los `_forzar` de cada test).
- [X] T034 [P] Ningún endpoint de lectura consulta ClickHouse: los repos sólo usan `RegistroPublicacionDashboard` / `DashboardKpi` / `DashboardOperativoEstado` (PostgreSQL). Sólo los jobs tocarían ClickHouse en producción (Principio III).
- [X] T035 Escenarios de quickstart.md cubiertos por los tests de integración (US1 esc. 1-3, US2 esc. 1-4, US3 esc. 1-2, FR-010 esc. 1).
- [X] T036 Constitution Check re-verificada: sin violaciones nuevas — 3 tablas nuevas justificadas, RBAC de dos niveles, backend/frontend desacoplados, KPIs no recalculados (OE-4 explícitamente no disponible).

## Dependencias clave

- Foundational (T006-T011) bloquea las tres historias de usuario.
- US1 (P1) es el MVP y es independiente de US2/US3.
- US2 (P2) es independiente de US1/US3 — su único requisito común es Foundational.
- US3 (P3) es independiente de US1/US2 en código, aunque conceptualmente se apoya en que 001-007 ya tengan datos operativos reales (ya cerradas, siempre cierto).
- Esta feature completa permanece en espera de producción hasta que 010-plataforma-datos-tactico-estrategico esté implementada (jobs T017/T024/T029 dependen de ClickHouse/Airflow reales); todo lo demás puede desarrollarse y probarse con fixtures desde ahora.
