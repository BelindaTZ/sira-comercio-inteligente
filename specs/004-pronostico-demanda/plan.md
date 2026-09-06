# Implementation Plan: Pronóstico de Demanda con Variables Exógenas

**Branch**: `004-pronostico-demanda` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-pronostico-demanda/spec.md`

## Summary

Entrenamiento mensual automático (job) de un modelo de pronóstico de demanda por producto y tienda, usando como variables exógenas la actividad promocional, los cambios de precio y los quiebres de stock del periodo, para no confundir un pico de ventas explicado por esas causas con un aumento sostenido de la demanda base. El modelo entrenado queda pendiente de aprobación hasta que un Jefe de TI lo revise — misma mecánica de "propuesta antes de impacto" que `propuesta_ajuste_precio` de 003. El pronóstico del modelo aprobado alimenta el punto de reposición diario y la sugerencia semanal de compra ya construidos en 001, con respaldo automático a la lógica de rotación reciente cuando no hay pronóstico vigente. Un job semanal mide la precisión del modelo en producción contra la demanda real y alerta si se degrada. Un reporte mensual consolida la demanda perdida ya registrada por 001.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (incorpora `scikit-learn`, reservado desde `domain-context.md` §9 y ahora usado por primera vez). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT, APScheduler (mismo stack de 001/002/003) + `scikit-learn` + `pandas`/`numpy` (preparación de variables y entrenamiento — primera feature que los usa). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios, `vue-echarts` (gráfico de tendencia de precisión semanal, ya aprobado en `domain-context.md` §7).

**Storage**: PostgreSQL 16 — el modelo entrena directamente contra `ventas`, `venta_detalle`, `promociones`, `historial_precios` y `eventos_quiebre_stock` ya existentes (sin ETL intermedio). Agrega 4 tablas nuevas (`modelo_demanda`, `pronostico_demanda`, `monitoreo_precision_modelo`, `configuracion_pronostico`) y extiende aditivamente `alertas_inventario` y `orden_compra_detalle` de 001 con una columna de origen del cálculo (ver `data-model.md`). No usa MinIO ni ClickHouse (Principio III) — el modelo entrena en el propio proceso backend, no en un cluster de ML separado; si el volumen lo exigiera en el futuro, se revisa junto con 010 (ya anotado en `domain-context.md` §8).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`, más pruebas del pipeline de entrenamiento sobre un dataset sintético pequeño y determinista (no las ~1.47M filas reales del dataset en cada corrida de test). Frontend: `Vitest` + `@vue/test-utils`. Por Principio X, cobertura obligatoria en: el cálculo de la métrica de precisión (WAPE), la exclusión de productos sin historial suficiente (FR-006), y el respaldo a rotación reciente cuando no hay pronóstico vigente (FR-008) — Principio X nombra explícitamente el cálculo de reposición como lógica crítica desde 001.

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001/002/003).

**Performance Goals**: El job mensual de entrenamiento y el job semanal de monitoreo corren en horario de baja actividad y no bloquean ninguna operación transaccional en curso — igual que los jobs semanales ya montados en 003. CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V). Ningún modelo entrenado se usa en producción sin una aprobación explícita de un Jefe de TI (SC-002) — el sistema nunca marca un modelo como vigente por sí solo. El cálculo de reposición/compra nunca queda sin valor: si no hay pronóstico vigente, usa siempre el respaldo de rotación reciente de 001 (SC-003).

**Scale/Scope**: 4 historias de usuario (P1-P4), 14 requisitos funcionales. Consume datos ya sembrados/generados por 001 (ventas, promociones, quiebres) y extiende puntualmente dos de sus tablas y sus jobs existentes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO/OT de origen (OT-7.2 completo, más el cierre de OT-5.1/OT-5.2 ya iniciados en 001). |
| II. Nivel Operativo = Registro Real | PASS | Entrenamiento, aprobación, pronóstico y monitoreo son INSERT/UPDATE reales sobre datos ya sembrados del dataset Dunnhumby; nada se simula en este flujo. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; `scikit-learn` corre embebido, no se invade el alcance de ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001/002/003: token de prueba mientras 008 no esté implementada. Solo un usuario con rol `Jefe_TI` puede aprobar/rechazar un modelo pendiente. |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyó `spec.md` de 001 explícitamente (Assumptions) antes de diseñar: 001 ya reservó esta separación ("el pronóstico avanzado de demanda... pertenece a la feature 004"). Esta feature extiende de forma aditiva `alertas_inventario`/`orden_compra_detalle` y los jobs de 001, no los reconstruye. |
| VII. Anclaje al Dataset Real | PASS | El modelo entrena contra ventas, promociones y precios reales ya sembrados del dataset Dunnhumby (con las columnas ya enriquecidas por 001); ninguna fila de entrenamiento es sintética. |
| VIII. Simplicidad Justificada | PASS | Un solo modelo global entrenado sobre todos los productos/tiendas (no un modelo individual por producto/tienda — ver `research.md` Decisión 2), reutiliza el mecanismo de scheduler ya montado en 002/003, y reutiliza el mismo patrón de aprobación pendiente/aprobado/rechazado de `propuesta_ajuste_precio` (003) en vez de inventar uno nuevo. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; `modules/forecasting/` ya reservado desde el `plan.md` de 001. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Listado de modelos pendientes de aprobación, gráfico de tendencia de precisión semanal, mismo panel de trabajo estandarizado que el resto del sistema. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-pronostico-demanda/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

**Criterio de organización**: el mismo ya fijado en 001/002/003 — por módulo de negocio. El grueso de esta feature vive en `modules/forecasting/` (ya reservado desde el `plan.md` de 001), con **dos extensiones puntuales explícitas**: el job diario de alertas de reposición (FR-020 de 001, `modules/inventario/`) y el job semanal de sugerencia de compra (FR-023 de 001, `modules/compras/`) se modifican para consultar primero el pronóstico vigente antes de caer a su lógica de rotación reciente actual — no se recrean esos jobs ni sus tablas.

```text
backend/
├── src/
│   ├── models/                      # se agregan: modelo_demanda.py, pronostico_demanda.py, monitoreo_precision_modelo.py, configuracion_pronostico.py; se extienden alertas_inventario.py y orden_compra_detalle.py (columna origen_calculo)
│   ├── modules/
│   │   ├── forecasting/             # router.py, service.py, repository.py, schemas.py, ml/entrenamiento.py, ml/variables.py, ml/metricas.py — entrenamiento, aprobación, consulta de pronóstico, monitoreo, reporte de demanda perdida
│   │   ├── inventario/              # se extiende (no se recrea): el cálculo diario de punto de reposición consulta ForecastingService.obtener_pronostico_vigente() antes de su lógica de rotación reciente
│   │   └── compras/                 # se extiende (no se recrea): la sugerencia semanal de orden de compra consulta el mismo servicio
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P4)
    └── unit/                        # métrica de precisión (WAPE), exclusión por historial insuficiente, respaldo a rotación reciente

frontend/
├── src/
│   ├── services/                    # forecastingApi.js (nuevo); se extienden inventarioApi.js y comprasApi.js (indicador de origen del valor)
│   ├── modules/
│   │   ├── forecasting/             # pages/ModelosPage.vue (aprobar/rechazar, tendencia de precisión), DemandaPerdidaPage.vue
│   │   ├── inventario/              # se extiende TablaAlertas.vue: indicador de origen (modelo/rotación reciente)
│   │   └── compras/                 # se extiende FormularioOrdenCompra.vue/TablaAlertas.vue: mismo indicador de origen
└── tests/
    ├── unit/                        # formateo de la métrica de precisión en UI
    └── component/                   # flujo de aprobación/rechazo de modelo
```

**Structure Decision**: Reutiliza íntegramente la estructura y el criterio de 001/002/003. `modules/forecasting/` (ya reservado) concentra el entrenamiento, la aprobación, el pronóstico y el monitoreo; `modules/inventario/` y `modules/compras/` de 001 se extienden puntualmente para consumir el pronóstico, documentado explícitamente para que `tasks.md` no lo trate como una omisión.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
