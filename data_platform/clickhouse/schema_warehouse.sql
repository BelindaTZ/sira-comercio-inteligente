-- ============================================================================
-- SIRA — Warehouse táctico-estratégico (ClickHouse, OLAP)
-- Feature 010-plataforma-datos-tactico-estrategico · data-model.md / research.md Decisión 3
--
-- Principio III (Separación de Motores): estas tablas viven SÓLO en ClickHouse.
-- Ningún dato de negocio del warehouse se escribe en PostgreSQL. PostgreSQL sólo
-- guarda el CONTROL del pipeline (modelo_datos_warehouse, corrida_carga,
-- registro_calidad_carga, politica_gobierno_datos).
--
-- Motor ReplacingMergeTree en todas: reprocesar la misma ventana de una corrida
-- incremental no duplica filas (FR-004, idempotencia). La clave de ordenamiento
-- ES la clave natural de deduplicación; `_version` (fecha de carga) resuelve cuál
-- gana ante colisión. Las dimensiones son upsert por PK del operativo; el fact
-- es upsert por `venta_detalle_id` (PK real del detalle de venta en PostgreSQL).
-- ============================================================================

CREATE DATABASE IF NOT EXISTS sira_warehouse;

-- ---------------------------------------------------------------------------
-- Dimensiones
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sira_warehouse.dim_tienda
(
    tienda_id     UInt32,
    codigo        String,
    nombre        String,
    ciudad        String DEFAULT '',
    activa        UInt8  DEFAULT 1,
    _version      DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY tienda_id;

CREATE TABLE IF NOT EXISTS sira_warehouse.dim_producto
(
    product_id        UInt32,
    product_category  String DEFAULT '',
    product_type      String DEFAULT '',
    department        String DEFAULT '',
    brand             String DEFAULT '',
    es_perecedero     UInt8  DEFAULT 0,
    clasificacion_abc String DEFAULT '',
    _version          DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY product_id;

CREATE TABLE IF NOT EXISTS sira_warehouse.dim_cliente
(
    household_id    UInt32,
    fecha_registro  Date DEFAULT toDate('1970-01-01'),
    activo          UInt8 DEFAULT 1,
    age             String DEFAULT '',
    income          String DEFAULT '',
    marital_status  String DEFAULT '',
    _version        DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY household_id;

CREATE TABLE IF NOT EXISTS sira_warehouse.dim_caja
(
    caja_id    UInt32,
    tienda_id  UInt32,
    nombre     String DEFAULT '',
    activa     UInt8  DEFAULT 1,
    _version   DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY caja_id;

CREATE TABLE IF NOT EXISTS sira_warehouse.dim_empleado
(
    empleado_id        UInt32,
    tienda_id          UInt32 DEFAULT 0,
    nombre             String DEFAULT '',
    fecha_contratacion Date   DEFAULT toDate('1970-01-01'),
    activo             UInt8  DEFAULT 1,
    _version           DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
ORDER BY empleado_id;

-- ---------------------------------------------------------------------------
-- Fact
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sira_warehouse.fact_venta
(
    venta_detalle_id UInt64,
    venta_id         UInt64,
    fecha_hora       DateTime,
    fecha            Date MATERIALIZED toDate(fecha_hora),
    semana           UInt8,
    tienda_id        UInt32,
    cajero_id        UInt32,
    household_id     UInt32 DEFAULT 0,       -- 0 = venta anónima
    product_id       UInt32,
    cantidad         Int32,
    sales_value      Decimal(12, 2),
    retail_disc      Decimal(12, 2) DEFAULT 0,
    coupon_disc      Decimal(12, 2) DEFAULT 0,
    anulada          UInt8 DEFAULT 0,
    _version         DateTime DEFAULT now()
)
ENGINE = ReplacingMergeTree(_version)
PARTITION BY toYYYYMM(fecha_hora)
ORDER BY (venta_detalle_id);
