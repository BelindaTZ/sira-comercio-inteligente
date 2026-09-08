# API Contracts: Traslados de Stock entre Tiendas

**Feature**: 012-traslados-stock-entre-tiendas | **Base path**: `/api/traslados` (además, `/api/compras/sugerencias` ya existente de 001/003 embebe `disponibilidad_otras_tiendas` — ver Ronda 1)

Todos los endpoints requieren JWT válido (008) y RBAC de módulo `Operaciones` (data-model.md §RBAC). Formato de error estándar del proyecto (`{"error": {"code", "message", "details"?}}`) en todos los 4xx/5xx.

## 1. Disponibilidad de stock por sucursal (US1, FR-001)

`GET /productos/{product_id}/disponibilidad-sucursales`

Respuesta 200:
```json
{
  "product_id": 123,
  "disponibilidad": [
    {"tienda_id": 1, "nombre_tienda": "Marzú Centro", "cantidad_disponible": 340},
    {"tienda_id": 2, "nombre_tienda": "Marzú Norte", "cantidad_disponible": 12},
    {"tienda_id": 3, "nombre_tienda": "Marzú Sur", "cantidad_disponible": 0}
  ]
}
```
RBAC: `Jefe_Operaciones` (lectura, toda la red).

## 2. Sugerencia de orden de compra extendida (US1, FR-002)

`GET /ordenes-compra/sugerencias` (endpoint ya existente de 001, extendido)

Cada ítem de la respuesta agrega el campo `disponibilidad_otras_tiendas` (mismo shape que el endpoint 1), calculado en la misma consulta — sin request adicional del frontend.

## 3. Registrar solicitud de traslado (US2, FR-003)

`POST /traslados`

Body:
```json
{
  "product_id": 123,
  "tienda_origen_id": 2,
  "tienda_destino_id": 1,
  "cantidad": 10
}
```
Respuesta 201: el traslado creado, `estado: "solicitado"`. 422 si `tienda_origen_id == tienda_destino_id` (CHECK de schema) o `cantidad <= 0`.
RBAC: `Encargado_Tienda` (alta, cualquier tienda como destino — la solicitud la origina quien necesita el producto), `Jefe_Operaciones`.

## 4. Listar traslados pendientes de resolución (US2)

`GET /traslados?estado=solicitado&tienda_origen_id={id}`

RBAC: `Encargado_Tienda` (limitado a `tienda_origen_id` = su propia tienda), `Jefe_Operaciones` (toda la red).

## 5. Aprobar o rechazar un traslado (US2, FR-004, FR-005, FR-006)

`PATCH /traslados/{traslado_id}/resolucion`

Body:
```json
{"decision": "aprobar"}
```
o
```json
{"decision": "rechazar", "motivo": "stock insuficiente para cubrir ventas propias"}
```
Respuesta 200: traslado con `estado: "en_transito"` (si aprobó) o `"rechazado"` (si rechazó), `resuelto_por` y `fecha_resolucion` completados. 409 si la cantidad solicitada excede `inventario.cantidad_disponible` de la tienda origen en el momento de resolver (Edge Case, FR-005) — cuerpo incluye el stock real disponible.
RBAC: `Encargado_Tienda` de la tienda origen únicamente (validado en servicio), `Jefe_Operaciones`.

## 6. Confirmar recepción (US3, FR-007, FR-008, FR-010)

`PATCH /traslados/{traslado_id}/recepcion`

Respuesta 200: traslado con `estado: "recibido"`, `recibido_por` y `fecha_recepcion` completados; `inventario.cantidad_disponible` de la tienda destino incrementado; si el producto es perecedero, se crea el lote de destino con `fecha_vencimiento` heredada del lote de origen consumido. 409 si el traslado no está en `en_transito`.
RBAC: `Encargado_Tienda` de la tienda destino únicamente, `Jefe_Operaciones`.

## 7. Cancelar una solicitud (US2/US3, FR-009)

`PATCH /traslados/{traslado_id}/cancelacion`

Respuesta 200: traslado con `estado: "cancelado"`, `fecha_cancelacion` completada. 409 si el traslado ya no está en `solicitado`.
RBAC: el empleado solicitante (`empleado_id`) o `Jefe_Operaciones`.

## 8. Listado semanal de traslados (US1/US3, FR-012)

`GET /traslados/reporte-semanal?desde={fecha}&hasta={fecha}`

Respuesta 200: lista de traslados del periodo con su estado actual, incluyendo los que quedaron `en_transito` sin confirmar (bandera `pendiente_confirmacion: true` cuando `estado == "en_transito"`).
RBAC: `Jefe_Operaciones` (toda la red).
