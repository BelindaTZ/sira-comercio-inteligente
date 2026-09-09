"""Router del módulo Clientes/Fidelización — `contracts/clientes.md` (feature 002).

RBAC: módulo `Marketing_CRM`. Alta/edición: Cajero/Encargado_Tienda; baja
(anonimización): Encargado_Tienda / Jefe_Marketing.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.security import Principal, require_permission
from src.modules.clientes.campanas_repository import CampanasRepository
from src.modules.clientes.campanas_service import CampanasService
from src.modules.clientes.directorio_repository import DirectorioRepository
from src.modules.clientes.repository import ClientesRepository
from src.modules.clientes.schemas import (
    CampanaDetalleOut,
    DirectorioItemOut,
    Ficha360Out,
    NivelConteoOut,
    ResumenCrmOut,
    CampanaReactivacionIn,
    CampanaResumenOut,
    ClienteDetalleOut,
    ClienteIn,
    ClienteOut,
    ClientePatch,
    DatosDemograficosOut,
    DecisionIn,
    EventoClienteOut,
    NivelFidelizacionOut,
    NivelUmbralPatch,
    RedencionIn,
    RiesgoFugaOut,
    TasaRedencionOut,
)
from src.modules.clientes.service import ClientesService
from src.shared.exceptions import NotFoundError
from src.shared.pagination import Page, PageParams, page_params

router = APIRouter(prefix="/clientes", tags=["clientes"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

_ver = require_permission("Marketing_CRM", "clientes", "select")
_alta = require_permission("Marketing_CRM", "clientes", "insert")
_edita = require_permission("Marketing_CRM", "clientes", "update")
_baja = require_permission("Marketing_CRM", "clientes", "delete")
_niveles_edita = require_permission("Marketing_CRM", "niveles_fidelizacion", "update")
_ver_churn = require_permission("Marketing_CRM", "churn_score", "select")
# tasa de redención: reporte de marketing (Jefe_Marketing tiene `cupon_enviado`,
# el Cajero no) — la redención en caja sí la hace el Cajero (`cupon_redimido`).
_ver_cupones = require_permission("Marketing_CRM", "cupon_enviado", "select")
_redime = require_permission("Marketing_CRM", "cupon_redimido", "insert")
# campañas de reactivación: sólo Jefe_Marketing (crea, envía, cierra y decide).
_campana_ve = require_permission("Marketing_CRM", "campanas", "select")
_campana_crea = require_permission("Marketing_CRM", "campanas", "insert")
_campana_gestiona = require_permission("Marketing_CRM", "campana_resultado", "insert")


def _svc(session: SessionDep) -> ClientesService:
    return ClientesService(ClientesRepository(session))


ServiceDep = Annotated[ClientesService, Depends(_svc)]


def _campanas_svc(session: SessionDep) -> CampanasService:
    return CampanasService(CampanasRepository(session))


CampanasDep = Annotated[CampanasService, Depends(_campanas_svc)]


async def _cliente_out(svc: ClientesService, cliente, *, detalle: bool = False):
    clv = await svc.repo.ultimo_clv(cliente.household_id)
    churn = await svc.repo.ultimo_churn(cliente.household_id)
    base = {
        "household_id": cliente.household_id,
        "nombre": cliente.nombre,
        "email": cliente.email,
        "telefono": cliente.telefono,
        "documento_identidad": cliente.documento_identidad,
        "fecha_nacimiento": cliente.fecha_nacimiento,
        "fecha_registro": cliente.fecha_registro,
        "activo": cliente.activo,
        "consentimiento_datos": cliente.consentimiento_datos,
        "fecha_consentimiento_datos": cliente.fecha_consentimiento_datos,
        "clv_score": clv.clv_score if clv else None,
        "nivel_fidelizacion_id": clv.nivel_id if clv else None,
        "severidad_churn": churn.severidad if churn else None,
    }
    if not detalle:
        return ClienteOut(**base)
    demo = await svc.repo.get_demografico(cliente.household_id)
    return ClienteDetalleOut(
        **base,
        datos_demograficos=(
            DatosDemograficosOut.model_validate(demo, from_attributes=True) if demo else None
        ),
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ClienteDetalleOut)
async def registrar_cliente(
    data: ClienteIn, svc: ServiceDep, _: Annotated[Principal, Depends(_alta)]
) -> ClienteDetalleOut:
    cliente = await svc.registrar_cliente(data)
    return await _cliente_out(svc, cliente, detalle=True)


@router.get("", response_model=Page[ClienteOut])
async def listar_clientes(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    search: str | None = None,
    activo: bool | None = None,
    nivel_fidelizacion_id: int | None = None,
) -> Page[ClienteOut]:
    page = await svc.listar(
        params, search=search, activo=activo, nivel_fidelizacion_id=nivel_fidelizacion_id
    )
    items = [await _cliente_out(svc, c) for c in page.items]
    return Page(items=items, total=page.total, page=page.page, size=page.size)


# --- niveles de fidelización (US2) — registrados antes de /{household_id} ---
@router.get("/niveles-fidelizacion", response_model=list[NivelFidelizacionOut])
async def listar_niveles(
    svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> list[NivelFidelizacionOut]:
    return [NivelFidelizacionOut.model_validate(n) for n in await svc.listar_niveles()]


@router.patch("/niveles-fidelizacion/{nivel_id}", response_model=NivelFidelizacionOut)
async def ajustar_nivel(
    nivel_id: int,
    data: NivelUmbralPatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_niveles_edita)],
) -> NivelFidelizacionOut:
    return NivelFidelizacionOut.model_validate(
        await svc.ajustar_umbral_nivel(nivel_id, data.umbral_clv_min)
    )


# --- riesgo de fuga (US3) — registrado antes de /{household_id} ---
@router.get("/riesgo-fuga", response_model=Page[RiesgoFugaOut])
async def listar_riesgo_fuga(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_churn)],
    params: Annotated[PageParams, Depends(page_params)],
    severidad: str | None = None,
) -> Page[RiesgoFugaOut]:
    """FR-011 / SC-005: el Jefe de Marketing filtra por severidad y recibe
    `ciclo_compra_dias` y `dias_desde_ultima_compra` ya calculados, sin derivarlos."""
    data = await svc.listar_riesgo_fuga(params, severidad=severidad)
    return Page(
        items=[RiesgoFugaOut(**row) for row in data["items"]],
        total=data["total"],
        page=data["page"],
        size=data["size"],
    )


# --- pantalla CRM: directorio + ficha 360 + KPIs (prefijo fijo antes de /{id}) ---
def _directorio(session: SessionDep) -> DirectorioRepository:
    return DirectorioRepository(session)


DirectorioDep = Annotated[DirectorioRepository, Depends(_directorio)]


@router.get("/directorio", response_model=Page[DirectorioItemOut])
async def directorio_clientes(
    repo: DirectorioDep,
    _: Annotated[Principal, Depends(_ver)],
    params: Annotated[PageParams, Depends(page_params)],
    search: str | None = None,
    nivel_id: int | None = None,
    activo: bool | None = True,
) -> Page[DirectorioItemOut]:
    """Directorio enriquecido: LTV, frecuencia, puntos, sucursal habitual y nivel
    del Club Marzú — el operador nunca deriva esto a mano (Principio XII)."""
    filas, total = await repo.directorio(
        search=search, nivel_id=nivel_id, activo=activo,
        offset=params.offset, limit=params.limit,
    )
    return Page[DirectorioItemOut](
        items=[DirectorioItemOut(**f) for f in filas],
        total=total, page=params.page, size=params.size,
    )


@router.get("/resumen-crm", response_model=ResumenCrmOut)
async def resumen_crm(
    repo: DirectorioDep, _: Annotated[Principal, Depends(_ver)]
) -> ResumenCrmOut:
    d = await repo.resumen_crm()
    niveles = await repo.conteo_por_nivel()
    club = float(d.get("ticket_club") or 0)
    no_club = float(d.get("ticket_no_club") or 0)
    asignados = d.get("asignados") or 0
    return ResumenCrmOut(
        base_activos=d.get("base_activos", 0),
        ticket_club=d.get("ticket_club"),
        ticket_no_club=d.get("ticket_no_club"),
        uplift_pct=round((club / no_club - 1) * 100, 1) if no_club else None,
        tasa_redencion_pct=(
            round(d["redimidos"] / asignados * 100, 1) if asignados else None
        ),
        redimidos=d.get("redimidos", 0),
        con_clv=d.get("con_clv", 0),
        niveles=[NivelConteoOut(**n) for n in niveles],
    )


@router.get("/{household_id}/ficha360", response_model=Ficha360Out)
async def ficha_360(
    household_id: int, repo: DirectorioDep, _: Annotated[Principal, Depends(_ver)]
) -> Ficha360Out:
    """Panel 360° del cliente: saldo de puntos, cupones activos, distribución de
    consumo por categoría y últimas compras."""
    d = await repo.ficha_360(household_id)
    return Ficha360Out(
        household_id=household_id,
        valor_canje_clp=d["puntos"],  # 1 punto = 1 CLP de canje
        **d,
    )


# --- campañas por hito (US4) — rutas con prefijo fijo antes de /{household_id} ---
@router.get("/cupones/tasa-redencion", response_model=list[TasaRedencionOut])
async def tasa_redencion(
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_ver_cupones)],
    tipo_evento: str | None = None,
) -> list[TasaRedencionOut]:
    """FR-014: redimidos / enviados por tipo de hito."""
    return [TasaRedencionOut(**row) for row in await svc.tasa_redencion(tipo_evento)]


@router.post("/cupones/{coupon_upc}/redimir", status_code=status.HTTP_201_CREATED)
async def redimir_cupon(
    coupon_upc: str,
    data: RedencionIn,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_redime)],
) -> dict:
    """FR-015: el cajero registra la redención del cupón en el punto de venta."""
    await svc.registrar_redencion(coupon_upc, data.household_id, data.campaign_id)
    return {"coupon_upc": coupon_upc, "household_id": data.household_id, "redimido": True}


@router.get("/{household_id}/eventos", response_model=list[EventoClienteOut])
async def eventos_cliente(
    household_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> list[EventoClienteOut]:
    """Auditoría/soporte: hitos del cliente y el cupón enviado en cada uno. La
    generación es automática (job diario, FR-012/FR-013), no se crea por aquí."""
    return [EventoClienteOut(**row) for row in await svc.eventos_de_cliente(household_id)]


# --- campañas de reactivación (US5) — antes de /{household_id} ---
@router.post("/campanas", status_code=status.HTTP_201_CREATED, response_model=CampanaDetalleOut)
async def crear_campana(
    data: CampanaReactivacionIn,
    svc: CampanasDep,
    _: Annotated[Principal, Depends(_campana_crea)],
) -> CampanaDetalleOut:
    """FR-016: crea la campaña y sus miembros con grupo ya asignado. No envía nada."""
    campana = await svc.crear_reactivacion(data)
    return CampanaDetalleOut(**await svc.detalle(campana.campaign_id))


@router.get("/campanas", response_model=Page[CampanaResumenOut])
async def listar_campanas(
    svc: CampanasDep,
    _: Annotated[Principal, Depends(_campana_ve)],
    params: Annotated[PageParams, Depends(page_params)],
    categoria_sira: str | None = None,
) -> Page[CampanaResumenOut]:
    page = await svc.listar(params, categoria_sira=categoria_sira)
    return Page(
        items=[CampanaResumenOut.model_validate(c) for c in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
    )


@router.get("/campanas/{campaign_id}", response_model=CampanaDetalleOut)
async def detalle_campana(
    campaign_id: int, svc: CampanasDep, _: Annotated[Principal, Depends(_campana_ve)]
) -> CampanaDetalleOut:
    return CampanaDetalleOut(**await svc.detalle(campaign_id))


@router.post("/campanas/{campaign_id}/enviar")
async def enviar_campana(
    campaign_id: int, svc: CampanasDep, _: Annotated[Principal, Depends(_campana_gestiona)]
) -> dict:
    """FR-017: 422 si la campaña no tiene al menos un miembro `grupo=control`."""
    return await svc.enviar(campaign_id)


@router.post("/campanas/{campaign_id}/cerrar", response_model=CampanaDetalleOut)
async def cerrar_campana(
    campaign_id: int, svc: CampanasDep, _: Annotated[Principal, Depends(_campana_gestiona)]
) -> CampanaDetalleOut:
    """FR-018: calcula tasas de retorno + uplift, inserta `campana_resultado`."""
    await svc.cerrar(campaign_id)
    return CampanaDetalleOut(**await svc.detalle(campaign_id))


@router.post("/campanas/{campaign_id}/decision", response_model=CampanaDetalleOut)
async def decidir_campana(
    campaign_id: int,
    data: DecisionIn,
    principal: Annotated[Principal, Depends(_campana_gestiona)],
    svc: CampanasDep,
) -> CampanaDetalleOut:
    """FR-019: aprobar la escalación o descartar la campaña según el uplift."""
    await svc.decidir(campaign_id, data.decision, principal.empleado_id)
    return CampanaDetalleOut(**await svc.detalle(campaign_id))


@router.get("/{household_id}", response_model=ClienteDetalleOut)
async def detalle_cliente(
    household_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_ver)]
) -> ClienteDetalleOut:
    cliente = await svc.repo.get_cliente(household_id)
    if cliente is None:
        raise NotFoundError(f"Cliente {household_id} no existe")
    return await _cliente_out(svc, cliente, detalle=True)


@router.patch("/{household_id}", response_model=ClienteDetalleOut)
async def actualizar_cliente(
    household_id: int,
    data: ClientePatch,
    svc: ServiceDep,
    _: Annotated[Principal, Depends(_edita)],
) -> ClienteDetalleOut:
    cliente = await svc.actualizar_cliente(household_id, data)
    return await _cliente_out(svc, cliente, detalle=True)


@router.delete("/{household_id}", response_model=ClienteOut)
async def dar_de_baja_cliente(
    household_id: int, svc: ServiceDep, _: Annotated[Principal, Depends(_baja)]
) -> ClienteOut:
    cliente = await svc.dar_de_baja(household_id)
    return await _cliente_out(svc, cliente)
