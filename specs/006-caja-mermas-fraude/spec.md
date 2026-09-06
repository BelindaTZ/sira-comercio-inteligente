# Feature Specification: Caja, Mermas y Fraude

**Feature Branch**: `006-caja-mermas-fraude`

**Created**: 2026-09-06

**Status**: Draft

**Input**: OT-6.1 a OT-6.4 completos (OE-6 Finanzas/Seguridad — domain-context.md §8: "006 solo cubre el cuadre de caja de ventas, no las cuentas por pagar a proveedor" ya cerradas en OT-6.5/001) más OT-5.5 (umbral de merma aceptable, sin feature dueña previa — 001 ya cubre OT-5.3/OT-5.4, registro y validación de mermas, pero no su seguimiento agregado contra un umbral).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cuadre de caja horario con detección automática de diferencias (Priority: P1) 🎯 MVP

Cada hora, el cajero cuadra su caja registrando el total físico contado; el sistema ya conoce el total esperado a partir de las ventas registradas y calcula automáticamente la diferencia, sin que nadie tenga que hacer la resta a mano. El Encargado de Tienda valida el cuadre de todas las cajas de su tienda.

**Why this priority**: Es el escenario central narrado en el enunciado (cobrar 5 y registrar 3) — sin cuadre horario con diferencia calculada automáticamente, ningún otro mecanismo de esta feature tiene datos sobre los cuales operar.

**Independent Test**: se puede probar abriendo una caja con un fondo inicial, registrando ventas, cerrando el cuadre horario con un total físico distinto del esperado, y verificando que el sistema calcula la diferencia sin intervención manual y que el Encargado de Tienda puede verla.

**Acceptance Scenarios**:

1. **Given** un cajero que inicia su turno, **When** registra la apertura de su caja con el fondo inicial, **Then** el sistema lo deja disponible para cobrar ventas.
2. **Given** una caja con ventas registradas durante la última hora, **When** el cajero registra su cuadre con el total físico contado, **Then** el sistema calcula automáticamente la diferencia entre el total esperado y el total registrado, sin que el cajero la calcule.
3. **Given** un cuadre con diferencia distinta de cero, **When** se guarda el cuadre, **Then** el sistema lo marca automáticamente para revisión, sin esperar a que alguien lo detecte manualmente.
4. **Given** todas las cajas de una tienda ya cuadradas en una hora determinada, **When** el Encargado de Tienda las revisa, **Then** puede ver el estado de cuadre de todas las cajas de su tienda en una sola consulta.

---

### User Story 2 - Certificación y actualización de datáfonos (Priority: P2)

El Jefe de TI mantiene un inventario del estado y la versión de firmware de cada datáfono de la red, identifica cuáles no cumplen el estándar de seguridad vigente, y coordina y registra su actualización o reemplazo.

**Why this priority**: Resuelve directamente el escenario narrado del datáfono viejo sin actualizar que expone al negocio a clonación de tarjetas y a demandas — es un control preventivo de seguridad de pagos, independiente del cuadre de caja (US1).

**Independent Test**: se puede probar registrando un datáfono con una versión de firmware desactualizada, verificando que el sistema lo identifica como no conforme, y registrando su actualización para verificar que deja de aparecer como no conforme.

**Acceptance Scenarios**:

1. **Given** el inventario de datáfonos de la red, **When** el Jefe de TI lo consulta, **Then** ve el modelo, la versión de firmware y la fecha de última actualización de cada uno.
2. **Given** un datáfono cuya versión de firmware no cumple el estándar de seguridad vigente, **When** el Jefe de TI consulta el inventario, **Then** ese datáfono aparece identificado como no conforme.
3. **Given** un datáfono no conforme, **When** el Jefe de TI registra su actualización o reemplazo, **Then** el datáfono deja de aparecer como no conforme y queda registrada la fecha de la resolución.

---

### User Story 3 - Análisis mensual de patrones de diferencias y escalamiento (Priority: P3)

El Jefe de Finanzas revisa mensualmente un reporte de diferencias de cuadre de caja agrupado por cajero y por turno, además de los ajustes de inventario con una diferencia negativa inusualmente grande (el caso que 001-core-ventas-inventario reservó explícitamente para esta feature). Cuando detecta un patrón sospechoso, escala el caso abriendo un incidente de fraude sobre el empleado involucrado.

**Why this priority**: Convierte los datos ya generados por US1 (y por el registro de ajustes de inventario de 001) en una señal accionable — depende de que exista historial de cuadres (US1), por eso va después.

**Independent Test**: se puede probar sembrando varios cuadres de un mismo cajero con diferencias repetidas en la misma dirección, consultando el reporte mensual agrupado por cajero/turno, y verificando que el Jefe de Finanzas puede abrir un incidente de fraude directamente desde ahí.

**Acceptance Scenarios**:

1. **Given** un mes con cuadres de caja de varios cajeros y turnos, **When** el Jefe de Finanzas consulta el reporte mensual, **Then** ve las diferencias agrupadas por cajero y por turno, no solo el total agregado de la tienda.
2. **Given** un ajuste de inventario (001) con una diferencia negativa que supera el umbral configurado, **When** el Jefe de Finanzas consulta el mismo reporte, **Then** ese ajuste aparece señalado junto con los patrones de caja, no en un reporte separado.
3. **Given** un patrón identificado como sospechoso, **When** el Jefe de Finanzas decide escalarlo, **Then** el sistema abre un incidente de fraude con el empleado involucrado y la evidencia que lo originó.

---

### User Story 4 - Aplicación del protocolo de escalamiento sobre un incidente de fraude (Priority: P4)

El Jefe de Finanzas mantiene el texto vigente del protocolo a seguir ante un caso de fraude confirmado, consultable por cualquier Encargado de Tienda. Cuando un incidente de fraude está abierto (originado en US3 o registrado directamente), el Encargado de Tienda aplica el protocolo, registra las acciones tomadas, y el incidente puede cerrarse.

**Why this priority**: Es la continuación natural de US3 (qué se hace con un incidente ya abierto) — depende de que exista al menos un incidente de fraude, generado por US3 o registrado manualmente.

**Independent Test**: se puede probar con un incidente de fraude en estado abierto, consultando el protocolo vigente, registrando las acciones tomadas por el Encargado de Tienda, y verificando que el incidente puede transicionar a en revisión y luego a cerrado con constancia de quién y cuándo lo cambió.

**Acceptance Scenarios**:

1. **Given** el protocolo de escalamiento vigente, **When** un Encargado de Tienda lo consulta, **Then** puede ver su texto completo sin depender de una política verbal o externa al sistema.
2. **Given** un incidente de fraude en estado abierto, **When** el Encargado de Tienda aplica el protocolo, **Then** puede registrar las acciones tomadas y el incidente pasa a en revisión.
3. **Given** un incidente en revisión ya investigado, **When** el Jefe de Finanzas lo cierra, **Then** queda registrado el resultado (fraude confirmado o descartado) sin acusar al empleado si la investigación no lo confirma.
4. **Given** un incidente de fraude sobre un empleado que ya fue dado de baja del sistema, **When** se consulta o se avanza ese incidente, **Then** el sistema permite seguir su curso normalmente, sin bloquearlo por la baja del empleado.

---

### User Story 5 - Umbral de merma aceptable y seguimiento semanal (Priority: P5)

El Jefe de Operaciones define, por categoría de producto, el umbral de merma aceptable. Cada semana, el Encargado de Tienda puede ver qué porcentaje de merma acumulada lleva su tienda frente a ese umbral, por categoría.

**Why this priority**: Resuelve el problema narrado de las mermas comiéndose hasta el 20% de la ganancia anual, pero es un objetivo de gestión de mediano plazo, no una señal de fraude en curso — la prioridad más baja de esta feature.

**Independent Test**: se puede probar definiendo un umbral para una categoría, registrando mermas de esa categoría en una tienda (ya registradas por 001), y verificando que el Encargado de Tienda puede ver el porcentaje acumulado frente al umbral esa semana.

**Acceptance Scenarios**:

1. **Given** una categoría de producto, **When** el Jefe de Operaciones define su umbral de merma aceptable, **Then** el umbral queda disponible para todas las tiendas de la red.
2. **Given** mermas ya registradas de una categoría en una tienda durante el periodo evaluado, **When** el Encargado de Tienda consulta el seguimiento semanal, **Then** ve el porcentaje de merma acumulada frente al umbral definido para esa categoría.
3. **Given** una tienda cuya merma acumulada de una categoría supera el umbral definido, **When** se genera el seguimiento semanal, **Then** el sistema lo muestra como alerta de gestión, sin bloquear ninguna venta, recepción de mercadería ni ningún otro flujo operativo.

---

### Edge Cases

- ¿Qué pasa si un cuadre horario no tiene ninguna diferencia? Se registra igual como cuadre normal, sin generar ninguna marca de revisión.
- ¿Qué pasa si dos cuadres consecutivos de la misma caja tienen diferencia en sentidos opuestos (una vez sobra, otra vez falta)? Ambos quedan registrados igual — es el análisis de patrones (User Story 3) quien decide si eso es sospechoso, no el cuadre individual.
- ¿Qué pasa si un datáfono marcado como no conforme sigue en uso mientras se coordina su reemplazo? El sistema no bloquea su uso automáticamente (la coordinación de reemplazo es un proceso, no instantáneo), pero mantiene visible su estado no conforme mientras tanto.
- ¿Qué pasa si la investigación de un incidente de fraude concluye que fue un error de conteo, no fraude real? El Jefe de Finanzas cierra el incidente dejando constancia de esa conclusión, sin que el sistema lo trate como una sanción confirmada contra el empleado.
- ¿Qué pasa si un incidente de fraude involucra a un empleado que ya fue dado de baja? El incidente sigue su curso normalmente — la baja del empleado no lo bloquea ni lo cierra automáticamente.
- ¿Qué pasa si la merma acumulada de una categoría supera el umbral a mitad de año? No bloquea ninguna operación — es una alerta de gestión, no una restricción dura (mismo criterio que las alertas de reposición de 001).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir al Cajero registrar la apertura de su caja con el fondo inicial al comenzar su turno (OO-B.17).
- **FR-002**: El sistema DEBE permitir al Cajero registrar el cuadre de su caja cada hora, indicando el total físico contado (OO-6.1.1).
- **FR-003**: El sistema DEBE calcular automáticamente la diferencia entre el total esperado (a partir de las ventas ya registradas) y el total físico contado en cada cuadre, sin depender de que el cajero la calcule (OO-6.1.3).
- **FR-004**: El sistema DEBE marcar automáticamente cualquier cuadre con diferencia distinta de cero para revisión, en el momento en que se registra (OO-6.1.3, Edge Case).
- **FR-005**: El Encargado de Tienda DEBE poder validar el cuadre horario de todas las cajas de su tienda en una sola consulta (OO-6.1.2).
- **FR-006**: El Jefe de TI DEBE poder registrar y actualizar el inventario de datáfonos por caja, incluyendo modelo, versión de firmware y fecha de última actualización (OO-6.3.1).
- **FR-007**: El sistema DEBE identificar automáticamente los datáfonos cuyo estado no cumpla el estándar de seguridad de pago vigente (OO-6.3.1).
- **FR-008**: El Jefe de TI DEBE poder registrar la actualización o el reemplazo de un datáfono no conforme, incluyendo la fecha en que quedó resuelto (OO-6.3.2).
- **FR-009**: El Jefe de Finanzas DEBE poder consultar mensualmente un reporte de diferencias de cuadre de caja agrupado por cajero y por turno (OO-6.2.1).
- **FR-010**: El sistema DEBE incluir en ese mismo reporte los ajustes de inventario (001) cuya diferencia negativa supere un umbral configurable — extensión del caso que 001-core-ventas-inventario reservó explícitamente para esta feature.
- **FR-011**: El Jefe de Finanzas DEBE poder escalar un patrón sospechoso abriendo un incidente de fraude sobre el empleado involucrado, con la evidencia que lo originó (OO-6.2.2).
- **FR-012**: El Jefe de Finanzas DEBE poder mantener el texto vigente del protocolo de escalamiento ante fraude confirmado (OO-6.4.1).
- **FR-013**: Cualquier Encargado de Tienda DEBE poder consultar el protocolo de escalamiento vigente (OO-6.4.1).
- **FR-014**: El Encargado de Tienda DEBE poder aplicar el protocolo sobre un incidente de fraude abierto, registrando las acciones tomadas (OO-6.4.2).
- **FR-015**: El sistema DEBE permitir transicionar un incidente de fraude entre abierto, en revisión y cerrado, dejando constancia de quién y cuándo lo cambió de estado.
- **FR-016**: El sistema NO DEBE impedir que un incidente de fraude siga su curso si el empleado involucrado ya fue dado de baja (Edge Case).
- **FR-017**: El Jefe de Operaciones DEBE poder definir el umbral de merma aceptable por categoría de producto, vigente para toda la red (OO-5.5.1).
- **FR-018**: El Encargado de Tienda DEBE poder consultar semanalmente el porcentaje de merma acumulada de su tienda frente al umbral definido, por categoría (OO-5.5.2).
- **FR-019**: El sistema NO DEBE bloquear ninguna operación cuando la merma acumulada de una categoría supere su umbral — solo mostrarlo como alerta de gestión (Edge Case).

### Key Entities

- **Apertura de Caja**: caja, cajero, fondo inicial, fecha y hora — ya reservada en el esquema desde 001, sin feature que la usara hasta ahora.
- **Cuadre de Caja**: caja, cajero, total esperado, total físico registrado, diferencia (calculada), fecha y hora — misma tabla ya reservada.
- **Datáfono**: caja asignada, modelo, versión de firmware, fecha de última actualización, estado de conformidad.
- **Incidente de Fraude**: empleado involucrado, cuadre de caja de origen (si aplica), descripción/evidencia, estado (abierto/en revisión/cerrado), fecha.
- **Protocolo de Escalamiento**: texto vigente, fecha de última actualización, definido por Jefe de Finanzas.
- **Umbral de Merma por Categoría**: categoría de producto, porcentaje de merma aceptable, definido por Jefe de Operaciones.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un cajero puede cuadrar su caja cada hora sin calcular manualmente ninguna diferencia.
- **SC-002**: El Encargado de Tienda ve el estado de cuadre de todas las cajas de su tienda en una sola consulta, sin revisar caja por caja.
- **SC-003**: El Jefe de TI puede identificar qué datáfonos no cumplen el estándar de seguridad sin inventariarlos manualmente uno por uno cada vez que lo necesita.
- **SC-004**: El Jefe de Finanzas puede ver el patrón de diferencias de un cajero específico a lo largo de un mes completo en una sola consulta, incluyendo ajustes de inventario inusuales.
- **SC-005**: Un incidente de fraude puede seguir su ciclo completo (abierto → en revisión → cerrado) quedando su historial consultable en cualquier momento.
- **SC-006**: El Encargado de Tienda puede ver, cada semana, si la merma acumulada de una categoría está por encima o por debajo del umbral definido, sin calcularlo manualmente.

## Assumptions

- **Boundary con 001-core-ventas-inventario**: 001 ya registra la venta y su medio de pago (no el cuadre de la caja física), ya registra y valida mermas por causa (OT-5.4), y ya registra ajustes de inventario con su diferencia calculada — esta feature no reconstruye ninguno de esos flujos, solo los consume/analiza. Las tablas `apertura_caja`, `cierre_caja`, `datafonos` e `incidentes_fraude` ya existen en el esquema desde 001, reservadas sin que ninguna feature las llenara hasta ahora.
- **OT-5.5 asignado a esta feature**: 001 cubre OT-5.3 (rotación FIFO) y OT-5.4 (registro/validación de merma por causa), pero no OT-5.5 (umbral de merma aceptable y su seguimiento) — se incorpora aquí porque el nombre mismo de la feature ("mermas") lo indica y porque no encaja en ninguna otra feature restante.
- **Sin gap de rol RBAC**: a diferencia de 002, 003, 004 y 005, todos los actores de OT-6.1 a OT-6.4 y OT-5.5 (Cajero, Encargado_Tienda, Jefe_Finanzas, Jefe_TI, Jefe_Operaciones) ya tienen rol RBAC propio sembrado en el esquema — no se requiere ninguna resolución de gap en esta feature.
- **Escalamiento a RRHH (OO-6.2.2) sin módulo operativo propio de RRHH**: OE-8 (RRHH) es estratégico/táctico en este proyecto, sin una feature operativa dueña de un flujo de tickets propio — "escalar a RRHH" se modela como abrir el incidente de fraude con el empleado identificado (visible para cualquier rol con acceso al módulo Finanzas), no como un flujo de aprobación separado hacia un sistema de RRHH que no existe en el alcance de este proyecto.
- **El protocolo de escalamiento (OO-6.4.1) es un texto de referencia versionado**, no un motor de flujo de aprobación multi-paso — mantiene el alcance simple (Principio VIII) mientras cumple el requisito de que exista un documento consultable dentro del sistema, no solo una política verbal o externa.
- **El umbral de merma (OT-5.5) es un objetivo de gestión, no una restricción dura**: superarlo nunca bloquea una venta, una recepción de mercadería ni ningún otro flujo operativo — mismo criterio ya usado para las alertas de reposición de 001.
- **OT-2.4 (límites de stock máximo) y OT-2.5 (coordinación de stock entre tiendas) permanecen fuera de esta feature** — no son mecanismos de caja, mermas ni fraude; siguen sin feature dueña, ya conversado con el usuario fuera de este documento.
