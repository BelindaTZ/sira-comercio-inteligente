# Quickstart: Clientes y Fidelización (002-clientes-fidelizacion)

Guía de validación ejecutable — no contiene código de implementación (eso vive en `tasks.md` y en el código real). Sirve para comprobar que la feature funciona de punta a punta una vez implementada.

## Prerrequisitos

- Docker Desktop corriendo (solo PostgreSQL 16 — esta feature no usa MinIO/ClickHouse/Airflow, Principio III).
- `01_operativo_postgres.sql` aplicado sobre la base (50 tablas + extensiones de 001 y 002).
- `backend/.env` con `DATABASE_URL` y `SENDGRID_API_KEY` (ya usado por 001, se reutiliza sin cambios).
- Dataset Dunnhumby sembrado (clientes/`household_id`, ventas históricas) — sin historial de compras no hay CLV ni churn que calcular.
- Un usuario autenticado con rol `Cajero`, otro `Encargado_Tienda` y otro `Jefe_Marketing` (JWT emitido por 008; token de prueba mientras tanto, igual que en 001).
- El job semanal de CLV/churn y el job diario de hitos deben poder ejecutarse manualmente (además de por su cron) para no depender de esperar días reales durante la demo — exponer un comando o endpoint interno de "forzar corrida" solo en entorno de desarrollo (detalle de implementación, no de este documento).

## Levantar el entorno

```bash
docker compose up -d postgres
cd backend && alembic upgrade head && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Escenario 1 — Alta de cliente con consentimiento rechazado (US1, P1)

1. `POST /api/clientes` con `consentimiento_datos: false`.
2. Forzar la corrida del job semanal de CLV/churn.
3. **Verificar**: el cliente no aparece en `GET /api/clientes/{household_id}` con ningún `clv_score` ni `severidad` de churn — el gating de consentimiento (FR-001) lo excluyó del cálculo.

## Escenario 2 — Baja con anonimización real (US1)

1. Registrar un cliente con `POST /api/clientes` (consentimiento aceptado).
2. `DELETE /api/clientes/{household_id}`.
3. **Verificar**: `GET /api/clientes/{household_id}` devuelve `nombre`/`email`/`telefono`/`fecha_nacimiento` anonimizados y `activo: false`, pero el mismo `household_id` — sus ventas históricas (si las tuviera) siguen íntegras (FR-003).

## Escenario 3 — CLV nunca colapsa a gasto bruto (US2, P2)

1. Elegir dos clientes con historial de compras: cliente A con compras frecuentes y margen bajo, cliente B con una sola compra grande de alto margen.
2. Forzar la corrida del job semanal de CLV.
3. **Verificar**: `GET /api/clientes/{household_id}` de ambos — el nivel de fidelización de A no queda automáticamente por debajo del de B solo por gasto acumulado; el `clv_score` de cada uno refleja la combinación de frecuencia y margen real, no el total gastado (FR-005, SC-001).

## Escenario 4 — Riesgo de fuga con severidad (US3, P3)

1. Elegir un cliente cuyo `dias_desde_ultima_compra` supere 1.5x su `ciclo_compra_dias` pero no 3x.
2. Forzar la corrida del job semanal de churn.
3. **Verificar**: `GET /api/clientes/riesgo-fuga?severidad=en_riesgo` lo incluye; `GET /api/clientes/riesgo-fuga?severidad=inactivo` no.
4. Repetir con un cliente cuyo `dias_desde_ultima_compra` supere 3x su ciclo — debe aparecer solo en `severidad=inactivo` (FR-010, SC-002).

## Escenario 5 — Cupón automático de cumpleaños (US4, P4)

1. Elegir un cliente activo cuya `fecha_nacimiento` sea la fecha simulada de "hoy" en el entorno de prueba.
2. Forzar la corrida del job diario de hitos.
3. **Verificar**: se creó un `eventos_cliente` (`tipo_evento = 'cumpleanos'`) y un `cupon_enviado` asociado, sin intervención manual (FR-012, FR-013, SC-003). `GET /api/clientes/{household_id}/eventos` lo muestra.
4. `POST /api/clientes/cupones/{coupon_upc}/redimir` con ese cliente.
5. **Verificar**: `GET /api/clientes/cupones/tasa-redencion?tipo_evento=cumpleanos` refleja la redención (FR-014).

## Escenario 6 — Localizar a un cliente afiliado por cédula en el punto de venta (US1, Ronda 5)

1. Registrar un cliente nuevo indicando su número de cédula además de nombre y email.
2. En el punto de venta, buscar ese cliente usando únicamente su número de cédula (`GET /api/clientes?search=<cedula>`).
3. **Verificar**: el sistema lo encuentra y permite vincular su `household_id` a la venta en curso, sin necesidad del nombre o email (FR-001, SC-008).

## Escenario 7 — Campaña de reactivación con grupo de control obligatorio y uplift real (US5, P5)

1. Tomar 10 clientes de `GET /api/clientes/riesgo-fuga` (mezcla de `en_riesgo`/`inactivo`).
2. `POST /api/clientes/campanas` con `categoria_sira: "reactivacion"` y los 10 miembros, todos con `grupo: "tratado"` (sin ningún `control`).
3. `POST /api/clientes/campanas/{campaign_id}/enviar` → **esperar 422**: no se puede enviar sin grupo de control definido (FR-017).
4. Recrear la campaña marcando 5 miembros como `control` y 5 como `tratado`, y reenviar → esperar 200 (solo el grupo tratado recibe el incentivo).
5. Simular que algunos clientes de ambos grupos vuelven a comprar.
6. `POST /api/clientes/campanas/{campaign_id}/cerrar`.
7. **Verificar**: `GET /api/clientes/campanas/{campaign_id}` devuelve `tasa_retorno_tratado`, `tasa_retorno_control` y `uplift` — nunca solo la tasa de redención de cupones (FR-018, SC-004).
8. `POST /api/clientes/campanas/{campaign_id}/decision` con `{decision: "aprobada_escalar"}` (FR-019).
