"""T050 — semilla sintética de `precio_competencia` (feature 003, research.md §5).

Para cada producto con `clasificacion_abc = 'A'` y `precio_base` definido, inserta
una fila `fuente_captura = 'sintetico'` con `precio = precio_base * (1 + U(-8%, +8%))`
y `fecha_captura` = hoy, para que US5/FR-016 sea demostrable desde el primer
arranque sin capturar cientos de precios a mano.

Idempotente: no vuelve a sembrar un producto que ya tiene una fila sintética.

Uso:
    python -m scripts.seed_precio_competencia_sintetico
"""

from __future__ import annotations

import asyncio
import random
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import text

from src.core.database import AsyncSessionLocal

VARIACION = Decimal("0.08")


async def main() -> None:
    rng = random.Random(2026)
    async with AsyncSessionLocal() as session:
        productos = (
            await session.execute(
                text(
                    "SELECT p.product_id, p.precio_base FROM productos p "
                    "WHERE p.clasificacion_abc = 'A' AND p.precio_base IS NOT NULL "
                    "AND NOT EXISTS (SELECT 1 FROM precio_competencia pc "
                    "  WHERE pc.product_id = p.product_id AND pc.fuente_captura = 'sintetico')"
                )
            )
        ).all()

        insertados = 0
        for product_id, precio_base in productos:
            factor = Decimal(str(1 + rng.uniform(-float(VARIACION), float(VARIACION))))
            precio = (Decimal(str(precio_base)) * factor).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            await session.execute(
                text(
                    "INSERT INTO precio_competencia "
                    "(product_id, competidor_id, tienda_id, precio, fecha_captura, "
                    " es_promocional, fuente_captura, registrado_por) "
                    "VALUES (:p, NULL, NULL, :precio, CURRENT_DATE, false, 'sintetico', NULL)"
                ),
                {"p": product_id, "precio": precio},
            )
            insertados += 1
        await session.commit()
        print(f"precio_competencia sintético: {insertados} filas insertadas")


if __name__ == "__main__":
    asyncio.run(main())
