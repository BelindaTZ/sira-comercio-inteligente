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
    estado VARCHAR(20) NOT NULL DEFAULT 'activo'
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
