# Contrato: Módulo Compras

Backend: `backend/src/modules/compras/router.py`. RBAC: módulo `Operaciones` (Jefe_Operaciones) y módulo `Finanzas` (Jefe_Finanzas) para facturas/pagos.

## GET /api/compras/sugerencias
Sugerencia semanal de orden por producto/proveedor, basada en rotación y demanda reciente. (FR-023)

## POST /api/compras/ordenes
Body: `{proveedor_id, tienda_id, empleado_id, tipo: "programada"|"especial", lineas: [{product_id, cantidad, costo_unitario}], motivo_desviacion?}`. `motivo_desviacion` obligatorio si `lineas` difiere de la sugerencia. 201 → orden `pendiente` o `aprobada`. (FR-024)

## POST /api/compras/ordenes/{orden_id}/pedido-especial
Body: `{motivo}`. Genera orden `tipo="especial"` fuera del calendario pactado y envía la solicitud por correo (SendGrid) al proveedor. (FR-029)

## POST /api/compras/proveedores
Body: `{nombre, ruc?, contacto?, condiciones_pago?, frecuencia_reposicion: "semanal"|"mensual"|"trimestral"}`. (FR-028, FR-032, OO-B.7)

## PATCH /api/compras/proveedores/{proveedor_id}
Body parcial, incluye `frecuencia_reposicion`. (OO-B.8)

## POST /api/compras/facturas
Body: `{orden_id, numero_factura, monto_total, fecha_emision, fecha_vencimiento, empleado_registra_id}`. Requiere `orden_id` en estado `recibida`. 201 → factura `pendiente`. 409 si ya existe `(orden_id, numero_factura)`. (FR-033)

## GET /api/compras/facturas
Query: `estado=pendiente|vencida, vencimiento_antes=YYYY-MM-DD`. Para la revisión semanal de Finanzas (OO-6.5.2, FR-040, Ronda 10 — endpoint ya existía en este contrato; el FR correspondiente faltaba en spec.md y quedó corregido en Ronda 10).

## GET /api/compras/facturas/resumen (Ronda 10)
Query: `desde=YYYY-MM-DD, hasta=YYYY-MM-DD`. Devuelve el total agregado de cuentas por pagar (suma de `monto_total` de facturas `pendiente` + `pagada_parcial`, menos lo ya pagado) para el reporte mensual del Jefe de Finanzas a Dirección General. (FR-041)

## GET /api/compras/reportes/automatico-vs-manual (Ronda 10)
Query: `mes=YYYY-MM`. Devuelve el porcentaje de órdenes `tipo='programada'` (por sugerencia) frente a `tipo='especial'` (manual/pedido especial) del mes, comparado contra la meta de OT-2.1. Solo Jefe de Operaciones. (FR-039)

## POST /api/compras/facturas/{factura_id}/pagos
Body: `{monto, medio_pago_id, referencia?, empleado_registra_id, empleado_autoriza_id}`. 403 si `empleado_registra_id == empleado_autoriza_id`. 200 → pago registrado, estado de la factura recalculado (`pagada_parcial`/`pagada`). (FR-034, FR-035)
