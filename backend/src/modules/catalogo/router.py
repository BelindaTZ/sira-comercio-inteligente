"""Router del módulo Catálogo — `contracts/catalogo.md` (US4, T067).

RBAC: módulo `Comercial` (Jefe_Comercial / Jefe_Operaciones).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.integrations import minio_client
from src.modules.catalogo.repository import CatalogoRepository
from src.modules.catalogo.schemas import (
    CatalogoResumenOut,
    PrecioMatrizItem,
    ProductoIn,
    ProductoOut,
    ProductoPatch,
    ReglaCanalOut,
    ReglaCanalPatch,
    SimulacionPrecioIn,
    SimulacionPrecioOut,
)
from src.modules.catalogo.service import CatalogoService
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/catalogo", tags=["catalogo"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver = require_permission("Comercial", "productos", "select")
_crear = require_permission("Comercial", "productos", "insert")
_editar = require_permission("Comercial", "productos", "update")
_canal_edita = require_permission("Comercial", "regla_recargo_canal", "update")


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
    product_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> ProductoOut:
    """Asigna una foto genérica de Unsplash por el nombre del producto. Gestión
    de imagen — basta con poder ver el catálogo (la usan también Operaciones)."""
    return _out(await svc.imagen_automatica(product_id))


@router.post("/productos/{product_id}/imagen", response_model=ProductoOut)
async def subir_imagen(
    product_id: int,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    archivo: Annotated[UploadFile, File(alias="archivo")],
) -> ProductoOut:
    """Sube una imagen propia (JPG/PNG/WEBP ≤ 5 MB) al bucket de MinIO y la fija
    como `imagen_url` del producto."""
    datos = await archivo.read()
    try:
        url = minio_client.subir_imagen_producto(
            product_id, datos, archivo.content_type or ""
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    return _out(await svc.actualizar_producto(product_id, ProductoPatch(imagen_url=url)))


@router.post("/productos/{product_id}/simular-precio", response_model=SimulacionPrecioOut)
async def simular_precio(
    product_id: int,
    data: SimulacionPrecioIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
) -> SimulacionPrecioOut:
    """Simulador de impacto (referencia de UI): proyecta margen y ganancia mensual
    ante un cambio de PVP, usando el factor de sensibilidad de la categoría."""
    return SimulacionPrecioOut(**await svc.simular_precio(product_id, data.delta_pct))


@router.get("/precios/canales", response_model=list[ReglaCanalOut])
async def listar_canales(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> list[ReglaCanalOut]:
    """Reglas de recargo por canal (Tienda Física / Delivery App / E-Commerce)."""
    return [ReglaCanalOut.model_validate(c) for c in await svc.listar_canales()]


@router.patch("/precios/canales/{canal}", response_model=ReglaCanalOut)
async def actualizar_canal(
    canal: str,
    data: ReglaCanalPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_canal_edita)],
) -> ReglaCanalOut:
    return ReglaCanalOut.model_validate(
        await svc.actualizar_canal(canal, data.markup_pct, data.activo)
    )


@router.get("/resumen", response_model=CatalogoResumenOut)
async def resumen_catalogo(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> CatalogoResumenOut:
    return CatalogoResumenOut(**await svc.resumen())


@router.get("/precios", response_model=Page[PrecioMatrizItem])
async def matriz_precios(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    search: str | None = None,
    categoria: str | None = None,
    margen: str | None = None,
    activo: bool | None = None,
) -> Page[PrecioMatrizItem]:
    data = await svc.matriz_precios(
        params, search=search, categoria=categoria, margen=margen, activo=activo
    )
    return Page[PrecioMatrizItem](
        items=[PrecioMatrizItem(**row) for row in data["items"]],
        total=data["total"],
        page=data["page"],
        size=data["size"],
    )


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
