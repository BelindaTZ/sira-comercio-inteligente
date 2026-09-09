"""CajaService — regla de negocio de caja, mermas y fraude (feature 006).

Orquesta las funciones puras de `src.shared.caja` contra el `CajaRepository`. El
router sólo traduce HTTP ↔ estos métodos (Principio V/XI). El `total_esperado` de
un cuadre se calcula aquí, server-side, nunca se acepta del cliente.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from decimal import Decimal

from src.modules.caja.repository import CajaRepository
from src.modules.caja.schemas import IncidenteFraudeIn
from src.shared import caja as logica
from src.shared import pagos
from src.shared.exceptions import ConflictError, NotFoundError

logger = logging.getLogger("sira.caja")


def _ahora() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class CajaService:
    def __init__(self, repo: CajaRepository) -> None:
        self.repo = repo

    # ============================================================ US1: cuadre
    async def registrar_apertura(
        self, *, caja_id: int, cajero_id: int, fondo_inicial: Decimal
    ):
        """FR-001 — apertura de caja al inicio del turno."""
        return await self.repo.crear_apertura(
            caja_id=caja_id,
            cajero_id=cajero_id,
            fondo_inicial=fondo_inicial,
            fecha_hora=_ahora(),
        )

    async def calcular_total_esperado(
        self, *, caja_id: int, momento: datetime
    ) -> tuple[Decimal, int]:
        """FR-003 / research.md Decisión 1/2 — total esperado del cuadre: suma de
        las ventas del cajero (por `cajero_id`, no por caja) desde el cuadre
        anterior de esa caja (o su apertura) hasta `momento`. Devuelve
        `(total_esperado, cajero_id)`."""
        apertura = await self.repo.apertura_vigente(caja_id, momento)
        if apertura is None:
            raise ConflictError(
                f"La caja {caja_id} no tiene una apertura vigente; regístrala antes de cuadrar"
            )
        ultimo = await self.repo.ultimo_cierre(caja_id, momento)
        desde = ultimo.fecha_hora if ultimo is not None else apertura.fecha_hora
        ventas = await self.repo.ventas_ventana_cajero(apertura.cajero_id, desde, momento)
        total = logica.total_esperado_ventana(ventas, desde=desde, hasta=momento)
        return total, apertura.cajero_id

    async def registrar_cierre(
        self, *, caja_id: int, total_registrado: Decimal
    ) -> dict:
        """FR-002/FR-003/FR-004 — registra el cuadre horario con `total_esperado`
        calculado server-side y marca automática para revisión si `diferencia <> 0`."""
        momento = _ahora()
        total_esperado, cajero_id = await self.calcular_total_esperado(
            caja_id=caja_id, momento=momento
        )
        cierre = await self.repo.crear_cierre(
            caja_id=caja_id,
            cajero_id=cajero_id,
            total_esperado=total_esperado,
            total_registrado=total_registrado,
            fecha_hora=momento,
        )
        return {
            "cierre_id": cierre.cierre_id,
            "caja_id": cierre.caja_id,
            "cajero_id": cierre.cajero_id,
            "total_esperado": cierre.total_esperado,
            "total_registrado": cierre.total_registrado,
            "diferencia": cierre.diferencia,
            "marcado_para_revision": logica.marcado_para_revision(cierre.diferencia),
            "fecha_hora": cierre.fecha_hora,
        }

    async def listar_cierres_tienda(
        self, *, tienda_id: int, dia: date | None = None
    ) -> list[dict]:
        """FR-005 — el estado de cuadre de todas las cajas de la tienda, en una
        sola consulta. El día por defecto es "hoy" en la misma referencia horaria
        (UTC) que usan los timestamps de cuadre."""
        filas = await self.repo.cierres_de_tienda(tienda_id, dia or _ahora().date())
        for f in filas:
            f["marcado_para_revision"] = logica.marcado_para_revision(f["diferencia"])
        return filas

    # ============================================================ US2: datáfonos
    async def listar_datafonos(self, estado: str | None = None):
        return await self.repo.listar_datafonos(estado)

    async def listar_cajas(self, tienda_id: int | None = None) -> list[dict]:
        return await self.repo.listar_cajas(tienda_id)

    async def registrar_datafono(
        self,
        *,
        caja_id: int,
        modelo: str | None,
        version_firmware: str | None,
        fecha_ultima_actualizacion,
    ):
        """FR-006 — da de alta un datáfono en el inventario. El estado de
        conformidad se calcula contra el estándar vigente (FR-007), no se recibe."""
        if not await self.repo.caja_existe(caja_id):
            raise NotFoundError(f"La caja {caja_id} no existe")
        version_minima = await self._version_minima_vigente()
        estado = logica.estado_datafono_restablecido(version_firmware, version_minima)
        return await self.repo.crear_datafono(
            caja_id=caja_id,
            modelo=modelo,
            version_firmware=version_firmware,
            fecha_ultima_actualizacion=fecha_ultima_actualizacion,
            estado=estado,
        )

    async def editar_datafono(
        self,
        datafono_id: int,
        *,
        modelo: str | None,
        version_firmware: str | None,
        fecha_ultima_actualizacion,
        campos_enviados: set[str],
    ):
        """FR-006 — edita los datos de inventario de un datáfono. Recalcula la
        conformidad salvo que esté `fuera_servicio` (ese estado sólo cambia por
        restablecer, FR-003 de 007)."""
        datafono = await self.repo.get_datafono(datafono_id)
        if datafono is None:
            raise NotFoundError(f"Datáfono {datafono_id} no existe")
        if "modelo" in campos_enviados:
            datafono.modelo = modelo
        if "version_firmware" in campos_enviados:
            datafono.version_firmware = version_firmware
        if "fecha_ultima_actualizacion" in campos_enviados:
            datafono.fecha_ultima_actualizacion = fecha_ultima_actualizacion
        if datafono.estado != "fuera_servicio":
            version_minima = await self._version_minima_vigente()
            datafono.estado = logica.estado_datafono_restablecido(
                datafono.version_firmware, version_minima
            )
        await self.repo.flush()
        return datafono

    async def _version_minima_vigente(self) -> str | None:
        vigente = await self.repo.configuracion_seguridad_vigente()
        return vigente.version_minima_firmware if vigente is not None else None

    async def evaluar_conformidad_datafonos(self) -> int:
        """FR-007 — recorre el inventario y marca `requiere_actualizacion` los
        datáfonos por debajo del estándar vigente (y devuelve a `activo` los que ya
        cumplen). No toca los `fuera_servicio`. Devuelve cuántos quedaron no
        conformes."""
        version_minima = await self._version_minima_vigente()
        no_conformes = 0
        for datafono in await self.repo.datafonos_evaluables():
            estado = logica.estado_datafono_restablecido(datafono.version_firmware, version_minima)
            datafono.estado = estado
            no_conformes += int(estado == "requiere_actualizacion")
        await self.repo.flush()
        return no_conformes

    # ============================================================ US1 (007): disponibilidad diaria
    async def marcar_datafono_fuera_servicio(self, datafono_id: int):
        """FR-001 — el Encargado de Tienda marca un datáfono como fuera de servicio."""
        datafono = await self.repo.get_datafono(datafono_id)
        if datafono is None:
            raise NotFoundError(f"Datáfono {datafono_id} no existe")
        if datafono.estado == "fuera_servicio":
            raise ConflictError(f"El datáfono {datafono_id} ya está fuera de servicio")
        return await self.repo.marcar_estado_datafono(datafono, "fuera_servicio")

    async def restablecer_datafono(self, datafono_id: int) -> dict:
        """FR-002/FR-003 — restablece un datáfono fuera de servicio reevaluando su
        conformidad de seguridad (reutiliza la regla de 006, sin duplicarla): queda
        `activo` si cumple el estándar vigente, `requiere_actualizacion` si no."""
        datafono = await self.repo.get_datafono(datafono_id)
        if datafono is None:
            raise NotFoundError(f"Datáfono {datafono_id} no existe")
        if datafono.estado != "fuera_servicio":
            raise ConflictError(
                f"El datáfono {datafono_id} no está fuera de servicio (está '{datafono.estado}')"
            )
        version_minima = await self._version_minima_vigente()
        estado = logica.estado_datafono_restablecido(datafono.version_firmware, version_minima)
        await self.repo.marcar_estado_datafono(datafono, estado)
        return {"datafono_id": datafono.datafono_id, "estado": estado}

    # ================================================= US3 (007): incidentes de seguridad
    async def registrar_incidente_seguridad(
        self, *, datafono_id: int | None, descripcion: str, registrado_por: int
    ):
        """FR-008 — registra un incidente de seguridad de pago, con o sin datáfono
        asociado (Edge Case)."""
        if datafono_id is not None and await self.repo.get_datafono(datafono_id) is None:
            raise NotFoundError(f"Datáfono {datafono_id} no existe")
        return await self.repo.crear_incidente_seguridad(
            datafono_id=datafono_id, registrado_por=registrado_por, descripcion=descripcion
        )

    async def listar_incidentes_seguridad(self, estado: str | None = None):
        return await self.repo.listar_incidentes_seguridad(estado)

    async def transicionar_incidente_seguridad(
        self, incidente_id: int, *, estado_nuevo: str, empleado_id: int
    ):
        """FR-009 — avanza el incidente entre abierto → en_investigacion → cerrado,
        dejando constancia de quién y cuándo."""
        incidente = await self.repo.get_incidente_seguridad(incidente_id)
        if incidente is None:
            raise NotFoundError(f"Incidente de seguridad {incidente_id} no existe")
        try:
            incidente.estado = pagos.siguiente_estado_incidente_seguridad(
                incidente.estado, estado_nuevo
            )
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        incidente.actualizado_por = empleado_id
        incidente.fecha_actualizacion = _ahora()
        await self.repo.flush()
        return incidente

    async def contar_incidentes_seguridad(self, desde: date | None, hasta: date | None) -> dict:
        """FR-011 — número de incidentes de seguridad de pago de un periodo."""
        total = await self.repo.contar_incidentes_seguridad(desde, hasta)
        return {"total": total, "periodo": {"desde": desde, "hasta": hasta}}

    # ============================================================ US4 (007): política de seguridad
    async def politica_seguridad_vigente(self):
        """FR-013 — texto vigente de la política de seguridad de pagos."""
        vigente = await self.repo.politica_vigente()
        if vigente is None:
            raise NotFoundError("Aún no se ha definido una política de seguridad de pagos")
        return vigente

    async def politica_seguridad_por_id(self, politica_id: int):
        """FR-014 — una versión específica de la política (aunque ya no sea vigente)."""
        fila = await self.repo.get_politica(politica_id)
        if fila is None:
            raise NotFoundError(f"Política de seguridad {politica_id} no existe")
        return fila

    async def definir_politica_seguridad(self, *, texto: str, definido_por: int):
        """FR-012 — nueva versión vigente (append-only, research.md Decisión 5)."""
        return await self.repo.crear_politica(texto=texto, definido_por=definido_por)

    async def actualizar_datafono(self, datafono_id: int, version_firmware_nueva: str):
        """FR-008 — registra la actualización/reemplazo: vuelve a `activo` y deja
        constancia de la fecha."""
        datafono = await self.repo.get_datafono(datafono_id)
        if datafono is None:
            raise NotFoundError(f"Datáfono {datafono_id} no existe")
        if datafono.estado == "activo":
            raise ConflictError(f"El datáfono {datafono_id} ya está conforme (activo)")
        datafono.version_firmware = version_firmware_nueva
        datafono.estado = "activo"
        datafono.fecha_ultima_actualizacion = date.today()
        await self.repo.flush()
        return datafono

    async def configuracion_seguridad_vigente(self):
        vigente = await self.repo.configuracion_seguridad_vigente()
        if vigente is None:
            raise NotFoundError("Aún no se ha definido un estándar de seguridad de pagos")
        return vigente

    async def definir_estandar_seguridad(
        self, *, version_minima_firmware: str, actualizado_por: int
    ):
        """FR-007 / research.md Decisión 5 — inserta una nueva versión vigente y
        recalcula la conformidad de todos los datáfonos (efecto secundario
        documentado en contracts/)."""
        fila = await self.repo.crear_configuracion_seguridad(
            version_minima_firmware=version_minima_firmware, actualizado_por=actualizado_por
        )
        await self.evaluar_conformidad_datafonos()
        return fila

    # ============================================================ US3: reporte + escalamiento
    async def generar_reporte_diferencias(self, *, mes: int, anio: int) -> dict:
        """FR-009/FR-010 — diferencias de cuadre agrupadas por cajero y turno, más
        los ajustes de inventario de 001 con faltante sobre el umbral configurable."""
        cierres = await self.repo.cierres_del_mes(mes, anio)
        cuadres = logica.agrupar_diferencias_por_turno(cierres)

        umbral = await self.repo.umbral_ajuste_anomalo()
        ajustes = await self.repo.ajustes_negativos_del_mes(mes, anio)
        senalados = [
            a for a in ajustes if logica.ajuste_inventario_anomalo(a["diferencia"], umbral)
        ]
        return {"cuadres": cuadres, "ajustes_senalados": senalados}

    async def escalar_incidente(self, data: IncidenteFraudeIn):
        """FR-011 — abre un incidente de fraude con la evidencia que lo originó.
        `cierre_id`/`ajuste_id` son opcionales (data-model.md, Decisión 6)."""
        return await self.repo.crear_incidente(
            empleado_id=data.empleado_id,
            descripcion=data.descripcion,
            cierre_id=data.cierre_id,
            ajuste_id=data.ajuste_id,
        )

    # ============================================================ US4: incidentes + protocolo
    async def listar_incidentes(self, *, estado: str | None = None, tienda_id: int | None = None):
        return await self.repo.listar_incidentes(estado=estado, tienda_id=tienda_id)

    async def protocolo_vigente(self):
        """FR-013 — texto del protocolo de escalamiento vigente."""
        vigente = await self.repo.protocolo_vigente()
        if vigente is None:
            raise NotFoundError("Aún no se ha definido un protocolo de escalamiento")
        return vigente

    async def definir_protocolo(self, *, texto: str, definido_por: int):
        """FR-012 / research.md Decisión 7 — nueva versión del protocolo (append-only)."""
        return await self.repo.crear_protocolo(texto=texto, definido_por=definido_por)

    async def aplicar_protocolo(
        self, incidente_id: int, *, acciones_tomadas: str, empleado_id: int
    ):
        """FR-014 — el Encargado registra las acciones y el incidente pasa a
        `en_revision`."""
        incidente = await self._incidente_o_404(incidente_id)
        self._transicionar(incidente, "aplicar_protocolo", empleado_id)
        incidente.acciones_tomadas = acciones_tomadas
        await self.repo.flush()
        return incidente

    async def cerrar_incidente(self, incidente_id: int, *, resultado: str, empleado_id: int):
        """FR-015/FR-016 — el Jefe de Finanzas cierra el incidente con su resultado.
        No se bloquea por `fecha_baja` del empleado involucrado."""
        incidente = await self._incidente_o_404(incidente_id)
        self._transicionar(incidente, "cerrar", empleado_id)
        incidente.resultado = resultado
        await self.repo.flush()
        return incidente

    async def _incidente_o_404(self, incidente_id: int):
        incidente = await self.repo.get_incidente(incidente_id)
        if incidente is None:
            raise NotFoundError(f"Incidente {incidente_id} no existe")
        return incidente

    @staticmethod
    def _transicionar(incidente, accion: str, empleado_id: int) -> None:
        try:
            incidente.estado = logica.siguiente_estado_incidente(incidente.estado, accion)
        except ValueError as exc:
            raise ConflictError(str(exc)) from exc
        incidente.actualizado_por = empleado_id
        incidente.fecha_actualizacion = _ahora()

    # ============================================================ US5: umbral de merma
    async def listar_umbrales(self):
        return await self.repo.listar_umbrales()

    async def definir_umbral(
        self, *, product_category: str, porcentaje_umbral: Decimal, definido_por: int
    ):
        """FR-017 — upsert del umbral aceptable de una categoría (research.md Decisión 8)."""
        return await self.repo.upsert_umbral(
            product_category=product_category,
            porcentaje_umbral=porcentaje_umbral,
            definido_por=definido_por,
        )

    async def calcular_seguimiento_semanal(
        self, *, tienda_id: int, semana: int, anio: int | None = None
    ) -> list[dict]:
        """FR-018/FR-019 / research.md Decisión 9 — % de merma acumulada de la
        tienda por categoría frente al umbral definido, para la semana indicada.
        `supera_umbral` es informativo, nunca bloquea nada."""
        anio = anio or _ahora().isocalendar().year
        filas = await self.repo.listar_umbrales()
        umbrales = {u.product_category: u.porcentaje_umbral for u in filas}
        if not umbrales:
            return []
        mermas = await self.repo.valor_merma_semana(tienda_id, semana, anio)
        ventas = await self.repo.valor_ventas_semana(tienda_id, semana, anio)

        salida = []
        for categoria, umbral in sorted(umbrales.items()):
            pct = logica.porcentaje_merma(
                mermas.get(categoria, Decimal("0")), ventas.get(categoria, Decimal("0"))
            )
            salida.append(
                {
                    "product_category": categoria,
                    "porcentaje_merma_acumulado": pct,
                    "porcentaje_umbral": umbral,
                    "supera_umbral": logica.supera_umbral(pct, umbral),
                }
            )
        return salida
