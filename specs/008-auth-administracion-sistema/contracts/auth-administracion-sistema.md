# Contratos: Autenticación y Administración del Sistema

**Backend**: `backend/src/modules/sistema/router.py` (login, cuentas, RBAC, recuperación, auditoría) y `backend/src/modules/rrhh/router.py` (empleados) — ambos módulos nuevos. RBAC: módulo `Sistema` para `Jefe_TI`, módulo `RRHH` para `Jefe_RRHH` (primer uso de ambos, ver data-model.md). `POST /api/auth/login` y `POST /api/auth/recuperar-password` son los únicos endpoints sin autenticación previa de todo el sistema.

## Autenticación (FR-001 a FR-004)

`POST /api/auth/login`
- Body: `{username, password}`.
- RBAC: ninguno (endpoint público).
- 200: `{access_token, usuario_id, expira_en}` (JWT con solo `usuario_id`, research.md Decisión 1); actualiza `ultimo_login` (FR-004).
- 401: credenciales incorrectas o cuenta inactiva — mismo mensaje genérico en ambos casos (FR-002, FR-003, Edge Case). Registra un `intentos_login` en cada intento, exitoso o no.

`PATCH /api/auth/mi-password`
- Cambia la propia contraseña de la cuenta autenticada (FR-011).
- Body: `{password_actual, password_nueva}`.
- RBAC: cualquier cuenta autenticada, sobre su propio `usuario_id` (research.md Decisión 5, sin gate de tabla).
- 200: contraseña actualizada. 401 si `password_actual` no coincide.

## Empleados (FR-005, FR-006, FR-014)

`POST /api/rrhh/empleados`
- Registra un empleado nuevo (FR-005).
- Body: `{nombre, puesto_id, tienda_id?, email?, telefono?, fecha_contratacion}`.
- RBAC: `Jefe_RRHH`.
- 201: empleado creado.

`PATCH /api/rrhh/empleados/{empleado_id}`
- Actualiza datos/puesto de un empleado existente (FR-006).
- RBAC: `Jefe_RRHH`.
- 200: empleado actualizado.

`PATCH /api/rrhh/empleados/{empleado_id}/baja`
- Da de baja a un empleado; el trigger de PostgreSQL inhabilita automáticamente su cuenta asociada (FR-014).
- Body: `{fecha_baja}`.
- RBAC: `Jefe_RRHH`.
- 200: empleado dado de baja. La cuenta asociada queda `activo=false` sin llamada adicional (verificable en `GET sistema/usuarios/{id}`).

## Cuentas de usuario (FR-007, FR-008, FR-012)

`POST /api/sistema/usuarios`
- Crea la cuenta de un empleado ya registrado, con rol inicial (FR-007).
- Body: `{empleado_id, username, password_inicial, role_id}`.
- RBAC: `Jefe_TI`.
- 201: cuenta creada. 409 si el empleado ya tiene una cuenta (FR-008, Edge Case — la unicidad de `empleado_id` ya lo garantiza a nivel de esquema).

`PATCH /api/sistema/usuarios/{usuario_id}/rol`
- Asigna o revoca el rol de una cuenta existente, con efecto inmediato (FR-012).
- Body: `{role_id}`.
- RBAC: `Jefe_TI`.
- 200: cuenta actualizada — el nuevo rol aplica desde el siguiente request de esa cuenta, sin requerir nuevo login (research.md Decisión 1).

## Recuperación de contraseña (FR-009, FR-010)

`POST /api/auth/recuperar-password`
- Solicita un enlace de recuperación de un solo uso, enviado por correo (SendGrid) al email del empleado asociado (FR-009).
- Body: `{email}`.
- RBAC: ninguno (endpoint público).
- 200: siempre responde igual exista o no el email (mismo criterio anti-enumeración que el login).

`POST /api/auth/recuperar-password/confirmar`
- Define la nueva contraseña usando el token recibido por correo.
- Body: `{token, password_nueva}`.
- RBAC: ninguno (autenticado por el token, no por JWT).
- 200: contraseña actualizada, token marcado `usado=true`. 410 si el token ya fue usado o venció (FR-010, Edge Case).

## Administración de RBAC (FR-013)

`GET /api/sistema/roles/{role_id}/permisos-modulo`
- Lista los módulos accesibles por un rol.
- RBAC: `Jefe_TI`.
- 200: `[{modulo_id, nombre, puede_ver, puede_editar}]`.

`PUT /api/sistema/roles/{role_id}/permisos-modulo/{modulo_id}`
- Otorga o retira acceso de un rol a un módulo.
- Body: `{puede_ver, puede_editar}`.
- RBAC: `Jefe_TI`.
- 200: permiso actualizado (upsert).

`GET /api/sistema/roles/{role_id}/permisos-tabla?modulo_id=`
- Lista los permisos de tabla de un rol dentro de un módulo.
- RBAC: `Jefe_TI`.
- 200: `[{nombre_tabla, can_select, can_insert, can_update, can_delete}]`.

`PUT /api/sistema/roles/{role_id}/permisos-tabla/{modulo_id}/{nombre_tabla}`
- Otorga o retira permiso de un rol sobre una tabla específica de un módulo.
- Body: `{can_select, can_insert, can_update, can_delete}`.
- RBAC: `Jefe_TI`.
- 200: permiso actualizado (upsert). 409 si el rol no tiene acceso al módulo indicado (Edge Case — ya garantizado por la FK compuesta del esquema).

## Auditoría (FR-016)

`GET /api/sistema/auditoria/reporte-mensual?mes=&anio=`
- Reporte de accesos del mes, agrupado por usuario: logins exitosos, intentos fallidos, acciones registradas en `auditoria_log` (FR-016).
- RBAC: `Jefe_TI`.
- 200: `[{usuario_id, username, logins_exitosos, intentos_fallidos, acciones_registradas, ultimo_login}]`.
