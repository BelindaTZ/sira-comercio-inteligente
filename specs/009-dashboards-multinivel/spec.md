# Feature Specification: Dashboards Multinivel

**Feature Branch**: `009-dashboards-multinivel`

**Created**: 2026-09-06

**Status**: Draft — **en espera de implementación** hasta que 010-plataforma-datos-tactico-estrategico esté construida (dependencia ya documentada en `constitution.md`/`domain-context.md`)

**Input**: OT-7.4 completo (OE-7 TI/Datos — dashboard estratégico consolidado, dashboards tácticos por departamento, verificación de disponibilidad de dashboards operativos en tienda). Consume la plataforma de datos que construye 010 — no la construye.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dashboard estratégico consolidado (Priority: P1) 🎯 MVP

El Gerente General consulta, en una sola vista, los KPIs principales de la red consolidada — actualizados automáticamente cada día, sin que nadie los arme a mano.

**Why this priority**: Es el nivel de mayor visibilidad de la organización (Dirección General) y el caso de uso que da nombre a "dashboards multinivel" — sin él, no hay ninguna vista consolidada de toda la red.

**Independent Test**: se puede probar forzando la actualización del dashboard estratégico y verificando que refleja los valores ya calculados por las features fuente (margen de 003, CLV/retención de 002, disponibilidad/merma de 001/006, pérdidas por fraude/incidentes de seguridad de pago de 006/007).

**Acceptance Scenarios**:

1. **Given** datos ya calculados por las features de origen, **When** el job diario publica el dashboard estratégico, **Then** el Gerente General ve los KPIs principales de cada Objetivo Estratégico que sí tiene una fuente de datos real.
2. **Given** un Objetivo Estratégico sin ninguna feature que calcule su KPI (Market Share/NPS de OE-4 — sin canal de encuesta a cliente en el alcance del proyecto), **When** se publica el dashboard, **Then** ese KPI se muestra explícitamente como no disponible, nunca con un valor inventado. OE-8 (rotación de personal/clima laboral) ya no cae en este caso: 011-recursos-humanos lo calcula (ver corrección en Assumptions).
3. **Given** el dashboard ya publicado, **When** el Gerente General lo consulta en cualquier momento del día, **Then** ve la fecha de la última actualización junto a los valores.

---

### User Story 2 - Dashboards tácticos por departamento (Priority: P2)

Cada Jefe de departamento consulta el dashboard de su propio departamento, con los KPIs y reportes ya calculados por la feature correspondiente — sin acceso a los dashboards de otros departamentos.

**Why this priority**: Es el nivel táctico de la misma OT — depende de que existan features fuente ya calculando datos por departamento (001-007), que ya están cerradas.

**Independent Test**: se puede probar iniciando sesión con el rol de un Jefe de departamento y verificando que ve únicamente el dashboard de su propio departamento, actualizado automáticamente.

**Acceptance Scenarios**:

1. **Given** un Jefe de departamento con datos ya calculados por su feature (ej. Jefe Comercial y el margen de 003), **When** consulta su dashboard táctico, **Then** ve los KPIs de su propio departamento, sin tener que consolidarlos manualmente.
2. **Given** dos Jefes de departamentos distintos, **When** uno intenta ver el dashboard del otro, **Then** el sistema no lo permite — cada uno ve solo el suyo, salvo el Gerente General (solo lectura de todos).
3. **Given** una feature fuente sin datos suficientes para calcular un KPI (ej. un modelo de pronóstico aún no entrenado), **When** se publica el dashboard táctico correspondiente, **Then** ese KPI se muestra como datos insuficientes, sin bloquear el resto del dashboard.

---

### User Story 3 - Verificación de disponibilidad de dashboards operativos en tienda (Priority: P3)

El Jefe de TI revisa diariamente que los dashboards operativos que cada tienda usa (alertas de reposición, seguimiento de merma, cuadre de caja, etc., ya construidos dentro de cada feature) estén disponibles y actualizados.

**Why this priority**: Es el nivel operativo de la misma OT — depende de que ya existan los dashboards operativos dentro de cada feature (001-007), y es una verificación de disponibilidad, no un cálculo nuevo.

**Independent Test**: se puede probar simulando que un dashboard operativo de una tienda no se actualiza por más de un día, y verificando que el Jefe de TI lo ve señalado en su revisión diaria.

**Acceptance Scenarios**:

1. **Given** los dashboards operativos ya construidos dentro de cada feature (001-007), **When** el Jefe de TI hace su revisión diaria, **Then** ve cuáles están disponibles y actualizados, y cuáles no, para toda la red de tiendas.
2. **Given** un dashboard operativo de una tienda que lleva más de un día sin actualizarse, **When** se genera la revisión diaria, **Then** el sistema lo señala como una alerta para el Jefe de TI.

---

### Edge Cases

- ¿Qué pasa con el KPI de OE-4 (Market Share/NPS), que no tiene ninguna feature que lo calcule (sin canal de encuesta a cliente en el alcance del proyecto)? Se muestra explícitamente como no disponible en cualquier dashboard donde aparecería — el sistema nunca inventa un valor (Principio VII). OE-8 (rotación de personal/clima laboral) ya tiene fuente real desde que se creó 011-recursos-humanos (ver corrección en Assumptions) — deja de ser un caso de "no disponible" y pasa a mostrarse con datos reales.
- ¿Qué pasa si una feature fuente aún no tiene datos suficientes para calcular su KPI (ej. churn de un cliente con menos de la ventana mínima de historial)? El dashboard lo muestra como datos insuficientes, sin bloquear el resto de KPIs del mismo dashboard.
- ¿Qué pasa si la plataforma de datos (010) aún no está construida? Esta feature no puede operar con volumen real de red — permanece en espera junto con 010 (Assumptions).
- ¿Qué pasa si dos roles de distinto departamento intentan ver el dashboard del otro? El RBAC ya existente (`role_permisos_modulo`) lo impide, sin necesidad de lógica adicional en esta feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE publicar/actualizar automáticamente, cada día, un dashboard estratégico consolidado con los KPIs de los Objetivos Estratégicos que tengan una fuente de datos real ya calculada por otra feature (OO-7.4.1, resuelto como job automático — gap de rol "Analista de Datos", mismo patrón que 004).
- **FR-002**: El sistema NO DEBE mostrar en el dashboard estratégico ningún KPI sin una fuente de datos real — se muestra como no disponible en su lugar (Edge Case).
- **FR-003**: El Gerente General DEBE poder consultar el dashboard estratégico en cualquier momento, viendo la fecha de su última actualización.
- **FR-004**: El sistema DEBE publicar/actualizar automáticamente, cada día, un dashboard táctico por departamento con los KPIs/reportes ya calculados por la feature correspondiente a ese departamento (OO-7.4.2, job automático).
- **FR-005**: Cada Jefe de departamento DEBE poder consultar únicamente el dashboard de su propio departamento; el Gerente General DEBE poder consultar todos (RBAC ya existente).
- **FR-006**: El Jefe de TI DEBE poder verificar diariamente qué dashboards operativos de tienda están disponibles y actualizados, y cuáles no, para toda la red (OO-7.4.3).
- **FR-007**: El sistema DEBE alertar al Jefe de TI cuando un dashboard operativo de una tienda lleve más de un día sin actualizarse.
- **FR-008**: El sistema DEBE registrar la fecha y hora de la última publicación exitosa de cada dashboard (estratégico, cada táctico, cada operativo de tienda).
- **FR-009**: Publicar o actualizar un dashboard NO DEBE degradar el rendimiento de las operaciones transaccionales normales del sistema.
- **FR-010**: El sistema DEBE permitir forzar manualmente la actualización de un dashboard sin esperar al job diario, en entorno de desarrollo (mismo patrón ya usado en 003-006).

### Key Entities

- **Dashboard Estratégico**: KPIs consolidados de toda la red por Objetivo Estratégico, fecha de última publicación.
- **Dashboard Táctico**: KPIs/reportes de un departamento específico, fecha de última publicación.
- **Dashboard Operativo (de tienda)**: ya construido dentro de cada feature 001-007; esta feature solo verifica su disponibilidad/actualización, no lo construye.
- **Registro de Publicación**: qué dashboard, cuándo se publicó, si tuvo éxito.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Gerente General ve el dashboard estratégico sin que pase más de un día desde el último cambio en los datos fuente.
- **SC-002**: Cada Jefe de departamento ve su propio dashboard táctico sin depender de un reporte manual armado por otra persona.
- **SC-003**: El Jefe de TI identifica qué dashboards operativos de tienda no están actualizados sin visitar cada tienda.
- **SC-004**: Ningún KPI mostrado en cualquier dashboard es un valor inventado — todo KPI mostrado proviene de una feature que realmente lo calcula.
- **SC-005**: La actualización de dashboards no genera ninguna degradación perceptible en el resto del sistema.

## Assumptions

- **Dependencia de 010-plataforma-datos-tactico-estrategico**: esta feature consume las agregaciones del warehouse que construye 010; no puede operar con volumen real de red hasta que 010 esté implementada — ambas quedan **en espera** (ya documentado en `constitution.md`), separadas a propósito porque un DAG se prueba con datos y un dashboard se prueba visualmente (Independent Test de Spec Kit).
- **Gap de rol RBAC — "Analista de Datos" (OO-7.4.1/7.4.2)**: mismo patrón ya resuelto en 004 (entrenamiento/monitoreo de modelos) — se convierte en job automático del sistema, dejando al Jefe de TI como actor humano real (OO-7.4.3, verificación de disponibilidad).
- **Sin cálculo propio de KPIs**: esta feature no recalcula ningún indicador — solo consolida y visualiza los ya calculados por 001-008, evitando duplicar lógica de cálculo ya construida en cada feature dueña (Principio VIII).
- **KPI sin fuente real (OE-4) documentado explícitamente**: Market Share/NPS (OE-4) no tiene ninguna feature que lo calcule (no hay canal de encuesta a cliente en el alcance del proyecto) — se muestra como no disponible, nunca inventado.
- **Corrección (OE-8 ya tiene fuente real)**: este documento se redactó originalmente asumiendo que OE-8 (rotación de personal/clima laboral) tampoco tenía feature dueña, por el vacío documentado en `spec.md` de 008. Ese vacío se resolvió creando **011-recursos-humanos** (ver ese spec.md), que calcula tasa de rotación por tienda/periodo y clima laboral semestral. En consecuencia, el dashboard estratégico de esta feature SÍ puede mostrar los KPIs de OE-8 con datos reales, tomados de 011 — ya no aplica el caso "no disponible" para OE-8, solo para OE-4.
