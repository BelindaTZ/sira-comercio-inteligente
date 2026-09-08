"""RRHHService — regla de negocio del CRUD de empleado (feature 008)."""

from __future__ import annotations

from datetime import date

from src.models.empleado import Empleado
from src.modules.rrhh.repository import RRHHRepository
from src.modules.rrhh.schemas import EmpleadoIn, EmpleadoPatch
from src.shared.exceptions import NotFoundError


class RRHHService:
    def __init__(self, repo: RRHHRepository) -> None:
        self.repo = repo

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
