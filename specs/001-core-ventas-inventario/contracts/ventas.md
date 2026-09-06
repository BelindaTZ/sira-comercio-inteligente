# Contrato: Módulo Ventas

Backend: `backend/src/modules/ventas/router.py`. RBAC: módulo `Ventas` (rol Cajero para operar, Encargado_Tienda para autorizar/anular).

## POST /api/ventas
Inicia una venta nueva en estado `en_curso`. Body: `{tienda_id, cajero_id, household_id?}`. 201 → `{venta_id, estado: "en_curso"}`. (FR-001)

## POST /api/ventas/{venta_id}/lineas
Agrega una línea por código de barras o `product_id` + `cantidad`. 200 → línea agregada, total recalculado. 409 si `cantidad` excede stock disponible (FR-006). (FR-001)

## DELETE /api/ventas/{venta_id}/lineas/{linea_id}
Requiere `autoriza_empleado_id` (encargado, distinto del cajero) y `motivo` en el body. 200 → línea removida, queda registrada en `lineas_venta_removidas`. 403 si `autoriza_empleado_id == cajero_id`. (FR-027)

## POST /api/ventas/{venta_id}/pago-tarjeta
Inicia/reintenta un intento de cobro con tarjeta (Stripe Payment Intents, modo test). Body: `{monto}`. 200 → `{intento_id, resultado: "aprobado"|"rechazado"|"error_tecnico", referencia_pasarela}`. El cajero nunca recibe ni envía datos de tarjeta en este payload (FR-003). Puede llamarse varias veces sobre la misma venta tras rechazo/error (FR-031). (FR-003, FR-030)

## POST /api/ventas/{venta_id}/confirmar
Body: `{medio_pago_id, tipo_comprobante: "factura"|"nota_venta", identificacion_comprador?, razon_social_comprador?}`. Requiere un intento de tarjeta `aprobado` si `medio_pago_id` es tarjeta. 200 → venta `confirmada`, descuenta inventario FIFO/FEFO, genera comprobante PDF. (FR-002, FR-004, FR-005, FR-036)

## POST /api/ventas/{venta_id}/anular
Solo si la venta está `confirmada` y dentro de la jornada de caja actual. Body: `{empleado_id, motivo}`. 200 → venta `anulada`, revierte inventario, crea fila en `anulaciones_venta`. (FR-007)

## GET /api/ventas/{venta_id}/comprobante
Sirve el PDF ya generado (no lo regenera) con `Content-Disposition: inline`, para que el navegador lo abra en su visor nativo (imprimir/guardar) en vez de forzar una descarga — el frontend abre esta URL automáticamente al confirmar la venta con éxito, sin que el cajero deba buscarlo manualmente (FR-004, SC-011). 200 → `application/pdf`.

## POST /api/ventas/{venta_id}/devoluciones
Body: `{product_id, cantidad, motivo}`. 200 → devolución registrada; reintegra inventario solo si el motivo lo justifica. (FR-025, FR-026)

## GET /api/ventas
Query: `tienda_id, fecha_desde, fecha_hasta, estado, household_id`. Paginado (Principio XII). (OO-B.12)
