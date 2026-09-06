# Feature Specification: Precios Dinámicos, Márgenes y Comparación de Competencia

**Feature Branch**: `003-precios-margenes`
**Created**: 2026-09-06
**Status**: Draft
**Input**: OE-1 (Comercial y Pricing) — OT-1.1 a OT-1.4 de `domain-context.md`, más OT-4.3 (comparación de precio vs. competencia, sin feature dueña previa — incorporada aquí por decisión del usuario)

## User Scenarios *(mandatory)*

### User Story 1 - Definir margen objetivo y calcular el margen real de cada venta (Priority: P1) 🎯 MVP

El Jefe Comercial define el margen objetivo (%) de cada categoría de producto. El sistema calcula, para cada venta ya confirmada, el margen real efectivamente obtenido (con cualquier descuento ya aplicado, nunca el precio de catálogo sin descontar) y lo deja consultable por categoría.

**Why this priority**: es la base de todo lo demás en esta feature — sin un margen objetivo definido y un margen real calculado correctamente, ni el motor de pricing, ni la detección de descuentos bajo margen, ni el reporte mensual tienen con qué compararse.

**Independent Test**: se puede probar definiendo el margen objetivo de una categoría y verificando que el margen real de una venta ya confirmada en esa categoría se calcula y queda disponible para consulta, sin depender de ninguna otra historia.

**Acceptance Scenarios**:

1. **Given** una categoría sin margen objetivo definido, **When** el Jefe Comercial lo define, **Then** queda disponible para todos los cálculos de margen de esa categoría desde ese momento en adelante.
2. **Given** una venta confirmada con un descuento ya aplicado sobre una línea, **When** el sistema calcula el margen real de esa línea, **Then** usa el precio final después del descuento, no el precio de catálogo original.
3. **Given** varias ventas de una misma categoría en un rango de fechas, **When** el Jefe Comercial consulta el margen real acumulado, **Then** lo ve comparado contra el margen objetivo vigente de esa categoría.

---

### User Story 2 - Motor de pricing dinámico con política diferenciada ancla/nicho (Priority: P2)

El Jefe Comercial define, por categoría, una regla de ajuste de precio basada en la desviación entre el margen real y el objetivo, con un factor de sensibilidad configurable. El sistema genera propuestas de ajuste de precio por producto; el Jefe Comercial las revisa y aprueba antes de que se publiquen. Los productos ancla y nicho de una misma categoría nunca comparten el mismo margen objetivo efectivo — los ancla se tratan de forma más agresiva (para atraer tráfico), los nicho más conservadora.

**Why this priority**: resuelve directamente el problema narrado de que un supermercado que no sabe qué margen da cada producto no puede diferenciar su estrategia de precio — pero depende de que US1 ya calcule el margen real.

**Independent Test**: se puede probar definiendo una regla de ajuste para una categoría, generando una propuesta, aprobándola, y verificando que el precio publicado y su historial reflejan el cambio — y que un producto ancla y uno nicho de la misma categoría reciben un margen objetivo efectivo distinto.

**Acceptance Scenarios**:

1. **Given** una categoría cuyo margen real está por encima de su margen objetivo, **When** se genera la propuesta de ajuste, **Then** el sistema propone bajar el precio de los productos de esa categoría, nunca lo aplica automáticamente al catálogo.
2. **Given** una propuesta de ajuste de precio pendiente, **When** el Jefe Comercial la aprueba, **Then** el precio de catálogo se actualiza y el cambio queda registrado en el historial de precios (con fecha de inicio y fin) por tienda.
3. **Given** una propuesta de ajuste de precio pendiente, **When** el Jefe Comercial no la aprueba, **Then** el precio de catálogo no cambia y la propuesta queda pendiente indefinidamente.
4. **Given** un producto ancla y un producto nicho de la misma categoría, **When** el sistema calcula el margen objetivo efectivo de cada uno, **Then** son distintos — el del ancla más bajo/agresivo que el del nicho.
5. **Given** un producto ya existente en el catálogo, **When** el Jefe Comercial revisa y cambia su clasificación ancla/nicho, **Then** el cambio aplica hacia adelante, sin recalcular el margen ya reportado de sus ventas pasadas.

---

### User Story 3 - Descuento manual en punto de venta con autorización obligatoria y detección de margen bajo mínimo (Priority: P3)

Un cajero nunca puede aplicar un descuento manual por sí mismo, sin importar el monto — necesita la autorización de un Encargado de Tienda (o superior), distinto de quien lo aplica, además de un motivo obligatorio (igualación de precio, producto por vencer, cortesía, corrección). Una vez autorizado, el sistema nunca bloquea la venta por esto, pero si el margen real resultante de esa línea cae bajo el margen objetivo efectivo de su producto, la marca automáticamente. El Encargado de Tienda revisa el listado diario de su tienda; el Jefe Comercial revisa el consolidado semanal de toda la red y registra la acción correctiva tomada.

**Why this priority**: resuelve el problema narrado de estar "tirando dinero en una economía de márgenes ajustados" sin darse cuenta, y cierra un riesgo real de fraude ("sweethearting" — descuentos indebidos a conocidos) que un descuento sin autorización dejaría abierto — depende de que US1 y US2 ya existan (margen objetivo efectivo por producto).

**Independent Test**: se puede probar intentando aplicar un descuento manual sin autorización de un Encargado de Tienda (debe rechazarse), luego con la autorización correcta resultando en margen bajo el mínimo, y verificando que aparece en el listado diario del Encargado de Tienda.

**Acceptance Scenarios**:

1. **Given** una línea de venta en curso, **When** el cajero intenta aplicar un descuento manual sin la autorización de un Encargado_Tienda, **Then** el sistema rechaza la operación — sin excepción por monto, ni siquiera un descuento menor.
2. **Given** una línea de venta en curso, **When** el mismo empleado que aplica el descuento intenta también autorizarlo, **Then** el sistema rechaza la operación — el autorizador debe ser un empleado distinto (mismo control que FR-027 de 001).
3. **Given** una línea de venta en curso, **When** el cajero aplica el descuento con autorización de un Encargado_Tienda pero sin indicar motivo, **Then** el sistema rechaza la operación — el motivo es obligatorio.
4. **Given** un descuento manual ya autorizado que deja el margen real de la línea por encima del margen objetivo efectivo, **When** se confirma la venta, **Then** la línea no se marca — el descuento se registra normalmente.
5. **Given** un descuento manual ya autorizado que deja el margen real de la línea por debajo del margen objetivo efectivo, **When** se confirma la venta, **Then** la venta se confirma igual (nunca se bloquea por el margen) y la línea queda marcada automáticamente en el listado del día.
6. **Given** líneas marcadas de varios días, **When** el Jefe Comercial revisa el consolidado semanal, **Then** puede registrar la acción correctiva tomada para cada una o para el patrón detectado.

---

### User Story 4 - Reporte mensual de margen real vs. objetivo a Dirección General (Priority: P4)

El Jefe Comercial genera mensualmente un reporte de margen real vs. margen objetivo por categoría, para presentarlo a Dirección General.

**Why this priority**: es el cierre del ciclo de gestión de margen — depende de que US1 (margen real) y la definición de márgenes objetivo ya existan; es consulta, no captura de datos nuevos.

**Independent Test**: se puede probar generando el reporte de un mes con ventas ya registradas y verificando que compara correctamente el margen real contra el objetivo de cada categoría.

**Acceptance Scenarios**:

1. **Given** un mes con ventas ya confirmadas en varias categorías, **When** el Jefe Comercial genera el reporte mensual, **Then** ve, por categoría, el margen real obtenido y el margen objetivo vigente ese mes, sin tener que calcularlo manualmente.

---

### User Story 5 - Comparar precio propio vs. precio de referencia de la competencia (Priority: P5)

El Jefe Comercial (o quien registre el dato) captura manualmente el precio de referencia de un producto en la competencia. El sistema calcula la desviación entre el precio propio y esa referencia, y alerta semanalmente sobre los productos cuya desviación supere un umbral configurable.

**Why this priority**: resuelve el problema narrado de perder la venta por un precio "ligeramente mayor" al de la competencia — es la historia menos urgente porque depende de que exista un precio propio ya gestionado (US1/US2) contra el cual comparar, y no bloquea nada operativo si no está lista.

**Independent Test**: se puede probar registrando un precio de referencia de competencia para un producto con una desviación mayor al umbral, y verificando que aparece en las alertas semanales.

**Acceptance Scenarios**:

1. **Given** un producto sin ningún precio de referencia de competencia registrado, **When** se generan las alertas semanales, **Then** ese producto no aparece — no se asume ninguna desviación sin dato real con qué comparar.
2. **Given** un producto con un precio de referencia de competencia cuya desviación frente al precio propio supera el umbral configurado, **When** se generan las alertas semanales, **Then** el Jefe Comercial lo ve en el listado sin calcular la diferencia manualmente.

---

### Edge Cases

- ¿Qué pasa si una categoría no tiene margen objetivo definido? El sistema usa un margen mínimo global de respaldo (configurable), documentado como tal — nunca asume 0% ni bloquea el cálculo por falta de dato.
- ¿Qué pasa si una línea de venta tiene, a la vez, un cupón de 002 y un descuento manual de esta feature? El margen real se calcula sobre el precio final después de TODOS los descuentos aplicados, no solo el manual — evita falsos positivos o negativos en la detección de margen bajo.
- ¿Qué pasa si el Jefe Comercial nunca aprueba una propuesta de ajuste de precio? Queda pendiente indefinidamente; el sistema nunca publica un cambio de precio sin aprobación humana explícita (mismo principio que las sugerencias de compra de 001: sugerencia ≠ decisión).
- ¿Qué pasa con el margen ya reportado de ventas pasadas si un producto cambia de categoría o de clasificación ancla/nicho? No se recalcula retroactivamente (Principio II, registro real) — el cambio aplica solo hacia adelante.
- ¿Qué pasa si no hay ningún precio de referencia de competencia para un producto? No genera alerta — ausencia de dato no es evidencia de desviación.
- ¿Qué pasa si el Encargado_Tienda que normalmente autoriza no está disponible en el momento? Cualquier empleado con rol Encargado_Tienda o superior en esa tienda puede autorizar — no depende de una persona específica, solo del rol.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema DEBE permitir a Jefe_Comercial definir y ajustar el margen objetivo (%) de cada categoría de producto.
- **FR-002**: El sistema DEBE calcular el margen real de cada línea de venta confirmada usando el precio efectivamente cobrado (después de cualquier descuento) y el costo del producto vigente al momento de la venta.
- **FR-003**: El sistema DEBE permitir consultar el margen real acumulado por categoría en un rango de fechas, comparado contra su margen objetivo vigente.
- **FR-004**: El sistema DEBE permitir a Jefe_Comercial definir, por categoría, una regla de ajuste de precio basada en la desviación entre margen real y margen objetivo, incluyendo un factor de sensibilidad ("elasticidad") configurado manualmente por categoría — no estimado por un modelo predictivo en esta feature.
- **FR-005**: El sistema DEBE generar, según la regla de su categoría, una propuesta de ajuste de precio por producto, sin aplicarla automáticamente al catálogo.
- **FR-006**: El sistema DEBE exigir que Jefe_Comercial revise y apruebe cada propuesta antes de publicarla; al aprobarla, DEBE actualizar el precio de catálogo y registrar el cambio en el historial de precios (por tienda, con fecha de inicio y fin).
- **FR-007**: El sistema DEBE calcular el margen objetivo efectivo de un producto aplicando un modificador según su clasificación ancla/nicho sobre el margen objetivo de su categoría — nunca el mismo valor para ambas clasificaciones.
- **FR-008**: El sistema DEBE permitir a Jefe_Comercial revisar y reclasificar la clasificación ancla/nicho de cualquier producto ya existente en el catálogo (no solo al momento del alta, ya cubierto por FR-012 de 001).
- **FR-009**: El sistema DEBE exigir la autorización de un empleado con rol Encargado_Tienda (o superior), distinto de quien aplica el descuento, para aplicar cualquier descuento manual (monto o porcentaje) a una línea de venta en curso — sin excepción por monto, ni siquiera descuentos menores — además de un motivo obligatorio, antes de confirmar la venta. Un cajero nunca puede autorizar su propio descuento (mismo control que FR-027 de 001: `empleado_aplica_id <> empleado_autoriza_id`).
- **FR-010**: Una vez autorizado el descuento manual (FR-009), el sistema DEBE recalcular el margen real de esa línea y, si queda por debajo de su margen objetivo efectivo, marcarla automáticamente para revisión posterior — la autorización de FR-009 no depende de este resultado (un Encargado_Tienda puede autorizar un descuento que igual caiga bajo margen, ej. producto por vencer) y la venta nunca se bloquea por esto.
- **FR-011**: El sistema DEBE permitir a Encargado_Tienda consultar diariamente el listado de líneas marcadas por margen bajo mínimo de su tienda.
- **FR-012**: El sistema DEBE permitir a Jefe_Comercial consultar semanalmente el listado consolidado de todas las tiendas y registrar la acción correctiva tomada.
- **FR-013**: El sistema DEBE generar mensualmente un reporte de margen real vs. margen objetivo por categoría, consultable por Jefe_Comercial.
- **FR-014**: El sistema DEBE permitir registrar manualmente el precio de referencia de un producto en la competencia — identificando al competidor (nombre y tipo: supermercado / tienda de barrio / tienda digital), opcionalmente la tienda Marzú de referencia (relevancia geográfica) y si el precio es promocional — junto con su fecha de captura. Para productos agregados en vivo con código de barras real (FR-013 de 001), el sistema DEBE además consultar automáticamente Open Prices (prices.openfoodfacts.org, misma familia de Open Food Facts ya usada en 001) como fuente adicional de precio de referencia — sin bloquear ni sustituir el registro manual, y sin que la ausencia de dato en Open Prices sea un error; esta consulta automática no aplica a los productos sembrados del dataset Dunnhumby, cuyo código de barras es sintético.
- **FR-015**: El sistema DEBE calcular automáticamente la desviación entre el precio propio de un producto y su precio de referencia de competencia más reciente, sin importar si ese precio fue capturado manualmente, vino de Open Prices o de la semilla sintética de demostración.
- **FR-016**: El sistema DEBE alertar a Jefe_Comercial semanalmente sobre los productos cuya desviación de precio frente a la competencia supere un umbral configurable.

### Key Entities *(include if feature involves data)*

- **Margen Objetivo**: categoría de producto, porcentaje objetivo.
- **Regla de Ajuste de Precio**: categoría, condición de desviación de margen, factor de sensibilidad/elasticidad.
- **Propuesta de Ajuste de Precio**: producto, precio propuesto, margen esperado, estado (pendiente/aprobada/rechazada), fecha.
- **Historial de Precio**: producto, tienda, precio, fecha de inicio, fecha de fin.
- **Línea de Venta (extendida)**: motivo del descuento manual, empleado que aplicó el descuento, empleado que lo autorizó (distinto del anterior), margen real de la línea, indicador de margen bajo mínimo.
- **Competidor**: nombre, tipo (supermercado / tienda de barrio / tienda digital), ciudad.
- **Precio de Referencia de Competencia**: producto, competidor (opcional — vacío cuando el dato viene de Open Prices), tienda Marzú de referencia (opcional), precio, fecha de captura, si es promocional, fuente de captura (manual / Open Prices / sintética).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las categorías con ventas en un mes dado tienen un margen objetivo definido antes de generar el reporte mensual de esa categoría.
- **SC-002**: Ninguna propuesta de ajuste de precio se publica en el catálogo sin aprobación explícita de Jefe_Comercial.
- **SC-003**: El margen objetivo efectivo de un producto ancla es siempre distinto (menor) al de un producto nicho de la misma categoría.
- **SC-004**: El 100% de los descuentos manuales aplicados tienen un empleado autorizador distinto de quien los aplicó, sin excepción por monto — y el 100% de las líneas con descuento manual que caen bajo el margen mínimo aparecen en el listado del mismo día, sin ningún cálculo manual.
- **SC-005**: El Jefe Comercial puede revisar la desviación de precio frente a la competencia sin calcular la diferencia manualmente.

## Assumptions

- El factor de sensibilidad/elasticidad (FR-004) es configurado manualmente por Jefe_Comercial por categoría, no estimado por un modelo predictivo — una estimación real por machine learning queda fuera del alcance de esta feature (posible mejora futura, no reservada a ninguna feature actual).
- OO-1.1.3 (cargar/actualizar costos de producto) ya está cubierto por FR-010 de 001 (`PATCH /api/catalogo/productos/{id}`); esta feature no lo reimplementa, solo lo consume como insumo para calcular margen real.
- El descuento manual (FR-009/FR-010) extiende el endpoint de línea de venta ya existente de 001 (`POST /api/ventas/{id}/lineas`), reutilizando la columna `venta_detalle.retail_disc` ya presente en el esquema sin uso, más un campo nuevo para el empleado autorizador (a definir en `data-model.md`) — no crea un flujo de venta paralelo (Principio VIII, DRY).
- No existe un rol RBAC "Analista de Pricing" en el esquema (solo `Jefe_Comercial`); `Jefe_Comercial` ejecuta también las acciones que `domain-context.md` asignaba a ese actor (OO-1.1.3, OO-1.4.1, OO-4.3.1) — misma decisión de alcance ya tomada para "Analista de Marketing" en la feature 002.
- El control de descuento manual combina dos capas: preventiva (autorización obligatoria de un Encargado_Tienda distinto del cajero, sin excepción por monto, antes de que la línea se confirme — FR-009) y detectiva sobre el resultado (si el margen real de la línea ya autorizada cae bajo el mínimo, se marca para revisión posterior, sin bloquear la venta — FR-010). Esta es una corrección de una ronda anterior de este mismo documento, que había interpretado — a partir de la redacción literal del BSC ("reportar"/"revisar") — que ningún control preventivo era necesario; el usuario aportó práctica real del sector (autorización de supervisor con PIN, sin excepción de monto, para evitar "sweethearting") y confirmó exigir la capa preventiva. `domain-context.md` no necesita cambio: OO-1.3.1/OO-1.3.2 siguen describiendo el reporte y la revisión, que ahora ocurren sobre descuentos ya autorizados.
- OT-4.3 (comparación de precio vs. competencia) no tenía ninguna feature dueña en `domain-context.md`; se incorpora aquí por su cercanía temática directa con el resto de esta feature — decisión confirmada por el usuario.
- La captura de precios de competencia es manual para el catálogo sembrado (dataset Dunnhumby, barcode sintético — Principio VII, no se puede comparar contra competidores reales) y sigue siendo el método principal y obligatorio para cualquier producto; para productos agregados en vivo con código de barras real (FR-013 de 001) se suma Open Prices (prices.openfoodfacts.org) como fuente automática adicional, sin necesidad de aprobar un proveedor externo nuevo — es la misma familia de servicio que Open Food Facts, ya usada en 001 y documentada en `domain-context.md` sección 9 (no viola Principio III ni Principio VII, ver `research.md` §5). Esta corrección responde a la investigación de mercado que aportó el usuario sobre cómo el sector captura precios de competencia (por competidor nombrado, con relevancia geográfica) — de ahí la nueva entidad Competidor y los campos de tienda/promoción.
- La reclasificación ancla/nicho (FR-008) y los cambios de categoría de un producto no recalculan retroactivamente el margen ya reportado de sus ventas pasadas (Principio II).
