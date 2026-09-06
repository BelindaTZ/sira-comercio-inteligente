# Research: Autenticación y Administración del Sistema

**Feature**: `008-auth-administracion-sistema` | **Date**: 2026-09-06

## Decisión 1: JWT transporta solo `usuario_id` — permisos resueltos contra PostgreSQL en cada request

**Decisión**: El JWT emitido al iniciar sesión contiene únicamente `usuario_id` (y su expiración) — nunca el `role_id` ni los permisos de módulo/tabla. En cada request autenticado, el backend resuelve el rol vigente y sus permisos consultando `usuarios`/`role_permisos_modulo`/`role_permisos_tabla` directamente. No existe lista de revocación de tokens.

**Razón**: FR-012 (Acceptance Scenario 1) exige explícitamente que un cambio de rol tenga "efecto inmediato... sin requerir que vuelva a iniciar sesión". Un JWT con el rol embebido solo se actualizaría en el próximo login, violando ese requisito salvo que se agregue una lista de revocación (infraestructura adicional, ej. Redis) — un JWT mínimo que solo identifica a la cuenta y una resolución de permisos en caliente contra la misma base de datos que ya gobierna el RBAC (Principio IV) resuelve el requisito sin infraestructura nueva (Principio VIII). El mismo mecanismo resuelve gratis la baja de cuenta (FR-003): si `usuarios.activo=false`, el request se rechaza en el momento, sin esperar la expiración del token.

**Alternativas consideradas**: JWT con rol/permisos embebidos + lista de revocación en Redis — rechazada por agregar un motor de datos nuevo (violaría Principio III/VIII) solo para resolver un problema que la resolución en caliente ya resuelve sin dependencias nuevas.

## Decisión 2: `recuperacion_password` como tabla nueva de enlaces de un solo uso

**Decisión**: Tabla nueva `recuperacion_password` (`token_id`, `usuario_id` FK, `token` único, `fecha_creacion`, `fecha_expiracion`, `usado` BOOLEAN DEFAULT false). Al solicitar recuperación se inserta una fila; al usarse, se marca `usado=true` (nunca se borra, para conservar el intento como evidencia).

**Razón**: Ninguna tabla existente modela un enlace de recuperación de contraseña. Un registro append-mostly (se inserta al solicitar, se actualiza una sola vez al usarse) es la forma más simple que soporta FR-009/FR-010 (un solo uso, vigencia limitada) sin necesitar borrar filas (Principio II, registro real).

**Alternativas consideradas**: Guardar el token directamente en `usuarios` (una sola columna `token_recuperacion`/`token_expiracion`) — rechazada porque no deja evidencia de intentos de recuperación ya usados o vencidos, y porque una segunda solicitud de recuperación sobrescribiría silenciosamente la anterior sin dejar rastro.

## Decisión 3: `intentos_login` como tabla nueva, distinta de `auditoria_log`

**Decisión**: Tabla nueva `intentos_login` (`intento_id`, `usuario_id` FK **nullable**, `username_intentado` VARCHAR, `exitoso` BOOLEAN, `fecha_hora`). Se inserta una fila en cada intento de login, exitoso o no; `usuario_id` queda `NULL` cuando el `username_intentado` no corresponde a ninguna cuenta (para no tener que resolver una cuenta inexistente a un FK).

**Razón**: `auditoria_log` (001) modela cambios de fila con `valores_anteriores`/`valores_nuevos` (JSONB) — un intento de login no tiene "antes/después" de ningún registro, forzarlo en `auditoria_log` violaría la forma de esa tabla (su `accion CHECK` ni siquiera admite un valor de login) y mezclaría dos conceptos de auditoría distintos en una sola tabla, igual que 007 (Decisión 4) evitó mezclar el incidente de seguridad de pago con el de fraude. FR-016 exige que el reporte mensual incluya "intentos fallidos" — información que no puede reconstruirse desde `auditoria_log` porque un intento fallido nunca modifica ninguna fila.

**Alternativas consideradas**: Agregar `'LOGIN_EXITOSO'`/`'LOGIN_FALLIDO'` al `CHECK` de `auditoria_log.accion` — rechazada porque `nombre_tabla`/`registro_id`/`valores_anteriores`/`valores_nuevos` no tienen un valor natural para un intento de login (forzaría columnas vacías o valores sintéticos), y porque el propio nombre de la tabla (`auditoria_log`, alineado 1:1 con cambios de fila) dejaría de reflejar su contenido real.

## Decisión 4: Inhabilitación automática de cuenta al dar de baja al empleado — trigger de PostgreSQL

**Decisión**: Un trigger `AFTER UPDATE ON empleados` que, cuando `NEW.activo=false AND OLD.activo=true` (transición a inactivo), ejecuta `UPDATE usuarios SET activo=false WHERE empleado_id = NEW.empleado_id`. El trigger nunca actúa en la dirección inversa (reactivar un empleado no reactiva su cuenta) — satisface FR-015 por construcción, sin lógica adicional.

**Razón**: FR-014 exige que la inhabilitación sea automática — con lógica solo en la capa de aplicación (`RRHHService.dar_baja_empleado()`), cualquier otro punto de entrada futuro que actualice `empleados.activo` (un script de mantenimiter, una carga masiva, otro módulo) podría olvidar la cascada, dejando una cuenta activa de un empleado dado de baja — un riesgo de seguridad real dado el enunciado del proyecto ("clonación de tarjetas", "demandas"). Un trigger a nivel de base de datos es la única garantía de que la regla se cumple sin importar quién actualice la fila, y es la solución más simple que cumple el requisito literal (Principio VIII no prohíbe un trigger cuando la alternativa —duplicar la cascada en cada posible llamador— es más compleja y más frágil).

**Alternativas consideradas**: Cascada solo en `RRHHService` (capa de aplicación) — rechazada porque no es verdaderamente "automática" si depende de que cada futuro llamador la implemente correctamente; un trigger es DRY por diseño (Principio VIII) frente a duplicar la regla en cada posible punto de entrada.

## Decisión 5: Self-service de contraseña propia — sin gate de RBAC de tabla

**Decisión**: `PATCH /api/auth/mi-password` (cambiar la propia contraseña, FR-011) no se gatea contra `role_permisos_tabla` sobre `usuarios` — cualquier cuenta autenticada puede ejecutar esta acción sobre su propia fila (`usuario_id` tomado del JWT, nunca del body), independientemente de su rol.

**Razón**: El RBAC de dos niveles (Principio IV) gobierna el acceso a datos de negocio por rol — la gestión de la credencial propia de una cuenta es una acción de autoservicio universal (todo rol la necesita) que no tiene sentido modelar como un permiso de tabla adicional por cada uno de los 10 roles.

**Alternativas consideradas**: Exigir permiso `can_update` sobre `usuarios` para este endpoint — rechazada porque obligaría a sembrar ese permiso para los 10 roles solo para que cada cuenta pueda cambiar su propia contraseña, una acción que no es "administrar la tabla `usuarios`" sino "gestionar mi propia cuenta".

## Decisión 6: Resumen de cambios de BSC y RBAC

- **OO-7.5.2 asignada, sin OO nueva**: bajo OT-7.5 ya existente — ver `spec.md` Assumptions para el detalle completo (incluyendo por qué OO-7.5.1 queda para 010).
- **Hallazgo de OE-8 (RRHH) resuelto por 011-recursos-humanos**: ver `spec.md` Assumptions, actualizado tras la creación de esa feature.
- **Sin gap de rol RBAC**: los actores de esta feature (`Jefe_RRHH`, `Jefe_TI`) ya tienen rol propio sembrado.
- **Primer uso de dos módulos RBAC ya sembrados desde 001**: `Sistema` ("Auditoría, configuración RBAC") y `RRHH` ("Empleados, capacitación, clima laboral") — ninguna feature anterior los había usado; esta es la primera, `role_permisos_modulo`/`role_permisos_tabla` se seedán para `Jefe_TI`→`Sistema` y `Jefe_RRHH`→`RRHH` en esta feature.
- **Login y recuperación de contraseña son los únicos endpoints sin RBAC de todo el sistema**, por definición — documentado explícitamente en `plan.md` para que no se interprete como una omisión de Principio IV.
