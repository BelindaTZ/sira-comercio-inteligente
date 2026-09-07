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

- [X] T001 Agregar `APScheduler` a `backend/pyproject.toml`; crear `backend/src/jobs/__init__.py` (el resto del stack ya está inicializado desde 001, no se repite)
- [X] T002 [P] Migración Alembic con las extensiones de esta feature: `clientes.consentimiento_datos`/`fecha_consentimiento_datos`, `churn_score.severidad`, `campanas.categoria_sira`, `campana_cliente.grupo`, tabla `campana_resultado`, tabla `cupon_enviado`, secuencia `campanas_campaign_id_seq`

---

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [X] T003 [P] Modelos SQLAlchemy nuevos/extendidos en `backend/src/models/`: `cliente.py` (extender), `cliente_demografico.py`, `nivel_fidelizacion.py`, `cliente_clv.py`, `churn_score.py` (extender), `campana.py` (extender), `campana_cliente.py` (extender), `campana_resultado.py`, `cupon.py`, `cupon_enviado.py`, `cupon_redimido.py`, `evento_cliente.py`
- [X] T004 Configurar `APScheduler` en `backend/src/jobs/scheduler.py`: registra el job semanal (CLV/churn) y el diario (hitos), arranque/apagado en el ciclo de vida de FastAPI (`backend/src/main.py`) — research.md §3
- [X] T005 [P] Endpoint interno solo-desarrollo para forzar manualmente cada job (usado por `quickstart.md`, no expuesto en producción)
- [X] T006 Montar el router del módulo `clientes` en `backend/src/main.py`

**Checkpoint**: ✅ infraestructura lista — las user stories pueden empezar. 89 tests de 001 siguen verdes.

> **Notas de implementación (Fases 1-2 — feature 002, 2026-09-06)**
> - Rama `002-clientes-fidelizacion` (creada desde `main` tras mergear 001).
> - **T001** — `apscheduler>=3.10` añadido a `pyproject.toml` (instalado 3.11.3); `src/jobs/`.
> - **T002** — migración `0006` idempotente. Las extensiones de 002 ya estaban en el DB
>   (la migración `0001` reproduce `01_operativo_postgres.sql` completo, que ya contiene
>   los bloques "EXTENSIÓN — Feature 002" rondas 1-2). `0006` las aplica sobre un DB que
>   se quedó en `0005` sin ellas (`ADD COLUMN IF NOT EXISTS`, `CREATE TABLE IF NOT EXISTS`,
>   `DO $$ EXCEPTION` para constraints) — en este DB es no-op. Añade RBAC de Jefe_Marketing
>   sobre `cliente_clv`, `churn_score`, `campana_resultado`, `cupon_enviado`, `clientes_demograficos`.
> - **T003** — 12 modelos nuevos en `src/models/` (36 tablas mapeadas en total). Los que
>   tasks.md marca "extender" no existían (001 solo mapeó sus tablas): se crean con las
>   columnas de la ronda 1-2 ya incluidas. FK a `empleados` como `Integer` (misma convención
>   que 001 para tablas de la feature 008). `campanas.campaign_id` con sequence START 100000.
> - **T004** — `src/jobs/scheduler.py` (`AsyncIOScheduler`, UTC): job `clv_churn_semanal`
>   (lunes 03:00) y `eventos_hito_diario` (06:00), arranque/apagado en el `lifespan` de
>   FastAPI. No arranca en `APP_ENV=test`. Los jobs abren su propia sesión y hacen `commit`.
> - **T005** — `POST /api/_dev/jobs/{nombre}` y `GET /api/_dev/jobs` (solo si `APP_ENV != production`).
> - **T006** — `src/modules/clientes/` (router/repository/service esqueleto) montado en `main.py`.
>   El **gating de consentimiento** (FR-001) ya vive en `ClientesRepository.household_ids_elegibles`
>   (activo + `consentimiento_datos = true`); los servicios de CLV/churn/campañas lo consumen.
> - Los dos jobs corren de punta a punta (stub: devuelven contadores en 0 — el cálculo real
>   es US2/US3/US4).

---

## Phase 3: User Story 1 - Registrar y mantener el perfil del cliente (Priority: P1) 🎯 MVP

**Goal**: alta de cliente con captura de consentimiento de tratamiento de datos, actualización sin perder historial, baja con anonimización real.

**Independent Test**: Escenarios 1-2 de `quickstart.md` (consentimiento rechazado, baja con anonimización).

### Tests para User Story 1 ⚠️

- [X] T007 [P] [US1] Contract test `POST /api/clientes` (rechaza email duplicado; acepta `consentimiento_datos: false` sin bloquear el alta; acepta `documento_identidad` opcional y rechaza 409 si ya existe cuando se proporciona, Ronda 5; acepta `datos_demograficos` opcional sin exigirlos en el alta — **FR-004**) en `backend/tests/contract/test_clientes_alta.py`
- [X] T051 [P] [US1] Contract test `GET /api/clientes?search=` localiza un cliente por `documento_identidad` igual que por nombre/email (Ronda 5) en `backend/tests/contract/test_clientes_busqueda_documento.py`
- [X] T008 [P] [US1] Contract test `PATCH /api/clientes/{id}` (no altera CLV/churn previos; revocar `consentimiento_datos` no anonimiza nada; agrega `datos_demograficos` opcionales después del alta — **FR-004**) en `backend/tests/contract/test_clientes_actualizar.py`
- [X] T009 [P] [US1] Contract test `DELETE /api/clientes/{id}` (verifica anonimización real de nombre/email/teléfono/fecha_nacimiento, `household_id` intacto) en `backend/tests/contract/test_clientes_baja.py`
- [X] T010 [P] [US1] Unit test del gating de consentimiento: un cliente con `consentimiento_datos=false` nunca aparece en el resultado del repository de CLV/churn/campañas en `backend/tests/unit/test_gating_consentimiento.py` (Principio X)
- [X] T011 [US1] Integration test Escenarios 1 y 2 de `quickstart.md` en `backend/tests/integration/test_us1_perfil_cliente.py`

### Implementación de User Story 1

- [X] T052 [US1] Migración Alembic (extiende la 0006, idempotente): `clientes.documento_identidad VARCHAR(13)` NULLABLE + índice único parcial `WHERE documento_identidad IS NOT NULL` en `backend/alembic/versions/`, reflejado en `01_operativo_postgres.sql` (Ronda 5, research.md §6)
- [X] T012 [US1] `ClientesRepository` (CRUD + filtro `consentimiento_datos=true` reutilizable por los jobs; `search` compara contra `nombre`/`email`/`documento_identidad`, Ronda 5) en `backend/src/modules/clientes/repository.py` (depende de T003, T052)
- [X] T013 [US1] `ClientesService.registrar_cliente` — captura consentimiento + fecha, valida email único y `documento_identidad` único cuando se proporciona (FR-001, Ronda 5) en `backend/src/modules/clientes/service.py`
- [X] T014 [US1] `ClientesService.actualizar_cliente` — incluye revocar/otorgar `consentimiento_datos` (actualiza `fecha_consentimiento_datos`, sin anonimizar) (FR-002) en `backend/src/modules/clientes/service.py`
- [X] T015 [US1] `ClientesService.dar_de_baja` — UPDATE de anonimización real, conserva `household_id` (FR-003, research.md §5) en `backend/src/modules/clientes/service.py`
- [X] T016 [P] [US1] Endpoints REST de perfil (`POST`/`PATCH`/`DELETE`/`GET /api/clientes`, incluye `documento_identidad` en body y en `search`) según `contracts/clientes.md` en `backend/src/modules/clientes/router.py` (depende de T013-T015)
- [X] T017 [P] [US1] Frontend: `ClientesPage.vue`, `FormularioCliente.vue` (captura el consentimiento en el alta y permite revocarlo/otorgarlo después desde el mismo formulario de edición; campo `documento_identidad` opcional en el alta/edición, Ronda 5) en `frontend/src/modules/clientes/`
- [X] T053 [US1] Frontend: `BuscadorCliente.vue` (busca por nombre/email/cédula vía `GET /api/clientes?search=` y vincula `household_id` a la venta en curso) integrado en `PuntoDeVentaPage.vue` de 001 — FR-008 de 001 dejó `household_id?` opcional en `POST /api/ventas` desde el inicio, pero nunca tuvo UI propia porque 002 (dueña de la búsqueda) todavía no existía cuando se implementó 001; se cierra aquí, no reabre 001 (Ronda 5) en `frontend/src/modules/pos/`
- [X] T018 [P] [US1] Frontend: `clientesApi.js` (capa de servicio centralizada, Principio XI) en `frontend/src/services/`

**Checkpoint**: ✅ US1 entregable de forma independiente — alta/actualización/baja de cliente de punta a punta. **110 tests verdes** (89 de 001 + 21 de US1).

> **Notas de implementación (Fase 3 — US1, 2026-09-06)**
> - **Ronda 5 del esquema** (`01_operativo_postgres.sql` + migración `0007`, idempotente):
>   `clientes.documento_identidad VARCHAR(13)` con índice único parcial
>   `WHERE documento_identidad IS NOT NULL`; `clientes.household_id` gana
>   `DEFAULT nextval('clientes_household_id_seq')` (START 900000, sobre el máx. sembrado 2500);
>   RBAC del módulo `Marketing_CRM` para `Cajero`/`Encargado_Tienda` sobre `clientes`/
>   `clientes_demograficos` (Cajero S+I+U; Encargado y Jefe_Marketing +D para la baja).
> - **Alta** (FR-001): consentimiento obligatorio en el body (sin default de aplicación);
>   409 si el email ya existe o si `documento_identidad` ya existe cuando se proporciona.
>   `consentimiento_datos = false` NO bloquea el alta.
> - **Edición** (FR-002): revocar/otorgar `consentimiento_datos` actualiza `fecha_consentimiento_datos`
>   y cambia el gating hacia adelante — sin anonimizar nada. No toca CLV/churn previos.
> - **Baja** (FR-003, research §5): UPDATE de anonimización real — `nombre='CLIENTE ANONIMIZADO'`,
>   `email='anon-{hid}@anonimizado.local'`, `telefono`/`fecha_nacimiento`/`documento_identidad` a NULL,
>   `activo=false`; `household_id` intacto. Nunca DELETE físico.
> - **Búsqueda** (Ronda 5): `GET /api/clientes?search=` compara contra nombre/email/documento_identidad
>   con `ilike`. `GET` devuelve el último `clv_score`/nivel/`severidad` por join contra
>   `cliente_clv`/`churn_score`.
> - **Gating de consentimiento** (Principio X): `ClientesRepository.household_ids_elegibles` /
>   `es_elegible` — `activo AND consentimiento_datos`; los jobs y (a futuro) los servicios de
>   CLV/churn/campañas parten de ahí. Cubierto por `tests/unit/test_gating_consentimiento.py`.
> - **Frontend** (T017/T018/T053): `/clientes` (`ClientesPage.vue` + `FormularioCliente.vue`,
>   captura/revoca consentimiento) y `clientesApi.js`. `BuscadorCliente.vue` integrado en el
>   Punto de Venta (`PuntoDeVentaPage.vue`) para vincular `household_id` a la venta — FR-008 de
>   001 ya lo aceptaba opcional, aquí se le da UI sin reabrir 001.
> - **FR-004** (datos demográficos opcionales): `DatosDemograficosIn`/`Out` en `schemas.py`,
>   `ClientesService._upsert_demografico` (upsert 1:1 sobre `clientes_demograficos`) — se pueden
>   dar en el alta (`POST`, campo `datos_demograficos`) o agregar/editar después (`PATCH`), nunca
>   obligatorios. Cubierto por `test_clientes_alta.py::test_alta_con_datos_demograficos` +
>   `test_clientes_actualizar.py::test_patch_agrega_datos_demograficos` (y `test_alta_basica`
>   prueba que el alta funciona sin ellos).

---

## Phase 4: User Story 2 - Calcular CLV compuesto y niveles de fidelización (Priority: P2)

**Goal**: CLV semanal que combina frecuencia y margen real (nunca gasto bruto), con reclasificación automática de nivel.

**Independent Test**: Escenario 3 de `quickstart.md`.

### Tests para User Story 2 ⚠️

- [X] T019 [P] [US2] Unit test de la fórmula de CLV: verifica que un cliente de compra frecuente/margen bajo y otro de compra única/margen alto no se ordenan solo por gasto acumulado en `backend/tests/unit/test_calculo_clv.py` (FR-005, Principio X)
- [X] T020 [P] [US2] Contract test `GET`/`PATCH /api/clientes/niveles-fidelizacion` en `backend/tests/contract/test_niveles_fidelizacion.py`
- [X] T021 [US2] Integration test Escenario 3 de `quickstart.md` en `backend/tests/integration/test_us2_clv.py`

### Implementación de User Story 2

- [X] T022 [US2] Job semanal `calcular_clv_job.py` — implementa la fórmula de `research.md` §1 (ventana 180 días, normalización percentil 95, gating de consentimiento) en `backend/src/jobs/`
- [X] T023 [US2] `ClientesService.reclasificar_nivel` — compara `clv_score` contra umbrales vigentes (FR-006, FR-008) en `backend/src/modules/clientes/service.py`
- [X] T024 [US2] Endpoints `GET`/`PATCH /api/clientes/niveles-fidelizacion` (FR-007) en `backend/src/modules/clientes/router.py`
- [X] T025 [P] [US2] Frontend: mostrar CLV/nivel actual en el detalle de `ClientesPage.vue`

**Checkpoint**: ✅ US2 entregable sobre US1 — CLV compuesto + niveles funcionando. **120 tests verdes**.

> **Notas de implementación (Fase 4 — US2, 2026-09-07)**
> - **Ronda 6 del esquema** (`01_operativo_postgres.sql` + migración `0008`, idempotente):
>   seed de `niveles_fidelizacion` — Bronce 0.00 / Plata 0.40 / Oro 0.70 / Platino 0.90
>   (el CLV es score 0..1; el Jefe de Marketing ajusta los umbrales vía `PATCH`, FR-007).
> - **CLV compuesto** (`src/shared/clv.py`, T019): `0.5·frecuencia_norm + 0.5·margen_norm`
>   sobre ventana de 180 días; cada componente normalizado contra el **percentil 95**
>   (interpolación lineal), truncado a 1.0. Margen real = Σ (`sales_value − productos.costo`)·
>   `cantidad` por línea de venta `confirmada`. Nunca es sólo el gasto bruto — verificado
>   con un test donde un cliente frecuente/margen-bajo empata con uno de compra única/
>   margen-alto (`tests/unit/test_calculo_clv.py`).
> - **Reclasificación de nivel** (T023, FR-006/FR-008): `nivel_para_score` asigna el nivel
>   más alto cuyo `umbral_clv_min ≤ score`; se aplica al insertar cada `cliente_clv` (upsert
>   por `household_id, fecha_calculo` — nunca sobrescribe otra fecha, Principio II).
> - **Job semanal** (T022): el CLV real vive en `ClientesService.recalcular_clv`, orquestado
>   por `recalcular_clv_churn` (churn sigue esqueleto US3). Se consolidó en la capa de
>   servicio + un solo job del scheduler (research §3) en vez de los archivos separados
>   `calcular_clv_job.py`/`calcular_churn_job.py` que sugería tasks.md.
> - **`/api/_dev/jobs/{nombre}`** ahora corre sobre la sesión del request (`Depends(get_session)`)
>   — así los tests de integración fuerzan el job y ven su propio dato bajo el savepoint.
> - **Endpoints** (T024): `GET /api/clientes/niveles-fidelizacion` (cualquier rol con `select`)
>   y `PATCH .../{nivel_id}` (Jefe_Marketing, `require_permission(..., "niveles_fidelizacion", "update")`).
> - **Frontend** (T025): columna "Nivel" + tarjeta de fidelización (CLV / nivel / severidad)
>   en el detalle de `ClientesPage.vue`; `clientesApi.niveles()`.

---

## Phase 5: User Story 3 - Detectar riesgo de fuga con severidad (Priority: P3)

**Goal**: ciclo de compra individual por cliente, con dos niveles de severidad (`en_riesgo`/`inactivo`), nunca un umbral fijo de días.

**Independent Test**: Escenario 4 de `quickstart.md`.

### Tests para User Story 3 ⚠️

- [X] T026 [P] [US3] Unit test de ciclo de compra individual + clasificación de severidad (1.5x/3x sobre el ciclo propio, nunca un umbral fijo de días) en `backend/tests/unit/test_calculo_churn.py` (FR-009, FR-010, Principio X)
- [X] T027 [P] [US3] Contract test `GET /api/clientes/riesgo-fuga?severidad=` en `backend/tests/contract/test_riesgo_fuga.py`
- [X] T028 [US3] Integration test Escenario 4 de `quickstart.md` en `backend/tests/integration/test_us3_churn.py`

### Implementación de User Story 3

- [X] T029 [US3] Job semanal `calcular_churn_job.py` — ciclo individual + severidad (research.md §2, gating de consentimiento) en `backend/src/jobs/`
- [X] T030 [US3] Endpoint `GET /api/clientes/riesgo-fuga` (filtro por severidad, paginado, sin cálculo manual — SC-005) en `backend/src/modules/clientes/router.py` (FR-011)
- [X] T031 [P] [US3] Frontend: `RiesgoFugaPage.vue`, `TablaClientesRiesgo.vue` (filtro reactivo por severidad) en `frontend/src/modules/clientes/`

**Checkpoint**: US3 entregable de forma independiente sobre US1 (no depende de US2). ✅

> **Notas de implementación (US3 — riesgo de fuga con severidad)**
> - **Lógica pura** (T026): `backend/src/shared/churn.py` — `ciclo_compra_dias(fechas)`
>   (promedio de intervalos entre compras consecutivas sobre las **últimas 10**,
>   requiere ≥2 compras, ignora fechas duplicadas), `severidad(dias, ciclo)`
>   (`en_riesgo` > 1.5×ciclo, `inactivo` > 3×ciclo — siempre relativo al ciclo
>   propio, nunca un umbral fijo de días) y `score_churn(dias, ciclo)` (proxy
>   0..1 que llega a 1.0 en el umbral de `inactivo`). 8 tests unitarios.
> - **Job** (T029): se consolidó en la capa de servicio igual que el CLV de US2 —
>   `ClientesService.recalcular_churn(fecha)` recorre `repo.fechas_compra_por_cliente()`
>   (con gating de consentimiento: `activo AND consentimiento_datos`), calcula
>   ciclo/días/severidad/score y hace `repo.upsert_churn(...)` (ON CONFLICT sobre
>   `household_id, fecha_calculo`). `recalcular_clv_churn` (job `clv_churn_semanal`)
>   ahora encadena CLV + churn y devuelve `clientes_con_churn`/`en_riesgo`/`inactivos`.
>   No se creó `calcular_churn_job.py` aparte (misma decisión de research §3 que en US2).
> - **Endpoint** (T030): `GET /api/clientes/riesgo-fuga?severidad=` — registrado
>   **antes** de `/{household_id}`, `require_permission("Marketing_CRM", "churn_score", "select")`
>   (sólo `Jefe_Marketing` tiene ese permiso de tabla, sembrado en migración 0006).
>   Paginado (`Page[RiesgoFugaOut]`); cada fila trae `ciclo_compra_dias` y
>   `dias_desde_ultima_compra` **ya calculados** por el backend (SC-005). La query
>   toma el `churn_score` más reciente por cliente (subconsulta de `MAX(fecha_calculo)`)
>   y filtra `severidad IS NOT NULL`. Como es multi-columna (`ChurnScore` + nombre +
>   cédula) no pasa por `BaseRepository.paginate` (usa `scalars`): se agregó
>   `repo.riesgo_fuga_pagina(...)` con `count` + `execute` manual.
> - **Frontend** (T031): `frontend/src/modules/clientes/RiesgoFugaPage.vue` (ruta
>   `/clientes/riesgo-fuga`, filtro reactivo por severidad con `watch`) +
>   `components/TablaClientesRiesgo.vue` (sólo presenta lo que el backend calculó).
>   Enlace desde `ClientesPage.vue`. `clientesApi.riesgoFuga({ severidad })`.
> - Suite backend completa: **132 passed** (`black` + `ruff check` limpios).

---

## Phase 6: User Story 4 - Campañas automáticas por hito (Priority: P4)

**Goal**: evento diario de cumpleaños/aniversario con cupón automático por correo, y tasa de redención consultable.

**Independent Test**: Escenario 5 de `quickstart.md`.

### Tests para User Story 4 ⚠️

- [X] T032 [P] [US4] Unit test de selección del producto ancla del cupón (`es_ancla=true`, mayor margen vigente) en `backend/tests/unit/test_seleccion_cupon_hito.py`
- [X] T033 [P] [US4] Contract test `GET /api/clientes/cupones/tasa-redencion` (agrupado por `tipo_evento`) en `backend/tests/contract/test_tasa_redencion.py`
- [X] T034 [US4] Integration test Escenario 5 de `quickstart.md` en `backend/tests/integration/test_us4_cupon_hito.py`

### Implementación de User Story 4

- [X] T035 [US4] Job diario `eventos_hito_job.py` — genera `eventos_cliente` + `cupon_enviado`, dispara SendGrid (reutiliza `sendgrid_client.py` de 001, sin duplicar) (FR-012, FR-013) en `backend/src/jobs/`
- [X] T036 [US4] `ClientesService.registrar_redencion` — `POST /api/clientes/cupones/{upc}/redimir` (FR-015) en `backend/src/modules/clientes/service.py`
- [X] T037 [US4] Endpoint `GET /api/clientes/cupones/tasa-redencion` (FR-014) en `backend/src/modules/clientes/router.py`
- [X] T038 [P] [US4] Frontend: panel de tasa de redención por hito en `frontend/src/modules/clientes/CampanasPage.vue`

**Checkpoint**: US4 entregable de forma independiente sobre US1. ✅

> **Notas de implementación (US4 — campañas automáticas por hito)**
> - **Selección del cupón** (T032): `backend/src/shared/cupon_hito.py` —
>   `seleccionar_producto_ancla(productos)` filtra `es_ancla AND activo` y toma el
>   de **mayor margen vigente** (`precio_base - costo`), con desempate estable por
>   `product_id` menor (dos corridas del job dan el mismo cupón si el catálogo no
>   cambia). 5 tests unitarios.
> - **Job diario** (T035): la lógica vive en `ClientesService.generar_eventos_hito(fecha)`
>   (misma decisión de research §3 que CLV/churn — no un archivo de job con lógica).
>   `repo.clientes_con_hito(hoy)` trae los clientes **elegibles** (activo +
>   consentimiento) cuya `fecha_nacimiento` (→ `cumpleanos`) o `fecha_registro`
>   (→ `aniversario_registro`) cae hoy. Por cada uno: `eventos_cliente` (idempotente
>   vía `evento_existe`), luego un `cupones` (ON CONFLICT DO NOTHING, `coupon_upc =
>   f"HITO{evento_id}"`) sobre una campaña permanente `categoria_sira='hito'`
>   (get-or-create), `cupon_enviado`, y envío best-effort por SendGrid
>   (`entregado=false` si falla — el registro nunca se bloquea, Principio II).
>   Sin producto ancla configurado se genera el evento pero no el cupón.
> - **Redención** (T036): `ClientesService.registrar_redencion(upc, household_id, campaign_id)`
>   inserta `cupon_redimido` (rechaza si el cliente no es elegible). Endpoint
>   `POST /api/clientes/cupones/{coupon_upc}/redimir` (body `{household_id, campaign_id}`),
>   Rol Cajero — `require_permission("Marketing_CRM", "cupon_redimido", "insert")`,
>   sembrado en **migración 0009 / `.sql` ronda 7** (el Cajero ya tenía el módulo).
> - **Tasa de redención** (T037): `GET /api/clientes/cupones/tasa-redencion?tipo_evento=`
>   → `{tipo_evento, enviados, redimidos, tasa}` agrupado por `eventos_cliente.tipo_evento`
>   vía el join `cupon_enviado.evento_id`; redimido = existe `cupon_redimido` con el
>   mismo `coupon_upc`+`household_id` (`COUNT(*) FILTER (WHERE EXISTS ...)`). Rol
>   Jefe_Marketing (`cupon_enviado` select — el Cajero redime pero no ve el reporte).
>   También `GET /api/clientes/{household_id}/eventos` (auditoría, contract de
>   `clientes.md`), registrado antes de `/{household_id}`.
> - **Frontend** (T038): `frontend/src/modules/clientes/CampanasPage.vue` (ruta
>   `/clientes/campanas`, tabla de tasa de redención por hito) + enlace desde
>   `ClientesPage.vue`; `clientesApi.tasaRedencion()` / `clientesApi.eventosCliente()`.
> - Suite backend completa: **141 passed** (`black` + `ruff check` limpios; frontend
>   `eslint` + `prettier` limpios).

---

## Phase 7: User Story 5 - Campañas de reactivación con grupo de control y uplift (Priority: P5)

**Goal**: campaña de reactivación que exige grupo de control antes de enviarse, con uplift real medido al cierre.

**Independent Test**: Escenario 7 de `quickstart.md`.

### Tests para User Story 5 ⚠️

- [X] T039 [P] [US5] Contract test `POST /api/clientes/campanas` + `POST /.../enviar` — 422 si no hay ningún miembro `grupo=control` en `backend/tests/contract/test_campana_reactivacion.py` (FR-017)
- [X] T040 [P] [US5] Unit test de cálculo de uplift: compara `tasa_retorno_tratado` vs `tasa_retorno_control`, nunca solo la tasa de redención en `backend/tests/unit/test_calculo_uplift.py` (FR-018, Principio X)
- [X] T041 [US5] Integration test Escenario 7 de `quickstart.md` en `backend/tests/integration/test_us5_reactivacion.py`

### Implementación de User Story 5

- [X] T042 [US5] `CampanasService.crear_campana_reactivacion` — crea campaña (`campanas_campaign_id_seq`) y miembros con grupo (FR-016) en `backend/src/modules/clientes/campanas_service.py`
- [X] T043 [US5] `CampanasService.enviar` — valida grupo de control, envía solo al grupo tratado (FR-017) en `backend/src/modules/clientes/campanas_service.py` (depende de T042)
- [X] T044 [US5] `CampanasService.cerrar` — calcula tasas de retorno + `uplift`, inserta `campana_resultado` (FR-018) en `backend/src/modules/clientes/campanas_service.py`
- [X] T045 [US5] Endpoint `POST /api/clientes/campanas/{id}/decision` (Jefe_Marketing, FR-019) en `backend/src/modules/clientes/router.py`
- [X] T046 [P] [US5] Frontend: `CampanasPage.vue`, `FormularioCampana.vue` (asignación de grupo tratado/control) en `frontend/src/modules/clientes/`

**Checkpoint**: US5 entregable de forma independiente sobre US3 (consume `riesgo-fuga` para elegir miembros). ✅

> **Notas de implementación (US5 — reactivación con grupo de control y uplift)**
> - **Uplift puro** (T040): `backend/src/shared/uplift.py` — `tasa_retorno(volvieron, total)`
>   (proporción del grupo que volvió a comprar; `0` si el grupo está vacío) y
>   `uplift(tasa_tratado, tasa_control)`. El test clave verifica que con redención
>   100% pero mismo retorno en ambos grupos el uplift es 0 — la redención no entra.
> - **Servicio/repo separados**: `campanas_service.py` + `campanas_repository.py`
>   (clase `CampanasService`/`CampanasRepository`), en el mismo módulo `clientes/`
>   pero fuera del ya grande `service.py`.
> - **Crear** (T042): `POST /api/clientes/campanas` — valida `categoria_sira`,
>   fechas, grupos ∈ {tratado, control}, sin household duplicado, y **gating FR-001**
>   (rechaza 422 si algún miembro no es `activo AND consentimiento_datos`). Crea
>   `campanas` (seq 100000, server_default) + `campana_cliente` con `grupo`.
> - **Enviar** (T043): valida que **todo** miembro tenga grupo y que exista **al
>   menos un `control`** → `BusinessRuleError` (422, FR-017); 409 si ya fue enviada.
>   Emite un `cupones` sobre el ancla de mayor margen (reutiliza `cupon_hito.py`),
>   `coupon_upc = f"REACT{campaign_id}"`, y un `cupon_enviado` (`evento_id=NULL`)
>   por cada **tratado** + correo best-effort. El control nunca recibe nada.
> - **Cerrar** (T044): `fecha_referencia = MAX(cupon_enviado.fecha_envio)`; por
>   grupo cuenta miembros y cuántos tienen una venta confirmada con `fecha_hora >=`
>   esa fecha (`COUNT(*) FILTER (WHERE EXISTS ...)`). Inserta `campana_resultado`
>   con las dos tasas; el `uplift` lo calcula la **columna generada** de la BD
>   (`refresh` lo trae de vuelta). 409 si no fue enviada o ya está cerrada.
> - **Decidir** (T045): `POST /api/clientes/campanas/{id}/decision` — exige que
>   `campana_resultado` exista (422 si no), valida `decision`, guarda
>   `empleado_decide_id` del principal (FR-019).
> - `GET /api/clientes/campanas` (paginado, `?categoria_sira=`) y
>   `GET /api/clientes/campanas/{id}` (miembros + resultado) — antes de `/{household_id}`.
>   Todos los endpoints: Rol Jefe_Marketing (`campanas` / `campana_resultado`).
> - **Frontend** (T046): `CampanasPage.vue` (secciones hito + reactivación con
>   acciones enviar/cerrar/decidir y uplift) + `components/FormularioCampana.vue`
>   (toma candidatos de `riesgo-fuga`, clic para alternar tratado/control, bloquea
>   el submit sin control). `clientesApi` con los 6 métodos de campaña.
> - Suite backend completa: **151 passed** (`black` + `ruff check` limpios; frontend
>   `eslint` + `prettier` limpios).

---

## Phase 8: Polish

- [X] T047 [P] Ejecutar `/speckit-analyze` sobre spec.md/plan.md/tasks.md de 002 antes de pasar a `/speckit-implement`
- [X] T048 [P] Ejecutar manualmente los 6 escenarios de `quickstart.md` de punta a punta
- [X] T049 Revisar cobertura de Principio X (cálculo de CLV, cálculo de churn+severidad, gating de consentimiento) — no se exige 100% del resto de la feature
- [X] T050 [P] Actualizar `checklists/requirements.md` con cualquier hallazgo de `/speckit-analyze`

**Checkpoint**: ✅ Feature 002 completa — 50/50 tareas + rondas 5-7 (T051-T053). **152 tests backend verdes**, build de frontend limpio.

> **Notas de implementación (Fase 8 — Polish, 2026-09-07)**
> - **T047** (`/speckit-analyze`): 0 issues CRITICAL/HIGH, 0 violaciones de constitución,
>   cobertura FR 19/19 y SC 8/8. Hallazgos MEDIUM (C1: FR-004 sin traza explícita;
>   I1: `plan.md` desactualizado sobre extensiones de esquema) — **ambos resueltos**.
>   El resto (LOW) son desviaciones ya documentadas en las notas de cada fase. Informe
>   completo y detalle de la remediación en `checklists/requirements.md` (Ronda 6).
> - **C1 resuelto**: agregado `test_clientes_actualizar.py::test_patch_agrega_datos_demograficos`
>   (FR-004 vía PATCH) + anotación de FR-004 en T007/T008 y notas de Fase 3.
> - **I1 resuelto**: `plan.md` (Summary + Technical Context/Storage) reescrito para remitir a
>   `data-model.md`/`01_operativo_postgres.sql` como fuente canónica del esquema y enumerar
>   las extensiones reales (rondas 1-2 + 5-7, migraciones `0006`-`0009`, todas aditivas).
> - **T048**: los 7 escenarios de `quickstart.md` (1-7, incluye el de Ronda 5) están cubiertos
>   por tests de integración de punta a punta (`httpx.AsyncClient` + PostgreSQL real), todos
>   verdes — mapeo escenario→test en `checklists/requirements.md` (Ronda 6).
> - **T049**: cobertura de Principio X verificada y completa — `test_calculo_clv.py`,
>   `test_calculo_churn.py`, `test_gating_consentimiento.py` (+ confirmación end-to-end en
>   `test_us1` esc. 1 y `test_campana_reactivacion`), más `test_seleccion_cupon_hito.py` y
>   `test_calculo_uplift.py`.
> - **T050**: `checklists/requirements.md` → nueva sección "Ronda 6" con el informe de
>   `/speckit-analyze`, la remediación de C1/I1 y el mapeo de escenarios.
> - Estado final: **152 tests backend** (`black` + `ruff check` limpios); frontend
>   `npm run build` OK, `eslint` + `prettier` limpios.
