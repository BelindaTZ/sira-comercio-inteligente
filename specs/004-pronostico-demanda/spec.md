# Feature Specification: Pronóstico de Demanda con Variables Exógenas

**Feature Branch**: `004-pronostico-demanda`
**Created**: 2026-09-06
**Status**: Draft
**Input**: OE-7 (TI y Datos) — OT-7.2 completo de `domain-context.md` (modelo predictivo de demanda con variables exógenas), más el cierre de OT-5.1 (reemplazar el punto de reorden fijo por demanda proyectada, iniciado en 001-core-ventas-inventario con una lógica de rotación reciente más simple) y de OT-5.2 (demanda perdida, cuyo registro por evento ya existe en 001 pero cuyo reporte mensual consolidado no tenía feature dueña)

## User Scenarios *(mandatory)*

### User Story 1 - Entrenar y aprobar el modelo de pronóstico antes de producción (Priority: P1) 🎯 MVP

El sistema entrena mensualmente, de forma automática, un modelo de pronóstico de demanda por producto y tienda, usando como variables explicativas el historial de ventas junto con la actividad promocional, los cambios de precio y los quiebres de stock del mismo periodo — para no confundir un pico de ventas causado por una promoción o una variación de precio con un aumento real y sostenido de la demanda. El sistema calcula la precisión del modelo entrenado contra datos que no usó para entrenar, y lo deja pendiente de aprobación. El Jefe de TI revisa esa precisión y aprueba o rechaza el modelo antes de que se use en producción.

**Why this priority**: sin un modelo entrenado y aprobado no hay ningún pronóstico que consumir — es la base de todo lo demás en esta feature. Publicar un modelo sin que nadie valide su precisión repetiría, a nivel de datos, el mismo error de "pricing sin aprobación" que la constitución exige evitar en otras features (control antes de impactar la operación, no después).

**Independent Test**: puede probarse forzando la corrida del job mensual de entrenamiento, verificando que el modelo resultante queda en estado pendiente con su métrica de precisión calculada, y que solo pasa a producción tras una aprobación explícita del Jefe de TI.

**Acceptance Scenarios**:

1. **Given** que se cumple la fecha de entrenamiento mensual, **When** el sistema ejecuta el job de entrenamiento, **Then** genera una nueva versión de modelo con su métrica de precisión calculada contra datos de validación, en estado "pendiente de aprobación".
2. **Given** un modelo pendiente de aprobación con una precisión aceptable, **When** el Jefe de TI lo aprueba, **Then** ese modelo pasa a ser el vigente en producción y queda disponible para el cálculo de pronóstico.
3. **Given** un modelo pendiente de aprobación con una precisión insuficiente, **When** el Jefe de TI lo rechaza, **Then** el modelo queda marcado como rechazado y el modelo previamente aprobado (si existe) sigue siendo el vigente en producción, sin interrupción.
4. **Given** que nunca existió un modelo aprobado para un producto/tienda determinado, **When** se necesita un pronóstico para ese producto/tienda, **Then** el sistema no falla ni bloquea el proceso que lo necesita — queda a cargo del cálculo de respaldo de la User Story 2.

---

### User Story 2 - Reposición y compras basadas en el pronóstico, con respaldo cuando no hay modelo (Priority: P2)

El punto de reposición dinámico que calcula diariamente 001-core-ventas-inventario (FR-020) y la sugerencia semanal de orden de compra por proveedor (FR-023 de 001) dejan de basarse únicamente en la rotación reciente: cuando existe un pronóstico vigente del modelo en producción para ese producto y tienda, el sistema lo usa como base del cálculo. Cuando no existe (modelo aún no entrenado para ese producto, historial insuficiente, o ningún modelo aprobado todavía), el sistema sigue usando la lógica de rotación reciente ya construida en 001, sin que el encargado de tienda ni el jefe de Operaciones noten una interrupción.

**Why this priority**: es la realización directa de OT-5.1 ("reemplazar el punto de reorden fijo por uno basado en demanda proyectada") y de la parte de OT-2.1 que exige que las compras se basen en demanda proyectada, no en rotación reciente ni en ofertas de proveedor — pero solo tiene sentido una vez que existe un modelo aprobado que consumir (depende de la User Story 1).

**Independent Test**: puede probarse comparando, para un producto con modelo vigente, que el punto de reposición y la sugerencia de compra usan el valor pronosticado; y por separado, para un producto sin modelo vigente, que ambos siguen calculándose con la lógica de rotación reciente de 001 sin quedar nunca sin valor.

**Acceptance Scenarios**:

1. **Given** un producto y tienda con un pronóstico vigente del modelo en producción, **When** se ejecuta el cálculo diario del punto de reposición, **Then** el punto de reposición usado es el del pronóstico, y la alerta generada indica que su origen es el modelo.
2. **Given** un producto y tienda sin ningún pronóstico vigente, **When** se ejecuta el cálculo diario del punto de reposición, **Then** el sistema usa la lógica de rotación reciente de 001, y la alerta generada indica que su origen es el cálculo de respaldo.
3. **Given** un producto con pronóstico vigente, **When** se genera la sugerencia semanal de orden de compra para su proveedor, **Then** la cantidad sugerida se basa en el pronóstico, visible como tal para el jefe de Operaciones.
4. **Given** que un modelo previamente vigente es reemplazado por una nueva versión aprobada, **When** se ejecuta el siguiente cálculo diario o semanal, **Then** usa la nueva versión sin ninguna acción manual adicional.

---

### User Story 3 - Monitorear la precisión del modelo ya en producción (Priority: P3)

Cada semana, el sistema compara el pronóstico que generó el modelo vigente contra la demanda real ya observada en ese periodo, y calcula qué tan preciso fue. Si la precisión cae por debajo de un umbral configurable, el sistema genera una alerta visible para el Jefe de TI, quien decide si conviene esperar al próximo reentrenamiento mensual o actuar antes.

**Why this priority**: un modelo que fue preciso al aprobarse puede degradarse con el tiempo (cambios reales en el comportamiento de compra, estacionalidad no vista en el entrenamiento); sin este monitoreo nadie se entera hasta que el punto de reposición empiece a fallar visiblemente. Depende de que ya exista un modelo en producción (User Story 1), y es complementaria — no bloqueante — al consumo del pronóstico de la User Story 2.

**Independent Test**: puede probarse dejando pasar al menos una semana de demanda real sobre un producto con pronóstico vigente, forzando la corrida del job semanal de monitoreo, y verificando que la métrica de precisión queda calculada y que se genera la alerta solo cuando cae bajo el umbral.

**Acceptance Scenarios**:

1. **Given** un modelo vigente en producción con al menos una semana de pronósticos ya comparables contra ventas reales, **When** se ejecuta el job semanal de monitoreo, **Then** se calcula y registra la métrica de precisión de esa semana para ese modelo.
2. **Given** una métrica de precisión semanal por debajo del umbral configurado, **When** se completa el cálculo, **Then** el sistema genera una alerta visible para el Jefe de TI.
3. **Given** el histórico de métricas semanales de un modelo, **When** el Jefe de TI lo consulta, **Then** puede ver la tendencia de precisión a lo largo del tiempo, no solo el valor de la semana más reciente.

---

### User Story 4 - Reporte mensual de demanda perdida por quiebre de stock (Priority: P4)

Cada mes, el sistema consolida los eventos de quiebre de stock ya registrados por los encargados de tienda (FR-022 de 001) en un reporte de demanda perdida estimada, desglosado por tienda y por categoría de producto, para que el Jefe de Operaciones priorice dónde actuar sin tener que sumar eventos manualmente.

**Why this priority**: reutiliza datos que ya se registran desde 001; es valiosa pero no bloquea nada de lo anterior — es la prioridad más baja de esta feature.

**Independent Test**: puede probarse registrando varios eventos de quiebre de stock en tiendas y categorías distintas durante el mes, y verificando que el reporte mensual los consolida correctamente por tienda y por categoría.

**Acceptance Scenarios**:

1. **Given** varios eventos de quiebre de stock registrados durante el mes en curso, **When** el Jefe de Operaciones genera el reporte mensual de demanda perdida, **Then** el reporte muestra el total estimado desglosado por tienda y por categoría de producto.
2. **Given** una tienda o categoría sin ningún evento de quiebre en el mes, **When** se genera el reporte, **Then** esa tienda o categoría no aparece con demanda perdida (ausencia de evento no se reporta como cero forzado ni como error).

---

### Edge Cases

- ¿Qué pasa si un producto es tan nuevo que no tiene suficiente historial de ventas para entrenar un modelo confiable? El sistema no lo incluye en el entrenamiento de ese mes; ese producto sigue cubierto por el cálculo de respaldo de rotación reciente (User Story 2) hasta acumular historial suficiente en un entrenamiento posterior.
- ¿Qué pasa si el Jefe de TI no revisa un modelo pendiente de aprobación durante varios días? El modelo previamente aprobado (si existe) sigue siendo el vigente en producción sin ningún límite de tiempo forzado — no hay una aprobación automática por defecto ni un vencimiento del modelo pendiente.
- ¿Qué pasa si nunca hubo ningún modelo aprobado para toda la tienda (por ejemplo, una tienda recién abierta)? Todos sus productos usan el cálculo de respaldo de rotación reciente hasta que un entrenamiento futuro los incluya.
- ¿Qué pasa si dos modelos quedan pendientes de aprobación al mismo tiempo (por ejemplo, se forzó un reentrenamiento manual antes de que terminara el ciclo mensual normal)? El Jefe de TI puede aprobar o rechazar cada uno de forma independiente; solo puede haber un modelo vigente en producción a la vez — aprobar uno nuevo reemplaza automáticamente al anterior como vigente.
- ¿Qué pasa si un producto tuvo ventas altas por una promoción y luego la promoción termina? El pronóstico para el periodo posterior a la promoción no debe partir de ese pico como si fuera la demanda base, porque el entrenamiento ya trató la promoción como variable explicativa separada, no como parte del patrón normal de ventas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE entrenar automáticamente, de forma mensual, un modelo de pronóstico de demanda por producto y tienda, usando como variables explicativas al menos el historial de ventas, la actividad promocional vigente, los cambios de precio y los eventos de quiebre de stock del periodo entrenado (OO-7.2.1).
- **FR-002**: El sistema DEBE calcular, para cada modelo entrenado, una métrica de precisión de pronóstico contra un conjunto de datos de validación que no haya usado para entrenar, antes de ofrecerlo para aprobación (OO-7.2.2).
- **FR-003**: El sistema DEBE mantener cada modelo recién entrenado en estado "pendiente de aprobación" y NO debe usarlo para ningún cálculo de reposición o de sugerencia de compra hasta que un Jefe de TI lo apruebe explícitamente (OO-7.2.2).
- **FR-004**: El sistema DEBE permitir a un Jefe de TI aprobar o rechazar un modelo pendiente, dejando registro de quién decidió, cuándo, y con qué métrica de precisión contaba al decidir (OO-7.2.2).
- **FR-005**: Si un Jefe de TI rechaza un modelo pendiente, el sistema DEBE conservar el modelo previamente aprobado (si existe) como el vigente en producción, sin interrupción del cálculo de pronóstico para los productos/tiendas ya cubiertos.
- **FR-006**: El sistema DEBE excluir del entrenamiento a los productos sin historial de ventas suficiente para un pronóstico confiable, dejándolos cubiertos por el cálculo de respaldo de FR-008.
- **FR-007**: El sistema DEBE usar el pronóstico de demanda del modelo vigente en producción, cuando exista para un producto y tienda, como base del cálculo diario del punto de reposición dinámico (FR-020 de 001-core-ventas-inventario), en lugar de la lógica de rotación reciente.
- **FR-008**: Si no existe un pronóstico vigente para un producto/tienda, el sistema DEBE calcular el punto de reposición usando la lógica de rotación reciente ya construida en 001 como respaldo, sin bloquear ni retrasar la generación de la alerta de reposición.
- **FR-009**: El sistema DEBE usar el pronóstico de demanda vigente, cuando exista, como base de la sugerencia semanal de orden de compra por producto y proveedor (FR-023 de 001), con el mismo respaldo de FR-008 cuando no exista pronóstico.
- **FR-010**: El sistema DEBE dejar visible, tanto en la alerta de reposición como en la sugerencia de orden de compra, si el valor usado provino del modelo de pronóstico o del cálculo de respaldo por rotación reciente.
- **FR-011**: El sistema DEBE calcular semanalmente, para el modelo vigente en producción, una métrica de precisión comparando el pronóstico generado contra la demanda real ya observada en ese periodo (OO-7.2.3).
- **FR-012**: El sistema DEBE generar una alerta visible para el Jefe de TI cuando la métrica de precisión semanal de un modelo en producción caiga por debajo de un umbral configurable.
- **FR-013**: El sistema DEBE permitir consultar el histórico de métricas de precisión semanal de un modelo, para observar su tendencia en el tiempo y no solo el valor más reciente.
- **FR-014**: El sistema DEBE generar mensualmente un reporte consolidado de demanda perdida estimada, a partir de los eventos de quiebre de stock ya registrados (FR-022 de 001), desglosado por tienda y por categoría de producto (OO-5.2.2).

### Key Entities *(include if feature involves data)*

- **Modelo de Pronóstico (versión)**: fecha de entrenamiento, métrica de precisión de validación, estado (pendiente de aprobación/aprobado/rechazado/reemplazado), empleado que aprobó o rechazó, fecha de la decisión.
- **Pronóstico de Demanda**: producto, tienda, periodo al que corresponde, cantidad pronosticada, versión de modelo que lo generó.
- **Métrica de Monitoreo Semanal**: modelo vigente, semana, métrica de precisión calculada contra demanda real, indicador de si superó el umbral de alerta.
- **Reporte de Demanda Perdida (mensual)**: periodo, tienda, categoría de producto, cantidad de eventos de quiebre consolidados, demanda estimada no satisfecha total.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los modelos entrenados mensualmente quedan con su métrica de precisión de validación calculada antes de estar disponibles para la decisión del Jefe de TI, sin excepciones.
- **SC-002**: Ningún modelo pasa a ser el vigente en producción sin una aprobación explícita registrada de un Jefe de TI.
- **SC-003**: El 100% de los productos/tienda sin pronóstico vigente (por historial insuficiente o por no tener aún ningún modelo aprobado) siguen generando su alerta de reposición mediante el cálculo de respaldo, sin quedar nunca sin ningún punto de reposición calculado.
- **SC-004**: El Jefe de TI puede identificar, sin cálculos manuales, si la precisión del modelo en producción se degradó en la semana más reciente respecto a su histórico.
- **SC-005**: El Jefe de Operaciones recibe el reporte mensual de demanda perdida ya desglosado por tienda y categoría, sin tener que consolidar manualmente los eventos de quiebre de stock.

## Assumptions

- No existe en el esquema RBAC un rol "Analista de Datos" ni "Analista de Operaciones" (solo `Jefe_TI` y `Jefe_Operaciones`) — mismo patrón de vacío ya detectado en 002 (Analista de Marketing) y 003 (Analista de Pricing), pero con una resolución distinta porque aquí sí existía una separación real de actores en el diseño original: OO-7.2.1 (entrenar) y OO-7.2.3 (monitorear) pasan a ser jobs automáticos del sistema — mismo patrón ya usado en 003 para la propuesta de ajuste de precio semanal y la alerta de competencia semanal — y el único actor humano necesario es el Jefe de TI, que aprueba/rechaza el modelo (OO-7.2.2) y revisa la alerta de degradación semanal; así se conserva la separación real entre "quien genera" (el sistema) y "quien aprueba antes de producción" (una persona), sin necesitar un rol nuevo. Para OO-5.2.2 se resuelve igual que en 002/003: `Jefe_Operaciones` ejecuta esa acción, sin un rol "Analista de Operaciones" separado.
- El modelo de pronóstico entrena localmente con `scikit-learn`/`statsmodels` (domain-context.md §9), sin servicio externo de ML ni credenciales adicionales.
- Esta feature NO reconstruye el mecanismo de alertas de reposición ni la tabla `alertas_inventario` ya construidos en 001 (FR-020/FR-021): solo cambia el insumo del cálculo cuando existe un pronóstico vigente, reutilizando la tabla y el flujo ya existentes (Principio VI/VIII).
- El reporte de demanda perdida reutiliza `eventos_quiebre_stock` ya registrado por 001 (FR-022); esta feature no cambia cómo se registra ese evento, solo lo consolida y reporta.
- La forma exacta de aproximar el efecto de "un producto relacionado dejó de estar disponible" (por ejemplo, usando eventos de quiebre de otros productos de la misma categoría en el mismo periodo como variable adicional) es una decisión de ingeniería de variables que se documenta en `research.md`, no en este spec — el requisito duro de esta especificación es que el modelo no trate una venta elevada explicada por promoción, precio o disponibilidad circunstancial como si fuera un aumento sostenido de la demanda base (FR-001).
- Esta feature no incluye el pipeline ELT de ClickHouse/Airflow (010-plataforma-datos-tactico-estrategico, en espera): el modelo entrena directamente contra las tablas operativas de PostgreSQL (`ventas`, `venta_detalle`, `promociones`, `historial_precios`, `eventos_quiebre_stock`); si el volumen llegara a exigir agregaciones del warehouse, se revisará junto con 010 (ya anotado en `domain-context.md` §8).
- Los jobs mensuales y semanales de esta feature reutilizan el mismo mecanismo de scheduler (APScheduler) ya configurado en 002/003 — sin Airflow ni un orquestador nuevo (Principio III).
- El umbral de precisión mínima para aprobar un modelo (FR-002/FR-003) y el umbral de degradación semanal (FR-012) son valores configurables por el negocio, no un valor único fijado en esta especificación — mismo patrón ya usado en 001 (umbral de vencimiento) y 003 (tolerancia de ajuste, umbral de alerta de competencia).
- La autenticación, los roles y los permisos de acceso a estas pantallas provienen de 008-auth-administracion-sistema; esta feature asume que ya existe un usuario autenticado con el rol correspondiente.
