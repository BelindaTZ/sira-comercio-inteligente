# Feature Specification: Recursos Humanos

**Feature Branch**: `011-recursos-humanos`

**Created**: 2026-09-06

**Status**: Draft

**Input**: OE-8 completo (OT-8.1 a OT-8.4 — retención de roles críticos, capacitación en el sistema, clima laboral semestral, plan de sucesión). Feature nueva, agregada tras detectar en `spec.md` de 008 que OE-8 no tenía ninguna feature dueña en el roadmap original de 10 features.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retención de roles críticos (Priority: P1) 🎯 MVP

El Jefe de RRHH identifica qué puestos son críticos para la operación (encargados de tienda, cajeros senior, analistas de datos) y registra las acciones de retención aplicadas a los empleados que los ocupan.

**Why this priority**: Es el OT de mayor impacto directo en el KPI de OE-8 (tasa de rotación de personal clave) y el único que requiere una decisión de negocio previa (qué puestos son críticos) de la que dependen las demás historias.

**Independent Test**: se puede probar marcando un puesto como crítico y registrando una acción de retención para un empleado que lo ocupa, verificando que queda visible en el listado de retención del Jefe de RRHH.

**Acceptance Scenarios**:

1. **Given** el catálogo de puestos (`roles_puesto`) ya existente, **When** el Jefe de RRHH marca uno o más puestos como críticos, **Then** el sistema los identifica como tales para todas las tiendas.
2. **Given** un puesto crítico con empleados activos, **When** el Jefe de RRHH registra una acción de retención (fecha, descripción), **Then** queda asociada al empleado y consultable en cualquier momento.

---

### User Story 2 - Capacitación en el sistema (Priority: P2)

El Jefe de RRHH programa sesiones de capacitación sobre las nuevas herramientas del sistema (dashboards, alertas, IA) por rol, y el Encargado de Tienda confirma el cumplimiento de su personal.

**Why this priority**: Depende de que ya existan empleados y puestos (P1 no es prerrequisito técnico, pero comparten el mismo actor principal y refuerzan el mismo objetivo de capital humano).

**Independent Test**: se puede probar programando una capacitación y marcando su cumplimiento para un empleado, verificando que el Encargado de Tienda ve el estado de cumplimiento de su personal.

**Acceptance Scenarios**:

1. **Given** una capacitación programada por rol, **When** un empleado la completa, **Then** el Encargado de Tienda puede confirmar el cumplimiento con la fecha de finalización.
2. **Given** el personal de una tienda con capacitaciones pendientes, **When** el Encargado de Tienda revisa su cumplimiento mensual, **Then** ve claramente quién completó y quién no cada capacitación asignada a su rol.

---

### User Story 3 - Clima laboral semestral y su cruce con rotación (Priority: P3)

El Jefe de RRHH aplica la encuesta de clima laboral/desempeño por tienda cada semestre y cruza el resultado con la tasa de rotación de esa tienda en el mismo periodo.

**Why this priority**: Es semestral (menor frecuencia que P1/P2) y depende de tener empleados y bajas ya registrados (`empleados.fecha_baja`, ya existente desde 001) para poder calcular la tasa de rotación a cruzar.

**Independent Test**: se puede probar registrando un resultado de encuesta para una tienda y un periodo, verificando que el sistema muestra junto a él la tasa de rotación de esa misma tienda en ese periodo.

**Acceptance Scenarios**:

1. **Given** el cierre de un semestre, **When** el Jefe de RRHH registra el resultado promedio de la encuesta de clima por tienda, **Then** el sistema lo asocia al periodo (ej. `2026-S2`) y a la tienda.
2. **Given** un resultado de clima ya registrado, **When** el Jefe de RRHH lo consulta, **Then** ve junto a él la tasa de rotación de esa tienda en el mismo periodo, calculada a partir de las bajas de empleados ya registradas.

---

### User Story 4 - Plan de sucesión (Priority: P4)

El Jefe de RRHH identifica candidatos internos para posiciones clave de gerencia de tienda y documenta el plan de sucesión por posición crítica.

**Why this priority**: Es anual (la menor frecuencia de las cuatro) y depende de que ya exista la identificación de roles críticos de P1 (una posición clave es, por definición, un puesto ya marcado como crítico).

**Independent Test**: se puede probar registrando un candidato interno para un puesto crítico y verificando que aparece en el plan de sucesión de ese puesto.

**Acceptance Scenarios**:

1. **Given** un puesto ya marcado como crítico (P1), **When** el Jefe de RRHH identifica un empleado interno como candidato, **Then** queda registrado en el plan de sucesión de ese puesto, con fecha.
2. **Given** un puesto crítico sin ningún candidato registrado, **When** el Jefe de RRHH consulta el plan de sucesión, **Then** el sistema lo señala explícitamente como sin cobertura.

---

### Edge Cases

- ¿Qué pasa si se intenta registrar una acción de retención para un empleado en un puesto que no está marcado como crítico? El sistema lo permite (la retención puede aplicarse a cualquier empleado), pero solo los puestos marcados como críticos alimentan el KPI de OT-8.1.
- ¿Qué pasa si un empleado causa baja (`empleados.fecha_baja`) antes de completar una capacitación ya programada? Su registro de capacitación queda como no completado, sin bloquear el cumplimiento del resto del personal de la tienda.
- ¿Qué pasa si una tienda no aplica la encuesta de clima en un semestre? No se genera ningún registro para ese periodo — no se inventa un resultado (Principio VII).
- ¿Qué pasa si un puesto crítico se marca como tal después de ya tener empleados activos en él? La retención y la sucesión aplican desde ese momento en adelante, sin reconstruir historial retroactivo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Jefe de RRHH DEBE poder marcar uno o más puestos (`roles_puesto`) como críticos, para toda la red (OO-8.1.1).
- **FR-002**: El Jefe de RRHH DEBE poder registrar una acción de retención (fecha, descripción) para un empleado, consultable en cualquier momento (OO-8.1.2).
- **FR-003**: El Jefe de RRHH DEBE poder programar una capacitación (nombre, descripción) dirigida a uno o más roles del sistema (OO-8.2.1).
- **FR-004**: El sistema DEBE registrar la fecha de finalización de una capacitación por empleado (OO-8.2.2, tabla `empleado_capacitacion`).
- **FR-005**: El Encargado de Tienda DEBE poder consultar el cumplimiento de capacitación de su propio personal, sin acceso al de otras tiendas (OO-8.2.2).
- **FR-006**: El Jefe de RRHH DEBE poder registrar el resultado promedio de la encuesta de clima laboral por tienda y periodo semestral (OO-8.3.1, tabla `clima_laboral`).
- **FR-007**: El sistema DEBE mostrar, junto a cada resultado de clima registrado, la tasa de rotación de esa misma tienda en el mismo periodo, calculada a partir de `empleados.fecha_baja` (OO-8.3.2).
- **FR-008**: El Jefe de RRHH DEBE poder registrar uno o más candidatos internos para un puesto crítico, con fecha (OO-8.4.1, tabla `plan_sucesion`).
- **FR-009**: El sistema DEBE señalar explícitamente cualquier puesto crítico sin ningún candidato registrado en el plan de sucesión (OO-8.4.2).
- **FR-010**: El sistema NO DEBE calcular ni mostrar ningún indicador de clima laboral o rotación para un periodo sin encuesta o sin bajas registradas — se muestra como sin datos, nunca inventado (Principio VII).

### Key Entities

- **Rol Crítico**: marca sobre un puesto existente (`roles_puesto`) que lo identifica como crítico para la operación; alimenta retención y sucesión.
- **Acción de Retención**: registro de una acción aplicada a un empleado en un puesto crítico, con fecha y descripción.
- **Capacitación**: sesión sobre el uso del sistema, dirigida a uno o más roles.
- **Registro de Capacitación de Empleado**: relación empleado-capacitación con fecha de finalización (o pendiente).
- **Encuesta de Clima Laboral**: resultado promedio por tienda y periodo semestral.
- **Plan de Sucesión**: candidato interno asociado a un puesto crítico, con fecha.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Jefe de RRHH identifica los puestos críticos de toda la red sin depender de una lista externa a Excel.
- **SC-002**: El Encargado de Tienda conoce el estado de cumplimiento de capacitación de su personal sin tener que preguntarle uno por uno.
- **SC-003**: El Jefe de RRHH ve, para cualquier tienda y semestre con encuesta aplicada, el clima laboral junto a la rotación del mismo periodo, sin cruzar los datos a mano.
- **SC-004**: Ningún puesto crítico queda sin cobertura de sucesión sin que el sistema lo señale explícitamente.
- **SC-005**: Ningún KPI de clima o rotación mostrado corresponde a un periodo sin datos reales registrados.

## Assumptions

- **Sin gap de rol RBAC**: a diferencia de otras features, `Jefe_RRHH` ya existe como rol seedeado en `01_operativo_postgres.sql` (junto con `Encargado_Tienda`, también seedeado) — no aplica el patrón de "actor sin rol RBAC" usado en 002/003/004/009/010.
- **Columna adicional pendiente de diseño**: `roles_puesto` no tiene hoy una columna que marque un puesto como crítico (FR-001); se resuelve como columna aditiva (`es_critico BOOLEAN`) al construir `data-model.md`, mismo patrón ya usado en 007 para la duración de cobro — no rompe las 50 tablas ya validadas.
- **Tasa de rotación calculada, no almacenada**: FR-007 se calcula a partir de `empleados.fecha_baja` ya existente (activo/inactivo por tienda y periodo) — no requiere una tabla nueva, solo una consulta agregada (Principio VIII, no duplicar dato ya existente).
- **Alcance acotado, con una corrección detectada al planificar**: esta feature usa las 4 tablas de RRHH ya reservadas desde el diseño inicial (`capacitaciones`, `empleado_capacitacion`, `clima_laboral`, `plan_sucesion`) más `empleados`/`roles_puesto` ya existentes. Al construir `data-model.md` se detectó que ninguna tabla reservada modela la acción de retención de FR-002 (`roles_puesto`, `plan_sucesion` y las 3 tablas de capacitación/clima no tienen ese propósito) — se agrega **una** tabla nueva y mínima, `acciones_retencion` (empleado_id, fecha, descripción), la única de toda esta feature, manteniendo el espíritu de "lo justo y necesario" (Principio VIII) a pedido explícito del usuario, aunque contradiga la formulación literal original de este párrafo ("no se agrega ninguna tabla nueva") — ver `data-model.md` para el detalle.
- **Sin dependencia de 009/010**: a diferencia de esas dos features, RRHH no depende de la plataforma de datos táctico/estratégica ni del warehouse — es registro operativo directo sobre PostgreSQL, por lo que puede implementarse de inmediato, sin quedar "en espera".
