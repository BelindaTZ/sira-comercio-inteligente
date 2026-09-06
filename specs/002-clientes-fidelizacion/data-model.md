# Data Model: Clientes y Fidelización (002-clientes-fidelizacion)

**Fase 1 de `/speckit-plan`**. La mayoría de las tablas de esta feature ya existen en el esquema base de 50 tablas (`01_operativo_postgres.sql`, sembradas desde el dataset Dunnhumby — `clientes`, `clientes_demograficos`, `niveles_fidelizacion`, `cliente_clv`, `churn_score`, `campanas`, `campana_cliente`, `cupones`, `cupon_redimido`, `eventos_cliente`). Esta feature solo agrega lo que el spec exige y el esquema base no cubre: consentimiento de datos, severidad de churn, clasificación de campaña propia de SIRA, grupo de control por campaña, resultado de uplift, y el registro de envío de cupón (necesario para calcular tasa de redención — el esquema base solo registra la redención, no el envío). Todos los cambios son aditivos (Principio VIII).

## 1. Cliente

- **Tabla**: `clientes` (ya existe; extendida en la ronda anterior).
- **Campos clave**: `household_id` (PK, natural del dataset), `nombre`, `email` (UNIQUE), `telefono`, `fecha_nacimiento`, `fecha_registro`, `activo`, `consentimiento_datos` (BOOLEAN NOT NULL, default `true` para filas sembradas — grandfathering), `fecha_consentimiento_datos` (TIMESTAMP NOT NULL).
- **Relaciones**: 1:1 con Datos Demográficos; 1:N con CLV histórico, Score de Churn, Ventas (household_id en `ventas`, ya resuelto en 001), Eventos de Cliente, Redenciones de Cupón; N:M con Campañas vía `campana_cliente`.
- **Validación**: `email` único; registro nuevo rechazado solo si el email ya existe (FR-001). El consentimiento se captura obligatoriamente en el alta — no tiene default a nivel de aplicación para clientes nuevos (el default `true` de la columna es exclusivamente para grandfathering de datos sembrados, ver `research.md` §5 y Assumptions de `spec.md`). `consentimiento_datos` es editable después del alta vía `PATCH` (FR-002) — cada cambio actualiza `fecha_consentimiento_datos`.
- **Transiciones de estado**: `activo=true` → `activo=false` + anonimización de `nombre`/`email`/`telefono`/`fecha_nacimiento` al darse de baja (FR-003, UPDATE real, conserva `household_id`). No hay transición inversa (un cliente anonimizado no se reactiva; si vuelve a comprar, se trata como alta nueva — Assumption ya documentada). Independiente de esa transición, `consentimiento_datos` alterna libremente `true ⇄ false` mientras el cliente sigue `activo` (revocar/otorgar, FR-002) — no anonimiza nada, solo activa/desactiva el gating de FR-001.

## 2. Datos Demográficos

- **Tabla**: `clientes_demograficos` (ya existe, sin cambios).
- **Campos clave**: `household_id` (PK/FK a `clientes`), `age`, `income`, `home_ownership`, `marital_status`, `household_size`, `household_comp`, `kids_count` — todos opcionales.
- **Relaciones**: 1:1 con Cliente, `ON DELETE CASCADE`.
- **Validación**: ninguno de estos campos es obligatorio para el alta de cliente (FR-004).

## 3. Nivel de Fidelización

- **Tabla**: `niveles_fidelizacion` (ya existe, sin cambios).
- **Campos clave**: `nivel_id` (PK), `nombre` (UNIQUE), `umbral_clv_min`.
- **Relaciones**: 1:N con CLV histórico (`cliente_clv.nivel_id`).
- **Validación**: los umbrales los define/ajusta el Jefe de Marketing (FR-007) — sin restricción de rango a nivel de esquema, la consistencia (que los umbrales no se crucen) es responsabilidad de la capa de servicio.

## 4. CLV (histórico)

- **Tabla**: `cliente_clv` (ya existe, sin cambios).
- **Campos clave**: `clv_id` (PK), `household_id` (FK), `nivel_id` (FK, nivel asignado según el score), `clv_score`, `fecha_calculo`. `UNIQUE(household_id, fecha_calculo)` — un registro por cliente y corrida del job semanal, nunca sobrescribe (Principio II).
- **Relaciones**: N:1 con Cliente, N:1 con Nivel de Fidelización.
- **Validación**: `clv_score` se calcula según la fórmula fija en `research.md` §1 (frecuencia + margen real normalizados, nunca gasto bruto puro — FR-005). Solo se calcula para clientes con `consentimiento_datos = true` (gating, FR-001) y con al menos 1 compra en la ventana (si no, no se inserta fila — Edge Case ya documentada).
- **Transiciones de estado**: la reclasificación de nivel (FR-008) es una nueva fila con `nivel_id` distinto en la siguiente `fecha_calculo`, no una actualización de la fila anterior.

## 5. Score de Churn

- **Tabla**: `churn_score` (ya existe; extendida en la ronda anterior con `severidad`).
- **Campos clave**: `churn_id` (PK), `household_id` (FK), `score` (0 a 1), `ciclo_compra_dias`, `severidad` (`en_riesgo`/`inactivo`/NULL), `fecha_calculo`. `UNIQUE(household_id, fecha_calculo)`.
- **Relaciones**: N:1 con Cliente.
- **Validación**: `ciclo_compra_dias` y `severidad` se calculan según `research.md` §2 (multiplicadores 1.5x/3x sobre el ciclo propio del cliente, nunca un umbral fijo de días — FR-009/FR-010). Solo se calcula para clientes con `consentimiento_datos = true`. Un cliente con menos de 2 compras no tiene fila (ciclo no calculable).
- **Transiciones de estado**: `severidad` puede pasar de NULL → `en_riesgo` → `inactivo` (o volver a NULL si el cliente vuelve a comprar dentro de su ciclo) en corridas sucesivas del job semanal — siempre como fila nueva, nunca UPDATE de una fila histórica.

## 6. Campaña

- **Tabla**: `campanas` (ya existe; **se extiende** con `categoria_sira`).
- **Campos clave**: `campaign_id` (PK, natural para campañas sembradas del dataset; **nuevo**: campañas creadas por el sistema usan `nextval('campanas_campaign_id_seq')`, secuencia que arranca en 100000 para no colisionar con los IDs ya sembrados — ver DDL abajo), `campaign_type` (campo original del dataset, TypeA/B/C — no se reutiliza para la clasificación de SIRA), `categoria_sira` (**nuevo**, `hito`/`reactivacion`, NULL para campañas sembradas que no aplican a ninguna de las dos), `start_date`, `end_date`.
- **Relaciones**: 1:N con `campana_cliente`, 1:1 con Resultado de Campaña (solo si `categoria_sira = 'reactivacion'`), 1:N con Cupón.
- **Validación**: `end_date >= start_date` (ya existente). Una campaña `categoria_sira = 'reactivacion'` no puede enviarse sin que exista al menos un `household_id` con `grupo = 'control'` en `campana_cliente` (FR-017, verificado en la capa de servicio antes de permitir el envío).

## 7. Miembro de Campaña (grupo tratado/control)

- **Tabla**: `campana_cliente` (ya existe; **se extiende** con `grupo`).
- **Campos clave**: `campaign_id` (FK), `household_id` (FK), `grupo` (**nuevo**, `tratado`/`control`, NULL para campañas que no son de reactivación). PK compuesta ya existente `(campaign_id, household_id)`.
- **Relaciones**: N:1 con Campaña, N:1 con Cliente.
- **Validación**: para una campaña `categoria_sira = 'reactivacion'`, todo miembro debe tener `grupo` definido antes del envío (FR-017); el grupo de control nunca recibe el cupón/incentivo (aplicado en la capa de servicio, no a nivel de esquema).

## 8. Resultado de Campaña (uplift)

- **Tabla**: `campana_resultado` (**nueva**).
- **Campos clave**: `campaign_id` (PK/FK a `campanas`), `tasa_retorno_tratado`, `tasa_retorno_control`, `uplift` (columna generada = `tasa_retorno_tratado - tasa_retorno_control`), `decision` (`aprobada_escalar`/`descartada`), `empleado_decide_id` (FK a `empleados`), `fecha_calculo`.
- **Relaciones**: 1:1 con Campaña.
- **Validación**: solo existe para campañas `categoria_sira = 'reactivacion'` ya cerradas. `uplift` compara ambas tasas de retorno, nunca solo la tasa de redención de cupones (FR-018, requisito duro). `decision` la toma el Jefe de Marketing en base al `uplift` calculado (FR-019).

## 9. Cupón

- **Tabla**: `cupones` (ya existe, sin cambios de esquema).
- **Campos clave**: `coupon_upc`, `product_id` (FK a `productos`), `campaign_id` (FK a `campanas`). PK compuesta `(coupon_upc, product_id, campaign_id)`.
- **Relaciones**: N:1 con Producto, N:1 con Campaña.
- **Validación/Nota**: para el cupón automático de hito (FR-013), el `product_id` se elige del catálogo entre los productos con `es_ancla = true` (mismo concepto ya definido en 001 para productos diseñados a atraer tráfico — se reutiliza sin inventar un nuevo tipo de "producto promocional", Principio VIII/DRY). La regla exacta de selección (ej. mayor margen entre los ancla vigentes) es responsabilidad de la capa de servicio, documentada en el `tasks.md` de esta feature.

## 10. Cupón Enviado

- **Tabla**: `cupon_enviado` (**nueva** — gap detectado: el esquema base solo registraba la *redención* de un cupón, no su *envío*; sin un registro de envío no hay denominador para calcular la tasa de redención que pide FR-014).
- **Campos clave**: `envio_id` (PK), `evento_id` (FK a `eventos_cliente`, NULL si el cupón se envía como parte de una campaña de reactivación en vez de un hito), `household_id` (FK), `coupon_upc`, `campaign_id` (FK a `campanas`), `fecha_envio`, `entregado` (BOOLEAN, default `true` — si SendGrid reporta fallo de entrega se marca `false`, pero el registro del envío/evento nunca se bloquea, Principio II).
- **Relaciones**: N:1 con Evento de Cliente (opcional), N:1 con Cliente, N:1 con Campaña.
- **Validación**: cada evento de hito (FR-012) genera exactamente un `cupon_enviado` al dispararse el cupón (FR-013).

## 11. Redención de Cupón

- **Tabla**: `cupon_redimido` (ya existe, sin cambios).
- **Campos clave**: `redemption_id` (PK), `household_id` (FK), `coupon_upc`, `campaign_id` (FK), `redemption_date`.
- **Relaciones**: N:1 con Cliente, N:1 con Campaña.
- **Validación**: la tasa de redención por hito (FR-014) = `COUNT(cupon_redimido) / COUNT(cupon_enviado)` agrupado por `eventos_cliente.tipo_evento` vía el join `cupon_enviado.evento_id`.

## 12. Evento de Cliente

- **Tabla**: `eventos_cliente` (ya existe, sin cambios).
- **Campos clave**: `evento_id` (PK), `household_id` (FK), `tipo_evento` (`cumpleanos`/`aniversario_registro`), `fecha`.
- **Relaciones**: 1:N con Cupón Enviado.
- **Validación**: generado diariamente solo para clientes `activo = true` y `consentimiento_datos = true` cuya fecha correspondiente sea ese día (FR-012).

## Trazabilidad cruzada

| Entidad | FR | OO / OT |
|---|---|---|
| Cliente | FR-001, FR-002, FR-003 | OO-B.1, OO-B.2, OO-B.3 |
| Datos Demográficos | FR-004 | OO-B.1 |
| Nivel de Fidelización | FR-006, FR-007, FR-008 | OT-3.1, OO-3.2.1, OO-3.2.2 |
| CLV (histórico) | FR-005 | OO-3.1.3, OT-3.1 |
| Score de Churn | FR-009, FR-010, FR-011 | OO-3.3.1, OO-3.3.2, OT-3.3 |
| Campaña | FR-012, FR-016 | OO-3.6.1, OO-3.4.1 |
| Miembro de Campaña | FR-017 | OO-3.4.1 |
| Resultado de Campaña | FR-018, FR-019 | OO-3.4.2, OO-3.4.3 |
| Cupón | FR-013 | OO-3.6.1 |
| Cupón Enviado | FR-013, FR-014 | OO-3.6.1, OO-3.6.2 |
| Redención de Cupón | FR-014, FR-015 | OO-3.6.2 |
| Evento de Cliente | FR-012 | OO-3.6.1 |
