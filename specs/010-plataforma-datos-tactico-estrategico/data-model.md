# Data Model: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico | **Fecha**: 2026-09-06

Todas las tablas de esta sección son de **control del pipeline**, viven en PostgreSQL (Principio II/III) y no contienen datos de negocio del warehouse — esos viven exclusivamente en ClickHouse (`data_platform/clickhouse/schema_warehouse.sql`, fuera del alcance de este documento por Principio III).

> **Ronda 1**: creadas por la migración Alembic `0018` (sobre `0017` de la feature 012) y por
> el bloque EXTENSIÓN de `01_operativo_postgres.sql`. RBAC: `Jefe_TI` ya tiene el módulo `TI`
> desde `0011` (feature 004); `0018` sólo agrega el permiso de tabla de las 4 tablas nuevas.

## Tabla nueva 1: `modelo_datos_warehouse`

```sql
CREATE TABLE modelo_datos_warehouse (
    entidad_id SERIAL PRIMARY KEY,
    nombre_entidad VARCHAR(60) NOT NULL UNIQUE,      -- 'fact_venta', 'dim_cliente', 'dim_producto', 'dim_tienda', 'dim_caja', 'dim_empleado'
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('fact','dimension')),
    tabla_origen_postgres VARCHAR(60) NOT NULL,       -- ej. 'ventas', 'clientes' — tabla de origen en el operativo
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT true,             -- false = definida pero su carga aún no arranca (Edge Case)
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_definicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

Cubre FR-001 y el Edge Case de tabla operativa nueva: el DAG (`carga_diaria_warehouse.py`) solo genera tasks para filas con `activa = true` — research.md Decisión 1.

## Tabla nueva 2: `corrida_carga`

```sql
CREATE TABLE corrida_carga (
    corrida_id BIGSERIAL PRIMARY KEY,
    entidad_id INTEGER NOT NULL REFERENCES modelo_datos_warehouse(entidad_id),
    tipo_carga VARCHAR(12) NOT NULL CHECK (tipo_carga IN ('completa','incremental')),
    origen VARCHAR(20) NOT NULL CHECK (origen IN ('postgres','minio_landing_zone')),
    estado VARCHAR(12) NOT NULL DEFAULT 'en_progreso'
        CHECK (estado IN ('en_progreso','exitosa','fallida')),
    filas_cargadas INTEGER,
    filas_error INTEGER NOT NULL DEFAULT 0,
    fecha_inicio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_fin TIMESTAMP,
    CHECK (estado = 'en_progreso' OR fecha_fin IS NOT NULL),
    CHECK (estado <> 'exitosa' OR filas_cargadas IS NOT NULL)
);
-- FR-005: nunca dos corridas activas a la vez sobre la misma entidad (mismo patrón de alertas_inventario/medios_pago).
CREATE UNIQUE INDEX uq_corrida_carga_en_progreso
    ON corrida_carga(entidad_id) WHERE estado = 'en_progreso';
CREATE INDEX idx_corrida_carga_entidad_fecha ON corrida_carga(entidad_id, fecha_inicio DESC);
```

`duracion_segundos` se deriva en la capa de lectura (`fecha_fin - fecha_inicio`), no se persiste — evita una columna generada que solo tiene sentido cuando `fecha_fin` ya existe. Cubre FR-002 a FR-006, FR-012 — research.md Decisiones 2 y 3.

## Tabla nueva 3: `registro_calidad_carga`

```sql
CREATE TABLE registro_calidad_carga (
    registro_id BIGSERIAL PRIMARY KEY,
    corrida_id BIGINT NOT NULL REFERENCES corrida_carga(corrida_id) ON DELETE CASCADE,
    descripcion_problema VARCHAR(300) NOT NULL,       -- ej. "referencia rota: product_id 99999 no existe en dim_producto"
    identificador_registro VARCHAR(100),               -- clave natural o PK del registro señalado, para trazabilidad
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_registro_calidad_carga_corrida ON registro_calidad_carga(corrida_id);
```

Cubre FR-007 — research.md Decisión 4. Un registro señalado aquí es el que NO se insertó en ClickHouse para esa corrida (el resto del lote sí).

## Tabla nueva 4: `politica_gobierno_datos`

```sql
CREATE TABLE politica_gobierno_datos (
    politica_id BIGSERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
-- Append-only: la vigente es MAX(fecha_creacion). Mismo patrón que protocolo_escalamiento_incidentes (006)
-- y politica_seguridad_pagos (007) — sin UPDATE/DELETE.
```

Cubre FR-009, FR-010 — research.md Decisión 5.

## RBAC — extensión de tabla sobre módulo ya existente (`TI`)

| Rol | Tabla | select | insert | update | delete | Alcance |
|---|---|---|---|---|---|---|
| Jefe_TI | `modelo_datos_warehouse` | ✔ | ✔ | ✔ | ✘ | Define y activa/desactiva entidades del modelo. |
| Jefe_TI | `corrida_carga` | ✔ | ✘ | ✘ | ✘ | Solo lectura — las filas las escribe el DAG (cuenta de servicio del pipeline, fuera del RBAC de usuario final). |
| Jefe_TI | `registro_calidad_carga` | ✔ | ✘ | ✘ | ✘ | Solo lectura, igual que `corrida_carga`. |
| Jefe_TI | `politica_gobierno_datos` | ✔ | ✔ | ✘ | ✘ | Append-only — nunca `update`/`delete`, igual que 006/007. |

## Trazabilidad: FR → Entidad / campo → OO/OT

| FR | Entidad / campo | OO / OT |
|---|---|---|
| FR-001 | `modelo_datos_warehouse` | OO-7.1.1 / OT-7.1 |
| FR-002, FR-003, FR-004, FR-005 | `corrida_carga` (tipo_carga, estado, índice único parcial) | OO-7.1.2 / OT-7.1 |
| FR-006 | Lectura de `corrida_carga` | OO-7.1.2 / OT-7.1 |
| FR-007 | `registro_calidad_carga` | OO-7.5.1 / OT-7.5 |
| FR-008 | `corrida_carga` + `registro_calidad_carga` (origen, destino, filas, resultado) | OO-7.5.1 / OT-7.5 |
| FR-009, FR-010 | `politica_gobierno_datos` | OO-7.5.1 / OT-7.5 |
| FR-011 | ClickHouse (fuera de PostgreSQL, sin entidad de control propia) | OT-7.1 |
| FR-012 | Endpoint de trigger manual sobre `corrida_carga` — sin entidad propia | OT-7.1 |
