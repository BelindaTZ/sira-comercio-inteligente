# Implementation Plan: Promociones Inteligentes

**Branch**: `005-promociones-inteligentes` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-promociones-inteligentes/spec.md`

## Summary

Cálculo mensual de reglas de asociación (afinidad de canasta) sobre el historial de ventas, mostradas como recomendación de cross-sell en el punto de venta y usadas para enviar proactivamente un cupón de descuento por correo cuando un cliente identificado compra el producto origen de una regla sin su complementario. En paralelo, clasificación mensual automática del catálogo por rotación (A/B/C, reutilizando el campo ya reservado en `productos` desde 001) y generación semanal, por tienda, de candidatos a liquidación de categoría C que el Encargado de Tienda ejecuta localmente — excluyendo productos con un ajuste de precio de 003 aún pendiente. Registro de la colocación de producto en anaquel destacado/mailer, reutilizando tablas ya sembradas del dataset y consumidas por 004.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (incorpora `mlxtend`, nueva dependencia para reglas de asociación — no confundir con `scikit-learn`/`statsmodels` ya reservados para 002/004, que no cubren market basket analysis). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT, APScheduler (mismo stack de 001-004) + `mlxtend` (Apriori/reglas de asociación, `research.md` Decisión 1) + `pandas` (ya reservado desde 004, se reutiliza para dar forma a la matriz de transacciones). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios (sin dependencias nuevas de frontend).

**Storage**: PostgreSQL 16 — el cálculo de afinidad corre sobre `ventas`/`venta_detalle` ya existentes; la clasificación ABC y la liquidación corren sobre esas mismas tablas más `productos`/`tiendas`. Agrega 3 tablas nuevas (`regla_afinidad`, `candidato_liquidacion`, `configuracion_promociones`) y extiende aditivamente `campanas` (nuevo valor `afinidad` en `categoria_sira`, ya extendida una vez en 002) y `cupon_enviado` (columna `regla_afinidad_id`, ambas de 002). Puebla — sin extender su esquema — el campo `clasificacion_abc` de `productos` (001) y las tablas `display_locations`/`mailer_locations`/`promociones` (ya sembradas del dataset, hasta ahora sin feature que las llenara). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`, más pruebas del cálculo de afinidad sobre un conjunto de transacciones sintético pequeño y determinista (no las ~1.47M filas reales en cada corrida de test). Frontend: `Vitest` + `@vue/test-utils`. Por Principio X, cobertura obligatoria en: el filtrado de reglas de asociación por soporte/confianza mínimos (FR-001), la exclusión de un candidato a liquidación con ajuste de precio pendiente (FR-013), y la prevención de cupones de afinidad duplicados (FR-007).

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001-004).

**Performance Goals**: La recomendación de cross-sell en el punto de venta responde sin demora perceptible durante el cobro (consulta indexada sobre reglas ya precalculadas, no un cálculo en vivo — SC-001). Los jobs mensuales (afinidad, clasificación ABC) y semanal (candidatos a liquidación) corren en horario de baja actividad, igual que los jobs ya montados en 002-004. CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V). Ninguna regla de afinidad se calcula ni se envía un cupón a un cliente sin consentimiento de datos aceptado (FR-006, reutiliza el control de 002). Un producto con una propuesta de ajuste de precio de 003 pendiente nunca se ofrece como candidato a liquidación al mismo tiempo (FR-013).

**Scale/Scope**: 4 historias de usuario (P1-P4), 16 requisitos funcionales. Reutiliza ~92,331 productos y el historial de ventas ya sembrados; no agrega volumen de datos propio salvo las reglas/candidatos/cupones que genera.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO/OT de origen (OT-3.5 completo incluyendo la nueva OO-3.5.3, y OT-2.2/OT-2.3 — ambos documentados como incorporados a esta feature en `spec.md` Assumptions). |
| II. Nivel Operativo = Registro Real | PASS | Reglas de asociación, cupones enviados, clasificación ABC y liquidaciones ejecutadas son INSERT/UPDATE reales sobre datos ya sembrados del dataset Dunnhumby; nada se simula. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; `mlxtend` corre embebido, sin invadir el alcance de ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001-004: token de prueba mientras 008 no esté implementada. `Jefe_Marketing` para reglas/cupones, `Jefe_Operaciones`/`Encargado_Tienda` para clasificación/liquidación, `Cajero` para ver la recomendación en el punto de venta. |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyeron explícitamente los spec.md de 001 (reserva de `modules/promociones/` y de `clasificacion_abc`), 002 (boundary explícito de OT-3.5 hacia esta feature, e infraestructura de cupones/campañas reutilizada) y 003 (boundary del ajuste de precio, FR-013) antes de diseñar. |
| VII. Anclaje al Dataset Real | PASS | El cálculo de afinidad y de rotación corre sobre ventas reales ya sembradas del dataset Dunnhumby; ninguna fila de entrenamiento/clasificación es sintética. |
| VIII. Simplicidad Justificada | PASS | Se eligió `mlxtend` (librería específica de market basket analysis) en vez de reimplementar Apriori a mano o forzar `scikit-learn` (que no cubre reglas de asociación de forma nativa) — ver `research.md` Decisión 1. La clasificación ABC reutiliza el campo ya reservado en `productos` en vez de crear una tabla nueva. El cupón de afinidad reutiliza `campanas`/`cupon_enviado` de 002 en vez de duplicar la infraestructura de cupones. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; `modules/promociones/` ya reservado desde el `plan.md` de 001. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Recomendación de cross-sell integrada al panel de cobro ya estandarizado; listados de reglas/candidatos con el mismo `DataTable.vue`/`WorkPanel.vue` del resto del sistema. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-promociones-inteligentes/
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

**Criterio de organización**: el mismo ya fijado en 001-004 — por módulo de negocio. El grueso de esta feature vive en `modules/promociones/` (ya reservado desde el `plan.md` de 001), con **tres extensiones puntuales explícitas**: el envío del cupón de afinidad reutiliza el servicio de cupones/campañas ya construido en `modules/clientes/` (002, no se duplica su lógica); la exclusión de un candidato a liquidación con ajuste de precio pendiente consulta de solo lectura `modules/pricing/` (003); y el punto de venta (`modules/ventas/` backend no cambia — la recomendación se resuelve en el frontend consultando directamente `modules/promociones/` con los productos ya en el carrito, sin acoplar `ventas/` a `promociones/`).

```text
backend/
├── src/
│   ├── models/                      # se agregan: regla_afinidad.py, candidato_liquidacion.py, configuracion_promociones.py; se extienden campana.py (nuevo valor 'afinidad' en categoria_sira) y cupon_enviado.py (columna regla_afinidad_id)
│   ├── modules/
│   │   ├── promociones/             # router.py, service.py, repository.py, schemas.py, analytics/afinidad.py (mlxtend), analytics/clasificacion_abc.py — reglas de asociación, clasificación ABC, candidatos/ejecución de liquidación, colocación en anaquel/mailer
│   │   ├── clientes/                # se extiende (no se recrea): ClientesService.registrar_envio_cupon() reutilizado para el nuevo tipo de cupón 'afinidad'
│   │   └── pricing/                 # se consulta de solo lectura (no se recrea): PricingRepository para verificar si un producto tiene una propuesta de ajuste de precio pendiente
│   ├── jobs/                        # se agregan: calcular_afinidad_job.py (mensual), clasificar_abc_job.py (mensual), generar_candidatos_liquidacion_job.py (semanal) — registrados en el scheduler.py ya existente (002)
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P4)
    └── unit/                        # filtrado de reglas por soporte/confianza, clasificación ABC (Pareto por valor de venta), exclusión por precio pendiente, anti-duplicado de cupón de afinidad

frontend/
├── src/
│   ├── services/                    # promocionesApi.js (nuevo); se extiende clientesApi.js (tasa de redención de cupones de afinidad, separada de la de hitos)
│   ├── modules/
│   │   ├── pos/                     # se extiende TicketVenta.vue de 001: banner de recomendación de cross-sell al agregar productos al carrito
│   │   └── promociones/             # pages/ReglasAfinidadPage.vue, LiquidacionPage.vue, ColocacionPromocionalPage.vue
└── tests/
    ├── unit/                        # formateo de soporte/confianza en UI
    └── component/                   # banner de recomendación en TicketVenta, flujo de ejecución de liquidación
```

**Structure Decision**: Reutiliza íntegramente la estructura y el criterio de 001-004. `modules/promociones/` (ya reservado) concentra afinidad, clasificación ABC, liquidación y colocación promocional; se extienden puntualmente `modules/clientes/` (cupones) y se consulta de solo lectura `modules/pricing/` (exclusión de candidatos), documentado explícitamente para que `tasks.md` no lo trate como una omisión. El punto de venta no requiere cambios de backend en `modules/ventas/`: el frontend consulta `promociones/` directamente con los product_id ya en el carrito.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
