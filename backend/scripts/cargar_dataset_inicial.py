"""Carga inicial del dataset Dunnhumby "The Complete Journey" → PostgreSQL.

Infraestructura de datos, NO una feature de Spec Kit (sin User Stories/FR
propios) — mismo estatus que `scripts/seed_precio_competencia_sintetico.py`.
Referencia exacta de todas las decisiones de mapeo: `.specify/memory/carga-inicial-dataset.md`.

Ninguna de las 12 features carga el dataset — todas lo asumen como prerrequisito.
Este script cierra ese hueco. Los ~430 tests usan sus propias fixtures, no esto:
la carga sólo hace falta para tener datos reales y de volumen al usar el sistema
o correr el pipeline ELT de 010 contra algo real.

Decisiones ya tomadas (no reabrir): 8 tiendas de mayor volumen de transacciones;
año completo (semanas 1-53) para esas 8.

Uso:
    python -m scripts.cargar_dataset_inicial            # sobre una base recién migrada (vacía)
    python -m scripts.cargar_dataset_inicial --reset    # TRUNCATE ... CASCADE del dataset y recarga
    python -m scripts.cargar_dataset_inicial --muestra  # sólo 3 tiendas y 4 semanas (prueba rápida)

Requiere: `docker compose up -d postgres`, `alembic upgrade head`, y `pandas`+`pyarrow`
(ya en `pyproject.toml`). El directorio `csv/` debe estar en la raíz del repo.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import random
from datetime import date
from pathlib import Path

import asyncpg
import pandas as pd
from src.core.config import settings
from src.modules.promociones.analytics import clasificacion_abc

log = logging.getLogger("sira.carga_inicial")

CSV_DIR = Path(__file__).resolve().parents[2] / "csv"
SEED = 20260908  # determinismo entre corridas (código de barras, cajero, medio de pago)

# --- §4: 8 ciudades ecuatorianas, una por tienda (orden = mayor a menor volumen) ---
CIUDADES = [
    "Quevedo",
    "Guayaquil",
    "Quito",
    "Manta",
    "Santo Domingo",
    "Babahoyo",
    "Machala",
    "Portoviejo",
]

# --- §3.4: heurístico es_perecedero / vida_util_dias por department ---
PERECEDEROS: dict[str, int] = {
    "PRODUCE": 7,
    "MEAT": 5,
    "MEAT-PCKGD": 5,
    "SEAFOOD": 3,
    "SEAFOOD-PCKGD": 3,
    "DELI": 4,
    "SALAD BAR": 4,
    "RESTAURANT": 4,
    "CHEF SHOPPE": 4,
    "PASTRY": 4,
    "FROZEN GROCERY": 90,
    "FLORAL": 7,
}

# --- §6: normalización de demographics.csv contra los CHECK del esquema ---
HOME_OWNERSHIP = {
    "Homeowner": "Homeowner",
    "Probable Homeowner": "Homeowner",
    "Renter": "Renter",
    "Probable Renter": "Renter",
    "": "Unknown",
}
MARITAL = {"Married": "Married", "Unmarried": "Single", "": "Unknown"}

# Tablas del dataset que `--reset` vacía (CASCADE arrastra las derivadas de 002-012).
TABLAS_RESET = [
    "venta_detalle",
    "ventas",
    "promociones",
    "cupon_redimido",
    "cupones",
    "campana_cliente",
    "campanas",
    "clientes_demograficos",
    "clientes",
    "empleados",
    "roles_puesto",
    "tiendas",
    "productos",
    "fabricantes",
    "margenes_objetivo",
    "display_locations",
    "mailer_locations",
    "medios_pago",
]


def _pid(v) -> int | None:
    """product_id robusto: `products.csv` tiene una fila con `9e+05` (Excel)."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return None


def ean13(product_id: int) -> str:
    """§3.2 — EAN-13 sintético determinista, prefijo GS1 20 (uso interno)."""
    base = "20" + str(product_id).zfill(10)[-10:]
    suma = sum((1 if i % 2 == 0 else 3) * int(d) for i, d in enumerate(base))
    return base + str((10 - suma % 10) % 10)


# ==========================================================================
async def cargar(*, reset: bool, muestra: bool) -> None:
    dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    conn = await asyncpg.connect(dsn)
    rng = random.Random(SEED)
    n_tiendas = 3 if muestra else 8
    semanas_ok = set(range(1, 5)) if muestra else set(range(1, 54))
    try:
        await _guardia(conn, reset=reset)

        # ---- pre-pass: transactions.csv (elige tiendas, precios, households) ----
        log.info("Leyendo transactions.csv (1.47M filas)…")
        tx = pd.read_csv(
            CSV_DIR / "transactions.csv",
            usecols=[
                "household_id",
                "store_id",
                "basket_id",
                "product_id",
                "quantity",
                "sales_value",
                "retail_disc",
                "coupon_disc",
                "coupon_match_disc",
                "week",
                "transaction_timestamp",
            ],
            dtype={"store_id": "int32", "week": "int16"},
            parse_dates=["transaction_timestamp"],
        )
        top_stores = tx["store_id"].value_counts().head(n_tiendas).index.tolist()
        store_map = {sid: f"T{i + 1:02d}" for i, sid in enumerate(top_stores)}
        log.info("Tiendas elegidas (store_id → código): %s", store_map)

        households = set(tx["household_id"].dropna().astype(int))
        tx8 = tx[tx["store_id"].isin(top_stores) & tx["week"].isin(semanas_ok)].copy()
        tx8["product_id"] = tx8["product_id"].map(_pid)
        tx8 = tx8.dropna(subset=["product_id"])
        tx8["product_id"] = tx8["product_id"].astype(int)
        log.info(
            "transactions filtradas a %d tiendas / %d semanas: %d filas (de %d)",
            n_tiendas,
            len(semanas_ok),
            len(tx8),
            len(tx),
        )
        del tx

        # precio unitario real por producto = Σ sales_value / Σ quantity (>0), 8 tiendas
        pos = tx8[tx8["quantity"] > 0].groupby("product_id")[["sales_value", "quantity"]].sum()
        precio = pos["sales_value"] / pos["quantity"]
        precio_por_producto: dict[int, float] = {
            int(k): round(float(v), 2) for k, v in precio.items() if pd.notna(v) and v > 0
        }

        async with conn.transaction():
            await _medios_pago(conn)
            prod_ids = await _catalogo(conn, precio_por_producto)
            tienda_ids = await _tiendas(conn, top_stores, store_map)
            cajeros = await _empleados(conn, tienda_ids)
            await _clientes(conn, households)
            camp_ids = await _campanas(conn)
            await _cupones(conn, prod_ids, camp_ids)
            await _promociones(conn, top_stores, store_map, tienda_ids, prod_ids, semanas_ok)
            await _ventas(conn, tx8, store_map, tienda_ids, cajeros, prod_ids, rng)
            await _margenes_objetivo(conn)
            await _clasificacion_abc(conn)

        await _resumen(conn)
    finally:
        await conn.close()


async def _guardia(conn: asyncpg.Connection, *, reset: bool) -> None:
    n = await conn.fetchval("SELECT count(*) FROM productos")
    if n and not reset:
        raise SystemExit(
            f"La base ya tiene {n} productos. Corré con --reset para vaciar las tablas "
            "del dataset (TRUNCATE ... CASCADE) y recargar."
        )
    if reset:
        log.warning(
            "--reset: TRUNCATE CASCADE de %s (arrastra tablas derivadas de 002-012)",
            ", ".join(TABLAS_RESET),
        )
        await conn.execute(f"TRUNCATE {', '.join(TABLAS_RESET)} RESTART IDENTITY CASCADE")


# --------------------------------------------------------------- §2
async def _medios_pago(conn: asyncpg.Connection) -> None:
    await conn.execute(
        "INSERT INTO medios_pago (nombre) VALUES ('Efectivo'),('Tarjeta'),('Digital') "
        "ON CONFLICT (nombre) DO NOTHING"
    )
    log.info("medios_pago: Efectivo / Tarjeta / Digital")


# --------------------------------------------------------------- §3
async def _catalogo(conn: asyncpg.Connection, precios: dict[int, float]) -> set[int]:
    df = pd.read_csv(CSV_DIR / "products.csv", dtype=str, keep_default_na=False)
    df["product_id"] = df["product_id"].map(_pid)
    df = df.dropna(subset=["product_id"]).drop_duplicates(subset=["product_id"])
    df["product_id"] = df["product_id"].astype(int)

    # fabricantes: un registro por manufacturer_id distinto
    manu = sorted({int(float(m)) for m in df["manufacturer_id"].dropna() if str(m).strip()})
    await conn.copy_records_to_table(
        "fabricantes",
        records=[(m, None) for m in manu],
        columns=["manufacturer_id", "nombre"],
    )
    log.info("fabricantes: %d", len(manu))

    filas = []
    for r in df.itertuples(index=False):
        pid = int(r.product_id)
        dep = (r.department or "").strip()
        pb = precios.get(pid)
        costo = round(pb * 0.70, 2) if pb is not None else None
        vida = PERECEDEROS.get(dep)
        mid = int(float(r.manufacturer_id)) if str(r.manufacturer_id).strip() else None
        dep_slug = dep.lower().replace(" ", "-").replace("/", "-") or "otros"
        filas.append(
            (
                pid,
                mid,
                dep or None,
                (r.brand or "").strip() or None,
                (r.product_category or "").strip() or None,
                (r.product_type or "").strip() or None,
                (r.package_size or "").strip() or None,
                costo,
                pb,
                vida is not None,
                vida,
                ean13(pid),
                f"producto-imagenes/placeholder/{dep_slug}.png",
            )
        )
    await conn.copy_records_to_table(
        "productos",
        records=filas,
        columns=[
            "product_id",
            "manufacturer_id",
            "department",
            "brand",
            "product_category",
            "product_type",
            "package_size",
            "costo",
            "precio_base",
            "es_perecedero",
            "vida_util_dias",
            "codigo_barras",
            "imagen_url",
        ],
    )
    con_precio = sum(1 for f in filas if f[8] is not None)
    log.info(
        "productos: %d (%d con precio real, %d sin señal de precio)",
        len(filas),
        con_precio,
        len(filas) - con_precio,
    )
    return set(df["product_id"])


# --------------------------------------------------------------- §4
async def _tiendas(conn, top_stores: list[int], store_map: dict[int, str]) -> dict[str, int]:
    ids: dict[str, int] = {}
    for sid in top_stores:
        cod = store_map[sid]
        ciudad = CIUDADES[int(cod[1:]) - 1]
        tid = await conn.fetchval(
            "INSERT INTO tiendas (codigo, nombre, ciudad, fecha_apertura) "
            "VALUES ($1, $2, $3, DATE '2016-06-01') RETURNING tienda_id",
            cod,
            f"Marzú - {ciudad}",
            ciudad,
        )
        ids[cod] = tid
    log.info("tiendas: %d (%s)", len(ids), ", ".join(ids))
    return ids


# --------------------------------------------------------------- §5
async def _empleados(conn, tienda_ids: dict[str, int]) -> dict[int, list[int]]:
    puestos = {}
    for nombre in ("Encargado_Tienda", "Reponedor", "Cajero"):
        puestos[nombre] = await conn.fetchval(
            "INSERT INTO roles_puesto (nombre) VALUES ($1) "
            "ON CONFLICT (nombre) DO UPDATE SET nombre = EXCLUDED.nombre RETURNING puesto_id",
            nombre,
        )
    cajeros: dict[int, list[int]] = {}
    for cod, tid in tienda_ids.items():
        roster = [("Encargado_Tienda", 1), ("Reponedor", 1), ("Cajero", 2)]
        for puesto, cuantos in roster:
            for k in range(1, cuantos + 1):
                eid = await conn.fetchval(
                    "INSERT INTO empleados (tienda_id, puesto_id, nombre, email, "
                    "fecha_contratacion) VALUES ($1, $2, $3, $4, DATE '2016-06-15') "
                    "RETURNING empleado_id",
                    tid,
                    puestos[puesto],
                    f"{puesto.replace('_', ' ')} {k} {cod}",
                    f"{puesto.lower()}{k}.{cod.lower()}@marzu-seed.local",
                )
                if puesto == "Cajero":
                    cajeros.setdefault(tid, []).append(eid)
    log.info("empleados: %d (4 por tienda)", len(tienda_ids) * 4)
    return cajeros


# --------------------------------------------------------------- §6
async def _clientes(conn, households: set[int]) -> None:
    camp = pd.read_csv(CSV_DIR / "campaigns.csv")
    red = pd.read_csv(CSV_DIR / "coupon_redemptions.csv")
    todos = households | set(camp["household_id"]) | set(red["household_id"])
    todos = {int(h) for h in todos if pd.notna(h)}

    # fecha_registro = primera transacción del household (o 2017-01-01)
    primera: dict[int, date] = {}
    for chunk in pd.read_csv(
        CSV_DIR / "transactions.csv",
        usecols=["household_id", "transaction_timestamp"],
        parse_dates=["transaction_timestamp"],
        chunksize=400_000,
    ):
        g = chunk.groupby("household_id")["transaction_timestamp"].min()
        for h, ts in g.items():
            h = int(h)
            d = ts.date()
            if h not in primera or d < primera[h]:
                primera[h] = d

    await conn.copy_records_to_table(
        "clientes",
        records=[(h, primera.get(h, date(2017, 1, 1))) for h in sorted(todos)],
        columns=["household_id", "fecha_registro"],
    )
    log.info("clientes: %d", len(todos))

    demo = pd.read_csv(CSV_DIR / "demographics.csv", dtype=str).fillna("")
    filas = []
    for r in demo.itertuples(index=False):
        h = _pid(r.household_id)
        if h is None or h not in todos:
            continue
        filas.append(
            (
                h,
                r.age or None,
                r.income or None,
                HOME_OWNERSHIP.get(r.home_ownership.strip(), "Unknown"),
                MARITAL.get(r.marital_status.strip(), "Unknown"),
                r.household_size or None,
                r.household_comp or None,
                r.kids_count or None,
            )
        )
    await conn.copy_records_to_table(
        "clientes_demograficos",
        records=filas,
        columns=[
            "household_id",
            "age",
            "income",
            "home_ownership",
            "marital_status",
            "household_size",
            "household_comp",
            "kids_count",
        ],
    )
    log.info("clientes_demograficos: %d", len(filas))


# --------------------------------------------------------------- §7 (campañas)
async def _campanas(conn) -> set[int]:
    desc = pd.read_csv(
        CSV_DIR / "campaign_descriptions.csv", parse_dates=["start_date", "end_date"]
    )
    filas = [
        (int(r.campaign_id), str(r.campaign_type), r.start_date.date(), r.end_date.date())
        for r in desc.itertuples(index=False)
        if r.end_date >= r.start_date
    ]
    await conn.copy_records_to_table(
        "campanas",
        records=filas,
        columns=["campaign_id", "campaign_type", "start_date", "end_date"],
    )
    camp_ids = {f[0] for f in filas}

    cc = pd.read_csv(CSV_DIR / "campaigns.csv").drop_duplicates()
    pares = {
        (int(r.campaign_id), int(r.household_id))
        for r in cc.itertuples(index=False)
        if pd.notna(r.household_id) and int(r.campaign_id) in camp_ids
    }
    await conn.copy_records_to_table(
        "campana_cliente", records=sorted(pares), columns=["campaign_id", "household_id"]
    )
    log.info("campanas: %d · campana_cliente: %d", len(camp_ids), len(pares))
    return camp_ids


# --------------------------------------------------------------- §7 (cupones)
async def _cupones(conn, prod_ids: set[int], camp_ids: set[int]) -> None:
    cup = pd.read_csv(CSV_DIR / "coupons.csv", dtype={"coupon_upc": str})
    cup["product_id"] = cup["product_id"].map(_pid)
    vistos: set[tuple] = set()
    filas = []
    for r in cup.itertuples(index=False):
        pid, cid = r.product_id, int(r.campaign_id)
        if pid is None or int(pid) not in prod_ids or cid not in camp_ids:
            continue
        clave = (str(r.coupon_upc), int(pid), cid)
        if clave in vistos:
            continue
        vistos.add(clave)
        filas.append(clave)
    await conn.copy_records_to_table(
        "cupones", records=filas, columns=["coupon_upc", "product_id", "campaign_id"]
    )

    red = pd.read_csv(
        CSV_DIR / "coupon_redemptions.csv",
        dtype={"coupon_upc": str},
        parse_dates=["redemption_date"],
    )
    rfilas = [
        (int(r.household_id), str(r.coupon_upc), int(r.campaign_id), r.redemption_date.date())
        for r in red.itertuples(index=False)
        if int(r.campaign_id) in camp_ids
    ]
    await conn.copy_records_to_table(
        "cupon_redimido",
        records=rfilas,
        columns=["household_id", "coupon_upc", "campaign_id", "redemption_date"],
    )
    log.info("cupones: %d · cupon_redimido: %d", len(filas), len(rfilas))


# --------------------------------------------------------------- §7 (promociones)
async def _promociones(conn, top_stores, store_map, tienda_ids, prod_ids, semanas_ok) -> None:
    dfs = []
    for parquet in ("promotions_weeks01-26.parquet", "promotions_weeks27-53.parquet"):
        p = CSV_DIR / parquet
        if p.exists():
            dfs.append(pd.read_parquet(p))
    if not dfs:
        log.warning("promociones: sin parquet, se omite")
        return
    promo = pd.concat(dfs, ignore_index=True)
    promo = promo[promo["store_id"].isin(top_stores) & promo["week"].isin(semanas_ok)]
    promo["product_id"] = promo["product_id"].map(_pid)
    promo = promo.dropna(subset=["product_id"])
    promo["product_id"] = promo["product_id"].astype(int)
    promo = promo[promo["product_id"].isin(prod_ids)].drop_duplicates()
    promo["display_location"] = promo["display_location"].where(promo["display_location"].notna())
    promo["mailer_location"] = promo["mailer_location"].where(promo["mailer_location"].notna())

    disp = sorted({str(x) for x in promo["display_location"].dropna()})
    mail = sorted({str(x) for x in promo["mailer_location"].dropna()})
    await conn.copy_records_to_table(
        "display_locations",
        records=[(d, f"Código Dunnhumby: {d}") for d in disp],
        columns=["codigo", "descripcion"],
    )
    await conn.copy_records_to_table(
        "mailer_locations",
        records=[(m, f"Código Dunnhumby: {m}") for m in mail],
        columns=["codigo", "descripcion"],
    )

    filas = [
        (
            int(r.product_id),
            tienda_ids[store_map[int(r.store_id)]],
            None if pd.isna(r.display_location) else str(r.display_location),
            None if pd.isna(r.mailer_location) else str(r.mailer_location),
            int(r.week),
            2017,
        )
        for r in promo.itertuples(index=False)
    ]
    await conn.copy_records_to_table(
        "promociones",
        records=filas,
        columns=[
            "product_id",
            "tienda_id",
            "display_location",
            "mailer_location",
            "semana",
            "anio",
        ],
    )
    log.info("promociones: %d (display=%d, mailer=%d)", len(filas), len(disp), len(mail))


# --------------------------------------------------------------- §8
async def _ventas(conn, tx8, store_map, tienda_ids, cajeros, prod_ids, rng) -> None:
    medios = {
        r["nombre"]: r["medio_pago_id"]
        for r in await conn.fetch("SELECT nombre, medio_pago_id FROM medios_pago")
    }
    # §8: distribución sintética 45% Efectivo / 40% Tarjeta / 15% Digital
    mp_valores = [medios["Efectivo"], medios["Tarjeta"], medios["Digital"]]
    mp_w = [45, 40, 15]

    descartadas = 0
    ventas_rec, detalle_rec = [], []
    for basket_id, g in tx8.groupby("basket_id", sort=False):
        r0 = g.iloc[0]
        cod = store_map[int(r0["store_id"])]
        tid = tienda_ids[cod]
        lineas = []
        for r in g.itertuples(index=False):
            pid = int(r.product_id)
            cant = int(float(r.quantity))
            if pid not in prod_ids or cant <= 0:
                descartadas += 1
                continue
            lineas.append(
                (
                    pid,
                    cant,
                    round(float(r.sales_value), 2),
                    round(float(r.retail_disc), 2),
                    round(float(r.coupon_disc), 2),
                    round(float(r.coupon_match_disc), 2),
                )
            )
        if not lineas:
            continue
        hh = r0["household_id"]
        household_id = int(hh) if pd.notna(hh) and int(hh) != 0 else None
        total = round(sum(ln[2] for ln in lineas), 2)
        ventas_rec.append(
            (
                int(basket_id),
                tid,
                rng.choice(cajeros[tid]),
                household_id,
                rng.choices(mp_valores, weights=mp_w, k=1)[0],
                r0["transaction_timestamp"].to_pydatetime(),
                int(r0["week"]),
                total if total >= 0 else 0,
                "confirmada",
            )
        )
        for pid, cant, sv, rd, cd, cmd in lineas:
            detalle_rec.append((int(basket_id), pid, cant, sv, rd, cd, cmd))

    await conn.copy_records_to_table(
        "ventas",
        records=ventas_rec,
        columns=[
            "venta_id",
            "tienda_id",
            "cajero_id",
            "household_id",
            "medio_pago_id",
            "fecha_hora",
            "semana",
            "total",
            "estado",
        ],
    )
    await conn.copy_records_to_table(
        "venta_detalle",
        records=detalle_rec,
        columns=[
            "venta_id",
            "product_id",
            "cantidad",
            "sales_value",
            "retail_disc",
            "coupon_disc",
            "coupon_match_disc",
        ],
    )
    log.info(
        "ventas: %d · venta_detalle: %d (%d líneas descartadas: producto inexistente o qty<=0)",
        len(ventas_rec),
        len(detalle_rec),
        descartadas,
    )


# --------------------------------------------------------------- §9
async def _margenes_objetivo(conn) -> None:
    cats = await conn.fetch(
        "SELECT DISTINCT product_category FROM productos WHERE product_category IS NOT NULL"
    )
    await conn.copy_records_to_table(
        "margenes_objetivo",
        records=[(r["product_category"], 25.00) for r in cats],
        columns=["product_category", "margen_objetivo_pct"],
    )
    log.info("margenes_objetivo: %d categorías @ 25%%", len(cats))


# --------------------------------------------------------------- §13
async def _clasificacion_abc(conn) -> None:
    """Corre la lógica real de 005 (`clasificacion_abc.clasificar_categoria`, Pareto)
    sobre TODAS las ventas cargadas — sin la ventana temporal del job, que apuntaría
    a 2026 y dejaría el histórico 2017 sin clasificar."""
    rows = await conn.fetch("""
        SELECT p.product_category AS cat, p.product_id,
               COALESCE(SUM(vd.sales_value * vd.cantidad - vd.retail_disc), 0)::float AS valor
        FROM productos p
        LEFT JOIN venta_detalle vd ON vd.product_id = p.product_id
        LEFT JOIN ventas v ON v.venta_id = vd.venta_id AND v.estado = 'confirmada'
        GROUP BY p.product_category, p.product_id
    """)
    por_cat: dict[str, dict[int, float]] = {}
    for r in rows:
        por_cat.setdefault(r["cat"] or "(sin categoría)", {})[r["product_id"]] = r["valor"] or 0.0

    asignaciones: list[tuple[str, int]] = []
    for valores in por_cat.values():
        for pid, clase in clasificacion_abc.clasificar_categoria(valores).items():
            asignaciones.append((clase, pid))
    await conn.executemany(
        "UPDATE productos SET clasificacion_abc = $1 WHERE product_id = $2", asignaciones
    )
    reparto = {c: sum(1 for cl, _ in asignaciones if cl == c) for c in ("A", "B", "C")}
    log.info("clasificacion_abc: %s", reparto)


async def _resumen(conn) -> None:
    tablas = [
        "productos",
        "fabricantes",
        "tiendas",
        "empleados",
        "clientes",
        "clientes_demograficos",
        "campanas",
        "campana_cliente",
        "cupones",
        "cupon_redimido",
        "promociones",
        "ventas",
        "venta_detalle",
        "margenes_objetivo",
    ]
    log.info("─── carga inicial completa ───")
    for t in tablas:
        log.info("  %-22s %s", t, await conn.fetchval(f"SELECT count(*) FROM {t}"))


def main() -> None:
    ap = argparse.ArgumentParser(description="Carga inicial del dataset Dunnhumby → PostgreSQL")
    ap.add_argument(
        "--reset",
        action="store_true",
        help="TRUNCATE ... CASCADE de las tablas del dataset antes de cargar",
    )
    ap.add_argument(
        "--muestra",
        action="store_true",
        help="carga reducida (3 tiendas, 4 semanas) para prueba rápida",
    )
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    asyncio.run(cargar(reset=args.reset, muestra=args.muestra))


if __name__ == "__main__":
    main()
