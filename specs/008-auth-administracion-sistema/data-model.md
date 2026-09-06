# Data Model: Autenticación y Administración del Sistema

**Feature**: `008-auth-administracion-sistema` | **Date**: 2026-09-06

## Entidades ya reservadas, pobladas por esta feature (sin cambio de esquema)

### Empleado (`empleados`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| empleado_id | SERIAL PK | |
| tienda_id | INTEGER FK → tiendas, NULLABLE | |
| puesto_id | INTEGER NOT NULL FK → roles_puesto | Catálogo de puestos, ya existente (usado también por 011) |
| nombre | VARCHAR(150) NOT NULL | |
| email | VARCHAR(150) UNIQUE | Usado por recuperación de contraseña (FR-009) |
| telefono | VARCHAR(20) | |
| fecha_contratacion | DATE NOT NULL | |
| fecha_baja | DATE | NULL mientras esté activo |
| activo | BOOLEAN NOT NULL DEFAULT true | Al pasar a `false`, dispara el trigger de Decisión 4 (research.md) |

**Uso en esta feature**: FR-005 (alta), FR-006 (actualización), FR-014 (baja — dispara inhabilitación de cuenta).

### Cuenta de Usuario (`usuarios`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| usuario_id | SERIAL PK | |
| empleado_id | INTEGER UNIQUE NOT NULL FK → empleados | La unicidad ya garantiza 1 cuenta por empleado (FR-008, Edge Case) |
| role_id | INTEGER NOT NULL FK → roles | Asignable/revocable (FR-012) |
| username | VARCHAR(50) UNIQUE NOT NULL | |
| password_hash | VARCHAR(255) NOT NULL | bcrypt vía `passlib` |
| activo | BOOLEAN NOT NULL DEFAULT true | `false` bloquea el login (FR-003); inhabilitado automáticamente por el trigger de `empleados` (Decisión 4), nunca reactivado automáticamente (FR-015) |
| ultimo_login | TIMESTAMP, NULLABLE | Actualizado en cada login exitoso (FR-004) |

**Uso en esta feature**: FR-001 a FR-004 (login), FR-007/FR-008 (alta de cuenta), FR-011 (cambio de contraseña propia), FR-012 (asignación de rol).

### Permiso de Módulo (`role_permisos_modulo`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| role_id | INTEGER FK → roles | PK compuesta |
| modulo_id | INTEGER FK → modulos | PK compuesta |
| puede_ver | BOOLEAN NOT NULL DEFAULT false | |
| puede_editar | BOOLEAN NOT NULL DEFAULT false | |

### Permiso de Tabla (`role_permisos_tabla`, desde 001)

| Campo | Tipo | Notas |
|---|---|---|
| role_id, modulo_id | INTEGER, INTEGER | PK compuesta + FK compuesta a `role_permisos_modulo` (garantiza que no puede existir sin el permiso de módulo — FR-013 Acceptance Scenario 3, Edge Case) |
| nombre_tabla | VARCHAR(60) | PK compuesta |
| can_select / can_insert / can_update / can_delete | BOOLEAN NOT NULL DEFAULT false | |

**Uso en esta feature**: FR-013 — primera feature que expone CRUD sobre estas dos tablas; 001-007 solo las consultaban para enforcement (dependencia declarada "token de prueba" en sus `plan.md`).

### Registro de Auditoría (`auditoria_log`, desde 001 — solo lectura agregada en esta feature)

| Campo | Tipo | Notas |
|---|---|---|
| log_id | BIGSERIAL PK | |
| usuario_id | INTEGER FK → usuarios, NULLABLE | |
| nombre_tabla | VARCHAR(60) NOT NULL | |
| accion | VARCHAR(10) CHECK IN (`INSERT`,`UPDATE`,`DELETE`) | |
| registro_id | VARCHAR(60) NOT NULL | |
| valores_anteriores / valores_nuevos | JSONB | |
| fecha_hora | TIMESTAMP NOT NULL | |

**Uso en esta feature**: FR-016 — consultada de solo lectura para el conteo de "acciones registradas" del reporte mensual (junto con `intentos_login` para los eventos de login).

## Entidades nuevas

### Recuperación de Contraseña (`recuperacion_password`)

| Campo | Tipo | Validación |
|---|---|---|
| token_id | BIGSERIAL PK | |
| usuario_id | INTEGER NOT NULL FK → usuarios | |
| token | VARCHAR(128) UNIQUE NOT NULL | Generado aleatoriamente, enviado por SendGrid |
| fecha_creacion | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |
| fecha_expiracion | TIMESTAMP NOT NULL | Vigencia limitada (FR-009) |
| usado | BOOLEAN NOT NULL DEFAULT false | `true` tras usarse una vez (FR-010) |

Nunca se borra (Principio II, evidencia de intentos de recuperación) — research.md Decisión 2.

### Intento de Login (`intentos_login`)

| Campo | Tipo | Validación |
|---|---|---|
| intento_id | BIGSERIAL PK | |
| usuario_id | INTEGER FK → usuarios, NULLABLE | `NULL` cuando `username_intentado` no corresponde a ninguna cuenta |
| username_intentado | VARCHAR(50) NOT NULL | Se guarda el texto ingresado, exista o no la cuenta |
| exitoso | BOOLEAN NOT NULL | |
| fecha_hora | TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP | |

Distinta de `auditoria_log` (research.md Decisión 3). Índices: `idx_intentos_login_usuario_id`, `idx_intentos_login_fecha_hora`.

## Trigger nuevo (sin cambio de esquema de tabla, solo comportamiento)

`trg_inhabilitar_cuenta_baja_empleado` — `AFTER UPDATE ON empleados FOR EACH ROW WHEN (NEW.activo = false AND OLD.activo = true) EXECUTE FUNCTION fn_inhabilitar_cuenta_usuario()`, que ejecuta `UPDATE usuarios SET activo = false WHERE empleado_id = NEW.empleado_id`. Ver research.md Decisión 4 para la justificación de usar un trigger en vez de lógica solo en la capa de aplicación.

## Extensión RBAC (seed, no cambio de esquema)

Primer uso de los módulos `Sistema` y `RRHH` (ambos ya sembrados desde 001 sin ninguna feature que los usara):

- `Jefe_TI`: `role_permisos_modulo` (`Sistema`, puede_ver=true, puede_editar=true); `role_permisos_tabla` sobre `usuarios`, `role_permisos_modulo`, `role_permisos_tabla`, `recuperacion_password`, `intentos_login`, `auditoria_log` (SELECT en todas, INSERT/UPDATE donde aplica administración).
- `Jefe_RRHH`: `role_permisos_modulo` (`RRHH`, puede_ver=true, puede_editar=true); `role_permisos_tabla` sobre `empleados` (SELECT/INSERT/UPDATE).
- Todos los demás roles: sin permiso de tabla nuevo — `PATCH /api/auth/mi-password` es self-service, no gateado por RBAC de tabla (research.md Decisión 5).

## Trazabilidad Entidad → FR → OO

| Entidad | FR | OO |
|---|---|---|
| Cuenta de Usuario (login) | FR-001, FR-002, FR-003, FR-004 | — (mecanismo transversal, Principio IV) |
| Empleado | FR-005, FR-006, FR-014, FR-015 | OO-B.9, OO-B.10, OO-B.11 |
| Cuenta de Usuario (alta) | FR-007, FR-008 | OO-B.18 |
| Recuperación de Contraseña | FR-009, FR-010 | — (seguridad, sin OO propia) |
| Cuenta de Usuario (password propia) | FR-011 | OO-B.19 |
| Permiso de Módulo / Tabla | FR-012, FR-013 | OO-B.20 |
| Intento de Login + Registro de Auditoría | FR-016 | OO-7.5.2 |
