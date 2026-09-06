# Implementation Plan: Autenticación y Administración del Sistema

**Branch**: `008-auth-administracion-sistema` | **Date**: 2026-09-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-auth-administracion-sistema/spec.md`

## Summary

Login con usuario/contraseña que otorga una sesión JWT asociada al rol real de la cuenta, reemplazando el token de prueba del que dependían 001-007 (Principio IV pasa de promesa de esquema a mecanismo real). Alta de empleado (primera feature que puebla `empleados` como registro propio, no solo referenciado) y de su cuenta de usuario asociada (1:1, ya garantizado por `usuarios.empleado_id UNIQUE`). Recuperación de contraseña por enlace de un solo uso vía SendGrid. Administración de RBAC: asignación de rol a una cuenta y administración de permisos de módulo/tabla por rol, con efecto inmediato sin necesidad de volver a iniciar sesión. Baja de empleado con inhabilitación automática de su cuenta (trigger, no bypasseable por ningún módulo llamador) y reporte mensual de auditoría de accesos (éxitos, fallidos, acciones registradas).

## Technical Context

**Language/Version**: Backend: Python 3.11+ (sin dependencias de análisis nuevas). Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT (mismo stack de 001-007; primera feature que efectivamente emite y valida JWT — 001-007 solo lo declaraban como dependencia futura), `passlib`/`bcrypt` (hash de contraseña — librería estándar del ecosistema FastAPI, no una dependencia de análisis nueva). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios.

**Storage**: PostgreSQL 16 — puebla (sin extender su esquema) `empleados` y `usuarios`, ya reservadas desde 001 sin feature que las registrara como propias hasta ahora (solo referenciadas por FK). Puebla y expone CRUD sobre `role_permisos_modulo`/`role_permisos_tabla` (ya reservadas, hasta ahora solo consultadas para enforcement por 001-007, nunca administradas). Extiende `auditoria_log` (ya reservada, poblada transversalmente desde 001) solo para lectura agregada (sin cambio de esquema). Agrega 2 tablas nuevas: `recuperacion_password` (enlaces de un solo uso) e `intentos_login` (éxitos/fallos de inicio de sesión, forma de dato distinta de `auditoria_log` — sin antes/después de fila). No usa MinIO ni ClickHouse (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Por Principio X, cobertura obligatoria en: RBAC (login exitoso/fallido sin distinguir causa, cuenta dada de baja rechazada, cambio de rol con efecto inmediato sin nuevo login, permiso de tabla rechazado sin acceso previo al módulo — integridad ya garantizada por la FK compuesta), el trigger de inhabilitación automática de cuenta al dar de baja al empleado (y que no se revierte automáticamente al reactivar), y el enlace de recuperación de un solo uso. Frontend: `Vitest` + `@vue/test-utils`.

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001-007).

**Performance Goals**: El cambio de rol o de permiso de módulo/tabla aplica de inmediato porque el JWT solo transporta `usuario_id` (nunca el rol ni los permisos) — el backend resuelve rol y permisos vigentes contra PostgreSQL en cada request (research.md Decisión 1), sin necesidad de lista de revocación ni reinicio (SC-004). CRUD estándar <1s en desarrollo (Principio X).

**Constraints**: Sin lógica de negocio en el frontend (Principio V) — la validación de credenciales, el hash de contraseña y la resolución de permisos ocurren siempre en el backend. `POST /api/auth/login` y `POST /api/auth/recuperar-password` son los únicos dos endpoints de todo el sistema sin autenticación previa (por definición — no puede exigirse un JWT para obtenerlo); todos los demás endpoints de esta y de 001-007 exigen JWT válido desde que esta feature esté disponible. Ningún endpoint revela si un nombre de usuario existe (FR-002, Edge Case).

**Scale/Scope**: 5 historias de usuario (P1-P5), 16 requisitos funcionales. Primera feature que puebla `empleados`/`usuarios` como registro propio; agrega volumen propio solo en enlaces de recuperación e intentos de login.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR cita su OO de origen (OO-B.9 a B.11, OO-B.18 a B.20, y OO-7.5.2 asignada sin crear OO nueva — ver spec.md Assumptions). |
| II. Nivel Operativo = Registro Real | PASS | Alta de empleado y de cuenta son INSERT reales; el login valida contra `password_hash` real, nunca simulado; la baja de cuenta es un UPDATE real disparado por trigger, no un estado de UI. |
| III. Separación de Motores | PASS | Solo PostgreSQL + el propio proceso backend; ninguna agregación requiere ClickHouse/Airflow (010, en espera). |
| IV. RBAC de Dos Niveles | PASS — esta feature lo implementa | Esta es la feature que convierte el RBAC de dos niveles de esquema sembrado a mecanismo real: 001-007 dependían de un token de prueba, declarado explícitamente en cada uno de sus `plan.md`. Los únicos endpoints sin RBAC son login y recuperación de contraseña, por definición (no puede exigirse credencial para obtenerla). |
| V. Backend y Frontend Desacoplados | PASS | FastAPI REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Se releyó explícitamente el esquema de `usuarios`/`role_permisos_modulo`/`role_permisos_tabla`/`auditoria_log` (ya reservado desde 001) antes de diseñar; no se recrea ningún flujo de negocio de 001-007, solo se les da autenticación real. |
| VII. Anclaje al Dataset Real | PASS | No aplica dataset Dunnhumby a esta feature (es administración de sistema, no venta/inventario/cliente); los empleados y cuentas que se registren son datos reales de la operación del sistema, no sintetizados. |
| VIII. Simplicidad Justificada | PASS | El JWT transporta solo `usuario_id` (sin rol/permisos embebidos) para que el cambio de rol sea inmediato sin lista de revocación (research.md Decisión 1) — la alternativa (JWT con rol embebido + blacklist de revocación) es la opción más compleja, rechazada. La inhabilitación automática de cuenta usa un trigger de PostgreSQL en vez de lógica de aplicación duplicada en cada módulo que pueda dar de baja a un empleado (research.md Decisión 4) — justificado porque "automático" es un requisito literal del FR-014, no una preferencia de implementación. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver Testing arriba. Contraseñas siempre hasheadas (`passlib`/bcrypt), nunca en texto plano ni en logs. |
| XI. Convenciones de Código y Arquitectura | PASS | Capas router→service→repository; módulo backend nuevo `modules/sistema/` (auth, RBAC admin, auditoría) y `modules/rrhh/` (empleados) — ambos módulos RBAC ya sembrados desde 001 sin uso hasta ahora. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Pantalla de login fuera del layout de navegación estándar (no aplica barra superior); administración de roles/permisos y catálogo de empleados con el mismo `DataTable.vue`/`WorkPanel.vue` del resto del sistema. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-auth-administracion-sistema/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

**Criterio de organización**: el mismo ya fijado en 001-007 — por módulo de negocio. Esta feature introduce dos módulos backend nuevos, ambos ya reservados en el esquema RBAC desde 001 sin uso hasta ahora: `modules/sistema/` (login, cuentas de usuario, administración de RBAC, recuperación de contraseña, auditoría — módulo RBAC `Sistema`, "Auditoría, configuración RBAC") y `modules/rrhh/` (empleados — módulo RBAC `RRHH`, "Empleados, capacitación, clima laboral"; esta feature solo cubre el CRUD base de empleado, 011-recursos-humanos lo extiende con capacitación/clima/sucesión).

```text
backend/
├── src/
│   ├── models/                      # se agregan: recuperacion_password.py, intento_login.py; empleado.py y usuario.py ya existían como modelos referenciados por FK (001), ahora con su propio repositorio/servicio
│   ├── modules/
│   │   ├── sistema/                 # router.py, service.py, repository.py, schemas.py — login, cuentas de usuario, administración de RBAC (role_permisos_modulo/tabla), recuperación de contraseña, reporte de auditoría
│   │   └── rrhh/                    # router.py, service.py, repository.py, schemas.py — CRUD de empleado (alta, actualización, baja)
│   ├── core/
│   │   └── security.py              # emisión/validación de JWT (usuario_id únicamente, research.md Decisión 1), hash de contraseña
│   └── db/
│       └── triggers/                # se agrega: trigger de inhabilitación automática de cuenta al dar de baja empleado (research.md Decisión 4)
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # rechazo de credenciales sin distinguir causa, efecto inmediato de cambio de rol, integridad de permiso de tabla sin módulo, trigger de baja de cuenta, enlace de recuperación de un solo uso

frontend/
├── src/
│   ├── services/                    # se agregan: authApi.js, sistemaApi.js, rrhhApi.js
│   ├── modules/
│   │   ├── auth/                    # pages/LoginPage.vue, RecuperarPasswordPage.vue (fuera del layout de navegación estándar)
│   │   ├── sistema/                 # pages/UsuariosPage.vue, RolesPermisosPage.vue, AuditoriaPage.vue
│   │   └── rrhh/                    # pages/EmpleadosPage.vue
│   └── router/                      # guard de navegación que exige JWT válido para toda ruta fuera de /auth
└── tests/
    ├── unit/                        # guard de navegación, formulario de login
    └── component/                   # flujo de alta de empleado + cuenta, flujo de asignación de rol
```

**Structure Decision**: Se introducen `modules/sistema/` y `modules/rrhh/` (ambos módulos RBAC ya reservados desde 001, sin uso hasta ahora) como ubicación de esta feature. `modules/rrhh/` cubre en esta feature solo el CRUD base de empleado — su ampliación (capacitación, clima laboral, plan de sucesión) queda documentada como alcance de 011-recursos-humanos, no de esta feature.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
