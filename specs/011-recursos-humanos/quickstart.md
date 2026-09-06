# Quickstart: Recursos Humanos

**Feature**: `011-recursos-humanos` | **Precondición**: backend levantado con las migraciones de esta feature aplicadas, empleados y cuentas ya registrados (008), token de prueba con el rol correspondiente (Principio IV, dependencia de 008).

## Escenario 1 — Marcar puesto crítico y registrar acción de retención (User Story 1, MVP)

1. Como `Jefe_RRHH`, `PATCH /api/rrhh/puestos/{puesto_id}/critico` con `{es_critico: true}` sobre un puesto con empleados activos.
2. `POST /api/rrhh/acciones-retencion` con `{empleado_id, fecha, descripcion}` para un empleado de ese puesto → verificar acción registrada.
3. `GET /api/rrhh/empleados/{empleado_id}/acciones-retencion` → verificar que la acción es consultable en cualquier momento.
4. Repetir el paso 2 para un empleado en un puesto NO marcado como crítico → verificar que el sistema lo permite igual (Edge Case).

## Escenario 2 — Capacitación con fan-out por rol y cumplimiento por tienda (User Story 2)

1. Como `Jefe_RRHH`, `POST /api/rrhh/capacitaciones` con `{nombre, role_ids: [role_id_cajero]}` → verificar `empleados_asignados` > 0 (fan-out hacia todos los empleados con cuenta activa en ese rol).
2. `PATCH /api/rrhh/empleado-capacitacion/{empleado_id}/{capacitacion_id}/completar` con `{fecha_completado}` para uno de esos empleados.
3. Como `Encargado_Tienda`, `GET /api/rrhh/tiendas/{tienda_id}/cumplimiento-capacitacion` → verificar que ve claramente quién completó y quién no, solo de su propia tienda.
4. Verificar que un empleado sin cuenta de usuario (008) en el rol objetivo NO aparece en el fan-out del paso 1.

## Escenario 3 — Clima laboral semestral cruzado con rotación (User Story 3)

1. Como `Jefe_RRHH`, `POST /api/rrhh/clima-laboral` con `{tienda_id, periodo: "2026-S2", resultado_promedio: 7.5}`.
2. Verificar (o sembrar) bajas de empleados de esa tienda con `fecha_baja` dentro de julio-diciembre 2026.
3. `GET /api/rrhh/tiendas/{tienda_id}/clima-rotacion?periodo=2026-S2` → verificar que la respuesta trae `resultado_promedio` junto con `tasa_rotacion_pct` calculada, sin cruzar los datos a mano.
4. Repetir el `GET` con un periodo sin ninguna encuesta registrada → verificar 404 (sin dato inventado, FR-010).

## Escenario 4 — Plan de sucesión y señalización de cobertura (User Story 4)

1. Usando el puesto marcado como crítico en el Escenario 1, `POST /api/rrhh/plan-sucesion` con `{puesto_id, empleado_candidato_id}`.
2. `GET /api/rrhh/plan-sucesion/cobertura` → verificar que ese puesto aparece con al menos un candidato y `sin_cobertura: false`.
3. Marcar un segundo puesto como crítico sin registrar ningún candidato.
4. Repetir el `GET` del paso 2 → verificar que ese segundo puesto aparece explícitamente con `sin_cobertura: true`.
