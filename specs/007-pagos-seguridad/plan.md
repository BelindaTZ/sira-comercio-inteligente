# Implementation Plan: Pagos y Seguridad

**Branch**: `007-pagos-seguridad` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-pagos-seguridad/spec.md`

## Summary

Disponibilidad operativa diaria de datáfonos (fuera de servicio/restablecido) sobre el mismo dato ya sembrado desde 001/006, reutilizando el valor `fuera_servicio` ya reservado en el enum de `datafonos.estado` sin uso hasta ahora; al restablecer, se reevalúa contra el estándar de seguridad vigente (006) antes de marcar operativo. Alta y baja de medios de pago con aprobación explícita del Jefe de TI, extendiendo aditivamente el catálogo mínimo `medios_pago` ya sembrado desde 001. Registro y seguimiento de incidentes de seguridad de pago (entidad nueva, independiente del incidente de fraude interno de 006) con conteo por periodo para el Jefe de Finanzas. Política de seguridad de pagos como texto de referencia versionado, mismo criterio que el protocolo de escalamiento de 006. Medición del tiempo de cobro (OT-4.2) agregando una marca de inicio de venta, exclusivamente prospectiva sobre ventas registradas en vivo, con revisión semanal por caja y mensual por tienda a nivel de red.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (sin dependencias de análisis nuevas, igual que 006 — toda la lógica es agregación SQL y reglas de negocio simples). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT (mismo stack de 001-006, sin librerías nuevas — Principio VIII). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios (sin dependencias nuevas).

**Storage**: PostgreSQL 16 — reutiliza el valor `fuera_servicio` ya reservado en el enum `CHECK` de `datafonos.estado` desde 001 (sin migración sobre esa tabla). Extiende aditivamente `medios_pago` (ya sembrada desde 001 como catálogo mínimo: `medio_pago_id`, `nombre`) con `aprobado`, `aprobado_por`, `fecha_aprobacion`, `fecha_baja`. Extiende aditivamente `ventas` (001) con `fecha_inicio_cobro` (nullable, solo ventas registradas en vivo desde esta feature — Principio VII). Agrega 2 tablas nuevas: `incidente_seguridad_pago` (distinta e independiente de `incidentes_fraude`, 006) y `politica_seguridad_pagos` (append-only, mismo criterio que `protocolo_escalamiento` de 006). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Por Principio X, cobertura obligatoria en: la reevaluación de conformidad de un datáfono al restablecerlo (FR-003, reutiliza la lógica de 006 sin duplicarla), la no oferta de medios de pago no aprobados/dados de baja en el punto de venta (FR-007), la independencia entre un incidente de seguridad de pago y un incidente de fraude sobre el mismo datáfono (FR-010), el cálculo de duración de cobro excluyendo ventas anuladas y ventas sin `fecha_inicio_cobro` (FR-015/FR-018). Frontend: `Vitest` + `@vue/test-utils`.

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001-006).

**Performance Goals**: La advertencia de datáfono fuera de servicio en el punto de venta ocurre en el mismo request de inicio de cobro, sin llamada asíncrona adicional. Los reportes de tiempo de cobro (semanal por caja, mensual por tienda) son agregaciones SQL sobre `ventas` ya indexada por `fecha_hora`/`tienda_id`; se agrega un índice sobre `fecha_inicio_cobro` para no forzar un full scan. CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V) — la duración de cobro y la evaluación de conformidad de un datáfono nunca se calculan en el cliente. Dar de baja el único medio de pago electrónico aprobado de la red no está bloqueado por el sistema (spec.md Assumptions, decisión de negocio). Ninguna venta con otro medio de pago disponible se bloquea porque un datáfono esté fuera de servicio (Edge Case).

**Scale/Scope**: 5 historias de usuario (P1-P5), 18 requisitos funcionales. Reutiliza tiendas/cajas/datáfonos/empleados/ventas/medios_pago ya sembrados; agrega volumen propio solo en incidentes de seguridad de pago, versiones de política, y la marca de inicio de cobro de ventas registradas en vivo desde esta feature en adelante.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO/OT de origen (OT-4.1 completo, OT-4.2 completo —incorporado a pedido explícito del usuario—, y la nueva OO-6.3.3 bajo el OT-6.3 ya existente, agregada al especificar esta feature y ya reflejada en `domain-context.md`). |
| II. Nivel Operativo = Registro Real | PASS | Marcado de datáfono, alta/baja de medio de pago, incidente de seguridad de pago y política son INSERT/UPDATE reales; la duración de cobro se calcula sobre timestamps reales de ventas registradas en vivo, nunca simulados. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; ninguna agregación requiere ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001-006: token de prueba mientras 008 no esté implementada. Extiende el acceso ya concedido de `Jefe_TI` al módulo `Finanzas` (006, Decisión 10) y agrega un nuevo acceso concedido de `Jefe_TI` al módulo `Ventas` (para `medios_pago`) y de `Jefe_Comercial` al módulo `Ventas` de solo lectura (mismo patrón que `Jefe_Marketing`→`Ventas` en 005). |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyeron explícitamente `plan.md`/`data-model.md` de 001 (flujo de cobro, tabla `ventas`) y de 006 (estado de datáfono, módulo `Finanzas`) antes de diseñar; ningún flujo de venta o de conformidad de seguridad se reconstruye, solo se extiende aditivamente. |
| VII. Anclaje al Dataset Real | PASS | `fecha_inicio_cobro` no se fabrica para las ~1.47M ventas ya sembradas de Dunnhumby (no traen ese dato) — la medición de tiempo de cobro aplica solo prospectivamente (spec.md Assumptions, mismo criterio de "cold start" que 004). |
| VIII. Simplicidad Justificada | PASS | Reutiliza el valor `fuera_servicio` ya reservado en el enum de `datafonos.estado` en vez de agregar una tabla o columna nueva (research.md Decisión 1). La política de seguridad de pagos es texto versionado, no un motor de cumplimiento normativo (spec.md Assumptions, mismo criterio que 006). El incidente de seguridad de pago no reutiliza `incidentes_fraude` porque su forma de datos es distinta (sin empleado implicado obligatorio) — reutilizar hubiera forzado columnas nulas contradictorias entre dos conceptos de negocio distintos. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; extiende `modules/finanzas/` (006) y `modules/ventas/` (001), sin módulo backend nuevo. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Inventario de datáfonos y catálogo de medios de pago con el mismo `DataTable.vue`/`WorkPanel.vue` del resto del sistema; advertencia de datáfono fuera de servicio como badge no bloqueante, consistente con las alertas de merma de 006. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-pagos-seguridad/
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

**Criterio de organización**: el mismo ya fijado en 001-006 — por módulo de negocio. Esta feature no introduce ningún módulo nuevo: extiende `modules/finanzas/` (006, disponibilidad de datáfonos, incidentes de seguridad de pago, política) y `modules/ventas/` (001, medios de pago, marca de inicio de cobro), con **un consulta cruzada de solo lectura explícita**: el flujo de cobro de `modules/ventas/` consulta `datafonos.estado` de `modules/finanzas/` para la advertencia previa (FR-004), sin duplicar esa tabla.

```text
backend/
├── src/
│   ├── models/                      # se agregan: incidente_seguridad_pago.py, politica_seguridad_pagos.py; se extiende medio_pago.py (aprobado, aprobado_por, fecha_aprobacion, fecha_baja) y venta.py (fecha_inicio_cobro)
│   ├── modules/
│   │   ├── finanzas/                # se extiende router.py/service.py/repository.py (006): disponibilidad diaria de datáfono, incidentes de seguridad de pago, política de seguridad de pagos
│   │   └── ventas/                  # se extiende router.py/service.py/repository.py (001): alta/baja de medios de pago, registro de fecha_inicio_cobro, reportes de tiempo de cobro; consulta de solo lectura a modules/finanzas/ (estado de datáfono de la caja) para la advertencia previa al cobro
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # reevaluación de conformidad al restablecer, exclusión de medios de pago no aprobados, independencia incidente de seguridad/fraude, cálculo de duración de cobro

frontend/
├── src/
│   ├── services/                    # se extiende finanzasApi.js (006) y ventasApi.js (001)
│   ├── modules/
│   │   ├── finanzas/                # pages/DatafonosPage.vue (extendida: acción marcar fuera de servicio/restablecido), IncidentesSeguridadPagoPage.vue (nueva), PoliticaSeguridadPagosPage.vue (nueva)
│   │   └── ventas/                  # pages/MediosPagoPage.vue (nueva), TiempoCobroPage.vue (nueva); PuntoDeVentaPage.vue (001, extendida: advertencia de datáfono fuera de servicio)
└── tests/
    ├── unit/                        # formateo de duración de cobro, badge de advertencia de datáfono
    └── component/                   # flujo de alta/baja de medio de pago, flujo de registro de incidente de seguridad de pago
```

**Structure Decision**: No se crea ningún módulo backend/frontend nuevo — esta feature extiende `modules/finanzas/` (006) y `modules/ventas/` (001), documentando explícitamente la única consulta cruzada de solo lectura (`ventas`→`finanzas`, estado de datáfono) para que `tasks.md` no la trate como una omisión ni la duplique.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
