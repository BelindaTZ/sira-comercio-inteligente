"""Excepciones de dominio, respuestas de error estándar y logging (T011).

Formato único de error para toda la API:
    {"error": {"code": "<slug>", "message": "<texto>", "details": <opcional>}}
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

logger = logging.getLogger("sira")


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
    )


class DomainError(Exception):
    """Error de regla de negocio. Cada subclase fija su `status_code` y `code`."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "domain_error"

    def __init__(self, message: str, *, details: Any = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class NotFoundError(DomainError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(DomainError):
    """Choca con el estado actual (ej. stock insuficiente, FR-006)."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class BusinessRuleError(DomainError):
    """Viola una invariante de negocio (ej. stock por lote insuficiente)."""

    status_code = 422  # Unprocessable Content
    code = "business_rule"


class ForbiddenError(DomainError):
    """Acción no permitida por una regla de control (ej. el mismo empleado
    registra y autoriza — FR-027/FR-034). Distinto de un fallo de RBAC."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"


def _payload(code: str, message: str, details: Any = None) -> dict[str, Any]:
    body: dict[str, Any] = {"error": {"code": code, "message": message}}
    if details is not None:
        body["error"]["details"] = details
    return body


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_: Request, exc: DomainError) -> JSONResponse:
        logger.info("DomainError %s: %s", exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content=_payload(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,  # Unprocessable Content
            content=_payload(
                "validation_error",
                "Datos de entrada inválidos",
                jsonable_encoder(exc.errors()),
            ),
        )

    @app.exception_handler(IntegrityError)
    async def _integrity(_: Request, exc: IntegrityError) -> JSONResponse:
        # Los CHECK de doble persona (cajero<>autoriza, registra<>autoriza) llegan
        # aquí si el servicio no los atajó antes: se traducen a 409, no a 500.
        logger.warning("IntegrityError: %s", exc.orig)
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_payload("integrity_error", "La operación viola una restricción de datos"),
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Error no controlado: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_payload("internal_error", "Error interno del servidor"),
        )
