# API Contracts: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico | **Base path**: `/api/plataforma-datos`

> **Ronda 1 (post-implementación)**: base path real `/api/plataforma-datos` (plano, mismo
> patrón que 002-012 — el borrador decía `/api/v1/ti/plataforma-datos`) y formato de error
> del proyecto `{"error": {"code": "...", "message": "...", "details": ...}}` (el borrador
> decía `{"detail": ...}`). Los paths de abajo se dejan como estaban salvo el prefijo.

Todos los endpoints requieren JWT válido (008) y RBAC de módulo `TI` (data-model.md §RBAC).

## 1. Modelo de datos único (US1, FR-001)

`GET /modelo` — lista todas las entidades del modelo (`fact_venta`, dimensiones), su tabla de origen y si están activas.

`POST /modelo` — registra una entidad nueva.
```json
{"nombre_entidad": "dim_producto", "tipo": "dimension", "tabla_origen_postgres": "productos", "descripcion": "..."}
```
Respuesta 201, `activa: true` por defecto.

`PATCH /modelo/{entidad_id}` — activa/desactiva una entidad (`{"activa": false}`) o corrige su descripción.

RBAC: `Jefe_TI`.

## 2. Monitoreo de corridas (US2, US3, FR-006, FR-008)

`GET /corridas?entidad_id={id}&estado={estado}`

Respuesta 200:
```json
{
  "corridas": [
    {
      "corrida_id": 4021,
      "entidad_id": 1,
      "nombre_entidad": "fact_venta",
      "tipo_carga": "incremental",
      "origen": "postgres",
      "estado": "exitosa",
      "filas_cargadas": 812,
      "filas_error": 3,
      "fecha_inicio": "2026-09-06T02:00:00Z",
      "fecha_fin": "2026-09-06T02:04:12Z",
      "duracion_segundos": 252
    }
  ]
}
```
RBAC: `Jefe_TI`.

## 3. Detalle de registros de calidad de una corrida (US3, FR-007)

`GET /corridas/{corrida_id}/calidad`

Respuesta 200:
```json
{
  "corrida_id": 4021,
  "registros": [
    {"descripcion_problema": "referencia rota: product_id 99999 no existe en dim_producto", "identificador_registro": "venta_detalle_id=88213", "fecha_hora": "2026-09-06T02:03:40Z"}
  ]
}
```
RBAC: `Jefe_TI`.

## 4. Política de gobierno de datos (US4, FR-009, FR-010)

`GET /politica` — devuelve la versión vigente (mayor `fecha_creacion`).

`GET /politica/historial` — todas las versiones, ordenadas por fecha descendente.

`POST /politica` — registra una nueva versión (nunca reemplaza la anterior — append-only, research.md Decisión 5).
```json
{"texto": "Texto completo de la política de gobierno de datos..."}
```
Respuesta 201.

RBAC: `Jefe_TI`.

## 5. Forzar corrida manual — solo entorno de desarrollo (FR-012)

`POST /corridas/forzar`
```json
{"entidad_id": 1, "tipo_carga": "incremental"}
```
409 si ya existe una corrida `en_progreso` para esa `entidad_id` (FR-005). 422 si la entidad
está inactiva. Deshabilitado fuera de entorno de desarrollo — la ruta no se monta si
`app_env == "production"` (mismo patrón de 003-006/009).

Respuesta 202: `{"corrida_id": ..., "estado": "exitosa"}` (sin ClickHouse configurado la
corrida es de control — abre y cierra su fila en `corrida_carga` sin mover datos de negocio).

RBAC: `Jefe_TI`.
