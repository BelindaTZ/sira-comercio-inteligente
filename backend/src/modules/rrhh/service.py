"""RRHHService — regla de negocio del módulo RRHH.

Feature 008: CRUD de empleado.
Feature 011: puestos críticos y retención (US1), capacitación con fan-out por rol
(US2), clima laboral cruzado con la tasa de rotación del mismo periodo (US3) y
plan de sucesión con señalización de cobertura (US4). El cálculo de rotación y la
señalización de cobertura nunca ocurren en el frontend (Principio V).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from src.models.accion_retencion import AccionRetencion
from src.models.capacitacion import Capacitacion
from src.models.clima_laboral import ClimaLaboral
from src.models.empleado import Empleado
from src.models.plan_sucesion import PlanSucesion
from src.models.rol_puesto import RolPuesto
from src.modules.rrhh.repository import RRHHRepository
from src.modules.rrhh.schemas import EmpleadoIn, EmpleadoPatch
from src.shared.exceptions import ForbiddenError, NotFoundError
from src.shared.rrhh import marcar_sin_cobertura, parse_periodo, tasa_rotacion


class RRHHService:
    def __init__(self, repo: RRHHRepository) -> None:
        self.repo = repo

    # ============================================================ 008: empleados
    async def crear_empleado(self, data: EmpleadoIn) -> Empleado:
        """FR-005 — alta de empleado."""
        return await self.repo.crear(
            Empleado(
                nombre=data.nombre.strip(),
                puesto_id=data.puesto_id,
                tienda_id=data.tienda_id,
                email=data.email,
                telefono=data.telefono,
                fecha_contratacion=data.fecha_contratacion,
                activo=True,
            )
        )

    async def actualizar_empleado(self, empleado_id: int, data: EmpleadoPatch) -> Empleado:
        """FR-006 — actualización de datos/puesto."""
        empleado = await self._empleado_o_404(empleado_id)
        for campo, valor in data.model_dump(exclude_unset=True).items():
            setattr(empleado, campo, valor)
        await self.repo.flush()
        return empleado

    async def dar_baja_empleado(self, empleado_id: int, fecha_baja: date) -> Empleado:
        """FR-014 — baja de empleado; el trigger de PostgreSQL inhabilita su cuenta
        automáticamente (research.md Decisión 4)."""
        empleado = await self._empleado_o_404(empleado_id)
        return await self.repo.dar_baja(empleado, fecha_baja)

    async def _empleado_o_404(self, empleado_id: int) -> Empleado:
        empleado = await self.repo.get(empleado_id)
        if empleado is None:
            raise NotFoundError(f"Empleado {empleado_id} no existe")
        return empleado

    # ============================================================ 011 US1: retención
    async def marcar_puesto_critico(self, puesto_id: int, es_critico: bool) -> RolPuesto:
        """FR-001 — marca/desmarca un puesto como crítico para toda la red."""
        puesto = await self.repo.get_puesto(puesto_id)
        if puesto is None:
            raise NotFoundError(f"Puesto {puesto_id} no existe")
        return await self.repo.marcar_puesto_critico(puesto, es_critico)

    async def registrar_accion_retencion(
        self, *, empleado_id: int, fecha: date, descripcion: str
    ) -> AccionRetencion:
        """FR-002 — se permite para un empleado en un puesto NO crítico (Edge Case);
        sólo los puestos críticos alimentan el KPI de OT-8.1."""
        await self._empleado_o_404(empleado_id)
        return await self.repo.crear_accion_retencion(
            AccionRetencion(empleado_id=empleado_id, fecha=fecha, descripcion=descripcion.strip())
        )

    async def acciones_retencion(self, empleado_id: int) -> list[AccionRetencion]:
        await self._empleado_o_404(empleado_id)
        return await self.repo.acciones_retencion_de(empleado_id)

    # ============================================================ 011 US2: capacitación
    async def programar_capacitacion(
        self, *, nombre: str, descripcion: str | None, role_ids: list[int]
    ) -> dict:
        """FR-003/FR-004 — INSERT en `capacitaciones` + fan-out inmediato hacia
        `empleado_capacitacion` para todos los empleados con cuenta activa en los
        roles objetivo (research.md Decisión 2)."""
        capacitacion = await self.repo.crear_capacitacion(
            Capacitacion(nombre=nombre.strip(), descripcion=descripcion)
        )
        objetivo = await self.repo.empleados_con_cuenta_activa_en_roles(sorted(set(role_ids)))
        asignados = await self.repo.asignar_capacitacion(capacitacion.capacitacion_id, objetivo)
        return {
            "capacitacion_id": capacitacion.capacitacion_id,
            "nombre": capacitacion.nombre,
            "descripcion": capacitacion.descripcion,
            "empleados_asignados": asignados,
        }

    async def confirmar_cumplimiento(
        self,
        *,
        empleado_id: int,
        capacitacion_id: int,
        fecha_completado: date,
        tienda_actor: int | None,
        restringir_a_tienda: bool,
    ):
        """FR-004/FR-005 — el `Encargado_Tienda` sólo puede confirmar el
        cumplimiento de empleados de su propia tienda."""
        registro = await self.repo.get_registro_capacitacion(empleado_id, capacitacion_id)
        if registro is None:
            raise NotFoundError(
                f"El empleado {empleado_id} no tiene asignada la capacitación {capacitacion_id}"
            )
        if restringir_a_tienda:
            tienda_empleado = await self.repo.tienda_de_empleado(empleado_id)
            if tienda_actor is None or tienda_empleado != tienda_actor:
                raise ForbiddenError(
                    "El Encargado de Tienda sólo confirma el cumplimiento de su propio personal"
                )
        return await self.repo.completar_capacitacion(registro, fecha_completado)

    async def cumplimiento_tienda(
        self, tienda_id: int, *, tienda_actor: int | None, restringir_a_tienda: bool
    ) -> list[dict]:
        """FR-005 — cumplimiento del personal de una tienda; el `Encargado_Tienda`
        no ve el de otras tiendas."""
        if restringir_a_tienda and tienda_id != tienda_actor:
            raise ForbiddenError(
                "El Encargado de Tienda sólo consulta el cumplimiento de su propia tienda"
            )
        return await self.repo.cumplimiento_por_tienda(tienda_id)

    # ============================================================ 011 US3: clima / rotación
    async def registrar_clima(
        self, *, tienda_id: int, periodo: str, resultado_promedio: Decimal
    ) -> ClimaLaboral:
        """FR-006 — resultado promedio de la encuesta por tienda y periodo semestral."""
        return await self.repo.crear_clima(
            ClimaLaboral(
                tienda_id=tienda_id, periodo=periodo, resultado_promedio=resultado_promedio
            )
        )

    async def clima_rotacion(self, tienda_id: int, periodo: str) -> dict:
        """FR-007/FR-010 — resultado de clima + tasa de rotación del mismo periodo,
        calculada desde `empleados.fecha_baja`. Un periodo sin encuesta registrada
        no devuelve ningún indicador: 404, sin dato inventado."""
        clima = await self.repo.clima_de(tienda_id, periodo)
        if clima is None:
            raise NotFoundError(
                f"No hay encuesta de clima para la tienda {tienda_id} en el periodo {periodo}"
            )
        inicio, fin = parse_periodo(periodo)
        bajas, plantilla_base = await self.repo.conteo_rotacion(tienda_id, inicio, fin)
        return {
            "encuesta_id": clima.encuesta_id,
            "resultado_promedio": clima.resultado_promedio,
            "tasa_rotacion_pct": tasa_rotacion(bajas=bajas, plantilla_base=plantilla_base),
        }

    # ============================================================ 011 US4: plan de sucesión
    async def registrar_candidato_sucesion(
        self, *, puesto_id: int, empleado_candidato_id: int
    ) -> PlanSucesion:
        """FR-008 — candidato interno para un puesto crítico."""
        puesto = await self.repo.get_puesto(puesto_id)
        if puesto is None:
            raise NotFoundError(f"Puesto {puesto_id} no existe")
        await self._empleado_o_404(empleado_candidato_id)
        return await self.repo.crear_sucesion(
            PlanSucesion(puesto_id=puesto_id, empleado_candidato_id=empleado_candidato_id)
        )

    async def cobertura_sucesion(self) -> list[dict]:
        """FR-009 — puestos críticos con sus candidatos; señala explícitamente los
        que no tienen ninguno."""
        agrupado: dict[int, dict] = {}
        for fila in await self.repo.cobertura_sucesion():
            puesto = agrupado.setdefault(
                fila["puesto_id"],
                {"puesto_id": fila["puesto_id"], "nombre": fila["nombre"], "candidatos": []},
            )
            if fila["empleado_candidato_id"] is not None:
                puesto["candidatos"].append(
                    {
                        "empleado_candidato_id": fila["empleado_candidato_id"],
                        "nombre": fila["nombre_candidato"],
                        "fecha": fila["fecha"],
                    }
                )
        return marcar_sin_cobertura(list(agrupado.values()))
