# Data Model: Promociones Inteligentes

Esta feature agrega 3 tablas nuevas (`regla_afinidad`, `candidato_liquidacion`, `configuracion_promociones`) y extiende de forma aditiva 2 tablas ya construidas por 002 (`campanas`, `cupon_enviado`). No agrega ninguna columna a `productos`: reutiliza el campo `clasificacion_abc` ya reservado desde 001, poblándolo por primera vez. Tampoco cambia el esquema de `display_locations`/`mailer_locations`/`promociones` (ya sembradas del dataset) — esta feature es la primera en llenarlas (`research.md` Decisión 6 de 004, boundary ya documentado ahí).

## 1. Regla de Asociación (Afinidad)

**Tabla**: `regla_afinidad`

**Campos clave**: `regla_id` (PK), `product_id_antecedente` (FK `productos`), `product_id_consecuente` (FK `productos`), `soporte` (DECIMAL), `confianza` (DECIMAL), `lift` (DECIMAL), `fecha_calculo`, `estado` (`vigente`/`reemplazada`/`desactivada`), `desactivada_por` (FK `empleados`, nullable), `fecha_desactivacion`.

**Relaciones**: N:1 con `productos` (dos veces: antecedente y consecuente). 1:N con `cupon_enviado` (vía `regla_afinidad_id`).

**Validación**: `product_id_antecedente <> product_id_consecuente`. `CHECK (estado IN ('vigente','reemplazada','desactivada'))`. `CHECK (estado <> 'desactivada' OR (desactivada_por IS NOT NULL AND fecha_desactivacion IS NOT NULL))`. Solo las reglas `estado = 'vigente'` se evalúan para la recomendación en punto de venta (FR-003) y para el disparo del cupón de afinidad (FR-006).

**Transiciones**: cada corrida mensual marca las `vigente` anteriores como `reemplazada` e inserta el nuevo cálculo como `vigente` (`research.md` Decisión 3). `vigente` → `desactivada` es la única transición manual (Jefe de Marketing, FR-002); no hay reactivación de una regla desactivada — un recálculo futuro del mismo par genera una fila nueva.

## 2. Extensión de `campanas` (002) — nuevo valor `afinidad`

**Cambio**: se amplía el `CHECK` existente de `categoria_sira` (agregado en 002 con `hito`/`reactivacion`) para admitir también `afinidad`.

**Rationale**: FR-006/FR-008 requieren un tercer tipo de campaña disparada por comportamiento de compra, no por fecha de hito ni por enrolamiento en una campaña de reactivación — se reutiliza la misma columna en vez de crear una tabla de campañas paralela (`research.md` Decisión 8). Se usa una única campaña `categoria_sira = 'afinidad'`, activa de forma continua, para todos los envíos de este tipo — no una por regla ni por envío.

## 3. Extensión de `cupon_enviado` (002) — origen en una regla de afinidad

**Cambio**: se agrega la columna `regla_afinidad_id BIGINT REFERENCES regla_afinidad(regla_id)`, nullable (NULL para cupones de hito o de campañas de reactivación, que no se originan en una regla de afinidad).

**Rationale**: Permite calcular la tasa de redención de cupones de afinidad por separado de los de hito (FR-008) sin necesitar una tabla de envíos propia — mismo criterio aditivo ya usado en 004 (`origen_calculo` sobre `alertas_inventario`/`orden_compra_detalle`).

**Validación**: `regla_afinidad_id IS NOT NULL` únicamente cuando `campaign_id` referencia la campaña `categoria_sira = 'afinidad'` (verificado en la capa de servicio, no como `CHECK` cruzado entre tablas).

## 4. Candidato de Liquidación

**Tabla**: `candidato_liquidacion`

**Campos clave**: `candidato_id` (PK), `product_id` (FK `productos`), `tienda_id` (FK `tiendas`), `semana`, `anio` (misma convención que `promociones`/`campanas`), `rotacion_reciente_calculada` (DECIMAL, unidades/semana), `descuento_sugerido_pct` (DECIMAL), `estado` (`candidato`/`ejecutado`), `fecha_ejecucion`, `ejecutado_por` (FK `empleados`, nullable).

**Relaciones**: N:1 con `productos`, `tiendas`. N:1 con `empleados` (quien ejecuta).

**Validación**: `UNIQUE (product_id, tienda_id, semana, anio)` — un solo candidato por producto/tienda/semana. `CHECK (estado = 'candidato' OR (fecha_ejecucion IS NOT NULL AND ejecutado_por IS NOT NULL))`. Solo se generan candidatos para productos con `productos.clasificacion_abc = 'C'` (FR-012, `research.md` Decisión 6).

**Uso**: si el Encargado de Tienda no ejecuta un candidato, este simplemente no transiciona de estado — la siguiente corrida semanal genera una fila nueva con `semana`/`anio` distintos, sin necesidad de un estado `descartado` explícito (Edge Case de `spec.md`).

## 5. Configuración de Promociones

**Tabla**: `configuracion_promociones`

**Campos clave**: `clave` (PK, ej. `soporte_minimo_regla`, `confianza_minima_regla`, `vigencia_cupon_afinidad_dias`, `rotacion_minima_liquidacion_semanal`, `descuento_liquidacion_pct`), `valor` (DECIMAL), `descripcion`.

**Relaciones**: Ninguna (tabla de configuración global, mismo patrón que `configuracion_pricing`/`configuracion_pronostico`).

**Validación**: Ninguna validación cruzada — son valores de negocio (`research.md` Decisiones 2 y 9), definidos por Jefe de Marketing (umbrales de afinidad) o Jefe de Operaciones (umbrales de liquidación) según la clave.

## 6. Clasificación ABC — sin tabla nueva, campo ya reservado en `productos`

**Cambio**: ninguno de esquema. El job mensual de clasificación (FR-009) actualiza `productos.clasificacion_abc` (columna `CHAR(1)` ya definida desde 001) para todo el catálogo, según el método Pareto por valor de venta acumulado dentro de cada `product_category` (`research.md` Decisión 5).

**Rationale**: El campo existe desde 001 sin que ninguna feature lo poblara — no se necesita ninguna tabla nueva, solo el job que finalmente lo calcula (Principio VIII). No se agrega dimensión de tienda a este campo (ver corrección documentada en el checklist de esta feature, Ronda 2).

## 7. Colocación Promocional — sin tabla nueva, reutiliza `promociones`/`display_locations`/`mailer_locations`

**Cambio**: ninguno de esquema. Esta feature es la primera en insertar filas en `promociones` (`product_id`, `tienda_id`, `display_location`, `mailer_location`, `semana`, `anio`) a través de un endpoint de gestión — hasta ahora la tabla solo era sembrada desde el dataset y consumida en solo lectura por 004.

**Rationale**: Cumple el boundary ya documentado en el spec.md de 002 ("la colocación de producto en anaquel/mailer... pertenece a la feature 005") y en el research.md de 004 (004 solo lee `promociones`, nunca la escribe) — sin duplicar ninguna tabla entre ambas features.

## Trazabilidad cruzada (entidad → FR → OO/OT)

| Entidad | FR | OO/OT |
|---|---|---|
| Regla de Asociación (`regla_afinidad`) | FR-001, FR-002, FR-003, FR-004, FR-005 | OO-3.5.1, OO-3.5.2 |
| Extensión `campanas`/`cupon_enviado` (cupón de afinidad) | FR-006, FR-007, FR-008 | OO-3.5.3 (nueva) |
| Clasificación ABC (`productos.clasificacion_abc`) | FR-009, FR-010 | OT-2.2 (OO-2.2.1, OO-2.2.2) |
| Regla de Liquidación / Candidato (`configuracion_promociones`, `candidato_liquidacion`) | FR-011, FR-012, FR-013, FR-014 | OT-2.3 (OO-2.3.1, OO-2.3.2) |
| Colocación Promocional (`promociones`/`display_locations`/`mailer_locations`) | FR-015, FR-016 | Boundary con 002/004, sin OO propia adicional |
