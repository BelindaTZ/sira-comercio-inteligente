# Quickstart: Pagos y Seguridad

**Feature**: `007-pagos-seguridad` | **Precondición**: backend levantado con las migraciones de esta feature aplicadas, dataset ya sembrado (001-006), token de prueba con el rol correspondiente (Principio IV, dependencia de 008).

## Escenario 1 — Disponibilidad diaria de un datáfono, con reevaluación al restablecer (User Story 1, MVP)

1. Como `Encargado_Tienda`, `PATCH /api/finanzas/datafonos/{datafono_id}/fuera-servicio` sobre un datáfono activo → verificar `estado='fuera_servicio'`.
2. Como `Cajero`, `GET /api/ventas/cajas/{caja_id}/datafono-disponible` sobre la caja de ese datáfono → verificar `disponible: false`.
3. Verificar (o registrar) una venta con otro medio de pago (efectivo) en esa misma caja → verificar que no se bloquea.
4. Como `Encargado_Tienda`, `PATCH /api/finanzas/datafonos/{datafono_id}/restablecer` sobre un datáfono cuyo `version_firmware` cumple el estándar vigente (006) → verificar `estado='activo'`.
5. Repetir el restablecimiento sobre un datáfono cuyo `version_firmware` NO cumple el estándar vigente → verificar `estado='requiere_actualizacion'` (no `'activo'`).

## Escenario 2 — Alta y baja de un medio de pago (User Story 2)

1. Como `Jefe_TI`, `POST /api/ventas/medios-pago` con `{nombre: "Billetera XYZ"}` → verificar `aprobado: true`, `aprobado_por` y `fecha_aprobacion` registrados.
2. Como `Cajero`, `GET /api/ventas/medios-pago/disponibles` → verificar que "Billetera XYZ" aparece en la lista.
3. Como `Jefe_TI`, `PATCH /api/ventas/medios-pago/{medio_pago_id}/baja` sobre un medio de pago existente con ventas ya registradas.
4. Repetir el `GET` del paso 2 → verificar que ya no aparece.
5. Verificar que las ventas ya registradas con ese medio de pago siguen intactas (consulta directa a `ventas`, sin cambio en `medio_pago_id` de ninguna fila histórica).

## Escenario 3 — Registro y seguimiento de un incidente de seguridad de pago, independiente de un incidente de fraude (User Story 3)

1. Como `Jefe_TI`, `POST /api/finanzas/incidentes-seguridad-pago` con `{datafono_id, descripcion: "Reporte de posible clonación"}` → verificar `estado: 'abierto'`.
2. `PATCH /api/finanzas/incidentes-seguridad-pago/{id}/transicionar` con `{estado_nuevo: 'en_investigacion'}` → verificar el cambio y `actualizado_por`/`fecha_actualizacion` completados.
3. `PATCH .../transicionar` con `{estado_nuevo: 'cerrado'}` → verificar `estado: 'cerrado'`.
4. Como `Jefe_Finanzas`, `GET /api/finanzas/incidentes-seguridad-pago/conteo?desde=&hasta=` → verificar que el conteo del periodo incluye este incidente.
5. Sobre el mismo `datafono_id`, abrir (o verificar ya abierto desde 006) un `incidente_fraude` → verificar que ambos incidentes existen de forma independiente, sin fusionarse ni afectarse entre sí.
6. Registrar un incidente de seguridad de pago sin `datafono_id` (Edge Case) → verificar que se acepta con solo la descripción.

## Escenario 4 — Política de seguridad de pagos versionada (User Story 4)

1. Como `Jefe_TI`, `PUT /api/finanzas/politica-seguridad-pagos` con `{texto: "..."}` (versión 1).
2. Como `Encargado_Tienda`, `GET /api/finanzas/politica-seguridad-pagos` → verificar que el texto completo es consultable.
3. Como `Jefe_TI`, `PUT /api/finanzas/politica-seguridad-pagos` con un texto nuevo (versión 2).
4. `GET /api/finanzas/politica-seguridad-pagos/{politica_id}` con el `politica_id` de la versión 1 → verificar que sigue siendo consultable íntegra, aunque ya no sea la vigente.

## Escenario 5 — Medición y revisión del tiempo de cobro (User Story 5)

1. Registrar una venta en vivo con `POST /api/ventas` incluyendo `fecha_inicio_cobro` al iniciar y confirmando después → verificar que la venta guardada trae ambos timestamps.
2. Repetir el paso 1 varias veces para la misma caja durante la semana.
3. Como `Encargado_Tienda`, `GET /api/ventas/cajas/{caja_id}/tiempo-cobro-semanal?semana=` → verificar `duracion_promedio_segundos` calculado sin intervención manual.
4. Anular una de esas ventas (001) y repetir el paso 3 → verificar que `cantidad_ventas_consideradas` baja en 1 y el promedio se recalcula sin esa venta (Edge Case, FR-018).
5. Repetir el registro para dos o más tiendas y, como `Jefe_Comercial`, `GET /api/ventas/tiendas/tiempo-cobro-mensual?mes=&anio=` → verificar que puede comparar el tiempo promedio entre tiendas.
6. Verificar que una venta ya sembrada del dataset Dunnhumby (sin `fecha_inicio_cobro`) no aparece considerada en ningún reporte de tiempo de cobro.
