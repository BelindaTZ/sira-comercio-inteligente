# Feature Specification: Promociones Inteligentes

**Feature Branch**: `005-promociones-inteligentes`

**Created**: 2026-09-06

**Status**: Draft

**Input**: OT-3.5 (motor de recomendaciones por afinidad de compra para cross-sell) y OT-3.6 ya cerrado en 002 — más el gap de OT-2.2/OT-2.3 (clasificación ABC y liquidación de categoría C, sin feature dueña previa) incorporado aquí por decisión documentada en Assumptions.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Recomendación de cross-sell en el punto de venta a partir de afinidad de compra (Priority: P1) 🎯 MVP

El sistema calcula mensualmente, a partir del historial de ventas, qué productos se compran juntos con más frecuencia de lo esperado (afinidad de canasta). Cuando un cajero está cobrando una venta y el carrito contiene un producto con una afinidad fuerte conocida hacia otro producto que no está en el carrito, el sistema muestra esa recomendación en el punto de venta antes de cerrar la venta.

**Why this priority**: Es el escenario central narrado en el enunciado (cuajada + cerveza sin alcohol) y el corazón de "promociones inteligentes" — sin esto no hay MVP.

**Independent Test**: se puede probar generando el cálculo mensual de afinidad sobre datos históricos con un par de productos claramente correlacionado, y verificando que al simular un cobro con uno de esos productos en el carrito, el sistema muestra la recomendación del otro.

**Acceptance Scenarios**:

1. **Given** un historial de ventas con un par de productos A/B comprados juntos con una frecuencia significativamente mayor a la esperada por azar, **When** se ejecuta el cálculo mensual de afinidad, **Then** se genera una regla de asociación A→B (o B→A) con su soporte y confianza.
2. **Given** una regla de asociación vigente A→B, **When** un cajero está cobrando una venta que contiene A pero no B, **Then** el sistema muestra en el punto de venta la recomendación de ofrecer B.
3. **Given** el carrito ya contiene tanto A como B, **When** el cajero cobra la venta, **Then** el sistema no muestra ninguna recomendación redundante sobre ese par.
4. **Given** un conjunto de reglas de asociación calculadas, **When** el Jefe de Marketing las revisa, **Then** puede desactivar manualmente cualquier regla que considere no accionable para el negocio (p. ej. dos productos que solo coinciden por ser ambos de compra casi universal).

---

### User Story 2 - Cupón de descuento enviado proactivamente por afinidad no aprovechada (Priority: P2)

Cuando un cliente identificado (con tarjeta de fidelización) compra un producto que forma parte de una regla de afinidad fuerte, pero no lleva el producto complementario, el sistema puede enviarle automáticamente por correo electrónico un cupón de descuento para ese producto complementario, invitándolo a volver a buscarlo.

**Why this priority**: Extiende el valor de la afinidad de compra (US1) de la tienda hacia el cliente individual, replicando el escenario narrado del "descuento enviado al cliente" — depende de que ya existan reglas de afinidad (US1).

**Independent Test**: se puede probar con un cliente con consentimiento de datos aceptado que compra el producto A de una regla A→B sin llevar B, y verificando que recibe un cupón de descuento para B y que ese envío queda registrado.

**Acceptance Scenarios**:

1. **Given** un cliente con consentimiento de datos aceptado (LOPDP, FR-001 de 002) que compra el producto A de una regla de afinidad A→B vigente sin llevar B en la misma compra, **When** se cierra la venta, **Then** el sistema le envía automáticamente un cupón de descuento para B por correo electrónico y registra el envío.
2. **Given** un cliente sin consentimiento de datos aceptado, **When** compra un producto que dispara una regla de afinidad, **Then** el sistema NO le envía ningún cupón personalizado (mismo límite ya establecido en 002 para CLV/churn/campañas).
3. **Given** un cupón de afinidad ya enviado a un cliente por un par de productos específico, **When** el mismo cliente vuelve a comprar el producto A sin B dentro de un periodo de vigencia configurable, **Then** el sistema no le envía un cupón duplicado para el mismo par mientras el cupón anterior siga vigente.
4. **Given** un conjunto de cupones de afinidad enviados, **When** el Jefe de Marketing consulta su tasa de redención, **Then** puede verla por separado de la tasa de redención de los cupones por hito (cumpleaños/aniversario) de 002.

---

### User Story 3 - Clasificación por rotación y liquidación de productos de categoría C (Priority: P3)

El sistema clasifica automáticamente cada producto en A, B o C según su velocidad de rotación (venta reciente relativa a su categoría). Para los productos clasificados como C con rotación por debajo del umbral definido por el Jefe de Operaciones, el sistema genera semanalmente, por tienda, una lista de candidatos a liquidación; el Encargado de Tienda ejecuta la liquidación de los que decide promocionar localmente.

**Why this priority**: Resuelve el problema narrado del capital inmovilizado en stock de baja rotación — depende de tener historial de ventas suficiente, y es independiente de las historias de afinidad (US1/US2).

**Independent Test**: se puede probar sembrando un producto con ventas consistentemente bajas en una tienda, ejecutando la clasificación mensual, verificando que queda en categoría C, que aparece como candidato a liquidación esa semana en esa tienda, y que el Encargado de Tienda puede ejecutar (o descartar) esa liquidación.

**Acceptance Scenarios**:

1. **Given** un producto con rotación consistentemente baja en toda la red durante el periodo evaluado, **When** se ejecuta la clasificación mensual por rotación, **Then** el producto queda marcado como categoría C a nivel de catálogo (clasificación de red, no por tienda — la rotación local se evalúa aparte al generar candidatos a liquidación, Acceptance Scenario 2).
2. **Given** un producto categoría C cuya rotación en una tienda está por debajo del umbral configurado por el Jefe de Operaciones, **When** se ejecuta el cálculo semanal de candidatos a liquidación, **Then** aparece en la lista de candidatos de esa tienda con el descuento sugerido según la regla vigente.
3. **Given** una lista de candidatos a liquidación de la semana, **When** el Encargado de Tienda ejecuta la liquidación de uno de ellos, **Then** el producto queda registrado como en liquidación activa en esa tienda con su descuento y fecha de ejecución.
4. **Given** un producto ya con una propuesta de ajuste de precio pendiente de aprobación (FR de 003-precios-margenes), **When** el sistema calcula candidatos a liquidación, **Then** ese producto no se ofrece como candidato hasta que la propuesta de precio pendiente se resuelva (evita que dos mecanismos cambien el precio del mismo producto al mismo tiempo).

---

### User Story 4 - Registro de colocación de producto en anaquel destacado o mailer promocional (Priority: P4)

El Jefe de Marketing o el Encargado de Tienda registra qué producto se coloca en una ubicación destacada de anaquel o se incluye en un mailer/volante promocional, por tienda y por semana — información que además alimenta como variable explicativa el modelo de pronóstico de demanda (004) y sirve para medir si la colocación realmente incrementó las ventas del producto.

**Why this priority**: Es la de menor prioridad de la feature — es principalmente registro/trazabilidad, sin la cual las otras tres historias igual funcionan; no depende de ellas.

**Independent Test**: se puede probar registrando la colocación de un producto en una ubicación de anaquel para una tienda y semana específicas, y verificando que queda consultable junto con el efecto observado en sus ventas de esa semana frente a semanas sin colocación.

**Acceptance Scenarios**:

1. **Given** un producto y una tienda, **When** el Jefe de Marketing registra su colocación en una ubicación de anaquel destacado para una semana determinada, **Then** el registro queda disponible para consulta y para el modelo de pronóstico de demanda (004).
2. **Given** un producto colocado en anaquel destacado o mailer durante una semana, **When** se consultan sus ventas de esa semana frente a un periodo sin colocación, **Then** el sistema muestra ambas cifras lado a lado, sin calcular automáticamente una atribución causal (eso queda como lectura del usuario, no como conclusión del sistema).

---

### Edge Cases

- ¿Qué pasa si dos reglas de asociación distintas aplican al mismo producto que ya está en el carrito (recomienda más de un producto complementario)? El sistema muestra únicamente la de mayor confianza/soporte, no una lista larga que distraiga el cobro.
- ¿Qué pasa si no hay suficientes transacciones históricas para calcular una regla de asociación confiable entre dos productos? El par simplemente no genera regla — no se fuerza una recomendación con datos insuficientes (soporte/confianza mínimos configurables).
- ¿Qué pasa si un producto participa en una regla de afinidad pero fue descontinuado del catálogo? La regla que lo incluye deja de evaluarse para nuevas recomendaciones sin necesidad de borrarla del historial.
- ¿Qué pasa si el correo del cupón de afinidad no se entrega (SendGrid falla)? El cupón y su envío quedan igual registrados (Principio II, igual que en 002) aunque la notificación no haya llegado.
- ¿Qué pasa si un producto de categoría C nunca tiene compras en una tienda durante el periodo evaluado (rotación cero, no solo baja)? Se incluye igualmente como candidato a liquidación — rotación cero es el caso más claro de capital inmovilizado, no una excepción.
- ¿Qué pasa si el Encargado de Tienda no ejecuta ninguno de los candidatos a liquidación de una semana? La lista de esa semana simplemente no genera ninguna liquidación activa; la próxima semana se recalcula desde cero con los datos más recientes.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE calcular mensualmente, a partir del historial de ventas por ticket, reglas de asociación entre productos (afinidad de canasta) con al menos soporte y confianza mínimos configurables, descartando pares sin suficiente evidencia histórica (OO-3.5.1).
- **FR-002**: El Jefe de Marketing DEBE poder revisar el conjunto de reglas de asociación vigentes y desactivar manualmente cualquiera que considere no accionable para el negocio (OO-3.5.1).
- **FR-003**: El sistema DEBE mostrar, durante el cobro de una venta en el punto de venta, una recomendación de cross-sell cuando el carrito contenga un producto con una regla de asociación vigente hacia un producto que no esté ya en el carrito (OO-3.5.2).
- **FR-004**: Cuando el carrito ya contiene ambos productos de una regla de asociación, el sistema NO DEBE mostrar una recomendación redundante sobre ese par (Edge Case).
- **FR-005**: Si más de una regla de asociación aplica al mismo producto en el carrito, el sistema DEBE mostrar únicamente la recomendación de mayor confianza/soporte (Edge Case).
- **FR-006**: El sistema DEBE enviar automáticamente, por correo electrónico, un cupón de descuento al cliente identificado que compre el producto origen de una regla de afinidad vigente sin llevar el producto complementario en la misma compra — únicamente si el cliente tiene el consentimiento de tratamiento de datos aceptado (FR-001 de 002) (OO-3.5.3, nueva — ver Assumptions).
- **FR-007**: El sistema NO DEBE enviar un cupón de afinidad duplicado al mismo cliente para el mismo par de productos mientras un cupón anterior para ese par siga vigente (Edge Case).
- **FR-008**: El sistema DEBE permitir consultar la tasa de redención de cupones de afinidad, de forma separada de la tasa de redención de cupones por hito (cumpleaños/aniversario) de 002 (OO-3.5.3).
- **FR-009**: El sistema DEBE clasificar automáticamente, de forma mensual, cada producto en categoría A, B o C según su velocidad de rotación relativa dentro de su categoría de producto, a nivel de catálogo de red (no por tienda — reutiliza el campo `clasificacion_abc` ya reservado en `productos` desde 001) (OO-2.2.1, ejecutado como job automático — ver Assumptions).
- **FR-010**: El Jefe de Operaciones DEBE poder revisar mensualmente el listado de productos que cambiaron de clasificación ABC (OO-2.2.2).
- **FR-011**: El Jefe de Operaciones DEBE poder definir y actualizar las reglas automáticas de liquidación de categoría C (umbral de rotación mínima y descuento sugerido) que aplican a toda la red (OO-2.3.1).
- **FR-012**: El sistema DEBE generar semanalmente, por tienda, la lista de productos categoría C cuya rotación en esa tienda está por debajo del umbral vigente, como candidatos a liquidación (OO-2.3.1).
- **FR-013**: El sistema NO DEBE incluir como candidato a liquidación un producto que ya tenga una propuesta de ajuste de precio pendiente de aprobación (003-precios-margenes) (Edge Case).
- **FR-014**: El Encargado de Tienda DEBE poder ejecutar la liquidación de un producto candidato de su tienda, quedando registrada con su descuento aplicado y fecha de ejecución (OO-2.3.2).
- **FR-015**: El Jefe de Marketing o el Encargado de Tienda DEBEN poder registrar la colocación de un producto en una ubicación de anaquel destacado o en un mailer promocional, por tienda y semana, reutilizando el catálogo de ubicaciones ya sembrado del dataset.
- **FR-016**: El sistema DEBE permitir consultar, para un producto colocado en anaquel destacado o mailer durante una semana, sus ventas de esa semana frente a un periodo de referencia sin colocación, sin calcular una atribución causal automática (Acceptance Scenario 2 de User Story 4).

### Key Entities

- **Regla de Asociación (Afinidad)**: par (o conjunto) de productos, soporte, confianza, fecha de cálculo, estado (activa/desactivada manualmente por Jefe de Marketing).
- **Cupón de Afinidad Enviado**: cliente, producto complementario ofrecido, regla de asociación que lo originó, fecha de envío, vigencia, si fue redimido.
- **Clasificación por Rotación (ABC)**: producto, tienda, clasificación (A/B/C), fecha de cálculo — ya reservado como campo en el catálogo de producto desde 001, sin una feature que lo calculara hasta ahora.
- **Regla de Liquidación de Categoría C**: umbral de rotación mínima, descuento sugerido, vigente para toda la red, definida por Jefe de Operaciones.
- **Candidato de Liquidación**: producto, tienda, semana, descuento sugerido, estado (candidato/ejecutado/descartado), fecha de ejecución si aplica.
- **Colocación Promocional**: producto, tienda, semana, tipo (anaquel destacado / mailer), ubicación específica — reutiliza el catálogo de ubicaciones ya sembrado del dataset.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El sistema calcula reglas de asociación mensualmente sin intervención manual, y un cajero ve la recomendación de cross-sell en el punto de venta sin percibir demora alguna al cobrar.
- **SC-002**: Un cliente con consentimiento aceptado que compra el producto origen de una regla de afinidad sin el complementario recibe su cupón de descuento el mismo día de la compra.
- **SC-003**: El Jefe de Operaciones puede ver, cada mes, qué productos cambiaron de clasificación ABC sin tener que calcular manualmente rotación alguna.
- **SC-004**: Cada semana, cada tienda cuenta con una lista de candidatos a liquidación de categoría C generada automáticamente, sin que el Encargado de Tienda tenga que identificar manualmente el stock de baja rotación.
- **SC-005**: El Jefe de Marketing puede comparar, para cualquier producto con colocación promocional registrada, sus ventas de esa semana frente a un periodo sin colocación, en la misma pantalla.

## Assumptions

- **Alcance de esta feature dentro de OE-3 (Marketing/CRM)**: 005 cubre OT-3.5 completo (motor de recomendaciones por afinidad + cross-sell en punto de venta). OT-3.6 (campañas por hito: cumpleaños/aniversario) ya fue cerrado en 002-clientes-fidelizacion — esta feature reutiliza su infraestructura de cupones/campañas (`campanas`, `cupon_enviado`, `cupon_redimido`) para el nuevo tipo de cupón por afinidad, sin duplicar tablas.
- **Gap de BSC incorporado — nueva OO-3.5.3**: el enunciado original narra explícitamente el escenario de un descuento enviado proactivamente al cliente cuando se detecta una compra de un producto sin su complementario habitual ("cuajada... le mandan un descuento al móvil"), pero ni `bsc-objetivos-estrategicos-tacticos.md` ni `oo-objetivos-operativos.md` tenían un Objetivo Operativo que lo cubriera — solo existía OO-3.5.1 (revisar reglas, mensual) y OO-3.5.2 (mostrar en punto de venta, diario). Se incorpora **OO-3.5.3 (Sistema): Enviar cupón de descuento personalizado cuando se detecta una oportunidad de afinidad no aprovechada — por evento**, bajo el mismo OT-3.5 ya existente (no se crea un OT nuevo). El BSC/OO se documentan explícitamente como sujetos a este tipo de ajuste (ver `bsc-objetivos-estrategicos-tacticos.md`, "Historial de cambios post-cierre inicial", precedente de OT-6.5 agregado en la feature 001).
- **Gap de feature dueña — OT-2.2 (clasificación ABC) y OT-2.3 (liquidación de categoría C) se incorporan a 005**: ambos OT existen en el BSC desde el inicio y el campo `clasificacion_abc` ya está reservado en la tabla `productos` desde 001, pero ninguna feature los había tomado como propios (001 solo declaró el campo, sin una FR que lo calculara). Se asignan a 005 porque OO-2.3.2 literalmente describe la acción como "ejecutar liquidación/**promoción** local" — encaja directamente en el propósito de "promociones inteligentes" de esta feature, y porque la liquidación de categoría C es una forma de promoción táctica (descuento temporal y local), distinta de la política de precio permanente de 003. **OT-2.4 (límites de stock máximo) y OT-2.5 (coordinación de stock entre tiendas) quedan explícitamente FUERA de esta feature** — no son mecanismos de promoción, son de capacidad de almacenamiento y logística entre tiendas; permanecen como gap sin feature dueña, pendiente de una decisión futura del usuario.
- **Mismo patrón de resolución de rol RBAC sin actor propio, ya usado en 002/003/004**: OO-2.2.1 asigna la ejecución de la clasificación ABC a un actor "Analista de Operaciones" sin rol RBAC sembrado (los 10 roles existentes no lo incluyen). Se resuelve igual que OO-7.2.1/OO-7.2.3 en 004: la clasificación ABC se convierte en un job automático del sistema (sin actor humano que la "ejecute"), dejando a Jefe_Operaciones como el actor humano real vía OO-2.2.2 (ya existente: "revisar productos que cambiaron de categoría").
- **Boundary con 003-precios-margenes**: la liquidación de categoría C (FR-011 a FR-014) es un descuento temporal y local por tienda, gestionado por Jefe_Operaciones/Encargado_Tienda — no reemplaza ni se ejecuta a través del motor de pricing dinámico de 003 (Jefe_Comercial, ajuste de `precio_base` a nivel de red). Un producto con una propuesta de ajuste de precio de 003 pendiente de aprobación no se ofrece como candidato a liquidación simultáneamente (FR-013), para evitar que dos mecanismos independientes cambien el precio efectivo del mismo producto al mismo tiempo.
- **Boundary con 004-pronostico-demanda**: la colocación de producto en anaquel/mailer (User Story 4) reutiliza exactamente las mismas tablas (`display_locations`, `mailer_locations`, `promociones`) que 004 ya consume como variable explicativa exógena de su modelo de pronóstico — 005 es quien las llena (las crea/gestiona); 004 solo las lee. No se duplica ninguna tabla entre ambas features.
- **Boundary con 002-clientes-fidelizacion**: el cupón de afinidad (User Story 2) reutiliza la infraestructura de `campanas`/`cupon_enviado`/`cupon_redimido` ya construida en 002, como un nuevo tipo de campaña/evento disparado por comportamiento de compra (afinidad no aprovechada) en vez de por fecha de hito (cumpleaños/aniversario) — mismo control de consentimiento de datos (LOPDP) ya establecido en 002.
- **Sin nueva integración externa**: el cálculo de reglas de asociación corre localmente sobre las tablas operativas de PostgreSQL (`ventas`, `venta_detalle`), sin depender de ClickHouse/Airflow (en pausa, 010) — la elección de librería/algoritmo específico (p. ej. reglas de asociación tipo Apriori/FP-Growth) se documenta en `research.md` de esta feature, no en el spec.
- **Sin acceso directo del cliente al sistema**: el cupón de afinidad se envía únicamente por correo electrónico (mismo canal ya aprobado en 002/constitución) — SIRA sigue sin ningún canal de autoservicio para el cliente final (decisión de alcance ya documentada en `domain-context.md`).
