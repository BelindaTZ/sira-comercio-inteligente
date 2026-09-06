# Implementation Plan: Caja, Mermas y Fraude

**Branch**: `006-caja-mermas-fraude` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/006-caja-mermas-fraude/spec.md`

## Summary

Cuadre de caja horario con cálculo automático de la diferencia (reutilizando la columna `GENERATED` ya reservada desde 001) y marcado automático para revisión cuando esa diferencia es distinta de cero, consultable por el Encargado de Tienda para todas las cajas de su tienda a la vez. Inventario de datáfonos con identificación automática de no conformidad frente a un estándar de seguridad de pago configurable (reutilizando el estado `requiere_actualizacion` ya reservado en el enum de `datafonos` desde 001) y su ciclo de actualización/reemplazo. Reporte mensual de diferencias de cuadre agrupado por cajero y turno, extendido con los ajustes de inventario (001) de diferencia negativa inusual, desde el cual el Jefe de Finanzas puede escalar un patrón sospechoso abriendo un incidente de fraude. Protocolo de escalamiento como texto de referencia versionado, aplicado por el Encargado de Tienda sobre un incidente abierto hasta su cierre. Umbral de merma aceptable por categoría definido a nivel de red, con seguimiento semanal del porcentaje acumulado por tienda.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (sin dependencias de análisis nuevas — a diferencia de 004/005, esta feature no requiere `statsmodels`, `prophet` ni `mlxtend`; toda la lógica es agregación SQL y reglas de negocio simples). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT, APScheduler (mismo stack de 001-005, sin librerías nuevas — Principio VIII). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios (sin dependencias nuevas).

**Storage**: PostgreSQL 16 — puebla (sin extender su esquema) `apertura_caja`, `cierre_caja` y `datafonos`, ya reservadas desde 001 sin feature que las llenara. Extiende aditivamente `incidentes_fraude` (ya reservada desde 001): `cierre_id` pasa a nullable y se agregan `ajuste_id` (FK opcional a `ajustes_inventario`, 001), `acciones_tomadas`, `resultado` y el par `actualizado_por`/`fecha_actualizacion` — necesario porque un incidente puede originarse en un patrón de cuadre (US3), en un ajuste de inventario anómalo (US3, FR-010) o registrarse directamente (US4 Acceptance Scenario 2 lo permite), y porque el ciclo abierto→en_revisión→cerrado (FR-015) necesita constancia de quién y cuándo. Agrega 3 tablas nuevas de configuración: `configuracion_seguridad_pagos` (estándar mínimo de firmware, versionado por fila), `protocolo_escalamiento` (texto vigente, versionado por fila) y `umbral_merma_categoria` (umbral por categoría, una fila por categoría). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Por Principio X, cobertura obligatoria en: el cálculo automático de la diferencia de cuadre (FR-003, incluyendo el caso de ventana horaria con cero ventas), el marcado automático para revisión (FR-004), la identificación automática de datáfonos no conformes (FR-007), la exclusión de bloqueo operativo cuando la merma supera el umbral (FR-019), y que un incidente de fraude sobre un empleado dado de baja no quede bloqueado (FR-016). Frontend: `Vitest` + `@vue/test-utils`.

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001-005).

**Performance Goals**: El cálculo de la diferencia de cuadre ocurre en el mismo request de guardado (columna `GENERATED`, sin cálculo asíncrono — SC-001). El reporte mensual y el seguimiento semanal de merma son agregaciones SQL sobre datos ya indexados (`idx_cierre_caja_diferencia`, `idx_mermas_producto_tienda`), sin requerir un job propio de background más allá de, opcionalmente, una vista materializada si el volumen lo justifica (decisión de implementación, no de spec). CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V) — la diferencia de cuadre nunca se calcula en el cliente. Ningún cierre de incidente de fraude puede acusar al empleado si la investigación no lo confirma (FR-015, Edge Case). Ninguna operación de venta, recepción de mercadería o registro de merma se bloquea por superar el umbral de OT-5.5 (FR-019).

**Scale/Scope**: 5 historias de usuario (P1-P5), 19 requisitos funcionales. Reutiliza tiendas/cajas/empleados/ventas ya sembrados; no agrega volumen de datos propio salvo cuadres, incidentes y configuración que esta feature genera operativamente.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO/OT de origen (OT-6.1 a OT-6.4 completos, OO-B.17 para la apertura de caja, y OT-5.5 — documentado como incorporado a esta feature en `spec.md` Assumptions). |
| II. Nivel Operativo = Registro Real | PASS | Aperturas, cuadres, incidentes y umbrales son INSERT/UPDATE reales sobre datos ya sembrados; la diferencia de cuadre se calcula con datos de venta reales, nunca simulados. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; ninguna agregación requiere ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001-005: token de prueba mientras 008 no esté implementada. Módulo `Finanzas` (ya sembrado como "Caja, cuadre, seguridad de pagos") concentra cuadre, datáfonos e incidentes; `Cajero` ya tiene permiso de tabla sembrado sobre `apertura_caja`/`cierre_caja` desde 001. |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyó explícitamente el spec.md de 001 (edge case textual que reserva la investigación de fraude sobre un ajuste de inventario para esta feature) antes de diseñar; ningún flujo de venta, merma o ajuste de 001 se reconstruye. |
| VII. Anclaje al Dataset Real | PASS | El total esperado de cada cuadre se calcula sobre `ventas`/`venta_detalle` reales ya sembrados; el % de merma semanal usa `mermas`/`venta_detalle` reales. |
| VIII. Simplicidad Justificada | PASS | Reutiliza el estado `requiere_actualizacion` ya reservado en el enum de `datafonos` en vez de agregar un valor nuevo (research.md Decisión 4). Modela "turno" como la apertura de caja vigente en vez de crear una entidad turno nueva (Decisión 3). El protocolo de escalamiento es texto versionado, no un motor de flujo (spec.md Assumptions). |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; nuevo `modules/caja/` (primera feature en usar el módulo `Finanzas` ya sembrado desde 001 en `modulos`). |
| XII. Usabilidad y Diseño de Interfaz | PASS | Cuadre de caja y reporte de diferencias con el mismo `DataTable.vue`/`WorkPanel.vue` del resto del sistema; alerta de merma como badge no bloqueante, consistente con las alertas de reposición de 001. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/006-caja-mermas-fraude/
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

**Criterio de organización**: el mismo ya fijado en 001-005 — por módulo de negocio. Esta feature introduce `modules/caja/` (módulo `Finanzas` ya sembrado desde 001 en la tabla `modulos`, sin feature que lo usara hasta ahora), con **una extensión puntual explícita**: la señalización de ajustes de inventario anómalos (FR-010) consulta de solo lectura `modules/inventario/` (001), sin duplicar su lógica de registro.

```text
backend/
├── src/
│   ├── models/                      # se agregan: configuracion_seguridad_pagos.py, protocolo_escalamiento.py, umbral_merma_categoria.py; se extiende incidente_fraude.py (cierre_id nullable, + ajuste_id, acciones_tomadas, resultado, actualizado_por, fecha_actualizacion)
│   ├── modules/
│   │   ├── finanzas/                # router.py, service.py, repository.py, schemas.py — apertura/cuadre de caja, datáfonos, reporte de patrones, incidentes de fraude, protocolo de escalamiento
│   │   └── inventario/              # se consulta de solo lectura (no se recrea): InventarioRepository para leer ajustes de inventario con diferencia negativa por encima del umbral configurable
│   ├── jobs/                        # se agrega: identificar_datafonos_no_conformes_job.py (al guardar/actualizar firmware, no requiere cadencia fija); se registra en el scheduler.py ya existente (002) solo si se decide una verificación periódica adicional
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # cálculo de diferencia de cuadre, ventana horaria por apertura, identificación de no conformidad de datáfono, cálculo de % de merma semanal, transición de estado de incidente

frontend/
├── src/
│   ├── services/                    # cajaApi.js (nuevo)
│   ├── modules/
│   │   └── finanzas/                # pages/CuadreCajaPage.vue, DatafonosPage.vue, ReporteDiferenciasPage.vue, IncidentesFraudePage.vue, ProtocoloEscalamientoPage.vue, SeguimientoMermaPage.vue
└── tests/
    ├── unit/                        # formateo de diferencia (positiva/negativa) en UI
    └── component/                   # flujo de registro de cuadre, flujo de aplicación de protocolo sobre un incidente
```

**Structure Decision**: Introduce `modules/caja/` (módulo ya reservado en el esquema RBAC desde 001, sin uso hasta ahora) como ubicación única del grueso de esta feature. La única extensión puntual es una consulta de solo lectura a `modules/inventario/` (001) para el reporte de patrones (FR-010), documentada explícitamente para que `tasks.md` no la trate como una omisión — no se duplica el registro de ajustes de inventario, que sigue perteneciendo a 001.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
