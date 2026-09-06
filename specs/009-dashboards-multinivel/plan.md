# Implementation Plan: Dashboards Multinivel

**Branch**: `009-dashboards-multinivel` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-dashboards-multinivel/spec.md`

**Estado**: en espera de implementación (junto con 010-plataforma-datos-tactico-estrategico) — este plan documenta el diseño completo para que la implementación pueda arrancar en cuanto 010 esté construida; no se ejecuta el `/speckit-implement` de esta feature antes de esa fecha.

## Summary

Cierra OT-7.4 (OE-7 TI/Datos): un dashboard estratégico consolidado para el Gerente General (US1, MVP), dashboards tácticos por departamento para cada Jefe (US2), y una verificación diaria de disponibilidad de los dashboards operativos ya construidos dentro de cada feature (US3). No recalcula ningún KPI (Principio VIII) — consolida y publica valores ya calculados por 001-008/011, leyendo del warehouse que construye 010 para las agregaciones pesadas y persistiendo en PostgreSQL solo el snapshot publicado y su registro de éxito/fecha (Principio II y III).

## Technical Context

**Language/Version**: Python 3.11 (backend, incluye el job diario de publicación), TypeScript 5.x (frontend).
**Primary Dependencies**: FastAPI, SQLAlchemy 2.0 (async, asyncpg), Alembic; Vue 3 + Vite + Pinia + Tailwind + vue-echarts (mismo stack de reportes/gráficos ya usado en 003-008). Airflow (010) orquesta el job diario; esta feature no agrega ninguna dependencia nueva propia.
**Storage**: PostgreSQL 16 para el snapshot publicado y el registro de publicación (Principio II — lo que el usuario consulta es un registro real, no una vista en vivo sobre ClickHouse en cada request); ClickHouse (010) como fuente de las agregaciones pesadas que alimentan el job diario (Principio III — separación de motores, nunca se consulta ClickHouse directamente desde el path de lectura del usuario).
**Testing**: pytest + httpx (contract/integration backend, con fixtures que simulan snapshots ya publicados — no requieren ClickHouse/Airflow reales para probar el contrato de lectura), Vitest + Vue Test Utils (frontend).
**Target Platform**: Web (backend Linux server, frontend SPA).
**Project Type**: Web application (backend + frontend separados, Principio V).
**Performance Goals**: FR-009 — publicar/actualizar un dashboard no debe degradar las operaciones transaccionales; el job diario corre fuera de horario pico y escribe un snapshot pequeño (decenas de filas por publicación), nunca una consulta agregada pesada en el camino de lectura del usuario (esa agregación ya la hizo 010/ClickHouse antes).
**Constraints**: Principio VII — ningún KPI sin fuente real (OE-4 Market Share/NPS permanece no disponible; OE-8 ya tiene fuente real desde 011, ver spec.md Assumptions). Principio III — el job diario es el único componente de esta feature que toca ClickHouse; el resto de la feature (lectura y RBAC) es OLTP puro.
**Scale/Scope**: 1 dashboard estratégico (red completa), hasta 6 dashboards tácticos (uno por departamento con Jefe propio: Comercial, Marketing_CRM, Operaciones, Finanzas, TI, RRHH — ver research.md Decisión 4), verificación diaria de disponibilidad sobre las 5 tiendas × dashboards operativos ya existentes por feature.

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeo requerido después del diseño de la Fase 1.*

| # | Principio | Cumplimiento |
|---|---|---|
| I | Trazabilidad al BSC | PASS — cada FR traza a OO-7.4.1/7.4.2/7.4.3 (OT-7.4, OE-7), ver data-model.md §Trazabilidad. |
| II | Nivel Operativo = Registro Real (NON-NEGOTIABLE) | PASS — cada publicación de dashboard (estratégico, táctico u operativo) escribe una fila real en `registro_publicacion_dashboard` con fecha y resultado; nunca se muestra "actualizado ahora mismo" sin una fila que lo respalde (FR-008). |
| III | Separación de Motores | PASS — es la feature que más depende de este principio: ClickHouse (010) calcula, PostgreSQL registra lo publicado; nunca se mezclan en el mismo query. |
| IV | RBAC de Dos Niveles Obligatorio | PASS — módulo `Direccion` (dashboard estratégico, Gerente General ya tiene lectura global); módulo propio de cada Jefe para su dashboard táctico (Comercial/Marketing_CRM/Operaciones/Finanzas/TI/RRHH); módulo `TI` para la verificación operativa (Jefe_TI). |
| V | Backend/Frontend Desacoplados | PASS — nueva sub-ruta REST bajo `modules/direccion/` y `modules/ti/dashboards/` (backend) y vistas Vue correspondientes. |
| VI | Features Autocontenidas | PASS — vive en módulos nuevos/ya reservados (`Direccion`, primer uso real; `TI`, ya usado por 006/007); no reabre ningún módulo de negocio de otra feature. |
| VII | Anclaje al Dataset Real | PASS — todo KPI mostrado proviene de una feature que lo calcula sobre el dataset real ya sembrado; OE-4 se muestra explícitamente no disponible, nunca inventado. |
| VIII | Simplicidad Justificada / DRY-KISS | PASS — 3 tablas nuevas, todas justificadas en research.md; el patrón "un tipo, varias variantes" ya usado en `alertas_inventario` (001) se reutiliza para `registro_publicacion_dashboard`. |
| IX | Guardrails de la IA sobre Specs (NON-NEGOTIABLE) | PASS — este plan no modifica `constitution.md`; la corrección de spec.md (OE-8 ahora con fuente real vía 011) quedó documentada explícitamente, no silenciosa. |
| X | Calidad / Testing / Seguridad | PASS — contract tests para cada endpoint de lectura y para el trigger manual de desarrollo (FR-010); el job diario en sí se prueba con fixtures, no con ClickHouse real (queda cubierto por los tests de 010). |
| XI | Convenciones de Código y Arquitectura | PASS — sigue la misma estructura de capas (router/service/repository) ya usada en el proyecto. |
| XII | Usabilidad y Diseño de Interfaz | PASS — cada dashboard muestra la fecha de última actualización junto a los valores (FR-003, FR-008), y todo KPI no disponible se distingue visualmente del que sí tiene datos (Edge Cases), siguiendo `design-system.md`. |

**Resultado**: sin violaciones. No se requiere entrada en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
specs/009-dashboards-multinivel/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── dashboards-multinivel.md
└── tasks.md
```

### Source Code (repository root)

```
backend/
├── modules/
│   ├── direccion/                          # NUEVO módulo (primer uso real)
│   │   ├── router.py                       # dashboard estratégico
│   │   ├── service.py
│   │   ├── repository.py
│   │   └── jobs/
│   │       └── publicar_dashboard_estrategico.py   # job diario (Airflow, 010)
│   └── ti/
│       └── dashboards/                     # NUEVO (dentro del módulo TI ya reservado)
│           ├── router.py                   # dashboards tácticos + verificación operativa
│           ├── service.py
│           ├── repository.py
│           └── jobs/
│               ├── publicar_dashboards_tacticos.py
│               └── verificar_dashboards_operativos.py
└── tests/
    ├── contract/test_dashboards_multinivel.py
    └── integration/test_publicacion_dashboards.py

frontend/
├── src/
│   ├── modules/
│   │   ├── direccion/
│   │   │   └── DashboardEstrategico.vue     # NUEVO
│   │   └── ti/
│   │       ├── DashboardTactico.vue         # NUEVO (reutilizado por cada Jefe, filtrado por su módulo)
│   │       └── VerificacionDashboardsOperativos.vue   # NUEVO
```

**Cruce entre módulos**: el dashboard táctico es la única pantalla que un mismo componente Vue sirve a 6 roles distintos (uno por Jefe de departamento), filtrando por el módulo propio de quien consulta — sin acceso cruzado (FR-005, RBAC ya existente). El job de publicación (`modules/direccion` y `modules/ti`) consulta ClickHouse (010) de forma exclusiva; ningún endpoint de lectura de usuario lo hace directamente (Principio III).

## Complexity Tracking

*Sin violaciones — tabla vacía.*

| Violación | Por qué es necesaria | Alternativa más simple rechazada |
|---|---|---|
| — | — | — |
