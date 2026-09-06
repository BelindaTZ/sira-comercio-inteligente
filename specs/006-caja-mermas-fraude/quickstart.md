# Quickstart: Caja, Mermas y Fraude

**Feature**: `006-caja-mermas-fraude` | **Precondición**: backend levantado con las migraciones de esta feature aplicadas, dataset ya sembrado (001-005), token de prueba con el rol correspondiente (Principio IV, dependencia de 008).

## Escenario 1 — Cuadre horario con diferencia detectada automáticamente (User Story 1, MVP)

1. Como `Cajero`, `POST /api/caja/apertura` con `{caja_id, fondo_inicial: 200.00}` → se recibe `apertura_id`.
2. Se registran ventas normales de 001 a nombre de ese cajero durante la hora siguiente.
3. `POST /api/caja/cierre` con `{caja_id, total_registrado: 480.00}` (un valor distinto de la suma real de ventas).
4. Verificar que la respuesta trae `diferencia` calculada automáticamente (no enviada por el cliente) y `marcado_para_revision: true`.
5. Repetir el cuadre con `total_registrado` exactamente igual al total esperado → verificar `diferencia: 0.00` y `marcado_para_revision: false`.

## Escenario 2 — El Encargado de Tienda valida todas las cajas de su tienda a la vez (User Story 1, AC4)

1. Repetir el Escenario 1 para dos o más cajas de la misma tienda.
2. Como `Encargado_Tienda`, `GET /api/caja/cierres?tienda_id=&fecha=hoy`.
3. Verificar que la respuesta trae el cuadre de **todas** las cajas de la tienda en una sola consulta, sin tener que pedirlas una por una.

## Escenario 3 — Certificación y actualización de datáfonos (User Story 2)

1. Como `Jefe_TI`, `PUT /api/caja/configuracion-seguridad-pagos` con `{version_minima_firmware: "3.2.0"}`.
2. Registrar (o verificar ya sembrado) un datáfono con `version_firmware: "2.9.0"`.
3. `GET /api/caja/datafonos?estado=requiere_actualizacion` → verificar que ese datáfono aparece listado como no conforme.
4. `PATCH /api/caja/datafonos/{datafono_id}/actualizar` con `{version_firmware_nueva: "3.2.0"}`.
5. Repetir el `GET` del paso 3 → verificar que el datáfono ya no aparece, y que `fecha_ultima_actualizacion` quedó registrada.

## Escenario 4 — Reporte mensual de patrones y apertura de incidente (User Story 3)

1. Sembrar varios cuadres (Escenario 1) de un mismo cajero con diferencia negativa repetida en distintos días del mismo mes.
2. Sembrar (o usar uno ya existente de 001) un `ajuste_inventario` con diferencia negativa grande.
3. Como `Jefe_Finanzas`, `GET /api/caja/reporte-diferencias?mes=&anio=`.
4. Verificar que la respuesta agrupa las diferencias por cajero/turno (no solo el total agregado de la tienda) y que el ajuste de inventario aparece en `ajustes_senalados` del mismo reporte, no en un endpoint separado.
5. `POST /api/caja/incidentes-fraude` con `{empleado_id, cierre_id, descripcion}` → verificar `estado: 'abierto'`.

## Escenario 5 — Aplicación del protocolo de escalamiento sobre un incidente (User Story 4)

1. Como `Jefe_Finanzas`, `PUT /api/caja/protocolo-escalamiento` con `{texto: "..."}`.
2. Usando el incidente abierto del Escenario 4, como `Encargado_Tienda`: `GET /api/caja/protocolo-escalamiento` → verificar que el texto completo es consultable.
3. `PATCH /api/caja/incidentes-fraude/{incidente_id}/aplicar-protocolo` con `{acciones_tomadas: "..."}` → verificar `estado: 'en_revision'`.
4. Como `Jefe_Finanzas`, `PATCH /api/caja/incidentes-fraude/{incidente_id}/cerrar` con `{resultado: 'descartado'}` → verificar `estado: 'cerrado'` sin que el empleado quede marcado como culpable.
5. Repetir el flujo completo (abrir → aplicar protocolo → cerrar) con un `empleado_id` que ya tenga `fecha_baja` en `empleados` → verificar que ninguno de los pasos se bloquea.

## Escenario 6 — Umbral de merma aceptable y seguimiento semanal (User Story 5)

1. Como `Jefe_Operaciones`, `PUT /api/caja/umbral-merma/{product_category}` con `{porcentaje_umbral: 5.0}`.
2. Verificar (o sembrar) mermas ya registradas (001) de esa categoría en una tienda durante la semana evaluada.
3. Como `Encargado_Tienda`, `GET /api/caja/tiendas/{tienda_id}/seguimiento-merma-semanal?semana=`.
4. Verificar que la respuesta trae el porcentaje acumulado frente al umbral, y `supera_umbral: true` cuando corresponde.
5. Verificar que ninguna venta, recepción de mercadería ni registro de merma de 001 se bloquea aunque `supera_umbral` sea `true` (Edge Case, FR-019).
