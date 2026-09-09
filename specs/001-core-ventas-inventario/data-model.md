# Data Model: Core de Ventas e Inventario (001-core-ventas-inventario)

**Fase 1 de `/speckit-plan`** — Entidades extraídas de `spec.md` (sección Key Entities), mapeadas contra `01_operativo_postgres.sql` (incluye las extensiones agregadas durante la especificación de esta feature). No se define DDL nuevo aquí: se referencia el ya validado. Reglas de validación citadas por su FR; transiciones de estado solo donde el spec o la constitución las exige.

## 1. Producto (Catálogo)

**Tabla**: `productos`

**Campos clave**: `product_id` (PK, natural key del dataset), `codigo_barras` (único), `costo`, `precio_base`, `es_perecedero`, `vida_util_dias`, `clasificacion_abc`, `es_ancla`, `imagen_url`, `activo`.

**Relaciones**: 1:N con `venta_detalle`, `lotes`, `orden_compra_detalle`, `mermas`, `ajustes_inventario`. N:1 con `fabricantes`.

**Validación**: costo/precio_base ≥ 0. Clasificación ancla/nicho obligatoria al alta (FR-012). Baja es lógica (`activo=false`), nunca DELETE físico — conserva historial de ventas (FR-011).

**Transiciones**: `activo=true` → `activo=false` (descontinuado, irreversible en este flujo — reactivar requeriría un alta nueva, fuera de alcance de esta feature).

### 1.1 Gestión de precios y márgenes (pantalla de Catálogo, feature 013)

La pantalla de Catálogo es de **gestión de precios y márgenes**, no multicanal — `.specify/memory/domain-context.md` es explícito: SIRA es de gestión interna para tiendas físicas, ningún OO ni feature contempla e-commerce, delivery ni autoservicio digital del cliente. (La migración 0024 introdujo por error una tabla `regla_recargo_canal` con canales `delivery_app`/`ecommerce`; la 0025 la elimina.)

- **`GET /catalogo/precios`** — matriz de sólo lectura: cada SKU con su margen real vs. el `margen_objetivo_pct` de su categoría y el estado resultante (`optimo` ≥ objetivo · `ajustado` dentro de 5 pp · `bajo` · `sin_precio`).
- **`POST /catalogo/productos/{id}/simular-precio`** — Simulador de Impacto: proyecta el margen y la ganancia mensual ante un cambio de PVP usando `margenes_objetivo.factor_sensibilidad` (0 = inelástico, 1 = muy elástico) como elasticidad de la categoría y las unidades/mes históricas del SKU. "Aplicar" persiste el nuevo `precio_base` vía el `PATCH` de producto (FR-010, conserva el histórico).
- **`GET /catalogo/resumen`** — KPIs de la cabecera. Los que agregan sobre todo el histórico de ventas (margen bruto ponderado, huella promocional) se leen de un snapshot `catalogo_kpi` (una fila) que refresca el job `refrescar_catalogo_kpi` cada 3 h — mismo criterio que los KPIs de los dashboards de la feature 009; no se calculan por request. Si el job nunca corrió, el endpoint calcula en vivo una vez.

## 2. Venta (Ticket/Comprobante)

**Tabla**: `ventas`

**Campos clave**: `venta_id` (PK), `tienda_id`, `cajero_id`, `household_id` (nullable = venta anónima), `medio_pago_id`, `total`, `estado`, `tipo_comprobante`, `identificacion_comprador`, `razon_social_comprador`.

**Relaciones**: 1:N con `venta_detalle`, `lineas_venta_removidas`, `intentos_pago_tarjeta`, `devoluciones`. 1:1 con `anulaciones_venta` (solo si se anula).

**Validación**: `total ≥ 0` (FR-001). No se puede confirmar si algún producto excede el stock disponible (FR-006). `tipo_comprobante='factura'` requiere `identificacion_comprador` real; por defecto `nota_venta` con identificación genérica `9999999999999` (FR-036).

**Transiciones de estado** (`estado`): `en_curso` → `confirmada` (al cobrar, FR-001/FR-004) → `anulada` (solo antes del cierre de caja de esa jornada, revierte el descuento de inventario asociado, no elimina el registro; genera fila en `anulaciones_venta` con motivo — FR-007). No hay transición de vuelta desde `anulada`.

## 3. Línea de Venta

**Tabla**: `venta_detalle`

**Campos clave**: `venta_detalle_id` (PK), `venta_id` (FK), `product_id`, `cantidad`, `sales_value` (precio unitario aplicado).

**Relaciones**: N:1 con `ventas` y `productos`. El/los lote(s) de origen del descuento FIFO se resuelven en `movimientos_inventario` (`referencia_tabla='venta_detalle'`), no como FK directa — una línea puede descontar de más de un lote si el primero no cubre la cantidad completa.

**Acumulación (feature 013)**: agregar el mismo `product_id` al ticket suma sobre la línea existente (una fila por SKU, como el POS de referencia). Excepción: si la línea ya tiene descuentos (`retail_disc`/`coupon_disc`/`coupon_match_disc`), se crea una fila nueva para no mezclar precios.

### 3.1 Pantalla de POS (feature 013)

`frontend/src/modules/pos/PuntoDeVentaPage.vue` — arquetipo Cockpit: columna de
registro rápido (escáner + grid de productos con foto/precio/stock desde
`GET /api/ventas/catalogo`, filtrable por categoría) + ticket con `+` por línea y
"Quitar" (con autorización, FR-027 — no hay `−` libre porque reducir lo
registrado es sub-registro); columna de cobro con medios de pago, montos rápidos
de efectivo y vuelto. El grid necesitó un endpoint de catálogo propio del módulo
`Ventas` porque el Cajero no lee `productos`/`inventario`.

**Validación**: `cantidad > 0`. El precio unitario aplicado no cambia si el precio del producto se actualiza después (FR-010) — es un valor congelado al momento de la venta.

## 4. Línea de Venta Removida (auditoría anti-fraude)

**Tabla**: `lineas_venta_removidas`

**Campos clave**: `remocion_id` (PK), `venta_id`, `product_id`, `cantidad`, `cajero_id`, `autoriza_empleado_id`, `motivo`.

**Relaciones**: N:1 con `ventas`.

**Validación**: `CHECK (cajero_id <> autoriza_empleado_id)` — control de doble persona, obligatorio sin excepciones (FR-027, SC-007). Solo aplica a líneas de una venta aún `en_curso` (no confirmada).

## 5. Intento de Pago con Tarjeta

**Tabla**: `intentos_pago_tarjeta`

**Campos clave**: `intento_id` (PK), `venta_id`, `resultado` (aprobado/rechazado/error_tecnico), `referencia_pasarela`, `monto`.

**Relaciones**: N:1 con `ventas` — una venta puede tener varios intentos (reintento tras rechazo o error técnico, FR-031) pero solo uno con `resultado='aprobado'` la lleva a `confirmada`.

**Validación**: `resultado` distingue explícitamente rechazo del banco de error técnico de comunicación (FR-030) — nunca se conflaten en el mismo valor.

## 6. Devolución

**Tabla**: `devoluciones`

**Campos clave**: `devolucion_id` (PK), `venta_id`, `product_id`, `cantidad`, `motivo`, `reintegra_inventario`.

**Relaciones**: N:1 con `ventas` y `productos`.

**Validación**: `cantidad > 0`. El inventario se reintegra solo si `reintegra_inventario=true`, es decir, solo cuando el motivo lo justifica (FR-025) — un motivo como "producto dañado por el cliente" no reintegra stock vendible.

## 7. Lote de Inventario

**Tabla**: `lotes`

**Campos clave**: `lote_id` (PK), `product_id`, `tienda_id`, `cantidad_recibida`, `fecha_vencimiento` (nullable), `codigo_lote_proveedor` (trazabilidad del lote físico del proveedor, distinto del código de barras del producto).

**Relaciones**: 1:N con `recepcion_mercaderia`. Consumido por el descuento FIFO/FEFO de `venta_detalle` vía `movimientos_inventario`.

**Validación**: `cantidad_recibida > 0`. Orden de consumo FIFO/FEFO determinístico: `fecha_vencimiento ASC NULLS LAST, cantidad_recibida ASC, lote_id ASC` (research.md #4) bajo `SELECT ... FOR UPDATE` para evitar sobreventa concurrente (FR-006).

## 7.1 Ubicación del Producto en Sala (feature 013)

**Tabla**: `ubicacion_producto` (migración 0021)

**Campos clave**: PK compuesta `(product_id, tienda_id)`, `pasillo` (obligatorio),
`gondola` (opcional), `nivel` (opcional), `actualizado_por` → `empleados`.

**Relaciones**: N:1 con `productos` y `tiendas` (ambas `ON DELETE CASCADE`).

**Propósito**: Principio XII — la pantalla "Gestión de Inventario & Alertas FIFO"
muestra dónde está cada SKU ("Pasillo 01 · G-03"). Una fila por (producto,
tienda); cambiar la ubicación es un `UPDATE` de la misma fila (la spec no pide
histórico de movimientos de góndola).

**RBAC**: módulo `Operaciones`. `Reponedor` y `Encargado_Tienda` la editan
(insert/update); `Jefe_Operaciones` la ve (select).

## 8. Recepción de Mercadería

**Tabla**: `recepcion_mercaderia`

**Campos clave**: `recepcion_id` (PK), `orden_id`, `lote_id`, `tienda_id`, `empleado_id`.

**Relaciones**: N:1 con `ordenes_compra` y `lotes` — es el segundo elemento del 3-way match (orden + recepción + factura).

**Validación**: Solo se puede recibir contra una orden en estado `aprobada` (FR-014); al registrarse, la orden pasa a `recibida`.

## 9. Ajuste de Inventario

**Tabla**: `ajustes_inventario`

**Campos clave**: `ajuste_id` (PK), `product_id`, `tienda_id`, `cantidad_sistema`, `cantidad_fisica`, `diferencia` (columna generada), `motivo` + `observaciones` (migración 0022 — trazabilidad de auditoría del descuadre).

**Validación**: `diferencia` se calcula en base de datos (`GENERATED ALWAYS AS`), no en la aplicación — es un dato derivado puro, no lógica de negocio (FR-017).

## 10. Merma

**Tabla**: `mermas`

**Campos clave**: `merma_id` (PK), `product_id`, `tienda_id`, `cantidad`, `causa` (caducidad/robo/rotura/error_humano), `valor`, `empleado_id`, `destino` + `observaciones` (migración 0022 — ficha de la declaración: destino físico de las unidades y detalle del siniestro).

**Relaciones**: N:1 con `productos`. No tiene FK directa a `lotes` en el DDL base — se identifica por producto/tienda (limitación heredada del esquema base, no introducida por esta feature).

**Validación**: `causa` es un valor cerrado de la lista (FR-018). El encargado valida o rechaza el registro (FR-019) — este estado de validación vive en la capa de aplicación sobre el registro, no como columna adicional en esta versión del DDL.

## 11. Alerta de Reposición / Vencimiento / Exceso de Stock

**Tabla**: `alertas_inventario`

**Campos clave**: `alerta_id` (PK), `tipo` (reposicion/vencimiento/exceso_stock — este último agregado en Ronda 9 para OT-2.4), `product_id`, `tienda_id`, `lote_id` (obligatorio solo si `tipo='vencimiento'`), `estado`.

**Ronda 9**: el tipo `exceso_stock` se genera al registrar una recepción de mercadería que deja el stock disponible de un producto por encima del `stock_maximo_categoria` vigente para su categoría/tienda (FR-038); no requiere `lote_id`, igual que `reposicion`.

**Relaciones**: N:1 con `productos`, `tiendas`, `lotes` (nullable).

**Validación**: `CHECK (tipo <> 'vencimiento' OR lote_id IS NOT NULL)`. Único índice parcial `(product_id, tienda_id, tipo)` con `estado='pendiente'` — impide una segunda alerta activa duplicada para el mismo producto/tienda mientras la anterior no se atienda (FR-021).

**Transiciones**: `pendiente` → `atendida` (el encargado la marca, FR-021). No hay reapertura de la misma fila — una nueva ocurrencia genera una alerta nueva.

## 12. Evento de Quiebre de Stock

**Tabla**: `eventos_quiebre_stock`

**Campos clave**: `evento_id` (PK), `product_id`, `tienda_id`, `empleado_id`, `demanda_estimada_no_satisfecha`, `es_alta_demanda` (Ronda 10: calculado al insertar según `productos.clasificacion_abc='A'` vigente en ese momento, no recalculado retroactivamente).

**Ronda 10**: cuando `es_alta_demanda=true`, el servicio DEBE notificar de inmediato al Jefe de Operaciones de la tienda (FR-043) — no es una columna que dispare notificación por trigger de BD (Principio XI), se resuelve en la capa de servicio del backend al insertar.

**Validación**: Es un registro append-only (FR-022) — no se edita ni se anula, alimenta el reporte mensual de demanda perdida (OO-5.2.2).

## 13. Orden de Compra

**Tablas**: `ordenes_compra` (cabecera) + `orden_compra_detalle` (líneas).

**Campos clave (cabecera)**: `orden_id` (PK), `proveedor_id`, `tienda_id`, `empleado_id`, `estado`, `tipo` (programada/especial), `motivo_desviacion`.

**Relaciones**: N:1 con `proveedores`. 1:N con `orden_compra_detalle`, `recepcion_mercaderia`, `facturas_proveedor`.

**Validación**: `motivo_desviacion` obligatorio en la capa de aplicación cuando la cantidad aprobada difiere de la sugerida (FR-024). `tipo='especial'` se origina siempre por FR-029 (correo fuera de calendario), nunca por el cálculo semanal automático.

**Transiciones**: `pendiente` (sugerida) → `aprobada` (o `cancelada`) → `recibida` (tras `recepcion_mercaderia`, FR-014). No retrocede.

## 14. Proveedor

**Tabla**: `proveedores`

**Campos clave**: `proveedor_id` (PK), `nombre`, `ruc`, `condiciones_pago`, `frecuencia_reposicion` (semanal/mensual/trimestral).

**Relaciones**: 1:N con `ordenes_compra`.

**Validación**: `ruc` no se valida contra el SRI (solo formato, dato descriptivo — ver Assumptions de spec.md). `frecuencia_reposicion` dispara el envío automático de la orden sugerida según su propio calendario (FR-028), independiente del ciclo semanal genérico de otros proveedores.

## 15. Factura de Proveedor

**Tabla**: `facturas_proveedor`

**Campos clave**: `factura_id` (PK), `orden_id` (FK), `numero_factura`, `monto_total`, `fecha_emision`, `fecha_vencimiento`, `estado`, `empleado_registra_id`.

**Relaciones**: N:1 con `ordenes_compra` (tercer elemento del 3-way match: orden + recepción + factura). 1:N con `pagos_proveedor`.

**Validación**: Único índice `(orden_id, numero_factura)` — no se puede registrar la misma factura dos veces contra la misma orden. `fecha_vencimiento >= fecha_emision` (FR-033). Solo se registra contra una orden ya en estado `recibida`.

**Transiciones**: `pendiente` → `pagada_parcial` (algún pago registrado, suma < monto_total) → `pagada` (suma = monto_total) — recalculado en la capa de servicio del backend al confirmar cada pago (FR-035), no con un trigger de base de datos (Principio XI). `vencida` se deriva al leer si `fecha_vencimiento < hoy` y `estado <> 'pagada'` (cálculo de consulta, no una transición almacenada).

## 16. Pago a Proveedor

**Tabla**: `pagos_proveedor`

**Campos clave**: `pago_id` (PK), `factura_id` (FK), `monto`, `medio_pago_id`, `referencia`, `empleado_registra_id`, `empleado_autoriza_id`.

**Relaciones**: N:1 con `facturas_proveedor` y `medios_pago`.

**Validación**: `CHECK (empleado_registra_id <> empleado_autoriza_id)` — control de doble persona obligatorio, sin excepciones (FR-034, SC-009), mismo patrón que `lineas_venta_removidas`. `monto > 0`; la suma de pagos de una factura no debe exceder `monto_total` (validado en la capa de servicio, no en el DDL, para poder dar un mensaje de error claro antes del INSERT).

## 17.1 Verificación de Anaquel — Alta Demanda (Ronda 10)

**Tabla**: `verificacion_anaquel`

**Campos clave**: `id` (PK), `product_id` (FK `productos`, debe tener `clasificacion_abc='A'` vigente al momento del registro — validado en la capa de servicio, no en el DDL, porque la clasificación puede cambiar después), `tienda_id` (FK `tiendas`), `fecha`, `disponible` (boolean), `empleado_id` (FK `empleados`, el Reponedor que la registró).

**Campos de auditoría de planograma** (migración 0023, todos opcionales — la referencia de UI "Verificar y Auditar Anaquel en Góndola" los pide): `facing_asignado` / `facing_real` (frentes que exige el planograma vs. contados en sala; `real < asignado` ⇒ quiebre visual), `esl_ok` (la etiqueta electrónica de precio coincide con el POS central), `fifo_ok` (el lote más antiguo está al frente), `observaciones` (texto libre del operador, ≤300 en la API). Se registran en el mismo POST y no rompen inserts previos.

**Relaciones**: N:1 con `productos`, `tiendas`, `empleados`.

**Validación**: Único índice `(product_id, tienda_id, fecha)` — una sola verificación por producto/tienda/día (Edge Case: si se reintenta el mismo día, se actualiza la fila existente en vez de duplicarla).

**Transiciones**: ninguna — es un registro puntual del día, no tiene ciclo de estados.

## 17. Stock Máximo por Categoría (Ronda 9)

**Tabla**: `stock_maximo_categoria`

**Campos clave**: `id` (PK), `product_category` (mismo dominio de texto que `productos.product_category`), `tienda_id` (FK `tiendas`), `cantidad_maxima`, `empleado_id` (FK `empleados`, quien lo definió), `fecha_definicion`.

**Campos de capacidad / reabastecimiento** (migración 0023, todos opcionales — la referencia de UI "Configurar Stock Máximo por Categoría" los pide): `capacidad_gondola` (límite físico lineal en unidades), `stock_minimo_reorden` (buffer crítico que dispara la solicitud prioritaria), `dias_cobertura` (cobertura objetivo, 2-14 en la UI), `politica_sobrestock` (`CHECK IN ('estricto','autorizado')` — bloqueo estricto de OC vs. sobre-stock con autorización del Gerente Comercial).

**Relaciones**: N:1 con `tiendas` y `empleados`. Sin FK a `productos` — aplica a nivel de categoría, no de producto individual, mismo criterio de granularidad que `umbral_merma_categoria` (006).

**Validación**: Único índice `(product_category, tienda_id)` — un solo valor vigente a la vez; una redefinición trimestral actualiza (UPDATE) la fila existente, sin historial de versiones (a diferencia de la política de seguridad de pagos en 007, que sí lo requiere).

**Transiciones**: ninguna — es un valor de configuración vigente, sin ciclo de estados.

## Trazabilidad cruzada (resumen)

| Entidad | FR principales | OO/OT |
|---|---|---|
| Venta / Línea de Venta | FR-001 a FR-008, FR-030, FR-031, FR-036 | OO-B.12, OO-B.13, OT-4.1, OO-4.1.1 |
| Línea de Venta Removida | FR-027 | OT-6.4 |
| Lote / Recepción | FR-005, FR-014, FR-015 | OO-5.3.1, OO-5.3.2, OO-B.15 |
| Alerta / Quiebre | FR-016, FR-020 a FR-022 | OT-5.1, OT-5.2, OO-5.1.1/2, OO-5.2.1/2 |
| Merma / Ajuste | FR-017 a FR-019 | OO-5.4.1/2, OO-B.16 |
| Orden de Compra / Proveedor | FR-023, FR-024, FR-028, FR-029, FR-032 | OT-2.1, OO-2.1.1 a 2.1.5 |
| Stock Máximo por Categoría | FR-037, FR-038 | OT-2.4, OO-2.4.1, OO-2.4.2 |
| Verificación de Anaquel (Alta Demanda) | FR-042, FR-043 | OT-4.4, OO-4.4.1, OO-4.4.2 |
| Reportes Ronda 10 (compras automático/manual, cuentas por pagar) | FR-039, FR-040, FR-041 | OO-2.1.5, OO-6.5.2, OO-6.5.3 |
| Factura / Pago a Proveedor | FR-033 a FR-035 | OT-6.5, OO-6.5.1 a 6.5.3 |
| Devolución | FR-025, FR-026 | OO-B.14 |
