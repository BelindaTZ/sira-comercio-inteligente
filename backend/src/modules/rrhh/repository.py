"""RRHHRepository (feature 008) — CRUD base de `empleados`. Sin lógica de negocio
(Principio XI). La ampliación (capacitación, clima, sucesión) es de 011."""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from src.models.empleado import Empleado


class RRHHRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

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
