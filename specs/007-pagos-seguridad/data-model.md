# Data Model: Pagos y Seguridad

**Feature**: `007-pagos-seguridad` | **Date**: 2026-09-06

## Entidad ya reservada, sin migración de esquema

### Datáfono (`datafonos`, desde 001, extendida de estado por 006)

| Campo | Tipo | Notas |
|---|---|---|
| datafono_id | SERIAL PK | |
| caja_id | INTEGER FK → cajas | |
| modelo | VARCHAR(60) | |
| version_firmware | VARCHAR(30) | |
| fecha_ultima_actualizacion | DATE | |
| estado | VARCHAR(30) | `activo` \| `requiere_actualizacion` \| `fuera_servicio` — enum ya reservado desde 001; ensanchado a VARCHAR(30) por 006 (el valor `requiere_actualizacion` no cabía en el VARCHAR(20) original); `requiere_actualizacion` usado por 006 (no conformidad de seguridad), `fuera_servicio` usado por esta feature (disponibilidad operativa diaria) |

**Uso en esta feature**: FR-001 (marcar `fuera_servicio`), FR-002/FR-003 (restablecer: reevaluar conformidad vía la función ya existente de 006 — research.md Decisión 2 — resultado `activo` o `requiere_actualizacion`), FR-004 (consulta de solo lectura desde `modules/ventas/` para la advertencia previa al cobro).

## Extensión aditiva de entidad existente

### Medio de Pago (`medios_pago`, desde 001 — extendida)

| Campo | Tipo | Notas |
|---|---|---|
| medio_pago_id | SERIAL PK | (sin cambio) |
| nombre | VARCHAR(30) UNIQUE NOT NULL | (sin cambio) — Efectivo, Tarjeta, Digital, y los que se den de alta |
| aprobado | BOOLEAN NOT NULL DEFAULT true | **Nueva** — FR-007: solo `true` se ofrece en el punto de venta |
| aprobado_por | INTEGER FK → empleados, NULLABLE | **Nueva** — `Jefe_TI` que dio de alta (FR-005) |
| fecha_aprobacion | TIMESTAMP, NULLABLE | **Nueva** |
| fecha_baja | TIMESTAMP, NULLABLE | **Nueva** — se completa al dar de baja (FR-006), sin borrar la fila ni afectar `ventas.medio_pago_id` ya registradas |

**Migración**: `ALTER TABLE medios_pago ADD COLUMN aprobado BOOLEAN NOT NULL DEFAULT true; ADD COLUMN aprobado_por INTEGER REFERENCES empleados(empleado_id); ADD COLUMN fecha_aprobacion TIMESTAMP; ADD COLUMN fecha_baja TIMESTAMP;` — puramente aditiva, no rompe ninguna fila existente de 001 (los 3 medios de pago ya sembrados quedan `aprobado=true` por defecto).

### Venta (`ventas`, desde 001 — extendida)

| Campo | Tipo | Notas |
|---|---|---|
| venta_id | BIGINT PK | (sin cambio) |
| ... | ... | (resto sin cambio — ver `001/data-model.md`) |
| fecha_hora | TIMESTAMP NOT NULL | (sin cambio) — momento de confirmación, semántica intacta (research.md Decisión 6) |
| fecha_inicio_cobro | TIMESTAMP, NULLABLE | **Nueva** — solo ventas registradas en vivo desde esta feature (FR-015); `NULL` en las ~1.47M ventas sembradas de Dunnhumby y en cualquier venta previa a esta feature (research.md Decisión 7) |

**Migración**: `ALTER TABLE ventas ADD COLUMN fecha_inicio_cobro TIMESTAMP; CREATE INDEX idx_ventas_fecha_inicio_cobro ON ventas(fecha_inicio_cobro) WHERE fecha_inicio_cobro IS NOT NULL;` — puramente aditiva.

## Entidades nuevas

### Incidente de Seguridad de Pago (`incidente_seguridad_pago`)

| Campo | Tipo | Validación |
|---|---|---|
| incidente_seguridad_id | BIGSERIAL PK | |
| datafono_id | INTEGER FK → datafonos, NULLABLE | Edge Case: reporte genérico sin datáfono identificado |
| registrado_por | INTEGER NOT NULL FK → empleados | `Jefe_TI` |
| descripcion | TEXT NOT NULL | |
| estado | VARCHAR(20) NOT NULL DEFAULT 'abierto' | CHECK IN (`abierto`, `en_investigacion`, `cerrado`) |
| actualizado_por | INTEGER FK → empleados, NULLABLE | Última transición (FR-009) |
| fecha_actualizacion | TIMESTAMP, NULLABLE | |
| fecha_hora | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | Apertura |

**Transiciones de estado**:

```text
abierto --[Jefe_TI avanza investigación]--> en_investigacion
en_investigacion --[Jefe_TI cierra]--> cerrado
```

Entidad independiente de `incidentes_fraude` (006) — research.md Decisión 4. Un mismo `datafono_id` puede tener un `incidentes_fraude` (006) y un `incidente_seguridad_pago` abiertos simultáneamente, sin fusionarse (FR-010).

### Política de Seguridad de Pagos (`politica_seguridad_pagos`)

| Campo | Tipo | Validación |
|---|---|---|
| politica_id | BIGSERIAL PK | |
| texto | TEXT NOT NULL | |
| definido_por | INTEGER NOT NULL FK → empleados | `Jefe_TI` |
| fecha_creacion | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |

Append-only (research.md Decisión 5). Vigente = fila con `fecha_creacion` más reciente. Índice: `idx_politica_seguridad_pagos_fecha_creacion` (DESC).

## Extensión RBAC (seed, no cambio de esquema)

`role_permisos_tabla` no tenía filas para `incidente_seguridad_pago` ni `politica_seguridad_pagos` (tablas nuevas), ni para `datafonos`/`medios_pago` a nombre de los roles nuevos que esta feature necesita. Se agrega:

- `Encargado_Tienda`: UPDATE sobre `datafonos` (marcar `fuera_servicio`/restablecer — módulo `Finanzas`, ya tiene acceso de módulo desde 006), SELECT sobre `politica_seguridad_pagos` (FR-013), SELECT sobre `ventas` (tiempo de cobro por caja, FR-016 — módulo `Ventas`, ya tiene acceso de módulo desde 001/006).
- `Jefe_TI`: INSERT/UPDATE sobre `incidente_seguridad_pago`, INSERT sobre `politica_seguridad_pagos` — acceso ya concedido al módulo `Finanzas` (006, Decisión 10), se extiende a estas dos tablas nuevas. **Nuevo acceso concedido**: INSERT/UPDATE sobre `medios_pago` — módulo `Ventas`, primera vez que `Jefe_TI` opera ahí (research.md Decisión 9).
- `Jefe_Finanzas`: SELECT sobre `incidente_seguridad_pago` (conteo por periodo, FR-011), SELECT sobre `politica_seguridad_pagos` (FR-013).
- `Jefe_Comercial`: **Nuevo acceso concedido de solo lectura** al módulo `Ventas` — SELECT agregado sobre `ventas` para el reporte mensual de tiempo de cobro por tienda a nivel de red (FR-017), mismo patrón que `Jefe_Marketing`→`Ventas` en 005.
- `Cajero`: sin cambio de permiso — `fecha_inicio_cobro` se completa dentro del mismo INSERT de venta ya permitido desde 001.

## Trazabilidad Entidad → FR → OO/OT

| Entidad | FR | OO/OT |
|---|---|---|
| Datáfono (disponibilidad diaria) | FR-001, FR-002, FR-003, FR-004 | OO-4.1.1 |
| Medio de Pago | FR-005, FR-006, FR-007 | OO-4.1.2 |
| Incidente de Seguridad de Pago | FR-008, FR-009, FR-010, FR-011 | OO-6.3.3 |
| Política de Seguridad de Pagos | FR-012, FR-013, FR-014 | OO-6.3.3 (documento de referencia relacionado) |
| Venta (fecha_inicio_cobro) | FR-015, FR-018 | OT-4.2 |
| Reporte de tiempo de cobro (query) | FR-016, FR-017 | OO-4.2.2, OO-4.2.3 |
