# Data Model: Recursos Humanos

**Feature**: `011-recursos-humanos` | **Date**: 2026-09-06

## Entidades ya reservadas, pobladas por esta feature (sin cambio de esquema)

### Capacitación (`capacitaciones`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| capacitacion_id | SERIAL PK | |
| nombre | VARCHAR(150) NOT NULL | |
| descripcion | TEXT | |

**Uso en esta feature**: FR-003. Los roles objetivo no se persisten aquí (research.md Decisión 2) — se resuelven solo en el momento de crear la capacitación, para el fan-out hacia `empleado_capacitacion`.

### Registro de Capacitación de Empleado (`empleado_capacitacion`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| empleado_id | INTEGER FK → empleados | PK compuesta |
| capacitacion_id | INTEGER FK → capacitaciones | PK compuesta |
| fecha_completado | DATE, NULLABLE | `NULL` = pendiente |

**Uso en esta feature**: FR-004 (fan-out al programar, research.md Decisión 2), FR-005 (consulta de cumplimiento, restringida por tienda para `Encargado_Tienda`).

### Encuesta de Clima Laboral (`clima_laboral`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| encuesta_id | SERIAL PK | |
| tienda_id | INTEGER FK → tiendas, NULLABLE | |
| periodo | VARCHAR(10) NOT NULL | Formato `'AAAA-Sn'`, ej. `'2026-S2'` |
| resultado_promedio | DECIMAL(4,2) CHECK BETWEEN 0 AND 10 | |
| fecha | DATE NOT NULL DEFAULT CURRENT_DATE | |

**Uso en esta feature**: FR-006 (registro), FR-007 (cruce con rotación calculada, research.md Decisión 3), FR-010 (sin fila = sin dato, nunca inventado).

### Plan de Sucesión (`plan_sucesion`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| sucesion_id | SERIAL PK | |
| puesto_id | INTEGER NOT NULL FK → roles_puesto | |
| empleado_candidato_id | INTEGER NOT NULL FK → empleados | |
| fecha | DATE NOT NULL DEFAULT CURRENT_DATE | |

**Uso en esta feature**: FR-008 (registro de candidato), FR-009 (consulta de puestos críticos sin fila coincidente aquí, research.md Decisión 4).

## Extensión aditiva de entidad existente

### Puesto (`roles_puesto`, desde 001 — extendida)

| Campo | Tipo | Notas |
|---|---|---|
| puesto_id | SERIAL PK | (sin cambio) |
| nombre | VARCHAR(60) UNIQUE NOT NULL | (sin cambio) |
| descripcion | VARCHAR(200) | (sin cambio) |
| es_critico | BOOLEAN NOT NULL DEFAULT false | **Nueva** — FR-001 |

**Migración**: `ALTER TABLE roles_puesto ADD COLUMN es_critico BOOLEAN NOT NULL DEFAULT false;` — puramente aditiva, no rompe ninguna fila existente de 001.

## Entidad nueva

### Acción de Retención (`acciones_retencion`)

| Campo | Tipo | Validación |
|---|---|---|
| accion_id | BIGSERIAL PK | |
| empleado_id | INTEGER NOT NULL FK → empleados | Puede ser un empleado en un puesto no crítico (Edge Case, se permite) |
| fecha | DATE NOT NULL DEFAULT CURRENT_DATE | |
| descripcion | TEXT NOT NULL | |

Única tabla nueva de esta feature — research.md Decisión 1. Índice: `idx_acciones_retencion_empleado_id`.

## Extensión RBAC (seed, no cambio de esquema)

Extiende el módulo `RRHH` ya reservado y primero usado por 008 (`Jefe_RRHH`, para `empleados`):

- `Jefe_RRHH`: UPDATE sobre `roles_puesto` (marcar `es_critico`), INSERT/SELECT sobre `acciones_retencion`, INSERT sobre `capacitaciones`, INSERT/UPDATE sobre `empleado_capacitacion`, INSERT/SELECT sobre `clima_laboral`, INSERT/SELECT sobre `plan_sucesion`.
- `Encargado_Tienda`: **Nuevo acceso concedido de solo lectura** al módulo `RRHH` — SELECT sobre `empleado_capacitacion` (restringido a su propia tienda vía `empleados.tienda_id`, FR-005), mismo patrón que `Jefe_Marketing`→`Ventas` (005) y `Jefe_Comercial`→`Ventas` (007).

## Trazabilidad Entidad → FR → OO

| Entidad | FR | OO |
|---|---|---|
| Puesto (es_critico) | FR-001 | OO-8.1.1 |
| Acción de Retención | FR-002 | OO-8.1.2 |
| Capacitación | FR-003 | OO-8.2.1 |
| Registro de Capacitación de Empleado | FR-004, FR-005 | OO-8.2.2 |
| Encuesta de Clima Laboral | FR-006, FR-010 | OO-8.3.1 |
| Rotación (query) | FR-007 | OO-8.3.2 |
| Plan de Sucesión | FR-008, FR-009 | OO-8.4.1, OO-8.4.2 |
