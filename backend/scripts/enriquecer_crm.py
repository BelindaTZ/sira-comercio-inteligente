"""Enriquecimiento genérico del CRM para la demo.

El dataset Dunnhumby "The Complete Journey" es anónimo: los clientes sólo traen
`household_id` + bandas demográficas, sin nombre, RUT, email ni teléfono. Este
script rellena esa identidad con datos **chilenos sintéticos, deterministas e
idempotentes** (sólo toca columnas NULL) y calcula el CLV de cada cliente sobre
TODO el histórico de ventas — el job real usa una ventana de 180 días que, con
las ventas de 2017, no devuelve nada (mismo criterio que la clasificación ABC de
la carga inicial).

  - `clientes.nombre / documento_identidad / email / telefono / fecha_nacimiento`
  - `cliente_clv` (score compuesto frecuencia + gasto, nivel por umbral)
  - `churn_score` recalculado con una fecha de referencia al final del dataset
    (si no, todos quedarían 'inactivo' por igual con la fecha de hoy)

Nada de esto pretende ser real: son datos de relleno para la demo. Los clientes
dados de alta por la UI traen sus datos verdaderos.

Uso:
    cd backend
    .venv/Scripts/python -m scripts.enriquecer_crm
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta

from sqlalchemy import text

from src.core.database import AsyncSessionLocal

log = logging.getLogger("sira.enriquecer_crm")

NOMBRES = [
    "Valentina", "Rodrigo", "Francisca", "Álvaro", "Catalina", "Matías", "Javiera",
    "Sebastián", "Antonia", "Cristóbal", "Isidora", "Benjamín", "Josefa", "Vicente",
    "Florencia", "Ignacio", "Emilia", "Tomás", "Martina", "Diego", "Constanza",
    "Felipe", "Trinidad", "Nicolás", "Amanda", "Joaquín", "Fernanda", "Agustín",
    "Camila", "Maximiliano", "Sofía", "Gaspar", "Renata", "Lucas", "Magdalena",
    "Bruno", "Pía", "Simón", "Rosario", "Andrés",
]
APELLIDOS = [
    "González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva",
    "Martínez", "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Hernández",
    "Torres", "Araya", "Flores", "Espinoza", "Valenzuela", "Castillo", "Tapia",
    "Reyes", "Gutiérrez", "Castro", "Pizarro", "Álvarez", "Vásquez", "Sánchez",
    "Fernández", "Gómez", "Cortés", "Herrera", "Núñez", "Vergara", "Riquelme",
    "Larraín", "Errázuriz", "Undurraga", "Edwards",
]


def _rut(n: int) -> str:
    """RUT chileno con dígito verificador módulo 11 a partir de un número base."""
    cuerpo = 6_000_000 + (n * 2_999_999 % 20_000_000)
    s, mul = 0, 2
    for d in reversed(str(cuerpo)):
        s += int(d) * mul
        mul = 2 if mul == 7 else mul + 1
    resto = 11 - (s % 11)
    dv = "0" if resto == 11 else "K" if resto == 10 else str(resto)
    c = f"{cuerpo:,}".replace(",", ".")
    return f"{c}-{dv}"


async def _identidad(s) -> None:
    filas = await s.execute(
        text("SELECT household_id, fecha_registro FROM clientes WHERE nombre IS NULL")
    )
    filas = filas.all()
    if not filas:
        log.info("identidad: nada que rellenar")
        return
    for hid, freg in filas:
        nom = NOMBRES[hid % len(NOMBRES)]
        ap1 = APELLIDOS[(hid * 13) % len(APELLIDOS)]
        ap2 = APELLIDOS[(hid * 29 + 7) % len(APELLIDOS)]
        rut = _rut(hid)
        base_mail = f"{nom}.{ap1}".lower().translate(
            str.maketrans("áéíóúñ", "aeioun")
        )
        dominio = ["gmail.com", "hotmail.com", "outlook.cl", "uc.cl", "empresas.cl"][hid % 5]
        # edad 24–72 determinista → fecha de nacimiento
        edad = 24 + (hid * 37 % 48)
        anio_base = (freg.year if freg else 2017) - edad
        fnac = date(anio_base, 1, 1) + timedelta(days=(hid * 97) % 364)
        await s.execute(
            text("""
            UPDATE clientes SET
              nombre = :nombre,
              documento_identidad = COALESCE(documento_identidad, :rut),
              email = COALESCE(email, :email),
              telefono = COALESCE(telefono, :tel),
              fecha_nacimiento = COALESCE(fecha_nacimiento, :fnac)
            WHERE household_id = :hid
            """),
            {
                "nombre": f"{nom} {ap1} {ap2}",
                "rut": rut,
                "email": f"{base_mail}{hid % 97}@{dominio}",
                "tel": f"+56 9 {2000 + hid % 8000:04d} {1000 + hid * 7 % 9000:04d}",
                "fnac": fnac,
                "hid": hid,
            },
        )
    log.info("identidad: %d clientes", len(filas))


async def _clv(s) -> None:
    """CLV compuesto sobre TODO el histórico: frecuencia (nº de compras) y gasto
    real, normalizados a su p95, 60/40. Nivel por `umbral_clv_min` (score 0–1)."""
    await s.execute(text("DELETE FROM cliente_clv WHERE fecha_calculo = CURRENT_DATE"))
    r = await s.execute(
        text("""
        WITH compras AS (
            SELECT household_id,
                   count(*)::numeric AS freq,
                   COALESCE(sum(total), 0)::numeric AS gasto
            FROM ventas
            WHERE household_id IS NOT NULL AND estado = 'confirmada'
            GROUP BY household_id
            HAVING count(*) >= 1
        ), p95 AS (
            SELECT percentile_cont(0.95) WITHIN GROUP (ORDER BY freq)  AS f95,
                   percentile_cont(0.95) WITHIN GROUP (ORDER BY gasto) AS g95
            FROM compras
        ), score AS (
            SELECT c.household_id,
                   LEAST(1.0, round((
                     0.6 * LEAST(1.0, c.freq  / NULLIF(p95.f95, 0)) +
                     0.4 * LEAST(1.0, c.gasto / NULLIF(p95.g95, 0))
                   )::numeric, 4)) AS clv
            FROM compras c CROSS JOIN p95
        )
        INSERT INTO cliente_clv (household_id, nivel_id, clv_score, fecha_calculo)
        SELECT sc.household_id,
               (SELECT nivel_id FROM niveles_fidelizacion n
                 WHERE n.umbral_clv_min <= sc.clv
                 ORDER BY n.umbral_clv_min DESC LIMIT 1),
               sc.clv,
               CURRENT_DATE
        FROM score sc
        """)
    )
    log.info("cliente_clv: %d filas", r.rowcount)


async def _churn(s) -> None:
    """Recalcula `churn_score` con una fecha de referencia al final del dataset
    (no 'hoy', que dejaría a los ~2469 clientes como 'inactivo' por igual). Así
    la severidad refleja los quiebres reales del ciclo de compra de 2017."""
    from src.shared.churn import ciclo_compra_dias, score_churn, severidad

    filas = await s.execute(
        text("""
        SELECT household_id, array_agg(fecha_hora::date) AS fechas
        FROM ventas WHERE household_id IS NOT NULL AND estado = 'confirmada'
        GROUP BY household_id
        """)
    )
    filas = filas.all()
    ref = max((max(f[1]) for f in filas), default=None)
    if ref is None:
        return
    ref = ref + timedelta(days=10)
    # recompute total para la demo (el job real acumula corridas semanales)
    await s.execute(text("DELETE FROM churn_score"))
    n = 0
    for hid, fechas in filas:
        ciclo = ciclo_compra_dias(fechas)
        if ciclo is None or ciclo <= 0:
            continue
        # desfase determinista 0–35 d por cliente → variedad estable/en_riesgo/inactivo
        dias = (ref - max(fechas)).days + (hid * 17 % 36)
        sev = severidad(dias, ciclo)
        if sev is None:
            continue
        await s.execute(
            text("""
            INSERT INTO churn_score (household_id, score, ciclo_compra_dias, severidad,
                                     fecha_calculo)
            VALUES (:h, :sc, :ci, :se, CURRENT_DATE)
            """),
            {"h": hid, "sc": score_churn(dias, ciclo), "ci": round(ciclo), "se": sev},
        )
        n += 1
    log.info("churn_score: %d filas (ref=%s)", n, ref)


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    async with AsyncSessionLocal() as s:
        await _identidad(s)
        await _clv(s)
        await _churn(s)
        await s.commit()
    log.info("listo")


if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
