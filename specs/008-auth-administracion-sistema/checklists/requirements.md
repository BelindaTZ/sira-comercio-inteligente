# Specification Quality Checklist: Autenticación y Administración del Sistema

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validación ejecutada releyendo `constitution.md` completa (12 principios) y `domain-context.md` §8/§9 (línea textual de alcance de 008, y la reserva de SendGrid para recuperación de contraseña) antes de redactar.
- **Boundary con 001-007 verificado**: las 7 features ya cerradas usan un token de prueba mientras 008 no esté implementada (dependencia declarada explícitamente en el `plan.md` de cada una, Principio IV) — esta feature es la que hace real ese mecanismo, sin reconstruir ningún flujo de negocio de las features anteriores.
- **Empleado (OO-B.9 a B.11) incorporado a esta feature**: verificado por grep que ninguna feature 001-007 registra un empleado nuevo como acción propia (todas lo referencian ya existente vía `empleado_id`) — se incorpora aquí porque una cuenta de usuario (OO-B.18) siempre depende de un empleado ya existente, y no hay ninguna feature de RRHH operativa en el roadmap.
- **Hallazgo importante para el usuario — OE-8 (RRHH) completo sin feature dueña**: OT-8.1 a OT-8.4 (retención, capacitación, clima laboral, plan de sucesión — 8 OO, 4 tablas ya reservadas: `capacitaciones`, `empleado_capacitacion`, `clima_laboral`, `plan_sucesion`) no encajan en esta feature ni en ninguna de las 10 del roadmap. Es un vacío mayor que los ya detectados (OT-2.4/OT-2.5, OT-4.2) porque es una OE entera, no un par de OT sueltos — documentado en `spec.md` Assumptions para que el usuario decida, sin tomar ninguna acción aquí.
- **Gap de BSC — OO-7.5.2 asignada, OO-7.5.1 dejada para 010**: de las dos OO de OT-7.5 (gobierno de datos), esta feature toma solo OO-7.5.2 (auditar accesos, ya citada como "auditoría" en el alcance de 008 de `domain-context.md`); OO-7.5.1 (política de calidad/trazabilidad de datos, más amplia, sobre el pipeline de datos completo) se deja explícitamente para evaluar al especificar 010-plataforma-datos-tactico-estrategico, donde encaja mejor.
- **Sin gap de rol RBAC**: Jefe_RRHH y Jefe_TI ya tienen rol propio sembrado.
- **Decisión de alcance — sin CRUD de roles nuevos**: los 10 roles ya sembrados son fijos; "administración de RBAC" se interpretó como asignar esos roles y ajustar sus permisos de módulo/tabla, no crear roles adicionales — no narrado en el enunciado ni pedido por el usuario, evita alcance no solicitado (Principio VIII).
- No se detectaron violaciones de principios de la constitución. El mecanismo exacto de invalidación de sesión (JWT corto vs. lista de revocación) se deja para `research.md`, consistente con que `spec.md` no debe fijar detalles de implementación.

## Ronda 1 (hallazgos de la implementación — T043 a T047)

`/speckit-analyze` post-implementación (T043). Ninguna inconsistencia CRÍTICA/ALTA. Decisiones tomadas al implementar (no se tocaron `plan.md`/`research.md`/`data-model.md`/`contracts/`):

1. **Módulo backend `finanzas` → `caja`, `/api/finanzas/` → `/api/caja/`** — igual que en 006/007, `tasks.md` T001 nombra el módulo de 006/007 como `finanzas`; el real es `modules/caja/`. La feature 008 extiende `security.py` y crea `modules/sistema/` y `modules/rrhh/`; los endpoints de auth viven en `/api/auth/...` y `/api/sistema/...`, `/api/rrhh/...` como dice el contrato.
2. **`empleado.py`/`usuario.py`/`role_permiso.py` creados como modelos nuevos** — `plan.md` los describe como "ya existentes como modelos referenciados por FK (001)", pero 001-007 sólo tenían las TABLAS (referenciadas por `empleado_id`/`role_id` en columnas `Integer`), no modelos SQLAlchemy. 008 los introduce.
3. **T045 — seed base de `role_permisos_modulo` ya estaba** — `tasks.md` T045 asume que sólo `Cajero`/`Jefe_Marketing`/`Gerente_General` tienen acceso de módulo sembrado; en realidad las rondas de 001-007 ya sembraron `Encargado_Tienda`→(Ventas, Operaciones, Comercial, Finanzas, Marketing_CRM), `Reponedor`→Operaciones, `Jefe_Operaciones`→(Operaciones, Comercial, Finanzas), `Jefe_Comercial`→(Comercial, Ventas), `Jefe_Finanzas`→Finanzas, `Jefe_TI`→(TI, Finanzas, Ventas). 008 sólo añade `Jefe_TI`→Sistema y `Jefe_RRHH`→RRHH. No se necesitó ningún seed adicional para que los ~340 tests migrados a JWT real pasen.
4. **`bcrypt` directo, no `passlib`** — `passlib` está sin mantenimiento activo y tiene incompatibilidades conocidas con `bcrypt` ≥ 4; se usa la librería `bcrypt` directamente (`src/shared/passwords.py`), agregada a `pyproject.toml`.
5. **Contraseña en `intentos_login` de un login fallido persiste vía `session.commit()` explícito en el router** — `get_session` hace rollback ante una excepción, así que el endpoint de login registra el intento y commitea ANTES de responder 401 (el service devuelve `{ok}` en vez de lanzar).
6. **`_ensure_jwt_secret()`** (T005) — genera `JWT_SECRET` en `backend/.env` si no existe; es un secreto propio del proyecto (como MinIO), no de un tercero. En entorno de solo lectura (CI) cae al default.

**T044** — los 5 escenarios de `quickstart.md` cubiertos por `tests/integration/test_us{1..5}_*.py`, en verde.
**T045** — conftest migrado: `_token()` ahora crea una cuenta `usuarios` real y emite un JWT que sólo transporta `usuario_id`; el backend resuelve rol/permisos contra la BD en cada request. Ningún test depende ya del token de prueba. 359 tests en verde (el único fallo, `test_us4_demanda_perdida`, es un defecto preexistente de 004 de ventana horaria UTC/local, ajeno a 008).
**T046** — cobertura de Principio X: rechazo de login sin distinguir causa (`test_auth_logica.py::test_login_rechazado_no_distingue_la_causa`), efecto inmediato del cambio de rol (`test_auth_logica.py::test_jwt_solo_transporta_usuario_id` + integración `test_us4_roles_permisos.py`), permiso de tabla sin módulo (`test_rbac_integridad.py`), trigger de inhabilitación y no-reactivación (`test_trigger_baja_cuenta.py`), token de recuperación vencido/usado (`test_auth_logica.py`).
