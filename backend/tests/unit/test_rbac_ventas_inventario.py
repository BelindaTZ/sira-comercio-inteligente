"""T074 — RBAC de dos niveles (rol→módulo→tabla) aplicado a los endpoints de 001.

Verifica la dependencia `require_permission` / `_has_permission` contra los
permisos realmente sembrados (base + rondas 7-10), y el decodificado del JWT.
"""

import jwt
import pytest
from fastapi import HTTPException
from sqlalchemy import text
from src.core.config import settings
from src.core.security import _has_permission, decode_token

# asyncio_mode = "auto" en pyproject: las pruebas async no necesitan marca; las
# de decodificado de token son síncronas y no deben llevarla.


async def _role_id(db_session, nombre: str) -> int:
    return await db_session.scalar(
        text("SELECT role_id FROM roles WHERE nombre = :n"), {"n": nombre}
    )


# --- decodificado del token ---
def test_decode_token_rechaza_firma_invalida():
    malo = jwt.encode({"empleado_id": 1, "role_id": 1}, "otra-clave", algorithm="HS256")
    with pytest.raises(HTTPException) as exc:
        decode_token(malo)
    assert exc.value.status_code == 401


def test_decode_token_exige_claims_obligatorios():
    incompleto = jwt.encode(
        {"empleado_id": 1}, settings.jwt_secret, algorithm=settings.jwt_algorithm
    )
    with pytest.raises(HTTPException) as exc:
        decode_token(incompleto)
    assert exc.value.status_code == 401


def test_decode_token_valido_extrae_principal():
    token = jwt.encode(
        {"empleado_id": 7, "role_id": 3, "rol": "Cajero", "tienda_id": 2},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    p = decode_token(token)
    assert p.empleado_id == 7 and p.role_id == 3 and p.tienda_id == 2


# --- rol → módulo → tabla ---
async def test_cajero_puede_insertar_ventas_pero_no_borrar(db_session):
    cajero = await _role_id(db_session, "Cajero")
    assert await _has_permission(db_session, cajero, "Ventas", "ventas", "insert") is True
    assert (
        await _has_permission(db_session, cajero, "Ventas", "ventas", "update") is True
    )  # ronda 7
    assert await _has_permission(db_session, cajero, "Ventas", "venta_detalle", "delete") is False


async def test_cajero_no_tiene_acceso_al_catalogo(db_session):
    cajero = await _role_id(db_session, "Cajero")
    assert await _has_permission(db_session, cajero, "Comercial", "productos", "update") is False


async def test_encargado_autoriza_remocion_de_linea(db_session):
    enc = await _role_id(db_session, "Encargado_Tienda")
    assert await _has_permission(db_session, enc, "Ventas", "venta_detalle", "delete") is True


async def test_reponedor_registra_pero_no_valida_mermas(db_session):
    rep = await _role_id(db_session, "Reponedor")
    assert await _has_permission(db_session, rep, "Operaciones", "mermas", "insert") is True
    assert await _has_permission(db_session, rep, "Operaciones", "mermas", "update") is False


async def test_reponedor_no_define_stock_maximo(db_session):
    rep = await _role_id(db_session, "Reponedor")
    assert (
        await _has_permission(db_session, rep, "Operaciones", "stock_maximo_categoria", "insert")
        is False
    )


async def test_finanzas_registra_pagos_a_proveedor(db_session):
    fin = await _role_id(db_session, "Jefe_Finanzas")
    assert await _has_permission(db_session, fin, "Finanzas", "pagos_proveedor", "insert") is True


async def test_jefe_comercial_edita_catalogo(db_session):
    com = await _role_id(db_session, "Jefe_Comercial")
    assert await _has_permission(db_session, com, "Comercial", "productos", "update") is True
    assert await _has_permission(db_session, com, "Comercial", "productos", "delete") is False


async def test_modulo_desconocido_niega(db_session):
    cajero = await _role_id(db_session, "Cajero")
    assert await _has_permission(db_session, cajero, "ModuloInventado", "ventas", "select") is False
