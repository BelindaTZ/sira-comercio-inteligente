# Specification Quality Checklist: Pronóstico de Demanda con Variables Exógenas

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validación ejecutada releyendo `constitution.md` completa (12 principios) y `domain-context.md` (OE-7 completo: OT-7.2; y el cierre de OT-5.1/OT-5.2 de OE-5, cuyo registro base ya vive en 001) antes de redactar.
- Investigación previa sobre `specs/001-core-ventas-inventario/` para fijar el límite exacto con esta feature: 001 ya construyó el mecanismo completo de alertas de reposición (`alertas_inventario`, FR-020/FR-021) y el registro de eventos de quiebre (`eventos_quiebre_stock`, FR-022) con una lógica de rotación reciente explícitamente marcada en su propio spec como reservada a ser reemplazada por 004 ("el pronóstico avanzado de demanda con modelo predictivo pertenece a la feature 004-pronostico-demanda"). Esta feature no reconstruye esas tablas ni ese flujo: solo cambia el insumo del cálculo (FR-007/FR-008) y consolida el reporte mensual de demanda perdida que nunca se construyó (FR-014, OO-5.2.2).
- Se detectó el mismo gap de rol RBAC que en 002 y 003 (actores "Analista de Datos" y "Analista de Operaciones" en `domain-context.md` sin rol propio en el esquema, solo `Jefe_TI` y `Jefe_Operaciones`), pero con una resolución distinta: a diferencia de 002/003 (donde todas las OO de ese OT ya apuntaban al mismo Jefe y el "Analista" era la única excepción), aquí el diseño original sí separaba "quien entrena/monitorea" (Analista de Datos) de "quien aprueba antes de producción" (Jefe de TI, ya un rol RBAC real) — colapsar ambos en Jefe_TI habría eliminado esa separación. Se resolvió convirtiendo el entrenamiento mensual (OO-7.2.1) y el monitoreo semanal (OO-7.2.3) en jobs automáticos del sistema (mismo patrón ya usado en 003 para la propuesta de ajuste de precio y la alerta de competencia semanales), dejando a Jefe de TI como el único actor humano: aprueba/rechaza el modelo y revisa la alerta de degradación. Para OO-5.2.2 (reporte de demanda perdida) sí aplica el mismo patrón de 002/003: `Jefe_Operaciones` ejecuta esa acción, sin rol nuevo.
- Se verificó contra el enunciado original: "la predicción de demanda no depende únicamente de cuánto se vendió anteriormente, porque puede haber tenido ventas elevadas por una promoción, por ausencia de sustitutos, por una variación temporal del precio, por disponibilidad circunstancial o porque otro producto relacionado dejó de estar disponible" — cubierto explícitamente por FR-001 (variables exógenas obligatorias al entrenar) y el Edge Case de fin de promoción, sin fijar en el spec la técnica exacta de ingeniería de variables (queda para `research.md`).
- Se confirmó que las tablas fuente de las variables exógenas (`promociones`, `historial_precios`, `eventos_quiebre_stock`) ya existen en `01_operativo_postgres.sql` desde 001/el esquema base — esta feature no crea tablas de entrada, solo tablas de salida del modelo (versión de modelo, pronóstico, métrica de monitoreo), a definir en `data-model.md`.
- No se detectaron violaciones de principios de la constitución.

## Ronda 2 (implementación — `/speckit-implement` + `/speckit-analyze` post-hoc)

- Feature implementada de punta a punta: módulo `backend/src/modules/forecasting/` (router/service/repository/schemas + `ml/metricas.py`, `ml/variables.py`, `ml/entrenamiento.py`), 4 modelos SQLAlchemy nuevos + columna `origen_calculo` aditiva en `alertas_inventario`/`orden_compra_detalle`, migración `0011_feature004_pronostico_demanda` (idempotente, espeja el bloque "EXTENSIÓN — Feature 004" del DDL + RBAC del módulo `TI`), 2 jobs `APScheduler` (`entrenar_modelo_demanda_mensual`, `monitorear_precision_semanal`) con sus endpoints dev de "forzar corrida". Extensiones puntuales de 001: el job diario de reposición (`modules/inventario/`) y la sugerencia semanal de compra (`modules/compras/`) consultan el pronóstico vigente antes de la rotación reciente y escriben `origen_calculo`. Frontend: `modules/forecasting/` (ModelosPage con gráfico de tendencia `vue-echarts`, DemandaPerdidaPage), `forecastingApi.js`, indicador de origen en `TablaAlertas.vue`.
- Dependencias nuevas: `scikit-learn`, `pandas`, `numpy` (primera feature que las usa, ya reservadas en `domain-context.md §9`) — agregadas a `pyproject.toml`.
- Modelo: un único regresor global (`HistGradientBoostingRegressor`) sobre una fila por producto×tienda×semana con rezagos + promedio móvil + variables exógenas (promo / cambio de precio / quiebre propio / tasa de quiebre de la categoría). Partición de validación siempre temporal. El objeto entrenado NO se persiste — sólo sus predicciones del horizonte (8 semanas) en `pronostico_demanda`; el reentrenamiento mensual las regenera. El pronóstico del horizonte usa las variables exógenas en su valor base (sin promo/cambio/quiebre) → demanda base, no un pico circunstancial (Edge Case de `spec.md`).
- Cobertura de tests: 226 backend (202 previos + 24 nuevos), 0 fallos. Principio X cubierto: `test_calculo_wape` (WAPE, incl. semana con demanda cero), `test_cold_start_historial` (exclusión por historial insuficiente), `test_us2_reposicion_pronostico` (respaldo a rotación reciente cuando no hay pronóstico vigente). Los 6 escenarios de `quickstart.md` quedan cubiertos por los tests de integración `test_us1_modelo` … `test_us4_demanda_perdida` (entrenamiento real de sklearn contra la BD PostgreSQL, forzando los jobs vía los endpoints dev).
- `/speckit-analyze` (post-hoc): 0 issues CRITICAL/HIGH; 14/14 FR con tarea; SC-001..SC-005 cubiertos. Hallazgos LOW: (a) el pronóstico del horizonte asume variables exógenas en su valor base para semanas futuras — coherente con el Edge Case de fin de promoción, documentado en `variables.fila_pronostico_base`; (b) `demanda_semanal_vigente` toma el pronóstico más temprano del modelo vigente como tasa de demanda para el cálculo de reposición de 001 — suficiente para el MVP, ninguna OO exige alinear con la semana ISO exacta del día de corrida.
