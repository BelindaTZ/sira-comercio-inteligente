# Feature Specification: Plataforma de Datos Táctico-Estratégica

**Feature Branch**: `010-plataforma-datos-tactico-estrategico`

**Created**: 2026-09-06

**Status**: Implementada (`/speckit-implement`, 2026-09-07). El pipeline ELT se desarrolló y probó con PostgreSQL/MinIO reales y dobles en memoria para ClickHouse/Airflow; su activación con volumen de producción se retoma junto con la capa táctica/estratégica (009-dashboards-multinivel).

**Input**: OT-7.1 completo (OE-7 TI/Datos — definición del modelo de datos único, carga/integración diaria de datos) más OO-7.5.1 (OT-7.5, gobierno de datos — calidad y trazabilidad), que la feature 008 dejó explícitamente pendiente de evaluar aquí por tratarse del pipeline de datos completo, no solo de accesos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Definición del modelo de datos único del warehouse (Priority: P1) 🎯 MVP

El Jefe de TI define, una sola vez, el modelo de datos único (fact_venta + dimensiones) que sirve de base a todas las cargas siguientes desde el operativo hacia el warehouse.

**Why this priority**: Sin un modelo definido, ninguna carga posterior tiene un destino claro — es el prerrequisito literal de OT-7.1 y de toda esta feature.

**Independent Test**: se puede probar documentando el modelo de datos único y verificando que cubre venta, cliente, inventario y caja (las cuatro áreas citadas explícitamente en OT-7.1) con una estructura que una carga real puede poblar.

**Acceptance Scenarios**:

1. **Given** los datos operativos ya existentes (venta, cliente, inventario, caja) en PostgreSQL, **When** el Jefe de TI define el modelo de datos único del warehouse, **Then** queda documentado un esquema que cubre las cuatro áreas sin ambigüedad.
2. **Given** el modelo ya definido, **When** una tabla operativa nueva se agrega en una feature futura, **Then** el Jefe de TI puede incorporarla al modelo antes de que sus datos empiecen a cargarse (Edge Case).

---

### User Story 2 - Carga diaria automática desde el operativo hacia el warehouse (Priority: P2)

El sistema ejecuta automáticamente, cada día, la carga de datos desde PostgreSQL y desde el landing-zone hacia el warehouse; el Jefe de TI monitorea el resultado de cada corrida.

**Why this priority**: Es la acción central de OT-7.1 — sin ella, el modelo definido en la historia anterior nunca se puebla con datos reales.

**Independent Test**: se puede probar ejecutando una carga completa inicial y verificando que el warehouse queda poblado; luego ejecutando una carga incremental y verificando que solo trae los datos nuevos o modificados desde la última corrida exitosa.

**Acceptance Scenarios**:

1. **Given** el modelo de datos ya definido, **When** se ejecuta la primera carga, **Then** el sistema trae el histórico completo ya sembrado como carga base (Edge Case).
2. **Given** una carga base ya realizada, **When** se ejecuta la carga diaria siguiente, **Then** el sistema trae solo los datos nuevos o modificados desde la última corrida exitosa, sin recargar todo de nuevo.
3. **Given** una corrida que falla a medias, **When** se reprocesa, **Then** el sistema no duplica los datos ya cargados exitosamente antes de la falla.
4. **Given** una corrida en curso, **When** se intenta iniciar otra sobre el mismo destino, **Then** el sistema lo impide hasta que la primera termine (Edge Case).
5. **Given** cualquier corrida ya finalizada, **When** el Jefe de TI la consulta, **Then** ve cuántas filas se cargaron, cuántas fallaron y cuánto tardó.

---

### User Story 3 - Calidad y trazabilidad de la carga de datos (Priority: P3)

El sistema detecta registros que no cumplen reglas mínimas de calidad al cargarse hacia el warehouse y los reporta sin bloquear el resto de la carga; cada corrida queda registrada con su origen, destino y resultado para trazabilidad.

**Why this priority**: Cubre OO-7.5.1 (gobierno de datos) — depende de que ya existan cargas reales (historias anteriores) sobre las cuales aplicar las reglas de calidad y dejar la traza.

**Independent Test**: se puede probar cargando un lote con un registro que rompe una regla de calidad (ej. una referencia a un producto inexistente) y verificando que el resto del lote se carga igual, con ese registro señalado aparte.

**Acceptance Scenarios**:

1. **Given** un lote de datos con un registro que no cumple una regla mínima de calidad, **When** se carga hacia el warehouse, **Then** el resto del lote se carga con normalidad y el registro problemático queda señalado aparte, sin detener la corrida.
2. **Given** cualquier corrida ya ejecutada, **When** el Jefe de TI consulta su trazabilidad, **Then** ve el origen, el destino, la cantidad de filas y el resultado, sin depender de los logs de Airflow directamente.

---

### User Story 4 - Política de gobierno de datos como documento de referencia (Priority: P4)

El Jefe de TI mantiene el texto vigente de la política de gobierno de datos (calidad, trazabilidad, acceso), consultable dentro del sistema.

**Why this priority**: Da cuerpo documental a OO-7.5.1 — la prioridad más baja porque es un documento de referencia, igual que el protocolo de escalamiento de 006 y la política de seguridad de pagos de 007, sin impacto operativo directo.

**Independent Test**: se puede probar definiendo el texto de la política y verificando que el Jefe de TI puede consultarlo íntegro en cualquier momento.

**Acceptance Scenarios**:

1. **Given** la política de gobierno de datos vigente, **When** el Jefe de TI la consulta, **Then** ve su texto completo sin depender de un documento externo al sistema.
2. **Given** una actualización de la política, **When** el Jefe de TI la registra, **Then** la versión anterior queda disponible para consulta histórica (mismo criterio que 006/007).

---

### Edge Cases

- ¿Qué pasa con la primera carga, antes de que exista algo "incremental" con qué compararse? Se trata como un caso especial de carga histórica completa, no como un error de "todo es nuevo".
- ¿Qué pasa si una tabla operativa nueva no está todavía en el modelo de datos único? Su carga queda pendiente hasta que el Jefe de TI la incorpore al modelo — el sistema no carga información sin una definición previa.
- ¿Qué pasa si dos corridas de carga se solapan? El sistema no permite una segunda corrida sobre el mismo destino mientras la anterior sigue en curso.
- ¿Qué pasa si una corrida falla a medias? Se puede reprocesar sin duplicar los datos ya cargados con éxito (idempotencia).
- ¿Qué pasa si un registro no cumple una regla de calidad? Se reporta aparte, sin bloquear el resto de la carga de esa corrida.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Jefe de TI DEBE poder definir y documentar el modelo de datos único del warehouse (fact_venta + dimensiones de venta, cliente, inventario y caja), como base de las cargas siguientes (OO-7.1.1).
- **FR-002**: El sistema DEBE ejecutar automáticamente, cada día, la carga de datos desde el operativo (PostgreSQL) y desde el landing-zone hacia el warehouse, sin intervención manual (OO-7.1.2, resuelto como job automático — gap de rol "Analista de Datos", mismo patrón que 004/009).
- **FR-003**: La primera carga DEBE traer el histórico completo ya sembrado como carga base; las siguientes DEBEN ser incrementales, trayendo solo datos nuevos o modificados desde la última corrida exitosa (Edge Case).
- **FR-004**: El sistema DEBE permitir reprocesar una corrida fallida sin duplicar los datos ya cargados exitosamente antes de la falla.
- **FR-005**: El sistema NO DEBE permitir dos corridas de carga simultáneas sobre el mismo destino (Edge Case).
- **FR-006**: El Jefe de TI DEBE poder consultar el resultado de cualquier corrida (filas cargadas, filas con error, duración, fecha).
- **FR-007**: El sistema DEBE detectar registros que no cumplan reglas mínimas de calidad al cargarse (ej. referencias rotas, campos obligatorios vacíos) y reportarlos, sin bloquear el resto de la carga (OO-7.5.1).
- **FR-008**: El sistema DEBE mantener un registro de trazabilidad de cada corrida (origen, destino, cantidad de filas, resultado), consultable por el Jefe de TI (OO-7.5.1).
- **FR-009**: El Jefe de TI DEBE poder mantener el texto vigente de la política de gobierno de datos (calidad, trazabilidad, acceso).
- **FR-010**: El sistema DEBE conservar las versiones anteriores de la política de gobierno de datos.
- **FR-011**: El warehouse DEBE quedar disponible para que otras features (009, y opcionalmente 004) consulten agregaciones sin impactar el rendimiento de la base operativa.
- **FR-012**: El sistema DEBE permitir forzar manualmente una corrida de carga sin esperar la cadencia diaria, en entorno de desarrollo.

### Key Entities

- **Modelo de Datos Único**: esquema del warehouse (fact_venta + dimensiones), definido y mantenido por el Jefe de TI.
- **Corrida de Carga**: origen, destino, fecha, filas cargadas, filas con error, duración, resultado.
- **Registro de Calidad**: registro señalado por incumplir una regla mínima durante una corrida, sin bloquear el resto.
- **Política de Gobierno de Datos**: texto vigente, historial de versiones.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El Jefe de TI define el modelo de datos único una sola vez y sirve de base estable para todas las cargas siguientes.
- **SC-002**: La carga diaria se ejecuta sin intervención manual, salvo cuando falla.
- **SC-003**: Ningún registro con un problema de calidad detectado bloquea la carga del resto de los datos de esa corrida.
- **SC-004**: El Jefe de TI rastrea el origen y resultado de cualquier corrida sin consultar los logs de Airflow directamente.
- **SC-005**: La política de gobierno de datos vigente es consultable por el Jefe de TI sin depender de un documento externo al sistema.

## Assumptions

- **Boundary con 008-auth-administracion-sistema**: OO-7.5.2 (auditar accesos a los datos del sistema) es de 008, ya cerrada; esta feature toma solo OO-7.5.1 (calidad y trazabilidad del pipeline de datos), que 008 dejó pendiente explícitamente de evaluar aquí por tratarse del gobierno del pipeline de datos completo (ELT, warehouse), no solo de cuentas de acceso.
- **Gap de rol RBAC — "Analista de Datos" (OO-7.1.2)**: mismo patrón ya resuelto en 004 y en 009 — se convierte en job automático del sistema, dejando al Jefe de TI como actor humano real (monitoreo de cada corrida, FR-006).
- **Prerrequisito de 009-dashboards-multinivel** y, condicionalmente, de 004-pronostico-demanda (si su modelo llega a necesitar agregaciones del warehouse en vez de entrenar directo contra PostgreSQL) — ya documentado en `domain-context.md`; no se modifica el spec ya cerrado de 004.
- **En espera de implementación** (junto con 009) hasta retomar la capa táctica/estratégica — ya documentado en `constitution.md`/`domain-context.md`; esta especificación queda lista para cuando se retome.
- **Motores ya decididos desde el inicio del proyecto** (Principio III): PostgreSQL (operativo, no tocado por esta feature salvo como origen de lectura), MinIO `landing-zone` (raw del Extract), ClickHouse (warehouse), Airflow (orquestación ELT) — el detalle de DAGs/esquema exacto se define en `plan.md`/`research.md`, no en este documento.
