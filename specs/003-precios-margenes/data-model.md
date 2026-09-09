# Data Model: Precios Dinámicos, Márgenes y Comparación de Competencia (003-precios-margenes)

**Fase 1 de `/speckit-plan`**. Dos tablas de esta feature ya existían en el esquema base sin usar (`historial_precios`, `margenes_objetivo` — módulo CATÁLOGO DE PRODUCTOS de `01_operativo_postgres.sql`); esta feature las activa y agrega solo lo que el spec exige y el esquema base no cubre: factor de sensibilidad por categoría, propuestas de ajuste de precio, la extensión de `venta_detalle` para el descuento manual autorizado y su margen real, la revisión de líneas marcadas, el registro de competidores y su precio de referencia (con fuente manual, Open Prices o sintética — `research.md` §5), y una tabla mínima de configuración para los tres valores que el spec pide como "configurables". Todos los cambios son aditivos (Principio VIII).

## 1. Margen Objetivo (y Regla de Ajuste de Precio)

- **Tabla**: `margenes_objetivo` (ya existe, sin usar hasta esta feature; **se extiende** con `factor_sensibilidad`).
- **Campos clave**: `product_category` (PK), `margen_objetivo_pct`, `factor_sensibilidad` (**nuevo**, DECIMAL nullable — `NULL` significa que esa categoría todavía no tiene una regla de ajuste activa, el job semanal de `research.md` §2/§6 simplemente la omite).
- **Relaciones**: 1:N lógico con `productos` vía `product_category` (no hay FK física porque `product_category` no es clave en `productos`, es un valor de texto compartido — mismo patrón ya usado en el esquema base).
- **Validación**: `margen_objetivo_pct BETWEEN 0 AND 100` (ya existente). `factor_sensibilidad BETWEEN 0 AND 1` cuando no es `NULL` (FR-004). La entidad "Regla de Ajuste de Precio" del spec **no es una tabla nueva**: es 1:1 con la categoría, igual que `margenes_objetivo` — separarla habría duplicado la clave `product_category` sin ninguna relación N:1 real que lo justifique (Principio VIII, DRY). La tolerancia mínima de desviación (2pp por defecto) y el margen mínimo global de respaldo no son por categoría — viven en `configuracion_pricing` (entidad 7).

## 2. Margen Objetivo Efectivo (ancla/nicho)

- **No es una tabla**: es un valor calculado en tiempo de consulta, nunca persistido — `margen_objetivo_efectivo(producto)` = `margenes_objetivo.margen_objetivo_pct` (de `productos.product_category`) + modificador fijo según `productos.es_ancla` (`-5pp` ancla / `+3pp` nicho, `research.md` §3), con piso en `configuracion_pricing.margen_minimo_global_pct`.
- **Relaciones**: N:1 con `productos` (usa `es_ancla`, ya existente desde 001) y con `margenes_objetivo` (usa `product_category`).
- **Validación**: FR-007/SC-003 — nunca el mismo valor para ancla y nicho de la misma categoría. No se persiste porque cambia si cambia `margenes_objetivo.margen_objetivo_pct` o la clasificación `es_ancla` del producto — persistirlo obligaría a mantenerlo sincronizado en dos lugares sin necesidad (Principio VIII).

## 3. Propuesta de Ajuste de Precio

- **Tabla**: `propuesta_ajuste_precio` (**nueva**).
- **Campos clave**: `propuesta_id` (PK), `product_id` (FK), `precio_actual`, `precio_propuesto`, `margen_esperado_pct`, `estado` (`pendiente`/`aprobada`/`rechazada`), `fecha_generada`, `fecha_resolucion` (NULL mientras `pendiente`), `aprobado_por` (FK a `empleados`, NULL mientras `pendiente`).
- **Relaciones**: N:1 con `productos`. N:1 opcional con `empleados` (quien la resuelve).
- **Validación**: `precio_actual`/`precio_propuesto ≥ 0`. `precio_propuesto` se calcula con la fórmula de `research.md` §2 (nunca bajo `costo × 1.01`). `CHECK (estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL))` — no puede quedar resuelta sin fecha ni responsable (FR-006, SC-002: ninguna se publica sin aprobación explícita).
- **Transiciones de estado**: `pendiente` → `aprobada` (actualiza `productos.precio_base` y `historial_precios`, ver entidad 4 — FR-006) o `pendiente` → `rechazada` (no cambia nada más, FR-005). Ninguna transición de vuelta a `pendiente`; una propuesta rechazada no se reintenta, el siguiente job semanal genera una propuesta nueva si la desviación persiste.

## 4. Historial de Precio

- **Tabla**: `historial_precios` (ya existe, sin usar hasta esta feature; **sin cambios de esquema**).
- **Campos clave**: `historial_id` (PK), `product_id` (FK), `tienda_id` (FK nullable a `tiendas`), `precio`, `fecha_inicio`, `fecha_fin` (NULL = vigente).
- **Relaciones**: N:1 con `productos`, N:1 opcional con `tiendas`.
- **Validación**: `CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio)` (ya existente). Esta feature escribe siempre con `tienda_id = NULL` (precio único para toda la cadena en el MVP, `research.md` §1) — la columna queda disponible sin usar con valor no nulo para una futura diferenciación por tienda.
- **Transiciones de estado**: al aprobar una propuesta (entidad 3), la fila vigente (`fecha_fin IS NULL`) se cierra (`fecha_fin = CURRENT_DATE`) y se inserta una fila nueva vigente — nunca se actualiza el `precio` de una fila ya cerrada (Principio II, registro histórico real).

## 5. Línea de Venta (extendida — descuento manual autorizado y margen real)

- **Tabla**: `venta_detalle` (ya existe desde 001; **se extiende**).
- **Campos clave nuevos**: `motivo_descuento` (VARCHAR, NULL si no hubo descuento manual), `empleado_aplica_id` (FK a `empleados`, NULL si no hubo descuento), `empleado_autoriza_id` (FK a `empleados`, NULL si no hubo descuento), `margen_real` (DECIMAL, calculado para **toda** línea confirmada, no solo las descontadas — FR-002), `margen_bajo_minimo` (BOOLEAN, default `false`).
- **Relaciones**: sin cambio (N:1 con `ventas` y `productos`, ya documentado en `data-model.md` de 001). El monto del descuento en sí reutiliza `venta_detalle.retail_disc`, ya existente y sin uso hasta esta feature (Assumptions de `spec.md`) — no se agrega una columna de monto nueva.
- **Validación**: `CHECK ((empleado_aplica_id IS NULL AND empleado_autoriza_id IS NULL) OR (empleado_aplica_id IS NOT NULL AND empleado_autoriza_id IS NOT NULL AND empleado_aplica_id <> empleado_autoriza_id))` — mismo patrón exacto que `lineas_venta_removidas` (FR-027) y `pagos_proveedor` (FR-034) de 001: sin excepción por monto, ambos vacíos (sin descuento) o ambos llenos y distintos (FR-009). El rol de `empleado_autoriza_id` (`Encargado_Tienda` o superior) se valida en la capa de servicio, no en el DDL (`research.md` §4). `margen_real` se calcula al confirmar la venta con el precio ya descontado y el costo vigente (FR-002); `margen_bajo_minimo` solo se marca `true` cuando la línea tuvo descuento manual autorizado **y** `margen_real` quedó bajo el margen objetivo efectivo del producto (FR-010) — una línea sin descuento con margen naturalmente bajo no activa esta marca, porque OT-1.3/FR-009/FR-010 acotan el control específicamente al descuento manual, no a cualquier causa de margen bajo.
- **Transiciones de estado**: `margen_bajo_minimo` se fija una sola vez al confirmar la venta (junto con `margen_real`), nunca se recalcula después — igual que `sales_value` en 001, es un valor congelado al momento de la venta (Principio II).

## 6. Revisión de Margen Bajo

- **Tabla**: `revision_margen_bajo` (**nueva** — FR-012 pide "registrar la acción correctiva tomada" y ninguna tabla existente tiene dónde guardar eso; sin esta tabla el listado consolidado semanal de Jefe_Comercial sería de solo lectura, sin poder cerrar el ciclo de gestión).
- **Campos clave**: `revision_id` (PK), `venta_detalle_id` (FK **UNIQUE** a `venta_detalle`), `revisado_por` (FK a `empleados`), `accion_correctiva` (texto libre), `fecha_revision`.
- **Relaciones**: 1:1 con Línea de Venta (una línea marcada se revisa una sola vez; corregir la nota exige un `UPDATE`, no una fila nueva).
- **Validación**: solo tiene sentido crear una fila si `venta_detalle.margen_bajo_minimo = true` (validado en la capa de servicio, no con un `CHECK` cruzado entre tablas). Una línea sin revisión simplemente no tiene fila aquí — el listado de FR-011 la sigue mostrando como pendiente.

## 7. Configuración de Pricing

- **Tabla**: `configuracion_pricing` (**nueva** — clave/valor mínimo para los 3 números que el spec exige como "configurables" sin darles ya un hogar: margen mínimo global de respaldo, tolerancia de desviación para generar propuestas, umbral de alerta de competencia).
- **Campos clave**: `clave` (PK, texto), `valor` (DECIMAL), `descripcion`.
- **Filas iniciales**: `margen_minimo_global_pct = 5.0` (Edge Case de `spec.md`, FR-007), `tolerancia_ajuste_pp = 2.0` (`research.md` §2, FR-005), `umbral_alerta_competencia_pct = 5.0` (FR-016).
- **Relaciones**: ninguna (tabla de configuración global, sin FK).
- **Validación**: se prefiere una tabla clave/valor genérica sobre 3 columnas sueltas en alguna tabla existente o 3 tablas de una sola fila cada una — evita elegir un "dueño" artificial para valores que no pertenecen a ninguna categoría/producto en particular (Principio VIII). Jefe_Comercial la edita vía un endpoint simple de configuración, no requiere una pantalla por valor.

### 7.1 Configuración de Impuestos y Precios Netos / PVP con IVA

- **Tabla**: `configuracion_impuestos` (clave/valor para parámetros tributarios generales, tarifa de IVA `iva_porcentaje_vigente = 15.0000` y código SRI `iva_codigo_sri = 4.0000`).
- **PVP y Precio Neto**: En el catálogo maestro y punto de venta, `precio_base` representa el **PVP Final (con IVA incluido del 15%)**. El precio neto sin impuestos se calcula dinámicamente: `precio_neto = precio_base / (1 + iva_pct / 100)`. La pantalla 'Catálogo Maestro de Productos & Precios' expone tanto el PVP Final (+ IVA) como el Precio Neto (sin IVA) para visualización de los roles autorizados (incluido `Encargado_Tienda`).
- **Seguridad**: `configuracion_impuestos` no es editable en la UI para evitar alteraciones no autorizadas; se parametriza únicamente a nivel de base de datos.


## 8. Competidor

- **Tabla**: `competidores` (**nueva** — el spec original solo pedía "precio de referencia de competencia" sin identificar al competidor; la investigación de mercado que aportó el usuario muestra que las herramientas reales del sector (Prisync, Price2Spy, Dealavo) siempre capturan por competidor nombrado, no un precio suelto sin origen).
- **Campos clave**: `competidor_id` (PK), `nombre` (texto), `tipo` (`supermercado` / `tienda_barrio` / `tienda_digital`), `ciudad` (texto, nullable — apoya la relevancia geográfica que pidió el usuario cuando el competidor no opera en todas las ciudades donde Marzú tiene tiendas).
- **Relaciones**: 1:N con Precio de Referencia de Competencia (entidad 9).
- **Validación**: `tipo` restringido a los tres valores anteriores (mismo patrón de catálogo cerrado ya usado en otros `CHECK` de texto del esquema). No tiene relación con `tiendas` de Marzú — es la competencia externa, nunca una sucursal propia.

## 9. Precio de Referencia de Competencia

- **Tabla**: `precio_competencia` (**nueva**).
- **Campos clave**: `precio_competencia_id` (PK), `product_id` (FK), `competidor_id` (FK a `competidores`, **nullable** — `NULL` cuando `fuente_captura = 'open_prices'`, dato crowdsourced sin competidor nombrado), `tienda_id` (FK nullable a `tiendas` — relevancia geográfica: precio válido solo para esa tienda de Marzú, o para toda la cadena si es `NULL`), `precio`, `fecha_captura`, `es_promocional` (BOOLEAN, default `false`), `fuente_captura` (`manual` / `open_prices` / `sintetico`, `research.md` §5), `registrado_por` (FK a `empleados`, NULL para `open_prices` y `sintetico` — ambos son automáticos, sin un Jefe_Comercial detrás de esa fila puntual).
- **Relaciones**: N:1 con `productos`. N:1 opcional con `competidores` (entidad 8). N:1 opcional con `tiendas` (ya existente desde 001).
- **Validación**: `precio ≥ 0`. `fuente_captura IN ('manual', 'open_prices', 'sintetico')`. La desviación de FR-015/FR-016 siempre usa la fila con `fecha_captura` más reciente por producto (`MAX(fecha_captura)`), sin importar su fuente, nunca un promedio histórico — un producto sin ninguna fila no genera alerta (Edge Case de `spec.md`: "ausencia de dato no es evidencia de desviación"). `fuente_captura` reemplaza al booleano `es_sintetico` de la versión anterior de esta entidad: con tres fuentes reales (no dos) un booleano ya no alcanza para distinguir `manual` de `open_prices`, ambas no-sintéticas pero de naturaleza distinta (atribuible a un competidor nombrado vs. crowdsourced anónimo) — se prefiere un solo campo de catálogo cerrado sobre dos booleanos (`es_sintetico` + `es_crowdsourced`) que podrían combinarse de forma inválida (Principio VIII, KISS). No existe validación cruzada a nivel de `CHECK` entre `fuente_captura` y `competidor_id`/`registrado_por` (p. ej. exigir que `manual` siempre traiga ambos) — se valida en la capa de servicio, igual que la regla de rol de `empleado_autoriza_id` en la entidad 5, porque no es un control anti-fraude que justifique el costo de un `CHECK` (a diferencia del `CHECK` de autorización de descuento, que sí protege contra manipulación directa de la base).

## Trazabilidad cruzada

| Entidad | FR | OO / OT |
|---|---|---|
| Margen Objetivo (y Regla de Ajuste) | FR-001, FR-004 | OO-1.1.1, OT-1.1 |
| Margen Objetivo Efectivo (ancla/nicho) | FR-007, FR-008 | OT-1.2, OO-1.2.1, OO-1.2.2 |
| Propuesta de Ajuste de Precio | FR-005, FR-006 | OO-1.1.2, OT-1.1 |
| Historial de Precio | FR-006 | OT-1.1 |
| Línea de Venta (extendida) | FR-002, FR-003, FR-009, FR-010 | OT-1.3, OO-1.3.1 |
| Revisión de Margen Bajo | FR-011, FR-012 | OO-1.3.1, OO-1.3.2 |
| Configuración de Pricing | FR-004, FR-007, FR-016 | OT-1.1, OT-1.3, OT-4.3 |
| Competidor | FR-014 | OT-4.3, OO-4.3.1 |
| Precio de Referencia de Competencia | FR-014, FR-015, FR-016 | OT-4.3, OO-4.3.1, OO-4.3.2 |
