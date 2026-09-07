"""Repositorio base genérico (T010).

Capa de acceso a datos reutilizable — sin lógica de negocio (Principio XI).
Toda consulta de listado pasa por `paginate()` (Principio XII).
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import Base
from src.shared.pagination import Page, PageParams

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # --- lectura ---
    async def get(self, pk: Any) -> ModelT | None:
        return await self.session.get(self.model, pk)

    async def list_all(self, *, order_by: Any = None) -> list[ModelT]:
        stmt: Select = select(self.model)
        if order_by is not None:
            stmt = stmt.order_by(order_by)
        return list((await self.session.scalars(stmt)).all())

    async def paginate(
        self,
        params: PageParams,
        *,
        stmt: Select | None = None,
        order_by: Any = None,
    ) -> Page[ModelT]:
        base_stmt = stmt if stmt is not None else select(self.model)

        total = await self.session.scalar(
            select(func.count()).select_from(base_stmt.order_by(None).subquery())
        )

        page_stmt = base_stmt
        if order_by is not None:
            page_stmt = page_stmt.order_by(order_by)
        page_stmt = page_stmt.offset(params.offset).limit(params.limit)

        items = list((await self.session.scalars(page_stmt)).all())
        return Page.build(items, int(total or 0), params)

    # --- escritura ---
    async def add(self, entity: ModelT) -> ModelT:
        self.session.add(entity)
        await self.session.flush()
        return entity

    async def delete(self, entity: ModelT) -> None:
        await self.session.delete(entity)
        await self.session.flush()
