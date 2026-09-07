"""CatalogoRepository (T064) — acceso a datos de `productos` e `historial_precios`."""

from __future__ import annotations

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.producto import Producto
from src.shared.repository import BaseRepository


class CatalogoRepository(BaseRepository[Producto]):
    model = Producto

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    def agregar(self, entity) -> None:
        self.session.add(entity)

    async def flush(self) -> None:
        await self.session.flush()

    async def refrescar(self, entity) -> None:
        await self.session.refresh(entity)

    async def get_producto(self, product_id: int) -> Producto | None:
        return await self.session.get(Producto, product_id)

    async def existe_barcode(self, codigo_barras: str) -> bool:
        stmt = select(Producto.product_id).where(Producto.codigo_barras == codigo_barras)
        return (await self.session.scalars(stmt)).first() is not None

    async def registrar_historial_precio(self, product_id: int, precio) -> None:
        from sqlalchemy import text

        await self.session.execute(
            text(
                "INSERT INTO historial_precios (product_id, tienda_id, precio, fecha_inicio) "
                "VALUES (:p, NULL, :precio, CURRENT_DATE)"
            ),
            {"p": product_id, "precio": precio},
        )

    def productos_query(
        self,
        *,
        search: str | None = None,
        codigo_barras: str | None = None,
        categoria: str | None = None,
        activo: bool | None = None,
    ) -> Select:
        stmt = select(Producto)
        if search:
            patron = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Producto.nombre.ilike(patron),
                    Producto.product_type.ilike(patron),
                    Producto.product_category.ilike(patron),
                )
            )
        if codigo_barras:
            stmt = stmt.where(Producto.codigo_barras == codigo_barras)
        if categoria:
            stmt = stmt.where(Producto.product_category == categoria)
        if activo is not None:
            stmt = stmt.where(Producto.activo.is_(activo))
        return stmt
