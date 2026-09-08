"""Router del módulo Catálogo — `contracts/catalogo.md` (US4, T067).

RBAC: módulo `Comercial` (Jefe_Comercial / Jefe_Operaciones).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.catalogo.repository import CatalogoRepository
from src.modules.catalogo.schemas import ProductoIn, ProductoOut, ProductoPatch
from src.modules.catalogo.service import CatalogoService
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/catalogo", tags=["catalogo"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver = require_permission("Comercial", "productos", "select")
_crear = require_permission("Comercial", "productos", "insert")
_editar = require_permission("Comercial", "productos", "update")


def _svc(session: SessionDep) -> CatalogoService:
    return CatalogoService(CatalogoRepository(session))


ServiceDep = Annotated[CatalogoService, Depends(_svc)]


def _out(producto, autocompletado: bool = False) -> ProductoOut:
    data = ProductoOut.model_validate(producto)
    data.autocompletado = autocompletado
    return data


@router.post("/productos", status_code=status.HTTP_201_CREATED, response_model=ProductoOut)
async def crear_producto(
    data: ProductoIn, svc: ServiceDep, _: Annotated[Principal, Depends(_crear)]
) -> ProductoOut:
    producto, autocompletado = await svc.crear_producto(data)
    return _out(producto, autocompletado)


@router.patch("/productos/{product_id}", response_model=ProductoOut)
async def actualizar_producto(
    product_id: int,
    data: ProductoPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_editar)],
) -> ProductoOut:
    return _out(await svc.actualizar_producto(product_id, data))


@router.delete("/productos/{product_id}", response_model=ProductoOut)
async def dar_de_baja(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_editar)]
) -> ProductoOut:
    return _out(await svc.dar_de_baja(product_id))


@router.post("/productos/{product_id}/imagen-auto", response_model=ProductoOut)
async def imagen_automatica(
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_editar)]
) -> ProductoOut:
    """Asigna una foto genérica de Unsplash por el nombre del producto. Para
    una imagen propia se usa `PATCH /productos/{id}` con `imagen_url`."""
    return _out(await svc.imagen_automatica(product_id))


@router.get("/categorias", response_model=list[str])
async def listar_categorias(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> list[str]:
    """Categorías existentes (valores distintos de `product_category`). Alimenta
    los selectores de categoría (p. ej. stock máximo). No hay alta de categoría
    suelta: una categoría "existe" cuando un producto la usa."""
    return await svc.categorias()


@router.get("/productos", response_model=Page[ProductoOut])
async def listar_productos(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    search: str | None = None,
    codigo_barras: str | None = None,
    categoria: str | None = None,
    activo: bool | None = None,
) -> Page[ProductoOut]:
    page = await svc.listar(
        params,
        search=search,
        codigo_barras=codigo_barras,
        categoria=categoria,
        activo=activo,
    )
    return Page[ProductoOut](
        items=[_out(p) for p in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
    )
