# Tasks: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico | **Input**: plan.md, research.md, data-model.md, contracts/plataforma-datos.md, quickstart.md

**Estado**: en espera de implementación (junto con 009) — estas tareas pueden desarrollarse y probarse con ClickHouse/MinIO de desarrollo o mocks; la activación en producción se retoma junto con la capa táctica/estratégica.

**Tests**: contract e integration antes de la implementación (Principio X); los tests de idempotencia y exclusión mutua (T019, T020) son los más críticos de esta feature.

## Phase 1: Setup

- T001 Crear rama `010-plataforma-datos-tactico-estrategico` y confirmar que `.specify/feature.json` apunta a esta feature.
- T002 [P] Crear paquete `backend/modules/ti/plataforma_datos/` (router, service, repository, schemas).
- T003 [P] Crear `data_platform/dags/` y `data_platform/clickhouse/` (estructura de infraestructura ELT, plan.md §Project Structure). Extender el `docker-compose.yml` ya creado en 001 (T005 de esa feature, con `postgres`+`minio`) agregando los servicios `clickhouse` y `airflow` (webserver+scheduler) — sin que el usuario tenga que levantar nada a mano; las credenciales de estos servicios de desarrollo (ej. usuario/password de Airflow, `CLICKHOUSE_URL` local) se fijan o generan dentro del propio `docker-compose.yml`/script de setup, y se replican en `backend/.env` automáticamente — igual que `JWT_SECRET` y las credenciales de MinIO (008 T005), no son credenciales de un tercero.
- T004 [P] Crear stubs de tests `backend/tests/contract/test_plataforma_datos.py` y `backend/tests/integration/test_idempotencia_carga.py`.
- T005 [P] Crear componentes frontend vacíos: `ModeloDatosWarehouse.vue`, `MonitoreoCorridas.vue`, `PoliticaGobiernoDatos.vue`.

## Phase 2: Foundational (bloqueante para todas las historias)

- T006 Migración Alembic: crear `modelo_datos_warehouse` (data-model.md).
- T007 Migración Alembic: crear `corrida_carga` con el índice único parcial de exclusión mutua (`uq_corrida_carga_en_progreso`) y el índice de listado.
- T008 Migración Alembic: crear `registro_calidad_carga`.
- T009 Migración Alembic: crear `politica_gobierno_datos`.
- T010 Seed: agregar filas de `role_permisos_tabla` para las 4 tablas nuevas bajo el módulo `TI` ya reservado, para `Jefe_TI` (data-model.md §RBAC).
- T011 [P] Definir schemas Pydantic base (`EntidadModeloOut`, `CorridaCargaOut`, `RegistroCalidadOut`, `PoliticaOut`) en `schemas.py`.
- T012 Definir el DDL inicial de ClickHouse (`data_platform/clickhouse/schema_warehouse.sql`): `fact_venta` + `dim_cliente`, `dim_producto`, `dim_tienda`, `dim_caja`, `dim_empleado`, motor `ReplacingMergeTree` (research.md Decisión 3).

**Checkpoint**: catálogo de modelo y tablas de control listas — cualquier historia de usuario puede implementarse desde aquí.

## Phase 3: User Story 1 - Definición del modelo de datos único del warehouse (P1) 🎯 MVP

### Tests

- T013 [P] [US1] Contract test `GET /modelo` y `POST /modelo` (201 en alta, entidad con `activa: true` por defecto).
- T014 [P] [US1] Contract test `PATCH /modelo/{entidad_id}` (activar/desactivar).
- T015 [US1] Integration test: una entidad registrada con `activa: false` no genera task en el DAG (Edge Case, Acceptance Scenario 2).

### Implementation

- T016 [US1] Implementar `repository.py`/`service.py` de alta y consulta de `modelo_datos_warehouse`.
- T017 [US1] Implementar `GET /modelo`, `POST /modelo`, `PATCH /modelo/{entidad_id}` (contracts #1).
- T018 [P] [US1] Componente `ModeloDatosWarehouse.vue` (listado + alta/edición para Jefe_TI).

**Checkpoint**: US1 funciona de forma independiente — MVP entregable (el modelo puede documentarse aun antes de que el DAG esté implementado).

## Phase 4: User Story 2 - Carga diaria automática desde el operativo hacia el warehouse (P2)

### Tests

- T019 [US2] Integration test: carga base (`tipo_carga='completa'`) sobre `fact_venta` trae el histórico completo ya sembrado (Acceptance Scenario 1).
- T020 [US2] Integration test: carga incremental posterior trae solo filas nuevas/modificadas desde la última corrida **exitosa** (research.md Decisión 3, Acceptance Scenario 2).
- T021 [US2] Integration test: reprocesar una corrida fallida a medias no duplica filas ya cargadas (idempotencia vía `ReplacingMergeTree`, Acceptance Scenario 3).
- T022 [US2] Integration test: iniciar una segunda corrida sobre una entidad con una corrida `en_progreso` es rechazado por el índice único parcial (Acceptance Scenario 4, FR-005).
- T023 [P] [US2] Contract test `GET /corridas` (filtros por `entidad_id`/`estado`, filas cargadas/con error/duración visibles).

### Implementation

- T024 [US2] Implementar `extract_postgres.py` (lectura de la tabla origen por entidad, con filtro incremental por fecha de modificación).
- T025 [US2] Implementar `load_landing_zone_minio.py` (raw del Extract a MinIO `landing-zone`, Principio III).
- T026 [US2] Implementar `load_clickhouse.py` (carga a ClickHouse vía `ReplacingMergeTree`) y `transform_in_warehouse.py` (transformaciones in-warehouse).
- T027 [US2] Implementar el DAG `carga_diaria_warehouse.py`: un task por entidad `activa` de `modelo_datos_warehouse`, cada uno abriendo/cerrando su propia fila de `corrida_carga`.
- T028 [US2] Implementar `GET /corridas` (contracts #2) y la lógica de `repository.py` correspondiente.
- T029 [P] [US2] Componente `MonitoreoCorridas.vue` para Jefe_TI.

**Checkpoint**: US2 funciona sobre la base de US1 — el warehouse se puebla de forma automática, idempotente y sin corridas concurrentes sobre el mismo destino.

## Phase 5: User Story 3 - Calidad y trazabilidad de la carga de datos (P3)

### Tests

- T030 [P] [US3] Integration test: un lote con un registro que rompe una regla de calidad (referencia rota) carga el resto con normalidad y señala el registro aparte (Acceptance Scenario 1).
- T031 [P] [US3] Contract test `GET /corridas/{corrida_id}/calidad`.
- T032 [US3] Integration test: el Jefe de TI consulta origen/destino/filas/resultado de una corrida sin depender de logs de Airflow (Acceptance Scenario 2, SC-004).

### Implementation

- T033 [US3] Implementar las dos reglas mínimas de calidad (referencias rotas, campos obligatorios vacíos) dentro de `load_clickhouse.py`, insertando en `registro_calidad_carga` cuando fallan, sin detener el resto del lote (research.md Decisión 4).
- T034 [US3] Implementar `GET /corridas/{corrida_id}/calidad` (contracts #3).

**Checkpoint**: la trazabilidad de OO-7.5.1 queda completa — origen, destino, filas, resultado y registros de calidad, todo consultable sin Airflow.

## Phase 6: User Story 4 - Política de gobierno de datos como documento de referencia (P4)

### Tests

- T035 [P] [US4] Contract test `POST /politica`, `GET /politica`, `GET /politica/historial` (append-only, la vigente es la más reciente).

### Implementation

- T036 [US4] Implementar `repository.py`/`service.py` de alta y consulta de `politica_gobierno_datos` (append-only, research.md Decisión 5).
- T037 [US4] Implementar los 3 endpoints (contracts #4).
- T038 [P] [US4] Componente `PoliticaGobiernoDatos.vue` (texto vigente + historial).

**Checkpoint**: las 4 historias de usuario están completas — la plataforma de datos queda lista para que 009 (y opcionalmente 004) la consuman en cuanto se retome la capa táctica/estratégica.

## Phase 7: Polish

- T039 Implementar el trigger manual de desarrollo `POST /corridas/forzar` (contracts #5, FR-012) y su bloqueo en producción.
- T040 [P] Revisar que los 12 FR de spec.md tengan al menos un test de contrato o integración que los cubra (tabla de trazabilidad, data-model.md).
- T041 [P] Confirmar que ningún endpoint de esta feature ni de 009 escribe datos de negocio en ClickHouse desde el camino de request de un usuario final (Principio III) — revisión de código dirigida.
- T042 Ejecutar quickstart.md end-to-end (4 escenarios) contra un entorno de desarrollo con ClickHouse/MinIO/Airflow reales o mocks equivalentes.
- T043 Re-chequeo de la tabla de Constitution Check de plan.md tras la implementación completa.

## Dependencias clave

- Foundational (T006-T012) bloquea las cuatro historias de usuario.
- US1 (P1) es el MVP y es prerrequisito conceptual de US2 (el DAG necesita el catálogo para saber qué cargar), aunque su código no depende del de US2.
- US2 (P2) depende de US1 (catálogo) y es prerrequisito de US3 (necesita corridas reales sobre las cuales aplicar reglas de calidad).
- US3 (P3) depende de que existan corridas (US2) para tener datos que auditar.
- US4 (P4) es independiente en código de US1-US3 — solo comparte el módulo `TI`.
- Esta feature y 009-dashboards-multinivel permanecen en espera de producción hasta retomar la capa táctica/estratégica (constitution.md); todo lo demás puede desarrollarse y probarse desde ahora con fixtures/mocks.
