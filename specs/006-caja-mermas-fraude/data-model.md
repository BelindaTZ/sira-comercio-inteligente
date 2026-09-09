# Data Model: Caja, Mermas y Fraude

**Feature**: `006-caja-mermas-fraude` | **Date**: 2026-09-06

## Entidades ya reservadas, pobladas por esta feature (sin cambio de esquema)

### Apertura de Caja (`apertura_caja`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| apertura_id | BIGSERIAL PK | |
| caja_id | INTEGER FK → cajas | |
| cajero_id | INTEGER FK → empleados | |
| fondo_inicial | DECIMAL(10,2) | CHECK >= 0 |
| fecha_hora | TIMESTAMP | default now |

**Uso en esta feature**: FR-001. También delimita el "turno" usado por el reporte mensual (research.md Decisión 3) — la apertura más reciente de la misma caja con `fecha_hora <= cierre.fecha_hora`.

### Cuadre de Caja (`cierre_caja`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| cierre_id | BIGSERIAL PK | |
| caja_id | INTEGER FK → cajas | |
| cajero_id | INTEGER FK → empleados | |
| total_esperado | DECIMAL(10,2) | Calculado por el backend (research.md Decisión 1) antes del INSERT, no confiado al cliente (Principio V) |
| total_registrado | DECIMAL(10,2) | Ingresado por el Cajero |
| diferencia | DECIMAL(10,2) GENERATED | `total_registrado - total_esperado`, columna ya reservada — cumple FR-003 sin lógica de aplicación |
| fecha_hora | TIMESTAMP | default now |

**Uso en esta feature**: FR-002, FR-003, FR-004 (marcado para revisión = consulta sobre el índice parcial ya reservado `idx_cierre_caja_diferencia WHERE diferencia <> 0`, sin columna de estado adicional), FR-005.

### Datáfono (`datafonos`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| datafono_id | SERIAL PK | |
| caja_id | INTEGER FK → cajas | |
| modelo | VARCHAR(60) | |
| version_firmware | VARCHAR(30) | |
| fecha_ultima_actualizacion | DATE | |
| estado | VARCHAR(20) | `activo` \| `requiere_actualizacion` \| `fuera_servicio` — enum ya reservado, `requiere_actualizacion` reutilizado como "no conforme" (research.md Decisión 4) |

**Uso en esta feature**: FR-006, FR-007 (job/consulta compara `version_firmware` contra `configuracion_seguridad_pagos` vigente y actualiza `estado`), FR-008 (al registrar actualización: `estado = 'activo'`, `fecha_ultima_actualizacion = CURRENT_DATE`).

**Pantalla (feature 013)** — `frontend/src/modules/caja/pages/DatafonosPage.vue`, arquetipo Gestión: fila de KPI de flota (terminales en inventario, no conformes al estándar, fuera de servicio, estándar vigente), tarjeta del estándar de seguridad y data-grid del inventario con chip de conformidad. Acciones: registrar datáfono (`POST /caja/datafonos`) y editar modelo/firmware/fecha (`PATCH /caja/datafonos/{id}`) — FR-006, Jefe_TI; registrar actualización (FR-008, sólo `requiere_actualizacion`); marcar fuera de servicio / restablecer (007 US1). El `estado` de conformidad lo calcula el sistema en el alta y en la edición contra el estándar vigente (FR-007). `scripts/preparar_demo.py::_caja_demo` siembra cajas + un datáfono por caja + el estándar vigente (el dataset Dunnhumby no trae infraestructura de sala).

## Entidades nuevas

### Configuración de Seguridad de Pagos (`configuracion_seguridad_pagos`)

| Campo | Tipo | Validación |
|---|---|---|
| config_id | BIGSERIAL PK | |
| version_minima_firmware | VARCHAR(30) NOT NULL | |
| vigente_desde | DATE NOT NULL DEFAULT CURRENT_DATE | |
| actualizado_por | INTEGER NOT NULL FK → empleados | Jefe_TI |
| fecha_creacion | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |

Append-only (research.md Decisión 5). Vigente = fila con `vigente_desde` más reciente. Índice: `idx_config_seguridad_pagos_vigente_desde` (DESC).

### Protocolo de Escalamiento (`protocolo_escalamiento`)

| Campo | Tipo | Validación |
|---|---|---|
| protocolo_id | BIGSERIAL PK | |
| texto | TEXT NOT NULL | |
| definido_por | INTEGER NOT NULL FK → empleados | Jefe_Finanzas |
| fecha_creacion | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |

Append-only (research.md Decisión 7). Vigente = fila más reciente por `fecha_creacion`.

**Pantalla (feature 013)** — `frontend/src/modules/caja/pages/ProtocoloEscalamientoPage.vue`
(componente compartido `DocumentoVersionado.vue`): documento de referencia
versionado — texto vigente + **historial de versiones** (nuevo endpoint
`GET /caja/protocolo-escalamiento/historial`, mismo RBAC que la lectura del
vigente; el diseño append-only ya lo implicaba) + publicar nueva versión
(Jefe_Finanzas). NO es un motor de flujo multi-paso (Assumptions): la "cadena de
escalamiento", la matriz RACI y los canales de notificación del mockup quedan
fuera de alcance.

### Umbral de Merma por Categoría (`umbral_merma_categoria`)

| Campo | Tipo | Validación |
|---|---|---|
| product_category | VARCHAR(100) PK | Mismo dominio que `productos.product_category` |
| porcentaje_umbral | DECIMAL(5,2) NOT NULL | CHECK > 0 AND <= 100 |
| definido_por | INTEGER NOT NULL FK → empleados | Jefe_Operaciones |
| fecha_actualizacion | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |

Actualizable in place, no append-only (research.md Decisión 8).

### Configuración de Caja (`configuracion_caja`)

| Campo | Tipo | Validación |
|---|---|---|
| clave | VARCHAR(60) PK | |
| valor | DECIMAL(12,6) NOT NULL | |
| descripcion | VARCHAR(250) | |

Clave/valor genérica, mismo patrón que `configuracion_pricing`/`configuracion_pronostico`/`configuracion_promociones`. Fila sembrada: `umbral_ajuste_inventario_anomalo = 10` (unidades, valor absoluto) — umbral configurable que FR-010 exige para señalar ajustes de inventario de 001 con diferencia negativa anómala en el reporte mensual de patrones.

## Extensión aditiva de entidad existente

### Incidente de Fraude (`incidentes_fraude`, desde 001 — extendida)

| Campo | Tipo | Notas |
|---|---|---|
| incidente_id | SERIAL PK | (sin cambio) |
| cierre_id | BIGINT FK → cierre_caja | **Pasa de NOT NULL a NULLABLE** (research.md Decisión 6) — presente solo si el incidente se originó en un patrón de cuadre (US3) |
| ajuste_id | BIGINT FK → ajustes_inventario | **Nueva, nullable** — presente solo si el incidente se originó en un ajuste de inventario anómalo (FR-010) |
| empleado_id | INTEGER NOT NULL FK → empleados | (sin cambio) — el incidente sigue su curso normalmente aunque el empleado ya tenga `fecha_baja` (FR-016) |
| descripcion | TEXT NOT NULL | (sin cambio) — evidencia que originó el incidente |
| acciones_tomadas | TEXT | **Nueva, nullable** — registradas por el Encargado de Tienda al aplicar el protocolo (FR-014) |
| resultado | VARCHAR(20) | **Nueva, nullable** — CHECK IN (`fraude_confirmado`, `descartado`), se completa solo al cerrar (US4 Acceptance Scenario 3) |
| estado | VARCHAR(20) | (sin cambio) `abierto` \| `en_revision` \| `cerrado` |
| actualizado_por | INTEGER FK → empleados | **Nueva, nullable** — quién ejecutó la última transición de estado (FR-015) |
| fecha_actualizacion | TIMESTAMP | **Nueva, nullable** — cuándo (FR-015) |
| fecha_hora | TIMESTAMP | (sin cambio) — fecha de apertura |

**Transiciones de estado**:

```text
abierto --[Encargado_Tienda aplica protocolo, registra acciones_tomadas]--> en_revision
en_revision --[Jefe_Finanzas cierra, registra resultado]--> cerrado
```

**Migración**: `ALTER TABLE incidentes_fraude ALTER COLUMN cierre_id DROP NOT NULL; ADD COLUMN ajuste_id BIGINT REFERENCES ajustes_inventario(ajuste_id); ADD COLUMN acciones_tomadas TEXT; ADD COLUMN resultado VARCHAR(20) CHECK (resultado IN ('fraude_confirmado','descartado')); ADD COLUMN actualizado_por INTEGER REFERENCES empleados(empleado_id); ADD COLUMN fecha_actualizacion TIMESTAMP;` — puramente aditiva/relajante, no rompe ninguna fila existente de 001.

**Pantalla (feature 013)** — `frontend/src/modules/caja/pages/IncidentesFraudePage.vue`,
arquetipo Gestión: fila de KPI (abiertos / en revisión / cerrados / cerrados como
fraude), data-grid del registro con origen (cuadre / ajuste / directo), evidencia,
acciones, resultado y "últ. cambio por # · fecha" (FR-015). Acciones por fila:
aplicar protocolo (Encargado, `prompt` de acciones → `en_revision`); cerrar
incidente (Jefe_Finanzas, modal fraude confirmado / descartado). "Registrar
incidente" abre uno directamente (FR-011, "registrado directamente"). El listado
`GET /caja/incidentes-fraude` enriquece cada fila con `empleado_nombre` (join a
`empleados`, sólo presentación). NO se implementa la telemetría del mockup (hash,
BIN, monto, riesgo %, motor SIRA, mapa de calor POS, reglas heurísticas): no está
en la entidad ni en la feature. `scripts/preparar_demo.py::_seguridad_pagos_demo`
siembra el protocolo, la política y 3 incidentes de ejemplo.

## Extensión RBAC (seed, no cambio de esquema)

`role_permisos_tabla` no tenía filas para `datafonos` ni `incidentes_fraude` (verificado — solo `apertura_caja`/`cierre_caja` para `Cajero` estaban sembradas desde 001). Esta feature agrega:

- `Cajero`: sin cambio (ya tiene `apertura_caja`/`cierre_caja` completos desde 001).
- `Encargado_Tienda`: SELECT sobre `cierre_caja`/`apertura_caja` (todas las cajas de su tienda), SELECT/INSERT/UPDATE sobre `incidentes_fraude` (abrir el caso al detectar algo sospechoso en su tienda y aplicar el protocolo; el `INSERT` se añade en la migración 0030 / feature 018 — cerrar como fraude confirmado sigue siendo del Jefe de Finanzas), SELECT sobre `protocolo_escalamiento`, `umbral_merma_categoria`, `mermas`, `venta_detalle` (seguimiento semanal).
- `Jefe_Finanzas`: SELECT sobre `cierre_caja`, `ajustes_inventario` (reporte), INSERT/UPDATE sobre `incidentes_fraude`, INSERT sobre `protocolo_escalamiento`.
- `Jefe_TI`: SELECT/INSERT/UPDATE sobre `datafonos`, INSERT sobre `configuracion_seguridad_pagos` — acceso concedido al módulo `Finanzas` (research.md Decisión 10), no solo a `TI`.
- `Jefe_Operaciones`: INSERT/UPDATE sobre `umbral_merma_categoria`.

## Trazabilidad Entidad → FR → OO/OT

| Entidad | FR | OO/OT |
|---|---|---|
| Apertura de Caja | FR-001 | OO-B.17 |
| Cuadre de Caja | FR-002, FR-003, FR-004, FR-005 | OO-6.1.1, OO-6.1.2, OO-6.1.3 |
| Datáfono | FR-006, FR-007, FR-008 | OO-6.3.1, OO-6.3.2 |
| Configuración de Seguridad de Pagos | FR-007 | OO-6.3.1 |
| Reporte de patrones (query) | FR-009, FR-010 | OO-6.2.1 |
| Incidente de Fraude | FR-011, FR-015, FR-016 | OO-6.2.2 |
| Protocolo de Escalamiento | FR-012, FR-013, FR-014 | OO-6.4.1, OO-6.4.2 |
| Umbral de Merma por Categoría | FR-017, FR-018, FR-019 | OO-5.5.1, OO-5.5.2 |
