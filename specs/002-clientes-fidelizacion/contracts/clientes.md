# Contrato: Módulo Clientes

Backend: `backend/src/modules/clientes/router.py`. RBAC: módulo `Marketing_CRM` (rol principal `Jefe_Marketing`; `Cajero`/`Encargado_Tienda` en las operaciones de alta/actualización/baja, igual que el resto de los maestros transversales — OO-B.1 a B.3).

## Perfil de cliente

### POST /api/clientes
Body: `{nombre, email, fecha_nacimiento?, consentimiento_datos: bool, datos_demograficos?: {age?, income?, home_ownership?, marital_status?, household_size?, kids_count?}}`. Rechaza 409 si `email` ya existe. Si `consentimiento_datos = false`, el cliente queda registrado sin quedar sujeto a CLV/churn/campañas (FR-001). Rol: `Cajero`/`Encargado_Tienda`.

### PATCH /api/clientes/{household_id}
Body parcial: `{nombre?, email?, telefono?, datos_demograficos?, consentimiento_datos?}`. No altera historial de ventas ni cálculos de CLV/churn ya calculados. Revocar `consentimiento_datos` (pasar a `false`) excluye al cliente de todo cálculo futuro de CLV/churn y de toda campaña/cupón segmentado — sin anonimizar el resto de sus datos ni requerir `DELETE`; volver a pasarlo a `true` lo reincorpora hacia adelante. Actualiza `fecha_consentimiento_datos` en cada cambio. (FR-002). Rol: `Cajero`/`Encargado_Tienda`.

### DELETE /api/clientes/{household_id}
Baja + anonimización real (`nombre`, `email`, `telefono`, `fecha_nacimiento` reemplazados; `household_id` se conserva). (FR-003). Rol: `Encargado_Tienda`.

### GET /api/clientes
Query: `search, activo, nivel_fidelizacion_id`. Paginado, filtros reactivos (Principio XII). Devuelve, por cliente, su `clv_score`/nivel y `severidad` de churn más recientes (join contra `cliente_clv`/`churn_score`, última `fecha_calculo`).

### GET /api/clientes/{household_id}
Detalle: perfil + datos demográficos + CLV actual + churn actual + eventos/cupones recientes.

## Fidelización (CLV)

### GET /api/clientes/niveles-fidelizacion
Lista niveles y sus `umbral_clv_min`. (FR-006)

### PATCH /api/clientes/niveles-fidelizacion/{nivel_id}
Body: `{umbral_clv_min}`. (FR-007). Rol: `Jefe_Marketing`.

## Riesgo de fuga (churn)

### GET /api/clientes/riesgo-fuga
Query: `severidad` (`en_riesgo`|`inactivo`), paginado. Cada fila trae `ciclo_compra_dias` y `dias_desde_ultima_compra` ya calculados — el Jefe de Marketing nunca calcula esto manualmente (SC-005). (FR-011). Rol: `Jefe_Marketing`.

## Campañas por hito (automáticas)

### GET /api/clientes/{household_id}/eventos
Lista los eventos de hito (cumpleaños/aniversario) del cliente junto con el cupón enviado en cada uno (`cupon_enviado`) y si fue redimido. Uso principalmente de auditoría/soporte — la generación del evento y el envío del cupón son automáticos (job diario, FR-012/FR-013), no se crean vía este endpoint.

### GET /api/clientes/cupones/tasa-redencion
Query: `tipo_evento?`. Devuelve `{tipo_evento, enviados, redimidos, tasa}` — `tasa = redimidos / enviados`, agrupado por tipo de evento. (FR-014). Rol: `Jefe_Marketing`.

### POST /api/clientes/cupones/{coupon_upc}/redimir
Body: `{household_id, campaign_id}`. Registra una fila en `cupon_redimido`. (FR-015). Rol: `Cajero` (en punto de venta, al aplicar el cupón).

## Campañas de reactivación (uplift)

### POST /api/clientes/campanas
Body: `{categoria_sira: "reactivacion", start_date, end_date, miembros: [{household_id, grupo: "tratado"|"control"}]}`. Crea la campaña (`campaign_id` desde `campanas_campaign_id_seq`) y sus miembros con grupo ya asignado. No envía nada todavía. (FR-016). Rol: `Jefe_Marketing`.

### POST /api/clientes/campanas/{campaign_id}/enviar
Envía el cupón/incentivo solo al grupo `tratado`. Responde 422 si la campaña no tiene al menos un miembro con `grupo = "control"` — sin grupo de control no hay forma de medir uplift al cierre (FR-017, requisito duro). Rol: `Jefe_Marketing`.

### POST /api/clientes/campanas/{campaign_id}/cerrar
Calcula `tasa_retorno_tratado`/`tasa_retorno_control` (proporción de cada grupo que volvió a comprar tras el envío) y el `uplift`, inserta `campana_resultado`. Nunca se basa solo en la tasa de redención del cupón (FR-018, requisito duro). Rol: `Jefe_Marketing` (mismo rol que crea, envía y decide la campaña — decisión de alcance, ver Assumptions de `spec.md`).

### POST /api/clientes/campanas/{campaign_id}/decision
Body: `{decision: "aprobada_escalar"|"descartada"}`. Requiere que `campana_resultado` ya exista (campaña cerrada). (FR-019). Rol: `Jefe_Marketing`.

### GET /api/clientes/campanas/{campaign_id}
Detalle: miembros (con grupo), y `campana_resultado` si ya fue calculado.

### GET /api/clientes/campanas
Query: `categoria_sira?`. Listado paginado.
