"""ForecastingService — regla de negocio del pronóstico de demanda (feature 004).

Orquesta el pipeline de ML (`ml/`), la persistencia de modelos/pronósticos, la
aprobación humana (mismo patrón que `propuesta_ajuste_precio` de 003), el
monitoreo semanal de precisión y el reporte de demanda perdida. El router sólo
traduce HTTP ↔ estos métodos (Principio V/XI).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import UTC, date, datetime
from decimal import Decimal

import pandas as pd

from src.modules.forecasting.ml import entrenamiento, variables
from src.modules.forecasting.ml.metricas import wape
from src.modules.forecasting.repository import ForecastingRepository
from src.shared.exceptions import ConflictError, NotFoundError

logger = logging.getLogger("sira.forecasting")

HORIZONTE_SEMANAS = 8
_DEFAULT_HISTORIAL_MIN = Decimal("12")
_DEFAULT_UMBRAL_DEGRADACION = Decimal("0.45")
SEMANAS_POR_ANIO = 52


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


def _siguiente_semana(semana: int, anio: int) -> tuple[int, int]:
    return (1, anio + 1) if semana >= SEMANAS_POR_ANIO else (semana + 1, anio)


class ForecastingService:
    def __init__(self, repo: ForecastingRepository) -> None:
        self.repo = repo

    # ================================================ US1: entrenamiento
    async def _construir_filas_semanales(self, minimo_semanas: int) -> tuple[list[dict], set]:
        ventas = await self.repo.ventas_semanales()
        if not ventas:
            return [], set()

        promo = await self.repo.semanas_con_promocion()
        cambios = await self.repo.cambios_precio()
        quiebres = await self.repo.quiebres_semanales()

        cambio_por = {}
        for c in cambios:
            prev = c.get("precio_prev")
            pct = 0.0
            if prev not in (None, 0):
                pct = round((c["precio"] - prev) / prev, 4)
            cambio_por[(c["product_id"], c["semana"], c["anio"])] = pct

        quiebre_propio = {
            (q["product_id"], q["tienda_id"], q["semana"], q["anio"]) for q in quiebres
        }
        # tasa de quiebre de la categoría por (categoria, tienda, semana, anio)
        cat_quiebre_prod: dict[tuple, set] = defaultdict(set)
        for q in quiebres:
            cat_quiebre_prod[(q["categoria"], q["tienda_id"], q["semana"], q["anio"])].add(
                q["product_id"]
            )
        categoria_por_producto = await self.repo.categoria_por_producto()
        prod_por_cat_semana: dict[tuple, set] = defaultdict(set)
        for v in ventas:
            cat = categoria_por_producto.get(v["product_id"])
            prod_por_cat_semana[(cat, v["tienda_id"], v["semana"], v["anio"])].add(v["product_id"])

        conteo: dict[tuple[int, int], int] = defaultdict(int)
        for v in ventas:
            conteo[(v["product_id"], v["tienda_id"])] += 1
        pares_ok = variables.pares_con_historial_suficiente(conteo, minimo_semanas)

        filas = []
        for v in ventas:
            par = (v["product_id"], v["tienda_id"])
            if par not in pares_ok:
                continue
            cat = categoria_por_producto.get(v["product_id"])
            key_cat = (cat, v["tienda_id"], v["semana"], v["anio"])
            total_cat = len(prod_por_cat_semana.get(key_cat, ())) or 1
            con_quiebre = len(cat_quiebre_prod.get(key_cat, ()))
            filas.append(
                {
                    "product_id": v["product_id"],
                    "tienda_id": v["tienda_id"],
                    "semana": int(v["semana"]),
                    "anio": int(v["anio"]),
                    "unidades": float(v["unidades"]),
                    "promo": int((v["product_id"], v["semana"], v["anio"]) in promo),
                    "cambio_precio_pct": cambio_por.get(
                        (v["product_id"], v["semana"], v["anio"]), 0.0
                    ),
                    "quiebre_propio": int(
                        (v["product_id"], v["tienda_id"], v["semana"], v["anio"]) in quiebre_propio
                    ),
                    "quiebre_categoria_pct": round(con_quiebre / total_cat, 4),
                }
            )
        return filas, pares_ok

    async def entrenar_modelo(self) -> dict:
        """FR-001/FR-002/FR-006 — job mensual: entrena el modelo global con
        variables exógenas, mide su WAPE de validación (partición temporal) y deja
        el modelo `pendiente` con sus pronósticos del horizonte."""
        minimo = int(
            await self.repo.valor_config("historial_minimo_semanas", _DEFAULT_HISTORIAL_MIN)
        )
        filas, pares_ok = await self._construir_filas_semanales(minimo)
        if not filas:
            return {"entrenado": False, "motivo": "sin combinaciones con historial suficiente"}

        dataset = variables.construir_dataset(filas)
        if dataset.empty:
            return {"entrenado": False, "motivo": "historial insuficiente para rezagos"}

        resultado = entrenamiento.entrenar(dataset)

        # pronóstico del horizonte: para cada par, las próximas HORIZONTE_SEMANAS.
        por_par: dict[tuple[int, int], list[dict]] = defaultdict(list)
        for f in filas:
            por_par[(f["product_id"], f["tienda_id"])].append(f)

        futuras = []
        for (pid, tid), historia in por_par.items():
            historia_ord = sorted(historia, key=lambda r: (r["anio"], r["semana"]))
            ultimas = [r["unidades"] for r in reversed(historia_ord)]
            semana, anio = historia_ord[-1]["semana"], historia_ord[-1]["anio"]
            for _ in range(HORIZONTE_SEMANAS):
                semana, anio = _siguiente_semana(semana, anio)
                futuras.append(variables.fila_pronostico_base(ultimas, pid, tid, semana, anio))

        df_fut = pd.DataFrame(futuras)
        preds = entrenamiento.pronosticar(resultado.modelo, df_fut)
        pronosticos = [
            {**fila, "cantidad_pronosticada": float(p)}
            for fila, p in zip(futuras, preds, strict=True)
        ]

        modelo = await self.repo.crear_modelo(
            wape_validacion=round(resultado.wape_validacion, 4),
            productos_cubiertos=len(pares_ok),
        )
        await self.repo.guardar_pronosticos(modelo.modelo_id, pronosticos)
        logger.info(
            "Modelo %s entrenado: WAPE=%.4f, %d pares, %d pronósticos",
            modelo.modelo_id,
            resultado.wape_validacion,
            len(pares_ok),
            len(pronosticos),
        )
        return {
            "entrenado": True,
            "modelo_id": modelo.modelo_id,
            "wape_validacion": round(resultado.wape_validacion, 4),
            "pares_cubiertos": len(pares_ok),
            "pronosticos_generados": len(pronosticos),
        }

    async def listar_modelos(self, estado: str | None = None):
        from src.models.modelo_demanda import ModeloDemanda

        stmt = self.repo.modelos_query(estado=estado).order_by(
            ModeloDemanda.fecha_entrenamiento.desc()
        )
        return list((await self.repo.session.scalars(stmt)).all())

    async def detalle_modelo(self, modelo_id: int) -> dict:
        modelo = await self.repo.get_modelo(modelo_id)
        if modelo is None:
            raise NotFoundError(f"Modelo {modelo_id} no existe")
        cubiertos = await self.repo.contar_pronosticos(modelo_id)
        return {
            "modelo_id": modelo.modelo_id,
            "fecha_entrenamiento": modelo.fecha_entrenamiento,
            "metrica_precision_validacion": modelo.metrica_precision_validacion,
            "estado": modelo.estado,
            "fecha_resolucion": modelo.fecha_resolucion,
            "aprobado_por": modelo.aprobado_por,
            "observaciones": modelo.observaciones,
            "productos_cubiertos": cubiertos,
        }

    async def aprobar_modelo(self, modelo_id: int, empleado_id: int, observaciones=None):
        modelo = await self.repo.get_modelo(modelo_id)
        if modelo is None:
            raise NotFoundError(f"Modelo {modelo_id} no existe")
        if modelo.estado != "pendiente":
            raise ConflictError(f"El modelo {modelo_id} ya está '{modelo.estado}'")
        vigente = await self.repo.modelo_aprobado()
        if vigente is not None and vigente.modelo_id != modelo_id:
            vigente.estado = "reemplazado"
            vigente.fecha_resolucion = _ahora()
            await self.repo.flush()
        modelo.estado = "aprobado"
        modelo.fecha_resolucion = _ahora()
        modelo.aprobado_por = empleado_id
        if observaciones:
            modelo.observaciones = observaciones
        await self.repo.flush()
        return modelo

    async def rechazar_modelo(self, modelo_id: int, empleado_id: int, observaciones: str):
        modelo = await self.repo.get_modelo(modelo_id)
        if modelo is None:
            raise NotFoundError(f"Modelo {modelo_id} no existe")
        if modelo.estado != "pendiente":
            raise ConflictError(f"El modelo {modelo_id} ya está '{modelo.estado}'")
        modelo.estado = "rechazado"
        modelo.fecha_resolucion = _ahora()
        modelo.aprobado_por = empleado_id
        modelo.observaciones = observaciones
        await self.repo.flush()
        return modelo

    # ================================================ US2: consumo del pronóstico
    async def obtener_pronostico_vigente(self, product_id: int, tienda_id: int, semana, anio):
        return await self.repo.pronostico_vigente(product_id, tienda_id, semana, anio)

    async def demanda_semanal_vigente(self, product_id: int, tienda_id: int) -> float | None:
        """FR-007/FR-008 — unidades pronosticadas para la próxima semana por el
        modelo vigente, o `None` (sin error) si no hay pronóstico → dispara el
        respaldo de rotación reciente de 001."""
        fila = await self.repo.pronostico_vigente_proximo(product_id, tienda_id)
        return float(fila.cantidad_pronosticada) if fila is not None else None

    async def consulta_pronostico(self, product_id: int, tienda_id: int, semana: int, anio: int):
        fila = await self.repo.pronostico_vigente(product_id, tienda_id, semana, anio)
        if fila is None:
            return {"pronostico_disponible": False}
        return {
            "pronostico_disponible": True,
            "cantidad_pronosticada": fila.cantidad_pronosticada,
            "modelo_id": fila.modelo_id,
            "semana": semana,
            "anio": anio,
        }

    # ================================================ US3: monitoreo semanal
    async def calcular_monitoreo_semanal(self, semana: int | None = None, anio: int | None = None):
        """FR-011/FR-012 — sólo sobre el modelo vigente. WAPE de la semana ya
        cerrada; marca alerta si supera `umbral_degradacion_semanal_pct`."""
        modelo = await self.repo.modelo_aprobado()
        if modelo is None:
            return {"calculado": False, "motivo": "no hay modelo vigente en producción"}

        if semana is None or anio is None:
            hoy = date.today()
            iso = hoy.isocalendar()
            semana, anio = iso.week, iso.year

        pronosticos = await self.repo.pronosticos_de_semana(modelo.modelo_id, semana, anio)
        if not pronosticos:
            return {"calculado": False, "motivo": "el modelo vigente no cubre esa semana"}
        reales = await self.repo.ventas_reales_de_semana(semana, anio)

        pares = sorted(pronosticos)
        y_real = [reales.get(par, 0.0) for par in pares]
        y_pred = [pronosticos[par] for par in pares]
        metrica = wape(y_real, y_pred)

        umbral = float(
            await self.repo.valor_config(
                "umbral_degradacion_semanal_pct", _DEFAULT_UMBRAL_DEGRADACION
            )
        )
        supero = metrica > umbral
        fila = await self.repo.guardar_monitoreo(modelo.modelo_id, semana, anio, metrica, supero)
        return {
            "calculado": True,
            "modelo_id": modelo.modelo_id,
            "semana": semana,
            "anio": anio,
            "metrica_precision": fila.metrica_precision,
            "supero_umbral_alerta": supero,
        }

    async def monitoreo_de_modelo(self, modelo_id: int):
        if await self.repo.get_modelo(modelo_id) is None:
            raise NotFoundError(f"Modelo {modelo_id} no existe")
        return await self.repo.monitoreo_de_modelo(modelo_id)

    async def alertas_monitoreo(self):
        return await self.repo.alertas_monitoreo()

    # ================================================ US4: demanda perdida
    async def reporte_demanda_perdida(self, desde: date, hasta: date, tienda_id: int | None = None):
        return await self.repo.demanda_perdida(desde, hasta, tienda_id)

    # ================================================ configuración
    async def listar_configuracion(self):
        return await self.repo.listar_configuracion()

    async def actualizar_configuracion(self, clave: str, valor: Decimal):
        fila = await self.repo.get_config(clave)
        if fila is None:
            raise NotFoundError(f"Clave de configuración '{clave}' no existe")
        fila.valor = valor
        await self.repo.flush()
        return fila
