"""CatalogoService — alta, edición y baja lógica de productos (US4).

FR-013: al alta, si faltan nombre/categoría/imagen se intenta autocompletar vía
Open Food Facts; si no hay coincidencia, el alta NO se bloquea (Principio II).
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from src.integrations import openfoodfacts_client
from src.models.producto import Producto
from src.modules.catalogo.repository import CatalogoRepository
from src.modules.catalogo.schemas import ProductoIn, ProductoPatch
from src.shared.exceptions import BusinessRuleError, ConflictError, NotFoundError

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

        # FR-014 (feature 003): un producto agregado en vivo lleva código de barras
        # real → se intenta una primera captura de precio de competencia vía Open
        # Prices. Best-effort: no bloquea el alta si falla o no hay dato.
        try:
            from src.modules.pricing.repository import PricingRepository
            from src.modules.pricing.service import PricingService

            await PricingService(PricingRepository(self.repo.session)).capturar_open_prices(
                producto.product_id
            )
        except Exception:  # noqa: BLE001
            logger.info("Open Prices no disponible al alta del producto %s", producto.product_id)

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
        if "imagen_url" in campos:
            producto.imagen_url = campos["imagen_url"]
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

    async def categorias(self) -> list[str]:
        return await self.repo.categorias()

    # ==================================== matriz de precios por canal (US4, 0024)
    async def listar_canales(self):
        return await self.repo.listar_canales()

    async def actualizar_canal(self, canal: str, markup_pct, activo):
        regla = await self.repo.get_canal(canal)
        if regla is None:
            raise NotFoundError(f"El canal '{canal}' no existe")
        if canal == "fisico" and markup_pct not in (None, 0, Decimal("0")):
            raise BusinessRuleError(
                "El canal físico es la base de cálculo: su recargo es siempre 0%."
            )
        if markup_pct is not None:
            regla.markup_pct = markup_pct
        if activo is not None:
            regla.activo = activo
        regla.updated_at = _ahora()
        await self.repo.flush()
        return regla

    @staticmethod
    def _estado_margen(margen_pct, objetivo) -> str:
        if margen_pct is None:
            return "sin_precio"
        if objetivo is None:
            return "optimo"
        obj = float(objetivo)
        if float(margen_pct) >= obj:
            return "optimo"
        if float(margen_pct) >= obj - 5:
            return "ajustado"
        return "bajo"

    async def matriz_precios(self, params, *, search, categoria, margen, activo) -> dict:
        filas, total = await self.repo.matriz_precios(
            search=search,
            categoria=categoria,
            margen=margen,
            activo=activo,
            offset=params.offset,
            limit=params.limit,
        )
        for f in filas:
            f["estado_margen"] = self._estado_margen(
                f.get("margen_pct"), f.get("margen_objetivo_pct")
            )
        return {"items": filas, "total": total, "page": params.page, "size": params.size}

    async def resumen(self) -> dict:
        return await self.repo.resumen_catalogo()

    async def simular_precio(self, product_id: int, delta_pct: Decimal) -> dict:
        producto = await self.repo.get_producto(product_id)
        if producto is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        if not producto.precio_base or not producto.costo:
            raise BusinessRuleError(
                "El producto no tiene precio y costo cargados: no se puede simular."
            )
        pvp = float(producto.precio_base)
        costo = float(producto.costo)
        d = float(delta_pct) / 100
        pvp_nuevo = round(pvp * (1 + d), 2)

        margen_actual = (pvp - costo) / pvp * 100 if pvp else None
        margen_nuevo = (pvp_nuevo - costo) / pvp_nuevo * 100 if pvp_nuevo else None

        unidades = await self.repo.unidades_mensuales(product_id)
        factor_raw = await self.repo.factor_sensibilidad_categoria(producto.product_category)
        factor = float(factor_raw) if factor_raw is not None else 0.20

        # Precio ↑ ⇒ volumen ↓, proporcional al factor de sensibilidad de la categoría.
        delta_unidades = round(-factor * d * unidades, 1)
        unidades_proy = max(0.0, unidades + delta_unidades)
        ganancia_actual = unidades * (pvp - costo)
        ganancia_nueva = unidades_proy * (pvp_nuevo - costo)

        return {
            "product_id": product_id,
            "nombre": producto.nombre,
            "pvp_actual": producto.precio_base,
            "pvp_nuevo": Decimal(str(pvp_nuevo)),
            "margen_actual_pct": round(margen_actual, 1) if margen_actual is not None else None,
            "margen_nuevo_pct": round(margen_nuevo, 1) if margen_nuevo is not None else None,
            "unidades_mes": unidades,
            "factor_elasticidad": factor,
            "delta_unidades_mes": delta_unidades,
            "ganancia_mensual_delta": round(ganancia_nueva - ganancia_actual, 0),
            "es_inelastico": factor < 0.15,
        }

    async def imagen_automatica(self, product_id: int) -> Producto:
        """Busca una foto genérica en Unsplash por el nombre del producto y la
        fija como `imagen_url`. Si no hay clave o coincidencia, deja la actual
        (Principio II) y el llamador puede subir una manual."""
        from src.integrations import unsplash_client

        producto = await self.repo.get_producto(product_id)
        if producto is None:
            raise NotFoundError(f"Producto {product_id} no existe")
        consulta = producto.nombre or producto.product_type or producto.product_category
        url = await unsplash_client.buscar_imagen(consulta or "")
        if url:
            producto.imagen_url = url
            producto.updated_at = _ahora()
            await self.repo.flush()
        return producto
