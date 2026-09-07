"""Esquema operativo base + extensiones de la feature 001

Aplica `01_operativo_postgres.sql` (fuente única de verdad del modelo operativo —
50 tablas + las extensiones aditivas de esta feature: alertas_inventario,
eventos_quiebre_stock, lineas_venta_removidas, intentos_pago_tarjeta,
facturas_proveedor, pagos_proveedor y las columnas nuevas en ventas/proveedores/
ordenes_compra/devoluciones/lotes). Principio VI: la migración referencia ese
archivo, no lo reescribe.

Revision ID: 0001
Revises:
Create Date: 2026-09-06

"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SQL_FILE = Path(__file__).resolve().parents[3] / "01_operativo_postgres.sql"


def _split_statements(script: str) -> list[str]:
    """Divide un script SQL en sentencias respetando comillas simples,
    comentarios de línea (--) y dollar-quoting ($tag$...$tag$)."""
    statements: list[str] = []
    buf: list[str] = []
    i = 0
    n = len(script)
    in_single = False
    dollar_tag: str | None = None

    while i < n:
        ch = script[i]
        nxt = script[i + 1] if i + 1 < n else ""

        if dollar_tag is not None:
            if script.startswith(dollar_tag, i):
                buf.append(dollar_tag)
                i += len(dollar_tag)
                dollar_tag = None
                continue
            buf.append(ch)
            i += 1
            continue

        if in_single:
            buf.append(ch)
            if ch == "'":
                if nxt == "'":
                    buf.append(nxt)
                    i += 2
                    continue
                in_single = False
            i += 1
            continue

        # fuera de comillas
        if ch == "-" and nxt == "-":
            eol = script.find("\n", i)
            if eol == -1:
                eol = n
            i = eol
            continue
        if ch == "'":
            in_single = True
            buf.append(ch)
            i += 1
            continue
        if ch == "$":
            end = script.find("$", i + 1)
            if end != -1:
                tag_body = script[i + 1 : end]
                if tag_body == "" or tag_body.isidentifier():
                    dollar_tag = script[i : end + 1]
                    buf.append(dollar_tag)
                    i = end + 1
                    continue
        if ch == ";":
            stmt = "".join(buf).strip()
            if stmt:
                statements.append(stmt)
            buf = []
            i += 1
            continue

        buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        statements.append(tail)
    return statements


def upgrade() -> None:
    script = SQL_FILE.read_text(encoding="utf-8")
    for statement in _split_statements(script):
        op.execute(statement)
        # Salvaguarda: la descripción de 'margen_minimo_global_pct' en
        # configuracion_pricing documenta el Edge Case de FR-007 y mide 201
        # caracteres. El .sql ya define VARCHAR(250); este ALTER (justo tras el
        # CREATE TABLE, antes del INSERT del seed) hace que la migración también
        # funcione si corre contra una copia previa del archivo con VARCHAR(200),
        # y es un no-op cuando la columna ya es >= 250.
        if statement.lstrip().upper().startswith("CREATE TABLE CONFIGURACION_PRICING"):
            op.execute(
                "ALTER TABLE configuracion_pricing ALTER COLUMN descripcion TYPE VARCHAR(250)"
            )


def downgrade() -> None:
    # El esquema base es el punto de partida; revertirlo = base limpia.
    op.execute("DROP SCHEMA public CASCADE")
    op.execute("CREATE SCHEMA public")
