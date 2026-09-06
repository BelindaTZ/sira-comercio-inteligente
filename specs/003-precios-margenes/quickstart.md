# Quickstart: Precios Dinámicos, Márgenes y Comparación de Competencia (003-precios-margenes)

Guía de validación ejecutable — no contiene código de implementación (eso vive en `tasks.md` y en el código real). Sirve para comprobar que la feature funciona de punta a punta una vez implementada.

## Prerrequisitos

- Docker Desktop corriendo (solo PostgreSQL 16 — esta feature no usa MinIO/ClickHouse/Airflow, Principio III).
- `01_operativo_postgres.sql` aplicado sobre la base (50 tablas + extensiones de 001, 002 y 003).
- `backend/.env` sin variables nuevas — el factor de sensibilidad es manual, no requiere credenciales de ningún servicio de ML. Open Prices no requiere API key para lectura (`research.md` §5).
- Catálogo sembrado con clasificación ancla/nicho y `clasificacion_abc` ya asignados (001), y al menos un producto agregado en vivo con código de barras real (para el Escenario 6).
- Un usuario autenticado con rol `Cajero`, otro `Encargado_Tienda` y otro `Jefe_Comercial` (JWT emitido por 008; token de prueba mientras tanto, igual que en 001/002).
- El job semanal de propuestas de ajuste y el job semanal de competencia deben poder ejecutarse manualmente (además de por su cron) para no depender de esperar una semana real durante la demo — exponer un comando o endpoint interno de "forzar corrida" solo en entorno de desarrollo (detalle de implementación, no de este documento).

## Levantar el entorno

```bash
docker compose up -d postgres
cd backend && alembic upgrade head && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Escenario 1 — Margen objetivo diferenciado ancla/nicho (US1/US2, P1/P2)

1. `PATCH /api/pricing/margenes/{product_category}` con `{margen_objetivo_pct: 20}` sobre una categoría con productos ancla y nicho.
2. `GET /api/pricing/productos/{product_id}/margen-efectivo` para un producto ancla de esa categoría, y para uno nicho.
3. **Verificar**: el margen objetivo efectivo del ancla es siempre menor que el del nicho, nunca el mismo valor (FR-007, SC-003).

## Escenario 2 — Propuesta de ajuste nunca se publica sin aprobación (US1, P1)

1. `PATCH /api/pricing/margenes/{product_category}` con un `factor_sensibilidad` (ej. 0.3) sobre una categoría con ventas recientes cuyo margen real se desvíe de su objetivo por más de la tolerancia (2pp por defecto).
2. Forzar la corrida del job semanal de propuestas.
3. **Verificar**: aparece una fila en `GET /api/pricing/propuestas?estado=pendiente`; `GET /api/catalogo/productos/{product_id}` todavía muestra el `precio_base` anterior — la propuesta no cambió nada por sí sola (SC-002).
4. `POST /api/pricing/propuestas/{propuesta_id}/aprobar`.
5. **Verificar**: `productos.precio_base` cambió al `precio_propuesto`, y `historial_precios` tiene una fila nueva vigente con `fecha_inicio = hoy` (FR-006).

## Escenario 3 — Descuento manual exige autorización de un Encargado_Tienda distinto, sin excepción por monto (US3, P3)

1. Iniciar una venta y agregar una línea (`POST /api/ventas` → `POST /api/ventas/{venta_id}/lineas`).
2. `POST /api/ventas/{venta_id}/lineas/{linea_id}/descuento` con un descuento pequeño (ej. $0.50) y `empleado_autoriza_id` igual al `empleado_aplica_id` (el mismo cajero) → **esperar 403**.
3. Repetir con `empleado_autoriza_id` de un empleado con rol `Jefe_TI` (no está en la lista de roles habilitados) → **esperar 403**.
4. Repetir con `empleado_autoriza_id` de un `Encargado_Tienda` real, distinto del cajero → **esperar 200**, sin importar que el monto sea pequeño (FR-009, SC-004).

## Escenario 4 — Descuento autorizado que cae bajo margen mínimo se marca sin bloquear la venta (US3, P3)

1. Repetir el paso 4 del Escenario 3 con un descuento grande, tal que el margen resultante quede bajo el margen objetivo efectivo del producto.
2. **Verificar**: la venta se confirma igual (`POST /api/ventas/{venta_id}/confirmar` → 200) — la autorización de FR-009 no depende de este resultado.
3. **Verificar**: `GET /api/pricing/margen-bajo?tienda_id={tienda_id}` incluye la línea, con `margen_bajo_minimo = true` (FR-010, SC-004).

## Escenario 5 — Cierre del ciclo de revisión de margen bajo (US3, P3)

1. Sobre la línea marcada del Escenario 4, `POST /api/pricing/margen-bajo/{venta_detalle_id}/revision` con `{accion_correctiva: "..."}`.
2. **Verificar**: `GET /api/pricing/margen-bajo?tienda_id={tienda_id}&revisado=false` ya no la incluye; `GET /api/pricing/margen-bajo?revisado=true` (sin `tienda_id`, vista consolidada de Jefe_Comercial) sí (FR-011, FR-012).

## Escenario 6 — Comparación de precio vs. competencia, con las tres fuentes (US5, P5)

1. Sobre un producto **sembrado** (barcode sintético): `POST /api/pricing/competidores` con un competidor de prueba, luego `POST /api/pricing/productos/{product_id}/precio-competencia` con un precio manual que se desvíe del propio por más del umbral (5% por defecto).
2. Forzar la corrida del job semanal de competencia.
3. **Verificar**: el producto aparece en `GET /api/pricing/competencia/alertas`, con `fuente_captura = "manual"` en su fila más reciente (FR-015, FR-016).
4. Sobre un producto **agregado en vivo** con código de barras real: no registrar nada manualmente, solo forzar la corrida del job semanal de competencia.
5. **Verificar**: si Open Prices tiene un precio reportado para ese código de barras, aparece una fila con `fuente_captura = "open_prices"` y `competidor_id = null` en `GET /api/pricing/productos/{product_id}/precio-competencia`; si Open Prices no tiene dato, no se crea ninguna fila y el producto simplemente no genera alerta — ninguno de los dos casos es un error (FR-014).
6. Sobre un producto sembrado sin ninguna fila en `precio_competencia`: **verificar** que no aparece en `GET /api/pricing/competencia/alertas` — ausencia de dato no es evidencia de desviación (Edge Case de `spec.md`).

## Escenario 7 — Reporte mensual de margen (US1, P1)

1. Con ventas confirmadas en varias categorías durante el mes en curso, `GET /api/pricing/reportes/margen?fecha_desde=...&fecha_hasta=...`.
2. **Verificar**: cada categoría con ventas muestra su margen real acumulado junto a su margen objetivo vigente, sin que Jefe_Comercial tenga que calcular la diferencia a mano (FR-003, FR-013).
