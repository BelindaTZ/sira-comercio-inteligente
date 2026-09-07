# Feature Specification: Core de Ventas e Inventario (Punto de Venta, Catálogo y Reposición)

**Feature Branch**: `001-core-ventas-inventario`

**Created**: 2026-09-04

**Status**: Draft

**Input**: User description: "Registrar ventas en el punto de venta, gestionar el catálogo de productos, controlar el inventario por lotes bajo FIFO, generar alertas de reposición y detectar quiebres de stock, además de sugerir órdenes de compra y procesar devoluciones — el núcleo transaccional operativo de SIRA para Marzú Retail Group."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Registrar una venta y cobrarla (Priority: P1)

Un cajero atiende a un cliente en el punto de venta: escanea o busca cada producto, el sistema calcula el total en tiempo real, el cajero selecciona el medio de pago (efectivo, tarjeta débito/crédito, transferencia o billetera digital) y confirma la venta. El sistema genera el comprobante y descuenta el inventario correspondiente de inmediato.

**Why this priority**: Es el corazón transaccional de todo el sistema (OO-B.12) y la única funcionalidad sin la cual no existe negocio que registrar, sea cual sea el resto de features. Sin esto no hay dato operativo real que alimente ningún nivel táctico o estratégico.

**Independent Test**: Puede probarse por completo registrando una venta de varios productos con distintos medios de pago y verificando que el total, el comprobante y el descuento de stock son correctos, sin depender de ninguna otra feature.

**Acceptance Scenarios**:

1. **Given** un producto con stock disponible, **When** el cajero lo agrega a la venta por su código de barras y confirma el pago en efectivo, **Then** la venta queda registrada, se genera el comprobante en PDF y el stock disponible del producto disminuye en la cantidad vendida.
2. **Given** una venta con productos de distintos medios de pago posibles, **When** el cajero elige pagar con tarjeta de crédito, **Then** el sistema muestra una simulación visual del paso de la tarjeta por el datáfono, procesa el cobro a través de la pasarela de pago electrónico aprobada (modo de prueba) sin que el cajero capture ni vea los datos de la tarjeta, y solo confirma la venta si el cobro es aceptado.
3. **Given** una venta con pago por tarjeta en curso, **When** el banco o la tarjeta rechaza el cobro (fondos insuficientes, tarjeta inválida, etc.), **Then** el sistema muestra retroalimentación clara de rechazo al finalizar la simulación, y permite al cajero reintentar el cobro o cambiar de medio de pago sin perder los productos ya escaneados.
4. **Given** una venta con pago por tarjeta en curso, **When** ocurre una falla de comunicación con la pasarela de pago (timeout, sin conexión, pasarela no disponible), **Then** el sistema lo distingue visualmente de un rechazo del banco — indicando que fue un error técnico, no un problema con la tarjeta del cliente — y permite reintentar el cobro sin perder los productos ya escaneados.
5. **Given** una venta ya confirmada dentro de la misma jornada de caja, **When** el cajero la anula por error, **Then** el sistema revierte el descuento de inventario asociado y marca la venta como anulada sin eliminarla del historial.
6. **Given** un producto ya escaneado y agregado a una venta aún no confirmada, **When** el cajero necesita quitarlo del ticket antes de cobrar, **Then** el sistema exige la confirmación de un encargado de tienda (rol distinto al del cajero) antes de remover la línea, y deja registro auditable de quién autorizó la remoción.
7. **Given** una venta a punto de confirmarse, **When** el cliente solicita factura con su identificación y razón social, **Then** el comprobante se emite como factura con esos datos; **When** el cliente no solicita factura, **Then** el comprobante se emite por defecto como nota de venta a consumidor final.

---

### User Story 2 - Gestionar inventario por lotes (recepción, FIFO y ajustes) (Priority: P2)

Un reponedor registra la mercadería que llega de un proveedor indicando el lote y la fecha de vencimiento cuando aplica, rota el anaquel siguiendo FIFO, y registra mermas con su causa cuando detecta producto dañado o vencido. Periódicamente, tras un conteo físico, se ajusta el inventario del sistema para que coincida con la realidad.

**Why this priority**: Sin inventario confiable por lote, las ventas del P1 pueden venderse sobre stock inexistente y ninguna alerta de reposición o reporte de merma tendría base real (OT-5.3, OT-5.4).

**Independent Test**: Puede probarse registrando una recepción de mercadería con dos lotes de distinta fecha de vencimiento, confirmando que el sistema indica cuál debe salir primero, y registrando una merma con causa para verificar que descuenta del lote correcto.

**Acceptance Scenarios**:

1. **Given** un producto perecedero sin stock previo, **When** el reponedor registra la recepción de un lote con cantidad y fecha de vencimiento, **Then** el lote queda disponible para venta y visible en el inventario de esa tienda.
2. **Given** dos lotes del mismo producto con distinta fecha de vencimiento, **When** se registra una venta de ese producto, **Then** el sistema descuenta primero del lote con fecha de vencimiento más próxima (FIFO).
3. **Given** una diferencia entre el stock del sistema y el conteo físico, **When** el encargado registra el ajuste, **Then** el sistema actualiza el stock disponible y conserva un registro de la diferencia encontrada.
4. **Given** una unidad de producto dañada detectada en anaquel, **When** el reponedor registra la merma con su causa, **Then** la unidad se descuenta del inventario disponible y el registro queda pendiente de validación por el encargado de tienda.

---

### User Story 3 - Alertas de reposición, quiebre de stock y sugerencia de compra (Priority: P3)

El sistema calcula diariamente un punto de reposición dinámico por producto y tienda; cuando el stock disponible cae por debajo, genera una alerta que el encargado de tienda revisa y atiende. Si un producto se agota antes de reponerse, el encargado registra el evento de quiebre. Semanalmente, el sistema sugiere una orden de compra por producto y proveedor, que el jefe de Operaciones aprueba, ajusta o rechaza.

**Why this priority**: Reemplaza el punto de reorden fijo por uno dinámico (OT-5.1) y cierra el ciclo entre inventario y compras (OT-2.1), pero depende de que P1 y P2 ya estén generando datos reales de venta y stock.

**Independent Test**: Puede probarse simulando ventas que bajen el stock de un producto por debajo de su punto de reposición y verificando que se genera la alerta, y por separado generando la sugerencia semanal de compra y aprobándola.

**Acceptance Scenarios**:

1. **Given** un producto cuyo stock disponible cae por debajo de su punto de reposición calculado, **When** se ejecuta el cálculo diario, **Then** se genera una alerta de reposición visible para el encargado de esa tienda.
2. **Given** una alerta de reposición pendiente, **When** el encargado la revisa y repone el producto, **Then** puede marcarla como atendida.
3. **Given** un producto agotado con un cliente que lo solicitó, **When** el encargado registra el evento de quiebre de stock, **Then** el evento queda disponible para el reporte mensual de demanda perdida.
4. **Given** el cálculo semanal de sugerencia de compra, **When** el jefe de Operaciones decide comprar una cantidad distinta a la sugerida, **Then** el sistema exige registrar el motivo de la desviación antes de aprobar la orden.
5. **Given** un proveedor con una frecuencia de reposición pactada (semanal, mensual o trimestral), **When** llega la fecha correspondiente a esa frecuencia, **Then** el sistema genera y envía la orden de compra sugerida a ese proveedor según su propio calendario, sin depender de la sugerencia semanal genérica de otros proveedores.
6. **Given** una necesidad urgente de reposición fuera del calendario pactado con un proveedor, **When** el jefe de Operaciones solicita un pedido especial, **Then** el sistema envía la solicitud por correo electrónico al proveedor fuera de su frecuencia habitual y deja registro del pedido especial y su motivo.
7. **Given** una orden de compra ya marcada como recibida, **When** el jefe de Operaciones registra la factura del proveedor (número, monto, fecha de emisión y vencimiento), **Then** la factura queda asociada a esa orden con estado pendiente hasta que se le registre un pago.
8. **Given** una factura de proveedor pendiente o parcialmente pagada, **When** el jefe de Finanzas registra un pago (monto, medio, referencia), **Then** el sistema exige que el empleado que autoriza el pago sea distinto de quien lo registró, y actualiza el estado de la factura (pagada parcial o pagada) según el monto acumulado pagado.
9. **Given** un stock máximo definido por el Jefe de Operaciones para una categoría y tienda, **When** una recepción de mercadería deja el stock disponible de un producto de esa categoría por encima del máximo, **Then** el sistema genera una alerta de exceso de stock visible para el encargado de esa tienda, sin impedir que la recepción se registre (Ronda 9, OT-2.4).
10. **Given** un stock máximo ya definido, **When** el Jefe de Operaciones lo revisa y actualiza trimestralmente, **Then** las alertas de exceso futuras usan el nuevo valor, sin afectar alertas ya generadas con el valor anterior (Ronda 9, OT-2.4).
11. **Given** el catálogo de productos clasificación A (alta demanda), **When** el Reponedor realiza su verificación diaria de anaquel, **Then** el sistema registra la disponibilidad física reportada por producto, tienda y fecha (Ronda 10, OT-4.4).
12. **Given** un evento de quiebre de stock (Acceptance Scenario 3) de un producto clasificación A, **When** se registra, **Then** el sistema lo marca como quiebre de alta demanda y notifica de inmediato al Jefe de Operaciones de esa tienda, sin esperar al reporte mensual de demanda perdida (Ronda 10, OT-4.4).
13. **Given** el cierre de un mes, **When** el Jefe de Operaciones consulta el reporte de órdenes de compra, **Then** puede ver el porcentaje de órdenes automáticas (por sugerencia) frente a especiales/manuales, comparado contra la meta de OT-2.1 (Ronda 10, OO-2.1.5).
14. **Given** facturas de proveedor pendientes o próximas a vencer, **When** el Jefe de Finanzas las consulta semanalmente, **Then** obtiene el listado priorizado sin consolidar manualmente distintas fuentes (Ronda 10, OO-6.5.2).
15. **Given** el cierre de un mes, **When** el Jefe de Finanzas consulta el total de cuentas por pagar, **Then** obtiene el monto agregado de exposición financiera con proveedores, listo para presentar a Dirección General (Ronda 10, OO-6.5.3).
16. **Given** un proveedor o un producto ya registrados, **When** el Jefe de Operaciones consulta su historial de compras, **Then** el sistema muestra los productos que ese proveedor ha suministrado antes, o los proveedores que han suministrado ese producto antes, según corresponda (Ronda 11).

---

### User Story 4 - Mantener el catálogo de productos (Priority: P4)

El jefe Comercial o de Operaciones da de alta productos nuevos indicando código, categoría, costo, precio, si es perecedero y su clasificación ancla/nicho; actualiza datos de productos existentes; y descontinúa productos que dejan de venderse. Al registrar un producto nuevo desde la interfaz, el sistema intenta autocompletar sus datos e imagen a partir de su código de barras real.

**Why this priority**: El catálogo es prerrequisito de las demás historias (no se puede vender, recibir ni reponer un producto que no existe en el catálogo), pero al estar ya poblado por la carga inicial del dataset, su prioridad de implementación es menor a las tres anteriores para tener un MVP funcional.

**Independent Test**: Puede probarse dando de alta un producto nuevo con un código de barras real y verificando que el sistema autocompleta nombre/marca/categoría/imagen, y por separado descontinuando un producto y verificando que su historial de ventas previo permanece intacto.

**Acceptance Scenarios**:

1. **Given** un código de barras real de un producto físico nuevo, **When** el usuario lo ingresa al dar de alta el producto, **Then** el sistema intenta autocompletar nombre, marca, categoría e imagen desde el servicio externo de catálogo abierto, dejando los campos editables.
2. **Given** un producto existente, **When** se actualiza su precio o costo, **Then** las ventas futuras usan el nuevo valor y las ventas ya registradas conservan el precio histórico aplicado.
3. **Given** un producto que se descontinúa, **When** el usuario lo da de baja, **Then** deja de estar disponible para nuevas ventas pero su historial permanece consultable.

---

### User Story 5 - Registrar una devolución (Priority: P5)

Un cajero o encargado registra la devolución de un producto ya vendido, indicando el motivo. Según el motivo, el producto se reintegra o no al inventario disponible.

**Why this priority**: Es un flujo de menor frecuencia que las ventas diarias, pero necesario para que el inventario y el historial de ventas reflejen la realidad del negocio (OO-B.14).

**Independent Test**: Puede probarse registrando una devolución sobre una venta ya confirmada y verificando que el inventario se ajusta según el motivo indicado.

**Acceptance Scenarios**:

1. **Given** una venta ya confirmada, **When** el cliente devuelve un producto en buen estado, **Then** el sistema registra la devolución con su motivo y reintegra la unidad al inventario disponible.
2. **Given** una venta ya confirmada, **When** el cliente devuelve un producto dañado, **Then** el sistema registra la devolución pero NO reintegra la unidad al inventario disponible para la venta.

### Edge Cases

- ¿Qué ocurre si el cajero intenta vender una cantidad mayor al stock disponible de un producto? El sistema debe impedir confirmar esa línea de venta e informar el stock real disponible.
- ¿Qué ocurre si se escanea un código de barras que no existe en el catálogo? El sistema debe informar que el producto no está registrado y ofrecer darlo de alta antes de continuar la venta.
- ¿Qué ocurre si se intenta registrar una devolución de una venta ya anulada, o de una venta de una jornada de caja ya cerrada hace varios días? El sistema debe permitir la devolución (no depende del cierre de caja) pero dejar registrado que ocurrió fuera del mismo día de la venta.
- ¿Qué ocurre si dos lotes del mismo producto tienen exactamente la misma fecha de vencimiento? El sistema debe descontar del lote con menor cantidad disponible primero, o del que se recibió primero, para mantener un criterio determinístico.
- ¿Qué ocurre si un ajuste de inventario por conteo físico registra una diferencia negativa inusualmente grande respecto al stock del sistema? El sistema debe permitir registrar el ajuste igualmente, pero señalarlo como revisión pendiente (la investigación de causa/fraude pertenece a 006-caja-mermas-fraude, no a esta feature).
- ¿Qué ocurre si un producto está marcado como descontinuado pero aún tiene stock remanente en algún lote? El producto no debe ofrecerse para nuevas recepciones de mercadería, pero su stock remanente debe seguir siendo vendible hasta agotarse o poder liquidarse.
- ¿Qué ocurre si se genera una alerta de reposición para un producto que ya tiene una alerta pendiente sin atender? El sistema no debe duplicar alertas; debe mantener una sola alerta activa por producto/tienda hasta que se marque como atendida.
- ¿Qué ocurre si el cajero necesita quitar un producto ya escaneado antes de confirmar el pago? El sistema debe exigir la confirmación de un encargado de tienda para remover la línea (nunca el cajero solo), dejando registro del evento — control equivalente al mecanismo físico de llave usado en cajas reales para prevenir sub-registro.
- ¿Qué ocurre si un proveedor no tiene una frecuencia de reposición pactada configurada? El sistema debe usar la sugerencia semanal genérica por defecto hasta que se configure una frecuencia específica para ese proveedor.
- ¿Qué ocurre si un producto entra a la sugerencia semanal de compra (por estar bajo su punto de reposición) pero nunca tuvo una orden de compra previa en esa tienda? El sistema debe incluirlo igual en la sugerencia (la selección depende solo del inventario, no del historial de compras) dejando el proveedor sin resolver, para que el Jefe de Operaciones lo asigne manualmente al crear la orden (research.md #11).
- ¿Qué ocurre si el pago con tarjeta es rechazado por el banco (no por una falla técnica)? El sistema debe mostrarlo con retroalimentación clara e inequívoca y permitir reintentar el cobro o cambiar de medio de pago, sin perder los productos ya escaneados en la venta.
- ¿Qué ocurre si la pasarela de pago no responde a tiempo o no hay conexión con ella (timeout, caída del servicio)? El sistema debe distinguirlo claramente de un rechazo del banco — es un error técnico del sistema, no un problema imputable a la tarjeta del cliente — e igualmente permitir reintentar sin perder la venta en curso.
- ¿Qué ocurre si no hay un stock máximo definido para la categoría/tienda de un producto recibido? El sistema no genera alerta de exceso — no hay valor de referencia contra el cual comparar, y no se asume ningún máximo por defecto (Ronda 9, OT-2.4).
- ¿Qué ocurre si un producto cambia de clasificación (A↔B/C) el mismo día en que se registra su verificación de anaquel o su evento de quiebre? El sistema usa la clasificación vigente al momento del evento, no una histórica (Ronda 10, OT-4.4).
- ¿Qué ocurre si un producto de clasificación A no tiene ninguna verificación de anaquel registrada en un día? El sistema no genera una alerta automática por la omisión en esta versión — es un registro del reponedor, no un chequeo forzado, mismo criterio de simplicidad ya usado para otros registros "por evento"/diarios (Ronda 10, OT-4.4).
- ¿Qué ocurre si la tienda no tiene una impresora física conectada al confirmar una venta? El sistema debe igualmente presentar el comprobante listo para guardarse como PDF (la misma ventana de impresión del navegador ofrece "Guardar como PDF" cuando no hay impresora disponible) — el cajero nunca debe tener que buscar el comprobante manualmente en otra pantalla.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir al cajero registrar una venta agregando productos línea por línea, por escaneo de código de barras o búsqueda manual, calculando el total en tiempo real (OO-B.12).
- **FR-002**: El sistema DEBE permitir seleccionar el medio de pago de la venta entre efectivo, tarjeta de débito, tarjeta de crédito, transferencia bancaria o billetera digital (OT-4.1).
- **FR-003**: Para pagos con tarjeta, el sistema DEBE procesar el cobro a través de la pasarela de pago electrónico aprobada en modo de prueba, sin que el cajero capture, vea o almacene los datos de la tarjeta del cliente — el ingreso de la tarjeta ocurre en un paso separado dirigido al cliente, replicando la separación real entre la caja registradora y el datáfono físico (OO-4.1.1).
- **FR-004**: El sistema DEBE generar un comprobante de venta en PDF al confirmar cada venta, como documento de negocio real, y DEBE presentarlo de inmediato listo para imprimir o guardar, sin que el cajero deba buscarlo manualmente en otra pantalla — mismo comportamiento sea cual sea el medio de pago usado (OO-B.12).
- **FR-005**: El sistema DEBE descontar automáticamente el inventario de los lotes correspondientes siguiendo la regla FIFO al confirmar la venta (OO-5.3.2).
- **FR-006**: El sistema DEBE impedir confirmar una venta cuando la cantidad solicitada de un producto supera el stock disponible, informando al cajero el stock real.
- **FR-007**: El sistema DEBE permitir anular una venta antes del cierre de la caja de esa jornada, revirtiendo el descuento de inventario asociado sin eliminar el registro (OO-B.13).
- **FR-008**: El sistema DEBE permitir vincular opcionalmente un cliente ya existente a la venta, sin bloquear la venta si el cliente no se identifica.
- **FR-009**: El sistema DEBE permitir registrar un producto nuevo en el catálogo con código, categoría, costo, precio, indicador de perecedero y vida útil (OO-B.4).
- **FR-010**: El sistema DEBE permitir actualizar precio, costo, categoría u otros datos de un producto existente, sin alterar el precio ya aplicado en ventas pasadas (OO-B.5).
- **FR-011**: El sistema DEBE permitir dar de baja (descontinuar) un producto conservando su historial de ventas (OO-B.6).
- **FR-012**: Al registrar un producto nuevo, el sistema DEBE requerir su clasificación como "ancla" o "nicho" (OO-1.2.1).
- **FR-013**: Al registrar un producto nuevo desde la interfaz, el sistema DEBE intentar autocompletar nombre, marca, categoría e imagen consultando su código de barras en un servicio externo de catálogo abierto de productos, permitiendo edición manual si no hay coincidencia (OO-B.4).
- **FR-014**: El sistema DEBE permitir registrar la recepción de mercadería de un proveedor indicando lote, cantidad y fecha de vencimiento cuando aplique (OO-B.15, OO-5.3.1).
- **FR-015**: El sistema DEBE priorizar visualmente, en las pantallas de inventario, los lotes más próximos a vencer para favorecer su rotación (OO-5.3.2).
- **FR-016**: El sistema DEBE alertar automáticamente sobre lotes de productos perecederos próximos a vencer, con un umbral de días configurable (OO-5.3.3).
- **FR-017**: El sistema DEBE permitir ajustar el inventario de un producto tras un conteo físico, registrando la diferencia entre el stock del sistema y el stock físico contado (OO-B.16).
- **FR-018**: El sistema DEBE permitir registrar una merma indicando producto, lote, cantidad y causa en el momento en que se detecta (OO-5.4.1).
- **FR-019**: El sistema DEBE permitir al encargado de tienda validar o rechazar los registros de merma de su tienda (OO-5.4.2).
- **FR-020**: El sistema DEBE calcular diariamente, para cada producto y tienda, un punto de reposición dinámico basado en su rotación reciente, y generar una alerta cuando el stock disponible caiga por debajo de ese punto (OO-5.1.1).
- **FR-021**: El sistema DEBE permitir al encargado de tienda marcar una alerta de reposición como atendida, y no debe generar una segunda alerta activa para el mismo producto/tienda mientras la anterior siga pendiente (OO-5.1.2).
- **FR-022**: El sistema DEBE permitir registrar un evento de quiebre de stock (producto agotado con demanda no satisfecha) cuando el encargado lo detecte (OO-5.2.1).
- **FR-023**: El sistema DEBE generar semanalmente una sugerencia de orden de compra por producto y proveedor, basada en rotación y demanda reciente (OO-2.1.1).
- **FR-024**: El sistema DEBE permitir aprobar, ajustar o rechazar cada orden de compra sugerida, y registrar un motivo obligatorio cuando la decisión se aparte de la sugerencia (OO-2.1.2, OO-2.1.3).
- **FR-025**: El sistema DEBE permitir registrar una devolución de un producto ya vendido indicando el motivo, y reintegrar la unidad al inventario disponible solo cuando el motivo lo justifique (OO-B.14).
- **FR-026**: El sistema DEBE mantener trazabilidad entre cada venta, sus líneas, los lotes de inventario afectados y, cuando exista, la devolución asociada.
- **FR-027**: El sistema DEBE permitir remover una línea de una venta aún no confirmada únicamente con la confirmación de un encargado de tienda (rol distinto al del cajero que la registró), dejando registro auditable del evento, la línea removida y quién autorizó (OE-6, OT-6.4).
- **FR-028**: El sistema DEBE permitir configurar, por proveedor, una frecuencia de reposición pactada (semanal, mensual o trimestral) y generar/enviar la orden de compra sugerida a ese proveedor según su propio calendario (OT-2.1).
- **FR-029**: El sistema DEBE permitir solicitar un pedido especial a un proveedor fuera de su frecuencia pactada, enviando la solicitud por correo electrónico y dejando registro del pedido especial y su motivo (OT-2.1, OO-2.1.3).
- **FR-030**: Durante un cobro con tarjeta, el sistema DEBE mostrar una simulación visual del paso de la tarjeta por el datáfono (inserción o acercamiento) mientras se procesa el cobro, y al finalizar DEBE mostrar retroalimentación clara e inequívoca distinguiendo tres resultados posibles: (1) pago aprobado, (2) pago rechazado por el banco/tarjeta, o (3) error técnico de comunicación con la pasarela — cada uno con su propia señal visual, sin que el rechazo del banco se confunda con una falla del sistema (OO-4.1.1).
- **FR-031**: Si el pago con tarjeta es rechazado por el banco o falla por un error técnico de comunicación con la pasarela, el sistema DEBE permitir reintentar el cobro o cambiar de medio de pago sin perder los productos ya escaneados en la venta en curso.
- **FR-032**: El sistema DEBE permitir registrar el RUC del proveedor como parte de sus datos (OO-B.7, OO-B.8).
- **FR-033**: El sistema DEBE permitir registrar la factura de un proveedor contra una orden de compra ya recibida, indicando número de factura, monto total, fecha de emisión y fecha de vencimiento (OO-2.1.4).
- **FR-034**: El sistema DEBE permitir registrar uno o varios pagos (parciales o total) contra una factura de proveedor, indicando monto, medio de pago y referencia, y DEBE exigir que el empleado que autoriza el pago sea distinto del que lo registra (OO-6.5.1).
- **FR-035**: El sistema DEBE actualizar automáticamente el estado de una factura de proveedor (pendiente/pagada parcial/pagada) según la suma de los pagos registrados contra ella, calculado en la capa de servicio del backend.
- **FR-036**: Al confirmar una venta, el sistema DEBE permitir emitir el comprobante como factura (con identificación y razón social reales del comprador) o como nota de venta a consumidor final (identificación genérica), a elección del cliente; por defecto se emite como nota de venta a consumidor final (OO-B.12).
- **FR-037**: El sistema DEBE permitir al Jefe de Operaciones definir y actualizar el stock máximo por categoría y tienda, con revisión trimestral (OO-2.4.1).
- **FR-038**: Al registrar una recepción de mercadería que deja el stock disponible de un producto por encima del stock máximo vigente para su categoría y tienda, el sistema DEBE generar una alerta de exceso de stock, sin bloquear ni impedir el registro de la recepción (OO-2.4.2, Edge Case).
- **FR-039**: El sistema DEBE generar mensualmente un reporte del porcentaje de órdenes de compra automáticas (por sugerencia semanal) frente a especiales/manuales, comparado contra la meta de OT-2.1, consultable por el Jefe de Operaciones (OO-2.1.5, Ronda 10).
- **FR-040**: El Jefe de Finanzas DEBE poder consultar semanalmente el listado de facturas de proveedor pendientes o próximas a vencer dentro de un umbral de días configurable, para priorizar sus pagos (OO-6.5.2, Ronda 10).
- **FR-041**: El sistema DEBE permitir al Jefe de Finanzas consultar mensualmente el total de cuentas por pagar (suma de facturas pendientes y pagadas parcialmente) como reporte de exposición financiera con proveedores (OO-6.5.3, Ronda 10).
- **FR-042**: El Reponedor DEBE poder registrar la verificación diaria de disponibilidad física en anaquel de los productos de clasificación A (alta demanda) de su tienda (OO-4.4.1, Ronda 10).
- **FR-043**: Cuando un evento de quiebre de stock (FR-022) corresponda a un producto de clasificación A, el sistema DEBE marcarlo como quiebre de alta demanda y notificar de inmediato al Jefe de Operaciones de esa tienda, sin esperar al reporte mensual de demanda perdida (OO-4.4.2, Ronda 10).
- **FR-044**: El sistema DEBE permitir consultar, para un proveedor dado, los productos que le han sido comprados anteriormente, y para un producto dado, los proveedores que lo han suministrado anteriormente, a partir del historial real de órdenes de compra (apoya OO-2.1.1, OO-2.1.3, Ronda 11).

### Key Entities *(include if feature involves data)*

- **Producto (Catálogo)**: código interno, código de barras (real o sintético), nombre, categoría, marca, costo, precio base, clasificación ancla/nicho, clasificación ABC, indicador de perecedero, vida útil, imagen, estado (activo/descontinuado).
- **Venta (Ticket/Comprobante)**: fecha/hora, tienda, cajero, cliente (opcional), líneas de venta, medio de pago, total, estado (confirmada/anulada), tipo de comprobante (factura/nota de venta), identificación y razón social del comprador registradas al momento de la venta, comprobante PDF asociado.
- **Línea de Venta**: producto, cantidad, precio unitario aplicado, lote(s) de origen del descuento FIFO.
- **Devolución**: venta original, producto, cantidad, motivo, indicador de reintegro a inventario.
- **Lote de Inventario**: producto, tienda, proveedor de origen, cantidad recibida, cantidad disponible, fecha de recepción, fecha de vencimiento (si aplica).
- **Ajuste de Inventario**: producto, tienda, cantidad según sistema, cantidad física contada, diferencia, fecha, responsable.
- **Merma**: producto, tienda, lote, cantidad, causa, estado de validación (pendiente/validada/rechazada).
- **Alerta de Reposición**: producto, tienda, punto de reposición calculado, stock disponible al momento del cálculo, fecha, estado (pendiente/atendida).
- **Evento de Quiebre de Stock**: producto, tienda, fecha, demanda estimada no satisfecha.
- **Orden de Compra (sugerida)**: proveedor, producto(s) y cantidades sugeridas, tipo (programada según frecuencia pactada / especial fuera de calendario), estado (sugerida/aprobada/ajustada/rechazada), motivo de desviación cuando aplica.
- **Proveedor**: nombre, RUC, datos de contacto, condiciones de pago, frecuencia de reposición pactada (semanal/mensual/trimestral).
- **Factura de Proveedor**: orden de compra asociada, número de factura, monto total, fecha de emisión, fecha de vencimiento, estado (pendiente/pagada parcial/pagada/vencida), empleado que la registró.
- **Pago a Proveedor**: factura asociada, monto, medio de pago, referencia, empleado que lo registró, empleado que lo autorizó (distinto al anterior), fecha/hora.
- **Stock Máximo por Categoría**: categoría de producto, tienda, cantidad máxima vigente, empleado que lo definió, fecha de definición (Ronda 9).
- **Verificación de Anaquel (Alta Demanda)**: producto (clasificación A), tienda, fecha, disponible (sí/no), reponedor que la registró (Ronda 10).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Un cajero puede completar el registro y cobro de una venta de 10 productos escaneados en menos de 90 segundos.
- **SC-002**: El descuento de inventario de una venta confirmada es visible para cualquier consulta de stock en menos de 5 segundos desde la confirmación.
- **SC-003**: El 100% de los lotes de productos perecederos con fecha de vencimiento registrada generan su alerta de próximo vencimiento antes de esa fecha.
- **SC-004**: El 100% de las alertas de reposición calculadas en un día quedan visibles para el encargado de la tienda correspondiente ese mismo día.
- **SC-005**: El catálogo completo de productos sembrados (aproximadamente 92,331) queda operativo sin ningún producto sin código de barras o imagen asignada.
- **SC-006**: El jefe de Operaciones puede aprobar o ajustar una orden de compra sugerida sin tener que calcular manualmente cantidades de rotación o demanda.
- **SC-007**: El 100% de las líneas removidas de una venta antes de confirmarla quedan con un encargado identificado como autorizador del evento.
- **SC-008**: El sistema muestra el resultado (aprobado/rechazado) de un cobro con tarjeta en menos de 5 segundos desde que finaliza la simulación visual del paso de tarjeta.
- **SC-009**: El 100% de los pagos a proveedor registrados tienen un empleado autorizador distinto de quien lo registró, sin excepciones.
- **SC-010**: El 100% de las ventas del sistema (sembradas o en vivo) quedan con un tipo de comprobante definido (factura o nota de venta), sin registros ambiguos.
- **SC-011**: El 100% de los comprobantes de venta quedan listos para imprimir o guardar en el mismo momento de confirmar la venta, sin que el cajero navegue a otra pantalla para buscarlos.
- **SC-012**: El Jefe de Operaciones puede definir o actualizar el stock máximo de una categoría/tienda sin intervención de TI, y toda recepción que lo supere queda visible como alerta el mismo día (Ronda 9).
- **SC-013**: El Jefe de Operaciones y el Jefe de Finanzas obtienen los reportes de % de compras automáticas y de cuentas por pagar sin consolidar manualmente ninguna fuente (Ronda 10).
- **SC-014**: Todo evento de quiebre de stock de un producto de alta demanda genera una notificación inmediata al Jefe de Operaciones, distinta y anterior al reporte mensual de demanda perdida (Ronda 10).
- **SC-015**: El Jefe de Operaciones puede consultar qué productos ha suministrado un proveedor, o qué proveedores han suministrado un producto, a partir del historial real de compras, sin consultar la base de datos directamente (Ronda 11).

## Assumptions

- Los aproximadamente 92,331 productos sembrados desde el dataset Dunnhumby ya cuentan, desde la carga inicial, con código de barras sintético (rango GS1 20-29, documentado como no real) e imagen placeholder por categoría, según la decisión registrada en `domain-context.md`; esta feature consume y gestiona esos datos, no los genera.
- La autenticación, los roles (cajero, encargado de tienda, reponedor, jefe de Operaciones) y los permisos de acceso a estas pantallas provienen de la feature 008-auth-administracion-sistema; esta feature asume que ya existe un usuario autenticado con el rol correspondiente.
- El cuadre de caja horario, el análisis de diferencias de caja y la clasificación/investigación de fraude pertenecen a la feature 006-caja-mermas-fraude; esta feature solo registra la venta y su medio de pago, no el cuadre de la caja física.
- El pronóstico avanzado de demanda con modelo predictivo pertenece a la feature 004-pronostico-demanda; el punto de reposición dinámico de esta feature usa una lógica de rotación reciente más simple, no el modelo predictivo completo.
- El registro del cliente en el programa de fidelización y el cálculo de CLV pertenecen a la feature 002-clientes-fidelizacion; esta feature solo permite vincular un cliente ya existente a la venta.
- Cada tienda/sucursal gestiona su propio stock de forma independiente; el traslado de mercadería entre sucursales es un evento explícito (OO-2.5.2) fuera del flujo normal de venta o reposición de esta feature.
- El comprobante de venta en PDF es un documento de negocio interno de Marzú Retail Group, no una factura electrónica autorizada por el SRI (Ecuador); esa integración está fuera del alcance de todo el proyecto, no solo de esta feature.
- El umbral de días de anticipación para alertar vencimientos próximos (FR-016) es configurable por el negocio; no se fija un valor único de fábrica en esta especificación.
- El descuento por FIFO/FEFO (primero en vencer, primero en salir) se aplica a nivel de lote de forma lógica, no por unidad física serializada. La fecha de vencimiento de un lote se conoce por el documento de recepción de mercadería (FR-014), nunca por el código de barras del producto: el código de barras estándar (EAN-13/UPC) es idéntico para todas las unidades de ese producto sin importar el lote, tal como lo define el estándar GS1 para bienes de consumo masivo — no es una limitación propia de SIRA (existen formatos especiales como GS1-128/DataMatrix que sí embeben lote y vencimiento, usados en industrias con trazabilidad regulada como farmacéutica o en productos etiquetados en tienda como charcutería, pero no aplican al catálogo de consumo masivo de Marzú Retail Group). Por eso el sistema no puede saber qué unidad física tomó el cliente del anaquel; el control que mantiene la suposición de FIFO/FEFO razonablemente válida es operativo (rotación física del anaquel por el reponedor, FR-015), no un mecanismo del sistema — una divergencia ocasional entre el lote lógico y el físico es una limitación aceptada, idéntica a la de sistemas reales de inventario por lote (SAP Retail, Oracle Retail, etc.) para productos sin serialización por unidad.
- La simulación visual del datáfono (FR-030) es un requisito de comportamiento (debe existir y dar retroalimentación clara); su diseño visual exacto (duración, estilo de animación, dispositivo donde se muestra — mismo monitor o pantalla secundaria orientada al cliente) se define en `design-system.md` y en la fase de `/speckit-plan`, no en este documento.
- La pasarela de pago (Stripe) no emite el comprobante fiscal de la venta (FR-036): solo procesa el cobro y devuelve una referencia de transacción (capturada en el intento de pago). El comprobante (factura o nota de venta) lo emite siempre Marzú vía PDF, sin importar el medio de pago usado.
- Todas las ventas sembradas desde el dataset Dunnhumby quedan por defecto como nota de venta a consumidor final (FR-036), porque el dataset no trae ninguna identificación fiscal real asociada a los household_id; el caso "factura con identificación real" solo se ejercita en ventas creadas en vivo durante la demostración.
- El pago a proveedor no valida contra el SRI (Ecuador) ni ningún servicio bancario real; es un registro contable interno de doble autorización (FR-034), consistente con la decisión ya tomada de no integrar servicios fiscales/bancarios reales en todo el proyecto.
- El diseño visual exacto del comprobante (incluyendo el logotipo de Marzú Retail Group, tipografía y disposición del encabezado) se define en `design-system.md`, mismo criterio ya usado para la simulación visual del datáfono (FR-030) — este documento solo exige que el comprobante exista, se presente listo para imprimir/guardar de inmediato (FR-004, SC-011), y distinga factura de nota de venta (FR-036).
- **Ronda 9 (post-cierre, gap OT-2.4 incorporado)**: OT-2.4 (límites de stock máximo por categoría) quedó sin feature dueña tras el cierre inicial de 001-006 — se incorpora aquí como extensión del mecanismo de alertas ya existente (`alertas_inventario`, OT-5.1), agregando un tipo nuevo (`exceso_stock`) en vez de crear un módulo aparte; el umbral es una fila de configuración vigente por categoría/tienda (sin historial de versiones), mismo criterio de simplicidad que `umbral_merma_categoria` en 006. OT-2.5 (coordinación de stock entre tiendas / traslados) se mantiene deliberadamente fuera de esta feature — reafirma la suposición ya existente de que cada tienda gestiona su stock de forma independiente — y se especifica por separado en la feature 012-traslados-stock-entre-tiendas, al ser un flujo propio (solicitud → traslado → recepción en destino) y no una alerta.
- **Ronda 10 (post-cierre, auditoría completa de cobertura OT/OO)**: antes de arrancar el batch de artefactos de 007-012, se auditaron las 108 OO del BSC contra los 12 spec.md y aparecieron 4 huecos adicionales, los 3 primeros de contenido (reportes faltantes sobre datos ya modelados en esta feature, sin tabla nueva) y el cuarto un OT completo sin feature dueña: **OO-2.1.5** (reporte mensual % automáticas vs. especiales/manuales, FR-039) — el endpoint `GET /api/compras/facturas` de `contracts/compras.md` ya citaba OO-6.5.2 desde antes sin que existiera el FR correspondiente; queda corregido con **FR-040**. **OO-6.5.3** (total de cuentas por pagar) es reporte nuevo, **FR-041**. **OT-4.4** (disponibilidad 95% de productos de alta demanda) no tenía ninguna feature dueña en las 12 — se incorpora aquí por ser inventario/reposición, reutilizando `productos.clasificacion_abc='A'` como definición de "alta demanda" (sin columna nueva) y el mecanismo ya existente de `eventos_quiebre_stock` (FR-022) para el escalamiento inmediato (FR-043); la verificación diaria de anaquel (FR-042) sí requiere una tabla nueva mínima (`verificacion_anaquel`), su único agregado de modelo de datos.
- **Ronda 11 (post-implementación de Fase 5, visibilidad proveedor↔producto)**: durante la Fase 5 se detectó que FR-023 (sugerencia semanal) resuelve el proveedor de un producto buscando su última orden de compra (research.md #11), pero el sistema no exponía ninguna forma de consultar esa relación directamente — ni qué productos trae un proveedor, ni qué proveedores han traído un producto. Se incorpora como dos consultas de solo lectura sobre el historial real de `ordenes_compra`/`orden_compra_detalle`, sin catálogo maestro ni tabla nueva (Principio VIII): FR-044.
