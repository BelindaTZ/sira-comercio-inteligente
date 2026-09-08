-- ============================================================================
-- SIRA — Sistema Inteligente de Retail Adaptativo (Marzú Retail Group)
-- Modelo de Base de Datos OPERATIVA — PostgreSQL (OLTP)
-- Convenciones: tablas en plural, snake_case, idx_tabla_columna, fk_tabla_columna
-- Orden de ejecución: respeta las dependencias de FK (ver módulos en orden)
-- ============================================================================

-- ============================================================================
-- MÓDULO 1: ORGANIZACIÓN Y SEGURIDAD (RBAC)
-- ============================================================================

CREATE TABLE tiendas (
    tienda_id SERIAL PRIMARY KEY,
    codigo VARCHAR(10) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    direccion VARCHAR(200),
    ciudad VARCHAR(100),
    telefono VARCHAR(20),
    fecha_apertura DATE,
    activa BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_tiendas_codigo ON tiendas(codigo);

CREATE TABLE roles_puesto (
    puesto_id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    descripcion VARCHAR(200)
);

CREATE TABLE empleados (
    empleado_id SERIAL PRIMARY KEY,
    tienda_id INTEGER REFERENCES tiendas(tienda_id) ON DELETE RESTRICT,
    puesto_id INTEGER NOT NULL REFERENCES roles_puesto(puesto_id) ON DELETE RESTRICT,
    nombre VARCHAR(150) NOT NULL,
    email VARCHAR(150) UNIQUE,
    telefono VARCHAR(20),
    fecha_contratacion DATE NOT NULL,
    fecha_baja DATE,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_empleados_tienda_id ON empleados(tienda_id);
CREATE INDEX idx_empleados_puesto_id ON empleados(puesto_id);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    descripcion VARCHAR(200)
);

CREATE TABLE usuarios (
    usuario_id SERIAL PRIMARY KEY,
    empleado_id INTEGER UNIQUE NOT NULL REFERENCES empleados(empleado_id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE RESTRICT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    activo BOOLEAN NOT NULL DEFAULT true,
    ultimo_login TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_usuarios_role_id ON usuarios(role_id);

CREATE TABLE modulos (
    modulo_id SERIAL PRIMARY KEY,
    nombre VARCHAR(60) UNIQUE NOT NULL,
    descripcion VARCHAR(200)
);

-- Rol obtiene acceso a un MÓDULO...
CREATE TABLE role_permisos_modulo (
    role_id INTEGER NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    modulo_id INTEGER NOT NULL REFERENCES modulos(modulo_id) ON DELETE CASCADE,
    puede_ver BOOLEAN NOT NULL DEFAULT false,
    puede_editar BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (role_id, modulo_id)
);

-- ...y dentro de ese módulo, permiso fino por TABLA (no puede existir sin el acceso al módulo)
CREATE TABLE role_permisos_tabla (
    role_id INTEGER NOT NULL,
    modulo_id INTEGER NOT NULL,
    nombre_tabla VARCHAR(60) NOT NULL,
    can_select BOOLEAN NOT NULL DEFAULT false,
    can_insert BOOLEAN NOT NULL DEFAULT false,
    can_update BOOLEAN NOT NULL DEFAULT false,
    can_delete BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (role_id, modulo_id, nombre_tabla),
    CONSTRAINT fk_role_permisos_tabla_modulo
        FOREIGN KEY (role_id, modulo_id) REFERENCES role_permisos_modulo(role_id, modulo_id) ON DELETE CASCADE
);

-- ============================================================================
-- MÓDULO 2: CATÁLOGO DE PRODUCTOS
-- ============================================================================

CREATE TABLE fabricantes (
    manufacturer_id INTEGER PRIMARY KEY,          -- natural key (viene del dataset)
    nombre VARCHAR(150)
);

CREATE TABLE productos (
    product_id INTEGER PRIMARY KEY,               -- natural key (viene del dataset, products.csv)
    manufacturer_id INTEGER REFERENCES fabricantes(manufacturer_id),
    department VARCHAR(60),
    brand VARCHAR(20) CHECK (brand IN ('Private','National')),
    product_category VARCHAR(100),
    product_type VARCHAR(100),
    package_size VARCHAR(30),
    costo DECIMAL(10,2) CHECK (costo >= 0),                 -- NO viene del dataset, se enriquece
    precio_base DECIMAL(10,2) CHECK (precio_base >= 0),     -- NO viene del dataset, se enriquece
    es_perecedero BOOLEAN NOT NULL DEFAULT false,
    vida_util_dias INTEGER,
    clasificacion_abc CHAR(1) CHECK (clasificacion_abc IN ('A','B','C')),
    es_ancla BOOLEAN NOT NULL DEFAULT false,
    codigo_barras VARCHAR(20) UNIQUE,       -- Sembrados: EAN-13 sintético con checksum válido, rango GS1 20-29 (uso interno, no resuelve en registros reales) -- generado en la carga inicial. Productos agregados en vivo por la UI: barcode real del producto físico.
    imagen_url VARCHAR(500),                -- Sembrados: ícono genérico placeholder por categoría (bucket MinIO producto-imagenes), no pretende ser la foto real. Productos agregados en vivo: imagen real de Open Food Facts o foto subida a MinIO.
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_productos_department ON productos(department);
CREATE INDEX idx_productos_codigo_barras ON productos(codigo_barras) WHERE codigo_barras IS NOT NULL;
CREATE INDEX idx_productos_category ON productos(product_category);
CREATE INDEX idx_productos_clasificacion_abc ON productos(clasificacion_abc);

CREATE TABLE historial_precios (
    historial_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    tienda_id INTEGER REFERENCES tiendas(tienda_id),
    precio DECIMAL(10,2) NOT NULL CHECK (precio >= 0),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)
);
CREATE INDEX idx_historial_precios_product_id ON historial_precios(product_id);

CREATE TABLE margenes_objetivo (
    product_category VARCHAR(100) PRIMARY KEY,
    margen_objetivo_pct DECIMAL(5,2) NOT NULL CHECK (margen_objetivo_pct BETWEEN 0 AND 100)
);

-- ============================================================================
-- MÓDULO 3: CLIENTES / CRM
-- ============================================================================

CREATE TABLE clientes (
    household_id INTEGER PRIMARY KEY,             -- natural key (viene del dataset)
    nombre VARCHAR(150),
    email VARCHAR(150) UNIQUE,
    telefono VARCHAR(20),
    fecha_nacimiento DATE,
    fecha_registro DATE NOT NULL DEFAULT CURRENT_DATE,
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE clientes_demograficos (
    household_id INTEGER PRIMARY KEY REFERENCES clientes(household_id) ON DELETE CASCADE,
    age VARCHAR(20),
    income VARCHAR(20),
    home_ownership VARCHAR(20) CHECK (home_ownership IN ('Homeowner','Renter','Unknown')),
    marital_status VARCHAR(20) CHECK (marital_status IN ('Married','Single','Unknown')),
    household_size VARCHAR(10),
    household_comp VARCHAR(30),
    kids_count VARCHAR(10)
);

CREATE TABLE niveles_fidelizacion (
    nivel_id SERIAL PRIMARY KEY,
    nombre VARCHAR(40) UNIQUE NOT NULL,
    umbral_clv_min DECIMAL(12,2) NOT NULL
);

CREATE TABLE cliente_clv (
    clv_id BIGSERIAL PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    nivel_id INTEGER REFERENCES niveles_fidelizacion(nivel_id),
    clv_score DECIMAL(12,2) NOT NULL,
    fecha_calculo DATE NOT NULL,
    UNIQUE (household_id, fecha_calculo)
);
CREATE INDEX idx_cliente_clv_household_id ON cliente_clv(household_id);

CREATE TABLE churn_score (
    churn_id BIGSERIAL PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    score DECIMAL(5,4) NOT NULL CHECK (score BETWEEN 0 AND 1),
    ciclo_compra_dias INTEGER,
    fecha_calculo DATE NOT NULL,
    UNIQUE (household_id, fecha_calculo)
);
CREATE INDEX idx_churn_score_household_id ON churn_score(household_id);

CREATE TABLE campanas (
    campaign_id INTEGER PRIMARY KEY,               -- natural key (viene del dataset)
    campaign_type VARCHAR(20),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    CHECK (end_date >= start_date)
);

CREATE TABLE campana_cliente (
    campaign_id INTEGER NOT NULL REFERENCES campanas(campaign_id) ON DELETE CASCADE,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    PRIMARY KEY (campaign_id, household_id)
);

CREATE TABLE cupones (
    coupon_upc VARCHAR(20) NOT NULL,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    campaign_id INTEGER NOT NULL REFERENCES campanas(campaign_id) ON DELETE CASCADE,
    PRIMARY KEY (coupon_upc, product_id, campaign_id)
);

CREATE TABLE cupon_redimido (
    redemption_id BIGSERIAL PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    coupon_upc VARCHAR(20) NOT NULL,
    campaign_id INTEGER NOT NULL REFERENCES campanas(campaign_id),
    redemption_date DATE NOT NULL
);
CREATE INDEX idx_cupon_redimido_household_id ON cupon_redimido(household_id);

CREATE TABLE eventos_cliente (
    evento_id BIGSERIAL PRIMARY KEY,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    tipo_evento VARCHAR(30) NOT NULL CHECK (tipo_evento IN ('cumpleanos','aniversario_registro')),
    fecha DATE NOT NULL
);
CREATE INDEX idx_eventos_cliente_household_id ON eventos_cliente(household_id);

-- ============================================================================
-- MÓDULO 4: PROMOCIONES
-- ============================================================================

CREATE TABLE display_locations (
    codigo VARCHAR(2) PRIMARY KEY,
    descripcion VARCHAR(60) NOT NULL
);

CREATE TABLE mailer_locations (
    codigo VARCHAR(2) PRIMARY KEY,
    descripcion VARCHAR(60) NOT NULL
);

CREATE TABLE promociones (
    promocion_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    tienda_id INTEGER REFERENCES tiendas(tienda_id),
    display_location VARCHAR(2) REFERENCES display_locations(codigo),
    mailer_location VARCHAR(2) REFERENCES mailer_locations(codigo),
    semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
    anio INTEGER NOT NULL
);
CREATE INDEX idx_promociones_product_id ON promociones(product_id);
CREATE INDEX idx_promociones_semana ON promociones(semana, anio);

-- ============================================================================
-- MÓDULO 5: VENTAS
-- ============================================================================

CREATE TABLE medios_pago (
    medio_pago_id SERIAL PRIMARY KEY,
    nombre VARCHAR(30) UNIQUE NOT NULL             -- Efectivo, Tarjeta, Digital
);

-- OJO: el dataset (transactions.csv) NO trae medio de pago; se sintetiza al cargar.
CREATE TABLE ventas (
    venta_id BIGINT PRIMARY KEY,                   -- basket_id del dataset
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cajero_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    household_id INTEGER REFERENCES clientes(household_id),   -- NULL = venta anónima
    medio_pago_id INTEGER REFERENCES medios_pago(medio_pago_id),
    fecha_hora TIMESTAMP NOT NULL,
    semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
    total DECIMAL(12,2) NOT NULL DEFAULT 0 CHECK (total >= 0),
    anulada BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_ventas_tienda_id ON ventas(tienda_id);
CREATE INDEX idx_ventas_household_id ON ventas(household_id);
CREATE INDEX idx_ventas_fecha_hora ON ventas(fecha_hora);

CREATE TABLE venta_detalle (
    venta_detalle_id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas(venta_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    sales_value DECIMAL(10,2) NOT NULL CHECK (sales_value >= 0),
    retail_disc DECIMAL(10,2) NOT NULL DEFAULT 0,
    coupon_disc DECIMAL(10,2) NOT NULL DEFAULT 0,
    coupon_match_disc DECIMAL(10,2) NOT NULL DEFAULT 0
);
CREATE INDEX idx_venta_detalle_venta_id ON venta_detalle(venta_id);
CREATE INDEX idx_venta_detalle_product_id ON venta_detalle(product_id);

CREATE TABLE devoluciones (
    devolucion_id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas(venta_id),
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    motivo VARCHAR(200) NOT NULL,
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_devoluciones_venta_id ON devoluciones(venta_id);

CREATE TABLE anulaciones_venta (
    anulacion_id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT UNIQUE NOT NULL REFERENCES ventas(venta_id),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    motivo VARCHAR(200) NOT NULL,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MÓDULO 6: CAJA
-- ============================================================================

CREATE TABLE cajas (
    caja_id SERIAL PRIMARY KEY,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    nombre VARCHAR(40) NOT NULL,
    activa BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX idx_cajas_tienda_id ON cajas(tienda_id);

CREATE TABLE apertura_caja (
    apertura_id BIGSERIAL PRIMARY KEY,
    caja_id INTEGER NOT NULL REFERENCES cajas(caja_id),
    cajero_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fondo_inicial DECIMAL(10,2) NOT NULL CHECK (fondo_inicial >= 0),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_apertura_caja_caja_id ON apertura_caja(caja_id);

-- Cuadre horario: diferencia calculada, no confiada a la aplicación
CREATE TABLE cierre_caja (
    cierre_id BIGSERIAL PRIMARY KEY,
    caja_id INTEGER NOT NULL REFERENCES cajas(caja_id),
    cajero_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    total_esperado DECIMAL(10,2) NOT NULL,
    total_registrado DECIMAL(10,2) NOT NULL,
    diferencia DECIMAL(10,2) GENERATED ALWAYS AS (total_registrado - total_esperado) STORED,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cierre_caja_caja_id ON cierre_caja(caja_id);
CREATE INDEX idx_cierre_caja_diferencia ON cierre_caja(diferencia) WHERE diferencia <> 0;

CREATE TABLE datafonos (
    datafono_id SERIAL PRIMARY KEY,
    caja_id INTEGER NOT NULL REFERENCES cajas(caja_id),
    modelo VARCHAR(60),
    version_firmware VARCHAR(30),
    fecha_ultima_actualizacion DATE,
    estado VARCHAR(30) NOT NULL DEFAULT 'activo'
        CHECK (estado IN ('activo','requiere_actualizacion','fuera_servicio'))
);

CREATE TABLE incidentes_fraude (
    incidente_id SERIAL PRIMARY KEY,
    cierre_id BIGINT NOT NULL REFERENCES cierre_caja(cierre_id),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    descripcion TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'abierto' CHECK (estado IN ('abierto','en_revision','cerrado')),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MÓDULO 7: PROVEEDORES Y COMPRAS
-- ============================================================================

CREATE TABLE proveedores (
    proveedor_id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    contacto VARCHAR(150),
    telefono VARCHAR(20),
    condiciones_pago VARCHAR(100),
    activo BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE ordenes_compra (
    orden_id BIGSERIAL PRIMARY KEY,
    proveedor_id INTEGER NOT NULL REFERENCES proveedores(proveedor_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','aprobada','recibida','cancelada')),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);
CREATE INDEX idx_ordenes_compra_proveedor_id ON ordenes_compra(proveedor_id);

CREATE TABLE orden_compra_detalle (
    orden_detalle_id BIGSERIAL PRIMARY KEY,
    orden_id BIGINT NOT NULL REFERENCES ordenes_compra(orden_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    costo_unitario DECIMAL(10,2) NOT NULL CHECK (costo_unitario >= 0)
);
CREATE INDEX idx_orden_compra_detalle_orden_id ON orden_compra_detalle(orden_id);

CREATE TABLE lotes (
    lote_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad_recibida INTEGER NOT NULL CHECK (cantidad_recibida > 0),
    fecha_vencimiento DATE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_lotes_product_tienda ON lotes(product_id, tienda_id);
CREATE INDEX idx_lotes_fecha_vencimiento ON lotes(fecha_vencimiento);

CREATE TABLE recepcion_mercaderia (
    recepcion_id BIGSERIAL PRIMARY KEY,
    orden_id BIGINT NOT NULL REFERENCES ordenes_compra(orden_id),
    lote_id BIGINT REFERENCES lotes(lote_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- MÓDULO 8: INVENTARIO
-- ============================================================================

CREATE TABLE inventario (
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad_disponible INTEGER NOT NULL DEFAULT 0 CHECK (cantidad_disponible >= 0),
    cantidad_minima INTEGER NOT NULL DEFAULT 0,
    cantidad_maxima INTEGER,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, tienda_id)
);

-- Ubicación física del SKU en sala (Principio XII: la pantalla de Inventario
-- muestra "Pasillo 01 · G-03"). Una fila por (producto, tienda). La mantiene el
-- Reponedor / Encargado_Tienda. Añadida por la migración 0021.
CREATE TABLE ubicacion_producto (
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id) ON DELETE CASCADE,
    pasillo VARCHAR(40) NOT NULL,           -- "Pasillo 01", "Cámara Fría A"
    gondola VARCHAR(20),                    -- "G-03", "R-04" (opcional)
    nivel VARCHAR(20),                      -- "Nivel medio" (opcional)
    actualizado_por INTEGER REFERENCES empleados(empleado_id),
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (product_id, tienda_id)
);
CREATE INDEX idx_ubicacion_producto_tienda ON ubicacion_producto(tienda_id);

CREATE TABLE movimientos_inventario (
    movimiento_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL,
    tienda_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL
        CHECK (tipo IN ('entrada','salida','ajuste','traslado_entrada','traslado_salida')),
    cantidad INTEGER NOT NULL,
    referencia_tabla VARCHAR(40),
    referencia_id BIGINT,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_movimientos_inventario_producto_tienda
        FOREIGN KEY (product_id, tienda_id) REFERENCES inventario(product_id, tienda_id)
);
CREATE INDEX idx_movimientos_inventario_producto_tienda ON movimientos_inventario(product_id, tienda_id);

CREATE TABLE traslados_stock (
    traslado_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_origen_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    tienda_destino_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'solicitado'
        CHECK (estado IN ('solicitado','en_transito','recibido','cancelado')),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (tienda_origen_id <> tienda_destino_id)
);

CREATE TABLE mermas (
    merma_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    causa VARCHAR(20) NOT NULL CHECK (causa IN ('caducidad','robo','rotura','error_humano')),
    valor DECIMAL(10,2) NOT NULL CHECK (valor >= 0),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);
CREATE INDEX idx_mermas_producto_tienda ON mermas(product_id, tienda_id);
CREATE INDEX idx_mermas_causa ON mermas(causa);

CREATE TABLE ajustes_inventario (
    ajuste_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad_sistema INTEGER NOT NULL,
    cantidad_fisica INTEGER NOT NULL,
    diferencia INTEGER GENERATED ALWAYS AS (cantidad_fisica - cantidad_sistema) STORED,
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ============================================================================
-- MÓDULO 9: RECURSOS HUMANOS
-- ============================================================================

CREATE TABLE capacitaciones (
    capacitacion_id SERIAL PRIMARY KEY,
    nombre VARCHAR(150) NOT NULL,
    descripcion TEXT
);

CREATE TABLE empleado_capacitacion (
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id) ON DELETE CASCADE,
    capacitacion_id INTEGER NOT NULL REFERENCES capacitaciones(capacitacion_id) ON DELETE CASCADE,
    fecha_completado DATE,
    PRIMARY KEY (empleado_id, capacitacion_id)
);

CREATE TABLE clima_laboral (
    encuesta_id SERIAL PRIMARY KEY,
    tienda_id INTEGER REFERENCES tiendas(tienda_id),
    periodo VARCHAR(10) NOT NULL,                  -- ej. '2026-S2'
    resultado_promedio DECIMAL(4,2) CHECK (resultado_promedio BETWEEN 0 AND 10),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE plan_sucesion (
    sucesion_id SERIAL PRIMARY KEY,
    puesto_id INTEGER NOT NULL REFERENCES roles_puesto(puesto_id),
    empleado_candidato_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE
);

-- ============================================================================
-- MÓDULO 10: SISTEMA / AUDITORÍA (transversal)
-- ============================================================================

CREATE TABLE auditoria_log (
    log_id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(usuario_id),
    nombre_tabla VARCHAR(60) NOT NULL,
    accion VARCHAR(10) NOT NULL CHECK (accion IN ('INSERT','UPDATE','DELETE')),
    registro_id VARCHAR(60) NOT NULL,
    valores_anteriores JSONB,
    valores_nuevos JSONB,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_auditoria_log_tabla ON auditoria_log(nombre_tabla);
CREATE INDEX idx_auditoria_log_usuario_id ON auditoria_log(usuario_id);


-- ============================================================================
-- SEED: MÓDULOS (uno por departamento del BSC)
-- ============================================================================
INSERT INTO modulos (nombre, descripcion) VALUES
    ('Direccion', 'Dashboards consolidados, solo lectura'),
    ('Comercial', 'Pricing, catálogo, márgenes'),
    ('Marketing_CRM', 'Clientes, campañas, cupones, fidelización'),
    ('Operaciones', 'Compras, proveedores, inventario'),
    ('Ventas', 'Ticket de venta, devoluciones'),
    ('Finanzas', 'Caja, cuadre, seguridad de pagos'),
    ('TI', 'Datos, dashboards, gobierno de datos'),
    ('RRHH', 'Empleados, capacitación, clima laboral'),
    ('Sistema', 'Auditoría, configuración RBAC');

-- ============================================================================
-- SEED: ROLES
-- ============================================================================
INSERT INTO roles (nombre, descripcion) VALUES
    ('Cajero', 'Ejecuta ventas y cuadre de caja en tienda'),
    ('Encargado_Tienda', 'Supervisa una sucursal'),
    ('Reponedor', 'Gestiona inventario físico y mermas en tienda'),
    ('Jefe_Comercial', 'Pricing y catálogo'),
    ('Jefe_Marketing', 'CRM, campañas y fidelización'),
    ('Jefe_Operaciones', 'Compras e inventario a nivel de red'),
    ('Jefe_Finanzas', 'Caja y seguridad de pagos'),
    ('Jefe_TI', 'Datos, dashboards y gobierno de datos'),
    ('Jefe_RRHH', 'Personal y capacitación'),
    ('Gerente_General', 'Solo lectura consolidada, todos los módulos');

-- ============================================================================
-- SEED: PERMISOS DE EJEMPLO (patrón — se repite para los 10 roles)
-- ============================================================================

-- CAJERO: acceso de edición a Ventas y Finanzas (solo sus propias tablas operativas)
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE r.nombre = 'Cajero' AND m.nombre IN ('Ventas','Finanzas');

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, false, false
FROM roles r
JOIN modulos m ON m.nombre = 'Ventas'
CROSS JOIN (VALUES ('ventas'), ('venta_detalle'), ('devoluciones')) AS t(tabla)
WHERE r.nombre = 'Cajero';

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, false, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES ('apertura_caja'), ('cierre_caja')) AS t(tabla)
WHERE r.nombre = 'Cajero';

-- JEFE DE MARKETING: edición completa en Marketing_CRM, solo lectura en Ventas
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, (m.nombre = 'Marketing_CRM')
FROM roles r, modulos m
WHERE r.nombre = 'Jefe_Marketing' AND m.nombre IN ('Marketing_CRM','Ventas');

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Marketing_CRM'
CROSS JOIN (VALUES ('clientes'),('campanas'),('campana_cliente'),('cupones'),
                    ('cupon_redimido'),('niveles_fidelizacion'),('eventos_cliente')) AS t(tabla)
WHERE r.nombre = 'Jefe_Marketing';

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'ventas', true, false, false, false
FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
WHERE r.nombre = 'Jefe_Marketing';

-- GERENTE GENERAL: solo lectura en TODOS los módulos, cero escritura operativa
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, false
FROM roles r, modulos m
WHERE r.nombre = 'Gerente_General';
-- (sin filas en role_permisos_tabla con INSERT/UPDATE/DELETE = true para este rol
--  a propósito: el nivel estratégico consulta/agrega, no opera registro a registro)

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (spec.md, ronda 4)
-- Todos los cambios son aditivos sobre el esquema base de 50 tablas ya
-- validado. Diseñados con /mcpmarket-me:schema-designer. Cada uno traza a un
-- FR concreto de specs/001-core-ventas-inventario/spec.md.
-- ============================================================================

-- FR-020/FR-021/FR-016: alertas de reposición (stock bajo el punto dinámico)
-- y de vencimiento próximo. Un solo tipo de tabla con 'tipo' evita duplicar
-- estructura para dos conceptos que comparten el mismo ciclo de vida
-- (pendiente -> atendida).
CREATE TABLE alertas_inventario (
    alerta_id BIGSERIAL PRIMARY KEY,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('reposicion','vencimiento')),
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    lote_id BIGINT REFERENCES lotes(lote_id),          -- solo aplica cuando tipo = 'vencimiento'
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','atendida')),
    fecha_generada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_atendida TIMESTAMP,
    empleado_atiende_id INTEGER REFERENCES empleados(empleado_id),
    CHECK (tipo <> 'vencimiento' OR lote_id IS NOT NULL)
);
CREATE INDEX idx_alertas_inventario_producto_tienda ON alertas_inventario(product_id, tienda_id);
CREATE INDEX idx_alertas_inventario_tipo ON alertas_inventario(tipo);
-- FR-021: nunca dos alertas del mismo tipo pendientes a la vez para el mismo producto/tienda.
CREATE UNIQUE INDEX uq_alertas_inventario_activa
    ON alertas_inventario(product_id, tienda_id, tipo) WHERE estado = 'pendiente';

-- FR-022: evento de quiebre de stock (producto agotado con demanda no satisfecha)
CREATE TABLE eventos_quiebre_stock (
    evento_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    demanda_estimada_no_satisfecha INTEGER CHECK (demanda_estimada_no_satisfecha IS NULL OR demanda_estimada_no_satisfecha > 0),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_eventos_quiebre_producto_tienda ON eventos_quiebre_stock(product_id, tienda_id);
CREATE INDEX idx_eventos_quiebre_fecha ON eventos_quiebre_stock(fecha_hora);

-- FR-028: frecuencia de reposición pactada por proveedor. NULL = usa la
-- sugerencia semanal genérica (edge case documentado en spec.md).
ALTER TABLE proveedores
    ADD COLUMN frecuencia_reposicion VARCHAR(20)
        CHECK (frecuencia_reposicion IN ('semanal','mensual','trimestral'));

-- FR-024/FR-029: distinguir orden programada (según frecuencia del proveedor
-- o la sugerencia semanal genérica) de un pedido especial fuera de calendario,
-- y registrar el motivo cuando la orden se aparta de la sugerencia del sistema.
ALTER TABLE ordenes_compra
    ADD COLUMN tipo VARCHAR(20) NOT NULL DEFAULT 'programada'
        CHECK (tipo IN ('programada','especial')),
    ADD COLUMN motivo_desviacion TEXT;

-- FR-027: una venta debe persistir desde que empieza a escanearse (Principio
-- II — nada de estado simulado sin persistencia real), no solo al confirmar
-- el cobro. 'estado' reemplaza al booleano 'anulada' (única fuente de verdad,
-- evita dos columnas que podían quedar inconsistentes entre sí).
ALTER TABLE ventas DROP COLUMN anulada;
ALTER TABLE ventas
    ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT 'en_curso'
        CHECK (estado IN ('en_curso','confirmada','anulada'));
-- Backfill: las ~92,331 ventas ya sembradas del dataset son ventas históricas
-- cerradas (no quedan 'en_curso').
UPDATE ventas SET estado = 'confirmada';
CREATE INDEX idx_ventas_estado ON ventas(estado) WHERE estado <> 'confirmada';

-- FR-027: registro auditable de una línea escaneada y luego removida antes de
-- confirmar el pago. El CHECK impide que el mismo empleado se autorice a sí
-- mismo la remoción (el "encargado" debe ser distinto del cajero).
CREATE TABLE lineas_venta_removidas (
    remocion_id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas(venta_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    cajero_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    autoriza_empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    motivo VARCHAR(200),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (cajero_id <> autoriza_empleado_id)
);
CREATE INDEX idx_lineas_venta_removidas_venta_id ON lineas_venta_removidas(venta_id);

-- FR-030/FR-031: cada intento de cobro con tarjeta queda registrado (permite
-- reintentos y distingue rechazo del banco vs. error técnico de la pasarela).
CREATE TABLE intentos_pago_tarjeta (
    intento_id BIGSERIAL PRIMARY KEY,
    venta_id BIGINT NOT NULL REFERENCES ventas(venta_id) ON DELETE CASCADE,
    resultado VARCHAR(20) NOT NULL CHECK (resultado IN ('aprobado','rechazado','error_tecnico')),
    referencia_pasarela VARCHAR(100),      -- id del PaymentIntent de Stripe (modo prueba)
    monto DECIMAL(12,2) NOT NULL CHECK (monto >= 0),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_intentos_pago_tarjeta_venta_id ON intentos_pago_tarjeta(venta_id);
CREATE INDEX idx_intentos_pago_tarjeta_resultado ON intentos_pago_tarjeta(resultado);

-- FR-025: si la devolución reintegra o no la unidad al inventario disponible
-- depende del motivo (p.ej. producto dañado no reingresa).
ALTER TABLE devoluciones
    ADD COLUMN reintegra_inventario BOOLEAN NOT NULL DEFAULT true;

-- FR-014: código de lote del proveedor (impreso en el empaque/albarán físico),
-- distinto del lote_id interno autogenerado. Solo relevante para trazabilidad
-- ante una eventualidad sanitaria/de calidad -- no participa en el flujo
-- normal de venta (que sigue descontando por FEFO a nivel de lote interno,
-- nunca por este código). Nullable: el proveedor no siempre lo declara.
ALTER TABLE lotes
    ADD COLUMN codigo_lote_proveedor VARCHAR(50);

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (spec.md, ronda 6)
-- Cuentas por pagar a proveedor (FR-032 a FR-035) y comprobante fiscal (FR-036)
-- ============================================================================

ALTER TABLE proveedores ADD COLUMN ruc VARCHAR(13);

CREATE TABLE facturas_proveedor (
    factura_id BIGSERIAL PRIMARY KEY,
    orden_id BIGINT NOT NULL REFERENCES ordenes_compra(orden_id),
    numero_factura VARCHAR(50) NOT NULL,
    monto_total DECIMAL(12,2) NOT NULL CHECK (monto_total > 0),
    fecha_emision DATE NOT NULL,
    fecha_vencimiento DATE NOT NULL CHECK (fecha_vencimiento >= fecha_emision),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','pagada_parcial','pagada','vencida')),
    empleado_registra_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX uq_factura_proveedor_numero ON facturas_proveedor(orden_id, numero_factura);
CREATE INDEX idx_facturas_proveedor_estado ON facturas_proveedor(estado) WHERE estado <> 'pagada';
CREATE INDEX idx_facturas_proveedor_vencimiento ON facturas_proveedor(fecha_vencimiento) WHERE estado <> 'pagada';

CREATE TABLE pagos_proveedor (
    pago_id BIGSERIAL PRIMARY KEY,
    factura_id BIGINT NOT NULL REFERENCES facturas_proveedor(factura_id),
    monto DECIMAL(12,2) NOT NULL CHECK (monto > 0),
    medio_pago_id INTEGER NOT NULL REFERENCES medios_pago(medio_pago_id),
    referencia VARCHAR(100),
    empleado_registra_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    empleado_autoriza_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (empleado_registra_id <> empleado_autoriza_id)
);
CREATE INDEX idx_pagos_proveedor_factura_id ON pagos_proveedor(factura_id);

ALTER TABLE ventas
    ADD COLUMN tipo_comprobante VARCHAR(20) NOT NULL DEFAULT 'nota_venta'
        CHECK (tipo_comprobante IN ('factura','nota_venta')),
    ADD COLUMN identificacion_comprador VARCHAR(13) NOT NULL DEFAULT '9999999999999',
    ADD COLUMN razon_social_comprador VARCHAR(150) NOT NULL DEFAULT 'CONSUMIDOR FINAL';

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (ronda 7 — implementación US1)
-- Detalles que el modelo conceptual dejaba implícitos y que el punto de venta
-- necesita para funcionar. Todo aditivo, cada uno traza a spec/research de 001.
-- ============================================================================

-- FR-001: 'venta_id' es el basket_id del dataset para las ventas históricas
-- sembradas (máx. 41_481_282_915). Las ventas nuevas del POS necesitan un
-- generador propio que no colisione con ese rango.
CREATE SEQUENCE IF NOT EXISTS ventas_venta_id_seq AS BIGINT START WITH 100000000000;
ALTER TABLE ventas ALTER COLUMN venta_id SET DEFAULT nextval('ventas_venta_id_seq');

-- FR-004 / research.md §7: el comprobante PDF se genera al confirmar y se
-- persiste tal cual se emitió en el bucket MinIO 'comprobantes-venta'. Aquí se
-- guarda la clave del objeto (no el binario) para servirlo luego.
ALTER TABLE ventas ADD COLUMN IF NOT EXISTS comprobante_objeto VARCHAR(300);

-- spec.md (Key Entities → Lote de Inventario): "cantidad recibida, cantidad
-- disponible". El DDL base solo tenía 'cantidad_recibida'; el descuento FIFO/FEFO
-- (FR-005) necesita el saldo vivo por lote. Se inicializa = cantidad_recibida.
ALTER TABLE lotes ADD COLUMN IF NOT EXISTS cantidad_disponible INTEGER;
UPDATE lotes SET cantidad_disponible = cantidad_recibida WHERE cantidad_disponible IS NULL;
ALTER TABLE lotes ALTER COLUMN cantidad_disponible SET NOT NULL;
ALTER TABLE lotes ADD CONSTRAINT chk_lotes_cantidad_disponible
    CHECK (cantidad_disponible >= 0 AND cantidad_disponible <= cantidad_recibida);

-- FR-005 / FR-026: trazabilidad venta → línea → lote(s) afectado(s). Una salida
-- por venta puede tocar más de un lote; cada movimiento anota de qué lote salió.
ALTER TABLE movimientos_inventario ADD COLUMN IF NOT EXISTS lote_id BIGINT REFERENCES lotes(lote_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_inventario_lote_id ON movimientos_inventario(lote_id);

-- RBAC de la ronda 7: el patrón base solo sembró Cajero/Jefe_Marketing/Gerente_General.
-- El flujo de venta necesita que el cajero confirme (UPDATE) y que el Encargado_Tienda
-- autorice remociones (FR-027) y anule ventas (FR-007).
UPDATE role_permisos_tabla SET can_update = true
    WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Cajero')
      AND nombre_tabla = 'ventas';

INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE r.nombre = 'Encargado_Tienda' AND m.nombre = 'Ventas'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, (t.tabla = 'venta_detalle')
FROM roles r
JOIN modulos m ON m.nombre = 'Ventas'
CROSS JOIN (VALUES ('ventas'), ('venta_detalle'), ('devoluciones')) AS t(tabla)
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (ronda 8 — implementación US2)
-- Gestión de inventario por lotes: estado de validación de merma y su lote.
-- spec.md Key Entities → Merma: "producto, tienda, lote, cantidad, causa,
-- estado de validación (pendiente/validada/rechazada)". El DDL base no los tenía.
-- ============================================================================

ALTER TABLE mermas ADD COLUMN IF NOT EXISTS lote_id BIGINT REFERENCES lotes(lote_id);
ALTER TABLE mermas ADD COLUMN IF NOT EXISTS estado_validacion VARCHAR(20) NOT NULL DEFAULT 'pendiente';
ALTER TABLE mermas ADD COLUMN IF NOT EXISTS empleado_valida_id INTEGER REFERENCES empleados(empleado_id);
ALTER TABLE mermas ADD COLUMN IF NOT EXISTS fecha_validacion TIMESTAMP;
ALTER TABLE mermas ADD CONSTRAINT chk_mermas_estado_validacion
    CHECK (estado_validacion IN ('pendiente','validada','rechazada'));
CREATE INDEX IF NOT EXISTS idx_mermas_estado_validacion ON mermas(estado_validacion)
    WHERE estado_validacion = 'pendiente';

-- RBAC ronda 8: el módulo 'Operaciones' no tenía permisos sembrados.
-- Reponedor registra recepciones/ajustes/mermas; Encargado_Tienda valida mermas;
-- Jefe_Operaciones supervisa toda la red.
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'Operaciones' AND r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla,
       true,
       true,
       (r.nombre <> 'Reponedor' OR t.tabla IN ('lotes','inventario')),
       false
FROM roles r
JOIN modulos m ON m.nombre = 'Operaciones'
CROSS JOIN (VALUES ('lotes'), ('recepcion_mercaderia'), ('ajustes_inventario'),
                    ('mermas'), ('inventario'), ('movimientos_inventario'),
                    ('ordenes_compra'), ('orden_compra_detalle')) AS t(tabla)
WHERE r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (ronda 9 — implementación US3)
-- Alertas de reposición/vencimiento/exceso, quiebre de alta demanda, stock
-- máximo por categoría, verificación de anaquel, y config de inventario.
-- data-model.md §17 / §17.1 (tablas Ronda 9/10 que faltaban en el DDL base).
-- ============================================================================

-- FR-038: nuevo tipo de alerta 'exceso_stock' (no requiere lote, como 'reposicion').
ALTER TABLE alertas_inventario DROP CONSTRAINT IF EXISTS alertas_inventario_tipo_check;
ALTER TABLE alertas_inventario ADD CONSTRAINT alertas_inventario_tipo_check
    CHECK (tipo IN ('reposicion','vencimiento','exceso_stock'));

-- FR-043: quiebre marcado como alta demanda al insertar (según clasificacion_abc='A'
-- vigente en ese momento; no se recalcula retroactivamente — data-model.md §12).
ALTER TABLE eventos_quiebre_stock ADD COLUMN IF NOT EXISTS es_alta_demanda BOOLEAN NOT NULL DEFAULT false;

-- FR-037 (Ronda 9): stock máximo vigente por categoría y tienda. Sin FK a productos
-- (granularidad de categoría, mismo criterio que umbral_merma_categoria de 006).
CREATE TABLE IF NOT EXISTS stock_maximo_categoria (
    id BIGSERIAL PRIMARY KEY,
    product_category VARCHAR(100) NOT NULL,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad_maxima INTEGER NOT NULL CHECK (cantidad_maxima > 0),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_definicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_stock_maximo_categoria
    ON stock_maximo_categoria(product_category, tienda_id);

-- FR-042 (Ronda 10): verificación diaria de anaquel de productos clasificación A.
CREATE TABLE IF NOT EXISTS verificacion_anaquel (
    id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    disponible BOOLEAN NOT NULL,
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_verificacion_anaquel_dia
    ON verificacion_anaquel(product_id, tienda_id, fecha);

-- FR-016 / FR-020: parámetros configurables por el negocio (spec: "no se fija un
-- valor único de fábrica"). Mismo patrón clave/valor que configuracion_pricing (003).
CREATE TABLE IF NOT EXISTS configuracion_inventario (
    clave VARCHAR(60) PRIMARY KEY,
    valor DECIMAL(10,4) NOT NULL,
    descripcion VARCHAR(250)
);
INSERT INTO configuracion_inventario (clave, valor, descripcion) VALUES
    ('lead_time_dias_default', 7, 'Días estimados entre orden y recepción, usado por el cálculo del punto de reposición cuando no hay un valor por proveedor (FR-020, research.md #5)'),
    ('stock_seguridad_pct', 0.20, 'Fracción del consumo del lead time que se mantiene como colchón de seguridad (FR-020, research.md #5)'),
    ('reposicion_ventana_dias', 14, 'Ventana de la media móvil de demanda diaria para el punto de reposición (FR-020)'),
    ('vencimiento_umbral_dias', 15, 'Días de anticipación para alertar un lote perecedero próximo a vencer (FR-016)')
ON CONFLICT (clave) DO NOTHING;

-- RBAC ronda 9: alertas/quiebres/stock-máximo/anaquel (Operaciones) y
-- facturas/pagos a proveedor (Finanzas).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE (m.nombre = 'Operaciones'
         AND r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones'))
   OR (m.nombre = 'Finanzas' AND r.nombre IN ('Jefe_Finanzas','Jefe_Operaciones'))
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla,
       true,
       (r.nombre <> 'Reponedor'
        OR t.tabla IN ('alertas_inventario','eventos_quiebre_stock','verificacion_anaquel')),
       (r.nombre <> 'Reponedor'),
       false
FROM roles r
JOIN modulos m ON m.nombre = 'Operaciones'
CROSS JOIN (VALUES ('alertas_inventario'), ('eventos_quiebre_stock'),
                    ('stock_maximo_categoria'), ('verificacion_anaquel'),
                    ('proveedores'), ('facturas_proveedor')) AS t(tabla)
WHERE r.nombre IN ('Reponedor','Encargado_Tienda','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES ('facturas_proveedor'), ('pagos_proveedor')) AS t(tabla)
WHERE r.nombre IN ('Jefe_Finanzas','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 001-core-ventas-inventario (ronda 10 — implementación US4/US5)
-- Catálogo de productos: nombre/marca y generador de product_id para altas nuevas.
-- spec.md Key Entities → Producto: "código interno, código de barras, nombre,
-- categoría, marca, ...". El DDL base (del dataset) no traía nombre ni marca libre.
-- ============================================================================

ALTER TABLE productos ADD COLUMN IF NOT EXISTS nombre VARCHAR(200);
ALTER TABLE productos ADD COLUMN IF NOT EXISTS marca VARCHAR(120);

-- FR-009: 'product_id' es la natural key del dataset (máx. 18_316_298). Las altas
-- nuevas por la UI necesitan su propio generador que no colisione con ese rango.
CREATE SEQUENCE IF NOT EXISTS productos_product_id_seq AS INTEGER START WITH 90000000;
ALTER TABLE productos ALTER COLUMN product_id SET DEFAULT nextval('productos_product_id_seq');

-- RBAC ronda 10: el módulo 'Comercial' no tenía permisos sembrados.
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'Comercial' AND r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

-- La "baja" de un producto es lógica (activo=false → UPDATE), por eso can_delete=false.
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Comercial'
CROSS JOIN (VALUES ('productos'), ('historial_precios'), ('margenes_objetivo')) AS t(tabla)
WHERE r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 003-precios-margenes (spec.md, plan.md, research.md, data-model.md)
-- ============================================================================

-- FR-004: factor de sensibilidad ("elasticidad") por categoría, configurado manualmente por Jefe_Comercial.
-- NULL = esa categoría todavía no tiene una regla de ajuste activa (el job semanal la omite, research.md §2).
ALTER TABLE margenes_objetivo
    ADD COLUMN factor_sensibilidad DECIMAL(4,2) CHECK (factor_sensibilidad IS NULL OR factor_sensibilidad BETWEEN 0 AND 1);

-- FR-005/FR-006: propuestas de ajuste de precio generadas por el sistema, nunca publicadas sin aprobación
-- explícita de Jefe_Comercial (SC-002). Al aprobarse, actualiza productos.precio_base + historial_precios (research.md §1).
CREATE TABLE propuesta_ajuste_precio (
    propuesta_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    precio_actual DECIMAL(10,2) NOT NULL CHECK (precio_actual >= 0),
    precio_propuesto DECIMAL(10,2) NOT NULL CHECK (precio_propuesto >= 0),
    margen_esperado_pct DECIMAL(5,2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente' CHECK (estado IN ('pendiente','aprobada','rechazada')),
    fecha_generada TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_resolucion TIMESTAMP,
    aprobado_por INTEGER REFERENCES empleados(empleado_id),
    CHECK (estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))
);
CREATE INDEX idx_propuesta_ajuste_precio_product_id ON propuesta_ajuste_precio(product_id);
CREATE INDEX idx_propuesta_ajuste_precio_estado ON propuesta_ajuste_precio(estado) WHERE estado = 'pendiente';

-- FR-009/FR-010: descuento manual en punto de venta con autorización obligatoria (mismo patrón CHECK de doble
-- persona que lineas_venta_removidas/FR-027 y pagos_proveedor/FR-034 de 001, sin excepción por monto), más el
-- margen real calculado para TODA línea confirmada (FR-002) y el indicador de margen bajo mínimo (FR-010).
-- El rol de empleado_autoriza_id (Encargado_Tienda o superior) se valida en la capa de servicio (research.md §4).
ALTER TABLE venta_detalle
    ADD COLUMN motivo_descuento VARCHAR(200),
    ADD COLUMN empleado_aplica_id INTEGER REFERENCES empleados(empleado_id),
    ADD COLUMN empleado_autoriza_id INTEGER REFERENCES empleados(empleado_id),
    ADD COLUMN margen_real DECIMAL(10,2),
    ADD COLUMN margen_bajo_minimo BOOLEAN NOT NULL DEFAULT false,
    ADD CONSTRAINT chk_venta_detalle_autorizacion_descuento CHECK (
        (empleado_aplica_id IS NULL AND empleado_autoriza_id IS NULL)
        OR (empleado_aplica_id IS NOT NULL AND empleado_autoriza_id IS NOT NULL AND empleado_aplica_id <> empleado_autoriza_id)
    );

-- FR-012: acción correctiva registrada por Jefe_Comercial sobre una línea marcada por margen bajo mínimo
-- (gap: sin esta tabla, el listado consolidado semanal sería de solo lectura).
CREATE TABLE revision_margen_bajo (
    revision_id BIGSERIAL PRIMARY KEY,
    venta_detalle_id BIGINT NOT NULL UNIQUE REFERENCES venta_detalle(venta_detalle_id) ON DELETE CASCADE,
    revisado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    accion_correctiva VARCHAR(500) NOT NULL,
    fecha_revision TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- FR-014: catálogo de competidores nombrados (captura manual, research.md §5) — nombre/tipo/ciudad,
-- sin relación con las tiendas propias de Marzú.
CREATE TABLE competidores (
    competidor_id SERIAL PRIMARY KEY,
    nombre VARCHAR(120) NOT NULL,
    tipo VARCHAR(20) NOT NULL CHECK (tipo IN ('supermercado','tienda_barrio','tienda_digital')),
    ciudad VARCHAR(100)
);

-- FR-014/FR-015/FR-016: precio de referencia de competencia — tres fuentes (research.md §5):
-- manual (Jefe_Comercial, por competidor nombrado, cualquier producto), open_prices (automático,
-- solo productos agregados en vivo con barcode real, competidor_id NULL por ser dato crowdsourced
-- sin atribuir) y sintetico (semilla inicial de demostración sobre clasificación A, dataset simulado
-- ya documentado en domain-context.md). fuente_captura reemplaza al booleano es_sintetico de la
-- primera versión de esta tabla porque dos fuentes no-sintéticas (manual/open_prices) ya no caben
-- en un solo booleano.
CREATE TABLE precio_competencia (
    precio_competencia_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    competidor_id INTEGER REFERENCES competidores(competidor_id),
    tienda_id INTEGER REFERENCES tiendas(tienda_id),
    precio DECIMAL(10,2) NOT NULL CHECK (precio >= 0),
    fecha_captura DATE NOT NULL DEFAULT CURRENT_DATE,
    es_promocional BOOLEAN NOT NULL DEFAULT false,
    fuente_captura VARCHAR(20) NOT NULL DEFAULT 'manual' CHECK (fuente_captura IN ('manual','open_prices','sintetico')),
    registrado_por INTEGER REFERENCES empleados(empleado_id)
);
CREATE INDEX idx_precio_competencia_product_id ON precio_competencia(product_id);

-- FR-004 (tolerancia global de ajuste), FR-007 (margen mínimo global de respaldo, Edge Case de spec.md),
-- FR-016 (umbral de alerta de competencia) — configuración clave/valor mínima, sin dueño natural en ninguna
-- tabla existente (Principio VIII: evita 3 tablas de una sola fila o columnas sueltas mal ubicadas).
CREATE TABLE configuracion_pricing (
    clave VARCHAR(60) PRIMARY KEY,
    valor DECIMAL(10,4) NOT NULL,
    descripcion VARCHAR(250)   -- 250 (no 200): la descripción de 'margen_minimo_global_pct'
                               -- documenta el Edge Case de FR-007 y mide 201 caracteres.
);
INSERT INTO configuracion_pricing (clave, valor, descripcion) VALUES
    ('margen_minimo_global_pct', 5.0, 'Piso de respaldo del margen objetivo efectivo cuando una categoría no tiene margen objetivo definido, o cuando el modificador ancla/nicho lo dejaría por debajo de este valor (Edge Case spec.md, FR-007)'),
    ('tolerancia_ajuste_pp', 2.0, 'Desviación mínima en puntos porcentuales para generar una propuesta de ajuste de precio (research.md #2, FR-005)'),
    ('umbral_alerta_competencia_pct', 5.0, 'Desviación mínima frente al precio de competencia para generar una alerta semanal (FR-016)');

-- RBAC feature 003: el módulo 'Comercial' cubre las tablas nuevas de pricing/competencia;
-- Cajero/Encargado_Tienda pueden actualizar venta_detalle (descuento manual, contracts/pricing.md).
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Comercial'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
CROSS JOIN (VALUES ('margenes_objetivo'), ('propuesta_ajuste_precio'), ('historial_precios'),
                    ('revision_margen_bajo'), ('competidores'), ('precio_competencia'),
                    ('configuracion_pricing')) AS t(tabla)
WHERE r.nombre IN ('Jefe_Comercial','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- FR-011/FR-012: el Encargado_Tienda ve y cierra el listado diario de margen bajo de SU tienda.
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE r.nombre = 'Encargado_Tienda' AND m.nombre = 'Comercial'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'revision_margen_bajo', true, true, true, false
FROM roles r JOIN modulos m ON m.nombre = 'Comercial'
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

UPDATE role_permisos_tabla SET can_update = true
WHERE nombre_tabla = 'venta_detalle'
  AND modulo_id = (SELECT modulo_id FROM modulos WHERE nombre = 'Ventas')
  AND role_id IN (SELECT role_id FROM roles WHERE nombre IN ('Cajero','Encargado_Tienda'));


-- ============================================================================
-- EXTENSIÓN — Feature 002-clientes-fidelizacion (spec.md, ronda 1)
-- Consentimiento de tratamiento de datos (FR-001) y severidad de churn (FR-010)
-- ============================================================================
ALTER TABLE clientes
    ADD COLUMN consentimiento_datos BOOLEAN NOT NULL DEFAULT true,
    ADD COLUMN fecha_consentimiento_datos TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE churn_score
    ADD COLUMN severidad VARCHAR(20)
        CHECK (severidad IN ('en_riesgo','inactivo'));

-- ============================================================================
-- EXTENSIÓN — Feature 002-clientes-fidelizacion (data-model.md, ronda 2)
-- Clasificación de campaña propia de SIRA, grupo de control, resultado de
-- uplift (FR-016 a FR-019) y registro de envío de cupón (FR-013/FR-014)
-- ============================================================================
CREATE SEQUENCE IF NOT EXISTS campanas_campaign_id_seq START WITH 100000;

ALTER TABLE campanas
    ADD COLUMN categoria_sira VARCHAR(20)
        CHECK (categoria_sira IN ('hito','reactivacion'));

ALTER TABLE campana_cliente
    ADD COLUMN grupo VARCHAR(20)
        CHECK (grupo IN ('tratado','control'));

CREATE TABLE campana_resultado (
    campaign_id INTEGER PRIMARY KEY REFERENCES campanas(campaign_id) ON DELETE CASCADE,
    tasa_retorno_tratado DECIMAL(5,4),
    tasa_retorno_control DECIMAL(5,4),
    uplift DECIMAL(5,4) GENERATED ALWAYS AS (tasa_retorno_tratado - tasa_retorno_control) STORED,
    decision VARCHAR(20) CHECK (decision IN ('aprobada_escalar','descartada')),
    empleado_decide_id INTEGER REFERENCES empleados(empleado_id),
    fecha_calculo DATE
);

CREATE TABLE cupon_enviado (
    envio_id BIGSERIAL PRIMARY KEY,
    evento_id BIGINT REFERENCES eventos_cliente(evento_id) ON DELETE CASCADE,
    household_id INTEGER NOT NULL REFERENCES clientes(household_id) ON DELETE CASCADE,
    coupon_upc VARCHAR(20) NOT NULL,
    campaign_id INTEGER NOT NULL REFERENCES campanas(campaign_id),
    fecha_envio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    entregado BOOLEAN NOT NULL DEFAULT true
);
CREATE INDEX idx_cupon_enviado_household_id ON cupon_enviado(household_id);
CREATE INDEX idx_cupon_enviado_evento_id ON cupon_enviado(evento_id);

-- ============================================================================
-- EXTENSIÓN — Feature 002-clientes-fidelizacion (spec.md, ronda 5)
-- Identificación del cliente afiliado por cédula en punto de venta (FR-001) y
-- generador de household_id para altas nuevas (el dataset llega hasta 2500).
-- ============================================================================

ALTER TABLE clientes ADD COLUMN documento_identidad VARCHAR(13);
CREATE UNIQUE INDEX uq_clientes_documento_identidad
    ON clientes(documento_identidad) WHERE documento_identidad IS NOT NULL;

CREATE SEQUENCE IF NOT EXISTS clientes_household_id_seq AS INTEGER START WITH 900000;
ALTER TABLE clientes ALTER COLUMN household_id SET DEFAULT nextval('clientes_household_id_seq');

-- RBAC ronda 5: el maestro de cliente se opera en caja (alta/edición por
-- Cajero/Encargado, baja sólo por Encargado_Tienda o Jefe_Marketing).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'Marketing_CRM' AND r.nombre IN ('Cajero','Encargado_Tienda')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, (r.nombre = 'Encargado_Tienda')
FROM roles r
JOIN modulos m ON m.nombre = 'Marketing_CRM'
CROSS JOIN (VALUES ('clientes'), ('clientes_demograficos')) AS t(tabla)
WHERE r.nombre IN ('Cajero','Encargado_Tienda')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

UPDATE role_permisos_tabla SET can_delete = true
WHERE role_id = (SELECT role_id FROM roles WHERE nombre = 'Jefe_Marketing')
  AND nombre_tabla IN ('clientes','clientes_demograficos');

-- ============================================================================
-- EXTENSIÓN — Feature 002-clientes-fidelizacion (spec.md, ronda 6)
-- Niveles de fidelización por defecto. El CLV compuesto (research.md §1) es un
-- score 0..1; el Jefe de Marketing ajusta los umbrales vía PATCH (FR-007).
-- ============================================================================
INSERT INTO niveles_fidelizacion (nombre, umbral_clv_min) VALUES
    ('Bronce', 0.00),
    ('Plata', 0.40),
    ('Oro', 0.70),
    ('Platino', 0.90)
ON CONFLICT (nombre) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 002-clientes-fidelizacion (spec.md, ronda 7)
-- Redención de cupón en caja (FR-015): la ejecuta el Cajero al aplicar el cupón
-- en el punto de venta. El patrón base sólo sembró cupon_redimido para
-- Jefe_Marketing; el Cajero ya tiene el módulo Marketing_CRM desde la ronda 5.
-- ============================================================================
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'cupon_redimido', true, true, false, false
FROM roles r
JOIN modulos m ON m.nombre = 'Marketing_CRM'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
WHERE r.nombre = 'Cajero'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;


-- ============================================================================
-- EXTENSIÓN — Feature 004-pronostico-demanda (spec.md, plan.md, research.md, data-model.md)
-- Pronóstico de demanda con variables exógenas. 4 tablas nuevas (salida del
-- modelo) + columna origen_calculo aditiva sobre alertas_inventario y
-- orden_compra_detalle de 001. No crea tablas de entrada: entrena contra
-- ventas / venta_detalle / promociones / historial_precios / eventos_quiebre_stock.
-- ============================================================================

-- 1. Versión de modelo — mismo patrón pendiente/aprobado/rechazado que propuesta_ajuste_precio (003).
CREATE TABLE modelo_demanda (
    modelo_id BIGSERIAL PRIMARY KEY,
    fecha_entrenamiento TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metrica_precision_validacion DECIMAL(6,4),
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente'
        CHECK (estado IN ('pendiente','aprobado','rechazado','reemplazado')),
    fecha_resolucion TIMESTAMP,
    aprobado_por INTEGER REFERENCES empleados(empleado_id),
    observaciones VARCHAR(500),
    CHECK (estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))
);
-- FR-005: sólo un modelo vigente en producción a la vez.
CREATE UNIQUE INDEX uq_modelo_demanda_aprobado ON modelo_demanda((estado)) WHERE estado = 'aprobado';

-- 2. Pronóstico por modelo/producto/tienda/semana (research.md Decisión 1).
CREATE TABLE pronostico_demanda (
    pronostico_id BIGSERIAL PRIMARY KEY,
    modelo_id BIGINT NOT NULL REFERENCES modelo_demanda(modelo_id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
    anio INTEGER NOT NULL,
    cantidad_pronosticada DECIMAL(10,2) NOT NULL CHECK (cantidad_pronosticada >= 0),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (modelo_id, product_id, tienda_id, semana, anio)
);
CREATE INDEX idx_pronostico_demanda_producto_tienda ON pronostico_demanda(product_id, tienda_id, semana, anio);

-- 3. Monitoreo semanal de precisión (FR-011/FR-013).
CREATE TABLE monitoreo_precision_modelo (
    monitoreo_id BIGSERIAL PRIMARY KEY,
    modelo_id BIGINT NOT NULL REFERENCES modelo_demanda(modelo_id) ON DELETE CASCADE,
    semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
    anio INTEGER NOT NULL,
    metrica_precision DECIMAL(6,4) NOT NULL,
    supero_umbral_alerta BOOLEAN NOT NULL DEFAULT false,
    fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (modelo_id, semana, anio)
);

-- 4. Configuración clave/valor (mismo patrón que configuracion_pricing de 003).
CREATE TABLE configuracion_pronostico (
    clave VARCHAR(60) PRIMARY KEY,
    valor DECIMAL(10,4) NOT NULL,
    descripcion VARCHAR(250)
);
INSERT INTO configuracion_pronostico (clave, valor, descripcion) VALUES
    ('precision_minima_aprobacion', 0.35, 'WAPE de validación máximo aceptable para que el Jefe de TI apruebe un modelo — referencia, no bloqueo automático (FR-002/FR-003)'),
    ('umbral_degradacion_semanal_pct', 0.45, 'WAPE semanal en producción por encima del cual se genera una alerta de degradación para el Jefe de TI (FR-012)'),
    ('historial_minimo_semanas', 12, 'Semanas mínimas de historial de ventas para incluir un producto/tienda en el entrenamiento; por debajo queda cubierto por el respaldo de rotación reciente (FR-006, research.md Decisión 6)');

-- 5/6. Origen del cálculo en las salidas ya construidas por 001 (FR-010).
ALTER TABLE alertas_inventario ADD COLUMN origen_calculo VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente'
    CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente'));
ALTER TABLE orden_compra_detalle ADD COLUMN origen_calculo VARCHAR(20) NOT NULL DEFAULT 'rotacion_reciente'
    CHECK (origen_calculo IN ('modelo_pronostico','rotacion_reciente'));

-- RBAC feature 004: el módulo 'TI' cubre modelo_demanda / pronostico_demanda /
-- monitoreo_precision_modelo / configuracion_pronostico (Jefe_TI); el reporte de
-- demanda perdida es una consulta sobre eventos_quiebre_stock, ya cubierta por
-- 'Operaciones' para Jefe_Operaciones (research.md Decisión 8).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'TI' AND r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r JOIN modulos m ON m.nombre = 'TI'
CROSS JOIN (VALUES ('modelo_demanda'), ('pronostico_demanda'),
                    ('monitoreo_precision_modelo'), ('configuracion_pronostico')) AS t(tabla)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'eventos_quiebre_stock', true, true, false, false
FROM roles r JOIN modulos m ON m.nombre = 'Operaciones'
WHERE r.nombre = 'Jefe_Operaciones'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;


-- ============================================================================
-- EXTENSIÓN — Feature 005-promociones-inteligentes (spec.md, plan.md, research.md, data-model.md)
-- Motor de afinidad de canasta (mlxtend), cupón de afinidad (reutiliza campanas/
-- cupon_enviado de 002), clasificación ABC (puebla productos.clasificacion_abc de
-- 001), liquidación de categoría C y colocación promocional (puebla promociones).
-- ============================================================================

-- 1. Reglas de asociación (afinidad de canasta) — research.md Decisión 1/3.
CREATE TABLE regla_afinidad (
    regla_id BIGSERIAL PRIMARY KEY,
    product_id_antecedente INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    product_id_consecuente INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    soporte DECIMAL(8,6) NOT NULL CHECK (soporte >= 0),
    confianza DECIMAL(8,6) NOT NULL CHECK (confianza >= 0),
    lift DECIMAL(10,4),
    fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    estado VARCHAR(20) NOT NULL DEFAULT 'vigente'
        CHECK (estado IN ('vigente','reemplazada','desactivada')),
    desactivada_por INTEGER REFERENCES empleados(empleado_id),
    fecha_desactivacion TIMESTAMP,
    motivo_desactivacion VARCHAR(300),
    CHECK (product_id_antecedente <> product_id_consecuente),
    CHECK (estado <> 'desactivada'
           OR (desactivada_por IS NOT NULL AND fecha_desactivacion IS NOT NULL))
);
CREATE INDEX idx_regla_afinidad_antecedente ON regla_afinidad(product_id_antecedente) WHERE estado = 'vigente';

-- 2. Extensión de campanas (002): nuevo valor 'afinidad' en categoria_sira.
ALTER TABLE campanas DROP CONSTRAINT IF EXISTS campanas_categoria_sira_check;
ALTER TABLE campanas ADD CONSTRAINT campanas_categoria_sira_check
    CHECK (categoria_sira IN ('hito','reactivacion','afinidad'));

-- 3. Extensión de cupon_enviado (002): regla de afinidad que originó el cupón.
ALTER TABLE cupon_enviado ADD COLUMN regla_afinidad_id BIGINT REFERENCES regla_afinidad(regla_id);

-- 4. Candidatos a liquidación de categoría C (FR-012/FR-014).
CREATE TABLE candidato_liquidacion (
    candidato_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    semana INTEGER NOT NULL CHECK (semana BETWEEN 1 AND 53),
    anio INTEGER NOT NULL,
    rotacion_reciente_calculada DECIMAL(10,2) NOT NULL,
    descuento_sugerido_pct DECIMAL(5,2) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'candidato' CHECK (estado IN ('candidato','ejecutado')),
    fecha_ejecucion TIMESTAMP,
    ejecutado_por INTEGER REFERENCES empleados(empleado_id),
    UNIQUE (product_id, tienda_id, semana, anio),
    CHECK (estado = 'candidato' OR (fecha_ejecucion IS NOT NULL AND ejecutado_por IS NOT NULL))
);
CREATE INDEX idx_candidato_liquidacion_tienda_semana ON candidato_liquidacion(tienda_id, semana, anio);

-- 5. Bitácora de reclasificaciones ABC (FR-010) — la clasificación en sí vive en
-- productos.clasificacion_abc (sin dimensión de tienda); esto es sólo el changelog.
CREATE TABLE cambio_clasificacion_abc (
    cambio_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id) ON DELETE CASCADE,
    clasificacion_anterior CHAR(1),
    clasificacion_nueva CHAR(1) NOT NULL,
    fecha_calculo TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_cambio_clasificacion_abc_fecha ON cambio_clasificacion_abc(fecha_calculo);

-- 6. Configuración clave/valor (research.md Decisiones 2/5/6/9).
CREATE TABLE configuracion_promociones (
    clave VARCHAR(60) PRIMARY KEY,
    valor DECIMAL(12,6) NOT NULL,
    descripcion VARCHAR(250)
);
INSERT INTO configuracion_promociones (clave, valor, descripcion) VALUES
    ('soporte_minimo_regla', 0.02, 'Soporte mínimo (fracción de tickets) para que un par de productos genere una regla de asociación (FR-001, research.md Decisión 2)'),
    ('confianza_minima_regla', 0.30, 'Confianza mínima (P(consecuente|antecedente)) para que una regla de asociación sea accionable (FR-001)'),
    ('vigencia_cupon_afinidad_dias', 30, 'Días durante los cuales un cupón de afinidad ya enviado bloquea el reenvío al mismo cliente para el mismo par (FR-007, research.md Decisión 9)'),
    ('rotacion_minima_liquidacion_semanal', 1.0, 'Unidades/semana por debajo de las cuales un producto categoría C en una tienda es candidato a liquidación (FR-011/FR-012)'),
    ('descuento_liquidacion_pct', 25.0, 'Descuento sugerido por defecto para la liquidación de un candidato de categoría C (FR-011)');

-- RBAC feature 005: Marketing_CRM (Jefe_Marketing) para afinidad/cupones/colocación;
-- Operaciones (Jefe_Operaciones / Encargado_Tienda) para ABC y liquidación (research.md Decisión 10).
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Marketing_CRM'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
CROSS JOIN (VALUES ('regla_afinidad'), ('promociones')) AS t(tabla)
WHERE r.nombre = 'Jefe_Marketing'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'promociones', true, true, false, false
FROM roles r
JOIN modulos m ON m.nombre = 'Marketing_CRM'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Operaciones'
CROSS JOIN (VALUES ('candidato_liquidacion'), ('configuracion_promociones'),
                    ('cambio_clasificacion_abc'), ('productos')) AS t(tabla)
WHERE r.nombre IN ('Jefe_Operaciones','Encargado_Tienda')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'Operaciones' AND r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'regla_afinidad', true, false, false, false
FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
WHERE r.nombre = 'Cajero'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 006-caja-mermas-fraude (spec.md, plan.md, research.md, data-model.md)
-- Cuadre de caja horario con diferencia calculada (columna GENERATED ya reservada),
-- inventario de datáfonos con conformidad automática frente al estándar de
-- seguridad de pagos, reporte mensual de patrones + incidentes de fraude,
-- protocolo de escalamiento versionado y umbral de merma aceptable por categoría.
-- `apertura_caja`, `cierre_caja`, `datafonos` e `incidentes_fraude` ya existen
-- desde 001; esta feature las puebla y extiende aditivamente `incidentes_fraude`.
-- ============================================================================

-- 1. Extensión aditiva de incidentes_fraude (research.md Decisión 6): un incidente
-- puede originarse en un cuadre (US3), en un ajuste de inventario anómalo (FR-010)
-- o registrarse directamente (US4); el ciclo abierto→en_revisión→cerrado deja
-- constancia de quién y cuándo (FR-015).
ALTER TABLE incidentes_fraude ALTER COLUMN cierre_id DROP NOT NULL;
ALTER TABLE incidentes_fraude ADD COLUMN ajuste_id BIGINT REFERENCES ajustes_inventario(ajuste_id);
ALTER TABLE incidentes_fraude ADD COLUMN acciones_tomadas TEXT;
ALTER TABLE incidentes_fraude ADD COLUMN resultado VARCHAR(20)
    CHECK (resultado IS NULL OR resultado IN ('fraude_confirmado','descartado'));
ALTER TABLE incidentes_fraude ADD COLUMN actualizado_por INTEGER REFERENCES empleados(empleado_id);
ALTER TABLE incidentes_fraude ADD COLUMN fecha_actualizacion TIMESTAMP;

-- 2. Estándar de seguridad de pagos (append-only, research.md Decisión 5).
CREATE TABLE configuracion_seguridad_pagos (
    config_id BIGSERIAL PRIMARY KEY,
    version_minima_firmware VARCHAR(30) NOT NULL,
    vigente_desde DATE NOT NULL DEFAULT CURRENT_DATE,
    actualizado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_config_seguridad_pagos_vigente_desde ON configuracion_seguridad_pagos(vigente_desde DESC);

-- 3. Protocolo de escalamiento ante fraude (texto versionado, research.md Decisión 7).
CREATE TABLE protocolo_escalamiento (
    protocolo_id BIGSERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_protocolo_escalamiento_fecha ON protocolo_escalamiento(fecha_creacion DESC);

-- 4. Umbral de merma aceptable por categoría (upsert in place, research.md Decisión 8).
CREATE TABLE umbral_merma_categoria (
    product_category VARCHAR(100) PRIMARY KEY,
    porcentaje_umbral DECIMAL(5,2) NOT NULL CHECK (porcentaje_umbral > 0 AND porcentaje_umbral <= 100),
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. Configuración clave/valor de caja — hoy sólo el umbral de ajuste anómalo (FR-010).
CREATE TABLE configuracion_caja (
    clave VARCHAR(60) PRIMARY KEY,
    valor DECIMAL(12,6) NOT NULL,
    descripcion VARCHAR(250)
);
INSERT INTO configuracion_caja (clave, valor, descripcion) VALUES
    ('umbral_ajuste_inventario_anomalo', 10, 'Unidades (valor absoluto) a partir de las cuales un ajuste de inventario de 001 con diferencia negativa se señala en el reporte mensual de patrones (FR-010)');

-- 6. Estado vigente inicial (best-effort: sólo si ya hay empleados sembrados).
INSERT INTO configuracion_seguridad_pagos (version_minima_firmware, actualizado_por)
SELECT '1.0.0', empleado_id FROM empleados ORDER BY empleado_id LIMIT 1;
INSERT INTO protocolo_escalamiento (texto, definido_por)
SELECT 'Protocolo de escalamiento ante fraude confirmado (versión inicial). Al detectar un caso: 1) documentar la evidencia, 2) notificar al Jefe de Finanzas, 3) aplicar las acciones del protocolo vigente, 4) registrar el resultado sin acusar al empleado si la investigación no lo confirma.',
       empleado_id FROM empleados ORDER BY empleado_id LIMIT 1;

-- 7. RBAC feature 006: módulo Finanzas (ya sembrado desde 001) — sin rol ni módulo
-- nuevo (research.md Decisión 10). Jefe_TI recibe acceso al módulo para datáfonos.
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'Finanzas'
  AND r.nombre IN ('Encargado_Tienda','Jefe_Finanzas','Jefe_TI','Jefe_Operaciones')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES
     ('apertura_caja', true, false, false),
     ('cierre_caja', true, false, false),
     ('incidentes_fraude', true, false, true),
     ('protocolo_escalamiento', true, false, false),
     ('umbral_merma_categoria', true, false, false),
     ('mermas', true, false, false),
     ('venta_detalle', true, false, false)
) AS t(tabla, sel, ins, upd)
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES
     ('apertura_caja', true, false, false),
     ('cierre_caja', true, false, false),
     ('ajustes_inventario', true, false, false),
     ('configuracion_caja', true, false, true),
     ('incidentes_fraude', true, true, true),
     ('protocolo_escalamiento', true, true, false)
) AS t(tabla, sel, ins, upd)
WHERE r.nombre = 'Jefe_Finanzas'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES ('datafonos'), ('configuracion_seguridad_pagos')) AS t(tabla)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'umbral_merma_categoria', true, true, true, false
FROM roles r JOIN modulos m ON m.nombre = 'Finanzas'
WHERE r.nombre = 'Jefe_Operaciones'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 007-pagos-seguridad (spec.md, plan.md, research.md, data-model.md)
-- Disponibilidad operativa diaria de datáfonos (reutiliza el valor `fuera_servicio`
-- del enum de `datafonos.estado`), alta/baja de medios de pago con aprobación,
-- incidentes de seguridad de pago (independientes de `incidentes_fraude` de 006),
-- política de seguridad de pagos versionada, y marca de inicio de cobro en `ventas`
-- para medir el tiempo de cobro (solo ventas registradas en vivo — Principio VII).
-- Extiende `modules/caja/` (006) y `modules/ventas/` (001); sin módulo nuevo.
-- ============================================================================

-- 1. medios_pago: aprobación explícita del Jefe de TI + baja sin borrar historial.
ALTER TABLE medios_pago ADD COLUMN aprobado BOOLEAN NOT NULL DEFAULT true;
ALTER TABLE medios_pago ADD COLUMN aprobado_por INTEGER REFERENCES empleados(empleado_id);
ALTER TABLE medios_pago ADD COLUMN fecha_aprobacion TIMESTAMP;
ALTER TABLE medios_pago ADD COLUMN fecha_baja TIMESTAMP;

-- 2. ventas: momento de inicio del cobro (nullable — NULL en las ~1.47M ventas
-- ya sembradas y en cualquier venta previa a esta feature, research.md Decisión 7).
ALTER TABLE ventas ADD COLUMN fecha_inicio_cobro TIMESTAMP;
CREATE INDEX idx_ventas_fecha_inicio_cobro ON ventas(fecha_inicio_cobro) WHERE fecha_inicio_cobro IS NOT NULL;

-- 3. Incidente de seguridad de pago — entidad nueva, independiente de
-- incidentes_fraude (006): no exige empleado implicado (research.md Decisión 4).
CREATE TABLE incidente_seguridad_pago (
    incidente_seguridad_id BIGSERIAL PRIMARY KEY,
    datafono_id INTEGER REFERENCES datafonos(datafono_id),
    registrado_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    descripcion TEXT NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'abierto'
        CHECK (estado IN ('abierto','en_investigacion','cerrado')),
    actualizado_por INTEGER REFERENCES empleados(empleado_id),
    fecha_actualizacion TIMESTAMP,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_incidente_seguridad_pago_estado ON incidente_seguridad_pago(estado);
CREATE INDEX idx_incidente_seguridad_pago_fecha ON incidente_seguridad_pago(fecha_hora);

-- 4. Política de seguridad de pagos — texto versionado append-only (Decisión 5).
CREATE TABLE politica_seguridad_pagos (
    politica_id BIGSERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_politica_seguridad_pagos_fecha_creacion ON politica_seguridad_pagos(fecha_creacion DESC);

-- 5. Estado vigente inicial de la política (best-effort: sólo si ya hay empleados).
INSERT INTO politica_seguridad_pagos (texto, definido_por)
SELECT 'Política de seguridad de pagos (versión inicial). Lineamientos: 1) todo datáfono debe cumplir la versión mínima de firmware vigente antes de operar; 2) no se almacenan datos completos de tarjeta en ningún sistema propio; 3) todo incidente de seguridad de pago se registra y se investiga hasta cerrarse; 4) sólo se ofrecen en caja los medios de pago aprobados por el Jefe de TI.',
       empleado_id FROM empleados ORDER BY empleado_id LIMIT 1;

-- 6. RBAC feature 007 — sin rol ni módulo nuevo. Jefe_TI y Jefe_Comercial
-- reciben acceso al módulo Ventas (mismo patrón que Jefe_Marketing→Ventas en 005).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, (r.nombre = 'Jefe_TI')
FROM roles r, modulos m
WHERE m.nombre = 'Ventas' AND r.nombre IN ('Jefe_TI','Jefe_Comercial')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'medios_pago', true, true, true, false
FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'ventas', true, false, false, false
FROM roles r JOIN modulos m ON m.nombre = 'Ventas'
WHERE r.nombre = 'Jefe_Comercial'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, t.sel, t.ins, t.upd, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES
     ('datafonos', true, false, true),
     ('politica_seguridad_pagos', true, false, false)
) AS t(tabla, sel, ins, upd)
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES ('incidente_seguridad_pago'), ('politica_seguridad_pagos')) AS t(tabla)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, false, false, false
FROM roles r
JOIN modulos m ON m.nombre = 'Finanzas'
CROSS JOIN (VALUES ('incidente_seguridad_pago'), ('politica_seguridad_pagos')) AS t(tabla)
WHERE r.nombre = 'Jefe_Finanzas'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 008-auth-administracion-sistema (spec.md, plan.md, research.md, data-model.md)
-- Login con JWT real (transporta sólo usuario_id — permisos resueltos en caliente
-- contra PostgreSQL, research.md Decisión 1), alta de empleado y de cuenta,
-- recuperación de contraseña de un solo uso, administración de RBAC, e
-- inhabilitación automática de cuenta al dar de baja al empleado (trigger).
-- Primeros usos de los módulos RBAC `Sistema` (Jefe_TI) y `RRHH` (Jefe_RRHH).
-- A partir de esta feature, todos los endpoints de 001-007 exigen JWT real.
-- ============================================================================

-- 1. Enlace de recuperación de contraseña de un solo uso (research.md Decisión 2).
CREATE TABLE recuperacion_password (
    token_id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(usuario_id) ON DELETE CASCADE,
    token VARCHAR(128) UNIQUE NOT NULL,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_expiracion TIMESTAMP NOT NULL,
    usado BOOLEAN NOT NULL DEFAULT false
);
CREATE INDEX idx_recuperacion_password_usuario_id ON recuperacion_password(usuario_id);

-- 2. Intentos de login, exitosos o no (research.md Decisión 3 — distinta de auditoria_log).
CREATE TABLE intentos_login (
    intento_id BIGSERIAL PRIMARY KEY,
    usuario_id INTEGER REFERENCES usuarios(usuario_id) ON DELETE SET NULL,
    username_intentado VARCHAR(50) NOT NULL,
    exitoso BOOLEAN NOT NULL,
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_intentos_login_usuario_id ON intentos_login(usuario_id);
CREATE INDEX idx_intentos_login_fecha_hora ON intentos_login(fecha_hora);

-- 3. Inhabilitación automática de cuenta al dar de baja al empleado (research.md
-- Decisión 4) — garantía a nivel de BD, no bypasseable por ningún llamador. No
-- actúa en la dirección inversa: reactivar al empleado NO reactiva la cuenta (FR-015).
CREATE OR REPLACE FUNCTION fn_inhabilitar_cuenta_usuario()
RETURNS TRIGGER AS $fn$
BEGIN
    UPDATE usuarios SET activo = false WHERE empleado_id = NEW.empleado_id;
    RETURN NEW;
END;
$fn$ LANGUAGE plpgsql;

CREATE TRIGGER trg_inhabilitar_cuenta_baja_empleado
AFTER UPDATE ON empleados
FOR EACH ROW
WHEN (NEW.activo = false AND OLD.activo = true)
EXECUTE FUNCTION fn_inhabilitar_cuenta_usuario();

-- 4. RBAC feature 008 — primer uso de `Sistema` (Jefe_TI) y `RRHH` (Jefe_RRHH).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE (m.nombre = 'Sistema' AND r.nombre = 'Jefe_TI')
   OR (m.nombre = 'RRHH' AND r.nombre = 'Jefe_RRHH')
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, t.w, t.w, false
FROM roles r
JOIN modulos m ON m.nombre = 'Sistema'
CROSS JOIN (VALUES
     ('usuarios', true),
     ('role_permisos_modulo', true),
     ('role_permisos_tabla', true),
     ('recuperacion_password', false),
     ('intentos_login', false),
     ('auditoria_log', false)
) AS t(tabla, w)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'empleados', true, true, true, false
FROM roles r JOIN modulos m ON m.nombre = 'RRHH'
WHERE r.nombre = 'Jefe_RRHH'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 011-recursos-humanos (spec.md, plan.md, research.md, data-model.md)
-- Cierra OE-8 (retención de roles críticos, capacitación en el sistema, clima
-- laboral semestral, plan de sucesión). Puebla las 4 tablas de RRHH ya reservadas
-- desde el diseño inicial (capacitaciones, empleado_capacitacion, clima_laboral,
-- plan_sucesion). Extiende aditivamente roles_puesto con es_critico y agrega una
-- única tabla nueva: acciones_retencion (research.md Decisión 1).
-- Extiende el módulo RBAC `RRHH` (primer uso por 008): Jefe_RRHH gana acceso a las
-- tablas de esta feature y Encargado_Tienda recibe un nuevo acceso de solo lectura
-- al cumplimiento de capacitación de su propia tienda (patrón Jefe_Marketing→Ventas
-- de 005 / Jefe_Comercial→Ventas de 007).
-- ============================================================================

-- 1. roles_puesto: marca de puesto crítico (FR-001) — aditiva, no rompe filas de 001.
ALTER TABLE roles_puesto ADD COLUMN IF NOT EXISTS es_critico BOOLEAN NOT NULL DEFAULT false;

-- 2. acciones_retencion — única tabla nueva de la feature (FR-002, research.md Decisión 1).
CREATE TABLE IF NOT EXISTS acciones_retencion (
    accion_id BIGSERIAL PRIMARY KEY,
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id) ON DELETE CASCADE,
    fecha DATE NOT NULL DEFAULT CURRENT_DATE,
    descripcion TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_acciones_retencion_empleado_id ON acciones_retencion(empleado_id);

-- 3. RBAC — extiende el módulo `RRHH` (data-model.md, Extensión RBAC).
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, t.upd, false
FROM roles r
JOIN modulos m ON m.nombre = 'RRHH'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
CROSS JOIN (VALUES
     ('roles_puesto', false, true),
     ('acciones_retencion', true, false),
     ('capacitaciones', true, false),
     ('empleado_capacitacion', true, true),
     ('clima_laboral', true, false),
     ('plan_sucesion', true, false)
) AS t(tabla, ins, upd)
WHERE r.nombre = 'Jefe_RRHH'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- Encargado_Tienda: nuevo acceso concedido de solo lectura al módulo `RRHH`
-- (cumplimiento de capacitación de su propio personal, FR-005).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, false
FROM roles r, modulos m
WHERE m.nombre = 'RRHH' AND r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'empleado_capacitacion', true, false, false, false
FROM roles r JOIN modulos m ON m.nombre = 'RRHH'
WHERE r.nombre = 'Encargado_Tienda'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 012-traslados-stock-entre-tiendas (spec.md, plan.md, research.md, data-model.md)
-- Cierra OT-2.5 (OE-2 Operaciones/Compras): visibilidad de stock entre sucursales
-- y flujo completo solicitud -> aprobacion/rechazo -> despacho -> recepcion de
-- traslados entre tiendas, con trazabilidad de responsable y fecha por transicion.
-- Primer y unico consumidor de `traslados_stock` (reservada desde el diseno base).
-- Sin tabla nueva: extension aditiva del CHECK de estado + columnas de trazabilidad.
-- RBAC: sin rol ni modulo nuevo; nivel de tabla para `traslados_stock` bajo el
-- modulo `Operaciones` ya reservado (Jefe_Operaciones toda la red; Encargado_Tienda
-- con alcance a su tienda, validado en la capa de servicio).
-- ============================================================================

-- 1. estado: + 'rechazado' (research.md Decision 1).
ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS traslados_stock_estado_check;
ALTER TABLE traslados_stock ADD CONSTRAINT traslados_stock_estado_check
    CHECK (estado IN ('solicitado','en_transito','recibido','cancelado','rechazado'));

-- 2. Columnas de trazabilidad por transicion (research.md Decision 2, FR-011).
ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS resuelto_por INTEGER REFERENCES empleados(empleado_id);
ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_resolucion TIMESTAMP;
ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS recibido_por INTEGER REFERENCES empleados(empleado_id);
ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_recepcion TIMESTAMP;
ALTER TABLE traslados_stock ADD COLUMN IF NOT EXISTS fecha_cancelacion TIMESTAMP;
ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_resolucion;
ALTER TABLE traslados_stock ADD CONSTRAINT chk_traslados_stock_resolucion
    CHECK (estado NOT IN ('en_transito','recibido','rechazado')
           OR (resuelto_por IS NOT NULL AND fecha_resolucion IS NOT NULL));
ALTER TABLE traslados_stock DROP CONSTRAINT IF EXISTS chk_traslados_stock_recepcion;
ALTER TABLE traslados_stock ADD CONSTRAINT chk_traslados_stock_recepcion
    CHECK (estado <> 'recibido' OR (recibido_por IS NOT NULL AND fecha_recepcion IS NOT NULL));

-- 3. Indices de apoyo (listado semanal FR-012 + filtro por tienda).
CREATE INDEX IF NOT EXISTS idx_traslados_stock_estado ON traslados_stock(estado) WHERE estado IN ('solicitado','en_transito');
CREATE INDEX IF NOT EXISTS idx_traslados_stock_tienda_origen ON traslados_stock(tienda_origen_id, estado);
CREATE INDEX IF NOT EXISTS idx_traslados_stock_tienda_destino ON traslados_stock(tienda_destino_id, estado);

-- 4. RBAC — traslados_stock bajo el modulo Operaciones (data-model.md).
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'traslados_stock', true, true, true, false
FROM roles r
JOIN modulos m ON m.nombre = 'Operaciones'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
WHERE r.nombre IN ('Jefe_Operaciones','Encargado_Tienda')
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- ============================================================================
-- EXTENSIÓN — Feature 010-plataforma-datos-tactico-estrategico (spec.md, plan.md, research.md, data-model.md)
-- Cierra OT-7.1 (OE-7 TI/Datos — modelo de datos único + carga/integración diaria)
-- y OO-7.5.1 (OT-7.5 gobierno de datos — calidad y trazabilidad del pipeline ELT),
-- que 008 dejó explícitamente pendiente de evaluar aquí.
-- 4 tablas de CONTROL del pipeline en PostgreSQL (Principio II/III — el resultado
-- de cada corrida es un registro real, no un estado en memoria de Airflow). Los
-- DATOS de negocio del warehouse (fact_venta + dimensiones) viven SÓLO en
-- ClickHouse (data_platform/clickhouse/schema_warehouse.sql), nunca aquí.
-- RBAC: sin rol ni módulo nuevo — módulo `TI` (Jefe_TI) ya reservado desde 004.
-- ============================================================================

-- 1. modelo_datos_warehouse — catálogo del modelo único (FR-001, research.md Decisión 1).
CREATE TABLE IF NOT EXISTS modelo_datos_warehouse (
    entidad_id SERIAL PRIMARY KEY,
    nombre_entidad VARCHAR(60) NOT NULL UNIQUE,
    tipo VARCHAR(10) NOT NULL CHECK (tipo IN ('fact','dimension')),
    tabla_origen_postgres VARCHAR(60) NOT NULL,
    descripcion TEXT,
    activa BOOLEAN NOT NULL DEFAULT true,
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_definicion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. corrida_carga — una fila por corrida de UNA entidad (research.md Decisión 2).
--    Exclusión mutua por destino (FR-005): índice único parcial WHERE estado = 'en_progreso'.
CREATE TABLE IF NOT EXISTS corrida_carga (
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
    CONSTRAINT chk_corrida_carga_fin CHECK (estado = 'en_progreso' OR fecha_fin IS NOT NULL),
    CONSTRAINT chk_corrida_carga_filas CHECK (estado <> 'exitosa' OR filas_cargadas IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_corrida_carga_en_progreso
    ON corrida_carga(entidad_id) WHERE estado = 'en_progreso';
CREATE INDEX IF NOT EXISTS idx_corrida_carga_entidad_fecha
    ON corrida_carga(entidad_id, fecha_inicio DESC);

-- 3. registro_calidad_carga — señalar, nunca bloquear (FR-007, research.md Decisión 4).
CREATE TABLE IF NOT EXISTS registro_calidad_carga (
    registro_id BIGSERIAL PRIMARY KEY,
    corrida_id BIGINT NOT NULL REFERENCES corrida_carga(corrida_id) ON DELETE CASCADE,
    descripcion_problema VARCHAR(300) NOT NULL,
    identificador_registro VARCHAR(100),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_registro_calidad_carga_corrida ON registro_calidad_carga(corrida_id);

-- 4. politica_gobierno_datos — append-only (FR-009/FR-010, research.md Decisión 5).
CREATE TABLE IF NOT EXISTS politica_gobierno_datos (
    politica_id BIGSERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    definido_por INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 5. RBAC — Jefe_TI sobre el módulo `TI` ya reservado (data-model.md §RBAC).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, true
FROM roles r, modulos m
WHERE m.nombre = 'TI' AND r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, t.upd, false
FROM roles r JOIN modulos m ON m.nombre = 'TI'
CROSS JOIN (VALUES
     ('modelo_datos_warehouse', true, true),
     ('corrida_carga', false, false),
     ('registro_calidad_carga', false, false),
     ('politica_gobierno_datos', true, false)
) AS t(tabla, ins, upd)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;


-- ============================================================================
-- EXTENSIÓN — Feature 009-dashboards-multinivel (spec.md, plan.md, research.md, data-model.md)
-- Cierra OT-7.4 (OE-7 TI/Datos): dashboard estratégico consolidado (Gerente
-- General, US1), dashboards tácticos por departamento (cada Jefe, US2) y
-- verificación diaria de disponibilidad de los dashboards operativos ya
-- construidos dentro de cada feature 001-007 (Jefe_TI, US3).
-- No recalcula ningún KPI (Principio VIII) — consolida y publica valores ya
-- calculados por otras features. Lo que el usuario consulta es un snapshot real
-- en PostgreSQL (Principio II); ClickHouse (010) sólo alimenta el job diario,
-- nunca el path de lectura (Principio III).
-- 3 tablas nuevas. RBAC: módulo `Direccion` (primer consumidor real,
-- Gerente_General) + módulo propio de cada Jefe + módulo `TI` (verificación).
-- ============================================================================

-- 1. registro_publicacion_dashboard — una fila por corrida del job diario para
--    cualquiera de los 3 niveles, éxito o falla (FR-001/FR-004/FR-006/FR-008).
CREATE TABLE IF NOT EXISTS registro_publicacion_dashboard (
    publicacion_id BIGSERIAL PRIMARY KEY,
    tipo_dashboard VARCHAR(20) NOT NULL
        CHECK (tipo_dashboard IN ('estrategico','tactico','operativo')),
    modulo_id INTEGER REFERENCES modulos(modulo_id),   -- sólo cuando tipo_dashboard = 'tactico'
    exito BOOLEAN NOT NULL,
    detalle_error TEXT,                                 -- sólo cuando exito = false
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_pub_dashboard_modulo_solo_tactico
        CHECK (tipo_dashboard = 'tactico' OR modulo_id IS NULL),
    CONSTRAINT chk_pub_dashboard_tactico_con_modulo
        CHECK (tipo_dashboard <> 'tactico' OR modulo_id IS NOT NULL),
    CONSTRAINT chk_pub_dashboard_error_si_falla
        CHECK (exito OR detalle_error IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS idx_registro_publicacion_tipo_fecha
    ON registro_publicacion_dashboard(tipo_dashboard, fecha_hora DESC);

-- 2. dashboard_kpi — snapshot de valores ya calculados (research.md Decisión 2).
--    disponible = false + valor NULL: mecanismo explícito para OE-4 (Principio VII).
CREATE TABLE IF NOT EXISTS dashboard_kpi (
    kpi_id BIGSERIAL PRIMARY KEY,
    publicacion_id BIGINT NOT NULL
        REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,
    dimension VARCHAR(60) NOT NULL,     -- 'OE-1'..'OE-8' (estratégico) o modulos.nombre (táctico)
    nombre_kpi VARCHAR(100) NOT NULL,
    valor DECIMAL(14,4),
    disponible BOOLEAN NOT NULL DEFAULT true,
    CONSTRAINT chk_dashboard_kpi_valor_si_disponible CHECK (disponible OR valor IS NULL)
);
CREATE INDEX IF NOT EXISTS idx_dashboard_kpi_publicacion ON dashboard_kpi(publicacion_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_kpi_dimension ON dashboard_kpi(dimension);

-- 3. dashboard_operativo_estado — verificación, no recálculo (research.md Decisión 3).
CREATE TABLE IF NOT EXISTS dashboard_operativo_estado (
    estado_id BIGSERIAL PRIMARY KEY,
    publicacion_id BIGINT NOT NULL
        REFERENCES registro_publicacion_dashboard(publicacion_id) ON DELETE CASCADE,
    tienda_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    nombre_dashboard VARCHAR(60) NOT NULL,   -- 'alertas_reposicion', 'cuadre_caja', ...
    fecha_ultima_actualizacion TIMESTAMP,     -- MAX(fecha_hora) de la tabla fuente para esa tienda
    disponible BOOLEAN NOT NULL              -- false si tiene más de 1 día de antigüedad (FR-007)
);
CREATE INDEX IF NOT EXISTS idx_dashboard_operativo_estado_publicacion
    ON dashboard_operativo_estado(publicacion_id);
CREATE UNIQUE INDEX IF NOT EXISTS uq_dashboard_operativo_estado_tienda_nombre
    ON dashboard_operativo_estado(publicacion_id, tienda_id, nombre_dashboard);
CREATE INDEX IF NOT EXISTS idx_dashboard_operativo_estado_no_disponible
    ON dashboard_operativo_estado(tienda_id, nombre_dashboard) WHERE disponible = false;

-- 4. RBAC — Gerente_General sobre el módulo `Direccion` (primer consumidor real).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, false
FROM roles r, modulos m
WHERE m.nombre = 'Direccion' AND r.nombre = 'Gerente_General'
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, false, false, false
FROM roles r JOIN modulos m ON m.nombre = 'Direccion'
CROSS JOIN (VALUES ('registro_publicacion_dashboard'), ('dashboard_kpi')) AS t(tabla)
WHERE r.nombre = 'Gerente_General'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- 5. RBAC — cada Jefe_* sobre `dashboard_kpi` en su propio módulo (dashboard táctico, FR-004/FR-005).
INSERT INTO role_permisos_modulo (role_id, modulo_id, puede_ver, puede_editar)
SELECT r.role_id, m.modulo_id, true, false
FROM (VALUES
     ('Jefe_Comercial','Comercial'), ('Jefe_Marketing','Marketing_CRM'),
     ('Jefe_Operaciones','Operaciones'), ('Jefe_Finanzas','Finanzas'),
     ('Jefe_TI','TI'), ('Jefe_RRHH','RRHH')
) AS x(rol, modulo)
JOIN roles r ON r.nombre = x.rol
JOIN modulos m ON m.nombre = x.modulo
ON CONFLICT (role_id, modulo_id) DO NOTHING;

INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'dashboard_kpi', true, false, false, false
FROM (VALUES
     ('Jefe_Comercial','Comercial'), ('Jefe_Marketing','Marketing_CRM'),
     ('Jefe_Operaciones','Operaciones'), ('Jefe_Finanzas','Finanzas'),
     ('Jefe_TI','TI'), ('Jefe_RRHH','RRHH')
) AS x(rol, modulo)
JOIN roles r ON r.nombre = x.rol
JOIN modulos m ON m.nombre = x.modulo
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- 6. RBAC — Gerente_General puede leer cualquier dashboard táctico (FR-005).
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, 'dashboard_kpi', true, false, false, false
FROM roles r
JOIN modulos m ON m.nombre IN ('Comercial','Marketing_CRM','Operaciones','Finanzas','TI','RRHH')
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
WHERE r.nombre = 'Gerente_General'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;

-- 7. RBAC — Jefe_TI: verificación operativa (toda la red) + trigger manual de FR-010.
INSERT INTO role_permisos_tabla (role_id, modulo_id, nombre_tabla, can_select, can_insert, can_update, can_delete)
SELECT r.role_id, m.modulo_id, t.tabla, true, t.ins, false, false
FROM roles r JOIN modulos m ON m.nombre = 'TI'
JOIN role_permisos_modulo rpm ON rpm.role_id = r.role_id AND rpm.modulo_id = m.modulo_id
CROSS JOIN (VALUES
     ('registro_publicacion_dashboard', true),
     ('dashboard_operativo_estado', false)
) AS t(tabla, ins)
WHERE r.nombre = 'Jefe_TI'
ON CONFLICT (role_id, modulo_id, nombre_tabla) DO NOTHING;
