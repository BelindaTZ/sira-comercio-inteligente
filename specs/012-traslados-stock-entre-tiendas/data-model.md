# Data Model: Traslados de Stock entre Tiendas

**Feature**: 012-traslados-stock-entre-tiendas | **Fecha**: 2026-09-06

## Entidades reutilizadas sin cambio

- **`productos`**, **`inventario`** (`product_id, tienda_id` → `cantidad_disponible`), **`lotes`** (`product_id, tienda_id, fecha_vencimiento`) — de 001, sin ninguna modificación. US1 consulta `inventario` directamente por `product_id` agrupando por `tienda_id`.
- **`movimientos_inventario`** — el CHECK `tipo IN ('entrada','salida','ajuste','traslado_entrada','traslado_salida')` ya incluye los dos tipos que esta feature necesita (reservados desde el diseño original, nunca usados hasta ahora). Cada traslado despachado genera una fila `tipo='traslado_salida'` (tienda origen) al pasar a `en_transito`, y una fila `tipo='traslado_entrada'` (tienda destino) al confirmarse la recepción — ambas con `referencia_tabla='traslados_stock'` y `referencia_id=traslado_id`.

## Extensión aditiva: `traslados_stock` (ya reservada, primer consumidor)

Definición actual (sin cambios, `01_operativo_postgres.sql` línea 456):

```sql
CREATE TABLE traslados_stock (
    traslado_id BIGSERIAL PRIMARY KEY,
    product_id INTEGER NOT NULL REFERENCES productos(product_id),
    tienda_origen_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    tienda_destino_id INTEGER NOT NULL REFERENCES tiendas(tienda_id),
    cantidad INTEGER NOT NULL CHECK (cantidad > 0),
    estado VARCHAR(20) NOT NULL DEFAULT 'solicitado'
        CHECK (estado IN ('solicitado','en_transito','recibido','cancelado')),
    empleado_id INTEGER NOT NULL REFERENCES empleados(empleado_id),
    fecha_hora TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (tienda_origen_id <> tienda_destino_id)
);
```

Extensión propuesta (research.md Decisiones 1 y 2):

```sql
ALTER TABLE traslados_stock
    DROP CONSTRAINT traslados_stock_estado_check,
    ADD CONSTRAINT traslados_stock_estado_check
        CHECK (estado IN ('solicitado','en_transito','recibido','cancelado','rechazado')),
    ADD COLUMN resuelto_por INTEGER REFERENCES empleados(empleado_id),
    ADD COLUMN fecha_resolucion TIMESTAMP,
    ADD COLUMN recibido_por INTEGER REFERENCES empleados(empleado_id),
    ADD COLUMN fecha_recepcion TIMESTAMP,
    ADD COLUMN fecha_cancelacion TIMESTAMP,
    ADD CONSTRAINT chk_traslados_stock_resolucion
        CHECK (estado NOT IN ('en_transito','recibido','rechazado')
               OR (resuelto_por IS NOT NULL AND fecha_resolucion IS NOT NULL)),
    ADD CONSTRAINT chk_traslados_stock_recepcion
        CHECK (estado <> 'recibido' OR (recibido_por IS NOT NULL AND fecha_recepcion IS NOT NULL));

CREATE INDEX idx_traslados_stock_estado ON traslados_stock(estado) WHERE estado IN ('solicitado','en_transito');
CREATE INDEX idx_traslados_stock_tienda_origen ON traslados_stock(tienda_origen_id, estado);
CREATE INDEX idx_traslados_stock_tienda_destino ON traslados_stock(tienda_destino_id, estado);
```

Notas:
- `resuelto_por` cubre tanto la aprobación como el rechazo (un solo responsable posible por solicitud, FR-004); `recibido_por` es siempre un empleado de la tienda destino, distinto en general de `resuelto_por` (tienda origen).
- El índice parcial sobre `estado IN ('solicitado','en_transito')` acelera el listado semanal de pendientes (FR-012, "despachados sin confirmar").
- Sin nueva tabla: Principio VIII — todo el ciclo cabe en columnas aditivas sobre la tabla ya reservada.

## RBAC — extensión de tabla sobre módulo ya existente (`Operaciones`)

Módulo `Operaciones` reservado desde 001 (sin alta nueva en `modulos`). Extensión de `role_permisos_tabla`:

| Rol | Tabla | select | insert | update | delete | Alcance |
|---|---|---|---|---|---|---|
| Jefe_Operaciones | `traslados_stock` | ✔ | ✔ | ✔ | ✘ | Toda la red (las 5 tiendas) — consulta US1 y listado semanal FR-012. |
| Encargado_Tienda | `traslados_stock` | ✔ | ✔ | ✔ | ✘ | Limitado a su propia tienda como origen o destino, validado en capa de servicio (mismo patrón que `empleado_autoriza_id` de `pagos_proveedor`/`venta_detalle`) — un Encargado no puede aprobar traslados de una tienda que no es la suya. |

Sin `delete` para ningún rol: un traslado se cancela (estado `cancelado`), nunca se borra — mismo criterio que `ventas` (`estado`, no `DELETE`) desde la Ronda 6 de 001.

## Trazabilidad: FR → Entidad → OO/OT

| FR | Entidad / campo | OO / OT |
|---|---|---|
| FR-001, FR-012 | `inventario` (consulta agregada por producto) | OO-2.5.1 / OT-2.5 |
| FR-002 | Extensión de contrato de sugerencia de compra (001), campo `disponibilidad_otras_tiendas` | OO-2.5.1 / OT-2.5 |
| FR-003 | `traslados_stock` (alta, estado `solicitado`) | OO-2.5.2 / OT-2.5 |
| FR-004, FR-005 | `traslados_stock.resuelto_por/fecha_resolucion`, validación de `inventario.cantidad_disponible` | OO-2.5.2 / OT-2.5 |
| FR-006 | `traslados_stock.estado='en_transito'`, `movimientos_inventario` (`traslado_salida`), `inventario` (descuento origen) | OO-2.5.2 / OT-2.5 |
| FR-007, FR-008 | `traslados_stock.recibido_por/fecha_recepcion/estado='recibido'`, `movimientos_inventario` (`traslado_entrada`), `inventario` (alta destino) | OO-2.5.2 / OT-2.5 |
| FR-009 | `traslados_stock.estado='cancelado'/fecha_cancelacion` | OO-2.5.2 / OT-2.5 |
| FR-010 | `lotes` (nuevo lote en destino, `fecha_vencimiento` heredada) | OO-2.5.2 / OT-2.5 |
| FR-011 | Todas las columnas de trazabilidad de `traslados_stock` | OT-2.5 (calidad de dato, Principio II) |
