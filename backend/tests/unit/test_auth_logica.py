"""T010 + T024 + T031 — reglas puras de autenticación (Principio X).

- rechazo de login sin distinguir causa (FR-002/FR-003)
- token de recuperación de un solo uso con vigencia limitada (FR-010)
- el JWT no embebe el rol → un cambio de rol tiene efecto inmediato (FR-012)
"""

from datetime import datetime, timedelta

import jwt
from src.core.config import settings
from src.core.security import crear_access_token, decode_usuario_id
from src.shared.auth import login_permitido, token_recuperacion_utilizable
from src.shared.passwords import hash_password, verify_password

AHORA = datetime(2026, 9, 8, 12, 0, 0)


# --- T010: login sin distinguir causa ---
def test_login_permitido_solo_con_las_tres_condiciones():
    assert login_permitido(usuario_existe=True, usuario_activo=True, password_ok=True) is True


def test_login_rechazado_no_distingue_la_causa():
    # username inexistente, cuenta inactiva y contraseña incorrecta → el mismo False
    inexistente = login_permitido(usuario_existe=False, usuario_activo=False, password_ok=False)
    inactiva = login_permitido(usuario_existe=True, usuario_activo=False, password_ok=True)
    pass_mala = login_permitido(usuario_existe=True, usuario_activo=True, password_ok=False)
    assert inexistente == inactiva == pass_mala is False


def test_hash_password_round_trip():
    h = hash_password("Contraseña-Segura-123")
    assert h != "Contraseña-Segura-123"
    assert verify_password("Contraseña-Segura-123", h) is True
    assert verify_password("otra", h) is False
    assert verify_password("x", "") is False


# --- T024: token de recuperación de un solo uso ---
def test_token_recuperacion_vigente_y_no_usado_sirve():
    assert token_recuperacion_utilizable(
        usado=False, fecha_expiracion=AHORA + timedelta(minutes=10), ahora=AHORA
    ) is True


def test_token_recuperacion_usado_no_sirve():
    assert token_recuperacion_utilizable(
        usado=True, fecha_expiracion=AHORA + timedelta(minutes=10), ahora=AHORA
    ) is False


def test_token_recuperacion_vencido_no_sirve():
    assert token_recuperacion_utilizable(
        usado=False, fecha_expiracion=AHORA - timedelta(seconds=1), ahora=AHORA
    ) is False


# --- T031: el JWT no embebe el rol ---
def test_jwt_solo_transporta_usuario_id():
    token, _ttl = crear_access_token(99)
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert payload["usuario_id"] == 99
    assert "role_id" not in payload and "rol" not in payload
    assert decode_usuario_id(token) == 99
