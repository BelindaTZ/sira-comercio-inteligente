"""Enriquecimiento genérico del catálogo para la demo.

El dataset Dunnhumby trae `product_type`, `product_category`, `package_size` y una
señal de precio sólo para ~1/3 de los productos — sin nombre comercial ni marca.
Este script rellena, de forma **determinista e idempotente** (sólo toca columnas
NULL), lo mínimo para que las pantallas de Catálogo e Inventario se vean
completas:

  - `productos.nombre`  ← `product_type` legible + `package_size`
  - `productos.marca`   ← marca genérica (pool fijo) o "Marca propia" si es Private
  - `productos.costo` / `precio_base` ← banda de precio por `department` cuando falta
  - `proveedores`       ← 8 distribuidores genéricos (si la tabla está vacía)
  - `lotes.codigo_lote_proveedor` ← `L-AAMM-Pnn-<lote_id>` cuando falta

Nada de esto pretende ser real: son datos de relleno para la demo. Los productos
dados de alta por la UI traen sus datos verdaderos (Open Food Facts / manual).
Todo en SQL de conjunto — corre en segundos aunque haya 90k+ productos.

Uso:
    python -m scripts.enriquecer_catalogo
"""

from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from src.core.database import AsyncSessionLocal

log = logging.getLogger("enriquecer_catalogo")

# Marcas inventadas (no son marcas reales) — pool fijo para asignación determinista.
MARCAS = [
    "Nordval", "Camino Real", "Frutos del Sur", "Andes Prime", "Selecta",
    "Vittal", "Doña Marta", "El Roble", "Pacífico", "Aurora",
    "Monteclaro", "Sabori", "Prado Verde", "Cumbre", "Bahía",
    "Tierra Nueva", "Origen", "Vívere", "Campo Lindo", "Astoria",
    "Delmar", "Norteño", "La Cosecha", "Reserva Andina",
]

PROVEEDORES = [
    ("Distribuidora Andes Ltda.", "ventas@andes.cl", "+56 2 2540 1100", "30 días"),
    ("Comercial Pacífico S.A.", "pedidos@pacifico.cl", "+56 2 2612 4300", "60 días"),
    ("Abastecimientos del Sur SpA", "contacto@abastesur.cl", "+56 41 220 8890", "30 días"),
    ("Logística Central Ltda.", "operaciones@logcentral.cl", "+56 2 2733 5510", "contado"),
    ("Importadora Monteclaro", "compras@monteclaro.cl", "+56 2 2985 7420", "45 días"),
    ("Frío Express Distribución", "frio@frioexpress.cl", "+56 2 2440 9020", "30 días"),
    ("Mayorista El Roble", "mayorista@elroble.cl", "+56 72 241 3360", "contado"),
    ("Alimentos Cumbre S.A.", "ventas@cumbre.cl", "+56 2 2891 6640", "60 días"),
]

# Banda de precio de venta (CLP) por department cuando el dataset no da señal.
BANDA_PRECIO: dict[str, tuple[int, int]] = {
    "GROCERY": (900, 4500),
    "PRODUCE": (600, 3200),
    "MEAT": (2500, 12000),
    "MEAT-PCKGD": (2200, 9000),
    "DELI": (1800, 8000),
    "PASTRY": (900, 4200),
    "SEAFOOD": (3000, 14000),
    "SEAFOOD-PCKGD": (2800, 11000),
    "DRUG GM": (1200, 9000),
    "NUTRITION": (2500, 18000),
    "SALAD BAR": (1500, 5000),
    "KIOSK-GAS": (700, 3500),
    "GARDEN CENTER": (1500, 20000),
    "SPIRITS": (3500, 25000),
    "COSMETICS": (2000, 15000),
    "FLORAL": (2500, 18000),
    "RESTAURANT": (2500, 9000),
}
BANDA_DEFECTO = (900, 6000)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    marcas_sql = "ARRAY[" + ",".join(f"'{m.replace(chr(39), chr(39) * 2)}'" for m in MARCAS) + "]"
    # CASE department → precio "objetivo" determinista (hash estable del product_id
    # dentro de la banda), redondeado a la centena; costo = 70% del precio.
    ramas = "\n".join(
        f"WHEN upper(trim(department)) = '{dep}' THEN {lo} + (abs(hashtext(product_id::text)) % {hi - lo})"
        for dep, (lo, hi) in BANDA_PRECIO.items()
    )
    lo_d, hi_d = BANDA_DEFECTO

    async with AsyncSessionLocal() as s:
        # 0 · normaliza a CLP los precios "reales" del dataset (vienen en USD,
        #     ~$0,50–$150) para que no convivan con los sintéticos en CLP.
        r = await s.execute(
            text("""
            UPDATE productos SET
              precio_base = round((precio_base * 950)::numeric / 100) * 100,
              costo = round((COALESCE(costo, precio_base * 0.70) * 950)::numeric / 100) * 100
            WHERE precio_base IS NOT NULL AND precio_base < 200
        """)
        )
        log.info("precio USD→CLP: %s productos", r.rowcount)

        # 1 · nombre + marca ------------------------------------------------
        r = await s.execute(
            text(f"""
            UPDATE productos SET
              nombre = COALESCE(nombre, left(
                initcap(regexp_replace(
                  COALESCE(NULLIF(trim(product_type), ''),
                           NULLIF(trim(product_category), ''),
                           'Producto genérico'), '\\s+', ' ', 'g'))
                || CASE WHEN NULLIF(trim(package_size), '') IS NOT NULL
                        THEN ' · ' || trim(package_size) ELSE '' END, 200)),
              marca = COALESCE(marca,
                CASE WHEN brand = 'Private' THEN 'Marca propia'
                     ELSE ({marcas_sql})[(product_id % {len(MARCAS)}) + 1] END)
            WHERE nombre IS NULL OR marca IS NULL
        """)
        )
        log.info("nombre/marca: %s productos", r.rowcount)

        # 2 · costo + precio_base cuando falta ----------------------------
        r = await s.execute(
            text(f"""
            UPDATE productos SET
              precio_base = round((
                CASE {ramas}
                     ELSE {lo_d} + (abs(hashtext(product_id::text)) % {hi_d - lo_d})
                END)::numeric / 100) * 100,
              costo = COALESCE(costo, round(((
                CASE {ramas}
                     ELSE {lo_d} + (abs(hashtext(product_id::text)) % {hi_d - lo_d})
                END)::numeric / 100) * 100 * 0.70, 2))
            WHERE precio_base IS NULL
        """)
        )
        log.info("precio sintético: %s productos", r.rowcount)

        # 3 · proveedores ------------------------------------------------
        if not await s.scalar(text("SELECT count(*) FROM proveedores")):
            for nombre, contacto, telefono, cond in PROVEEDORES:
                await s.execute(
                    text(
                        "INSERT INTO proveedores (nombre, contacto, telefono, condiciones_pago) "
                        "VALUES (:n, :c, :t, :cp)"
                    ),
                    {"n": nombre, "c": contacto, "t": telefono, "cp": cond},
                )
            log.info("proveedores: %s", len(PROVEEDORES))

        # 4 · codigo_lote_proveedor -----------------------------------
        r = await s.execute(
            text("""
            WITH provs AS (
                SELECT proveedor_id, row_number() OVER (ORDER BY proveedor_id) - 1 AS ix,
                       count(*) OVER () AS n
                FROM proveedores
            )
            UPDATE lotes l SET codigo_lote_proveedor =
                'L-' || to_char(COALESCE(l.created_at, CURRENT_TIMESTAMP), 'YYMM')
                || '-P' || lpad((p.ix + 1)::text, 2, '0') || '-' || l.lote_id
            FROM provs p
            WHERE l.codigo_lote_proveedor IS NULL AND p.n > 0 AND p.ix = l.lote_id % p.n
        """)
        )
        log.info("codigo_lote_proveedor: %s lotes", r.rowcount)

        # 5 · refresca los vencimientos de los lotes perecederos para que la demo
        #     se vea "actual" sin importar cuándo se cargó el dataset: ventana de
        #     -7 a +67 días desde hoy (≈9% vencidos, el resto repartido).
        r = await s.execute(
            text("""
            UPDATE lotes l SET fecha_vencimiento =
                CURRENT_DATE + ((abs(hashtext(l.lote_id::text)) % 75) - 7)
            FROM productos p
            WHERE p.product_id = l.product_id AND p.es_perecedero
              AND l.codigo_lote_proveedor LIKE 'L-%'
        """)
        )
        log.info("vencimientos refrescados: %s lotes", r.rowcount)

        # 6 · realinea las alertas de vencimiento pendientes con las fechas nuevas
        if r.rowcount:
            await s.execute(
                text(
                    "DELETE FROM alertas_inventario WHERE tipo = 'vencimiento' AND estado = 'pendiente'"
                )
            )
            r = await s.execute(
                text("""
                INSERT INTO alertas_inventario (tipo, product_id, tienda_id, lote_id, estado)
                SELECT 'vencimiento', l.product_id, l.tienda_id, l.lote_id, 'pendiente'
                FROM lotes l
                WHERE l.fecha_vencimiento IS NOT NULL
                  AND l.fecha_vencimiento <= CURRENT_DATE + 7
            """)
            )
            log.info("alertas de vencimiento regeneradas: %s", r.rowcount)

        # 7 · ubicación en sala de los SKU con inventario (pasillo/góndola
        #     determinista por department). Se cubre solo lo que se ve.
        r = await s.execute(
            text("""
            WITH deps AS (
                SELECT p.department, dense_rank() OVER (ORDER BY p.department) AS d
                FROM (SELECT DISTINCT department FROM productos WHERE department IS NOT NULL) p
            )
            INSERT INTO ubicacion_producto (product_id, tienda_id, pasillo, gondola)
            SELECT i.product_id, i.tienda_id,
                   'Pasillo ' || lpad(((COALESCE(d.d, 1) % 12) + 1)::text, 2, '0'),
                   'G-' || lpad(((abs(hashtext(i.product_id::text)) % 24) + 1)::text, 2, '0')
            FROM inventario i
            JOIN productos p ON p.product_id = i.product_id
            LEFT JOIN deps d ON d.department = p.department
            ON CONFLICT (product_id, tienda_id) DO NOTHING
        """)
        )
        log.info("ubicaciones sembradas: %s", r.rowcount)

        # 8 · órdenes de compra "en tránsito" (aprobadas, sin recibir) para que
        #     la columna En tránsito / el filtro tengan datos.
        if not await s.scalar(
            text("SELECT 1 FROM ordenes_compra WHERE estado = 'aprobada' LIMIT 1")
        ):
            await s.execute(
                text("""
                WITH tiendas_top AS (
                    SELECT tienda_id FROM tiendas WHERE codigo <> 'DEMO' ORDER BY tienda_id LIMIT 6
                ), emp AS (
                    SELECT e.empleado_id, e.tienda_id,
                           row_number() OVER (PARTITION BY e.tienda_id ORDER BY e.empleado_id) rn
                    FROM empleados e
                ), nueva AS (
                    INSERT INTO ordenes_compra (proveedor_id, tienda_id, empleado_id, estado)
                    SELECT (SELECT min(proveedor_id) FROM proveedores), t.tienda_id,
                           (SELECT empleado_id FROM emp WHERE emp.tienda_id = t.tienda_id AND rn = 1),
                           'aprobada'
                    FROM tiendas_top t
                    WHERE EXISTS (SELECT 1 FROM emp WHERE emp.tienda_id = t.tienda_id)
                    RETURNING orden_id, tienda_id
                )
                INSERT INTO orden_compra_detalle (orden_id, product_id, cantidad, costo_unitario)
                SELECT n.orden_id, x.product_id,
                       40 + (abs(hashtext(x.product_id::text)) % 160),
                       COALESCE(p.costo, 100)
                FROM nueva n
                JOIN LATERAL (
                    SELECT i.product_id FROM inventario i
                    WHERE i.tienda_id = n.tienda_id AND i.cantidad_disponible <= i.cantidad_minima
                    ORDER BY i.product_id LIMIT 12
                ) x ON true
                JOIN productos p ON p.product_id = x.product_id
            """)
            )
            log.info("órdenes de compra en tránsito sembradas")

        # 9 · mermas validadas del mes para la KPI "Tasa merma mensual"
        if not await s.scalar(
            text("SELECT 1 FROM mermas WHERE fecha >= date_trunc('month', CURRENT_DATE) LIMIT 1")
        ):
            await s.execute(
                text("""
                INSERT INTO mermas (product_id, tienda_id, cantidad, causa, valor,
                                    empleado_id, fecha, estado_validacion)
                SELECT i.product_id, i.tienda_id,
                       1 + (abs(hashtext(i.product_id::text)) % 6),
                       (ARRAY['caducidad','rotura','robo','error_humano'])[1 + (i.product_id % 4)],
                       COALESCE(p.costo, 100) * (1 + (abs(hashtext(i.product_id::text)) % 6)),
                       (SELECT empleado_id FROM empleados e WHERE e.tienda_id = i.tienda_id
                        ORDER BY e.empleado_id LIMIT 1),
                       CURRENT_DATE - (abs(hashtext(i.product_id::text)) % 25),
                       'validada'
                FROM inventario i
                JOIN productos p ON p.product_id = i.product_id
                WHERE p.es_perecedero
                ORDER BY i.product_id
                LIMIT 40
            """)
            )
            log.info("mermas validadas del mes sembradas")

        await s.commit()

    await _imagenes_unsplash(limite=90)
    log.info("catálogo enriquecido")


async def _imagenes_unsplash(limite: int) -> None:
    """Best-effort: pide unas pocas fotos a Unsplash para los SKU con inventario
    que aún tienen el placeholder. El tier Demo son 50 req/hora, así que se hace
    en tandas chicas; el resto queda con el ícono por categoría."""
    from src.integrations import unsplash_client

    if not unsplash_client.is_configured():
        log.info("Unsplash sin clave — se omiten las imágenes")
        return
    async with AsyncSessionLocal() as s:
        filas = (
            await s.execute(
                text("""
                SELECT DISTINCT p.product_id, p.nombre
                FROM productos p JOIN inventario i ON i.product_id = p.product_id
                WHERE p.imagen_url LIKE 'producto-imagenes/placeholder/%'
                ORDER BY p.product_id
                LIMIT :lim
            """),
                {"lim": limite},
            )
        ).all()
        n = 0
        for product_id, nombre in filas:
            url = await unsplash_client.buscar_imagen(nombre or "")
            if url:
                await s.execute(
                    text("UPDATE productos SET imagen_url = :u WHERE product_id = :p"),
                    {"u": url, "p": product_id},
                )
                n += 1
        await s.commit()
        log.info("imágenes Unsplash: %s/%s", n, len(filas))


if __name__ == "__main__":
    asyncio.run(main())
