"""CatalogoService — alta, edición y baja lógica de productos (US4).

FR-013: al alta, si faltan nombre/categoría/imagen se intenta autocompletar vía
Open Food Facts; si no hay coincidencia, el alta NO se bloquea (Principio II).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from src.integrations import openfoodfacts_client
from src.models.producto import Producto
from src.modules.catalogo.repository import CatalogoRepository
from src.modules.catalogo.schemas import ProductoIn, ProductoPatch
from src.shared.exceptions import ConflictError, NotFoundError

logger = logging.getLogger("sira.catalogo")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CatalogoService:
    def __init__(self, repo: CatalogoRepository) -> None:
        self.repo = repo

    async def crear_producto(self, data: ProductoIn) -> tuple[Producto, bool]:
        if await self.repo.existe_barcode(data.codigo_barras):
            raise ConflictError(f"Ya existe un producto con el código {data.codigo_barras}")

        nombre = data.nombre
        categoria = data.categoria
        marca = data.marca
        imagen_url = None
        autocompletado = False

        # FR-013: autocompletar sólo lo que falta.
        if not (nombre and categoria):
            externo = await openfoodfacts_client.buscar_por_barcode(data.codigo_barras)
            if externo is not None:
                autocompletado = True
                nombre = nombre or externo.nombre
                categoria = categoria or externo.categoria
                marca = marca or externo.marca
                imagen_url = externo.imagen_url

        producto = Producto(
            codigo_barras=data.codigo_barras,
            nombre=nombre,
            marca=marca,
            product_category=categoria,
            product_type=nombre,  # compat. con el dato del dataset
            costo=data.costo,
            precio_base=data.precio_base,
            es_perecedero=data.es_perecedero,
            vida_util_dias=data.vida_util_dias,
            es_ancla=(data.clasificacion == "ancla"),
            imagen_url=imagen_url,
            activo=True,
        )
        self.repo.agregar(producto)
        await self.repo.flush()
        await self.repo.refrescar(producto)
        return producto, autocompletado

    async def actualizar_producto(self, product_id: int, data: ProductoPatch) -> Producto:
        producto = await self.repo.get_producto(product_id)
        if producto is None:
            raise NotFoundError(f"Producto {product_id} no existe")

        campos = data.model_dump(exclude_unset=True)
        precio_nuevo = campos.get("precio_base")

        if "nombre" in campos:
            producto.nombre = campos["nombre"]
            producto.product_type = campos["nombre"]
        if "categoria" in campos:
            producto.product_category = campos["categoria"]
        if "marca" in campos:
            producto.marca = campos["marca"]
        if "costo" in campos:
            producto.costo = campos["costo"]
        if "es_perecedero" in campos:
            producto.es_perecedero = campos["es_perecedero"]
        if "vida_util_dias" in campos:
            producto.vida_util_dias = campos["vida_util_dias"]
        if "clasificacion" in campos:
            producto.es_ancla = campos["clasificacion"] == "ancla"
        if precio_nuevo is not None and precio_nuevo != producto.precio_base:
            # FR-010: el precio histórico no se altera — se conserva el rastro.
            await self.repo.registrar_historial_precio(product_id, precio_nuevo)
            producto.precio_base = precio_nuevo

        producto.updated_at = _ahora()
        await self.repo.flush()
        return producto

    async def dar_de_baja(self, product_id: int) -> Producto:
        producto = await self.repo.get_producto(product_id)
        if producto is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        # FR-011: baja lógica, nunca DELETE físico — conserva el historial de ventas.
        producto.activo = False
        producto.updated_at = _ahora()
        await self.repo.flush()
        return producto

    async def listar(self, params, **filtros):
        stmt = self.repo.productos_query(**filtros)
        return await self.repo.paginate(params, stmt=stmt, order_by=Producto.product_id.desc())
