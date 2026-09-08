# Implementation Plan: Traslados de Stock entre Tiendas

**Branch**: `012-traslados-stock-entre-tiendas` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/012-traslados-stock-entre-tiendas/spec.md`

## Summary

Cierra OT-2.5 (OE-2 Operaciones/Compras): visibilidad de stock entre sucursales antes de comprar (US1, MVP), y un flujo completo de solicitud → aprobación/rechazo → despacho → recepción de traslados entre tiendas (US2, US3), con trazabilidad íntegra de responsable y fecha en cada transición. Reutiliza al máximo el modelo de datos de 001-core-ventas-inventario (`productos`, `inventario`, `lotes`, `movimientos_inventario`) y consume por primera vez la tabla `traslados_stock`, reservada desde el diseño original del esquema. Sin dependencia de 009/010 (no está "en espera").

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5.x (frontend) — sin cambio respecto al stack ya establecido.
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic; Vue 3 + Vite + Pinia + Tailwind + vue-echarts. Sin dependencias nuevas — esta feature no introduce ninguna librería de análisis ni servicio externo.
**Storage**: PostgreSQL 16 (única fuente OLTP, Principio III). Extiende `traslados_stock` (aditivo) y reutiliza `movimientos_inventario` (tipos `traslado_salida`/`traslado_entrada` ya reservados), `inventario` y `lotes` de 001, sin tablas paralelas.
**Testing**: pytest + httpx (contract/integration backend), Vitest + Vue Test Utils (frontend) — mismo patrón que 001-011.
**Target Platform**: Web (backend Linux server, frontend SPA) — sin cambio.
**Project Type**: Web application (backend + frontend separados, Principio V).
**Performance Goals**: Consulta de stock por sucursal (US1) responde en el mismo orden de magnitud que cualquier consulta de `inventario` ya existente en 001 (sin agregaciones pesadas: es una lectura directa de una tabla ya indexada por `product_id, tienda_id`).
**Constraints**: RBAC de dos niveles obligatorio (Principio IV) — módulo `Operaciones`, ya usado por 001, sin módulo nuevo. Cero simulación: cada transición de `traslados_stock` (aprobar/rechazar/despachar/recibir/cancelar) debe persistir registro real con empleado y fecha (Principio II), nunca un campo booleano de conveniencia.
**Scale/Scope**: 5 tiendas de la red (dataset ya sembrado), volumen de traslados esperado bajo (decenas por semana), sin necesidad de particionamiento ni tablas de series de tiempo.

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeo requerido después del diseño de la Fase 1.*

| # | Principio | Cumplimiento |
|---|---|---|
| I | Trazabilidad al BSC | PASS — cada FR traza a OO-2.5.1 u OO-2.5.2 (OT-2.5, OE-2), ver data-model.md §Trazabilidad. |
| II | Nivel Operativo = Registro Real (NON-NEGOTIABLE) | PASS — cada transición de un traslado (aprobar, rechazar, despachar, recibir, cancelar) escribe una fila real en `traslados_stock` y en `movimientos_inventario`, con empleado y fecha; no hay estado simulado ni contador en memoria. |
| III | Separación de Motores | PASS — todo el flujo es OLTP puro (PostgreSQL); no participa ClickHouse ni Airflow (sin dependencia de 009/010). |
| IV | RBAC de Dos Niveles Obligatorio | PASS — módulo `Operaciones` (ya reservado por 001); nivel de tabla nuevo para `traslados_stock` (Jefe_Operaciones: CRUD completo a nivel de red; Encargado_Tienda: alta/lectura/actualización limitada a su propia tienda, validado en capa de servicio igual que `empleado_autoriza_id` en pagos_proveedor/venta_detalle). |
| V | Backend/Frontend Desacoplados | PASS — nueva sub-ruta REST bajo `modules/operaciones/` (backend) y vista Vue correspondiente (frontend), mismo patrón que toda feature anterior. |
| VI | Features Autocontenidas | PASS — vive en `backend/src/modules/traslados/` (módulo plano, mismo patrón que 002-011 — ver Ronda 1); reutiliza `InventarioRepository` de 001 para el movimiento de stock, sin duplicar modelos. |
| VII | Anclaje al Dataset Real | PASS — usa las 5 tiendas y el catálogo de productos ya sembrados; sin datos sintéticos nuevos. |
| VIII | Simplicidad Justificada / DRY-KISS | PASS — cero tablas nuevas (reutiliza `traslados_stock` ya reservada); único cambio de schema es aditivo (columnas de trazabilidad + extensión del CHECK de `estado`), justificado en research.md. |
| IX | Guardrails de la IA sobre Specs (NON-NEGOTIABLE) | PASS — este plan no modifica `constitution.md`; la única corrección fue documentada explícitamente en spec.md (Assumptions), no silenciosa. |
| X | Calidad / Testing / Seguridad | PASS — contract tests para cada endpoint (contracts/traslados-stock-entre-tiendas.md) e integration tests para el ciclo completo solicitado→recibido y para el rechazo/cancelación. |
| XI | Convenciones de Código y Arquitectura | PASS — sigue la misma estructura de capas (router/service/repository) ya usada en `modules/operaciones/` desde 001. |
| XII | Usabilidad y Diseño de Interfaz | PASS — la disponibilidad por sucursal se muestra en la misma pantalla de sugerencia de orden de compra (FR-002), sin navegación adicional; sigue `design-system.md`. |

**Resultado**: sin violaciones. No se requiere entrada en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
specs/012-traslados-stock-entre-tiendas/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── traslados-stock-entre-tiendas.md
└── tasks.md
```

### Source Code (repository root)

```
backend/
├── modules/
│   └── operaciones/                       # ya existe desde 001
│       ├── traslados/                     # NUEVO
│       │   ├── router.py                  # endpoints de disponibilidad y traslados
│       │   ├── service.py                 # reglas de aprobación/rechazo/despacho/recepción
│       │   ├── repository.py
│       │   └── schemas.py
│       └── ... (ordenes_compra, inventario — ya existentes de 001)
└── tests/
    ├── contract/test_traslados_stock.py    # NUEVO
    └── integration/test_ciclo_traslado.py  # NUEVO

frontend/
├── src/
│   ├── modules/
│   │   └── operaciones/
│   │       ├── DisponibilidadSucursales.vue   # NUEVO (US1)
│   │       ├── SolicitarTraslado.vue          # NUEVO (US2)
│   │       ├── AprobarTraslados.vue           # NUEVO (US2)
│   │       └── ConfirmarRecepcion.vue         # NUEVO (US3)
│   └── stores/
│       └── traslados.ts                        # NUEVO (Pinia)
```

**Cruce entre módulos**: ninguno nuevo. `Jefe_Operaciones` y `Encargado_Tienda` ya operan íntegramente dentro de `Operaciones` — a diferencia de 007/008/011, esta feature no requiere una consulta de solo lectura hacia otro módulo.

## Complexity Tracking

*Sin violaciones — tabla vacía.*

| Violación | Por qué es necesaria | Alternativa más simple rechazada |
|---|---|---|
| — | — | — |
