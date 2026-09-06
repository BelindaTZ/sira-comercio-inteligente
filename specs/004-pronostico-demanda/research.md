# Research: Pronóstico de Demanda con Variables Exógenas

## Decisión 1: Granularidad del pronóstico — producto × tienda × semana

**Decision**: El modelo pronostica la cantidad de unidades demandadas por producto y tienda para cada semana, usando la misma convención `semana`/`año` ya usada por `promociones` y `campanas` (numeración de semana del dataset Dunnhumby, `research.md` §5 de 003 la reutiliza también para Open Prices).

**Rationale**: Alinea la unidad de pronóstico con la unidad en la que ya llegan las variables exógenas (`promociones.semana/anio`) y con la cadencia de los OO que consume esta feature (OO-7.2.1 mensual para entrenar, OO-7.2.3 semanal para monitorear, OO-5.1.1 diario para el punto de reposición — el pronóstico semanal se distribuye entre los días de la semana en el cálculo diario de 001, no se re-pronostica cada día). Pronosticar a nivel diario multiplicaría el volumen de filas de entrenamiento sin variables exógenas nuevas que lo justifiquen (Principio VIII).

**Alternatives considered**: Pronóstico diario — más granular pero sin variables exógenas diarias reales en el dataset (las promociones y los quiebres ya están capturados a nivel semanal), así que no aportaría precisión adicional, solo costo computacional. Pronóstico mensual — demasiado grueso para alimentar el punto de reposición diario de 001 sin perder toda la variación de corto plazo.

## Decisión 2: Un solo modelo global, no un modelo por producto/tienda

**Decision**: Se entrena un único modelo de regresión (`scikit-learn`, ej. Gradient Boosting) sobre una tabla con una fila por combinación producto×tienda×semana ya observada, donde el producto, la tienda, la categoría y las variables exógenas son columnas de entrada (features) y la cantidad vendida esa semana es el objetivo. El mismo modelo pronostica para todos los productos y tiendas.

**Rationale**: El catálogo tiene ~92,331 productos sembrados en múltiplas tiendas — entrenar un modelo de series de tiempo individual por cada combinación (ej. SARIMAX de `statsmodels`) implicaría miles de modelos entrenándose cada mes, desproporcionado para el alcance académico de este proyecto y para Principio VIII (Simplicidad Justificada). Un modelo global captura patrones compartidos entre productos similares (misma categoría, mismo comportamiento ante promociones) y escala sin multiplicar el tiempo de entrenamiento por el tamaño del catálogo.

**Alternatives considered**: Un modelo de series de tiempo (`statsmodels` SARIMAX/ETS) por producto/tienda — más preciso en teoría para productos con suficiente historial propio, pero inviable de entrenar y mantener mensualmente a esta escala sin infraestructura de cómputo distribuido (fuera de alcance, y candidato a revisarse junto con la feature 010 si el proyecto avanza más allá del alcance académico). Un modelo por categoría de producto (intermedio) — se descarta por ahora por la misma razón de simplicidad; queda anotado como posible refinamiento futuro, no como requisito de esta especificación.

## Decisión 3: Variables exógenas y cómo se construyen

**Decision**: Por cada fila producto×tienda×semana del conjunto de entrenamiento, además del historial de ventas (rezagos y promedio móvil de semanas anteriores), se agregan estas variables explicativas:
- **Promoción activa**: si existe una fila en `promociones` para ese producto/semana/año (indicador binario; opcionalmente el tipo de exhibición/mailer).
- **Cambio de precio**: si `historial_precios` registra un cambio de precio vigente en esa semana para ese producto, y la magnitud del cambio (% respecto al precio anterior).
- **Quiebre de stock propio**: si existe un `eventos_quiebre_stock` para ese producto/tienda en esa semana (una semana con quiebre no debe leerse como "baja demanda", sino como demanda no capturada).
- **Quiebre de stock de la categoría** (aproximación al efecto de "un producto relacionado dejó de estar disponible", ver Assumptions de `spec.md`): proporción de productos de la misma `product_category` en esa tienda/semana que tuvieron al menos un evento de quiebre — una categoría con varios sustitutos agotados puede explicar un pico de demanda en los productos restantes de esa categoría.

**Rationale**: Responde directamente al requisito duro de FR-001/spec Edge Cases — el modelo no debe tratar una venta elevada explicada por promoción, precio o disponibilidad circunstancial como si fuera un aumento sostenido de la demanda base. Las tres primeras variables usan tablas que ya existen sin transformación adicional (`promociones`, `historial_precios`, `eventos_quiebre_stock`, todas de 001/el esquema base). La cuarta es la única derivada (una agregación simple, no una tabla nueva ni una relación de sustitución explícita entre productos, que no existe en el esquema y está fuera de alcance modelar aquí).

**Alternatives considered**: Modelar explícitamente qué producto es sustituto de cuál (ej. una tabla `producto_sustituto`) — más preciso pero requeriría una fuente de verdad sobre sustitución que no existe en el dataset ni fue pedida por ninguna OO; la aproximación por categoría cubre el mismo efecto observado sin inventar una relación no verificable (Principio VII).

## Decisión 4: Separación de entrenamiento y validación — por tiempo, no aleatoria

**Decision**: El conjunto de validación usado para calcular la métrica de precisión (FR-002) es siempre el periodo más reciente disponible (ej. las últimas 4 semanas antes de la fecha de entrenamiento), nunca una muestra aleatoria del historial completo.

**Rationale**: Una serie de tiempo con una partición aleatoria filtra información del futuro hacia el entrenamiento (el modelo "vería" indirectamente patrones de semanas posteriores a través de otras filas del mismo producto), inflando artificialmente la precisión medida. La partición temporal replica la situación real de producción: el modelo solo puede usar lo que ya pasó para pronosticar lo que viene.

**Alternatives considered**: Validación cruzada aleatoria (k-fold) — es el default de muchas herramientas de ML, pero es metodológicamente incorrecto para series de tiempo por la fuga de información descrita; se descarta explícitamente aunque sea más simple de implementar.

## Decisión 5: Métrica de precisión — WAPE, no MAPE ni RMSE puro

**Decision**: La métrica de precisión (FR-002, FR-011) es el **WAPE** (Weighted Absolute Percentage Error): `suma(|demanda real − pronóstico|) / suma(demanda real)`, calculada sobre el conjunto de validación o el periodo de monitoreo correspondiente.

**Rationale**: El dataset de retail tiene muchas combinaciones producto/tienda/semana con demanda real igual a cero o muy baja (productos de nicho, baja rotación) — el MAPE clásico (`|real-pronóstico|/real`) queda indefinido o se dispara a valores absurdos cuando la demanda real es cero, lo que rompería el umbral de aprobación de FR-003 con falsos negativos. El WAPE agrega el error y la demanda real por separado antes de dividir, así que una semana con demanda cero en un producto no distorsiona la métrica global, y el resultado sigue siendo un porcentaje interpretable para el Jefe de TI sin conocimiento estadístico profundo (Principio XII, mismo criterio de "métrica de negocio legible" ya aplicado al margen de 003).

**Alternatives considered**: MAPE — descartado por la razón de ceros ya explicada. RMSE — es una medida en las unidades originales (unidades de producto), no un porcentaje, así que un mismo RMSE significa cosas distintas para un producto de alta rotación que para uno de nicho; dificulta fijar un único umbral de aprobación global (FR-003) que tenga sentido para todo el catálogo a la vez.

## Decisión 6: Umbral mínimo de historial para entrenar un producto (cold start)

**Decision**: Un producto/tienda solo entra al entrenamiento mensual si tiene al menos 12 semanas de historial de ventas registrado; por debajo de eso, queda excluido de ese entrenamiento (FR-006) y cubierto por el respaldo de rotación reciente de 001 (FR-008) hasta que un entrenamiento futuro lo incluya.

**Rationale**: Un modelo de regresión con rezagos y promedios móviles necesita un mínimo de observaciones por combinación para que esas variables tengan sentido (con menos de un trimestre de historial, el "promedio móvil de 4 semanas" es en la práctica todo el historial disponible, sin poder separar patrón de ruido). Se eligió un valor de negocio configurable en `configuracion_pronostico`, no fijo en el código, siguiendo el mismo patrón ya usado en 001 (umbral de vencimiento) y 003 (tolerancia de ajuste).

**Alternatives considered**: Sin umbral mínimo (entrenar con cualquier historial disponible) — se descarta porque generaría pronósticos poco confiables para productos nuevos, exactamente el caso que FR-006/Edge Cases de `spec.md` pide excluir explícitamente.

## Decisión 7: Aprobación del modelo — mismo patrón de `propuesta_ajuste_precio` (003), no uno nuevo

**Decision**: Cada modelo entrenado queda en estado `pendiente` hasta que un Jefe de TI lo apruebe o rechace explícitamente (`aprobado_por`/`fecha_resolucion`, con el mismo `CHECK` de consistencia que ya usa `propuesta_ajuste_precio` de 003: `estado = 'pendiente' OR (fecha_resolucion IS NOT NULL AND aprobado_por IS NOT NULL)`). Solo puede haber un modelo con estado `aprobado` (vigente) a la vez — aprobar uno nuevo reemplaza automáticamente al anterior, marcándolo `reemplazado`.

**Rationale**: Es exactamente el mismo problema estructural que la propuesta de ajuste de precio de 003 (un cambio generado por el sistema no debe impactar la operación sin que una persona lo revise primero) — reutilizar el patrón evita inventar un mecanismo nuevo para el mismo tipo de control (Principio VIII, DRY a nivel de patrón, no de tabla compartida entre dominios distintos).

**Alternatives considered**: Aprobación automática si la métrica de precisión supera un umbral, sin intervención humana — se descartó porque el spec (FR-003, SC-002) exige explícitamente una aprobación humana registrada antes de producción; una aprobación puramente automática sería indistinguible, a efectos de control, de no tener aprobación en absoluto.

## Decisión 8: "Analista de Datos" y "Analista de Operaciones" sin rol RBAC propio — jobs automáticos, no un rol nuevo

**Decision**: OO-7.2.1 (entrenar) y OO-7.2.3 (monitorear) se implementan como jobs automáticos de APScheduler (mismo mecanismo ya montado en 002/003), sin actor humano — el único humano en el ciclo es el Jefe de TI, que aprueba/rechaza (OO-7.2.2) y revisa la alerta de degradación semanal. OO-5.2.2 (reporte de demanda perdida) lo ejecuta `Jefe_Operaciones`, sin un rol "Analista de Operaciones" separado.

**Rationale**: Ya documentado en `spec.md` (Assumptions) y en el checklist de esta feature — se repite aquí porque determina directamente el diseño técnico: no hay ningún endpoint de "registrar entrenamiento" ni "registrar monitoreo" pensado para que una persona lo dispare manualmente en producción (solo existe, igual que en 003, un endpoint de "forzar corrida" reservado a entorno de desarrollo para poder probar sin esperar el cron real).

**Alternatives considered**: Colapsar también OO-7.2.2 en un job automático (auto-aprobación) — descartado en la Decisión 7. Agregar un rol RBAC nuevo "Analista de Datos" — descartado por ser exactamente el mismo tipo de vacío ya resuelto sin rol nuevo en 002/003, y porque la acción en sí (entrenar) no requiere que una persona la dispare.
