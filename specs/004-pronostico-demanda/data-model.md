# Data Model: Pronóstico de Demanda con Variables Exógenas

Esta feature agrega 4 tablas nuevas (salida del modelo: versión, pronóstico, monitoreo, configuración) y extiende de forma aditiva 2 tablas ya construidas por 001 (`alertas_inventario`, `orden_compra_detalle`) con una columna de origen del cálculo. No crea ninguna tabla de entrada: las variables exógenas (`promociones`, `historial_precios`, `eventos_quiebre_stock`) y el historial de ventas (`ventas`, `venta_detalle`) ya existen desde 001/el esquema base (`research.md` Decisión 3).

## 1. Modelo de Pronóstico (versión)

**Tabla**: `modelo_demanda`

**Campos clave**: `modelo_id` (PK), `fecha_entrenamiento`, `metrica_precision_validacion` (WAPE, `research.md` Decisión 5), `estado` (pendiente/aprobado/rechazado/reemplazado), `fecha_resolucion`, `aprobado_por` (FK `empleados`, nullable), `observaciones`.

**Relaciones**: 1:N con `pronostico_demanda` y `monitoreo_precision_modelo`. N:1 con `empleados` (quien aprueba/rechaza).

**Validación**: `CHECK (estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))` — mismo patrón que `propuesta_ajuste_precio` de 003 (FR-004). Índice único parcial sobre una expresión constante `WHERE estado = 'aprobado'` — garantiza que solo puede existir un modelo vigente en producción a la vez (FR-005), mismo tipo de técnica que la alerta única activa de `alertas_inventario` (001).

**Transiciones**: `pendiente` → `aprobado` (reemplaza automáticamente al `aprobado` anterior, que pasa a `reemplazado`) o `pendiente` → `rechazado` (FR-004). No hay reapertura de un modelo rechazado o reemplazado — un nuevo entrenamiento genera una fila nueva.

## 2. Pronóstico de Demanda

**Tabla**: `pronostico_demanda`

**Campos clave**: `pronostico_id` (PK), `modelo_id` (FK), `product_id` (FK), `tienda_id` (FK), `semana`, `anio` (misma convención que `promociones`, `research.md` Decisión 1), `cantidad_pronosticada`, `created_at`.

**Relaciones**: N:1 con `modelo_demanda`, `productos`, `tiendas`.

**Validación**: `UNIQUE (modelo_id, product_id, tienda_id, semana, anio)` — una sola predicción por modelo/producto/tienda/semana. `cantidad_pronosticada >= 0`.

**Uso**: El pronóstico "vigente" para un producto/tienda/semana es el que pertenece al `modelo_demanda` con `estado = 'aprobado'`; el respaldo de rotación reciente de 001 aplica cuando no existe ninguna fila que cumpla esa condición (FR-007/FR-008).

## 3. Métrica de Monitoreo Semanal

**Tabla**: `monitoreo_precision_modelo`

**Campos clave**: `monitoreo_id` (PK), `modelo_id` (FK), `semana`, `anio`, `metrica_precision` (WAPE de esa semana contra demanda real ya observada), `supero_umbral_alerta` (boolean), `fecha_calculo`.

**Relaciones**: N:1 con `modelo_demanda`.

**Validación**: `UNIQUE (modelo_id, semana, anio)` — una sola medición semanal por modelo (FR-011).

**Uso**: Solo se calcula para el `modelo_demanda` vigente en producción en el momento de la corrida semanal (FR-011); su histórico completo por modelo permite ver tendencia, no solo el último valor (FR-013).

## 4. Configuración de Pronóstico

**Tabla**: `configuracion_pronostico`

**Campos clave**: `clave` (PK, ej. `precision_minima_aprobacion`, `umbral_degradacion_semanal_pct`, `historial_minimo_semanas`), `valor` (DECIMAL), `descripcion`.

**Relaciones**: Ninguna (tabla de configuración global, mismo patrón que `configuracion_pricing` de 003).

**Validación**: Ninguna validación cruzada — los umbrales de aprobación (FR-002/FR-003) y de degradación (FR-012) son valores de negocio, no reglas de integridad de datos.

## 5. Extensión de `alertas_inventario` (001) — origen del cálculo

**Cambio**: se agrega la columna `origen_calculo VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente' CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente'))`.

**Rationale**: FR-010 exige que la alerta de reposición deje visible si el punto usado vino del modelo o del respaldo — se agrega como columna nueva a la tabla ya construida por 001, no como tabla paralela (Principio VI/VIII). El valor por defecto (`rotacion_reciente`) preserva el comportamiento de 001 para instalaciones sin esta feature activa.

## 6. Extensión de `orden_compra_detalle` (001) — origen del cálculo

**Cambio**: se agrega la misma columna `origen_calculo VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente' CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente'))`.

**Rationale**: Mismo requisito de FR-010, aplicado a la sugerencia semanal de orden de compra (FR-009 de esta feature, que extiende FR-023 de 001).

## Reporte de Demanda Perdida (mensual) — sin tabla nueva

El reporte de FR-014/OO-5.2.2 es una consulta agregada sobre `eventos_quiebre_stock` (ya sembrado por 001, FR-022) unida con `productos.product_category` y `tiendas`, agrupada por tienda y categoría en el rango de fechas del mes — no requiere una tabla nueva, mismo criterio ya usado en el reporte mensual de margen de 003 (que tampoco tiene tabla propia, se calcula sobre `venta_detalle`).

## Trazabilidad cruzada (entidad → FR → OO/OT)

| Entidad | FR | OO/OT |
|---|---|---|
| Modelo de Pronóstico (`modelo_demanda`) | FR-001 a FR-005 | OO-7.2.1, OO-7.2.2 |
| Pronóstico de Demanda (`pronostico_demanda`) | FR-006 a FR-009 | OT-5.1, OT-2.1 |
| Extensión `alertas_inventario`/`orden_compra_detalle` (origen) | FR-010 | OT-5.1, OT-2.1 |
| Métrica de Monitoreo (`monitoreo_precision_modelo`) | FR-011 a FR-013 | OO-7.2.3 |
| Configuración (`configuracion_pronostico`) | FR-002, FR-003, FR-006, FR-012 | — (transversal) |
| Reporte de Demanda Perdida (consulta, sin tabla) | FR-014 | OO-5.2.2 |
