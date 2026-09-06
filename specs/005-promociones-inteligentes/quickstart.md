# Quickstart: Promociones Inteligentes (005-promociones-inteligentes)

Guía de validación ejecutable — no contiene código de implementación (eso vive en `tasks.md` y en el código real). Sirve para comprobar que la feature funciona de punta a punta una vez implementada.

## Prerrequisitos

- Docker Desktop corriendo (solo PostgreSQL 16 — esta feature no usa MinIO/ClickHouse/Airflow, Principio III).
- `01_operativo_postgres.sql` aplicado sobre la base (50 tablas base + extensiones de 001, 002, 003 y 004).
- Catálogo sembrado con suficiente historial de ventas para que al menos un par de productos muestre afinidad real (para el Escenario 1) y al menos un producto con rotación consistentemente baja en al menos una tienda (para el Escenario 4).
- Un cliente sembrado con consentimiento de datos aceptado (FR-001 de 002) que haya comprado el producto antecedente de una regla sin el consecuente (para el Escenario 2).
- Un usuario autenticado con rol `Jefe_Marketing`, otro con `Jefe_Operaciones`, otro con `Encargado_Tienda` y otro con `Cajero` (JWT emitido por 008; token de prueba mientras tanto, igual que en 001-004).
- Los jobs mensuales (afinidad, clasificación ABC) y el semanal (candidatos a liquidación) deben poder ejecutarse manualmente además de por su cron — mismos endpoints de "forzar corrida" en entorno de desarrollo ya usados en 003/004.

## Levantar el entorno

```bash
docker compose up -d postgres
cd backend && alembic upgrade head && uvicorn src.main:app --reload
cd frontend && npm install && npm run dev
```

## Escenario 1 — El motor de afinidad genera una regla y la muestra en el punto de venta (US1, P1)

1. Forzar la corrida del job mensual de afinidad (`POST /api/promociones/reglas-afinidad/calcular`).
2. **Verificar**: aparece una nueva `regla_afinidad` con `estado = 'vigente'` para el par de productos con compra conjunta frecuente, con su soporte y confianza calculados.
3. Simular el inicio de un cobro con el producto antecedente de esa regla en el carrito, sin el consecuente (`GET /api/promociones/recomendacion-cross-sell?product_ids=...`).
4. **Verificar**: la respuesta recomienda el producto consecuente con su confianza (`recomendacion_disponible: true`).
5. Agregar también el producto consecuente al carrito y volver a consultar.
6. **Verificar**: ya no se recomienda ese par (`recomendacion_disponible: false` para ese consecuente, FR-004).

## Escenario 2 — Desactivar manualmente una regla no accionable (US1, P1)

1. Con la regla del Escenario 1 vigente, `POST /api/promociones/reglas-afinidad/{regla_id}/desactivar`.
2. **Verificar**: la regla pasa a `estado = 'desactivada'` y la consulta de recomendación del Escenario 1 ya no la considera.

## Escenario 3 — Cupón de afinidad enviado proactivamente por correo (US2, P2)

1. Con una regla de afinidad vigente A→B, registrar una venta de un cliente con consentimiento aceptado que compra A sin B.
2. **Verificar**: se genera automáticamente un `cupon_enviado` con `regla_afinidad_id` apuntando a esa regla, asociado a la campaña `categoria_sira = 'afinidad'`, y el correo queda registrado como enviado (aunque SendGrid falle, Principio II).
3. Registrar una segunda venta del mismo cliente comprando A sin B otra vez, dentro de la ventana de vigencia configurada.
4. **Verificar**: no se genera un segundo cupón para el mismo par mientras el anterior siga vigente (FR-007).
5. `GET /api/promociones/cupones-afinidad/tasa-redencion`.
6. **Verificar**: la tasa se calcula por separado de la tasa de redención de cupones por hito de 002.

## Escenario 4 — Clasificación ABC y candidato a liquidación (US3, P3)

1. Forzar la corrida del job mensual de clasificación ABC (`POST /api/promociones/clasificacion-abc/calcular`).
2. **Verificar**: un producto con ventas consistentemente bajas dentro de su categoría queda con `clasificacion_abc = 'C'` a nivel de catálogo (no por tienda, Ronda 2 del checklist de esta feature).
3. Forzar la corrida del job semanal de candidatos a liquidación para la tienda donde ese producto también rota poco (`POST /api/promociones/liquidacion/candidatos/calcular`).
4. **Verificar**: el producto aparece en `GET /api/promociones/liquidacion/candidatos?tienda_id=...` con su descuento sugerido.
5. `POST /api/promociones/liquidacion/candidatos/{candidato_id}/ejecutar` como Encargado de Tienda.
6. **Verificar**: el candidato queda `estado = 'ejecutado'` con `fecha_ejecucion`/`ejecutado_por`.

## Escenario 5 — Un producto con ajuste de precio pendiente no se ofrece como candidato (US3, P3 / Edge Case)

1. Crear una `propuesta_ajuste_precio` (003) en estado `pendiente` para un producto ya clasificado `C`.
2. Forzar la corrida del job semanal de candidatos a liquidación.
3. **Verificar**: ese producto NO aparece en la lista de candidatos de ninguna tienda mientras la propuesta siga `pendiente` (FR-013).

## Escenario 6 — Registro de colocación en anaquel/mailer y su efecto observado (US4, P4)

1. `POST /api/promociones/colocaciones` registrando un producto en una ubicación de anaquel destacado para una tienda y semana determinadas.
2. **Verificar**: la colocación queda consultable en `GET /api/promociones/colocaciones?tienda_id=...&semana=...&anio=...`.
3. `GET /api/promociones/colocaciones/{promocion_id}/efecto`.
4. **Verificar**: el sistema muestra las ventas de esa semana junto a las de un periodo de referencia sin colocación, sin calcular ninguna atribución causal automática (FR-016).
