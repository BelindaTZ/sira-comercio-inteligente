"""Script dedicado para actualizar fotos de productos en SIRA usando Unsplash.

A diferencia de `enriquecer_catalogo.py`, este script:
  1. ÚNICAMENTE actualiza la columna `imagen_url` de los productos.
  2. NO inserta productos nuevos, NO crea inventario, NO toca precios ni órdenes.
  3. Respeta estrictamente el límite de 50 peticiones/hora de la cuenta Demo de Unsplash.
  4. Utiliza limpieza de términos y fallback a categoría para maximizar aciertos.
  5. Actualiza `updated_at` para avanzar secuencialmente sin estancarse en fallos.

Uso:
    # Por defecto: actualiza hasta 40 productos que están en inventario activo
    python -m scripts.actualizar_imagenes_unsplash

    # Especificar un límite personalizado de productos
    python -m scripts.actualizar_imagenes_unsplash --limite 15

    # Actualizar sobre todo el catálogo (no solo productos en inventario)
    python -m scripts.actualizar_imagenes_unsplash --todos --limite 40
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import text

from src.core.database import AsyncSessionLocal
from src.integrations import unsplash_client

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("actualizar_imagenes")


async def procesar_imagenes(
    limite: int = 40,
    solo_inventario: bool = True,
    pausa_segundos: float = 0.8,
) -> dict[str, int]:
    if not unsplash_client.is_configured():
        log.error("ERROR: UNSPLASH_ACCESS_KEY no está configurada en backend/.env")
        return {"exitosos": 0, "sin_foto": 0, "total": 0}

    log.info("Iniciando actualización de fotos con Unsplash...")
    log.info(
        "Límite solicitado: %d productos | Modo: %s",
        limite,
        "Solo productos en inventario" if solo_inventario else "Todo el catálogo",
    )

    async with AsyncSessionLocal() as session:
        if solo_inventario:
            query = text("""
                SELECT p.product_id, p.nombre, p.product_category, p.product_type
                FROM productos p
                WHERE EXISTS (SELECT 1 FROM inventario i WHERE i.product_id = p.product_id)
                  AND p.imagen_url LIKE 'producto-imagenes/placeholder/%'
                ORDER BY p.updated_at ASC NULLS FIRST, p.product_id ASC
                LIMIT :lim
            """)
        else:
            query = text("""
                SELECT p.product_id, p.nombre, p.product_category, p.product_type
                FROM productos p
                WHERE p.imagen_url LIKE 'producto-imagenes/placeholder/%'
                ORDER BY p.updated_at ASC NULLS FIRST, p.product_id ASC
                LIMIT :lim
            """)

        filas = (await session.execute(query, {"lim": limite})).all()

        if not filas:
            log.info("No hay productos con placeholder pendientes de actualizar.")
            return {"exitosos": 0, "sin_foto": 0, "total": 0}

        log.info("Se encontraron %d productos pendientes de foto en este lote.", len(filas))
        print("-" * 70)

        exitosos = 0
        sin_foto = 0

        for idx, (pid, nombre, categoria, tipo) in enumerate(filas, start=1):
            cuota = unsplash_client.obtener_estado_cuota()
            rem = cuota.get("remaining")
            if rem is not None and rem <= 1:
                log.warning(
                    "Cuota de Unsplash casi agotada (restantes: %s/50). Deteniendo lote.", rem
                )
                break

            nombre_mostrar = (nombre or tipo or categoria or f"SKU {pid}")[:35]
            print(f"[{idx}/{len(filas)}] SKU {pid}: '{nombre_mostrar}'", end=" ", flush=True)

            url = await unsplash_client.buscar_imagen_producto(
                nombre=nombre,
                categoria=categoria,
                tipo=tipo,
            )

            cuota_post = unsplash_client.obtener_estado_cuota()
            rem_post = cuota_post.get("remaining")
            rem_txt = f"{rem_post}/50" if rem_post is not None else "N/D"

            if url:
                await session.execute(
                    text("""
                        UPDATE productos
                        SET imagen_url = :u, updated_at = CURRENT_TIMESTAMP
                        WHERE product_id = :p
                    """),
                    {"u": url, "p": pid},
                )
                await session.commit()
                exitosos += 1
                print(f"-> OK Foto asignada (Cuota: {rem_txt})")
            else:
                if rem_post is not None and rem_post <= 0:
                    print("-> LIMITE DE CUOTA ALCANZADO")
                    break

                # Marcar updated_at para que en el próximo lote avance a otros productos
                await session.execute(
                    text("UPDATE productos SET updated_at = CURRENT_TIMESTAMP WHERE product_id = :p"),
                    {"p": pid},
                )
                await session.commit()
                sin_foto += 1
                print(f"-> Sin foto en Unsplash (Cuota: {rem_txt})")

            if pausa_segundos > 0 and idx < len(filas):
                await asyncio.sleep(pausa_segundos)

        print("-" * 70)
        cuota_final = unsplash_client.obtener_estado_cuota()
        rem_fin = cuota_final.get("remaining")
        print("\n" + "=" * 50)
        print(" RESUMEN DE ACTUALIZACIÓN DE FOTOS")
        print("=" * 50)
        print(f" - Fotos asignadas exitosamente : {exitosos}")
        print(f" - Sin coincidencia en Unsplash : {sin_foto}")
        print(f" - Cuota restante en Unsplash   : {rem_fin if rem_fin is not None else 'N/D'}/50")
        print("=" * 50)

        if rem_fin is not None and rem_fin <= 5:
            print("\nNOTA: Tu cuota por hora de Unsplash está por agotarse o agotada.")
            print("Vuelve a ejecutar este script en aproximadamente 1 hora para la siguiente tanda.")

        return {"exitosos": exitosos, "sin_foto": sin_foto, "total": len(filas)}


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Actualiza fotos de productos con Unsplash respetando límites de 50 req/hora."
    )
    parser.add_argument(
        "--limite",
        type=int,
        default=40,
        help="Cantidad máxima de productos a procesar en esta tanda (defecto: 40).",
    )
    parser.add_argument(
        "--todos",
        action="store_true",
        help="Procesar todo el catálogo general en vez de solo productos en inventario.",
    )
    parser.add_argument(
        "--pausa",
        type=float,
        default=0.8,
        help="Segundos de espera entre consultas a Unsplash (defecto: 0.8).",
    )

    args = parser.parse_args()
    asyncio.run(
        procesar_imagenes(
            limite=args.limite,
            solo_inventario=not args.todos,
            pausa_segundos=args.pausa,
        )
    )


if __name__ == "__main__":
    main()
