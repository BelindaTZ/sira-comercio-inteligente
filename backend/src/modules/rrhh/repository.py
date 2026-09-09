"""RRHHRepository — acceso a datos del módulo RRHH. Sin lógica de negocio
(Principio XI).

Feature 008: CRUD base de `empleados`.
Feature 011: puestos críticos (`roles_puesto.es_critico`), `acciones_retencion`,
capacitación con fan-out (`capacitaciones`, `empleado_capacitacion`, más una
consulta de solo lectura a `usuarios.role_id` de `modules/sistema/` — boundary
documentado en plan.md), clima laboral + rotación (`clima_laboral`,
`empleados.fecha_baja`) y plan de sucesión (`plan_sucesion`).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.accion_retencion import AccionRetencion
from src.models.capacitacion import Capacitacion
from src.models.clima_laboral import ClimaLaboral
from src.models.empleado import Empleado
from src.models.empleado_capacitacion import EmpleadoCapacitacion
from src.models.plan_sucesion import PlanSucesion
from src.models.rol_puesto import RolPuesto


class RRHHRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---------------------------------------------------------------- empleados (008)
    async def get(self, empleado_id: int) -> Empleado | None:
        return await self.session.get(Empleado, empleado_id)

    async def crear(self, empleado: Empleado) -> Empleado:
        self.session.add(empleado)
        await self.session.flush()
        await self.session.refresh(empleado)
        return empleado

    async def flush(self) -> None:
        await self.session.flush()

    async def dar_baja(self, empleado: Empleado, fecha_baja: date) -> Empleado:
        empleado.activo = False
        empleado.fecha_baja = fecha_baja
        await self.session.flush()
        # el trigger trg_inhabilitar_cuenta_baja_empleado ya inhabilitó la cuenta;
        # se recarga para que un GET posterior en la misma sesión lo refleje.
        await self.session.refresh(empleado)
        return empleado

    # ---------------------------------------------------------------- puestos críticos (011)
    async def get_puesto(self, puesto_id: int) -> RolPuesto | None:
        return await self.session.get(RolPuesto, puesto_id)

    async def marcar_puesto_critico(self, puesto: RolPuesto, es_critico: bool) -> RolPuesto:
        puesto.es_critico = es_critico
        await self.session.flush()
        return puesto

    # ---------------------------------------------------------------- retención (011)
    async def crear_accion_retencion(self, accion: AccionRetencion) -> AccionRetencion:
        self.session.add(accion)
        await self.session.flush()
        await self.session.refresh(accion)
        return accion

    async def acciones_retencion_de(self, empleado_id: int) -> list[AccionRetencion]:
        stmt = (
            select(AccionRetencion)
            .where(AccionRetencion.empleado_id == empleado_id)
            .order_by(AccionRetencion.fecha.desc(), AccionRetencion.accion_id.desc())
        )
        return list((await self.session.scalars(stmt)).all())

    # ---------------------------------------------------------------- capacitación (011)
    async def crear_capacitacion(self, capacitacion: Capacitacion) -> Capacitacion:
        self.session.add(capacitacion)
        await self.session.flush()
        await self.session.refresh(capacitacion)
        return capacitacion

    async def empleados_con_cuenta_activa_en_roles(self, role_ids: list[int]) -> list[int]:
        """Fan-out: `empleado_id` de los empleados con cuenta de usuario activa
        (`usuarios`, 008) cuyo `role_id` esté entre los roles objetivo. Un empleado
        sin cuenta NO se incluye (research.md Decisión 2, boundary con 008)."""
        if not role_ids:
            return []
        rows = await self.session.execute(
            text("""
                SELECT u.empleado_id
                FROM usuarios u
                JOIN empleados e ON e.empleado_id = u.empleado_id
                WHERE u.activo = true
                  AND e.activo = true
                  AND u.role_id = ANY(:role_ids)
                ORDER BY u.empleado_id
            """),
            {"role_ids": role_ids},
        )
        return [r.empleado_id for r in rows]

    async def asignar_capacitacion(self, capacitacion_id: int, empleado_ids: list[int]) -> int:
        """Inserta una fila pendiente por empleado (idempotente ante reejecución)."""
        insertados = 0
        for empleado_id in empleado_ids:
            self.session.add(
                EmpleadoCapacitacion(
                    empleado_id=empleado_id, capacitacion_id=capacitacion_id, fecha_completado=None
                )
            )
            insertados += 1
        await self.session.flush()
        return insertados

    async def get_registro_capacitacion(
        self, empleado_id: int, capacitacion_id: int
    ) -> EmpleadoCapacitacion | None:
        return await self.session.get(EmpleadoCapacitacion, (empleado_id, capacitacion_id))

    async def completar_capacitacion(
        self, registro: EmpleadoCapacitacion, fecha_completado: date
    ) -> EmpleadoCapacitacion:
        registro.fecha_completado = fecha_completado
        await self.session.flush()
        return registro

    async def tienda_de_empleado(self, empleado_id: int) -> int | None:
        return await self.session.scalar(
            text("SELECT tienda_id FROM empleados WHERE empleado_id = :e"), {"e": empleado_id}
        )

    async def cumplimiento_por_tienda(self, tienda_id: int) -> list[dict]:
        rows = await self.session.execute(
            text("""
                SELECT e.empleado_id, e.nombre,
                       rp.nombre AS puesto, e.fecha_contratacion,
                       c.capacitacion_id, c.nombre AS nombre_capacitacion,
                       ec.fecha_completado
                FROM empleado_capacitacion ec
                JOIN empleados e ON e.empleado_id = ec.empleado_id
                JOIN capacitaciones c ON c.capacitacion_id = ec.capacitacion_id
                LEFT JOIN roles_puesto rp ON rp.puesto_id = e.puesto_id
                WHERE e.tienda_id = :t
                ORDER BY e.nombre, c.nombre
            """),
            {"t": tienda_id},
        )
        return [dict(r._mapping) for r in rows]

    async def listar_capacitaciones(self, tienda_id: int | None = None) -> list[dict]:
        """Catálogo de capacitaciones con su avance (asignados / completados). Si
        se pasa `tienda_id`, los contadores se limitan al personal de esa tienda;
        si no, son de toda la red."""
        filtro = "AND e.tienda_id = :t" if tienda_id is not None else ""
        rows = await self.session.execute(
            text(f"""
                SELECT c.capacitacion_id, c.nombre, c.descripcion,
                       count(e.empleado_id) AS asignados,
                       count(ec.fecha_completado) FILTER (WHERE e.empleado_id IS NOT NULL)
                         AS completados
                FROM capacitaciones c
                LEFT JOIN empleado_capacitacion ec
                       ON ec.capacitacion_id = c.capacitacion_id
                LEFT JOIN empleados e
                       ON e.empleado_id = ec.empleado_id {filtro}
                GROUP BY c.capacitacion_id, c.nombre, c.descripcion
                ORDER BY c.nombre
            """),
            {"t": tienda_id} if tienda_id is not None else {},
        )
        return [dict(r._mapping) for r in rows]

    async def listar_roles(self) -> list[dict]:
        rows = await self.session.execute(
            text("SELECT role_id, nombre FROM roles ORDER BY nombre")
        )
        return [dict(r._mapping) for r in rows]

    async def listar_tiendas_activas(self) -> list[dict]:
        rows = await self.session.execute(
            text(
                "SELECT tienda_id, codigo, nombre, ciudad FROM tiendas "
                "WHERE activa = true ORDER BY nombre"
            )
        )
        return [dict(r._mapping) for r in rows]

    # ---------------------------------------------------------------- clima / rotación (011)
    async def crear_clima(self, clima: ClimaLaboral) -> ClimaLaboral:
        self.session.add(clima)
        await self.session.flush()
        await self.session.refresh(clima)
        return clima

    async def clima_de(self, tienda_id: int, periodo: str) -> ClimaLaboral | None:
        stmt = (
            select(ClimaLaboral)
            .where(ClimaLaboral.tienda_id == tienda_id, ClimaLaboral.periodo == periodo)
            .order_by(ClimaLaboral.encuesta_id.desc())
        )
        return (await self.session.scalars(stmt)).first()

    async def conteo_rotacion(self, tienda_id: int, inicio: date, fin: date) -> tuple[int, int]:
        """`(bajas dentro del periodo, plantilla al inicio del periodo)` para una
        tienda, a partir de `empleados.fecha_contratacion` / `fecha_baja`."""
        row = (
            await self.session.execute(
                text("""
                    SELECT
                      COUNT(*) FILTER (
                        WHERE fecha_baja IS NOT NULL AND fecha_baja BETWEEN :inicio AND :fin
                      ) AS bajas,
                      COUNT(*) FILTER (
                        WHERE fecha_contratacion <= :fin
                          AND (fecha_baja IS NULL OR fecha_baja >= :inicio)
                      ) AS plantilla_base
                    FROM empleados
                    WHERE tienda_id = :t
                """),
                {"t": tienda_id, "inicio": inicio, "fin": fin},
            )
        ).first()
        return int(row.bajas), int(row.plantilla_base)

    # ---------------------------------------------------------------- plan de sucesión (011)
    async def crear_sucesion(self, sucesion: PlanSucesion) -> PlanSucesion:
        self.session.add(sucesion)
        await self.session.flush()
        await self.session.refresh(sucesion)
        return sucesion

    async def cobertura_sucesion(self) -> list[dict]:
        """Todos los puestos críticos con sus candidatos (research.md Decisión 4)."""
        rows = await self.session.execute(text("""
                SELECT rp.puesto_id, rp.nombre,
                       ps.empleado_candidato_id, e.nombre AS nombre_candidato, ps.fecha
                FROM roles_puesto rp
                LEFT JOIN plan_sucesion ps ON ps.puesto_id = rp.puesto_id
                LEFT JOIN empleados e ON e.empleado_id = ps.empleado_candidato_id
                WHERE rp.es_critico = true
                ORDER BY rp.nombre, ps.fecha
            """))
        return [dict(r._mapping) for r in rows]
