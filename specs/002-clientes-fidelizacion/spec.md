# Feature Specification: Clientes y Fidelización (CLV, Churn, Campañas por Hitos)

**Feature Branch**: `002-clientes-fidelizacion`

**Created**: 2026-09-05

**Status**: Draft

**Input**: Perfil de cliente, cálculo de CLV compuesto (frecuencia + margen, no gasto bruto), segmentación por nivel de valor, detección de riesgo de fuga con ciclo de compra individual, campañas automáticas por hito (cumpleaños/aniversario) y medición de uplift real de campañas de reactivación (OE-3 Marketing/CRM, OT-3.1 a OT-3.4 y OT-3.6, más OO-B.1 a B.3).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar y mantener el perfil del cliente (Priority: P1)

Un cajero o encargado de tienda registra un cliente nuevo (nombre, email, fecha de nacimiento) al momento de una venta o por solicitud propia, puede actualizar sus datos de contacto después, y puede darlo de baja/anonimizarlo si el cliente lo solicita, sin perder la integridad de su historial de compras.

**Why this priority**: Es la base de todo lo demás en esta feature (CLV, churn, campañas dependen de que exista un cliente) y de la feature 001, que ya asume poder vincular un cliente existente a una venta (OO-B.1 a B.3).

**Independent Test**: Puede probarse por completo registrando, actualizando y dando de baja un cliente, sin depender de que existan cálculos de CLV o churn todavía.

**Acceptance Scenarios**:

1. **Given** un cliente nuevo con email no registrado antes, **When** el cajero lo registra con nombre, email y fecha de nacimiento, **Then** el cliente queda creado y disponible para vincularse a ventas.
2. **Given** un email ya registrado por otro cliente, **When** se intenta registrar un cliente nuevo con ese mismo email, **Then** el sistema rechaza el registro e informa el conflicto.
5. **Given** un cliente afiliado que da su número de cédula en el punto de venta, **When** el cajero lo busca por ese número, **Then** el sistema lo encuentra y permite vincularlo a la venta en curso, sin necesidad de que el cliente recuerde el email con el que se registró (Ronda 5).
3. **Given** un cliente existente, **When** se actualizan sus datos de contacto, **Then** el historial de compras y cálculos previos (CLV, churn) asociados a ese cliente no se alteran.
4. **Given** un cliente que solicita darse de baja, **When** el encargado ejecuta la baja, **Then** el cliente queda marcado inactivo y sus datos personales (nombre, email, teléfono, fecha de nacimiento) se anonimizan, conservando únicamente el identificador para no romper la integridad de sus ventas históricas.

---

### User Story 2 - Calcular CLV compuesto y segmentar por nivel de valor (Priority: P2)

El sistema calcula semanalmente, para cada cliente con historial de compras, un CLV compuesto por frecuencia de compra y margen real generado (no el gasto bruto acumulado), y lo asigna a un nivel de fidelización según umbrales configurables por el Jefe de Marketing.

**Why this priority**: Resuelve directamente el problema narrado de que "el gasto total no refleja el valor real del cliente" (OT-3.1, OT-3.2) y es el insumo que usan las otras historias (churn, campañas) para priorizar a quién atender primero.

**Independent Test**: Puede probarse generando ventas con distintos patrones (compras frecuentes de bajo monto vs. una compra grande única) y verificando que el CLV y el nivel asignado reflejan frecuencia+margen, no el monto total gastado.

**Acceptance Scenarios**:

1. **Given** dos clientes con el mismo gasto total pero uno compra frecuentemente productos de mayor margen y el otro rara vez productos de bajo margen, **When** se calcula el CLV semanal, **Then** el cliente con mayor frecuencia y margen obtiene un CLV mayor, aunque el gasto total sea igual.
2. **Given** el CLV calculado de un cliente, **When** supera el umbral de un nivel de fidelización superior, **Then** el sistema lo reclasifica automáticamente a ese nivel.
3. **Given** el Jefe de Marketing, **When** ajusta los umbrales de segmentación, **Then** los clientes se reclasifican según los nuevos umbrales en el siguiente cálculo, no de forma retroactiva sobre cálculos ya hechos.

---

### User Story 3 - Detectar riesgo de fuga (churn) con ciclo individual (Priority: P3)

El sistema calcula el ciclo de compra habitual de cada cliente activo (cada cuántos días suele volver) y marca como en riesgo de fuga a quien se desvía significativamente de su propio ciclo — no a quien simplemente no compra en un umbral fijo de 30 días para todos.

**Why this priority**: Resuelve el problema narrado de "el cliente fiel se va y no te enteras" y su matiz explícito: un umbral fijo de inactividad es incorrecto porque cada cliente tiene su propio ritmo de compra (OT-3.3).

**Independent Test**: Puede probarse con dos clientes de frecuencias de compra muy distintas (uno compra cada 3 días, otro cada 45) y verificando que cada uno se marca en riesgo solo al desviarse de SU propio ciclo, no de un umbral global.

**Acceptance Scenarios**:

1. **Given** un cliente cuyo ciclo habitual de compra es cada 5 días, **When** pasan 15 días sin una compra suya, **Then** el sistema lo marca en riesgo de fuga, aunque 15 días sea menos que "30 días" para otro cliente.
2. **Given** un cliente cuyo ciclo habitual es cada 40 días, **When** pasan 35 días sin comprar, **Then** el sistema NO lo marca en riesgo de fuga, porque sigue dentro de su ciclo normal.
3. **Given** la lista de clientes en riesgo de fuga, **When** el Jefe de Marketing la revisa, **Then** puede decidir lanzar o no una campaña de reactivación sobre ese cliente.

---

### User Story 4 - Campañas automáticas por hito (cumpleaños/aniversario) (Priority: P4)

El sistema detecta diariamente qué clientes cumplen años o aniversario de registro ese día, les envía automáticamente un cupón de descuento por correo electrónico, y permite revisar la tasa de redención de esos cupones.

**Why this priority**: Resuelve directamente el escenario narrado del cupón de cumpleaños como mecanismo de fidelización (OT-3.6).

**Independent Test**: Puede probarse configurando la fecha de nacimiento de un cliente de prueba como la fecha actual y verificando que recibe el cupón automáticamente sin intervención manual.

**Acceptance Scenarios**:

1. **Given** un cliente activo cuyo cumpleaños es hoy, **When** se ejecuta el job diario, **Then** se genera su evento de cumpleaños y se envía automáticamente un cupón por correo.
2. **Given** un cliente activo cuyo aniversario de registro es hoy, **When** se ejecuta el job diario, **Then** ocurre lo mismo que en el escenario 1 para ese hito.
3. **Given** un cliente dado de baja/anonimizado, **When** su fecha de nacimiento coincide con hoy, **Then** el sistema NO le envía ningún cupón.
4. **Given** un conjunto de cupones enviados por hito, **When** el Jefe de Marketing consulta la tasa de redención, **Then** ve el porcentaje de cupones efectivamente usados frente a los enviados.

---

### User Story 5 - Medir el uplift real de campañas de reactivación (Priority: P5)

Antes de lanzar una campaña de reactivación a clientes en riesgo de fuga, el Jefe de Marketing define un grupo de control (clientes en riesgo que NO reciben el incentivo). Al cierre de la campaña, el sistema compara la tasa de retorno del grupo tratado contra el grupo de control para calcular el uplift real, no solo la tasa de redención del cupón.

**Why this priority**: Resuelve directamente el problema narrado de que "un descuento de reactivación puede traer a un cliente que igual iba a volver" — sin grupo de control no se puede distinguir el efecto real de la campaña de lo que habría pasado de todos modos. Es la historia más avanzada, depende de que US3 (churn) ya identifique a quién dirigir la campaña.

**Independent Test**: Puede probarse definiendo una campaña piloto sobre un conjunto de clientes en riesgo, dividiéndolos en tratado/control, y verificando que el cálculo de uplift al cierre compara ambos grupos, no solo cuenta redenciones.

**Acceptance Scenarios**:

1. **Given** una campaña de reactivación piloto sobre clientes en riesgo de fuga, **When** el Jefe de Marketing la configura, **Then** el sistema exige definir qué parte de esos clientes queda como grupo de control antes de poder enviarla.
2. **Given** una campaña ya cerrada con grupo de control definido, **When** se calcula el uplift, **Then** el resultado compara la tasa de retorno del grupo tratado contra la del grupo de control, no solo la tasa de redención de cupones.
3. **Given** el uplift calculado de una campaña piloto, **When** el Jefe de Marketing lo revisa, **Then** puede aprobar escalarla a toda la base de clientes en riesgo o descartarla.

### Edge Cases

- ¿Qué pasa con un cliente nuevo sin historial de compras aún? No tiene CLV ni churn calculable — queda sin nivel de fidelización asignado hasta su primera compra, no se le asigna el nivel más bajo por defecto (evita castigar a un cliente recién registrado).
- ¿Qué pasa si un cliente anonimizado por baja (US1) vuelve a comprar con un email nuevo? Se trata como un cliente nuevo — el sistema no reconstruye ni vincula al perfil anonimizado anterior, es una decisión de alcance, no un error.
- ¿Qué pasa si se intenta enviar una campaña de reactivación sin grupo de control definido? El sistema lo impide (FR-017): sin grupo de control no hay forma de calcular uplift al cierre.
- ¿Qué pasa si el correo del cupón de cumpleaños no se entrega (SendGrid falla)? El evento y el cupón quedan igual registrados en el sistema (Principio II — el registro de negocio no depende de un servicio externo de terceros), aunque la notificación no haya llegado.
- ¿Qué pasa si un cliente rechaza el consentimiento de tratamiento de datos al registrarse? Queda registrado solo con datos básicos (nombre, email, fecha de nacimiento) — el sistema NO le calcula CLV ni riesgo de fuga, ni lo incluye en campañas segmentadas ni en cupones automáticos por hito, hasta que otorgue el consentimiento.
- ¿Qué pasa si un cliente revoca su consentimiento después de tener historial de CLV/churn ya calculado? El historial pasado no se borra ni se recalcula (Principio II, registro real); simplemente no se genera ningún cálculo nuevo mientras el consentimiento esté revocado, y deja de aparecer en campañas futuras — igual que un cliente que nunca lo otorgó.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir registrar un cliente nuevo con nombre, email, fecha de nacimiento, número de cédula/RUC (documento de identidad, opcional) y su consentimiento explícito de tratamiento de datos personales para fines de fidelización (aceptado o rechazado, con fecha de captura), rechazando el registro únicamente si el email ya existe, o si el documento de identidad ya existe cuando se proporciona (OO-B.1, cumplimiento LOPDP; Ronda 5). Si el consentimiento es rechazado, el cliente queda registrado solo con datos básicos, fuera del alcance de FR-005, FR-009/FR-010 y de toda campaña o cupón segmentado.
- **FR-002**: El sistema DEBE permitir actualizar los datos de contacto de un cliente existente, incluyendo revocar o volver a otorgar su consentimiento de tratamiento de datos (con nueva fecha de captura), sin alterar su historial de ventas ni sus cálculos de CLV/churn ya calculados (OO-B.2). Revocar el consentimiento excluye al cliente de todo cálculo futuro de CLV/churn y de toda campaña o cupón segmentado (mismo gating de FR-001), sin anonimizar sus demás datos ni requerir la baja completa (FR-003).
- **FR-003**: El sistema DEBE permitir dar de baja a un cliente a solicitud, marcándolo inactivo y anonimizando sus datos personales (nombre, email, teléfono, fecha de nacimiento), conservando su identificador para no romper la integridad referencial de sus ventas históricas (OO-B.3).
- **FR-004**: El sistema DEBE permitir registrar datos demográficos opcionales del cliente (edad, nivel de ingreso, tipo de vivienda, estado civil, tamaño y composición del hogar) sin que sean obligatorios para el alta.
- **FR-005**: El sistema DEBE calcular semanalmente, para cada cliente con historial de compras, un CLV compuesto que combine frecuencia de compra y margen real generado — nunca el gasto bruto acumulado como única variable (OO-3.1.3, OT-3.1).
- **FR-006**: El sistema DEBE asignar automáticamente a cada cliente un nivel de fidelización según su CLV más reciente frente a umbrales configurables (OT-3.1).
- **FR-007**: El sistema DEBE permitir al Jefe de Marketing definir y ajustar los umbrales de CLV de cada nivel de fidelización (OO-3.2.1).
- **FR-008**: El sistema DEBE reclasificar automáticamente a cada cliente cuando su CLV recalculado cruza el umbral de otro nivel (OO-3.2.2).
- **FR-009**: El sistema DEBE calcular el ciclo de compra individual de cada cliente activo (intervalo típico entre sus propias compras), no aplicar un umbral fijo igual para todos los clientes (OO-3.3.1, OT-3.3).
- **FR-010**: El sistema DEBE clasificar a un cliente en un nivel de severidad de riesgo de fuga cuando el tiempo transcurrido desde su última compra exceda su propio ciclo de compra calculado: **en_riesgo** cuando lo excede significativamente, e **inactivo** cuando lo excede de forma prolongada sin que el cliente haya vuelto a comprar. Los multiplicadores exactos de cada umbral (sobre el ciclo propio del cliente) son una decisión técnica de `research.md`/`plan.md`, mismo patrón que la fórmula de CLV (FR-005).
- **FR-011**: El sistema DEBE permitir al Jefe de Marketing consultar la lista de clientes en riesgo de fuga, filtrable por nivel de severidad (en_riesgo / inactivo), y decidir una acción sobre cada uno (OO-3.3.2).
- **FR-012**: El sistema DEBE generar diariamente un evento de cumpleaños o de aniversario de registro para cada cliente activo cuya fecha correspondiente sea ese día (OO-3.6.1).
- **FR-013**: Al generarse un evento de cumpleaños o aniversario, el sistema DEBE enviar automáticamente un cupón de descuento al cliente por correo electrónico, sin intervención manual (OO-3.6.1).
- **FR-014**: El sistema DEBE permitir consultar la tasa de redención de cupones enviados por hito, agrupada por tipo de evento (OO-3.6.2).
- **FR-015**: El sistema DEBE permitir registrar la redención de un cupón por parte de un cliente.
- **FR-016**: El sistema DEBE permitir crear una campaña de reactivación dirigida a un subconjunto de clientes en riesgo de fuga, ya sea del nivel en_riesgo o del nivel inactivo (OO-3.4.1).
- **FR-017**: Al crear una campaña de reactivación, el sistema DEBE exigir la definición de un grupo de control (clientes en riesgo que no reciben el incentivo) antes de permitir su envío (OO-3.4.1).
- **FR-018**: Al cierre de una campaña de reactivación, el sistema DEBE calcular su uplift comparando la tasa de retorno del grupo tratado contra la del grupo de control — no únicamente la tasa de redención de cupones (OO-3.4.2).
- **FR-019**: El sistema DEBE permitir al Jefe de Marketing aprobar la escalación de una campaña piloto a toda la base de clientes en riesgo, o descartarla, en base al uplift calculado (OO-3.4.3).

### Key Entities *(include if feature involves data)*

- **Cliente**: identificador, nombre, email, teléfono, fecha de nacimiento, fecha de registro, estado (activo/inactivo-anonimizado), consentimiento de tratamiento de datos (aceptado/rechazado, capturado en el alta y revocable/otorgable de nuevo después vía actualización de perfil) y fecha de captura del consentimiento (se actualiza en cada cambio).
- **Datos Demográficos**: edad, nivel de ingreso, tipo de vivienda, estado civil, tamaño y composición del hogar — todos opcionales, asociados 1:1 a un cliente.
- **Nivel de Fidelización**: nombre del nivel, umbral mínimo de CLV para pertenecer a él.
- **CLV (histórico)**: cliente, score de CLV, nivel asignado, fecha de cálculo — un registro por cliente y fecha de cálculo, conserva histórico (no sobrescribe).
- **Score de Churn**: cliente, score de riesgo (0 a 1), nivel de severidad (en_riesgo / inactivo), ciclo de compra calculado en días, fecha de cálculo — histórico.
- **Campaña**: identificador, tipo, fecha de inicio, fecha de fin.
- **Cupón**: identificador de cupón, producto asociado, campaña a la que pertenece.
- **Redención de Cupón**: cliente, cupón, campaña, fecha de redención.
- **Evento de Cliente**: cliente, tipo de evento (cumpleaños/aniversario de registro), fecha.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Todo cliente con al menos una compra registrada tiene un CLV calculado y un nivel de fidelización asignado antes de que termine la semana de esa compra.
- **SC-002**: El cálculo de riesgo de fuga no usa ningún umbral de días igual para todos los clientes — cada marca de riesgo se basa en el ciclo de compra propio del cliente evaluado.
- **SC-003**: El 100% de los clientes activos que cumplen años o aniversario de registro reciben su cupón automático ese mismo día, sin que nadie tenga que generarlo manualmente.
- **SC-004**: El 100% de las campañas de reactivación medidas por uplift tienen un grupo de control definido antes de su envío — ninguna se mide solo por tasa de redención.
- **SC-005**: El Jefe de Marketing puede revisar la lista de clientes en riesgo de fuga sin calcular manualmente el ciclo de compra de ninguno.
- **SC-006**: El 100% de los clientes registrados tiene su consentimiento de tratamiento de datos capturado explícitamente (aceptado o rechazado) al momento del alta, y puede revocarlo u otorgarlo de nuevo en cualquier momento posterior sin necesidad de darse de baja.
- **SC-007**: Los clientes en riesgo de fuga quedan clasificados en al menos dos niveles de severidad (en_riesgo / inactivo), y toda campaña de reactivación puede dirigirse a cualquiera de los dos niveles.
- **SC-008**: Un cajero puede localizar y vincular a un cliente afiliado a una venta en curso dando únicamente su número de cédula, sin depender de que recuerde o dicte su email (Ronda 5).

## Assumptions

- La fórmula exacta y los pesos del CLV compuesto (cuánto pesa la frecuencia frente al margen) son una decisión técnica de `research.md`/`plan.md`, no de este documento — aquí se fija como requisito duro que NUNCA sea solo el gasto bruto acumulado (FR-005).
- El motor de recomendaciones por afinidad de compra/cross-sell (OT-3.5) pertenece a la feature 005-promociones-inteligentes, junto con la colocación de producto en anaquel/mailer (`display_locations`, `mailer_locations`, `promociones`) — esta feature no lo implementa.
- El cálculo de uplift usa una comparación simple de tasas de retorno entre grupo tratado y grupo de control (Principio VIII, KISS); no se exige una prueba de significancia estadística formal en esta versión.
- La vinculación de un cliente a una venta (household_id en `ventas`) ya está resuelta en la feature 001-core-ventas-inventario; esta feature no reimplementa el flujo de venta, solo provee el maestro de cliente y sus cálculos.
- La autenticación, los roles (Jefe de Marketing, Cajero, Encargado de Tienda) y los permisos de acceso a estas pantallas provienen de la feature 008-auth-administracion-sistema.
- Un cliente anonimizado por baja (FR-003) que vuelve a comprar se trata como un cliente nuevo si usa un email distinto; el sistema no intenta reidentificarlo con su perfil anterior — es una decisión de alcance, no una limitación técnica a resolver.
- El envío de correo (cupón de cumpleaños, notificaciones de campaña) usa SendGrid, ya aprobado en la constitución; una falla de entrega no bloquea ni revierte el registro del evento/cupón en el sistema (Principio II).
- El consentimiento de tratamiento de datos (FR-001) es la base legal del perfilado de cliente (LOPDP Ecuador): un cliente sin consentimiento aceptado nunca entra a los cálculos de CLV (FR-005), riesgo de fuga (FR-009/FR-010), ni a campañas o cupones segmentados — puede seguir comprando con registro básico, pero fuera de todo perfilado.
- Los umbrales exactos que distinguen en_riesgo de inactivo (ej. múltiplos del ciclo de compra propio del cliente) se definen en `research.md`/`plan.md`; aquí solo se fija como requisito duro que existan al menos dos niveles de severidad, no un único estado binario (FR-010).
- Los clientes sembrados desde el dataset base (histórico/sintético usado para pruebas) quedan con `consentimiento_datos = true` por defecto (grandfathering de datos ya existentes al momento de introducir FR-001); el flujo de registro nuevo siempre captura el consentimiento explícitamente, sin valor por defecto.
- `domain-context.md` (OO-3.4.2) asignaba conceptualmente el cálculo de uplift a un actor "Analista de Marketing"; no existe un rol RBAC propio para eso (`01_operativo_postgres.sql` solo siembra `Jefe_Marketing`) y no se agrega uno nuevo solo para esta acción (Principio VIII, KISS) — el mismo `Jefe_Marketing` calcula el uplift (FR-018) y decide la escalación (FR-019). Decisión de alcance confirmada por el usuario, `domain-context.md` ya actualizado.
- **OT-7.3 (post-cierre, decisión de cobertura)**: la auditoría completa de cobertura OT/OO (Ronda 10 de 001) detectó que OT-7.3 (OE-7 TI y Datos: "Desarrollar modelos de score de churn y CLV disponibles para negocio", actor nominal Analista de Datos) nunca se había cruzado explícitamente con esta feature, aunque el cálculo semanal de CLV (FR-005) y la clasificación de riesgo de fuga (FR-009/FR-010) ya satisfacen la intención de negocio de ese OT desde el cierre inicial. Se decide, con el usuario, declarar OT-7.3 satisfecho por esta feature: el cálculo es determinístico por fórmula (no un modelo entrenado por separado por TI), ejecutado como job automático del "Sistema" y revisado por Jefe_Marketing — mismo patrón de "sin rol RBAC propio, resuelto sin agregar un actor nuevo" ya aplicado a OO-3.4.2 arriba. No se crea ninguna feature ni tarea nueva para OT-7.3; `domain-context.md` y `oo-objetivos-operativos.md` quedan actualizados con esta traza.
- **Ronda 5 (post-inicio de implementación, identificación en punto de venta)**: el usuario señaló, antes de implementar User Story 1, que un programa de fidelización real normalmente identifica al cliente afiliado por su cédula en caja, no por email/nombre (más rápido, sin ambigüedad de escritura, y el dataset base — Dunnhumby, panel de hogares de EE.UU. — nunca tuvo este concepto). Se agrega `documento_identidad` (cédula/RUC) como campo **opcional** del perfil de cliente (FR-001): único cuando se proporciona, pero el alta sigue sin exigirlo (no todo cliente da su cédula al registrarse, igual que hoy no todos dan datos demográficos, FR-004). `GET /api/clientes` (`search`) ahora también compara contra este campo. La feature 001 (venta) no se modifica: solo consume el `household_id` que el cajero ya resolvió en 002, sin importar si la búsqueda fue por nombre, email o cédula. Al revisar esto se confirmó que `PuntoDeVentaPage.vue` (001) nunca llegó a construir un buscador de cliente propio — FR-008 de 001 dejó `household_id?` opcional en `POST /api/ventas` desde el inicio, pero la UI de búsqueda dependía de un endpoint que 002 todavía no existía; esa pieza se construye ahora como parte de 002 (T053), integrada dentro del módulo `pos/` de 001 sin reabrir su spec.
