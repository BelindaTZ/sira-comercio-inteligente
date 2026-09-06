# Feature Specification: Autenticación y Administración del Sistema

**Feature Branch**: `008-auth-administracion-sistema`

**Created**: 2026-09-06

**Status**: Draft

**Input**: Login y sesión autenticada; gestión de cuentas de usuario y de empleado (OO-B.9 a B.11, OO-B.18 a B.20 — domain-context.md §8: "login, gestión de usuarios/cuentas, administración de RBAC, auditoría, configuración general"); administración de RBAC (asignación de roles a módulos/tablas); recuperación de contraseña por correo (SendGrid, ya reservado para esta feature en `domain-context.md` §9); y una nueva OO bajo OT-7.5 (OE-7 TI/Datos, ya existente) para la auditoría mensual de accesos al sistema, sin feature dueña previa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Inicio de sesión autenticado (Priority: P1) 🎯 MVP

Cualquier usuario del sistema (Cajero, Encargado de Tienda, cualquier Jefe de departamento, Gerente General) inicia sesión con su usuario y contraseña, y el sistema le otorga una sesión que refleja su rol — esta es la base sin la cual ninguna de las features 001-007 puede probarse con el RBAC real (todas dependían hasta ahora de un token de prueba).

**Why this priority**: Sin esta historia, el RBAC de dos niveles (Principio IV) sigue siendo una promesa de esquema, no un mecanismo real — es la dependencia declarada explícitamente en el plan.md de cada feature anterior.

**Independent Test**: se puede probar iniciando sesión con credenciales válidas y verificando que la sesión resultante permite u obliga exactamente los mismos accesos que el token de prueba usado hasta ahora; y que credenciales inválidas son rechazadas.

**Acceptance Scenarios**:

1. **Given** una cuenta de usuario activa con credenciales correctas, **When** intenta iniciar sesión, **Then** el sistema le otorga una sesión asociada a su rol y registra el momento del último acceso.
2. **Given** credenciales incorrectas, **When** se intenta iniciar sesión, **Then** el sistema rechaza el acceso sin indicar si el usuario existe o si fue la contraseña la que falló (Edge Case).
3. **Given** una cuenta de usuario dada de baja, **When** intenta iniciar sesión, **Then** el sistema rechaza el acceso aunque la contraseña sea correcta.

---

### User Story 2 - Alta de empleado y cuenta de usuario asociada (Priority: P2)

El Jefe de RRHH registra un empleado nuevo; el Jefe de TI crea la cuenta de usuario del sistema ligada a ese empleado, con un rol inicial asignado.

**Why this priority**: Sin un empleado registrado no puede existir una cuenta de usuario (`usuarios.empleado_id` es obligatorio) — es el prerrequisito de todas las demás historias de esta feature, y cubre un vacío real: ninguna feature 001-007 registra un empleado nuevo, solo lo referencian ya existente.

**Independent Test**: se puede probar registrando un empleado nuevo, creando su cuenta de usuario con un rol, y verificando que puede iniciar sesión con ese rol.

**Acceptance Scenarios**:

1. **Given** los datos de un empleado nuevo (nombre, rol/puesto, tienda asignada, fecha de contratación), **When** el Jefe de RRHH lo registra, **Then** el sistema lo guarda y queda disponible para que TI le cree una cuenta.
2. **Given** un empleado registrado sin cuenta de usuario, **When** el Jefe de TI le crea una cuenta con usuario, contraseña inicial y rol, **Then** el empleado puede iniciar sesión con esa cuenta.
3. **Given** un intento de crear una cuenta para un empleado que ya tiene una, **When** se envía la solicitud, **Then** el sistema la rechaza — una cuenta por empleado (Edge Case).

---

### User Story 3 - Recuperación y actualización de contraseña (Priority: P3)

Un usuario que olvida su contraseña solicita recuperarla y recibe un enlace por correo (SendGrid) para definir una nueva; cualquier usuario puede actualizar su propia contraseña estando autenticado.

**Why this priority**: Es la segunda acción más frecuente después del login mismo — sin ella, un olvido de contraseña requeriría intervención manual de TI en cada caso.

**Independent Test**: se puede probar solicitando la recuperación con un correo registrado, verificando que llega un enlace de un solo uso con vigencia limitada, y que al usarlo se puede definir una nueva contraseña con la cual iniciar sesión.

**Acceptance Scenarios**:

1. **Given** un usuario que olvidó su contraseña, **When** solicita recuperarla con el correo de su empleado, **Then** recibe un enlace de un solo uso con vigencia limitada.
2. **Given** un enlace de recuperación ya usado o vencido, **When** se intenta usar de nuevo, **Then** el sistema lo rechaza y exige solicitar uno nuevo.
3. **Given** una sesión autenticada, **When** el usuario cambia su propia contraseña indicando la actual, **Then** el sistema la actualiza y exige la nueva contraseña en el siguiente inicio de sesión.

---

### User Story 4 - Asignación de roles y administración de permisos (Priority: P4)

El Jefe de TI asigna o revoca el rol de una cuenta de usuario, y administra qué módulos y tablas puede ver/editar cada rol — sin necesidad de tocar el esquema de base de datos directamente para cada cambio de permisos.

**Why this priority**: Es la extensión natural de OO-B.20 y de la "administración de RBAC" citada en `domain-context.md` — depende de que ya existan cuentas de usuario (User Story 2) y roles ya sembrados (no crea roles nuevos, ver Assumptions).

**Independent Test**: se puede probar cambiando el rol de una cuenta existente y verificando que su acceso a los módulos cambia de inmediato; y ajustando el permiso de un rol sobre un módulo/tabla y verificando que afecta a todas las cuentas de ese rol.

**Acceptance Scenarios**:

1. **Given** una cuenta de usuario con un rol, **When** el Jefe de TI le asigna un rol distinto, **Then** su acceso a módulos y tablas cambia de inmediato al del nuevo rol, sin requerir que vuelva a iniciar sesión.
2. **Given** un rol con acceso a un módulo, **When** el Jefe de TI ajusta su permiso sobre una tabla específica de ese módulo (ver/crear/editar/eliminar), **Then** el cambio aplica a todas las cuentas con ese rol.
3. **Given** un intento de dar permiso de tabla sin acceso previo al módulo, **When** se intenta guardar, **Then** el sistema lo rechaza (integridad ya garantizada por la FK compuesta del esquema).

---

### User Story 5 - Baja de cuenta/empleado y auditoría mensual de accesos (Priority: P5)

El Jefe de TI da de baja la cuenta de un empleado que deja la empresa; mensualmente, revisa un reporte de auditoría de accesos al sistema (quién accedió a qué, cuándo) para detectar actividad indebida.

**Why this priority**: Cierra el ciclo de vida de la cuenta y cubre el KPI de gobierno de datos de OE-7 ("auditar accesos"), sin feature dueña previa — es la prioridad más baja porque es de revisión periódica, no de operación diaria.

**Independent Test**: se puede probar dando de baja una cuenta y verificando que no puede iniciar sesión; y consultando el reporte mensual de auditoría para verificar que refleja los accesos e intentos de acceso ya ocurridos.

**Acceptance Scenarios**:

1. **Given** un empleado que deja la empresa, **When** el Jefe de RRHH lo da de baja, **Then** su cuenta de usuario asociada queda automáticamente inhabilitada para iniciar sesión, sin eliminar su historial de acciones ya registradas.
2. **Given** un mes con actividad de inicio de sesión y cambios sobre datos del sistema, **When** el Jefe de TI consulta el reporte mensual de auditoría, **Then** ve los accesos e intentos fallidos del periodo, agrupados por usuario.
3. **Given** una cuenta ya inhabilitada, **When** se reactiva el empleado (Edge Case), **Then** la cuenta sigue inhabilitada hasta que el Jefe de TI la reactive explícitamente — la baja de la cuenta no se revierte automáticamente junto con la del empleado.

---

### Edge Cases

- ¿Qué pasa si se ingresan credenciales incorrectas repetidamente? El sistema no revela si falló el usuario o la contraseña, para no ayudar a un atacante a enumerar cuentas válidas — mismo criterio de seguridad ya aplicado en el manejo de datos de tarjeta (001, 007).
- ¿Qué pasa si se intenta crear una segunda cuenta de usuario para un empleado que ya tiene una? El sistema lo rechaza — la relación empleado↔cuenta es 1 a 1 (`usuarios.empleado_id UNIQUE`, ya reservado desde 001).
- ¿Qué pasa si un enlace de recuperación de contraseña se usa dos veces? La segunda vez se rechaza — de un solo uso.
- ¿Qué pasa si se intenta asignar permiso de tabla a un rol sin acceso al módulo correspondiente? El sistema lo rechaza — ya garantizado por la integridad referencial del esquema (FK compuesta `role_permisos_tabla` → `role_permisos_modulo`).
- ¿Qué pasa si se reactiva a un empleado que había sido dado de baja junto con su cuenta? La cuenta permanece inhabilitada — reactivarla es una decisión separada y explícita del Jefe de TI, no automática.
- ¿Qué pasa con las sesiones ya emitidas de una cuenta que se da de baja o cambia de rol mientras el usuario sigue conectado? Quedan fuera del alcance de este documento el mecanismo exacto de invalidación en curso (token de corta duración vs. lista de revocación) — se resuelve en `research.md`/`plan.md`, no aquí.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a cualquier usuario iniciar sesión con su nombre de usuario y contraseña, otorgando una sesión asociada a su rol.
- **FR-002**: El sistema DEBE rechazar el inicio de sesión con credenciales incorrectas sin distinguir si falló el usuario o la contraseña (Edge Case).
- **FR-003**: El sistema DEBE rechazar el inicio de sesión de una cuenta dada de baja, aunque la contraseña sea correcta.
- **FR-004**: El sistema DEBE registrar el momento del último inicio de sesión exitoso de cada cuenta.
- **FR-005**: El Jefe de RRHH DEBE poder registrar un empleado nuevo con su rol/puesto, tienda asignada y fecha de contratación (OO-B.9).
- **FR-006**: El Jefe de RRHH DEBE poder actualizar los datos o el puesto de un empleado existente (OO-B.10).
- **FR-007**: El Jefe de TI DEBE poder crear la cuenta de usuario de un empleado ya registrado, con usuario, contraseña inicial y rol (OO-B.18).
- **FR-008**: El sistema NO DEBE permitir crear una segunda cuenta de usuario para un empleado que ya tiene una (Edge Case).
- **FR-009**: El sistema DEBE permitir a un usuario solicitar la recuperación de su contraseña mediante un enlace de un solo uso enviado por correo, con vigencia limitada.
- **FR-010**: El sistema NO DEBE permitir reutilizar un enlace de recuperación de contraseña ya usado o vencido (Edge Case).
- **FR-011**: El sistema DEBE permitir a un usuario autenticado cambiar su propia contraseña indicando la actual (OO-B.19).
- **FR-012**: El Jefe de TI DEBE poder asignar o revocar el rol de una cuenta de usuario existente, con efecto inmediato sobre su acceso (OO-B.20).
- **FR-013**: El Jefe de TI DEBE poder administrar el permiso de un rol sobre un módulo (ver/editar) y sobre una tabla específica de ese módulo (ver/crear/editar/eliminar) — "administración de RBAC".
- **FR-014**: El Jefe de RRHH DEBE poder dar de baja a un empleado, lo que DEBE inhabilitar automáticamente su cuenta de usuario asociada para iniciar sesión, sin eliminar su historial de acciones ya registradas (OO-B.11).
- **FR-015**: El sistema NO DEBE reactivar automáticamente una cuenta de usuario inhabilitada cuando su empleado asociado se reactiva — requiere una acción explícita del Jefe de TI (Edge Case).
- **FR-016**: El Jefe de TI DEBE poder consultar mensualmente un reporte de auditoría de accesos al sistema, agrupado por usuario, incluyendo intentos fallidos.

### Key Entities

- **Empleado**: nombre, tienda asignada (nullable), puesto/rol laboral, fecha de contratación, fecha de baja (nullable), activo — ya reservado desde 001, sin feature que lo registrara hasta ahora.
- **Cuenta de Usuario**: empleado asociado (1:1), usuario, contraseña (hash), rol, activa, último inicio de sesión.
- **Rol**: ya sembrados 10 roles fijos — esta feature no crea roles nuevos, solo los asigna a cuentas y administra sus permisos (Assumptions).
- **Permiso de Módulo / Permiso de Tabla**: qué puede ver/editar cada rol a nivel de módulo, y qué puede seleccionar/insertar/actualizar/eliminar a nivel de tabla específica.
- **Recuperación de Contraseña**: enlace de un solo uso, vigencia limitada, asociado a una cuenta.
- **Registro de Auditoría**: usuario, tabla afectada, acción, valores antes/después, fecha — ya reservado desde 001, poblado transversalmente por todas las features, consultado por esta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Cualquier usuario puede iniciar sesión y obtener acceso exactamente al conjunto de módulos/tablas que su rol permite, sin depender de un token de prueba.
- **SC-002**: Un empleado nuevo puede tener una cuenta de usuario funcional (con login exitoso) en menos de dos pasos (alta de empleado, alta de cuenta).
- **SC-003**: Un usuario que olvida su contraseña puede recuperar el acceso sin intervención manual de TI.
- **SC-004**: Un cambio de rol o de permiso de módulo/tabla aplica de inmediato, sin requerir una migración ni un reinicio del sistema.
- **SC-005**: Una cuenta de un empleado dado de baja no puede iniciar sesión, verificable en el 100% de los casos.
- **SC-006**: El Jefe de TI puede reportar la actividad de acceso de un mes completo sin consultar la base de datos directamente.

## Assumptions

- **OO-7.5.2 asignada (sin crear OO nueva)**: `oo-objetivos-operativos.md` tenía OO-7.5.1 (definir política de calidad/trazabilidad de datos) y OO-7.5.2 (auditar accesos a los datos del sistema, mensual) bajo OT-7.5, ninguna asignada a una feature hasta ahora. Esta feature toma **OO-7.5.2** (auditoría de accesos) porque encaja directamente con "auditoría" ya citado como alcance de 008 en `domain-context.md` — no requiere una OO nueva, solo se asigna la ya existente. **OO-7.5.1** (política de calidad/trazabilidad de datos, más amplia que solo accesos) se deja fuera de esta feature — se evaluará al especificar 010-plataforma-datos-tactico-estrategico, donde encaja mejor por tratarse de gobierno del pipeline de datos completo (ELT, warehouse), no solo de cuentas de acceso.
- **Empleado (OO-B.9 a B.11) incorporado a esta feature**: su actor nominal es "Jefe de RRHH" (rol ya sembrado, sin gap), pero ningún feature 001-007 lo registra como propio — se incorpora aquí porque una cuenta de usuario (OO-B.18) siempre requiere un empleado ya existente (`usuarios.empleado_id` es obligatorio y único), y no existe ninguna feature de RRHH operativa en el roadmap de 10 features a la que asignárselo de otra forma.
- **Hallazgo — OE-8 (RRHH) resuelto por la feature nueva 011-recursos-humanos**: OT-8.1 (retención de roles críticos), OT-8.2 (capacitación en el sistema), OT-8.3 (clima laboral) y OT-8.4 (plan de sucesión) — con sus 8 OO y las 4 tablas ya reservadas en el esquema desde 001 (`capacitaciones`, `empleado_capacitacion`, `clima_laboral`, `plan_sucesion`) — no encajaban en esta feature (que solo absorbe el CRUD base de Empleado, no la gestión táctica de RRHH) ni en ninguna de las 10 features del roadmap original. Se detectó aquí como vacío real y grande (una OE completa), igual que OT-2.4/OT-2.5 y OT-4.2 en features anteriores, y se resolvió creando **011-recursos-humanos** (feature nueva, acotada a OE-8 completo) — ver ese spec.md.
- **Roles fijos, sin CRUD de roles nuevos**: los 10 roles (`Cajero`, `Encargado_Tienda`, `Reponedor`, `Jefe_Comercial`, `Jefe_Marketing`, `Jefe_Operaciones`, `Jefe_Finanzas`, `Jefe_TI`, `Jefe_RRHH`, `Gerente_General`) ya están sembrados y son los mismos citados en cada spec.md de 001-007 — "administración de RBAC" en esta feature significa asignar esos roles a cuentas y ajustar sus permisos de módulo/tabla, no crear roles nuevos (fuera de alcance, no narrado en el enunciado ni pedido por el usuario).
- **Sin gap de rol RBAC**: todos los actores de esta feature (Jefe_RRHH, Jefe_TI) ya tienen rol propio sembrado.
- **Mecanismo exacto de invalidación de sesión ante cambio de rol/baja de cuenta** (Edge Case) se deja para `research.md`/`plan.md` — es una decisión técnica (JWT de corta duración vs. lista de revocación), no de alcance funcional.
