# Quickstart: Plataforma de Datos Táctico-Estratégica

**Feature**: 010-plataforma-datos-tactico-estrategico

**Nota**: los escenarios de carga (2-4) pueden probarse contra un ClickHouse/MinIO de desarrollo o con mocks — no requieren el volumen completo de producción para validar el contrato de idempotencia/exclusión mutua.

## Escenario 1 — Definir el modelo de datos único (US1, MVP)

1. Como `Jefe_TI`, `POST /api/plataforma-datos/modelo` para registrar `fact_venta` y sus dimensiones (`dim_cliente`, `dim_producto`, `dim_tienda`, `dim_caja`, `dim_empleado`), cada una con su `tabla_origen_postgres`.
2. `GET /api/plataforma-datos/modelo` y verificar que las cuatro áreas de OT-7.1 (venta, cliente, inventario, caja) están cubiertas.
3. Registrar una entidad nueva con `activa: false` (Edge Case: tabla operativa nueva aún no incorporada) y verificar que el DAG no genera task para ella.

## Escenario 2 — Carga base e incremental (US2)

1. Ejecutar la primera corrida sobre `fact_venta` (`tipo_carga: "completa"`) y verificar que trae el histórico completo ya sembrado (~92,331 ventas).
2. Ejecutar la corrida diaria siguiente (`tipo_carga: "incremental"`) y verificar que solo trae ventas nuevas o modificadas desde la última corrida exitosa.
3. Simular una corrida que falla a medias y reprocesarla — verificar que no se duplican las filas ya cargadas (research.md Decisión 3).
4. Con una corrida en `estado: "en_progreso"` sobre `fact_venta`, intentar iniciar otra sobre la misma entidad y verificar el rechazo (índice único parcial, FR-005).
5. `GET /api/plataforma-datos/corridas?entidad_id=1` y verificar que muestra filas cargadas, filas con error, duración y resultado de cada corrida (FR-006).

## Escenario 3 — Calidad y trazabilidad (US3)

1. Cargar un lote con un registro que referencia un `product_id` inexistente y verificar que el resto del lote se carga con normalidad.
2. `GET /api/plataforma-datos/corridas/{corrida_id}/calidad` y verificar que ese registro aparece señalado con su descripción del problema.
3. Confirmar que el Jefe de TI puede ver origen, destino, filas y resultado de la corrida sin consultar los logs de Airflow directamente (SC-004).

## Escenario 4 — Política de gobierno de datos (US4)

1. Como `Jefe_TI`, `POST /api/plataforma-datos/politica` con el texto inicial.
2. `GET /api/plataforma-datos/politica` y verificar que devuelve ese texto.
3. Registrar una segunda versión y verificar que `GET /politica` ahora devuelve la nueva, mientras que `GET /politica/historial` sigue mostrando ambas.
