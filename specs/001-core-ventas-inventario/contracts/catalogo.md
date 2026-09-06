# Contrato: Módulo Catálogo

Backend: `backend/src/modules/catalogo/router.py`. RBAC: módulo `Comercial` (Jefe_Comercial/Jefe_Operaciones).

## POST /api/catalogo/productos
Body: `{codigo_barras, nombre?, categoria?, costo, precio_base, es_perecedero, vida_util_dias?, clasificacion: "ancla"|"nicho"}`. Si `nombre`/`categoria`/`imagen` faltan, intenta autocompletar consultando Open Food Facts por `codigo_barras`; si no hay coincidencia, quedan editables sin bloquear el alta. (FR-009, FR-012, FR-013)

## PATCH /api/catalogo/productos/{product_id}
Body parcial: `{precio_base?, costo?, categoria?, ...}`. No altera `sales_value` ya aplicado en ventas pasadas (congelado en `venta_detalle`). (FR-010)

## DELETE /api/catalogo/productos/{product_id}
Baja lógica (`activo=false`), conserva historial de ventas. (FR-011)

## GET /api/catalogo/productos
Query: `search, codigo_barras, categoria, activo`. Paginado.
