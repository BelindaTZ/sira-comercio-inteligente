---
título: Carga Inicial del Dataset (Dunnhumby → PostgreSQL)
estado: implementado — `backend/scripts/cargar_dataset_inicial.py` (2026-09-08). No es una feature de Spec Kit (sin User Stories/FR propios), mismo estatus que `scripts/seed_precio_competencia_sintetico.py`.
---

> **Implementación** (`python -m scripts.cargar_dataset_inicial`, flags `--reset` / `--muestra`):
> sigue este documento paso por paso. Notas de la implementación:
> - `medios_pago` se siembra vía `INSERT ... ON CONFLICT (nombre)` (§2).
> - `roles_puesto` estaba **vacío** en la base (no "reservado") — el script crea `Encargado_Tienda` / `Reponedor` / `Cajero` (§5).
> - `products.csv` tiene 1 fila con `product_id = 9e+05` (Excel) — se coerce con `int(float(v))`.
> - `demographics.csv`: `home_ownership` trae `Probable Homeowner/Renter` y vacíos, `marital_status` trae `Unmarried` — se normaliza a los valores del CHECK (`Homeowner/Renter/Unknown`, `Married/Single/Unknown`).
> - Inserción masiva con `asyncpg.copy_records_to_table` (COPY), todo en una transacción.
> - `--reset` hace `TRUNCATE ... RESTART IDENTITY CASCADE` de las 18 tablas del dataset (arrastra las derivadas de 002-012).
> - **El test suite (`pytest`) asume una base sin dataset** (sólo migraciones + seed RBAC, ver `conftest.py`). Con el dataset cargado, 2 tests de `test_riesgo_fuga.py` fallan por paginación (clientes reales empujan a los de la fixture fuera de la página) — es la contraparte esperada de "los 400+ tests usan fixtures, no el dataset".
> - Verificado con `--muestra` (3 tiendas / 4 semanas): 92,331 productos (EAN-13 válidos y únicos), `ventas.total` = Σ líneas exacto, ABC clasificado (Pareto real de 005).

# Carga Inicial del Dataset — Dunnhumby → PostgreSQL

## 0. Por qué existe este documento

Ninguna de las 12 features (001-012) especifica jamás la carga real del dataset Dunnhumby a PostgreSQL — todas la asumen como un prerrequisito ya cumplido ("carga inicial", ver `domain-context.md` línea 363 y `01_operativo_postgres.sql`: `productos.product_id`, `clientes.household_id`, `campanas.campaign_id` y `ventas.venta_id` llevan el comentario inline "natural key (viene del dataset)"). Es un hueco real del roadmap, detectado al implementar 010. Este documento cierra ese hueco: especifica exactamente cómo debe correr esa carga, para que Code la implemente como un script (`backend/scripts/cargar_dataset_inicial.py`), no como una feature nueva — no tiene User Stories ni FR propios, es infraestructura de datos igual que `seed_precio_competencia_sintetico.py` de 003.

**No bloquea nada de lo ya implementado**: los 400+ tests de 001-012 usan sus propias fixtures (datos mínimos insertados directamente en cada test), nunca el dataset real. Esta carga solo hace falta para tener datos reales y de volumen realista al usar el sistema manualmente o al correr el pipeline ELT de 010 contra algo real.

**Decisiones ya tomadas por el usuario (no reabrir)**:
- **Alcance de tiendas**: un puñado, no las 457 `store_id` reales del dataset — se eligen las **8 tiendas de mayor volumen de transacciones**, no las 457.
- **Volumen de transacciones**: **el año completo** (semanas 1-53), pero solo para esas 8 tiendas — no un subconjunto de semanas.

## 1. Orden de carga (respeta FKs; cada paso asume el anterior ya corrió)

1. `medios_pago` (ver §2 — hallazgo nuevo, no viene del dataset)
2. `display_locations`, `mailer_locations` (catálogos chicos, ver §7)
3. `fabricantes` (desde `products.csv`)
4. `productos` (desde `products.csv`, ver §3)
5. `tiendas` (síntesis, ver §4) — **antes** de leer `transactions.csv`, porque el mapeo `store_id → tienda_id` sale de ahí
6. `empleados` (síntesis por tienda, ver §5) — antes de `ventas` (requiere `cajero_id`)
7. `clientes` + `clientes_demograficos` (desde `demographics.csv`, ver §6)
8. `campanas`, `campana_cliente` (desde `campaigns.csv`/`campaign_descriptions.csv`)
9. `cupones`, `cupon_redimido` (desde `coupons.csv`/`coupon_redemptions.csv`)
10. `promociones` (desde los parquet de promociones, ver §7)
11. `ventas` + `venta_detalle` (desde `transactions.csv`, filtrado a las 8 tiendas — ver §8)
12. `margenes_objetivo` (síntesis, ver §9)
13. **Post-carga**: correr una vez la clasificación ABC real de 005 (`clasificar_abc_mensual`, o su lógica equivalente) contra las ventas recién cargadas — ver §3.4. Solo después de esto tiene sentido generar los precios de competencia sintéticos de 003 (§5 de su research.md), que ya asumen `clasificacion_abc = 'A'`.

## 2. `medios_pago` — hallazgo adicional, nunca sembrado en ningún lado

Verificado por grep en todo el repo: **ninguna migración ni el SQL base siembra `medios_pago`** — el comentario de la tabla ("Efectivo, Tarjeta, Digital") nunca se materializó fuera de los fixtures de test (`conftest.py`). Sembrar, en este orden (el `medio_pago_id` resultante es el que usan 001/007 por nombre):

```sql
INSERT INTO medios_pago (nombre) VALUES ('Efectivo'), ('Tarjeta'), ('Digital');
```

## 3. `productos` (desde `products.csv`, 92,331 filas — TODAS, sin filtrar por tienda)

Mapeo directo de columnas: `product_id`, `manufacturer_id`, `department`, `brand` (ya viene `'National'`/`'Private'`, coincide con el `CHECK`), `product_category`, `product_type`, `package_size`.

Columnas que el dataset NO trae (`productos.costo`/`precio_base` dicen explícitamente "NO viene del dataset, se enriquece"):

### 3.1 `costo` / `precio_base`
No hay precio real en `products.csv`. Usar el promedio de `sales_value / quantity` de ese `product_id` en `transactions.csv` (de las 8 tiendas elegidas, todo el año) como `precio_base`; si el producto no tiene ninguna transacción en esas 8 tiendas, `precio_base = NULL` (no inventar un precio sin ninguna señal). `costo = precio_base × 0.70` (margen del 30% parejo, documentado como heurística sintética — Principio VII) — cualquier valor razonable sirve porque **ningún FR de ninguna feature exige que este costo/margen inicial sea "correcto"**, solo que sea numéricamente consistente (`costo < precio_base`, `CHECK >= 0`).

### 3.2 `codigo_barras` (EAN-13 sintético, rango GS1 20-29, ya documentado en `domain-context.md`)
Algoritmo determinista por `product_id` (para que sea reproducible entre corridas):
1. Prefijo `"20"` + 10 dígitos derivados de `product_id` (ej. `str(product_id).zfill(10)[-10:]`, o un hash estable truncado a 10 dígitos si `product_id` tiene más de 10 dígitos — no es el caso aquí, el máximo real es `18316298`).
2. Calcular el dígito de checksum EAN-13 estándar (suma ponderada ×1/×3 alternada sobre los primeros 12 dígitos, módulo 10) y agregarlo como dígito 13.
3. Verificar unicidad contra el índice `UNIQUE` de `codigo_barras` (colisión → variar el hash) — con 92,331 productos contra 10^10 combinaciones el riesgo de colisión real es despreciable.

### 3.3 `imagen_url`
Placeholder genérico por `department` (31 valores distintos, no por `product_category` que tiene 304 — más manejable). Un ícono genérico por `department` en el bucket MinIO `producto-imagenes` (ej. `producto-imagenes/placeholder/{department_slug}.png`), documentado como no-real (Principio VII). Si no existen esos 31 íconos placeholder todavía en MinIO, Code puede usar un único ícono genérico compartido para los 31 hasta que existan (no bloquea nada).

### 3.4 `es_perecedero` / `vida_util_dias`
El dataset no lo indica explícitamente, pero `department` (columna limpia, 31 valores) lo insinúa con suficiente claridad para un heurístico documentado:

| `department` | `es_perecedero` | `vida_util_dias` |
|---|---|---|
| PRODUCE | true | 7 |
| MEAT, MEAT-PCKGD | true | 5 |
| SEAFOOD, SEAFOOD-PCKGD | true | 3 |
| DELI, SALAD BAR, RESTAURANT, CHEF SHOPPE | true | 4 |
| PASTRY | true | 4 |
| FROZEN GROCERY | true | 90 |
| FLORAL | true | 7 |
| Cualquier otro (GROCERY, DRUG GM, COSMETICS, HOUSEWARES, AUTOMOTIVE, etc.) | false | `NULL` |

### 3.5 `clasificacion_abc` / `es_ancla`
**No asignar en este paso.** Dejar `NULL`/`false` durante la carga de `productos` — recién tiene sentido calcularlos **después** de cargar `ventas`/`venta_detalle` (paso 11), corriendo la lógica real de clasificación ABC que ya construyó la feature 005 (`clasificar_abc_mensual`, Pareto sobre valor de venta acumulado) contra el año recién cargado. Evita inventar una segunda regla de clasificación paralela a la que 005 ya implementó (Principio VIII).

## 4. `tiendas` — síntesis (8 tiendas, elegidas por volumen real de transacciones)

1. Contar transacciones por `store_id` en `transactions.csv` (columna 2) y tomar los **8 `store_id` con más filas**.
2. Mapear cada uno a un `tienda_id` (orden de mayor a menor volumen): `codigo` = `T01`..`T08`.
3. `nombre`/`ciudad`: usar una ciudad ecuatoriana distinta por tienda (coherente con la narrativa "cadena de minimarkets en centros comerciales" de Marzú) — por ejemplo Quevedo, Guayaquil, Quito, Manta, Santo Domingo, Babahoyo, Machala, Portoviejo. El nombre exacto de cada tienda (ej. `"Marzú - Quevedo"`) es libre, documentado como sintético.
4. `fecha_apertura`: cualquier fecha anterior a `2017-01-01` (inicio real del dataset) — ej. `2016-06-01` para las 8, sin impacto funcional.
5. Guardar el mapeo `store_id → tienda_id` en memoria/un diccionario del script — se reutiliza en el paso 11 para filtrar y remapear `transactions.csv`.

## 5. `empleados` — roster mínimo por tienda (no viene del dataset, Dunnhumby no tiene datos de empleados)

Por cada una de las 8 tiendas: 1 `Encargado_Tienda`, 1 `Reponedor`, 2 `Cajero` (usando los `roles_puesto` ya reservados desde el diseño original) — 4 empleados × 8 tiendas = 32 empleados sembrados. `email` sintético único (ej. `cajero1.t01@marzu-seed.local`), `fecha_contratacion` anterior a `2017-01-01`. Cada venta cargada en el paso 11 elige un `cajero_id` al azar entre los 2 cajeros de su tienda (no hay forma de saber cuál cajero real atendió cada transacción del dataset — es una asignación sintética, documentada como tal).

No hace falta crear `usuarios`/login para estos empleados sembrados salvo que se quiera poder iniciar sesión como ellos — si se quiere, basta re-ejecutar el flujo de alta de 008 (`POST /rrhh/empleados` + `POST /sistema/usuarios`) sobre estos mismos empleados después de la carga.

## 6. `clientes` + `clientes_demograficos` (desde `demographics.csv`, TODOS los household_id — no solo los de las 8 tiendas)

- `clientes`: un registro por cada `household_id` distinto que aparezca en **cualquiera** de `transactions.csv`, `campaigns.csv` o `coupon_redemptions.csv` (2,469 households distintos en total) — no limitar a los de las 8 tiendas elegidas, porque `campanas`/`cupones` son conceptos a nivel de cliente, no de tienda, y limitar aquí rompería FKs de `campana_cliente`/`cupon_redimido` para households que compraron solo en una tienda no elegida. `email`/`nombre`/`telefono` quedan `NULL` (el dataset no los trae — son opcionales en el esquema); `fecha_registro` = fecha de la primera transacción de ese household en el dataset (o `2017-01-01` si no tiene ninguna transacción, solo aparece en campañas/cupones).
- `clientes_demograficos`: solo para los 801 `household_id` que aparecen en `demographics.csv` (el resto de clientes simplemente no tiene fila aquí — es 1:1 opcional, coincide con que en el dataset real la mayoría de households no participó del panel demográfico).

## 7. `campanas`/`campana_cliente`, `cupones`/`cupon_redimido`, `promociones` (todo el año, sin filtrar por tienda salvo donde el esquema lo pide)

- `campanas` ← `campaign_descriptions.csv` (`campaign_id`, `campaign_type`, `start_date`, `end_date`); `campana_cliente` ← `campaigns.csv` (`campaign_id`, `household_id`).
- `cupones` ← `coupons.csv` (`coupon_upc`, `product_id`, `campaign_id`); `cupon_redimido` ← `coupon_redemptions.csv` (`household_id`, `coupon_upc`, `campaign_id`, `redemption_date`).
- `display_locations`/`mailer_locations`: sembrar un código por cada valor distinto visto en los datos de promociones (`display_location`: `0,1,2,3,4,5,6,7,9,A`; `mailer_location`: `0,A,C,D,F,H,J,L,P,X,Z`, confirmados en `promotions_sample.csv`) con una descripción genérica (`"Código Dunnhumby: <valor>"`) si no se tiene a mano el glosario oficial del dataset — no bloquea nada, es solo texto descriptivo.
- `promociones`: el dataset completo de promociones (año completo) vive en `csv/promotions_weeks01-26.parquet` + `csv/promotions_weeks27-53.parquet` (mismas 5 columnas que `promotions_sample.csv`: `product_id, store_id, display_location, mailer_location, week`), léelos con `pandas.read_parquet` (puede requerir `pip install pyarrow` en el entorno de Code si no está ya). Filtrar por las 8 `store_id` elegidas igual que en `ventas` (§8) y remapear a `tienda_id`; `anio` no viene en el parquet — asumir `2017` para todas las filas de ambos años. `promotions_sample.csv` es solo una muestra de referencia, no la fuente completa — no cargarlo si ya se cargó desde los parquet (evitar duplicar).

## 8. `ventas` + `venta_detalle` (desde `transactions.csv`, filtrado a las 8 tiendas — año completo)

1. Filtrar `transactions.csv` a solo las filas cuyo `store_id` esté en el mapeo del paso 4 (año completo, semanas 1-53 — sin recortar por fecha).
2. Agrupar por `basket_id` → una fila de `ventas` por `basket_id` distinto (`venta_id = basket_id`, coincide con el comentario ya existente en el esquema).
   - `tienda_id` = mapeo del paso 4 (mismo `store_id` en todas las filas de ese `basket_id`, es consistente en el dataset real).
   - `household_id`: el del dataset — si viene vacío/0 en alguna fila de Dunnhumby (venta anónima real), dejar `NULL` (`ventas.household_id` ya es nullable, "NULL = venta anónima" según el comentario del esquema).
   - `cajero_id`: al azar entre los cajeros de esa tienda (§5).
   - `medio_pago_id`: al azar entre los 3 de §2 (no hay dato real de medio de pago en Dunnhumby) — distribución sugerida 45% Efectivo / 40% Tarjeta / 15% Digital, documentada como sintética.
   - `fecha_hora` = `transaction_timestamp` de cualquiera de sus filas (son iguales dentro del mismo `basket_id` en el dataset real).
   - `semana` = columna `week` del dataset (ya viene 1-53, coincide con el `CHECK`).
   - `total` = suma de `sales_value` de sus líneas (calculado, no confiar en ningún total del CSV).
3. `venta_detalle`: una fila por cada fila de `transactions.csv` de ese `basket_id` — `product_id`, `cantidad` (columna `quantity`, convertir a entero), `sales_value`, `retail_disc`, `coupon_disc`, `coupon_match_disc` van directos, sin transformación (ya existe la lógica de 003 que resta estos tres al calcular `margen_real`, ver `ventas/service.py::_precio_unitario_aplicado`).
4. Filas con `product_id` que no exista en `productos` (posible si `products.csv` no cubre el 100% de los `product_id` de `transactions.csv`) o `quantity <= 0`: descartar esa línea, registrar un conteo de filas descartadas en el log del script — no debe abortar la carga completa por una minoría de filas inconsistentes del dataset real (mismo espíritu que la calidad "fail-soft" que ya usa el pipeline ELT de 010).

## 9. `margenes_objetivo` — síntesis (304 `product_category` distintas, ninguna sembrada hoy)

Sembrar una fila por cada `product_category` distinta vista en `productos`, con `margen_objetivo_pct = 25.00` parejo para las 304 (heurística de arranque documentada — Jefe_Comercial las ajusta después vía FR-004 de 003, uno por uno o por lote, no hay urgencia de que el valor inicial sea "correcto").

## 10. Volumen esperado tras la carga (orden de magnitud, para que Code sepa qué esperar)

- `productos`: 92,331 (completo)
- `tiendas`: 8 · `empleados`: 32
- `clientes`: ~2,469 · `clientes_demograficos`: 801
- `ventas`/`venta_detalle`: bastante menos que el 1.47M de filas del CSV completo, porque se filtra a solo 8 de las 457 tiendas reales — el propio script debe loguear cuántas filas quedan tras el filtro antes de insertar, para que el usuario vea el tamaño real resultante.
