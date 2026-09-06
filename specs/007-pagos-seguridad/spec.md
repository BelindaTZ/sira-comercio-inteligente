# Feature Specification: Pagos y Seguridad

**Feature Branch**: `007-pagos-seguridad`

**Created**: 2026-09-06

**Status**: Draft

**Input**: OT-4.1 completo (OE-4 Comercial/Experiencia de Cliente — OO-4.1.1 verificación diaria de disponibilidad de datáfonos, OO-4.1.2 alta y aprobación de nuevos medios de pago) más una nueva OO bajo OT-6.3 (OE-6 Finanzas/Seguridad, ya existente) para cubrir el KPI secundario de OE-6 "Incidentes de seguridad de pago" — sin feature dueña previa, distinto de los incidentes de fraude interno de caja que cubre 006 — y la política de seguridad de pagos como documento de referencia, reforzando el requisito no funcional de seguridad narrado explícitamente en el enunciado original ("datáfono viejo sin actualizar... tarjetas clonadas... demandas y multas"). Incorpora también OT-4.2 (OE-4, reducir el tiempo de cobro 20%, sin feature dueña previa) a pedido explícito del usuario — comparte con OT-4.1 la naturaleza de "experiencia de cobro en el punto de venta" y no encaja en ninguna otra feature de las ya cerradas ni de las restantes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Verificación diaria de disponibilidad de datáfonos (Priority: P1) 🎯 MVP

El Encargado de Tienda verifica cada día que los datáfonos de su tienda funcionan, y marca como fuera de servicio cualquiera que no responda — sin esperar a la certificación trimestral de conformidad de seguridad (006) para saber que un datáfono simplemente no está operando.

**Why this priority**: Es la acción diaria más básica de OT-4.1 y la única de esta feature con impacto inmediato en el cobro — un datáfono caído sin marcar deja a un cajero intentando cobrar con tarjeta sin saber por qué falla.

**Independent Test**: se puede probar marcando un datáfono como fuera de servicio, verificando que queda visible en ese estado, y luego restableciéndolo para verificar que vuelve a estar disponible.

**Acceptance Scenarios**:

1. **Given** un datáfono que no responde durante la verificación diaria, **When** el Encargado de Tienda lo marca como fuera de servicio, **Then** el sistema lo refleja de inmediato como no disponible para cobro.
2. **Given** un datáfono previamente marcado fuera de servicio que vuelve a funcionar, **When** el Encargado de Tienda lo marca como restablecido, **Then** el sistema lo vuelve a evaluar contra el estándar de seguridad vigente (006) antes de marcarlo operativo — si aún no cumple el estándar, queda como no conforme en lugar de operativo.
3. **Given** una caja cuyo datáfono está marcado fuera de servicio, **When** un cajero intenta cobrar con tarjeta en esa caja, **Then** el sistema lo advierte antes de intentar procesar el cobro, sin bloquear el cobro con otro medio de pago (efectivo, transferencia) en la misma caja.

---

### User Story 2 - Alta y aprobación de nuevos medios de pago (Priority: P2)

El Jefe de TI da de alta un nuevo medio de pago (por ejemplo, una nueva billetera digital) dejando constancia de su aprobación, y puede dar de baja uno existente sin borrar el historial de ventas ya registradas con él.

**Why this priority**: Resuelve el segundo objetivo operativo de OT-4.1 — sin aprobación explícita, cualquier medio de pago quedaría disponible en el punto de venta sin control alguno, contradiciendo el requisito de seguridad de la feature.

**Independent Test**: se puede probar dando de alta un medio de pago nuevo y verificando que aparece disponible para selección en el punto de venta; y dando de baja uno existente y verificando que deja de estar disponible para ventas nuevas sin afectar las ya registradas.

**Acceptance Scenarios**:

1. **Given** un medio de pago nuevo que el Jefe de TI decide aprobar, **When** lo da de alta, **Then** queda disponible para selección en el punto de venta de todas las tiendas.
2. **Given** un medio de pago existente que deja de estar aprobado, **When** el Jefe de TI lo da de baja, **Then** deja de estar disponible para ventas nuevas, sin alterar ninguna venta ya registrada con ese medio de pago.
3. **Given** un medio de pago no aprobado o dado de baja, **When** se intenta seleccionar en el punto de venta, **Then** el sistema no lo ofrece como opción.

---

### User Story 3 - Registro y seguimiento de incidentes de seguridad de pago (Priority: P3)

El Jefe de TI registra un incidente de seguridad de pago cuando detecta actividad sospechosa asociada a un datáfono (por ejemplo, un reporte de una tarjeta clonada o una brecha potencial) — distinto de un incidente de fraude interno de caja, que sigue siendo responsabilidad de 006. El Jefe de Finanzas puede consultar cuántos incidentes de este tipo hubo en un periodo.

**Why this priority**: Cubre directamente el escenario narrado del datáfono viejo que expone al negocio a clonación de tarjetas y a demandas — sin este registro, el KPI secundario de OE-6 ("Incidentes de seguridad de pago") no tiene ninguna fuente de datos real.

**Independent Test**: se puede probar registrando un incidente de seguridad de pago asociado a un datáfono, verificando que sigue su ciclo hasta cerrarse, y que el conteo del periodo lo refleja.

**Acceptance Scenarios**:

1. **Given** actividad sospechosa asociada a un datáfono, **When** el Jefe de TI registra un incidente de seguridad de pago, **Then** queda asociado al datáfono involucrado con su descripción, en estado abierto.
2. **Given** un incidente de seguridad de pago abierto, **When** el Jefe de TI avanza la investigación, **Then** puede transicionarlo a en investigación y finalmente a cerrado, dejando constancia de quién y cuándo lo cambió.
3. **Given** varios incidentes de seguridad de pago registrados en un periodo, **When** el Jefe de Finanzas consulta el conteo del periodo, **Then** lo obtiene sin tener que consolidar manualmente distintas fuentes.
4. **Given** un datáfono con un incidente de fraude interno de caja abierto en 006, **When** también se detecta un incidente de seguridad de pago sobre el mismo datáfono, **Then** ambos incidentes existen de forma independiente, sin fusionarse — tienen causas raíz distintas.

---

### User Story 4 - Política de seguridad de pagos como documento de referencia (Priority: P4)

El Jefe de TI mantiene el texto vigente de la política de seguridad de pagos (lineamientos de seguridad de datos de tarjeta, PCI-style), consultable por cualquier Jefe de Finanzas o Encargado de Tienda.

**Why this priority**: Da cuerpo documental al requisito no funcional de seguridad narrado explícitamente en el enunciado — la prioridad más baja porque no bloquea ninguna operación, es un documento de referencia igual que el protocolo de escalamiento de 006.

**Independent Test**: se puede probar definiendo el texto de la política y verificando que cualquier Encargado de Tienda puede consultarlo íntegro.

**Acceptance Scenarios**:

1. **Given** la política de seguridad de pagos vigente, **When** un Jefe de Finanzas o Encargado de Tienda la consulta, **Then** puede ver su texto completo sin depender de un documento externo al sistema.
2. **Given** una actualización de la política, **When** el Jefe de TI la registra, **Then** la versión anterior queda disponible para saber bajo cuál se abrió un incidente en curso (mismo criterio que el protocolo de escalamiento de 006).

---

### User Story 5 - Medición y revisión del tiempo de cobro (Priority: P5)

El sistema registra cuánto dura cada venta desde que se inicia hasta que se confirma. El Encargado de Tienda revisa semanalmente el tiempo promedio de cobro por caja de su tienda, y el Jefe Comercial lo revisa mensualmente por tienda a nivel de toda la red para definir acciones donde el tiempo de cobro sea alto.

**Why this priority**: Cubre OT-4.2, sin feature dueña previa y explícitamente incorporado a esta feature a pedido del usuario — es la prioridad más baja porque es una métrica de gestión, sin ningún impacto en si una venta se puede o no completar.

**Independent Test**: se puede probar registrando una venta en vivo de principio a fin, y verificando que su duración queda calculada y disponible tanto en la revisión semanal por caja como en la mensual por tienda.

**Acceptance Scenarios**:

1. **Given** una venta que se inicia y se confirma, **When** se guarda, **Then** el sistema calcula su duración total sin que nadie la calcule a mano.
2. **Given** varias ventas confirmadas de una caja durante la semana, **When** el Encargado de Tienda consulta el tiempo promedio de cobro de esa caja, **Then** lo obtiene sin calcularlo manualmente venta por venta.
3. **Given** varias tiendas con su tiempo promedio de cobro de un mes, **When** el Jefe Comercial las consulta, **Then** puede compararlas entre sí para decidir dónde actuar.
4. **Given** una venta anulada, **When** se calcula el tiempo promedio de cobro, **Then** esa venta queda excluida del cálculo (Edge Case).

---

### Edge Cases

- ¿Qué pasa si todos los datáfonos de una tienda quedan fuera de servicio al mismo tiempo? El cobro con tarjeta no es posible en esa tienda hasta restablecer al menos uno; el sistema no bloquea el cobro con otros medios de pago (efectivo, transferencia bancaria) en ninguna caja de esa tienda.
- ¿Qué pasa si un datáfono no conforme (marcado `requiere_actualizacion` por 006) además deja de funcionar físicamente? El Encargado de Tienda lo marca fuera de servicio igual que cualquier otro — la falta de conformidad y la falta de funcionamiento son dos problemas distintos que pueden coexistir.
- ¿Qué pasa si se intenta dar de baja el único medio de pago electrónico aprobado de la red? El sistema lo permite (no impone un mínimo de medios de pago activos) — es una decisión de negocio, no una restricción del sistema.
- ¿Qué pasa si la política de seguridad de pagos cambia mientras un incidente de seguridad de pago sigue abierto? El incidente no se ve afectado; la versión anterior de la política sigue siendo consultable para saber cuál estaba vigente cuando se abrió el caso.
- ¿Qué pasa si un incidente de seguridad de pago no logra identificar un datáfono específico (por ejemplo, un reporte genérico de un banco sobre varias transacciones)? El sistema permite registrar el incidente sin un datáfono asociado, dejando la descripción como única evidencia.
- ¿Qué pasa con el tiempo de cobro de las ventas ya sembradas desde el dataset Dunnhumby? No se calcula — el dataset no trae un momento de inicio de venta distinto del de confirmación, y el sistema no fabrica esa duración (Principio VII); la medición de tiempo de cobro solo aplica a ventas registradas en vivo desde que esta feature está disponible.
- ¿Qué pasa si una venta se anula antes del cierre de caja? Queda excluida del cálculo de tiempo de cobro — una venta anulada no representa una experiencia de cobro real completada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El Encargado de Tienda DEBE poder marcar un datáfono de su tienda como fuera de servicio cuando detecta que no funciona (OO-4.1.1).
- **FR-002**: El Encargado de Tienda DEBE poder marcar un datáfono previamente fuera de servicio como restablecido (OO-4.1.1).
- **FR-003**: Al restablecer un datáfono, el sistema DEBE volver a evaluarlo contra el estándar de seguridad vigente (006) antes de marcarlo operativo — si no cumple, queda como no conforme en lugar de operativo (Edge Case).
- **FR-004**: El sistema DEBE advertir al Cajero antes de intentar un cobro con tarjeta en una caja cuyo datáfono está marcado fuera de servicio, sin bloquear el cobro con otro medio de pago en esa misma caja (Edge Case).
- **FR-005**: El Jefe de TI DEBE poder dar de alta un nuevo medio de pago dejando constancia de su aprobación (OO-4.1.2).
- **FR-006**: El Jefe de TI DEBE poder dar de baja un medio de pago existente, sin alterar ninguna venta ya registrada con ese medio de pago (OO-4.1.2).
- **FR-007**: El sistema NO DEBE ofrecer en el punto de venta ningún medio de pago que no esté aprobado o que haya sido dado de baja.
- **FR-008**: El Jefe de TI DEBE poder registrar un incidente de seguridad de pago asociado a un datáfono (o sin datáfono asociado, Edge Case), con su descripción.
- **FR-009**: El sistema DEBE permitir transicionar un incidente de seguridad de pago entre abierto, en investigación y cerrado, dejando constancia de quién y cuándo lo cambió.
- **FR-010**: Un incidente de seguridad de pago y un incidente de fraude interno de caja (006) sobre el mismo datáfono DEBEN poder coexistir de forma independiente, sin fusionarse (Edge Case).
- **FR-011**: El Jefe de Finanzas DEBE poder consultar el número de incidentes de seguridad de pago de un periodo determinado.
- **FR-012**: El Jefe de TI DEBE poder mantener el texto vigente de la política de seguridad de pagos.
- **FR-013**: Cualquier Jefe de Finanzas o Encargado de Tienda DEBE poder consultar la política de seguridad de pagos vigente.
- **FR-014**: El sistema DEBE conservar las versiones anteriores de la política de seguridad de pagos, para saber cuál estaba vigente cuando se abrió un incidente en curso.
- **FR-015**: El sistema DEBE registrar el momento en que una venta se confirma, distinto del momento en que se inició, para poder calcular la duración total del cobro (OT-4.2) — solo para ventas registradas en vivo, no para las ya sembradas del dataset (Edge Case).
- **FR-016**: El Encargado de Tienda DEBE poder consultar el tiempo promedio de cobro por caja de su tienda en un periodo semanal (OO-4.2.2).
- **FR-017**: El Jefe Comercial DEBE poder consultar el tiempo promedio de cobro por tienda a nivel de toda la red, mensualmente (OO-4.2.3).
- **FR-018**: El sistema NO DEBE incluir una venta anulada en el cálculo del tiempo promedio de cobro (Edge Case).

### Key Entities

- **Estado Operativo de Datáfono**: extiende el estado ya existente del datáfono (006) con la disponibilidad diaria (operativo/fuera de servicio), distinta de su conformidad de seguridad (006, trimestral).
- **Medio de Pago**: catálogo de medios de pago con su condición de aprobado/dado de baja, quién lo aprobó y cuándo.
- **Incidente de Seguridad de Pago**: datáfono involucrado (opcional), descripción, estado (abierto/en investigación/cerrado), fecha, distinto del Incidente de Fraude de 006.
- **Política de Seguridad de Pagos**: texto vigente, historial de versiones, definida por Jefe de TI.
- **Duración de Cobro**: momento de inicio y de confirmación de una venta registrada en vivo, usada para calcular el tiempo de cobro por caja/tienda — no aplica a ventas del dataset sembrado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un Encargado de Tienda puede marcar y restablecer la disponibilidad de un datáfono sin intervención de TI.
- **SC-002**: Ningún medio de pago no aprobado o dado de baja aparece disponible para selección en el punto de venta.
- **SC-003**: Un incidente de seguridad de pago puede seguir su ciclo completo (abierto → en investigación → cerrado) consultable en cualquier momento.
- **SC-004**: El Jefe de Finanzas puede reportar el número de incidentes de seguridad de pago de un periodo sin consolidar manualmente distintas fuentes.
- **SC-005**: La política de seguridad de pagos vigente es consultable por cualquier Jefe de Finanzas o Encargado de Tienda sin depender de un documento externo al sistema.
- **SC-006**: El Encargado de Tienda y el Jefe Comercial pueden ver el tiempo promedio de cobro (por caja y por tienda, respectivamente) sin calcularlo manualmente venta por venta.

## Assumptions

- **Gap de BSC incorporado — nueva OO-6.3.3**: `oo-objetivos-operativos.md` no tenía ningún Objetivo Operativo que produjera el KPI secundario de OE-6 "Incidentes de seguridad de pago" — OT-6.3 (certificación de datáfonos, 006) solo cubre la conformidad preventiva del firmware, no el registro de un incidente de seguridad ya ocurrido (ej. sospecha de clonación de tarjeta), y OT-6.2/OT-6.4 (006) cubren específicamente el fraude interno de caja, con `incidentes_fraude` requiriendo un empleado involucrado — un incidente de seguridad de pago no necesariamente implica a un empleado. Se agrega **OO-6.3.3 (Jefe de TI): Registrar y dar seguimiento a un incidente de seguridad de pago cuando se detecta actividad sospechosa asociada a un datáfono — por evento**, bajo el OT-6.3 ya existente (mismo criterio que OO-3.5.3 en 005: sin crear un OT nuevo). Documentado aquí y pendiente de reflejar en `bsc-objetivos-estrategicos-tacticos.md`/`oo-objetivos-operativos.md` del proyecto una vez el usuario apruebe este spec.
- **OT-4.2 incorporado a pedido explícito del usuario**: quedaba sin feature dueña (verificado por grep sin resultado en los 6 spec.md ya cerrados) y no encajaba de forma obvia en ninguna de las features restantes (008 es auth/administración, 009/010 son dashboards/plataforma de datos, en espera) — el usuario decidió incorporarlo aquí en vez de dejarlo como gap, junto a OT-4.1, por compartir la naturaleza de "experiencia de cobro en el punto de venta" (misma OE-4). OO-4.2.1 ("Cajero: registrar venta usando el flujo rápido del sistema") ya está satisfecho estructuralmente por el flujo de venta de 001 (FR-001 a FR-008) — no existe un "flujo lento" alternativo con el que contrastar, así que no requiere un FR nuevo en esta feature; solo OO-4.2.2 y OO-4.2.3 (medir y revisar el tiempo de cobro) necesitaban requisitos nuevos (FR-015 a FR-018).
- **Anclaje al dataset real para el tiempo de cobro (FR-015)**: las ~1.47M ventas ya sembradas desde Dunnhumby no tienen un momento de inicio de venta distinto del de confirmación — el sistema no fabrica esa duración para no violar el Principio VII; la medición de tiempo de cobro aplica solo prospectivamente, a ventas registradas en vivo desde que esta feature esté disponible (mismo criterio de "cold start" ya usado en 004 para el pronóstico de demanda).
- **Boundary con 006-caja-mermas-fraude**: el estado de conformidad de seguridad de un datáfono (`activo`/`requiere_actualizacion`, evaluado trimestralmente por Jefe de TI) sigue siendo de 006; esta feature agrega la disponibilidad operativa diaria (`fuera_servicio`, evaluada por Encargado de Tienda) sobre el mismo dato, sin duplicar la tabla. El Incidente de Seguridad de Pago (esta feature) y el Incidente de Fraude (006) son entidades distintas e independientes — un incidente de seguridad de pago no requiere un empleado involucrado, mientras que un incidente de fraude siempre lo requiere.
- **Boundary con 001-core-ventas-inventario**: 001 ya cubre la selección de medio de pago en el flujo de cobro (FR-002 de 001, OT-4.1) y la simulación de la pasarela de pago (FR-003/FR-030 de 001); esta feature no reconstruye ese flujo, solo restringe qué medios de pago están disponibles para seleccionar (FR-007), agrega una advertencia previa cuando el datáfono de la caja está fuera de servicio (FR-004), y agrega el registro del momento de confirmación de la venta para medir su duración (FR-015) — extensiones puntuales del flujo de cobro ya existente, no un nuevo flujo de venta.
- **Sin gap de rol RBAC**: los actores de esta feature (Encargado_Tienda, Jefe_TI, Jefe_Finanzas, Jefe_Comercial) ya tienen rol propio sembrado en el esquema — tercera feature consecutiva (junto con 006 y la mayor parte de 007) sin ninguna resolución de gap de rol.
- **Gap identificado y dejado fuera de esta feature — OT-2.4/OT-2.5**: siguen sin feature dueña (conversado con el usuario durante 006), sin relación con "pagos y seguridad" — no se resuelven aquí.
- **La política de seguridad de pagos (OO-6.3.3 relacionado) es un texto de referencia versionado**, mismo criterio de simplicidad ya usado para el protocolo de escalamiento de 006 (Principio VIII) — no un motor de cumplimiento normativo automatizado.
