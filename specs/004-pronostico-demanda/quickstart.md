# Quickstart: Pronóstico de Demanda con Variables Exógenas (004-pronostico-demanda)

Guía de validación ejecutable — no contiene código de implementación (eso vive en `tasks.md` y en el código real). Sirve para comprobar que la feature funciona de punta a punta una vez implementada.

## Prerrequisitos

- Docker Desktop corriendo (solo PostgreSQL 16 — esta feature no usa MinIO/ClickHouse/Airflow, Principio III).
- `01_operativo_postgres.sql` aplicado sobre la base (50 tablas base + extensiones de 001, 002, 003 y 004).
- Catálogo sembrado con al menos un producto/tienda con más de 12 semanas de historial de ventas (para el Escenario 1) y otro con menos (para el Escenario 4, cold start).
- Un usuario autenticado con rol `Jefe_TI` y otro con rol `Jefe_Operaciones` (JWT emitido por 008; token de prueba mientras tanto, igual que en 001/002/003).
- El job mensual de entrenamiento y el job semanal de monitoreo deben poder ejecutarse manualmente además de por su cron — mismos endpoints de "forzar corrida" en entorno de desarrollo ya usados en 003.

## Levantar el entorno

```bash
docker compose up -d postgres
cd backend && alembic upgrade head && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Escenario 1 — Un modelo entrenado no impacta nada hasta que el Jefe de TI lo aprueba (US1, P1)

1. Forzar la corrida del job mensual de entrenamiento (`POST /api/forecasting/modelos/entrenar`).
2. **Verificar**: aparece un nuevo `modelo_demanda` en `GET /api/forecasting/modelos?estado=pendiente` con su `metrica_precision_validacion` (WAPE) ya calculada.
3. **Verificar**: para un producto/tienda con historial suficiente, `GET /api/forecasting/productos/{product_id}/tiendas/{tienda_id}/pronostico` todavía responde `pronostico_disponible: false` si nunca hubo un modelo aprobado — el modelo pendiente no se usa todavía (SC-002).
4. `POST /api/forecasting/modelos/{modelo_id}/aprobar`.
5. **Verificar**: ahora la misma consulta de pronóstico responde con `cantidad_pronosticada` y el `modelo_id` recién aprobado.

## Escenario 2 — Rechazar un modelo no interrumpe el que ya estaba en producción (US1, P1)

1. Con un modelo ya aprobado y vigente (Escenario 1), forzar un nuevo entrenamiento.
2. `POST /api/forecasting/modelos/{nuevo_modelo_id}/rechazar` con un motivo.
3. **Verificar**: el modelo anterior sigue apareciendo como el único con `estado = 'aprobado'`, y el pronóstico consultado en el Escenario 1 no cambia (FR-005).

## Escenario 3 — El punto de reposición y la sugerencia de compra usan el pronóstico cuando existe (US2, P2)

1. Con un modelo aprobado y pronóstico vigente para un producto/tienda (Escenario 1), forzar el cálculo diario de punto de reposición de 001.
2. **Verificar**: la alerta de reposición generada (`alertas_inventario`) para ese producto/tienda tiene `origen_calculo = 'modelo_pronostico'`.
3. Forzar la sugerencia semanal de orden de compra de 001 para el proveedor de ese producto.
4. **Verificar**: la línea de la orden sugerida (`orden_compra_detalle`) también tiene `origen_calculo = 'modelo_pronostico'` (FR-009, FR-010).

## Escenario 4 — Producto sin historial suficiente sigue cubierto por el respaldo de 001 (US2, P2 / Edge Case)

1. Elegir un producto/tienda con menos de 12 semanas de historial de ventas (o una tienda recién creada sin ningún modelo que la incluya).
2. Forzar el cálculo diario de punto de reposición y la sugerencia semanal de compra para ese producto/tienda.
3. **Verificar**: ambos se calculan igual (nunca quedan sin valor), y su `origen_calculo` es `rotacion_reciente` (FR-006, FR-008, SC-003).

## Escenario 5 — Monitoreo semanal detecta degradación de precisión (US3, P3)

1. Con un modelo vigente en producción y al menos una semana de ventas reales ya registradas después de su aprobación, forzar la corrida del job semanal de monitoreo (`POST /api/forecasting/monitoreo/calcular`).
2. **Verificar**: aparece una fila nueva en `GET /api/forecasting/modelos/{modelo_id}/monitoreo` con la métrica de esa semana.
3. Repetir con datos donde el pronóstico se aleje deliberadamente de la demanda real observada, por encima del umbral configurado.
4. **Verificar**: el modelo aparece en `GET /api/forecasting/monitoreo/alertas` (FR-012), y su histórico de monitoreo permite ver la tendencia, no solo el último valor (FR-013).

## Escenario 6 — Reporte mensual de demanda perdida por tienda y categoría (US4, P4)

1. Registrar varios `eventos_quiebre_stock` (FR-022 de 001) en tiendas y categorías de producto distintas durante el mes en curso.
2. `GET /api/forecasting/reportes/demanda-perdida?fecha_desde=...&fecha_hasta=...`.
3. **Verificar**: el reporte muestra el total estimado desglosado por tienda y por categoría (FR-014, SC-005); una tienda o categoría sin ningún evento de quiebre ese mes no aparece con demanda perdida (no se fuerza a cero ni es un error).
