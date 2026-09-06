# Research: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico | **Fecha**: 2026-09-06

## Decisión 1: `modelo_datos_warehouse` como catálogo, no como schema embebido en código

**Decisión**: el modelo de datos único (FR-001) se documenta como una tabla catálogo en PostgreSQL (`modelo_datos_warehouse`), con una fila por entidad del warehouse (`fact_venta`, `dim_cliente`, `dim_producto`, `dim_tienda`, `dim_caja`, `dim_empleado`), su tabla de origen en PostgreSQL y si está `activa`. El DDL real de ClickHouse (`schema_warehouse.sql`) es generado/mantenido a partir de este catálogo, no al revés — así el Edge Case de spec.md ("una tabla operativa nueva no está todavía en el modelo... su carga queda pendiente") se implementa como una simple validación: el DAG solo carga entidades con `activa = true` en este catálogo.

**Alternativas consideradas**: definir el modelo únicamente como el DDL de ClickHouse, sin catálogo en PostgreSQL — rechazada porque el DDL de ClickHouse no es consultable por RBAC (Principio IV exige control de acceso vía PostgreSQL) ni deja un `definido_por`/`fecha_definicion` auditable (Principio II).

## Decisión 2: `corrida_carga` a nivel de entidad, con exclusión mutua vía índice único parcial

**Decisión**: una fila de `corrida_carga` corresponde a una entidad del modelo (ej. una corrida de `fact_venta`), no a todo el DAG diario completo — así FR-005 ("no permitir dos corridas simultáneas sobre el mismo destino") se implementa con el mismo patrón ya usado en `alertas_inventario`/`medios_pago`: un índice único parcial `WHERE estado = 'en_progreso'` sobre `entidad_id`, que la base de datos rechaza automáticamente si Airflow intentara lanzar dos tasks sobre el mismo destino a la vez — sin necesitar un lock distribuido aparte.

**Alternativas consideradas**: una tabla `corrida_dag` a nivel de DAG completo (una fila por ejecución diaria de todas las entidades juntas) — rechazada porque no permite reprocesar una sola entidad fallida sin reprocesar todas (contradice FR-004, reprocesamiento idempotente por partes).

## Decisión 3: idempotencia de la carga incremental (FR-003, FR-004)

**Decisión**: cada corrida incremental usa como filtro `updated_at`/`fecha_hora` de la tabla origen mayor a la fecha de fin de la última corrida **exitosa** de esa misma entidad (no de la última corrida, exitosa o no) — así una corrida fallida a medias nunca "avanza" el punto de corte, y el reproceso simplemente repite la misma ventana de tiempo. La carga hacia ClickHouse usa `INSERT` con deduplicación por clave natural (motor `ReplacingMergeTree` de ClickHouse, estándar para este patrón), de modo que reprocesar la misma ventana dos veces no duplica filas.

**Alternativas consideradas**: llevar un cursor de "última fila procesada" por `id` autoincremental — rechazada porque varias tablas origen (ej. `inventario`, que es upsert por PK compuesta, no solo INSERT) se actualizan in place; un cursor por fecha de modificación cubre tanto altas como cambios, mientras que un cursor por ID autoincremental solo cubre altas nuevas.

## Decisión 4: `registro_calidad_carga` — señalar, nunca bloquear (FR-007)

**Decisión**: una regla de calidad rota (ej. referencia a un `product_id` inexistente) genera una fila en `registro_calidad_carga` ligada a la corrida, pero esa fila específica del lote simplemente no se inserta en ClickHouse — el resto del lote continúa. Reglas mínimas de calidad para la primera versión: referencias rotas (FK lógica a una dimensión inexistente) y campos obligatorios vacíos en el fact — ambas verificables sin necesitar un motor de reglas configurable (Principio VIII: lo justo y necesario, no una DSL de validación).

**Alternativas consideradas**: motor de reglas de calidad configurable (tipo Great Expectations) — rechazado por Principio VIII para esta primera versión; las dos reglas mínimas del spec.md (referencias rotas, campos obligatorios vacíos) no justifican esa complejidad todavía.

## Decisión 5: `politica_gobierno_datos` — mismo patrón append-only que 006/007

**Decisión**: igual que `protocolo_escalamiento_incidentes` (006) y `politica_seguridad_pagos` (007) — cada actualización inserta una fila nueva, nunca se actualiza una fila existente; la vigente es la de `fecha_creacion` más reciente. Consistencia de patrón en todo el proyecto para "documento de referencia versionado" (Principio VIII, reutilización de un patrón ya validado tres veces).

## Decisión 6: BSC / RBAC — resumen

FR-001 a FR-006 y FR-011/FR-012 trazan a OT-7.1 (OO-7.1.1 modelo único, OO-7.1.2 carga automática); FR-007 a FR-010 trazan a OT-7.5 (OO-7.5.1 calidad/trazabilidad — OO-7.5.2 ya resuelto por 008). Gap de rol "Analista de Datos" resuelto como job automático (mismo patrón que 004/009), dejando a Jefe_TI como único actor humano real: define el modelo, monitorea corridas, mantiene la política. Sin módulo RBAC nuevo — todo bajo `TI`, ya reservado desde 006.
