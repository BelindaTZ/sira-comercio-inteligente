# Contratos: Pagos y Seguridad

**Backend**: `backend/src/modules/finanzas/router.py` (extendido, 006) y `backend/src/modules/ventas/router.py` (extendido, 001). RBAC: módulo `Finanzas` para disponibilidad de datáfonos/incidentes de seguridad de pago/política (acceso ya concedido a `Jefe_TI` desde 006, Decisión 10); módulo `Ventas` para medios de pago (nuevo acceso concedido a `Jefe_TI`) y reportes de tiempo de cobro (nuevo acceso concedido de solo lectura a `Jefe_Comercial`, mismo patrón que `Jefe_Marketing` en 005). El endpoint de inicio de cobro consulta de solo lectura `modules/finanzas/` (`datafonos.estado`) — research.md Decisión 8.

## Disponibilidad diaria de datáfonos (FR-001 a FR-004)

`PATCH /api/caja/datafonos/{datafono_id}/fuera-servicio`
- Marca un datáfono como fuera de servicio (FR-001). Ruta real bajo `/api/caja/...` (nomenclatura de 006).
- Body: `{motivo}` — texto libre obligatorio (1-200 chars), constancia de por qué (feature 013).
- RBAC: `Encargado_Tienda`.
- 200: datáfono a `estado='fuera_servicio'`, `motivo_fuera_servicio` guardado. 409 si ya está `fuera_servicio`. 422 sin `motivo`.

`PATCH /api/caja/datafonos/{datafono_id}/restablecer`
- Restablece un datáfono, reevaluando su conformidad de seguridad antes de marcarlo operativo (FR-002, FR-003). Limpia `motivo_fuera_servicio`.
- RBAC: `Encargado_Tienda`.
- 200: `{datafono_id, estado: 'activo' | 'requiere_actualizacion'}` — nunca queda en `fuera_servicio`. 409 si no estaba `fuera_servicio`.

`GET /api/ventas/cajas/{caja_id}/datafono-disponible`
- Consulta rápida de solo lectura usada por el flujo de cobro antes de intentar procesar con tarjeta (FR-004).
- RBAC: `Cajero`.
- 200: `{disponible: boolean, estado}` — `disponible=false` cuando `estado` es `fuera_servicio` o `requiere_actualizacion`; el frontend usa esto solo para advertir, nunca para bloquear el cobro con otro medio de pago.

## Medios de pago (FR-005 a FR-007)

`GET /api/ventas/medios-pago?aprobado=`
- Catálogo de medios de pago, filtrable por aprobado/dado de baja.
- RBAC: `Jefe_TI`.
- 200: `[{medio_pago_id, nombre, aprobado, aprobado_por, fecha_aprobacion, fecha_baja}]`.

`POST /api/ventas/medios-pago`
- Da de alta un nuevo medio de pago aprobado (FR-005).
- Body: `{nombre}`.
- RBAC: `Jefe_TI`.
- 201: `{medio_pago_id, nombre, aprobado: true, aprobado_por, fecha_aprobacion}`.

`PATCH /api/ventas/medios-pago/{medio_pago_id}/baja`
- Da de baja un medio de pago existente, sin afectar ventas ya registradas (FR-006).
- RBAC: `Jefe_TI`.
- 200: `{medio_pago_id, aprobado: false, fecha_baja}`. 409 si ya está dado de baja.

`GET /api/ventas/medios-pago/disponibles`
- Medios de pago ofrecidos en el punto de venta — solo los aprobados y no dados de baja (FR-007).
- RBAC: `Cajero`.
- 200: `[{medio_pago_id, nombre}]`.

## Incidentes de seguridad de pago (FR-008 a FR-011)

`POST /api/finanzas/incidentes-seguridad-pago`
- Registra un incidente de seguridad de pago, con o sin datáfono asociado (FR-008, Edge Case).
- Body: `{datafono_id?, descripcion}`.
- RBAC: `Jefe_TI`.
- 201: `{incidente_seguridad_id, datafono_id, registrado_por, descripcion, estado: 'abierto', fecha_hora}`.

`GET /api/finanzas/incidentes-seguridad-pago?estado=`
- Lista incidentes de seguridad de pago, filtrable por estado.
- RBAC: `Jefe_TI`, `Jefe_Finanzas` (solo lectura).
- 200: `[{incidente_seguridad_id, datafono_id, descripcion, estado, fecha_hora}]`.

`PATCH /api/finanzas/incidentes-seguridad-pago/{incidente_seguridad_id}/transicionar`
- Avanza el incidente entre `abierto` → `en_investigacion` → `cerrado` (FR-009).
- Body: `{estado_nuevo: 'en_investigacion' | 'cerrado'}`.
- RBAC: `Jefe_TI`.
- 200: incidente actualizado, `actualizado_por`/`fecha_actualizacion` completados. 409 si la transición no es válida desde el estado actual.

`GET /api/finanzas/incidentes-seguridad-pago/conteo?desde=&hasta=`
- Número de incidentes de seguridad de pago de un periodo (FR-011).
- RBAC: `Jefe_Finanzas`.
- 200: `{total: integer, periodo: {desde, hasta}}`.

## Política de seguridad de pagos (FR-012 a FR-014)

`GET /api/finanzas/politica-seguridad-pagos`
- Texto vigente de la política (FR-013).
- RBAC: `Jefe_TI`, `Jefe_Finanzas`, `Encargado_Tienda`.
- 200: `{politica_id, texto, definido_por, fecha_creacion}`.

`PUT /api/finanzas/politica-seguridad-pagos`
- Define una nueva versión vigente (FR-012).
- Body: `{texto}`.
- RBAC: `Jefe_TI`.
- 201: nueva fila vigente; la versión anterior sigue consultable por su `politica_id` para incidentes ya abiertos (FR-014).

`GET /api/caja/politica-seguridad-pagos/historial`
- Todas las versiones de la política, más reciente primero (append-only, FR-014). Feature 013. Ruta real bajo `/api/caja/...`.
- RBAC: igual que la lectura del vigente.
- 200: `[{politica_id, texto, definido_por, fecha_creacion}]`.

`GET /api/finanzas/politica-seguridad-pagos/{politica_id}`
- Consulta una versión específica de la política (FR-014, saber cuál estaba vigente cuando se abrió un incidente).
- RBAC: `Jefe_TI`, `Jefe_Finanzas`.
- 200: `{politica_id, texto, definido_por, fecha_creacion}`.

## Tiempo de cobro (FR-015 a FR-018)

`POST /api/ventas` (extensión, 001)
- El flujo de creación de venta (001) recibe/registra `fecha_inicio_cobro` al iniciar el cobro, junto con `fecha_hora` al confirmarla (FR-015) — no aplica a ventas no registradas en vivo por esta feature.
- RBAC: `Cajero` (sin cambio de rol respecto a 001).

`GET /api/ventas/cajas/{caja_id}/tiempo-cobro-semanal?semana=`
- Tiempo promedio de cobro de una caja en una semana, excluyendo ventas anuladas y ventas sin `fecha_inicio_cobro` (FR-016, FR-018).
- RBAC: `Encargado_Tienda`.
- 200: `{caja_id, semana, duracion_promedio_segundos, cantidad_ventas_consideradas}`.

`GET /api/ventas/tiendas/tiempo-cobro-mensual?mes=&anio=`
- Tiempo promedio de cobro por tienda a nivel de toda la red, para un mes (FR-017).
- RBAC: `Jefe_Comercial`.
- 200: `[{tienda_id, duracion_promedio_segundos, cantidad_ventas_consideradas}]`.
