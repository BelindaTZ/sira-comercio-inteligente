# Quickstart: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel

**Nota**: los escenarios que involucran el job diario asumen un fixture de `dashboard_kpi`/`registro_publicacion_dashboard` ya poblado (no requieren ClickHouse/Airflow reales corriendo — esa cadena completa se valida en 010).

## Escenario 1 — Dashboard estratégico consolidado (US1, MVP)

1. Con un fixture de una publicación ya exitosa (`registro_publicacion_dashboard.tipo_dashboard='estrategico'`, `exito=true`) y sus `dashboard_kpi` asociados, como `Gerente_General`, `GET /api/v1/direccion/dashboard-estrategico`.
2. Verificar que la respuesta trae los KPIs de los OE con fuente real, la fecha de última publicación, y que el KPI de OE-4 aparece con `disponible: false` y `valor: null` (Edge Case).
3. Verificar que un KPI de OE-8 (ej. tasa de rotación, fuente 011) aparece con `disponible: true` y un valor real (corrección de esta ronda).

## Escenario 2 — Dashboard táctico por departamento y aislamiento entre Jefes (US2)

1. Con fixtures de `dashboard_kpi` para `dimension='Comercial'` y `dimension='Finanzas'`, como `Jefe_Comercial`, `GET /api/v1/ti/dashboards/tactico/Comercial`. Verificar que solo trae KPIs de Comercial.
2. Como el mismo `Jefe_Comercial`, `GET /api/v1/ti/dashboards/tactico/Finanzas`. Verificar 403.
3. Como `Gerente_General`, repetir el paso 2 y verificar 200 (acceso a todos).
4. Con un KPI marcado `disponible: false` por falta de datos suficientes (ej. modelo aún no entrenado), verificar que el resto del dashboard se muestra normalmente (Edge Case).

## Escenario 3 — Verificación de disponibilidad de dashboards operativos (US3)

1. Con un fixture donde `dashboard_operativo_estado` de una tienda tiene `fecha_ultima_actualizacion` de hace más de un día, como `Jefe_TI`, `GET /api/v1/ti/dashboards/operativos/verificacion?fecha=...`. Verificar que esa fila aparece con `disponible: false`.
2. `GET /api/v1/ti/dashboards/operativos/alertas` y verificar que solo trae esa fila (y ninguna de las que sí están al día).

## Escenario 4 — Forzar publicación manual en desarrollo (FR-010)

1. En entorno de desarrollo, como `Jefe_TI`, `POST /api/v1/ti/dashboards/estrategico/forzar-publicacion`. Verificar 202 y que se crea una fila nueva en `registro_publicacion_dashboard`.
2. Repetir la misma llamada simulando entorno de producción y verificar 403.
