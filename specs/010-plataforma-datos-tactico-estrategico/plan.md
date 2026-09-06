# Implementation Plan: Plataforma de Datos Táctico-Estratégica

**Branch**: `010-plataforma-datos-tactico-estrategico` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/010-plataforma-datos-tactico-estrategico/spec.md`

**Estado**: en espera de implementación (junto con 009-dashboards-multinivel) — este plan documenta el diseño completo del pipeline ELT para que la implementación pueda arrancar en cuanto se retome la capa táctica/estratégica; no se ejecuta el `/speckit-implement` de esta feature antes de esa fecha.

## Summary

Construye la plataforma de datos que 009 consume: el modelo de datos único del warehouse (fact_venta + dimensiones, US1, MVP), la carga diaria automática ELT desde PostgreSQL y MinIO `landing-zone` hacia ClickHouse (US2), la detección de calidad y trazabilidad de cada corrida (US3, OO-7.5.1) y la política de gobierno de datos como documento versionado (US4). Toma OO-7.5.1 explícitamente dejado pendiente por 008 (que resolvió solo OO-7.5.2, auditoría de accesos). No recalcula ningún KPI de negocio — construye la infraestructura sobre la que 009 y, opcionalmente, 004 leen agregaciones.

## Technical Context

**Language/Version**: Python 3.11 (DAGs de Airflow, jobs ELT).
**Primary Dependencies**: Apache Airflow (orquestación), ClickHouse (driver `clickhouse-connect` o equivalente), boto3/MinIO SDK (lectura de `landing-zone`), SQLAlchemy 2.0/asyncpg (lectura de PostgreSQL como origen y escritura de las tablas de control en PostgreSQL). Sin frontend propio de alto tráfico — el monitoreo de corridas es una pantalla de solo lectura para Jefe_TI, mismo stack Vue ya usado en el resto del proyecto.
**Storage**: PostgreSQL 16 para las tablas de control del pipeline (`modelo_datos_warehouse`, `corrida_carga`, `registro_calidad_carga`, `politica_gobierno_datos` — Principio II: el resultado de cada corrida es un registro real, no un estado en memoria de Airflow); MinIO `landing-zone` como raw del Extract; ClickHouse como warehouse final (fact_venta + dimensiones, Principio III). Ninguna tabla operativa de 001-009/011/012 se modifica — esta feature solo LEE de ellas como origen.
**Testing**: pytest para la lógica de idempotencia/incrementalidad de los jobs (con un ClickHouse/MinIO de prueba o mocks), contract tests para los endpoints de monitoreo (PostgreSQL real, sin depender de Airflow corriendo). Vitest + Vue Test Utils para la pantalla de monitoreo.
**Target Platform**: Docker Desktop + Airflow (ya fijado como infraestructura del proyecto, constitution.md).
**Project Type**: Web application (backend + frontend) + pipeline de datos (DAGs) — la única feature del proyecto con un componente de infraestructura de datos además del backend/frontend habitual.
**Performance Goals**: FR-011 — el warehouse debe quedar disponible para 009 (y opcionalmente 004) sin degradar PostgreSQL; toda lectura agregada pesada ocurre contra ClickHouse, nunca contra las tablas operativas en el camino de lectura de otra feature.
**Constraints**: Principio III (separación de motores) es el eje de toda esta feature — Extract (PostgreSQL/MinIO) → Load raw (MinIO `landing-zone`) → Load (ClickHouse) → Transform in-warehouse, exactamente el flujo ELT ya fijado en `constitution.md`, sin desviaciones. FR-005 exige exclusión mutua por destino (una corrida a la vez por entidad del modelo).
**Scale/Scope**: ~92,331 ventas y su detalle ya sembrados (carga base, FR-003) más las tablas de cliente/inventario/caja de 001-002/006; cargas incrementales diarias de bajo volumen relativo en producción.

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeo requerido después del diseño de la Fase 1.*

| # | Principio | Cumplimiento |
|---|---|---|
| I | Trazabilidad al BSC | PASS — cada FR traza a OO-7.1.1/7.1.2 (OT-7.1) u OO-7.5.1 (OT-7.5), ambos bajo OE-7, ver data-model.md §Trazabilidad. |
| II | Nivel Operativo = Registro Real (NON-NEGOTIABLE) | PASS — cada corrida de carga escribe una fila real en `corrida_carga` (filas cargadas/con error, duración, resultado) antes/durante/después de ejecutarse; nunca se reporta el estado de una corrida solo desde los logs de Airflow (SC-004). |
| III | Separación de Motores | PASS — es la feature que define el límite: PostgreSQL (origen + control del pipeline), MinIO `landing-zone` (raw), ClickHouse (warehouse). Ningún dato de negocio del warehouse se escribe en PostgreSQL ni viceversa. |
| IV | RBAC de Dos Niveles Obligatorio | PASS — módulo `TI` (ya reservado desde 006); tablas nuevas de esta feature bajo ese mismo módulo, sin módulo nuevo. |
| V | Backend/Frontend Desacoplados | PASS — nueva sub-ruta REST bajo `modules/ti/plataforma_datos/` (backend, expone las tablas de control) y vista Vue de monitoreo. |
| VI | Features Autocontenidas | PASS — vive en `modules/ti/plataforma_datos/` y en DAGs de Airflow propios; no modifica ninguna tabla de otra feature, solo lee de ellas. |
| VII | Anclaje al Dataset Real | PASS — la carga base (FR-003) trae el histórico real ya sembrado, sin generar datos sintéticos nuevos. |
| VIII | Simplicidad Justificada / DRY-KISS | PASS — 4 tablas de control, todas justificadas en research.md; reutiliza el patrón de partial unique index ya usado en `alertas_inventario`/`medios_pago` para la exclusión mutua de FR-005, y el patrón append-only ya usado en `politica_seguridad_pagos` (007) para la política de gobierno de datos. |
| IX | Guardrails de la IA sobre Specs (NON-NEGOTIABLE) | PASS — este plan no modifica `constitution.md`; no se detectó ninguna inconsistencia en spec.md que requiriera corrección en esta ronda. |
| X | Calidad / Testing / Seguridad | PASS — tests de idempotencia (reprocesar sin duplicar, FR-004) y de exclusión mutua (FR-005) son los más críticos de esta feature; contract tests para el monitoreo. |
| XI | Convenciones de Código y Arquitectura | PASS — capas router/service/repository para el monitoreo; los DAGs siguen la convención de Airflow ya fijada como infraestructura. |
| XII | Usabilidad y Diseño de Interfaz | PASS — el monitoreo de corridas muestra filas cargadas/con error/duración de forma clara para Jefe_TI, siguiendo `design-system.md`. |

**Resultado**: sin violaciones. No se requiere entrada en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```
specs/010-plataforma-datos-tactico-estrategico/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── plataforma-datos.md
└── tasks.md
```

### Source Code (repository root)

```
backend/
├── modules/
│   └── ti/
│       └── plataforma_datos/               # NUEVO (dentro del módulo TI ya reservado)
│           ├── router.py                   # monitoreo de corridas, modelo de datos, política
│           ├── service.py
│           ├── repository.py
│           └── schemas.py
└── tests/
    ├── contract/test_plataforma_datos.py
    └── integration/test_idempotencia_carga.py

data_platform/                              # NUEVO — no es "backend" de request/response, es infraestructura ELT
├── dags/
│   ├── carga_diaria_warehouse.py           # DAG principal, un task por entidad de modelo_datos_warehouse
│   └── dags_utils/
│       ├── extract_postgres.py
│       ├── load_landing_zone_minio.py
│       ├── load_clickhouse.py
│       └── transform_in_warehouse.py
└── clickhouse/
    └── schema_warehouse.sql                # DDL de fact_venta + dimensiones (ClickHouse, no PostgreSQL)

frontend/
├── src/
│   └── modules/
│       └── ti/
│           └── plataforma_datos/
│               ├── ModeloDatosWarehouse.vue    # NUEVO (US1)
│               ├── MonitoreoCorridas.vue       # NUEVO (US2/US3)
│               └── PoliticaGobiernoDatos.vue   # NUEVO (US4)
```

**Cruce entre módulos**: ninguno nuevo — todo vive dentro de `TI`, ya reservado desde 006. La única relación entre capas es de lectura: los DAGs leen PostgreSQL (todas las features 001-009/011/012) como origen, nunca escriben en sus tablas.

## Complexity Tracking

*Sin violaciones — tabla vacía.*

| Violación | Por qué es necesaria | Alternativa más simple rechazada |
|---|---|---|
| — | — | — |
