# Contrato: Módulo Inventario

Backend: `backend/src/modules/inventario/router.py`. RBAC: módulo `Operaciones` (Reponedor registra, Encargado_Tienda valida/atiende).

## POST /api/inventario/recepciones
Body: `{orden_id, product_id, tienda_id, cantidad, fecha_vencimiento?, codigo_lote_proveedor?}`. Requiere `orden_id` en estado `aprobada`. 201 → crea `lotes` + `recepcion_mercaderia`, la orden pasa a `recibida`. (FR-014)

## GET /api/inventario/lotes
Query: `product_id, tienda_id, proximos_a_vencer=true&dias=N`. Ordena por `fecha_vencimiento ASC NULLS LAST` para priorizar rotación (FR-015).

## GET /api/inventario/alertas
Query: `tipo=reposicion|vencimiento, estado=pendiente, tienda_id`. (FR-016, FR-020)

## POST /api/inventario/alertas/{alerta_id}/atender
Body: `{empleado_id}`. 200 → `estado="atendida"`. No genera una segunda alerta activa para el mismo producto/tienda mientras esta exista (FR-021).

## POST /api/inventario/quiebres
Body: `{product_id, tienda_id, empleado_id, demanda_estimada_no_satisfecha?}`. 201 → evento registrado (append-only). (FR-022)

## POST /api/inventario/ajustes
Body: `{product_id, tienda_id, cantidad_fisica, empleado_id}`. `cantidad_sistema` se toma del inventario actual; `diferencia` es columna calculada en BD. (FR-017)

## POST /api/inventario/mermas
Body: `{product_id, tienda_id, cantidad, causa, empleado_id}`. `causa` ∈ {caducidad, robo, rotura, error_humano}. (FR-018)

## POST /api/inventario/mermas/{merma_id}/validar
Body: `{empleado_id, decision: "validada"|"rechazada"}`. Solo Encargado_Tienda de esa tienda. (FR-019)

## PUT /api/inventario/stock-maximo
Body: `{product_category, tienda_id, cantidad_maxima, empleado_id}`. 200 → crea o actualiza (upsert) la fila vigente en `stock_maximo_categoria`. Solo Jefe_Operaciones. (FR-037, Ronda 9)

## GET /api/inventario/stock-maximo
Query: `tienda_id, product_category?`. Lista los máximos vigentes. (FR-037, Ronda 9)

## POST /api/inventario/recepciones (extendido, Ronda 9)
Además del comportamiento ya descrito arriba: si la recepción deja el stock disponible del producto por encima del `cantidad_maxima` vigente para su `product_category`/`tienda_id`, genera una `alerta_inventario` tipo `exceso_stock` sin bloquear la recepción. (FR-038)

## POST /api/inventario/verificacion-anaquel (Ronda 10)
Body: `{product_id, tienda_id, fecha, disponible, empleado_id}`. Requiere `productos.clasificacion_abc='A'` vigente para `product_id`. 201/200 → upsert por `(product_id, tienda_id, fecha)`. Solo Reponedor. (FR-042)

## POST /api/inventario/quiebres (extendido, Ronda 10)
Además del comportamiento ya descrito arriba: si `product_id` tiene `clasificacion_abc='A'` vigente, marca el evento con `es_alta_demanda=true` y notifica de inmediato al Jefe de Operaciones de la tienda. (FR-043)
