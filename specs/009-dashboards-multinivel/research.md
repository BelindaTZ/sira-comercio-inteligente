# Research: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel | **Fecha**: 2026-09-06

## Decisión 1: `registro_publicacion_dashboard` — una tabla, tres tipos (patrón ya usado en `alertas_inventario`)

**Decisión**: una sola tabla con columna `tipo_dashboard IN ('estrategico','tactico','operativo')` registra cada intento de publicación (éxito o falla) para los tres niveles, en vez de tres tablas separadas de bitácora. Mismo criterio que `alertas_inventario` (001): dos o tres conceptos que comparten exactamente el mismo ciclo de vida (job corre → éxito/falla → fecha) no justifican estructuras separadas.

**Alternativas consideradas**: tres tablas (`publicacion_estrategico`, `publicacion_tactico`, `publicacion_operativo`) — rechazada por Principio VIII: las tres tendrían columnas idénticas salvo la referencia (red completa / módulo / tienda), que ya cabe en columnas nullable de una sola tabla.

## Decisión 2: `dashboard_kpi` — tabla única para estratégico y táctico, con `dimension` como referencia blanda

**Decisión**: una sola tabla `dashboard_kpi` almacena el snapshot de valores publicados tanto del dashboard estratégico como de los tácticos, diferenciados por `publicacion_id` (que ya indica el `tipo_dashboard`). La columna `dimension` (VARCHAR) contiene el código de Objetivo Estratégico (`'OE-1'`...`'OE-8'`) para filas estratégicas, o el nombre del módulo (`modulos.nombre`) para filas tácticas. No se modela como FK dura porque son dos espacios de conceptos distintos: el código OE es un concepto puramente del BSC (no existe una tabla `objetivos_estrategicos` en el esquema — el BSC vive en `domain-context.md`, no en la base de datos), mientras que el nombre de módulo sí podría ser FK pero solo para la mitad táctica de la tabla. Esta es una excepción documentada a "siempre FK cuando se pueda" (Principio VIII prioriza no duplicar estructura sobre una integridad referencial parcial).

**Alternativas consideradas**: dos tablas separadas (`dashboard_estrategico_kpi` con `oe_codigo` de texto, `dashboard_tactico_kpi` con `modulo_id` FK real) — más "correcta" en términos de integridad referencial, pero rechazada porque ambas tendrían columnas idénticas (`nombre_kpi`, `valor`, `disponible`) salvo la clave de dimensión, y el proyecto ya prefirió la tabla única con discriminador en un caso equivalente (`alertas_inventario`, Decisión 1 de esta misma feature).

## Decisión 3: `dashboard_operativo_estado` — verificación, no recálculo

**Decisión**: esta tabla NO almacena ningún KPI operativo (esos ya viven dentro de cada feature 001-007: `alertas_inventario`, `apertura_caja`/`cierre_caja`, `mermas`, etc.). Solo registra, por tienda y por nombre de dashboard operativo (`'alertas_reposicion'`, `'cuadre_caja'`, `'seguimiento_merma'`, ...), la fecha de su dato más reciente (`fecha_ultima_actualizacion`, calculada por el job diario como `MAX(fecha_hora)` de la tabla fuente correspondiente para esa tienda) y si está `disponible` (más de un día de antigüedad → `false`, FR-007). El job de verificación no toca ninguna tabla de otra feature más que con `SELECT MAX(...)` de solo lectura.

**Alternativas consideradas**: exponer un endpoint que cada feature deba "reportar su propio estado" activamente (patrón push) — rechazada por Principio VI (Features Autocontenidas): obligaría a modificar 001-007 ya cerradas para que llamen a esta feature nueva. El patrón elegido (pull, `MAX(fecha_hora)` de solo lectura) no requiere tocar ninguna feature existente.

## Decisión 4: qué departamentos tienen dashboard táctico propio

**Decisión**: de los 9 módulos RBAC, 6 tienen un Jefe de departamento dedicado y por lo tanto dashboard táctico propio: Comercial (Jefe_Comercial), Marketing_CRM (Jefe_Marketing), Operaciones (Jefe_Operaciones), Finanzas (Jefe_Finanzas), TI (Jefe_TI), RRHH (Jefe_RRHH). Los otros 3 no generan un dashboard táctico independiente: `Direccion` es exclusivamente el módulo del dashboard estratégico (Gerente General); `Ventas` no tiene un Jefe propio en el catálogo de roles — su supervisión táctica (ej. tiempo de cobro de 007) ya está cubierta por el acceso de solo lectura de `Jefe_Comercial` a `Ventas` (precedente de 007), así que no se duplica como un dashboard separado; `Sistema` es auditoría/configuración RBAC, sin KPI de negocio que consolidar (008 ya expone su propio reporte de auditoría).

**Alternativas consideradas**: un dashboard táctico por cada uno de los 9 módulos — rechazada porque 3 de ellos no tienen un KPI de negocio propio que consolidar ni un Jefe dedicado que lo consuma; hubiera sido una pantalla vacía o duplicada.

## Decisión 5: BSC — estado de KPIs sin fuente real (post-corrección)

Ver spec.md (Assumptions, corregido en esta ronda): OE-4 (Market Share/NPS) permanece sin fuente real — no hay canal de encuesta a cliente en el alcance del proyecto, se muestra como no disponible. OE-8 (rotación de personal/clima laboral) ya NO cae en este caso: 011-recursos-humanos, creada después del primer borrador de este spec.md, calcula ambos indicadores (tasa de rotación por tienda/periodo y resultado de clima laboral semestral) — el dashboard estratégico los muestra con datos reales de 011 desde que esta feature se implemente.

## Decisión 6: BSC / RBAC — resumen

Todos los FR trazan a OT-7.4 (OO-7.4.1 dashboard estratégico, OO-7.4.2 dashboards tácticos, OO-7.4.3 verificación operativa), bajo OE-7 TI/Datos. Gap de rol "Analista de Datos" resuelto como job automático (mismo patrón que 004), dejando a Jefe_TI como el único actor humano real de esta feature (verificación, US3) y a cada Jefe de departamento como consumidor de lectura de su propio dashboard táctico (US2).
