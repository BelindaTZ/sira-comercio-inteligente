# Implementation Plan: Recursos Humanos

**Branch**: `011-recursos-humanos` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-recursos-humanos/spec.md`

## Summary

Marca de puestos críticos sobre `roles_puesto` (columna nueva, aditiva) y registro de acciones de retención sobre empleados en esos puestos (única tabla nueva de esta feature). Programación de capacitaciones dirigidas a uno o más roles del sistema, con fan-out automático hacia `empleado_capacitacion` para todos los empleados con cuenta activa en esos roles (008), y confirmación de cumplimiento por el Encargado de Tienda limitada a su propio personal. Registro semestral de clima laboral por tienda con cálculo de la tasa de rotación del mismo periodo a partir de `empleados.fecha_baja` ya existente, sin tabla ni columna nueva para la rotación. Plan de sucesión por puesto crítico, con señalización explícita de puestos críticos sin candidato.

## Technical Context

**Language/Version**: Backend: Python 3.11+ (sin dependencias de análisis nuevas). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT (mismo stack de 001-008, sin librerías nuevas — Principio VIII). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios.

**Storage**: PostgreSQL 16 — puebla (sin extender su esquema) `capacitaciones`, `empleado_capacitacion`, `clima_laboral` y `plan_sucesion`, las 4 tablas de RRHH ya reservadas desde el diseño inicial sin ninguna feature que las usara hasta ahora. Extiende aditivamente `roles_puesto` (001) con `es_critico BOOLEAN NOT NULL DEFAULT false`. Agrega **una única tabla nueva**, `acciones_retencion` — corrección detectada al planificar frente a la formulación original de `spec.md` Assumptions, que asumía cero tablas nuevas (ver esa sección, ya corregida). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Por Principio X, cobertura obligatoria en: el fan-out de una capacitación programada hacia todos los empleados con cuenta activa en los roles objetivo (FR-003/FR-004), la restricción del Encargado de Tienda al cumplimiento de su propio personal (FR-005), el cálculo de la tasa de rotación por tienda/periodo excluyendo periodos sin datos (FR-007/FR-010), y la señalización de puestos críticos sin candidato de sucesión (FR-009). Frontend: `Vitest` + `@vue/test-utils`.

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001-008).

**Performance Goals**: El cruce clima/rotación (FR-007) y la señalización de puestos sin sucesión (FR-009) son agregaciones SQL simples sobre datos ya sembrados/registrados, sin job de background. CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V) — el cálculo de rotación y la señalización de cobertura de sucesión nunca ocurren en el cliente. Un periodo sin encuesta de clima o sin bajas registradas no genera ningún indicador inventado — se muestra explícitamente como "sin datos" (FR-010, Principio VII). El fan-out de capacitación solo alcanza a empleados con cuenta de usuario ya creada (008) — un empleado sin cuenta aún no queda incluido hasta que la tenga (boundary con 008, documentado en research.md).

**Scale/Scope**: 4 historias de usuario (P1-P4), 10 requisitos funcionales. Reutiliza empleados/puestos/tiendas/cuentas ya sembrados; agrega volumen propio en acciones de retención, capacitaciones programadas, resultados de clima y candidatos de sucesión.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO de origen (OO-8.1.1/8.1.2, OO-8.2.1/8.2.2, OO-8.3.1/8.3.2, OO-8.4.1/8.4.2 — OE-8 completo, ver spec.md Input). |
| II. Nivel Operativo = Registro Real | PASS | Marca de puesto crítico, acción de retención, capacitación, cumplimiento, encuesta de clima y candidato de sucesión son INSERT/UPDATE reales sobre empleados/tiendas reales. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; ninguna agregación requiere ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Mismo criterio que 001-008: token de prueba mientras 008 no esté implementada operativamente en el entorno de prueba. Extiende el acceso ya concedido de `Jefe_RRHH` al módulo `RRHH` (008, primer uso) y agrega un nuevo acceso concedido de solo lectura de `Encargado_Tienda` a `RRHH` (mismo patrón que `Jefe_Marketing`→`Ventas` en 005 y `Jefe_Comercial`→`Ventas` en 007). |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyó explícitamente `data-model.md`/`plan.md` de 008 (`empleados`, `usuarios`, módulo `RRHH`) antes de diseñar; no se reconstruye el CRUD de empleado ni el de cuentas, solo se consumen para el fan-out de capacitación y el cálculo de rotación. |
| VII. Anclaje al Dataset Real | PASS | La tasa de rotación se calcula sobre `empleados.fecha_baja` real; un periodo sin encuesta de clima o sin bajas no genera ningún indicador inventado (FR-010). |
| VIII. Simplicidad Justificada | PASS | La tasa de rotación se calcula on-the-fly desde `empleados.fecha_baja`, sin tabla ni columna nueva para almacenarla (spec.md Assumptions). El fan-out de capacitación reutiliza `empleado_capacitacion` (ya reservada) en vez de crear una tabla `capacitacion_rol` intermedia — la asociación por rol es un evento de un solo momento (al programar), no una relación persistente que deba consultarse después. `acciones_retencion` es la única tabla nueva de toda la feature, y solo se agregó tras confirmar que ninguna tabla reservada modela ese concepto (research.md Decisión 1). |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`; la corrección de la Assumption original de `spec.md` (tabla nueva) queda documentada explícitamente, no aplicada en silencio. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; extiende `modules/rrhh/` (008, empleados) con capacitación/clima/sucesión/retención, sin módulo backend nuevo. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Catálogo de puestos críticos, capacitaciones y plan de sucesión con el mismo `DataTable.vue`/`WorkPanel.vue` del resto del sistema; puesto crítico sin candidato como badge de alerta no bloqueante, consistente con otras alertas del sistema (001, 006). |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/011-recursos-humanos/
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

**Criterio de organización**: el mismo ya fijado en 001-008 — por módulo de negocio. Esta feature no introduce ningún módulo nuevo: extiende `modules/rrhh/` (008, CRUD base de empleado) con retención, capacitación, clima laboral y plan de sucesión, con **una consulta cruzada de solo lectura explícita**: el fan-out de capacitación por rol consulta `usuarios.role_id` de `modules/sistema/` (008) para resolver qué empleados tienen cuenta activa en los roles objetivo, sin duplicar esa tabla.

```text
backend/
├── src/
│   ├── models/                      # se agregan: accion_retencion.py, capacitacion.py, empleado_capacitacion.py, clima_laboral.py, plan_sucesion.py; se extiende roles_puesto.py (es_critico)
│   ├── modules/
│   │   └── rrhh/                    # se extiende router.py/service.py/repository.py (008): puestos críticos, retención, capacitación (con fan-out), clima laboral + rotación, plan de sucesión
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P4)
    └── unit/                        # fan-out de capacitación por rol, restricción de Encargado_Tienda a su tienda, cálculo de rotación por periodo, señalización de puesto crítico sin sucesión

frontend/
├── src/
│   ├── services/                    # se extiende rrhhApi.js (008)
│   ├── modules/
│   │   └── rrhh/                    # pages/PuestosCriticosPage.vue (nueva), RetencionPage.vue (nueva), CapacitacionesPage.vue (nueva), ClimaLaboralPage.vue (nueva), PlanSucesionPage.vue (nueva); EmpleadosPage.vue (008, extendida: indicador de puesto crítico)
└── tests/
    ├── unit/                        # badge de puesto crítico sin sucesión
    └── component/                   # flujo de programar capacitación → confirmar cumplimiento, flujo de registrar clima → ver rotación cruzada
```

**Structure Decision**: No se crea ningún módulo backend/frontend nuevo — esta feature extiende `modules/rrhh/` (008), documentando explícitamente la única consulta cruzada de solo lectura (`rrhh`→`sistema`, `usuarios.role_id`) para el fan-out de capacitación por rol.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
