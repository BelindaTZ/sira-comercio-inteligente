# Implementation Plan: Core de Ventas e Inventario (Punto de Venta, Catálogo y Reposición)

**Branch**: `001-core-ventas-inventario` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-core-ventas-inventario/spec.md`

## Summary

Núcleo transaccional operativo de SIRA: registro de venta en punto de venta con cobro (efectivo, tarjeta vía Stripe modo prueba, transferencia, billetera), gestión de inventario por lotes bajo FIFO, alertas de reposición y de vencimiento, detección de quiebre de stock, sugerencia y aprobación de órdenes de compra (incluyendo frecuencia pactada por proveedor y pedidos especiales), catálogo de productos, y devoluciones. Enfoque técnico: API REST en FastAPI sobre el esquema PostgreSQL ya validado (extendido con 7 cambios aditivos para esta feature — ver `data-model.md`), consumida por una SPA en Vue 3. Toda regla de negocio (FIFO, punto de reposición, validación de stock, separación cajero/datáfono) vive en el backend; el frontend solo presenta y consume la API.

## Technical Context

**Language/Version**: Backend: Python 3.11+. Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic (migraciones sobre `01_operativo_postgres.sql`), PyJWT, `stripe` (SDK oficial, modo test), `reportlab` (PDF), `sendgrid` (pedidos especiales por correo). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, `vue-echarts` (no se usa en esta feature en particular, pero es parte del stack fijo), Axios.

**Storage**: PostgreSQL 16 — esquema operativo `01_operativo_postgres.sql` más la extensión aditiva de esta feature (`alertas_inventario`, `eventos_quiebre_stock`, `lineas_venta_removidas`, `intentos_pago_tarjeta`, columnas nuevas en `proveedores`/`ordenes_compra`/`devoluciones`/`ventas`). MinIO bucket `producto-imagenes` para imágenes de producto (Principio III).

**Testing**: Backend: `pytest` + `httpx` (contract e integración contra la API), `pytest-asyncio`. Frontend: `Vitest` + `@vue/test-utils`. Por Principio X, cobertura obligatoria en: cálculo de FIFO por lote, cálculo del punto de reposición dinámico, cálculo de totales/descuentos de venta, y verificación de RBAC en cada endpoint.

**Target Platform**: Aplicación web (API + SPA). Entorno de desarrollo/demo local orquestado con Docker Desktop (PostgreSQL, MinIO, backend, frontend) — ClickHouse/Airflow quedan fuera del alcance de esta feature (capa táctica/estratégica en pausa, Principio III).

**Project Type**: web (backend + frontend detectados en la estructura del repo).

**Performance Goals**: CRUD estándar <1s en desarrollo (Principio X). SC-001: venta de 10 productos escaneados <90s. SC-002: descuento de inventario reflejado <5s tras confirmar. SC-008: resultado de cobro con tarjeta <5s tras la simulación visual.

**Constraints**: Sin lógica de negocio en el frontend (Principio V). RBAC (rol→módulo→tabla) verificado en cada endpoint contra el esquema ya existente (Principio IV). Credenciales solo vía `.env`, JWT + RBAC en cada request (Principio X). El cajero nunca debe capturar ni ver datos de tarjeta (FR-003) — el paso de cobro con tarjeta es un componente de frontend separado del formulario de venta.

**Scale/Scope**: ~92,331 productos sembrados (catálogo completo desde la carga inicial), 5 historias de usuario (P1-P5), 31 requisitos funcionales, operación multi-tienda (cada tienda gestiona su propio stock, Principio de independencia por sucursal documentado en Assumptions del spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR-00N del spec cita su OO/OT de origen; el plan no introduce funcionalidad sin ese respaldo. |
| II. Nivel Operativo = Registro Real | PASS | La venta persiste en PostgreSQL desde que se agrega la primera línea (`ventas.estado = 'en_curso'`), no como estado en memoria/sesión; toda acción (venta, ajuste, merma, remoción de línea, intento de pago) es un INSERT/UPDATE real. |
| III. Separación de Motores | PASS | Esta feature opera exclusivamente sobre PostgreSQL (OLTP) y el bucket MinIO `producto-imagenes`; no toca ClickHouse ni Airflow. |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Cada endpoint valida contra `role_permisos_modulo`/`role_permisos_tabla` ya existentes. El middleware de autenticación JWT en sí lo entrega la feature 008; 001 consume ese contrato (ver Assumptions del spec) sin bloquear su propio desarrollo (se usa un JWT de prueba mientras 008 no esté implementada). |
| V. Backend y Frontend Desacoplados | PASS | FastAPI expone solo REST/JSON; Vue consume vía capa de servicios centralizada (Principio XI). |
| VI. Features Autocontenidas | PASS | Este plan referencia `domain-context.md` y `01_operativo_postgres.sql`, no los redefine. |
| VII. Anclaje al Dataset Real | PASS | El catálogo de productos, ventas históricas y clientes provienen del dataset Dunnhumby ya sembrado; los únicos datos sintetizados (código de barras, imagen placeholder, medio de pago) ya estaban documentados como tales antes de este plan. |
| VIII. Simplicidad Justificada | PASS | Los 7 cambios de esquema de esta feature son aditivos y cada uno traza a un FR concreto (ver comentarios en `01_operativo_postgres.sql`); no se introduce ningún motor, microservicio o dependencia fuera del stack ya fijado en la constitución. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar tasks.md; ningún documento previo se sobrescribió sin aprobación. |
| X. Calidad, Testing y Seguridad | PASS | Ver sección Testing arriba; JWT+RBAC en cada endpoint; secretos solo vía `.env`. |
| XI. Convenciones de Código | PASS | Ver Project Structure: capas router→service→repository en backend, composables + capa de servicios en frontend. |
| XII. Usabilidad y Diseño de Interfaz | PASS | Los listados (ventas, inventario, alertas, órdenes de compra) usan filtros reactivos y paginación; el punto de venta y demás pantallas siguen `design-system.md` y la navegación horizontal con mega-menú ya definidos. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-core-ventas-inventario/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

**Criterio de organización**: por **módulo de negocio** (el mismo criterio que ya usa el RBAC de `01_operativo_postgres.sql` — Direccion, Comercial, Marketing_CRM, Operaciones, Ventas, Finanzas, TI, RRHH, Sistema), no por número de feature de Spec Kit. Se decidió así porque `domain-context.md` ya deja explícito que ninguna de las 9 features mapea 1 a 1 con un módulo — organizar por feature hubiera duplicado modelos compartidos (`Producto`, `Venta`, etc.) en varias carpetas, violando DRY (Principio VIII). La trazabilidad a la feature no se pierde: cada tarea de `tasks.md` referencia el archivo exacto dentro de `modules/` y el FR que resuelve.

```text
backend/
├── src/
│   ├── main.py                      # entrypoint FastAPI
│   ├── core/                        # config, seguridad (JWT), sesión de BD, dependencia de RBAC reutilizable
│   ├── shared/                      # reutilizable entre módulos: repositorio base, paginación, respuestas/excepciones estándar
│   ├── models/                      # modelos SQLAlchemy, uno por tabla de 01_operativo_postgres.sql (fuente única, sin duplicar por módulo)
│   ├── modules/
│   │   ├── ventas/                  # router.py, service.py, repository.py, schemas.py — venta, cobro, devolución, anulación, remoción de línea
│   │   ├── inventario/              # lotes, FEFO, ajustes, mermas, alertas de inventario, eventos de quiebre, stock máximo por categoría (Ronda 9)
│   │   ├── catalogo/                # productos (consumido también por 003/004/005 vía models/, no por import cruzado entre módulos)
│   │   ├── compras/                 # proveedores, órdenes de compra (programadas y especiales)
│   │   ├── clientes/                # feature 002 (a futuro)
│   │   ├── pricing/                 # feature 003 (a futuro)
│   │   ├── forecasting/             # feature 004 (a futuro)
│   │   ├── promociones/             # feature 005 (a futuro)
│   │   ├── caja/                    # feature 006 (a futuro)
│   │   ├── pagos/                   # feature 007 (a futuro)
│   │   ├── auth/                    # feature 008 (a futuro)
│   │   ├── dashboards/              # feature 009 (en espera)
│   │   ├── rrhh/                    # feature 011 (nueva, agregada tras hallazgo de gap OE-8 en 008 — sin dependencia de 009/010)
│   │   └── traslados/               # feature 012 (nueva, OT-2.5, coordinación de stock entre tiendas — usa traslados_stock, reservada desde el diseño original)
│   └── integrations/                # stripe_client.py, sendgrid_client.py, openfoodfacts_client.py, reportlab_invoice.py
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # fifo_fefo, cálculo de punto de reposición, cálculo de totales

frontend/
├── src/
│   ├── core/                        # composables reutilizables entre módulos: usePaginacion, useFiltrosReactivos
│   ├── shared/                      # componentes genéricos reutilizables: DataTable.vue, WorkPanel.vue (Principio XII, una sola implementación)
│   ├── services/                    # capa centralizada de llamadas a la API (Principio XI): ventasApi.js, inventarioApi.js, catalogoApi.js, comprasApi.js
│   ├── modules/
│   │   ├── pos/                     # pages/PuntoDeVentaPage.vue, components/TicketVenta.vue, BuscadorProducto.vue, SimuladorDatafono.vue
│   │   ├── inventario/              # pages/InventarioPage.vue, components/TablaLotes.vue, FormularioAjuste.vue, FormularioMerma.vue
│   │   ├── catalogo/                # pages/CatalogoPage.vue, components/FormularioProducto.vue
│   │   ├── compras/                 # pages/ComprasPage.vue, components/TablaAlertas.vue, FormularioOrdenCompra.vue
│   │   └── ... (clientes/, pricing/, promociones/, caja/, pagos/, auth/, dashboards/, rrhh/, traslados/ — a futuro, mismo patrón)
│   ├── assets/
│   │   └── animations/              # pago-exitoso.mp4, pago-rechazado.mp4, pago-error.mp4 (ya en el repo)
│   └── router/
└── tests/
    ├── unit/                        # composables, formateo de totales
    └── component/                   # TicketVenta, SimuladorDatafono
```

**Structure Decision**: Aplicación web con `backend/` y `frontend/` como raíces separadas (Principio V). Dentro de cada una, el código se agrupa por **módulo de negocio** en `modules/` (arquitectura por capas dentro de cada módulo — router → service → repository en backend, componentes + composables en frontend, Principio XI), con `core/`/`shared/` para lo transversal y `models/`/`services/` (API) como fuente única de verdad, evitando duplicar entidades compartidas entre features.

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
