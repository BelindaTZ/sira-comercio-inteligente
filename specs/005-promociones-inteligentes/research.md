# Research: Promociones Inteligentes

## Decisión 1: Reglas de asociación con `mlxtend` (Apriori + association_rules), no `scikit-learn` ni una implementación propia

**Decision**: El cálculo mensual de afinidad de canasta (FR-001) usa `mlxtend.frequent_patterns` (`apriori` para encontrar conjuntos frecuentes de productos comprados juntos, `association_rules` para derivar reglas antecedente→consecuente con su soporte, confianza y lift), sobre una matriz binaria transacción×producto construida a partir de `venta_detalle` agrupado por `venta_id`.

**Rationale**: `scikit-learn` (ya reservado desde 002/004) no implementa reglas de asociación de forma nativa — es una librería de aprendizaje supervisado/no supervisado clásico, no de market basket analysis. `mlxtend` es la librería estándar de Python para esto, ampliamente documentada y mantenida, evita reimplementar Apriori a mano (Principio VIII, KISS). Es una dependencia local, sin llamadas externas, consistente con el resto del proyecto.

**Alternatives considered**: Implementar Apriori manualmente — descartado por reinventar algo ya resuelto por una librería madura sin ganancia real (Principio VIII). Usar reglas de co-ocurrencia simples (contar cuántas veces dos productos aparecen juntos, sin soporte/confianza formales) — descartado porque no distingue una afinidad real de una coincidencia esperada por popularidad general de ambos productos (dos productos que casi todo el mundo compra van a coincidir mucho sin que exista afinidad real); soporte y confianza (y opcionalmente lift) sí capturan esa diferencia.

## Decisión 2: Umbrales de soporte/confianza configurables, no fijos en código

**Decision**: El soporte mínimo y la confianza mínima para que un par de productos genere una regla (FR-001) son valores configurables en `configuracion_promociones` (`soporte_minimo_regla`, `confianza_minima_regla`), no constantes en el código.

**Rationale**: El umbral correcto depende del volumen de transacciones y de qué tan "accionable" quiere el Jefe de Marketing que sea una recomendación — mismo criterio ya usado para el umbral de historial mínimo de 004 y las tolerancias de 003: un valor de negocio se configura, no se fija en el código (Principio VIII, mismo patrón que `configuracion_pronostico`/`configuracion_pricing`).

**Alternatives considered**: Umbral fijo en el código — descartado porque obligaría a un despliegue nuevo para ajustar la sensibilidad del motor, algo que el Jefe de Marketing debe poder ajustar sin depender de TI (mismo argumento ya usado en 003/004 para sus configuraciones).

## Decisión 3: Reemplazo del conjunto de reglas cada corrida mensual, con desactivación manual persistente

**Decision**: Cada corrida mensual marca todas las reglas `vigente` anteriores como `reemplazada` e inserta el nuevo conjunto calculado como `vigente`. Una regla que el Jefe de Marketing desactivó manualmente (FR-002) queda en estado `desactivada` y no vuelve a activarse automáticamente aunque el mismo par de productos reaparezca en una corrida futura — el par simplemente se recalcula como una regla nueva (`vigente`) que el Jefe de Marketing puede volver a desactivar si lo considera necesario.

**Rationale**: Evita que un par de productos desactivado por no ser accionable (Edge Case de `spec.md`: "dos productos que solo coinciden por ser ambos de compra casi universal") vuelva a aparecer silenciosamente sin que nadie lo revise — cada corrida es una fotografía nueva del comportamiento de compra reciente, consistente con la cadencia mensual de OO-3.5.1.

**Alternatives considered**: Mantener reglas indefinidamente hasta que dejen de cumplir soporte/confianza — más complejo de auditar (¿por qué una regla sigue vigente 6 meses después?) y no se ajusta a la cadencia mensual de revisión que pide OO-3.5.1.

## Decisión 4: Solo una recomendación por producto en el carrito — la de mayor confianza

**Decision**: Cuando el frontend consulta reglas aplicables a los productos ya en el carrito (FR-003), si más de una regla vigente aplica al mismo producto, el backend devuelve únicamente la de mayor confianza (FR-005).

**Rationale**: Responde directamente al Edge Case de `spec.md` — mostrar varias recomendaciones a la vez distrae al cajero durante el cobro (Principio XII, un panel de trabajo no debe sobrecargar al usuario operativo con decisiones no esenciales). Confianza (probabilidad condicional de comprar el consecuente dado el antecedente) es más directamente interpretable como "qué tan buena es esta recomendación específica" que el soporte (que mide frecuencia general, no relevancia condicional).

**Alternatives considered**: Mostrar las top-3 recomendaciones — descartado por la misma razón de sobrecarga en un flujo operativo que debe ser rápido (OT-4.2, reducir tiempo de cobro, ya un objetivo de esta misma organización).

## Decisión 5: Clasificación ABC por valor de venta acumulado (Pareto clásico), no por unidades vendidas

**Decision**: La clasificación mensual de catálogo (FR-009) usa el método ABC clásico de inventarios: se ordenan los productos de una misma `product_category` por su valor de venta acumulado (`sales_value` de `venta_detalle`) en el periodo evaluado (ej. últimos 90 días), y se clasifican por contribución acumulada — A el primer ~70-80% del valor, B el siguiente ~15-20%, C el resto (umbrales exactos configurables).

**Rationale**: Es el método estándar de clasificación ABC de inventarios (principio de Pareto: una minoría de productos concentra la mayoría del valor de venta) — más robusto y más fácil de justificar a Jefe de Operaciones que una métrica de "velocidad de rotación" ad hoc, y correlaciona naturalmente con qué productos son más importantes de mantener bien abastecidos (A) frente a candidatos a liquidar si además rotan poco en una tienda específica (C, FR-012).

**Alternatives considered**: Clasificar por unidades vendidas en vez de valor — descartado porque dos productos con el mismo volumen de unidades pueden tener un valor de venta muy distinto (un producto de bajo precio unitario puede vender muchas unidades sin ser realmente relevante para el negocio); el valor de venta ya captura esa diferencia sin necesitar una segunda dimensión.

## Decisión 6: Candidatos a liquidación — clasificación de catálogo (ABC) + rotación local (por tienda), dos pasos separados

**Decision**: Un producto es candidato a liquidación en una tienda (FR-012) si (a) su clasificación de catálogo es `C` (calculada en red, Decisión 5) y (b) su rotación reciente específicamente en esa tienda (ej. unidades vendidas en las últimas 4 semanas) está por debajo del umbral configurado por el Jefe de Operaciones (`configuracion_promociones.rotacion_minima_liquidacion_semanal`). La clasificación ABC en sí NO se calcula por tienda — solo a nivel de catálogo (ver corrección de `spec.md`, Ronda 2 del checklist de esta feature).

**Rationale**: OO-2.2.1 dice literalmente "clasificar el catálogo" (sin mención de tienda) y el campo `clasificacion_abc` ya existe como columna simple en `productos` desde 001, sin dimensión de tienda — extender ese campo a producto×tienda hubiera requerido una tabla nueva no anticipada por el esquema base. En cambio, OO-2.3.2 sí es explícitamente "local" (cada tienda ejecuta su propia liquidación) — separar ambos pasos permite que un producto C a nivel de catálogo, pero que en una tienda puntual sigue rotando bien, no se ofrezca como candidato ahí (evita liquidar producto que sí se está vendiendo en esa sucursal).

**Alternatives considered**: Clasificación ABC por producto×tienda (tabla nueva) — descartado por requerir una tabla adicional sin que ninguna OO lo pida explícitamente, y porque complica innecesariamente la trazabilidad de un campo que el esquema base ya modeló como global (Principio VIII).

## Decisión 7: Exclusión de candidatos con ajuste de precio pendiente (boundary con 003)

**Decision**: Al generar la lista semanal de candidatos a liquidación (FR-012), el sistema excluye cualquier producto que tenga una fila en `propuesta_ajuste_precio` (003) con `estado = 'pendiente'` (FR-013).

**Rationale**: Evita que dos mecanismos independientes (el motor de pricing de 003 y la liquidación local de 005) cambien el precio efectivo del mismo producto en la misma ventana de tiempo, lo que generaría un resultado impredecible y dificultaría auditar cuál de los dos causó el cambio. La verificación es una consulta de solo lectura contra una tabla que ya existe (003) — no se duplica ni se sincroniza estado entre features (Principio VI).

**Alternatives considered**: Permitir ambos mecanismos simultáneamente y resolver el conflicto en la capa de presentación — descartado por trasladar al usuario un problema que el sistema puede evitar directamente en el cálculo (Principio XII, el sistema no debe generar una decisión que sabe de antemano que es contradictoria).

## Decisión 8: Cupón de afinidad — nuevo valor de `categoria_sira` en `campanas`, reutilizando la infraestructura de 002

**Decision**: El envío proactivo de un cupón por afinidad no aprovechada (FR-006) reutiliza `campanas` (extendiendo su `categoria_sira` ya existente con un tercer valor `afinidad`, además de `hito`/`reactivacion` de 002) y `cupon_enviado` (extendida con una columna `regla_afinidad_id` nullable, FK a la nueva tabla `regla_afinidad`). Se usa una única campaña de categoría `afinidad` activa de forma continua (no una campaña por cada regla ni por cada envío) — el detalle de qué regla originó cada envío vive en `cupon_enviado.regla_afinidad_id`, no en la campaña.

**Rationale**: Evita duplicar toda la infraestructura de cupones/campañas/redención ya construida en 002 (Principio VIII, DRY) — el cupón de afinidad es, en esencia, el mismo mecanismo (cliente + cupón + campaña + redención) con un disparador distinto (comportamiento de compra, no fecha de hito ni enrolamiento en campaña de reactivación). Una campaña por regla o por envío multiplicaría filas de `campanas` sin necesidad, ya que `campanas` no es la entidad que varía por envío.

**Alternatives considered**: Tabla de cupones propia para 005 — descartado por duplicar exactamente lo que `cupon_enviado`/`cupon_redimido` ya resuelven, incluyendo el cálculo de tasa de redención que FR-008 pide mantener separado por tipo (algo que ya se logra filtrando por `categoria_sira`/`regla_afinidad_id IS NOT NULL`, sin tabla nueva).

## Decisión 9: Anti-duplicado de cupón de afinidad — ventana de vigencia configurable

**Decision**: El sistema no envía un nuevo cupón de afinidad al mismo cliente para el mismo par de productos si ya existe un `cupon_enviado` con el mismo `household_id` y `regla_afinidad_id` cuya `fecha_envio` está dentro de una ventana de vigencia configurable (`configuracion_promociones.vigencia_cupon_afinidad_dias`) (FR-007).

**Rationale**: Sin este control, un cliente que compra frecuentemente el producto A sin B recibiría un cupón cada vez, saturando su correo y devaluando el mecanismo — mismo espíritu de "no repetir una notificación ya enviada mientras siga vigente" que rige el resto del sistema de cupones. Un valor configurable (no fijo) permite ajustar la frecuencia sin desplegar código nuevo, igual que el resto de umbrales de esta feature.

**Alternatives considered**: No reenviar nunca el mismo par a un mismo cliente (ventana infinita) — descartado porque una oportunidad de negocio real (el cliente sigue sin llevar el complementario meses después) quedaría permanentemente descartada por un único envío pasado.

## Decisión 10: Nueva OO-3.5.3 y asignación de OT-2.2/OT-2.3 a esta feature — resumen técnico

**Decision**: Como ya se documentó en `spec.md` (Assumptions) y en el checklist de esta feature, se incorpora **OO-3.5.3 (Sistema): Enviar cupón de descuento personalizado cuando se detecta una oportunidad de afinidad no aprovechada — por evento** bajo el OT-3.5 ya existente, y se asignan a esta feature los objetivos OT-2.2 (clasificación ABC) y OT-2.3 (liquidación de categoría C), sin feature dueña previa. El actor "Analista de Operaciones" de OO-2.2.1 se resuelve igual que en 004: job automático del sistema, sin rol RBAC nuevo — el actor humano real es `Jefe_Operaciones` vía OO-2.2.2 (ya existente).

**Rationale**: Se repite aquí porque determina directamente el diseño técnico: no existe ningún endpoint de "ejecutar clasificación ABC" pensado para que una persona lo dispare en producción (solo, igual que en 003/004, un endpoint de "forzar corrida" reservado a entorno de desarrollo).

**Alternatives considered**: Ya evaluadas y descartadas en `spec.md`/checklist — no se repiten aquí para evitar duplicar el mismo razonamiento en dos documentos.
