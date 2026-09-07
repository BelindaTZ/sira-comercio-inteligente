# Tasks: Pronóstico de Demanda con Variables Exógenas

**Input**: Design documents from `/specs/004-pronostico-demanda/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/pronostico.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: cálculo de la métrica de precisión (WAPE), exclusión de productos sin historial suficiente (cold start), y el respaldo a rotación reciente cuando no hay pronóstico vigente — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: `modules/forecasting/` es el módulo nuevo de esta feature (ya reservado desde el `plan.md` de 001); `modules/inventario/` y `modules/compras/` de 001 se extienden puntualmente (no se recrean) para consumir el pronóstico. Reutiliza infraestructura transversal ya construida en 001/002/003: FastAPI, SQLAlchemy async, Alembic, RBAC, `scheduler.py` (APScheduler), `DataTable.vue`/`WorkPanel.vue`.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US4), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- [X] T001 Crear el esqueleto de `backend/src/modules/forecasting/` (`router.py`, `service.py`, `repository.py`, `schemas.py`, `ml/__init__.py`, `ml/variables.py`, `ml/entrenamiento.py`, `ml/metricas.py`), vacíos con la estructura de capas ya usada en `pricing/` de 003.
- [X] T002 [P] Migración Alembic: crear `modelo_demanda`, `pronostico_demanda`, `monitoreo_precision_modelo`, `configuracion_pronostico`, y `ALTER TABLE alertas_inventario ADD COLUMN origen_calculo` / `ALTER TABLE orden_compra_detalle ADD COLUMN origen_calculo` (`data-model.md` completo), con seed inicial de `configuracion_pronostico` (`precision_minima_aprobacion`, `umbral_degradacion_semanal_pct`, `historial_minimo_semanas=12`).
- [X] T003 [P] Frontend: crear `frontend/src/modules/forecasting/` (`pages/ModelosPage.vue`, `pages/DemandaPerdidaPage.vue` vacíos) y `frontend/src/services/forecastingApi.js`; extender `inventarioApi.js` y `comprasApi.js` para incluir `origen_calculo` en sus respuestas ya existentes.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [X] T004 [P] Modelos SQLAlchemy: `ModeloDemanda`, `PronosticoDemanda`, `MonitoreoPrecisionModelo`, `ConfiguracionPronostico` en `models/`; extender `AlertaInventario` y `OrdenCompraDetalle` con el campo `origen_calculo`.
- [X] T005 Registrar dos nuevos jobs en el `scheduler.py` ya existente (APScheduler, mismo mecanismo de 002/003): `entrenar_modelo_demanda_job` (mensual) y `monitorear_precision_job` (semanal), sin ejecutar todavía su lógica (se completa en Phase 3/5).
- [X] T006 [P] Extender el endpoint de "forzar corrida" de desarrollo ya usado en 003 para incluir estos dos jobs (`POST /api/forecasting/modelos/entrenar`, `POST /api/forecasting/monitoreo/calcular`).
- [X] T007 Montar `forecasting.router` en `main.py`; verificar en RBAC que los módulos `TI` y `Operaciones` (ya sembrados) cubren los endpoints de esta feature — sin rol ni módulo nuevo (`research.md` Decisión 8).

**Checkpoint**: Migraciones aplicadas, modelos disponibles, jobs registrados (sin lógica), router montado — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Entrenar y aprobar el modelo de pronóstico antes de producción (Priority: P1) 🎯 MVP

**Goal**: Un job mensual entrena un modelo con variables exógenas, calcula su precisión de validación, y lo deja pendiente hasta que un Jefe de TI lo apruebe o rechace.

**Independent Test**: forzar la corrida del job mensual, verificar que el modelo queda pendiente con su métrica calculada, y que solo pasa a producción tras una aprobación explícita.

### Tests para User Story 1 ⚠️

- [X] T008 [P] [US1] Unit test: cálculo de la métrica WAPE (`ml/metricas.py`) — incluye el caso de semanas con demanda real igual a cero, verificando que no queda indefinido ni distorsiona el agregado (`research.md` Decisión 5).
- [X] T009 [P] [US1] Unit test: exclusión de productos/tienda con menos del historial mínimo configurado (`historial_minimo_semanas`) del conjunto de entrenamiento (FR-006).
- [X] T010 [P] [US1] Contract test: `POST /api/forecasting/modelos/{id}/aprobar` y `.../rechazar` — verificar transición de estado, el `CHECK` de consistencia, y el reemplazo automático del modelo previamente vigente al aprobar uno nuevo.
- [X] T011 [US1] Integration test: ciclo completo — forzar entrenamiento → modelo pendiente con métrica calculada → aprobar → queda vigente y disponible para consulta de pronóstico (Escenario 1 de `quickstart.md`).

### Implementación de User Story 1

- [X] T012 [P] [US1] `ml/variables.py`: construir el dataset de entrenamiento (una fila por producto×tienda×semana con historial suficiente) con rezagos/promedio móvil de ventas, indicador de promoción (`promociones`), indicador y magnitud de cambio de precio (`historial_precios`), indicador de quiebre propio y tasa de quiebre de la categoría (`eventos_quiebre_stock`) — `research.md` Decisión 3.
- [X] T013 [US1] `ml/entrenamiento.py`: entrenar el modelo global de regresión (`scikit-learn`) con partición temporal (no aleatoria) para el conjunto de validación (`research.md` Decisión 2 y 4).
- [X] T014 [US1] `ml/metricas.py`: calcular el WAPE de validación (depende de T008).
- [X] T015 [US1] `ForecastingRepository`: CRUD de `modelo_demanda` y `pronostico_demanda` (guardar el modelo entrenado con sus predicciones iniciales, estado `pendiente`).
- [X] T016 [US1] `ForecastingService.entrenar_modelo()`: orquesta T012-T015, respeta `historial_minimo_semanas` (depende de T009), completa la lógica del job `entrenar_modelo_demanda_job` (T005).
- [X] T017 [US1] `ForecastingService.aprobar_modelo()` / `.rechazar_modelo()`: transición de estado, reemplazo automático del vigente anterior al aprobar (`research.md` Decisión 7).
- [X] T018 [US1] Endpoints: `GET /api/forecasting/modelos`, `GET .../{id}`, `POST .../aprobar`, `POST .../rechazar`, `POST .../entrenar` (dev) — `contracts/pronostico.md`.
- [X] T019 [US1] `frontend/src/modules/forecasting/pages/ModelosPage.vue`: listado de modelos por estado, acciones de aprobar/rechazar con motivo obligatorio al rechazar.

**Checkpoint**: un modelo puede entrenarse, validarse y aprobarse/rechazarse de punta a punta — MVP entregable de forma independiente.

---

## Phase 4: User Story 2 - Reposición y compras basadas en el pronóstico, con respaldo cuando no hay modelo (Priority: P2)

**Goal**: El punto de reposición diario y la sugerencia semanal de compra de 001 usan el pronóstico vigente cuando existe, y caen a la lógica de rotación reciente de 001 cuando no.

**Independent Test**: comparar, para un producto con modelo vigente, que ambos cálculos usan el pronóstico; para uno sin modelo vigente, que ambos calculan igual que antes de esta feature.

### Tests para User Story 2 ⚠️

- [X] T020 [P] [US2] Unit test: `ForecastingService.obtener_pronostico_vigente()` devuelve el valor del modelo `aprobado` cuando existe, y `None` (sin error) cuando no — dispara el respaldo (FR-007/FR-008).
- [X] T021 [US2] Integration test: cálculo diario de punto de reposición y sugerencia semanal de compra, una vez para un producto con pronóstico vigente y otra vez para uno sin él, verificando `origen_calculo` en ambos casos (Escenario 3 y 4 de `quickstart.md`).

### Implementación de User Story 2

- [X] T022 [US2] `ForecastingService.obtener_pronostico_vigente(product_id, tienda_id, semana, anio)`: función compartida — la usará también el endpoint de consulta directa (T024) (depende de T015).
- [X] T023 [US2] Extender el job diario de punto de reposición de 001 (`modules/inventario/`) para consultar T022 antes de su lógica de rotación reciente actual, escribiendo `origen_calculo` en la alerta generada (FR-007, FR-008, FR-010).
- [X] T024 [US2] Extender el job semanal de sugerencia de compra de 001 (`modules/compras/`) con la misma lógica sobre `orden_compra_detalle` (FR-009, FR-010).
- [X] T025 [US2] Endpoint: `GET /api/forecasting/productos/{product_id}/tiendas/{tienda_id}/pronostico` (`contracts/pronostico.md`).
- [X] T026 [US2] Extender las respuestas ya existentes de `contracts/inventario.md`/`contracts/compras.md` de 001 con el campo `origen_calculo` (sin romper compatibilidad — campo aditivo).
- [X] T027 [US2] Extender `TablaAlertas.vue` (usado en los módulos `inventario` y `compras` del frontend) para mostrar un indicador visual de origen (modelo/rotación reciente) — FR-010.

**Checkpoint**: OT-5.1 y la parte de OT-2.1 sobre demanda proyectada quedan completamente realizadas, sin romper el comportamiento de 001 cuando no hay modelo.

---

## Phase 5: User Story 3 - Monitorear la precisión del modelo ya en producción (Priority: P3)

**Goal**: Un job semanal compara el pronóstico contra la demanda real observada y alerta al Jefe de TI si la precisión se degrada bajo un umbral.

**Independent Test**: forzar la corrida semanal sobre un modelo con al menos una semana de demanda real ya comparable, y verificar que la métrica queda calculada y que la alerta solo aparece si cae bajo el umbral.

### Tests para User Story 3 ⚠️

- [X] T028 [P] [US3] Unit test: comparación de pronóstico vs. demanda real de una semana ya cerrada, y la marca `supero_umbral_alerta` contra `umbral_degradacion_semanal_pct` de `configuracion_pronostico`.
- [X] T029 [US3] Contract test: `GET /api/forecasting/modelos/{id}/monitoreo` y `GET /api/forecasting/monitoreo/alertas`.
- [X] T030 [US3] Integration test: dos semanas de monitoreo consecutivas sobre el mismo modelo, verificando que el histórico completo queda consultable, no solo la última (Escenario 5 de `quickstart.md`).

### Implementación de User Story 3

- [X] T031 [US3] `ml/metricas.py`: extender con el cálculo de WAPE semanal contra demanda real ya observada (depende de T014).
- [X] T032 [US3] `ForecastingService.calcular_monitoreo_semanal()`: solo sobre el modelo vigente en producción; completa la lógica del job `monitorear_precision_job` (T005) (depende de T022, T031).
- [X] T033 [US3] Endpoints: `GET .../monitoreo`, `GET .../monitoreo/alertas`, `POST .../monitoreo/calcular` (dev) — `contracts/pronostico.md`.
- [X] T034 [US3] Frontend: gráfico de tendencia de precisión semanal (`vue-echarts`, ya aprobado en `domain-context.md` §7) dentro de `ModelosPage.vue`, con indicador de alerta cuando corresponda.

**Checkpoint**: un modelo en producción queda vigilado semana a semana sin intervención manual, con una alerta clara cuando se degrada.

---

## Phase 6: User Story 4 - Reporte mensual de demanda perdida por quiebre de stock (Priority: P4)

**Goal**: Consolidar mensualmente los eventos de quiebre de stock ya registrados por 001 en un reporte por tienda y categoría.

**Independent Test**: registrar eventos de quiebre en tiendas/categorías distintas durante el mes y verificar que el reporte los consolida correctamente.

### Tests para User Story 4 ⚠️

- [X] T035 [US4] Integration test: varios `eventos_quiebre_stock` en tiendas/categorías distintas, verificando el desglose del reporte y que una tienda/categoría sin eventos no aparece forzada a cero (Escenario 6 de `quickstart.md`).

### Implementación de User Story 4

- [X] T036 [US4] `ForecastingService.reporte_demanda_perdida(fecha_desde, fecha_hasta, tienda_id?)`: consulta agregada sobre `eventos_quiebre_stock` (sin tabla nueva, `data-model.md`).
- [X] T037 [US4] Endpoint: `GET /api/forecasting/reportes/demanda-perdida` (`contracts/pronostico.md`).
- [X] T038 [US4] Frontend: `DemandaPerdidaPage.vue` — tabla desglosada por tienda/categoría, reutilizando `DataTable.vue`.

**Checkpoint**: OO-5.2.2 queda cerrado, reutilizando datos ya registrados desde 001, sin bloquear ninguna historia anterior.

---

## Phase 7: Polish

- [X] T039 Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- [X] T040 Correr los 6 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- [X] T041 Revisar cobertura de Principio X: confirmar que el cálculo de WAPE, la exclusión por historial insuficiente y el respaldo a rotación reciente tienen test unitario (T008, T009, T020) antes de cerrar la feature.
- [X] T042 Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final (nueva "Ronda" si aplica).

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias.
- US1 (T012-T019) es prerrequisito real de US2 (T022 depende de que exista `modelo_demanda`/`pronostico_demanda` con datos, T015) y de US3 (T032 depende de T022).
- US2 y US3 no dependen entre sí — pueden implementarse en paralelo una vez cerrada US1.
- US4 no depende de ninguna otra historia de esta feature (solo de `eventos_quiebre_stock`, ya construido en 001) — puede implementarse en cualquier momento, incluso antes que US1-US3, aunque se numera al final por ser la prioridad más baja.
