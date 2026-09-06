# Contratos: Recursos Humanos

**Backend**: `backend/src/modules/rrhh/router.py` (extendido, 008). RBAC: módulo `RRHH` para `Jefe_RRHH` (acceso ya concedido desde 008); nuevo acceso concedido de solo lectura a `Encargado_Tienda` (mismo patrón que `Jefe_Marketing`/`Jefe_Comercial` en 005/007). El fan-out de capacitación consulta de solo lectura `modules/sistema/` (`usuarios.role_id`, 008) — research.md Decisión 2.

## Puestos críticos y retención (FR-001, FR-002)

`PATCH /api/rrhh/puestos/{puesto_id}/critico`
- Marca o desmarca un puesto como crítico (FR-001).
- Body: `{es_critico: boolean}`.
- RBAC: `Jefe_RRHH`.
- 200: puesto actualizado.

`POST /api/rrhh/acciones-retencion`
- Registra una acción de retención para un empleado (FR-002).
- Body: `{empleado_id, fecha, descripcion}`.
- RBAC: `Jefe_RRHH`.
- 201: acción registrada.

`GET /api/rrhh/empleados/{empleado_id}/acciones-retencion`
- Lista las acciones de retención de un empleado.
- RBAC: `Jefe_RRHH`.
- 200: `[{accion_id, fecha, descripcion}]`.

## Capacitación (FR-003 a FR-005)

`POST /api/rrhh/capacitaciones`
- Programa una capacitación dirigida a uno o más roles del sistema (FR-003); dispara el fan-out hacia `empleado_capacitacion` para todos los empleados con cuenta activa en esos roles (FR-004).
- Body: `{nombre, descripcion?, role_ids: [int]}`.
- RBAC: `Jefe_RRHH`.
- 201: `{capacitacion_id, nombre, descripcion, empleados_asignados: integer}`.

`PATCH /api/rrhh/empleado-capacitacion/{empleado_id}/{capacitacion_id}/completar`
- Registra la fecha de finalización de una capacitación para un empleado.
- Body: `{fecha_completado}`.
- RBAC: `Jefe_RRHH`, `Encargado_Tienda` (solo empleados de su tienda).
- 200: registro actualizado.

`GET /api/rrhh/tiendas/{tienda_id}/cumplimiento-capacitacion`
- Cumplimiento de capacitación del personal de una tienda (FR-005).
- RBAC: `Encargado_Tienda` (solo su propia tienda).
- 200: `[{empleado_id, nombre, capacitacion_id, nombre_capacitacion, fecha_completado}]` — `fecha_completado: null` = pendiente.

## Clima laboral y rotación (FR-006, FR-007, FR-010)

`POST /api/rrhh/clima-laboral`
- Registra el resultado promedio de la encuesta de clima por tienda y periodo (FR-006).
- Body: `{tienda_id, periodo, resultado_promedio}`.
- RBAC: `Jefe_RRHH`.
- 201: `{encuesta_id, tienda_id, periodo, resultado_promedio, fecha}`.

`GET /api/rrhh/tiendas/{tienda_id}/clima-rotacion?periodo=`
- Resultado de clima laboral de una tienda/periodo junto con la tasa de rotación del mismo periodo (FR-007, research.md Decisión 3).
- RBAC: `Jefe_RRHH`.
- 200: `{encuesta_id, resultado_promedio, tasa_rotacion_pct}` o 404 si no hay encuesta registrada para ese periodo (FR-010, sin dato inventado).

## Plan de sucesión (FR-008, FR-009)

`POST /api/rrhh/plan-sucesion`
- Registra un candidato interno para un puesto crítico (FR-008).
- Body: `{puesto_id, empleado_candidato_id}`.
- RBAC: `Jefe_RRHH`.
- 201: `{sucesion_id, puesto_id, empleado_candidato_id, fecha}`.

`GET /api/rrhh/plan-sucesion/cobertura`
- Lista todos los puestos críticos junto con sus candidatos registrados; señala explícitamente los que no tienen ninguno (FR-009).
- RBAC: `Jefe_RRHH`.
- 200: `[{puesto_id, nombre, candidatos: [{empleado_candidato_id, nombre, fecha}], sin_cobertura: boolean}]`.
