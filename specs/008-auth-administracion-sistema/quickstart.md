# Quickstart: Autenticación y Administración del Sistema

**Feature**: `008-auth-administracion-sistema` | **Precondición**: backend levantado con las migraciones de esta feature aplicadas, dataset ya sembrado (001-007) — a partir de esta feature, todos los escenarios de 001-007 deben repetirse usando un JWT real en vez del token de prueba.

## Escenario 1 — Login exitoso, credenciales incorrectas y cuenta dada de baja (User Story 1, MVP)

1. `POST /api/auth/login` con credenciales válidas de una cuenta activa → verificar `access_token` recibido y `ultimo_login` actualizado.
2. `POST /api/auth/login` con la contraseña incorrecta → verificar 401 con el mismo mensaje genérico que si el usuario no existiera.
3. `POST /api/auth/login` con un `username` que no existe → verificar el mismo 401 genérico del paso 2 (no debe distinguirse).
4. Dar de baja la cuenta usada en el paso 1 (Escenario 3) y repetir `POST /api/auth/login` con la contraseña correcta → verificar 401 (cuenta inactiva).
5. Verificar que cada intento de los pasos 1-4 quedó registrado en `intentos_login`.

## Escenario 2 — Alta de empleado y cuenta de usuario asociada, con rechazo de cuenta duplicada (User Story 2)

1. Como `Jefe_RRHH`, `POST /api/rrhh/empleados` con los datos de un empleado nuevo → verificar el empleado creado.
2. Como `Jefe_TI`, `POST /api/sistema/usuarios` con `{empleado_id, username, password_inicial, role_id}` → verificar la cuenta creada.
3. `POST /api/auth/login` con esas credenciales → verificar login exitoso con el rol asignado.
4. Repetir `POST /api/sistema/usuarios` para el mismo `empleado_id` → verificar 409 (Edge Case, una cuenta por empleado).

## Escenario 3 — Recuperación de contraseña de un solo uso (User Story 3)

1. `POST /api/auth/recuperar-password` con el email de un empleado con cuenta → verificar respuesta genérica (200 exista o no el email) y un enlace enviado (simulado vía SendGrid en entorno de prueba).
2. `POST /api/auth/recuperar-password/confirmar` con el token recibido y una nueva contraseña → verificar 200 y que el login con la nueva contraseña funciona.
3. Repetir el paso 2 con el mismo token → verificar 410 (ya usado).
4. Como usuario autenticado, `PATCH /api/auth/mi-password` con la contraseña actual y una nueva → verificar 200 y que el login exige la nueva contraseña en el siguiente intento.

## Escenario 4 — Asignación de rol y administración de permisos (User Story 4)

1. Como `Jefe_TI`, `PATCH /api/sistema/usuarios/{usuario_id}/rol` con un `role_id` distinto sobre una cuenta ya logueada → verificar que el próximo request de esa cuenta ya refleja el acceso del nuevo rol, sin nuevo login.
2. `PUT /api/sistema/roles/{role_id}/permisos-modulo/{modulo_id}` con `{puede_ver: true, puede_editar: true}` → verificar el acceso otorgado.
3. `PUT /api/sistema/roles/{role_id}/permisos-tabla/{modulo_id}/{nombre_tabla}` con permisos específicos → verificar que aplica a todas las cuentas de ese rol.
4. Repetir el paso 3 con un `modulo_id` al que el rol NO tiene acceso (paso 2 no ejecutado para ese módulo) → verificar 409 (Edge Case).

## Escenario 5 — Baja de cuenta con inhabilitación automática y reporte mensual de auditoría (User Story 5)

1. Dar de baja al empleado del Escenario 2 (`PATCH /api/rrhh/empleados/{empleado_id}/baja`) → verificar, sin ninguna llamada adicional, que `GET sistema/usuarios/{usuario_id}` muestra `activo=false`.
2. Intentar `POST /api/auth/login` con esa cuenta → verificar 401.
3. Reactivar al empleado (Edge Case) → verificar que la cuenta sigue `activo=false` hasta que `Jefe_TI` la reactive explícitamente.
4. Como `Jefe_TI`, `GET /api/sistema/auditoria/reporte-mensual?mes=&anio=` sobre el mes de los escenarios anteriores → verificar que el reporte agrupado por usuario incluye logins exitosos, intentos fallidos y acciones registradas, sin consolidar manualmente ninguna fuente.
