# Implementation Plan: Precios Dinámicos, Márgenes y Comparación de Competencia

**Branch**: `003-precios-margenes` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-precios-margenes/spec.md`

## Summary

Motor de pricing dinámico por categoría (propuesta generada por el sistema, aprobada por Jefe Comercial antes de publicarse, con historial de precio por tienda), margen objetivo efectivo diferenciado por clasificación ancla/nicho, descuento manual en punto de venta con autorización obligatoria de un Encargado_Tienda distinto del cajero (mismo control anti-fraude que la remoción de línea de 001) y detección automática de margen bajo mínimo, reporte mensual de margen real vs. objetivo, y comparación manual de precio propio vs. precio de referencia de competencia con alertas de desviación. Enfoque técnico: extiende el backend FastAPI/PostgreSQL ya validado — reutiliza `historial_precios` y `margenes_objetivo` (ya existentes en el esquema, sin usar hasta ahora) y extiende puntualmente el endpoint de línea de venta de 001, sin crear un flujo de venta paralelo.

## Technical Context

**Language/Version**: Backend: Python 3.11+. Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT (mismo stack de 001/002, sin dependencias nuevas — el factor de sensibilidad/elasticidad es configurado manualmente, no requiere `scikit-learn`/`statsmodels`, reservados para el forecasting real de 004). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios.

**Storage**: PostgreSQL 16 — reutiliza `historial_precios` y `margenes_objetivo` del esquema base (sin usar hasta esta feature), más la extensión aditiva de esta feature (`propuesta_ajuste_precio`, `precio_competencia`, y columnas nuevas en `venta_detalle`: motivo del descuento, empleado que aplica, empleado que autoriza, margen real, indicador de margen bajo mínimo — ver `data-model.md`). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Frontend: `Vitest` + `@vue/test-utils`. Por Principio X (que cita explícitamente "cálculo de margen" como lógica crítica), cobertura obligatoria en: cálculo de margen real por línea, cálculo del margen objetivo efectivo por ancla/nicho, y el control de doble autorización del descuento manual (`empleado_aplica_id <> empleado_autoriza_id`).

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001/002).

**Performance Goals**: CRUD estándar <1s en desarrollo (Principio X). SC-004: la marca de margen bajo mínimo aparece el mismo día, sin cálculo manual.

**Constraints**: Sin lógica de negocio en el frontend (Principio V). Ninguna propuesta de ajuste de precio se publica sin aprobación explícita de Jefe_Comercial (SC-002) — el sistema nunca escribe `productos.precio_base` de forma autónoma. Ningún descuento manual se aplica sin autorización de un Encargado_Tienda distinto de quien lo aplica, sin excepción por monto (SC-004, corrección de ronda 2 de esta spec).

**Scale/Scope**: 5 historias de usuario (P1-P5), 16 requisitos funcionales, opera sobre el catálogo y ventas ya sembrados/gestionados por 001.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO/OT de origen (OE-1 completo + OT-4.3 de OE-4, incorporada por decisión del usuario). |
| II. Nivel Operativo = Registro Real | PASS | Toda propuesta de ajuste, aprobación, descuento manual y captura de precio de competencia es un INSERT/UPDATE real; el margen real de una línea se calcula y persiste al confirmar la venta, no se recalcula retroactivamente si cambian costos/categoría después (Assumptions del spec). |
| III. Separación de Motores | PASS | Solo PostgreSQL; el factor de elasticidad es manual, no requiere ClickHouse/ML — evita invadir el alcance de 004/010. |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001/002: token de prueba mientras 008 no esté implementada. La autorización de descuento manual valida además que el `empleado_autoriza_id` tenga rol `Encargado_Tienda` o superior, no solo que sea distinto del cajero. |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se investigó explícitamente contra 001 antes de escribir el spec (vía subagente) para no duplicar alcance; el descuento manual extiende un endpoint de 001 de forma documentada, no lo redefine. |
| VII. Anclaje al Dataset Real | PASS | Costos/precios ya sembrados (Dunnhumby + enriquecimiento de 001); el factor de elasticidad y los precios de competencia son datos sintetizados/manuales, documentados explícitamente como tales (Assumptions). |
| VIII. Simplicidad Justificada | PASS | Reutiliza 2 tablas ya existentes sin uso (`historial_precios`, `margenes_objetivo`) y la columna `venta_detalle.retail_disc`; el descuento manual reutiliza el mismo patrón `CHECK` de doble persona ya usado en FR-027/FR-034 de 001, sin inventar un mecanismo nuevo. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`; la corrección de ronda 2 de `spec.md` (autorización de descuento) se hizo con confirmación explícita del usuario. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba — Principio X nombra explícitamente "cálculo de margen" como lógica crítica. |
| XI. Convenciones de Código | PASS | Capas router→service→repository; el endpoint de descuento manual vive en `modules/ventas/` (no en `modules/pricing/`), documentado explícitamente en Project Structure. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Listados de propuestas de precio y de líneas bajo margen mínimo, paginados y filtrables, mismo panel de trabajo estandarizado. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-precios-margenes/
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

**Criterio de organización**: el mismo ya fijado en 001/002 — por módulo de negocio. La mayor parte de esta feature vive en `modules/pricing/` (ya reservado desde el `plan.md` de 001), con **una excepción explícita**: el descuento manual en punto de venta (FR-009/FR-010) extiende `modules/ventas/` (endpoint `POST /api/ventas/{id}/lineas/{id}/descuento`), porque es una acción sobre una venta en curso — meterlo en `modules/pricing/` obligaría a que ese módulo conozca el ciclo de vida de una venta, duplicando lógica que ya vive en `ventas/` (Principio VIII, DRY).

```text
backend/
├── src/
│   ├── models/                      # se agregan: propuesta_ajuste_precio.py, precio_competencia.py, historial_precio.py, margen_objetivo.py; se extiende venta_detalle.py (motivo/autorizador/margen)
│   ├── modules/
│   │   ├── pricing/                 # router.py, service.py, repository.py, schemas.py — margen objetivo, motor de ajuste, reporte mensual, comparación de competencia
│   │   └── ventas/                  # se extiende (no se recrea): nuevo endpoint de descuento manual con autorización, reutiliza VentasService ya existente de 001
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # cálculo de margen real, margen objetivo efectivo ancla/nicho, doble autorización de descuento

frontend/
├── src/
│   ├── services/                    # pricingApi.js (nuevo); se extiende ventasApi.js (endpoint de descuento)
│   ├── modules/
│   │   ├── pricing/                 # pages/MargenesPage.vue, PropuestasPrecioPage.vue, CompetenciaPage.vue; components/TablaMargenBajo.vue, FormularioReglaAjuste.vue
│   │   └── pos/                     # se extiende TicketVenta.vue de 001: botón "Aplicar descuento" + modal de autorización (Encargado_Tienda)
└── tests/
    ├── unit/                        # cálculo de margen mostrado en UI
    └── component/                   # modal de autorización de descuento
```

**Structure Decision**: Reutiliza íntegramente la estructura y el criterio de 001/002. `modules/pricing/` (ya reservado) concentra el motor de precios, márgenes y competencia; el descuento manual es la única pieza que vive en `modules/ventas/` por ser parte del ciclo de vida de una venta en curso — decisión documentada explícitamente para que `tasks.md` no la trate como una omisión.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
