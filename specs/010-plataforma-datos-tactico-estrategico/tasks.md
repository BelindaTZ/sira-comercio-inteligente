# Tasks: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico | **Input**: plan.md, research.md, data-model.md, contracts/plataforma-datos.md, quickstart.md

**Estado**: implementada (`/speckit-implement`, 2026-09-07). Se desarrolló y probó con
PostgreSQL/MinIO reales y dobles en memoria para ClickHouse/Airflow — el contrato de
idempotencia/exclusión mutua no depende del volumen de producción (quickstart.md).

**Ronda 1 (post-implementación) — sin cambio de alcance ni de FR**:
- módulo backend plano `backend/src/modules/plataforma_datos/` (no anidado bajo `ti/`) — mismo patrón que 002-012
- `frontend/src/services/plataformaDatosApi.js` + `frontend/src/modules/plataforma-datos/pages/` (sin Pinia/TypeScript)
- base path real `/api/plataforma-datos`; formato de error del proyecto `{"error": {...}}` (el contrato decía `/api/v1/ti/plataforma-datos` y `{"detail": ...}`)
- migración Alembic `0018` (sobre 0017 de la feature 012, no `0011`)
- el orquestador de una corrida es único y compartido entre el DAG y el endpoint dev (`data_platform/dags/dags_utils/pipeline.py`)

**Tests**: contract e integration antes de la implementación (Principio X); los tests de idempotencia y exclusión mutua (T021, T022) son los más críticos de esta feature.

## Phase 1: Setup

- [X] T001 Crear rama `010-plataforma-datos-tactico-estrategico` y confirmar que `.specify/feature.json` apunta a esta feature.
- [X] T002 [P] Crear paquete `backend/src/modules/plataforma_datos/` (router, service, repository, schemas). *(Ronda 1: módulo plano.)*
- [X] T003 [P] Crear `data_platform/dags/` y `data_platform/clickhouse/` (estructura de infraestructura ELT). Extender el `docker-compose.yml` de 001 con los servicios `clickhouse` y `airflow` bajo el perfil `data` (`docker compose --profile data up -d`) — credenciales de desarrollo fijadas en el propio compose, `CLICKHOUSE_URL` ya reservado en `backend/.env`. Notas de arranque: (a) Airflow lleva su metadata en una base `airflow` APARTE de `sira` — `data_platform/postgres-init/` la crea en un volumen nuevo, `docker compose exec postgres createdb -U sira airflow` en uno existente; (b) `_PIP_ADDITIONAL_REQUIREMENTS` no fuerza SQLAlchemy 2.0 (Airflow 2.9 fija 1.4.x, que ya trae `ext.asyncio`); (c) `.airflowignore` excluye `dags_utils/` del parser de DAGs. Verificado end-to-end: Extract PostgreSQL → landing-zone MinIO → ClickHouse `ReplacingMergeTree` → `corrida_carga` exitosa.
- [X] T004 [P] Crear stubs de tests `backend/tests/contract/test_plataforma_datos.py` y `backend/tests/integration/test_idempotencia_carga.py`.
- [X] T005 [P] Crear componentes frontend: `ModeloDatosWarehousePage.vue`, `MonitoreoCorridasPage.vue`, `PoliticaGobiernoDatosPage.vue` + `plataformaDatosApi.js` + 3 rutas.

## Phase 2: Foundational (bloqueante para todas las historias)

- [X] T006 Migración Alembic `0018`: crear `modelo_datos_warehouse` (data-model.md).
- [X] T007 Migración Alembic `0018`: crear `corrida_carga` con el índice único parcial de exclusión mutua (`uq_corrida_carga_en_progreso`) y el índice de listado.
- [X] T008 Migración Alembic `0018`: crear `registro_calidad_carga`.
- [X] T009 Migración Alembic `0018`: crear `politica_gobierno_datos`.
- [X] T010 Seed: `role_permisos_tabla` para las 4 tablas nuevas bajo el módulo `TI` ya reservado, para `Jefe_TI` (data-model.md §RBAC) — en la migración `0018` y en el bloque EXTENSIÓN de `01_operativo_postgres.sql`.
- [X] T011 [P] Schemas Pydantic base (`EntidadModeloOut`/`Create`/`Patch`, `CorridaOut`, `RegistroCalidadOut`, `PoliticaOut`, `ForzarCorrida*`) en `schemas.py`.
- [X] T012 DDL de ClickHouse (`data_platform/clickhouse/schema_warehouse.sql`): `fact_venta` + `dim_cliente`/`dim_producto`/`dim_tienda`/`dim_caja`/`dim_empleado`, motor `ReplacingMergeTree` (research.md Decisión 3).

**Checkpoint**: catálogo de modelo y tablas de control listas — cualquier historia de usuario puede implementarse desde aquí.

## Phase 3: User Story 1 - Definición del modelo de datos único del warehouse (P1) 🎯 MVP

### Tests

- [X] T013 [P] [US1] Contract test `GET /modelo` y `POST /modelo` (201 en alta, entidad con `activa: true` por defecto) + 409 en nombre duplicado.
- [X] T014 [P] [US1] Contract test `PATCH /modelo/{entidad_id}` (activar/desactivar).
- [X] T015 [US1] Integration test: una entidad `activa = false` no aparece en la lista de entidades que el DAG carga (Edge Case, Acceptance Scenario 2).

### Implementation

- [X] T016 [US1] `repository.py`/`service.py` de alta y consulta de `modelo_datos_warehouse`.
- [X] T017 [US1] `GET /modelo`, `POST /modelo`, `PATCH /modelo/{entidad_id}` (contracts #1).
- [X] T018 [P] [US1] `ModeloDatosWarehousePage.vue` (listado + alta + activar/desactivar para Jefe_TI).

**Checkpoint**: US1 funciona de forma independiente — MVP entregable.

## Phase 4: User Story 2 - Carga diaria automática desde el operativo hacia el warehouse (P2)

### Tests

- [X] T019 [US2] Integration test: carga base (`tipo_carga='completa'`) sobre `fact_venta` trae el histórico completo sembrado (Acceptance Scenario 1).
- [X] T020 [US2] Integration test: carga incremental posterior trae sólo filas nuevas/modificadas desde la última corrida **exitosa** (research.md Decisión 3, Acceptance Scenario 2).
- [X] T021 [US2] Integration test: reprocesar una corrida (misma ventana) no duplica filas en ClickHouse (`ReplacingMergeTree`, Acceptance Scenario 3) + corrida fallida a medias queda `estado='fallida'`.
- [X] T022 [US2] Integration test: iniciar una segunda corrida sobre una entidad con una corrida `en_progreso` es rechazado por el índice único parcial (`CorridaEnProgresoError`, Acceptance Scenario 4, FR-005).
- [X] T023 [P] [US2] Contract test `GET /corridas` (filtros por `entidad_id`/`estado`; filas cargadas/con error/duración visibles) + 403 sin permiso.

### Implementation

- [X] T024 [US2] `extract_postgres.py` (SELECT por entidad hacia las columnas del schema de ClickHouse; filtro incremental por watermark, `>=` para no perder el borde).
- [X] T025 [US2] `load_landing_zone_minio.py` (raw del Extract a MinIO `landing-zone`, Principio III).
- [X] T026 [US2] `load_clickhouse.py` (INSERT a `ReplacingMergeTree` + 2 reglas de calidad) y `transform_in_warehouse.py` (`OPTIMIZE ... FINAL`). Orquestación en `pipeline.py`.
- [X] T027 [US2] DAG `carga_diaria_warehouse.py`: un task por entidad `activa`, cada uno abriendo/cerrando su propia fila de `corrida_carga` vía `pipeline.correr_carga`.
- [X] T028 [US2] `GET /corridas` (contracts #2) + `repository.listar_corridas` con la duración derivada.
- [X] T029 [P] [US2] `MonitoreoCorridasPage.vue` para Jefe_TI (+ botón "forzar corrida" sólo en `import.meta.env.DEV`).

**Checkpoint**: US2 funciona sobre la base de US1 — el warehouse se puebla de forma automática, idempotente y sin corridas concurrentes sobre el mismo destino.

## Phase 5: User Story 3 - Calidad y trazabilidad de la carga de datos (P3)

### Tests

- [X] T030 [P] [US3] Integration test: un lote con una fila de referencia rota carga el resto con normalidad y señala esa fila en `registro_calidad_carga` (Acceptance Scenario 1).
- [X] T031 [P] [US3] Contract test `GET /corridas/{corrida_id}/calidad` (200 + forma; 404 si la corrida no existe).
- [X] T032 [US3] Cubierto por T030 + T023: origen/destino/filas/resultado de una corrida consultables sin logs de Airflow (SC-004).

### Implementation

- [X] T033 [US3] Las dos reglas mínimas de calidad (referencias rotas, campos obligatorios vacíos) dentro de `load_clickhouse.cargar`, insertando en `registro_calidad_carga` vía `pipeline`, sin detener el resto del lote (research.md Decisión 4).
- [X] T034 [US3] `GET /corridas/{corrida_id}/calidad` (contracts #3).

**Checkpoint**: la trazabilidad de OO-7.5.1 queda completa — origen, destino, filas, resultado y registros de calidad, todo consultable sin Airflow.

## Phase 6: User Story 4 - Política de gobierno de datos como documento de referencia (P4)

### Tests

- [X] T035 [P] [US4] Contract test `POST /politica`, `GET /politica`, `GET /politica/historial` (append-only, la vigente es la más reciente; 404 si aún no hay ninguna).

### Implementation

- [X] T036 [US4] `repository.py`/`service.py` de alta y consulta de `politica_gobierno_datos` (append-only, research.md Decisión 5).
- [X] T037 [US4] Los 3 endpoints (contracts #4).
- [X] T038 [P] [US4] `PoliticaGobiernoDatosPage.vue` (texto vigente + historial).

**Checkpoint**: las 4 historias de usuario están completas.

## Phase 7: Polish

- [X] T039 `POST /corridas/forzar` (contracts #5, FR-012) montado sólo si `settings.app_env != "production"` (403 en prod por no existir la ruta, mismo patrón que 003-006/009); 409 si ya hay una corrida `en_progreso`, 422 si la entidad está inactiva.
- [X] T040 [P] Trazabilidad de los 12 FR (ver tabla abajo) — cada uno con al menos un test de contrato o integración.
- [X] T041 [P] Revisión dirigida: ningún endpoint de esta feature escribe datos de negocio en ClickHouse desde el camino de request — el módulo backend nunca instancia un cliente de ClickHouse; `forzar_corrida` llama a `pipeline.correr_carga` con `cliente_ch=None` (corrida de control, sin mover datos). El único escritor de ClickHouse es `data_platform/` (Principio III).
- [X] T042 [P] Índices de apoyo creados en `0018` (`uq_corrida_carga_en_progreso`, `idx_corrida_carga_entidad_fecha`, `idx_registro_calidad_carga_corrida`); el listado de corridas filtra por `entidad_id`/`estado` y ordena por `fecha_inicio DESC` — cubierto por el índice compuesto.
- [X] T043 Re-chequeo de la tabla de Constitution Check de plan.md — sigue en PASS (ver plan.md §Constitution Check, nota de ronda 1).

## Trazabilidad FR → test

| FR | Test |
|---|---|
| FR-001 | `test_get_modelo_lista_entidades`, `test_post_modelo_201_activa_por_defecto` |
| FR-002 | `carga_diaria_warehouse` (DAG) + `test_carga_base_completa_trae_historico` |
| FR-003 | `test_carga_base_completa_trae_historico`, `test_incremental_solo_trae_filas_nuevas` |
| FR-004 | `test_reprocesar_no_duplica`, `test_corrida_fallida_queda_registrada` |
| FR-005 | `test_dos_corridas_en_progreso_rechazadas`, `test_forzar_corrida_202_y_409_si_en_progreso` |
| FR-006 | `test_get_corridas_filtros_y_forma` |
| FR-007 | `test_referencia_rota_se_senala_sin_frenar_el_lote`, `test_get_calidad_de_corrida_200` |
| FR-008 | `test_get_corridas_filtros_y_forma`, `test_referencia_rota_se_senala_sin_frenar_el_lote` |
| FR-009 | `test_politica_append_only_vigente_es_la_mas_reciente` |
| FR-010 | `test_politica_append_only_vigente_es_la_mas_reciente` (historial conserva versiones) |
| FR-011 | Principio III — control en PostgreSQL, datos en ClickHouse; `test_*` de `dags_utils` no tocan tablas operativas salvo lectura |
| FR-012 | `test_forzar_corrida_202_y_409_si_en_progreso`, `test_forzar_corrida_entidad_inactiva_422` |

## Dependencias clave

- Foundational (T006-T012) bloquea las cuatro historias de usuario.
- US1 (P1) es el MVP y prerrequisito conceptual de US2 (el DAG necesita el catálogo).
- US2 (P2) depende de US1 y es prerrequisito de US3 (necesita corridas reales).
- US3 (P3) depende de que existan corridas (US2).
- US4 (P4) es independiente en código de US1-US3 — sólo comparte el módulo `TI`.
