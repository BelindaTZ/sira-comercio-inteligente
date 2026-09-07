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
