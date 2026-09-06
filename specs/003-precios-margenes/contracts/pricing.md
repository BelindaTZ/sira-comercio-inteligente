# Contrato: Módulo Pricing

Backend: `backend/src/modules/pricing/router.py`, salvo el descuento manual (FR-009/FR-010), que extiende `backend/src/modules/ventas/router.py` — decisión explícita de `plan.md` (Project Structure): es una acción sobre una venta en curso, meterla en `pricing/` obligaría a ese módulo a conocer el ciclo de vida de una venta (Principio VIII, DRY). RBAC: módulo `Comercial` (rol principal `Jefe_Comercial`; `Encargado_Tienda` en el listado diario de margen bajo de su tienda — FR-011; `Cajero`/`Encargado_Tienda` en el endpoint de descuento manual, dentro del módulo `Ventas`).

## Márgenes objetivo y regla de ajuste (FR-001, FR-004)

### GET /api/pricing/margenes
Lista `margenes_objetivo` por categoría junto con su `factor_sensibilidad` (`null` si la categoría aún no tiene regla de ajuste activa — el job semanal la omite, `research.md` §2). Rol: `Jefe_Comercial`.

### PATCH /api/pricing/margenes/{product_category}
Body parcial: `{margen_objetivo_pct?, factor_sensibilidad?}`. `factor_sensibilidad` entre 0 y 1 (típicamente 0.1-0.5). (FR-001, FR-004). Rol: `Jefe_Comercial`.

## Propuestas de ajuste de precio (FR-005, FR-006)

### GET /api/pricing/propuestas
Query: `estado` (`pendiente`/`aprobada`/`rechazada`), `product_category?`. Paginado (Principio XII). Generadas por el job semanal (`research.md` §2/§6), nunca creadas manualmente por este endpoint.

### GET /api/pricing/propuestas/{propuesta_id}
Detalle: `precio_actual`, `precio_propuesto`, `margen_esperado_pct`, `estado`, fechas.

### POST /api/pricing/propuestas/{propuesta_id}/aprobar
200 → actualiza `productos.precio_base`, cierra la vigencia anterior en `historial_precios` e inserta la nueva (`research.md` §1). 409 si la propuesta ya no está `pendiente`. Ninguna propuesta se publica sin esta llamada explícita (FR-006, SC-002). Rol: `Jefe_Comercial`.

### POST /api/pricing/propuestas/{propuesta_id}/rechazar
Body: `{motivo?}`. 200 → `estado = "rechazada"`, no cambia nada más. No se reintenta automáticamente — el siguiente job semanal genera una propuesta nueva si la desviación persiste (FR-005). Rol: `Jefe_Comercial`.

## Margen objetivo efectivo — ancla/nicho (FR-007, FR-008)

### GET /api/pricing/productos/{product_id}/margen-efectivo
Valor calculado en el momento, nunca persistido (`data-model.md` entidad 2). 200 → `{margen_objetivo_categoria, modificador_pp, margen_objetivo_efectivo, margen_minimo_global_aplicado: bool}`. (FR-007)

### PATCH /api/catalogo/productos/{product_id}
La reclasificación ancla/nicho de un producto ya existente (FR-008) reutiliza el endpoint genérico ya definido en `contracts/catalogo.md` de 001 (`{clasificacion?}` dentro de su body parcial) — no se crea un endpoint nuevo (Principio VIII, DRY; Principio VI, no redefinir lo que 001 ya resolvió). No recalcula retroactivamente el margen ya reportado de ventas pasadas (Principio II).

## Descuento manual en punto de venta (FR-009, FR-010)

### POST /api/ventas/{venta_id}/lineas/{linea_id}/descuento
Body: `{tipo: "monto"|"porcentaje", valor, motivo, empleado_aplica_id, empleado_autoriza_id}`. `empleado_autoriza_id` se resuelve en el frontend re-autenticando (PIN/contraseña) al Encargado_Tienda físicamente presente — nunca un campo de texto libre que el cajero teclea a mano (mismo mecanismo ya implícito en `DELETE .../lineas/{linea_id}` de 001, documentado aquí explícitamente, `research.md` §4). Sin excepción por monto (FR-009). 200 → línea actualizada (`venta_detalle.retail_disc`, `margen_real` recalculado con el precio ya descontado y el costo vigente); si `margen_real` queda bajo el margen objetivo efectivo del producto, la línea se marca `margen_bajo_minimo = true` para revisión posterior, **sin bloquear la venta** (FR-010). 403 si `empleado_autoriza_id == empleado_aplica_id`, o si el rol de `empleado_autoriza_id` no está en `{Encargado_Tienda, Jefe_Comercial, Jefe_Operaciones, Jefe_Finanzas, Gerente_General}` (`research.md` §4). Rol: `Cajero` (aplica), `Encargado_Tienda` o superior de esa lista (autoriza).

## Revisión de margen bajo (FR-011, FR-012)

### GET /api/pricing/margen-bajo
Query: `tienda_id?, revisado: bool?`. Paginado. Lista líneas con `margen_bajo_minimo = true` (join contra `revision_margen_bajo` para saber si ya tienen `accion_correctiva`). Sin filtro `tienda_id`, devuelve el consolidado de todas las tiendas (uso semanal de Jefe_Comercial, FR-012); con `tienda_id`, el listado diario de una tienda (FR-011).

### POST /api/pricing/margen-bajo/{venta_detalle_id}/revision
Body: `{accion_correctiva}`. 200 → crea (o actualiza si ya existía, vía `UPDATE`, nunca una fila nueva — `data-model.md` entidad 6) la fila en `revision_margen_bajo`. 422 si `venta_detalle.margen_bajo_minimo` no es `true`. (FR-012). Rol: `Jefe_Comercial` (consolidado) o `Encargado_Tienda` (líneas de su propia tienda).

## Reporte de margen (FR-003, FR-013)

### GET /api/pricing/reportes/margen
Query: `fecha_desde, fecha_hasta, product_category?`. 200 → margen real acumulado por categoría en el rango, comparado contra su margen objetivo vigente (FR-003). Generado bajo demanda (no un job) — el corte mensual de FR-013 es este mismo endpoint invocado con el rango del mes. Rol: `Jefe_Comercial`.

## Competencia — competidores y precios de referencia (FR-014, FR-015, FR-016)

### GET /api/pricing/competidores
Query: `tipo?, ciudad?`. Lista el catálogo de competidores nombrados (`research.md` §5).

### POST /api/pricing/competidores
Body: `{nombre, tipo: "supermercado"|"tienda_barrio"|"tienda_digital", ciudad?}`. (FR-014). Rol: `Jefe_Comercial`.

### POST /api/pricing/productos/{product_id}/precio-competencia
Body: `{competidor_id, precio, fecha_captura?, tienda_id?, es_promocional?}`. Siempre crea la fila con `fuente_captura = "manual"` (el servidor lo fija, nunca viene del body) y `registrado_por` = el usuario autenticado. `tienda_id` es opcional — `null` significa que ese precio de competencia aplica a toda la cadena, no solo a una tienda de Marzú (relevancia geográfica). (FR-014). Rol: `Jefe_Comercial`.

### GET /api/pricing/productos/{product_id}/precio-competencia
Historial de capturas de ese producto (cualquier `fuente_captura`), ordenado por `fecha_captura` descendente. Cada fila indica su fuente (`manual`/`open_prices`/`sintetico`) y, si aplica, el competidor y la tienda de referencia.

### GET /api/pricing/competencia/alertas
Query: `umbral?` (por defecto, `configuracion_pricing.umbral_alerta_competencia_pct`). Paginado. Lista los productos cuya desviación entre `precio_base` y su `precio_competencia` más reciente (sin importar la fuente) supera el umbral — generada por el job semanal (`research.md` §5/§6). Un producto sin ninguna fila en `precio_competencia` no aparece (ausencia de dato no es evidencia de desviación, Edge Case de `spec.md`). (FR-015, FR-016). Rol: `Jefe_Comercial`.

**Nota de implementación** (sin endpoint propio — automático): al registrar un producto en vivo con código de barras real (`POST /api/catalogo/productos` de 001) y en el job semanal de competencia, el sistema consulta Open Prices (prices.openfoodfacts.org) por ese código de barras e inserta una fila `fuente_captura = "open_prices"` si hay dato disponible — best-effort, un fallo o ausencia de dato no bloquea nada (`research.md` §5/§6). No aplica a los productos sembrados del dataset Dunnhumby (barcode sintético).

## Configuración de pricing (FR-004, FR-007, FR-016)

### GET /api/pricing/configuracion
Lista las 3 filas de `configuracion_pricing` (`margen_minimo_global_pct`, `tolerancia_ajuste_pp`, `umbral_alerta_competencia_pct`).

### PATCH /api/pricing/configuracion/{clave}
Body: `{valor}`. (FR-004, FR-007, FR-016). Rol: `Jefe_Comercial`.
