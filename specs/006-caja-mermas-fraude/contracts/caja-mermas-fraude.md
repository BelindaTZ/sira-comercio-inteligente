# Contratos: Caja, Mermas y Fraude

**Backend**: `backend/src/modules/caja/router.py`. RBAC: módulo `Finanzas` (ya sembrado desde 001 como "Caja, cuadre, seguridad de pagos") concentra todos los endpoints de esta feature; `Jefe_TI` recibe acceso concedido a este módulo específicamente para `datafonos`/`configuracion-seguridad-pagos` (research.md Decisión 10); el reporte de patrones consulta de solo lectura `modules/inventario/` (001, `plan.md`).

## Apertura y cuadre de caja (FR-001 a FR-005)

`POST /api/caja/apertura`
- Registra la apertura de una caja al inicio del turno (FR-001).
- Body: `{caja_id, fondo_inicial}`.
- RBAC: `Cajero`.
- 201: `{apertura_id, caja_id, cajero_id, fondo_inicial, fecha_hora}`.

`POST /api/caja/cierre`
- Registra el cuadre horario; `total_esperado` se calcula en el backend (research.md Decisión 1 y 2), nunca recibido del cliente (Principio V) — FR-002, FR-003.
- Body: `{caja_id, total_registrado}`.
- RBAC: `Cajero`.
- 201: `{cierre_id, total_esperado, total_registrado, diferencia, marcado_para_revision: boolean}` — `marcado_para_revision = true` cuando `diferencia <> 0` (FR-004).

`GET /api/caja/cierres?tienda_id=&fecha=`
- Lista el estado de cuadre de todas las cajas de una tienda para una fecha (FR-005).
- RBAC: `Encargado_Tienda`.
- 200: `[{caja_id, cierre_id, cajero_id, total_esperado, total_registrado, diferencia, fecha_hora}]`.

## Datáfonos (FR-006 a FR-008)

`GET /api/caja/datafonos?estado=`
- Inventario de datáfonos, filtrable por estado; incluye los identificados como no conformes (FR-006, FR-007).
- RBAC: `Jefe_TI`.
- 200: `[{datafono_id, caja_id, modelo, version_firmware, fecha_ultima_actualizacion, estado}]`.

`PATCH /api/caja/datafonos/{datafono_id}/actualizar`
- Registra la actualización o reemplazo de un datáfono no conforme (FR-008).
- Body: `{version_firmware_nueva}`.
- RBAC: `Jefe_TI`.
- 200: datáfono actualizado a `estado='activo'`, `fecha_ultima_actualizacion=CURRENT_DATE`. 409 si el datáfono ya está `activo`.

`GET /api/caja/configuracion-seguridad-pagos`
- Estándar de seguridad de pago vigente (FR-007).
- RBAC: `Jefe_TI`.
- 200: `{config_id, version_minima_firmware, vigente_desde, actualizado_por}`.

`PUT /api/caja/configuracion-seguridad-pagos`
- Define un nuevo estándar vigente (inserta una nueva versión, research.md Decisión 5).
- Body: `{version_minima_firmware}`.
- RBAC: `Jefe_TI`.
- 201: nueva fila vigente. Efecto secundario: recalcula automáticamente la conformidad de todos los datáfonos existentes.

## Reporte mensual de patrones y escalamiento (FR-009 a FR-011)

`GET /api/caja/reporte-diferencias?mes=&anio=`
- Diferencias de cuadre agrupadas por cajero y turno (research.md Decisión 3), más los ajustes de inventario (001) con diferencia negativa por encima del umbral configurable (FR-009, FR-010).
- RBAC: `Jefe_Finanzas`.
- 200: `{cuadres: [{cajero_id, apertura_id, fecha_turno, suma_diferencias, cantidad_cuadres_con_diferencia}], ajustes_senalados: [{ajuste_id, product_id, tienda_id, diferencia, empleado_id, fecha}]}`.

`POST /api/caja/incidentes-fraude`
- Escala un patrón sospechoso abriendo un incidente de fraude (FR-011).
- Body: `{empleado_id, cierre_id?, ajuste_id?, descripcion}` — `cierre_id`/`ajuste_id` opcionales y mutuamente no exclusivos con un registro directo (data-model.md, Decisión 6).
- RBAC: `Jefe_Finanzas`.
- 201: `{incidente_id, empleado_id, cierre_id, ajuste_id, descripcion, estado: 'abierto', fecha_hora}`.

## Incidentes de fraude y protocolo de escalamiento (FR-012 a FR-016)

`GET /api/caja/incidentes-fraude?estado=`
- Lista incidentes de fraude, filtrable por estado.
- RBAC: `Jefe_Finanzas`, `Encargado_Tienda` (solo los de su tienda).
- 200: `[{incidente_id, empleado_id, estado, descripcion, acciones_tomadas, resultado, fecha_hora}]`.

`GET /api/caja/protocolo-escalamiento`
- Texto del protocolo de escalamiento vigente (FR-013).
- RBAC: cualquier `Encargado_Tienda`, `Jefe_Finanzas`.
- 200: `{protocolo_id, texto, definido_por, fecha_creacion}`.

`PUT /api/caja/protocolo-escalamiento`
- Define una nueva versión del protocolo (FR-012).
- Body: `{texto}`.
- RBAC: `Jefe_Finanzas`.
- 201: nueva fila vigente.

`PATCH /api/caja/incidentes-fraude/{incidente_id}/aplicar-protocolo`
- Registra las acciones tomadas y transiciona el incidente a `en_revision` (FR-014).
- Body: `{acciones_tomadas}`.
- RBAC: `Encargado_Tienda`.
- 200: incidente actualizado, `estado='en_revision'`, `actualizado_por`/`fecha_actualizacion` completados. 409 si el incidente no está `abierto`.

`PATCH /api/caja/incidentes-fraude/{incidente_id}/cerrar`
- Cierra el incidente con su resultado (FR-015).
- Body: `{resultado: 'fraude_confirmado' | 'descartado'}`.
- RBAC: `Jefe_Finanzas`.
- 200: incidente actualizado, `estado='cerrado'`. 409 si el incidente no está `en_revision`. Funciona igual si el empleado del incidente ya tiene `fecha_baja` (FR-016).

## Umbral de merma y seguimiento semanal (FR-017 a FR-019)

`GET /api/caja/umbral-merma`
- Lista los umbrales de merma vigentes por categoría.
- RBAC: `Jefe_Operaciones`, `Encargado_Tienda` (solo lectura).
- 200: `[{product_category, porcentaje_umbral, definido_por, fecha_actualizacion}]`.

`PUT /api/caja/umbral-merma/{product_category}`
- Define o actualiza el umbral aceptable de una categoría (FR-017).
- Body: `{porcentaje_umbral}`.
- RBAC: `Jefe_Operaciones`.
- 200: umbral actualizado (upsert).

`GET /api/caja/tiendas/{tienda_id}/seguimiento-merma-semanal?semana=&anio=`
- Porcentaje de merma acumulada de la tienda por categoría frente al umbral definido, para la semana ISO indicada (research.md Decisión 9) — FR-018, FR-019.
- `semana`: número de semana ISO (obligatorio). `anio`: opcional, año ISO — por defecto el año ISO vigente, para desambiguar la semana en un cruce de año.
- RBAC: `Encargado_Tienda`.
- 200: `[{product_category, porcentaje_merma_acumulado, porcentaje_umbral, supera_umbral: boolean}]` — `supera_umbral=true` es solo informativo, nunca bloquea ninguna otra operación (FR-019).
