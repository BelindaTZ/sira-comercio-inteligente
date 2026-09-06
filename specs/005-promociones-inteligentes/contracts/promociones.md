# Contratos: Promociones Inteligentes

**Backend**: `backend/src/modules/promociones/router.py`. RBAC: módulo `Marketing_CRM` para reglas de afinidad, cupones y colocación promocional; módulo `Operaciones` para clasificación ABC, reglas de liquidación y ejecución de candidatos; el punto de venta consulta `Ventas`/`Marketing_CRM` para la recomendación (sin endpoint nuevo en `modules/ventas/`, `plan.md`).

## Reglas de asociación / afinidad (FR-001 a FR-005)

`GET /api/promociones/reglas-afinidad?estado=vigente`
- Lista las reglas de asociación, filtrable por estado (vigente/reemplazada/desactivada).
- RBAC: `Jefe_Marketing`.
- 200: `[{regla_id, product_id_antecedente, product_id_consecuente, soporte, confianza, lift, estado, fecha_calculo}]`.

`POST /api/promociones/reglas-afinidad/{regla_id}/desactivar`
- Desactiva manualmente una regla vigente (FR-002).
- Body: `{motivo?: string}`.
- RBAC: `Jefe_Marketing`.
- 200: regla actualizada a `desactivada`. 409 si la regla ya no está `vigente`.

`GET /api/promociones/recomendacion-cross-sell?product_ids=1,2,3`
- Dado un conjunto de productos ya en el carrito, devuelve la recomendación de cross-sell de mayor confianza cuyo antecedente esté en el carrito y cuyo consecuente no lo esté (FR-003, FR-004, FR-005).
- RBAC: `Cajero`.
- 200: `{product_id_recomendado, confianza}` o `{recomendacion_disponible: false}` si ninguna regla vigente aplica.

`POST /api/promociones/reglas-afinidad/calcular` *(solo entorno de desarrollo)*
- Fuerza la corrida del job mensual de cálculo de afinidad sin esperar el cron real — mismo patrón que los endpoints de "forzar corrida" ya usados en 003/004.
- RBAC: `Jefe_Marketing`.
- 201: nuevo conjunto de reglas `vigente`.

## Cupón de afinidad (FR-006 a FR-008)

`GET /api/promociones/cupones-afinidad?household_id=`
- Lista los cupones de afinidad enviados, opcionalmente filtrados por cliente.
- RBAC: `Jefe_Marketing`.
- 200: `[{envio_id, household_id, product_id_ofrecido, regla_afinidad_id, fecha_envio, entregado, redimido}]`.

`GET /api/promociones/cupones-afinidad/tasa-redencion`
- Tasa de redención de cupones de afinidad, separada de la de cupones por hito (FR-008 — complementa `GET /api/clientes/cupones/tasa-redencion` de 002, que sigue cubriendo hito/reactivación).
- RBAC: `Jefe_Marketing`.
- 200: `{enviados, redimidos, tasa_pct}`.

*Nota de implementación (sin endpoint propio de envío)*: el envío del cupón de afinidad (FR-006) ocurre internamente al cerrar una venta que cumple la condición de afinidad no aprovechada — no es una acción disparada manualmente por un usuario, así que no existe un `POST` para "enviar cupón"; solo el job de desarrollo de abajo permite forzar la evaluación sin esperar una venta real.

`POST /api/promociones/cupones-afinidad/evaluar-venta/{venta_id}` *(solo entorno de desarrollo)*
- Fuerza la evaluación de una venta ya registrada contra las reglas vigentes, para poder probar el envío sin depender del flujo real de cobro.
- RBAC: `Jefe_Marketing`.
- 200: `{cupones_generados: number}`.

## Clasificación ABC (FR-009, FR-010)

`GET /api/promociones/clasificacion-abc?cambios_desde=`
- Lista productos cuya `clasificacion_abc` cambió desde la fecha indicada (por defecto, el último cálculo mensual) — FR-010.
- RBAC: `Jefe_Operaciones`.
- 200: `[{product_id, clasificacion_anterior, clasificacion_nueva, fecha_calculo}]`.

`POST /api/promociones/clasificacion-abc/calcular` *(solo entorno de desarrollo)*
- Fuerza la corrida del job mensual de clasificación ABC.
- RBAC: `Jefe_Operaciones`.
- 201: `{productos_reclasificados: number}`.

## Liquidación de categoría C (FR-011 a FR-014)

`GET /api/promociones/liquidacion/reglas`
- Consulta la regla de liquidación vigente (umbral de rotación mínima y descuento sugerido).
- RBAC: `Jefe_Operaciones`.
- 200: `{rotacion_minima_liquidacion_semanal, descuento_liquidacion_pct}`.

`PATCH /api/promociones/liquidacion/reglas`
- Actualiza el umbral y/o el descuento sugerido (FR-011).
- Body: `{rotacion_minima_liquidacion_semanal?: number, descuento_liquidacion_pct?: number}`.
- RBAC: `Jefe_Operaciones`.
- 200: regla actualizada.

`GET /api/promociones/liquidacion/candidatos?tienda_id=&semana=&anio=`
- Lista los candidatos a liquidación de una tienda para una semana (por defecto, la semana en curso) — FR-012, excluye automáticamente productos con ajuste de precio pendiente en 003 (FR-013).
- RBAC: `Encargado_Tienda`, `Jefe_Operaciones`.
- 200: `[{candidato_id, product_id, rotacion_reciente_calculada, descuento_sugerido_pct, estado}]`.

`POST /api/promociones/liquidacion/candidatos/{candidato_id}/ejecutar`
- Ejecuta la liquidación de un candidato (FR-014).
- RBAC: `Encargado_Tienda`.
- 200: candidato actualizado a `ejecutado` con `fecha_ejecucion`/`ejecutado_por`. 409 si ya no está `candidato`.

`POST /api/promociones/liquidacion/candidatos/calcular` *(solo entorno de desarrollo)*
- Fuerza la corrida del job semanal de generación de candidatos.
- RBAC: `Jefe_Operaciones`.
- 201: `{candidatos_generados: number}`.

## Colocación promocional en anaquel/mailer (FR-015, FR-016)

`GET /api/promociones/colocaciones?tienda_id=&semana=&anio=`
- Lista las colocaciones registradas (anaquel destacado / mailer) por tienda y semana.
- RBAC: `Jefe_Marketing`, `Encargado_Tienda`.
- 200: `[{promocion_id, product_id, tienda_id, display_location, mailer_location, semana, anio}]`.

`POST /api/promociones/colocaciones`
- Registra la colocación de un producto en una ubicación de anaquel destacado o mailer para una tienda y semana (FR-015).
- Body: `{product_id, tienda_id, display_location?, mailer_location?, semana, anio}`.
- RBAC: `Jefe_Marketing`, `Encargado_Tienda`.
- 201: colocación creada.

`GET /api/promociones/colocaciones/{promocion_id}/efecto`
- Compara las ventas del producto en la tienda durante la semana de colocación contra un periodo de referencia sin colocación, sin calcular una atribución causal automática (FR-016).
- RBAC: `Jefe_Marketing`.
- 200: `{ventas_semana_colocacion, ventas_semana_referencia}`.
