# Data Model: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel | **Fecha**: 2026-09-06

## Tabla nueva 1: `registro_publicacion_dashboard`

```sql
CREATE TABLE registro_publicacion_dashboard (
    publicacion_id BIGSERIAL PRIMARY KEY,
    tipo_dashboard VARCHAR(20) NOT NULL
        CHECK (tipo_dashboard IN ('estrategico','tactico','operativo')),
    modulo_id INTEGER REFERENCES modulos(modulo_id),      -- solo aplica cuando tipo_dashboard = 'tactico'
    exito BOOLEAN NOT NULL,
    detalle_error TEXT,                                    -- solo cuando exito = false
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (tipo_dashboard = 'tactico' OR modulo_id IS NULL),
    CHECK (tipo_dashboard <> 'tactico' OR modulo_id IS NOT NULL),
    CHECK (exito OR detalle_error IS NOT NULL)
);
CREATE INDEX idx_registro_publicacion_tipo_fecha ON registro_publicacion_dashboard(tipo_dashboard, fecha_hora DESC);
```

Cubre FR-001, FR-004, FR-006, FR-008: cada corrida del job diario (o del trigger manual de FR-010) inserta una fila aquí, éxito o no.

## Tabla nueva 2: `dashboard_kpi`

```sql
CREATE TABLE dashboard_kpi (
    kpi_id BIGSERIAL PRIMARY KEY,
    publicacion_id BIGINT NOT NULL REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,
    dimension VARCHAR(60) NOT NULL,     -- 'OE-1'..'OE-8' (estratégico) o modulos.nombre (táctico) — research.md Decisión 2
    nombre_kpi VARCHAR(100) NOT NULL,
    valor DECIMAL(14,4),                -- NULL cuando disponible = false
    disponible BOOLEAN NOT NULL DEFAULT true,
    CHECK (disponible OR valor IS NULL)
);
CREATE INDEX idx_dashboard_kpi_publicacion ON dashboard_kpi(publicacion_id);
CREATE INDEX idx_dashboard_kpi_dimension ON dashboard_kpi(dimension);
```

Cubre FR-001, FR-002, FR-004: `disponible = false` es el mecanismo explícito para OE-4 (Market Share/NPS) — nunca se inserta un `valor` inventado para esa fila (Principio VII).

## Tabla nueva 3: `dashboard_operativo_estado`

```sql
CREATE TABLE dashboard_operativo_estado (
    estado_id BIGSERIAL PRIMARY KEY,
    publicacion_id BIGINT NOT NULL REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,  -- tipo_dashboard = 'operativo'
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    nombre_dashboard VARCHAR(60) NOT NULL,   -- ej. 'alertas_reposicion', 'cuadre_caja', 'seguimiento_merma'
    fecha_ultima_actualizacion TIMESTAMP,     -- MAX(fecha_hora) de la tabla fuente de esa feature para esa tienda
    disponible BOOLEAN NOT NULL              -- false si fecha_ultima_actualizacion tiene más de 1 día (FR-007)
);
CREATE INDEX idx_dashboard_operativo_estado_publicacion ON dashboard_operativo_estado(publicacion_id);
CREATE UNIQUE INDEX uq_dashboard_operativo_estado_tienda_nombre
    ON dashboard_operativo_estado(publicacion_id, tienda_id, nombre_dashboard);
CREATE INDEX idx_dashboard_operativo_estado_no_disponible
    ON dashboard_operativo_estado(tienda_id, nombre_dashboard) WHERE disponible = false;
```

Cubre FR-006, FR-007: solo lectura (`MAX(fecha_hora)`) contra las tablas fuente ya existentes de 001-007 — research.md Decisión 3. El índice parcial sobre `disponible = false` es lo que consulta directamente la alerta diaria de Jefe_TI.

## RBAC — módulos y tablas

`Direccion` es un módulo ya reservado desde el seed original pero sin ninguna feature que lo usara hasta ahora (primer consumidor real):

| Rol | Módulo | Tabla | select | insert | update | delete | Alcance |
|---|---|---|---|---|---|---|---|
| Gerente_General | Direccion | `registro_publicacion_dashboard`, `dashboard_kpi` (dimension tipo OE) | ✔ (ya global) | ✘ | ✘ | ✘ | Toda la red — ya tiene lectura global en todos los módulos por seed. |
| Jefe_Comercial | Comercial | `dashboard_kpi` (dimension='Comercial') | ✔ | ✘ | ✘ | ✘ | Solo filas con `dimension='Comercial'`, validado en capa de servicio (igual que el alcance por tienda de 012). |
| Jefe_Marketing | Marketing_CRM | `dashboard_kpi` (dimension='Marketing_CRM') | ✔ | ✘ | ✘ | ✘ | Igual criterio, su propio módulo. |
| Jefe_Operaciones | Operaciones | `dashboard_kpi` (dimension='Operaciones') | ✔ | ✘ | ✘ | ✘ | Igual criterio. |
| Jefe_Finanzas | Finanzas | `dashboard_kpi` (dimension='Finanzas') | ✔ | ✘ | ✘ | ✘ | Igual criterio. |
| Jefe_RRHH | RRHH | `dashboard_kpi` (dimension='RRHH') | ✔ | ✘ | ✘ | ✘ | Igual criterio. |
| Jefe_TI | TI | `registro_publicacion_dashboard`, `dashboard_kpi` (dimension='TI'), `dashboard_operativo_estado` | ✔ | ✔ (solo el trigger manual FR-010) | ✘ | ✘ | `dashboard_operativo_estado`: toda la red (verificación diaria, OO-7.4.3). |

Sin `delete` ni `update` para ningún rol: un snapshot publicado es histórico e inmutable — una publicación con error se corrige generando una nueva fila, nunca editando la anterior (mismo criterio de append-only ya usado en `politica_seguridad_pagos` de 007).

## Trazabilidad: FR → Entidad → OO/OT

| FR | Entidad / campo | OO / OT |
|---|---|---|
| FR-001, FR-002 | `registro_publicacion_dashboard` (tipo='estrategico'), `dashboard_kpi` (dimension=OE-x) | OO-7.4.1 / OT-7.4 |
| FR-003 | Lectura de `dashboard_kpi`/`registro_publicacion_dashboard` más reciente | OO-7.4.1 / OT-7.4 |
| FR-004, FR-005 | `registro_publicacion_dashboard` (tipo='tactico', modulo_id), `dashboard_kpi` (dimension=nombre módulo) | OO-7.4.2 / OT-7.4 |
| FR-006, FR-007 | `dashboard_operativo_estado` | OO-7.4.3 / OT-7.4 |
| FR-008 | `registro_publicacion_dashboard.fecha_hora/exito` (los tres tipos) | OT-7.4 (calidad de dato, Principio II) |
| FR-009 | Diseño del job (batch nocturno, snapshot pequeño) — sin entidad propia | OT-7.4 |
| FR-010 | Endpoint de trigger manual sobre el mismo job — sin entidad propia (solo entorno de desarrollo) | OT-7.4 |
