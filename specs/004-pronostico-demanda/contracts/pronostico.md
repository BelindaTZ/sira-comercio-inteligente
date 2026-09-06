# Contratos: Pronóstico de Demanda con Variables Exógenas

**Backend**: `backend/src/modules/forecasting/router.py`, salvo el consumo del pronóstico en el cálculo diario de reposición (`modules/inventario/`) y en la sugerencia semanal de compra (`modules/compras/`), que extienden jobs ya existentes de 001 sin exponer un endpoint nuevo (`plan.md`, Project Structure). RBAC: módulo `TI` para aprobar/rechazar y ver el monitoreo; módulo `Operaciones` para el reporte de demanda perdida.

## Modelos de pronóstico (FR-001 a FR-005)

`GET /api/forecasting/modelos?estado=pendiente`
- Lista los modelos de pronóstico, filtrable por estado (pendiente/aprobado/rechazado/reemplazado).
- RBAC: `Jefe_TI`.
- 200: `[{modelo_id, fecha_entrenamiento, metrica_precision_validacion, estado, fecha_resolucion, aprobado_por}]`.

`GET /api/forecasting/modelos/{modelo_id}`
- Detalle de un modelo, incluyendo cuántos productos/tiendas cubre su pronóstico.
- RBAC: `Jefe_TI`.
- 200 / 404 si no existe.

`POST /api/forecasting/modelos/{modelo_id}/aprobar`
- Aprueba el modelo pendiente; reemplaza automáticamente al modelo vigente anterior (si existe), que pasa a `reemplazado` (FR-005).
- Body: `{observaciones?: string}`.
- RBAC: `Jefe_TI`.
- 200: modelo actualizado a `aprobado`. 409 si el modelo ya no está `pendiente`.

`POST /api/forecasting/modelos/{modelo_id}/rechazar`
- Rechaza el modelo pendiente; el modelo previamente aprobado (si existe) sigue vigente sin cambios (FR-005).
- Body: `{observaciones: string}` (motivo obligatorio).
- RBAC: `Jefe_TI`.
- 200: modelo actualizado a `rechazado`. 409 si el modelo ya no está `pendiente`.

`POST /api/forecasting/modelos/entrenar` *(solo entorno de desarrollo)*
- Fuerza la corrida del job mensual de entrenamiento sin esperar el cron real — mismo patrón que el endpoint de "forzar corrida" ya usado en 003 para sus jobs semanales.
- RBAC: `Jefe_TI`.
- 201: nuevo `modelo_demanda` en estado `pendiente`.

## Consulta de pronóstico por producto/tienda (FR-006 a FR-010)

`GET /api/forecasting/productos/{product_id}/tiendas/{tienda_id}/pronostico?semana=&anio=`
- Devuelve el pronóstico vigente (del modelo `aprobado`) para esa combinación y semana, si existe; si no existe, indica explícitamente que no hay pronóstico vigente (no es un error, FR-008).
- RBAC: `Jefe_Operaciones`, `Jefe_TI`.
- 200: `{cantidad_pronosticada, modelo_id, semana, anio}` o `{pronostico_disponible: false}`.

*Nota de implementación (sin endpoint propio)*: el cálculo diario del punto de reposición (`GET`/job interno de `modules/inventario/`, FR-020 de 001) y la sugerencia semanal de orden de compra (job interno de `modules/compras/`, FR-023 de 001) consultan internamente este mismo servicio antes de calcular con la lógica de rotación reciente — no exponen un endpoint nuevo, extienden el existente de 001 agregando el campo `origen_calculo` (`modelo_pronostico`/`rotacion_reciente`, FR-010) a su respuesta ya documentada en `contracts/inventario.md`/`contracts/compras.md` de 001.

## Monitoreo de precisión (FR-011 a FR-013)

`GET /api/forecasting/modelos/{modelo_id}/monitoreo`
- Histórico de métricas de precisión semanal de un modelo, para observar tendencia (FR-013).
- RBAC: `Jefe_TI`.
- 200: `[{semana, anio, metrica_precision, supero_umbral_alerta, fecha_calculo}]`.

`GET /api/forecasting/monitoreo/alertas`
- Lista los modelos cuya métrica de precisión semanal más reciente superó el umbral de alerta (FR-012).
- RBAC: `Jefe_TI`.
- 200: `[{modelo_id, semana, anio, metrica_precision}]`.

`POST /api/forecasting/monitoreo/calcular` *(solo entorno de desarrollo)*
- Fuerza la corrida del job semanal de monitoreo.
- RBAC: `Jefe_TI`.
- 201: nueva fila en `monitoreo_precision_modelo`.

## Reporte de demanda perdida (FR-014)

`GET /api/forecasting/reportes/demanda-perdida?fecha_desde=&fecha_hasta=&tienda_id=`
- Reporte mensual consolidado por tienda y categoría de producto, a partir de `eventos_quiebre_stock` (OO-5.2.2).
- RBAC: `Jefe_Operaciones`.
- 200: `[{tienda_id, product_category, cantidad_eventos, demanda_estimada_no_satisfecha}]`.

## Configuración de pronóstico (FR-002, FR-003, FR-006, FR-012)

`GET /api/forecasting/configuracion`
- Lista los umbrales configurables (`precision_minima_aprobacion`, `umbral_degradacion_semanal_pct`, `historial_minimo_semanas`).
- RBAC: `Jefe_TI`.
- 200: `[{clave, valor, descripcion}]`.

`PATCH /api/forecasting/configuracion/{clave}`
- Actualiza un umbral.
- Body: `{valor: number}`.
- RBAC: `Jefe_TI`.
- 200: valor actualizado. 404 si la clave no existe.
