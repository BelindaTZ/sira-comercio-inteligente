# SIRA — Backend (API REST)

FastAPI + SQLAlchemy 2.0 async + Alembic sobre PostgreSQL 16.

## Puesta en marcha (desarrollo)

```bash
# 1. Levantar infraestructura (desde la raíz del repo)
docker compose up -d postgres minio

# 2. Entorno Python
cd backend
python -m venv .venv && .venv/Scripts/activate      # Windows
pip install -e ".[dev]"

# 3. Configurar credenciales
cp .env.example .env        # y completar JWT_SECRET, claves de MinIO, etc.

# 4. Aplicar el esquema (migración 0001 = 01_operativo_postgres.sql completo)
alembic upgrade head

# 5. Servir
uvicorn src.main:app --reload
```

- Salud: `GET http://localhost:8000/api/health`
- Docs: `http://localhost:8000/docs`

### Datos de demo (para probar la app end-to-end)

```bash
# 1. dataset Dunnhumby completo (8 tiendas, 52 semanas, ~1-2 min). --muestra = 3 tiendas / 4 semanas.
#    Repetir con --reset para recargar sobre una BD ya poblada.
python -m scripts.cargar_dataset_inicial

# 2. cuentas de login + enriquecimiento del catálogo + competencia sintética
#    + inventario/lotes/alertas de demo + jobs derivados + dashboards 009
python -m scripts.preparar_demo
```

`scripts.enriquecer_catalogo` (paso 2 de `preparar_demo`, también ejecutable
suelto) rellena de forma determinista lo que el dataset Dunnhumby no trae:
`nombre`/`marca` de producto, `costo`/`precio_base` sintéticos por categoría con
margen variado (y normaliza a CLP los precios reales que venían en USD), 8
proveedores genéricos, `codigo_lote_proveedor` y vencimientos de lotes frescos
relativos a hoy.

`scripts.enriquecer_crm` (paso 2b) hace lo mismo para el CRM: identidad chilena
sintética de los clientes (nombre + RUT + email + teléfono + fecha de nacimiento)
y `cliente_clv` calculado sobre todo el histórico de ventas (el job real usa una
ventana de 180 días que, con ventas de 2017, queda vacía).

`preparar_demo` deja una cuenta por rol RBAC (`demo.gerente`, `demo.ti`,
`demo.comercial`, `demo.marketing`, `demo.operaciones`, `demo.finanzas`, `demo.rrhh`,
`demo.encargado`, `demo.reponedor`, `demo.cajero`), todas con contraseña **`Sira2026!`**.
Login en `http://localhost:5173/auth/login`. Sólo `scripts.seed_usuarios_demo`
(idempotente, `--reset-password` para re-hashear) si sólo hacen falta las cuentas.
El prefijo `demo.` evita chocar con los usernames que fabrican los fixtures de pytest
sobre la misma BD.

## Convenciones

- Capas: `router → service → repository` (Principio XI). Sin lógica de negocio en routers.
- `black` formatea, `ruff check` lintea. `pytest` para tests (BD real vía Docker, sin mocks).
- Toda credencial vía `.env` (Principio X) — nunca hardcodeada.

## Estructura

| Carpeta | Contenido |
|---|---|
| `src/core/` | config, `database.py` (sesión async), `security.py` (JWT + RBAC) |
| `src/shared/` | `repository.py` (base + paginación), `exceptions.py`, `pagination.py` |
| `src/models/` | modelos SQLAlchemy 1:1 con las tablas de la feature 001 |
| `src/modules/` | un paquete por módulo de negocio (ventas, inventario, catalogo, compras) |
| `src/integrations/` | clientes Stripe, SendGrid, Open Food Facts, reportlab+MinIO |
| `alembic/` | migraciones incrementales |
