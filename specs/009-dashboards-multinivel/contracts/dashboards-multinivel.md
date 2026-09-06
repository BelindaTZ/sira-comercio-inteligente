# API Contracts: Dashboards Multinivel

**Feature**: 009-dashboards-multinivel | **Base path**: `/api/v1`

Todos los endpoints requieren JWT válido (008) y RBAC de módulo (data-model.md §RBAC). Formato de error estándar del proyecto (`{"detail": "..."}`).

## 1. Dashboard estratégico (US1, FR-001, FR-002, FR-003)

`GET /direccion/dashboard-estrategico`

Respuesta 200:
```json
{
  "publicacion_id": 501,
  "fecha_publicacion": "2026-09-06T04:00:00Z",
  "kpis": [
    {"dimension": "OE-1", "nombre_kpi": "Rotación de inventario", "valor": 8.2, "disponible": true},
    {"dimension": "OE-4", "nombre_kpi": "Market Share", "valor": null, "disponible": false},
    {"dimension": "OE-8", "nombre_kpi": "Tasa de rotación de personal clave", "valor": 4.1, "disponible": true}
  ]
}
```
RBAC: `Gerente_General` (lectura global ya existente).

## 2. Dashboard táctico por departamento (US2, FR-004, FR-005)

`GET /ti/dashboards/tactico/{modulo_nombre}`

`modulo_nombre` ∈ `{Comercial, Marketing_CRM, Operaciones, Finanzas, TI, RRHH}` (research.md Decisión 4). 403 si el `modulo_nombre` solicitado no coincide con el módulo propio del rol autenticado (salvo `Gerente_General`, que puede consultar cualquiera).

Respuesta 200: mismo shape que el endpoint 1, con `kpis` filtrados a `dimension = modulo_nombre`.

RBAC: cada `Jefe_*` (lectura de su propio módulo únicamente), `Gerente_General` (todos).

## 3. Verificación diaria de dashboards operativos (US3, FR-006, FR-007)

`GET /ti/dashboards/operativos/verificacion?fecha={fecha}`

Respuesta 200:
```json
{
  "publicacion_id": 812,
  "fecha_verificacion": "2026-09-06T05:00:00Z",
  "estado_por_tienda": [
    {"tienda_id": 1, "nombre_dashboard": "alertas_reposicion", "fecha_ultima_actualizacion": "2026-09-06T03:10:00Z", "disponible": true},
    {"tienda_id": 3, "nombre_dashboard": "cuadre_caja", "fecha_ultima_actualizacion": "2026-09-04T22:00:00Z", "disponible": false}
  ]
}
```
RBAC: `Jefe_TI`.

## 4. Alertas de dashboards no disponibles (US3, FR-007)

`GET /ti/dashboards/operativos/alertas`

Respuesta 200: subconjunto del endpoint 3, solo filas con `disponible: false` (usa el índice parcial de data-model.md).

RBAC: `Jefe_TI`.

## 5. Forzar actualización manual — solo entorno de desarrollo (FR-010)

`POST /ti/dashboards/{tipo}/forzar-publicacion`

`tipo` ∈ `{estrategico, tactico, operativo}`. Body opcional `{"modulo_nombre": "Comercial"}` cuando `tipo = "tactico"`. Deshabilitado fuera de entorno de desarrollo (mismo patrón ya usado en 003-006) — 403 en producción.

Respuesta 202: `{"publicacion_id": ..., "estado": "en_proceso"}`.

RBAC: `Jefe_TI` (único rol que dispara jobs manualmente en desarrollo, mismo patrón de 003-006).
