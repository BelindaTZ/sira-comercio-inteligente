# Quickstart: Core de Ventas e Inventario (001-core-ventas-inventario)

Guía de validación ejecutable — no contiene código de implementación (eso vive en `tasks.md` y en el código real). Sirve para comprobar que la feature funciona de punta a punta una vez implementada.

## Prerrequisitos

- Docker Desktop corriendo (PostgreSQL 16 + MinIO — ClickHouse/Airflow NO se levantan para esta feature, Principio III).
- `01_operativo_postgres.sql` aplicado sobre la base (50 tablas + extensiones de esta feature).
- `backend/.env` con `DATABASE_URL`, `STRIPE_SECRET_KEY` (modo test — el cobro se confirma de forma síncrona, sin webhook, research.md Decisión 6), `SENDGRID_API_KEY`, credenciales de MinIO.
- Dataset Dunnhumby sembrado (productos, clientes, fabricantes) — sin esto no hay catálogo con el que probar.
- Un usuario autenticado con rol Cajero y otro con rol Encargado_Tienda (JWT emitido por la feature 008; para probar 001 de forma aislada, un token de prueba con esos roles es suficiente — ver Assumptions de spec.md).

## Levantar el entorno

```bash
docker compose up -d postgres minio
cd backend && alembic upgrade head && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Escenario 1 — Venta completa con tarjeta aprobada (US1, P1)

1. Iniciar una venta (`POST /api/ventas`).
2. Agregar 2-3 productos por código de barras (`POST /api/ventas/{id}/lineas`).
3. Cobrar con tarjeta usando la tarjeta de prueba `4242 4242 4242 4242` (`POST /api/ventas/{id}/pago-tarjeta`) → esperar `resultado: "aprobado"`.
4. Confirmar la venta como nota de venta a consumidor final (`POST /api/ventas/{id}/confirmar`).
5. **Verificar**: el stock disponible de cada producto bajó en la cantidad vendida (SC-002); el comprobante PDF se abrió automáticamente listo para imprimir/guardar al confirmar (SC-011), y también es accesible después vía `GET /api/ventas/{id}/comprobante`.

## Escenario 2 — Tarjeta rechazada y reintento con efectivo (US1)

1. Repetir pasos 1-2 del Escenario 1.
2. Cobrar con la tarjeta de prueba de rechazo de Stripe → esperar `resultado: "rechazado"`, distinto visualmente de un error técnico.
3. Reintentar el cobro con `medio_pago_id` = efectivo y confirmar.
4. **Verificar**: la venta se confirma sin haber perdido las líneas ya escaneadas (FR-031).

## Escenario 3 — Remoción de línea con doble autorización (US1)

1. Iniciar venta, agregar una línea.
2. Intentar `DELETE .../lineas/{id}` con `autoriza_empleado_id` igual al `cajero_id` de la venta → esperar 403.
3. Repetir con un `autoriza_empleado_id` de un Encargado_Tienda distinto → esperar 200.
4. **Verificar**: SC-007 (100% de líneas removidas quedan con un autorizador identificado).

## Escenario 4 — Alerta de reposición y sugerencia de compra (US3, P3)

1. Vender un producto hasta que su stock disponible caiga bajo el punto de reposición calculado.
2. Ejecutar el job diario de cálculo (o su endpoint manual de prueba).
3. **Verificar**: aparece una alerta `pendiente` (`GET /api/inventario/alertas`); no se duplica si se vuelve a ejecutar el job el mismo día (FR-021).
4. Consultar la sugerencia semanal (`GET /api/compras/sugerencias`) y aprobarla ajustando la cantidad → **verificar** que exige `motivo_desviacion` (FR-024).

## Escenario 5 — Ciclo completo de compra a proveedor (US3)

1. Aprobar una orden de compra (Escenario 4) y registrar su recepción (`POST /api/inventario/recepciones`) → la orden pasa a `recibida`.
2. Registrar la factura del proveedor (`POST /api/compras/facturas`) con `fecha_vencimiento` a 30 días.
3. Registrar un pago parcial con `empleado_registra_id` igual a `empleado_autoriza_id` → esperar 403.
4. Repetir con dos empleados distintos → esperar 200, factura en `pagada_parcial`.
5. **Verificar**: SC-009 (todo pago tiene un autorizador distinto de quien lo registró).

## Escenario 6 — Recepción de mercadería y rotación FIFO/FEFO (US2, P2)

1. Registrar dos lotes del mismo producto con distinta `fecha_vencimiento`.
2. Vender una cantidad que solo alcance el primer lote.
3. **Verificar**: el descuento tomó primero el lote con vencimiento más próximo (research.md #4); las pantallas de inventario muestran ese lote priorizado visualmente (FR-015).

## Escenario 7 — Stock máximo por categoría y alerta de exceso (US3, Ronda 9)

1. Como Jefe de Operaciones, definir el stock máximo de una categoría para una tienda (`PUT /api/inventario/stock-maximo`).
2. Registrar una recepción de mercadería de un producto de esa categoría que deje el stock disponible por encima del máximo definido.
3. **Verificar**: la recepción se registra normalmente (no se bloquea) y aparece una alerta tipo `exceso_stock` visible para el encargado de esa tienda (FR-037, FR-038).

## Escenario 8 — Verificación de anaquel de alta demanda y escalamiento de quiebre (US3, Ronda 10)

1. Como Reponedor, registrar la verificación diaria de anaquel de un producto clasificación A, marcándolo disponible o no disponible.
2. Registrar un evento de quiebre de stock (FR-022) para ese mismo producto clasificación A.
3. **Verificar**: el evento queda marcado como quiebre de alta demanda y el Jefe de Operaciones de esa tienda recibe la notificación de inmediato, sin esperar al reporte mensual (FR-042, FR-043).

## Fuera de alcance de esta guía

Cuadre de caja horario (006), pronóstico predictivo completo (004), CLV/fidelización (002) — no se validan aquí aunque compartan datos con esta feature.
