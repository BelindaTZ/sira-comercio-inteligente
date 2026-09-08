# Quickstart: Traslados de Stock entre Tiendas

**Feature**: 012-traslados-stock-entre-tiendas

## Escenario 1 — Consultar stock en otras sucursales (US1, MVP)

1. Como `Jefe_Operaciones`, autenticarse (JWT de 008).
2. `GET /api/traslados/productos/{product_id}/disponibilidad-sucursales` para un producto ya sembrado en al menos dos tiendas.
3. Verificar que la respuesta trae `cantidad_disponible` de cada tienda en una sola llamada.
4. `GET /api/compras/sugerencias` y confirmar que cada sugerencia trae `disponibilidad_otras_tiendas` embebida, sin una segunda llamada.

## Escenario 2 — Solicitar, aprobar y despachar un traslado (US2)

1. Como `Encargado_Tienda` de la tienda destino, `POST /api/traslados` indicando `product_id`, `tienda_origen_id`, `tienda_destino_id`, `cantidad` ≤ stock disponible de origen. Verificar `estado: "solicitado"`.
2. Como `Encargado_Tienda` de la tienda origen, `PATCH /api/traslados/{id}/resolucion` con `{"decision": "aprobar"}`. Verificar `estado: "en_transito"`, `resuelto_por` y `fecha_resolucion` completados.
3. Verificar que `inventario.cantidad_disponible` de la tienda origen disminuyó en la cantidad trasladada, y que existe una fila nueva en `movimientos_inventario` con `tipo='traslado_salida'`.
4. Repetir el paso 1-2 con una cantidad mayor al stock disponible de origen y verificar el 409 con el stock real informado (Edge Case, FR-005).
5. Repetir el paso 1 y, en el paso 2, usar `{"decision": "rechazar", "motivo": "..."}`. Verificar `estado: "rechazado"` y que el inventario de ninguna tienda cambió.

## Escenario 3 — Confirmar recepción (US3)

1. A partir de un traslado en `en_transito` (Escenario 2, paso 2), como `Encargado_Tienda` de la tienda destino, `PATCH /api/traslados/{id}/recepcion`.
2. Verificar `estado: "recibido"`, `recibido_por` y `fecha_recepcion` completados, `inventario.cantidad_disponible` de la tienda destino incrementado, y una fila nueva en `movimientos_inventario` con `tipo='traslado_entrada'`.
3. Repetir con un producto perecedero y verificar que el nuevo lote de la tienda destino conserva la `fecha_vencimiento` del lote de origen consumido (Edge Case, FR-010).

## Escenario 4 — Cancelar antes de aprobación

1. Registrar una solicitud de traslado (Escenario 2, paso 1) y, antes de que la tienda origen la resuelva, `PATCH /api/traslados/{id}/cancelacion` como el empleado solicitante.
2. Verificar `estado: "cancelado"` y que ningún inventario cambió.

## Escenario 5 — Listado semanal con pendientes de confirmar (FR-012)

1. Con al menos un traslado en `en_transito` sin recibir, `GET /api/traslados/reporte-semanal?desde=...&hasta=...` como `Jefe_Operaciones`.
2. Verificar que ese traslado aparece con `pendiente_confirmacion: true`.
