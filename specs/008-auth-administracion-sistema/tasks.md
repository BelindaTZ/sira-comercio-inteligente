# Tasks: Autenticación y Administración del Sistema

**Input**: Design documents from `/specs/008-auth-administracion-sistema/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/auth-administracion-sistema.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: el rechazo de credenciales incorrectas sin distinguir causa (username inexistente vs. contraseña incorrecta), el rechazo de login de una cuenta inactiva, el efecto inmediato de un cambio de rol/permiso sin nuevo login, el rechazo de un permiso de tabla sin acceso previo al módulo, el trigger de inhabilitación automática de cuenta al dar de baja al empleado (y que no se revierte al reactivar), y el rechazo de un enlace de recuperación ya usado o vencido — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: Esta feature introduce dos módulos backend nuevos: `modules/sistema/` (login, cuentas, RBAC, recuperación, auditoría) y `modules/rrhh/` (empleados). A partir de esta feature, todos los endpoints de 001-007 exigen JWT real — su token de prueba queda reemplazado.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US5), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- **T001** Crear el esqueleto de `backend/src/modules/sistema/` y `backend/src/modules/rrhh/` (`router.py`, `service.py`, `repository.py`, `schemas.py` cada uno), calcado de la estructura de capas ya usada en `caja/` (006) y `finanzas/`/`ventas/` (007).
- **T002** [P] Migración Alembic: crear `recuperacion_password` e `intentos_login` (`data-model.md` completo).
- **T003** [P] Migración Alembic: crear el trigger `trg_inhabilitar_cuenta_baja_empleado` + función `fn_inhabilitar_cuenta_usuario()` (`data-model.md`, research.md Decisión 4).
- **T004** [P] Seed de `role_permisos_modulo`/`role_permisos_tabla`: `Jefe_TI`→`Sistema` (todas las tablas de esta feature), `Jefe_RRHH`→`RRHH` (`empleados`) — primer uso de ambos módulos (`data-model.md`, Extensión RBAC).
- **T005** [P] `backend/src/core/security.py`: utilidades de hash de contraseña (`passlib`/bcrypt) y emisión/validación de JWT (solo `usuario_id`, research.md Decisión 1). Incluye generar automáticamente `JWT_SECRET` en `backend/.env` si no existe todavía (parte del setup del entorno de desarrollo) — nunca se le pide al desarrollador que invente o busque este valor a mano; es un secreto propio del proyecto (como las credenciales de MinIO), no una credencial de un tercero como Stripe/SendGrid.
- **T006** [P] Frontend: crear páginas vacías `frontend/src/modules/auth/pages/LoginPage.vue`, `RecuperarPasswordPage.vue`, `frontend/src/modules/sistema/pages/UsuariosPage.vue`, `RolesPermisosPage.vue`, `AuditoriaPage.vue`, `frontend/src/modules/rrhh/pages/EmpleadosPage.vue`.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- **T007** [P] Modelos SQLAlchemy: `RecuperacionPassword`, `IntentoLogin` en `models/`; exponer `Empleado`/`Usuario`/`RolePermisoModulo`/`RolePermisoTabla` (ya existentes como modelos de 001) a través de repositorios propios de esta feature.
- **T008** Middleware/dependencia FastAPI de autenticación: valida JWT, resuelve `usuario_id` → cuenta/rol/permisos vigentes en cada request (depende de T005) — reemplaza el token de prueba de 001-007 en todos los routers existentes.
- **T009** Montar `sistema.router` y `rrhh.router` en `main.py`; aplicar el middleware de T008 a todos los routers de 001-007.

**Checkpoint**: Migraciones y trigger aplicados, modelos disponibles, autenticación real montada — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Inicio de sesión autenticado (Priority: P1) 🎯 MVP

**Goal**: Cualquier usuario inicia sesión y obtiene una sesión real asociada a su rol, reemplazando el token de prueba de 001-007.

**Independent Test**: iniciar sesión con credenciales válidas y verificar que la sesión resultante permite exactamente los mismos accesos que el token de prueba usado hasta ahora; credenciales inválidas son rechazadas sin distinguir causa.

### Tests para User Story 1 ⚠️

- **T010** [P] [US1] Unit test: rechazo de login sin distinguir username inexistente de contraseña incorrecta (FR-002, Edge Case).
- **T011** [P] [US1] Unit test: rechazo de login de una cuenta con `activo=false` (FR-003).
- **T012** [US1] Contract test: `POST auth/login`.
- **T013** [US1] Integration test: login exitoso → `ultimo_login` actualizado → `intentos_login` registra el intento (Escenario 1 de `quickstart.md`).

### Implementación de User Story 1

- **T014** [US1] `SistemaRepository`: consulta de `usuarios` por `username`, verificación de `password_hash` (bcrypt).
- **T015** [US1] `SistemaService.login()`: orquesta T014 + T010/T011, actualiza `ultimo_login`, registra `intentos_login` (depende de T007).
- **T016** [US1] Endpoint: `POST auth/login` — `contracts/auth-administracion-sistema.md`.
- **T017** [US1] `frontend/.../LoginPage.vue` y guard de navegación que exige JWT válido para toda ruta fuera de `/auth`.

**Checkpoint**: MVP — cualquier usuario puede iniciar sesión y su rol real gobierna su acceso, sin depender de un token de prueba (SC-001).

---

## Phase 4: User Story 2 - Alta de empleado y cuenta de usuario asociada (Priority: P2)

**Goal**: El Jefe de RRHH registra un empleado nuevo; el Jefe de TI crea su cuenta de usuario con un rol inicial.

**Independent Test**: registrar un empleado nuevo, crear su cuenta de usuario con un rol, y verificar que puede iniciar sesión con ese rol.

### Tests para User Story 2 ⚠️

- **T018** [P] [US2] Unit test: rechazo de una segunda cuenta para un empleado que ya tiene una (FR-008, Edge Case).
- **T019** [US2] Integration test: alta de empleado → alta de cuenta → login exitoso con el rol asignado (Escenario 2 de `quickstart.md`).

### Implementación de User Story 2

- **T020** [US2] `RRHHRepository`/`RRHHService`: CRUD base de `empleados` (alta, actualización).
- **T021** [US2] `SistemaRepository`/`SistemaService.crear_cuenta_usuario()`: INSERT de `usuarios`, hash de `password_inicial` (depende de T018).
- **T022** [US2] Endpoints: `POST rrhh/empleados`, `PATCH rrhh/empleados/{id}`, `POST sistema/usuarios` — `contracts/auth-administracion-sistema.md`.
- **T023** [US2] `frontend/.../EmpleadosPage.vue` y `UsuariosPage.vue`: alta de empleado y de cuenta.

**Checkpoint**: OO-B.9/B.10/B.18 completos — un empleado nuevo tiene una cuenta funcional en menos de dos pasos (SC-002).

---

## Phase 5: User Story 3 - Recuperación y actualización de contraseña (Priority: P3)

**Goal**: Un usuario recupera su contraseña por correo con un enlace de un solo uso, y puede cambiar su propia contraseña estando autenticado.

**Independent Test**: solicitar recuperación con un correo registrado, verificar que llega un enlace de un solo uso con vigencia limitada, y que al usarlo se puede definir una nueva contraseña con la cual iniciar sesión.

### Tests para User Story 3 ⚠️

- **T024** [P] [US3] Unit test: rechazo de un token de recuperación ya usado o vencido (FR-010, Edge Case).
- **T025** [US3] Integration test: solicitar recuperación → confirmar con el token → login con la nueva contraseña → reintentar el mismo token (rechazado) (Escenario 3 de `quickstart.md`).

### Implementación de User Story 3

- **T026** [US3] `SistemaRepository`: INSERT de `recuperacion_password` (token aleatorio, vigencia limitada); UPDATE `usado=true` al confirmar (depende de T024).
- **T027** [US3] `SistemaService.solicitar_recuperacion()`: envía el enlace por SendGrid (respuesta genérica exista o no el email — mismo criterio anti-enumeración que FR-002).
- **T028** [US3] `SistemaService.confirmar_recuperacion()` / `.cambiar_password_propia()`: actualiza `password_hash` (depende de T026).
- **T029** [US3] Endpoints: `POST auth/recuperar-password`, `POST auth/recuperar-password/confirmar`, `PATCH auth/mi-password`.
- **T030** [US3] `frontend/.../RecuperarPasswordPage.vue`.

**Checkpoint**: un usuario recupera el acceso sin intervención manual de TI (SC-003).

---

## Phase 6: User Story 4 - Asignación de roles y administración de permisos (Priority: P4)

**Goal**: El Jefe de TI asigna/revoca roles y administra permisos de módulo/tabla, con efecto inmediato.

**Independent Test**: cambiar el rol de una cuenta existente y verificar que su acceso cambia de inmediato; ajustar el permiso de un rol sobre un módulo/tabla y verificar que afecta a todas las cuentas de ese rol.

### Tests para User Story 4 ⚠️

- **T031** [P] [US4] Unit test: un cambio de rol (T033) se refleja en el siguiente request sin nuevo login (research.md Decisión 1, FR-012).
- **T032** [US4] Integration test: cambio de rol → efecto inmediato; ajuste de permiso de tabla sin acceso previo al módulo → rechazado (Escenario 4 de `quickstart.md`).

### Implementación de User Story 4

- **T033** [US4] `SistemaService.asignar_rol()`: UPDATE de `usuarios.role_id` (depende de T031).
- **T034** [US4] `SistemaRepository`: upsert de `role_permisos_modulo`/`role_permisos_tabla` (la FK compuesta ya garantiza la integridad del Edge Case).
- **T035** [US4] Endpoints: `PATCH sistema/usuarios/{id}/rol`, `GET`/`PUT sistema/roles/{id}/permisos-modulo/{id}`, `GET`/`PUT sistema/roles/{id}/permisos-tabla/{modulo}/{tabla}`.
- **T036** [US4] `frontend/.../RolesPermisosPage.vue`: asignación de rol por cuenta, matriz de permisos de módulo/tabla por rol.

**Checkpoint**: OO-B.20 completo — un cambio de rol o permiso aplica sin migración ni reinicio (SC-004).

---

## Phase 7: User Story 5 - Baja de cuenta/empleado y auditoría mensual de accesos (Priority: P5)

**Goal**: Dar de baja a un empleado inhabilita automáticamente su cuenta; el Jefe de TI revisa mensualmente un reporte de auditoría de accesos.

**Independent Test**: dar de baja una cuenta y verificar que no puede iniciar sesión; consultar el reporte mensual de auditoría y verificar que refleja los accesos e intentos ya ocurridos.

### Tests para User Story 5 ⚠️

- **T037** [P] [US5] Unit test: el trigger de T003 inhabilita la cuenta al dar de baja al empleado, y no la reactiva automáticamente al reactivar al empleado (FR-014, FR-015, Edge Case).
- **T038** [US5] Integration test: baja de empleado → cuenta inhabilitada → login rechazado → reporte mensual de auditoría refleja los eventos del periodo (Escenario 5 de `quickstart.md`).

### Implementación de User Story 5

- **T039** [US5] `RRHHService.dar_baja_empleado()`: UPDATE `empleados.activo=false`/`fecha_baja` (el trigger de T003 hace el resto, depende de T037).
- **T040** [US5] `SistemaRepository.reporte_auditoria_mensual(mes, anio)`: agrega `intentos_login` (éxitos/fallos) + `auditoria_log` (acciones) agrupado por usuario.
- **T041** [US5] Endpoints: `PATCH rrhh/empleados/{id}/baja`, `GET sistema/auditoria/reporte-mensual`.
- **T042** [US5] `frontend/.../AuditoriaPage.vue`: reporte mensual agrupado por usuario.

**Checkpoint**: OO-B.11/OO-7.5.2 completos — una cuenta dada de baja no puede iniciar sesión en el 100% de los casos, y el reporte mensual no requiere consulta directa a la base de datos (SC-005, SC-006).

---

## Phase 8: Polish

- **T043** Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- **T044** Correr los 5 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- **T045** Migrar los tests de contrato/integración de 001-007 del token de prueba a JWT real emitido por esta feature (depende de T016) — verificar que ningún test queda dependiendo del token de prueba. Incluye seedear el acceso base de `role_permisos_modulo` que ninguna feature anterior sembró todavía sobre su propio módulo principal — el seed original de `01_operativo_postgres.sql` solo cubre `Cajero`, `Jefe_Marketing` y `Gerente_General`: falta `Jefe_Operaciones`→`Operaciones`, `Jefe_Comercial`→`Comercial`, `Jefe_Finanzas`→`Finanzas`, `Encargado_Tienda`→`Ventas`+`Operaciones`, `Reponedor`→`Operaciones` (más el `role_permisos_tabla` de cada uno sobre las tablas que su propia feature ya documenta). Sin este seed, los tests migrados de 001-007 fallarían al pasar del token de prueba a RBAC real.
- **T046** Revisar cobertura de Principio X: confirmar que el rechazo de credenciales sin distinguir causa (T010), el efecto inmediato de cambio de rol (T031), el rechazo de permiso de tabla sin módulo (integridad de esquema), el trigger de inhabilitación (T037) y el rechazo de token de recuperación vencido/usado (T024) tienen test unitario antes de cerrar la feature.
- **T047** Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final.

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias — en particular T008 (middleware de autenticación) es prerrequisito de que 001-007 dejen de depender del token de prueba.
- US1 (T010-T017) es prerrequisito real de US2-US5 en el sentido de que todas dependen de que exista el mecanismo de login — pero US2 (alta de empleado/cuenta) puede desarrollarse en paralelo, probándose con datos ya sembrados hasta integrarse con US1.
- US2 (T018-T023) es prerrequisito de datos de US3/US4/US5 (necesitan una cuenta ya creada para recuperar contraseña, asignar rol o darla de baja), pero no bloquea su implementación de código.
- US3 (T024-T030), US4 (T031-T036) y US5 (T037-T042) no dependen entre sí — pueden implementarse en paralelo una vez cerrada la Phase 2.
- T045 (migrar tests de 001-007 a JWT real) es la tarea que materializa la dependencia "token de prueba" declarada explícitamente en el `plan.md` de cada feature anterior — debe ejecutarse antes de dar por cerrada esta feature.
