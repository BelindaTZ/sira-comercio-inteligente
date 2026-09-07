# Implementation Plan: Clientes y Fidelización (CLV, Churn, Campañas por Hitos)

**Branch**: `002-clientes-fidelizacion` | **Date**: 2026-09-05 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-clientes-fidelizacion/spec.md`

## Summary

Maestro de cliente (alta con captura de consentimiento de tratamiento de datos, actualización, baja con anonimización real), cálculo semanal de CLV compuesto (frecuencia + margen real, nunca gasto bruto) con niveles de fidelización reclasificados automáticamente, detección de riesgo de fuga usando el ciclo de compra individual de cada cliente con dos niveles de severidad (`en_riesgo`/`inactivo`), campañas automáticas por hito (cumpleaños/aniversario) con cupón enviado por correo, y campañas de reactivación que exigen grupo de control antes del envío para medir uplift real al cierre. Enfoque técnico: API REST en FastAPI sobre el esquema PostgreSQL ya validado, extendido **sólo con cambios aditivos** (Principio VIII); la lista canónica y actualizada de esas extensiones vive en `data-model.md` y en los bloques "EXTENSIÓN — Feature 002" de `01_operativo_postgres.sql` (rondas 1-2 en el diseño inicial; rondas 5-7 agregadas durante la implementación — `documento_identidad`, `campanas.categoria_sira`, `campana_cliente.grupo`, tablas `campana_resultado`/`cupon_enviado`, secuencias, seed de niveles y RBAC — todas documentadas en Assumptions de `spec.md` y en las notas de `tasks.md`). Consumida por la SPA Vue 3 ya en curso. El cálculo de CLV/churn y el evento diario de hitos corren como jobs periódicos dentro del propio backend (no como pipeline ELT — Principio III reserva Airflow/ClickHouse para agregación táctica/estratégica en 009/010).

## Technical Context

**Language/Version**: Backend: Python 3.11+. Frontend: Node.js 20+ / Vue 3.4+.

**Primary Dependencies**: Backend: FastAPI, Pydantic v2, SQLAlchemy 2.0 (async) + asyncpg, Alembic, PyJWT, `sendgrid` (cupón de hito y notificaciones de campaña, ya aprobado y ya integrado por 001), `APScheduler` (jobs periódicos embebidos — ver research.md). Frontend: Vue 3, Vue Router, Pinia, Vite, Tailwind CSS, Axios (mismo stack fijo que 001, sin dependencias nuevas de frontend). Sin dependencias nuevas de backend más allá de `APScheduler` — la selección del producto ancla del cupón y el cálculo de uplift son lógica pura en `backend/src/shared/` (Principio VIII).

**Storage**: PostgreSQL 16 — esquema operativo `01_operativo_postgres.sql` más las extensiones **aditivas** de esta feature. La lista canónica está en `data-model.md`; a alto nivel: `clientes` (`consentimiento_datos`, `fecha_consentimiento_datos`, `documento_identidad`), `churn_score.severidad`, `campanas.categoria_sira`, `campana_cliente.grupo`, tablas nuevas `campana_resultado` y `cupon_enviado`, secuencias `campanas_campaign_id_seq`/`clientes_household_id_seq`, seed de `niveles_fidelizacion` y RBAC de `Marketing_CRM`. Migraciones Alembic `0006`-`0009` (idempotentes). No usa MinIO ni ClickHouse — feature puramente operativa (Principio III).

**Testing**: Backend: `pytest` + `pytest-asyncio` + `httpx.AsyncClient`. Frontend: `Vitest` + `@vue/test-utils`. Por Principio X, cobertura obligatoria en: cálculo del CLV compuesto (verificar que nunca colapsa a gasto bruto puro), cálculo del ciclo de compra individual y su clasificación de severidad (verificar que nunca usa un umbral fijo igual para todos los clientes), y el gating de consentimiento (un cliente sin consentimiento aceptado nunca aparece en CLV/churn/campañas).

**Target Platform**: Aplicación web (API + SPA). Docker Desktop con solo PostgreSQL para esta feature (MinIO/ClickHouse/Airflow no aplican, Principio III).

**Project Type**: web (backend + frontend, misma estructura que 001).

**Performance Goals**: CRUD estándar <1s en desarrollo (Principio X). SC-001: CLV calculado antes de fin de la semana de la primera compra (job semanal). SC-003: 100% de cupones de hito enviados el mismo día del evento (job diario).

**Constraints**: Sin lógica de negocio en el frontend (Principio V). RBAC verificado en cada endpoint (Principio IV) — 002 consume el JWT/roles de 008 con un token de prueba mientras tanto, mismo criterio ya aceptado en 001. El gating de consentimiento (FR-001) se aplica en la capa de servicio/repository, nunca en el frontend. La anonimización de baja (FR-003) es un UPDATE real que conserva `household_id` — nunca un DELETE físico ni un simple flag sin anonimizar. Una falla de SendGrid no bloquea el registro del evento/cupón (Principio II).

**Scale/Scope**: Base de clientes ya sembrada desde el dataset Dunnhumby (`household_id` existente en `clientes`/`clientes_demograficos`), 5 historias de usuario (P1-P5), 19 requisitos funcionales.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Estado | Nota |
|---|---|---|
| I. Trazabilidad al BSC | PASS | Cada FR-00N cita su OO/OT de origen (OE-3: OT-3.1 a 3.4 y 3.6; OO-B.1 a B.3). |
| II. Nivel Operativo = Registro Real | PASS | Alta/actualización/baja de cliente son INSERT/UPDATE reales; CLV y churn se guardan como historial (`cliente_clv`/`churn_score`, un registro por fecha de cálculo, nunca sobrescriben). |
| III. Separación de Motores | PASS | Esta feature opera exclusivamente sobre PostgreSQL; el cálculo de CLV/churn es agregación operativa ligera sobre datos propios, no un pipeline ELT (eso es 009/010). No toca MinIO ni ClickHouse. |
| IV. RBAC de Dos Niveles | PASS (dependencia declarada) | Igual que 001: cada endpoint valida contra `role_permisos_modulo`/`role_permisos_tabla`; la emisión real del JWT la entrega 008, se usa un token de prueba mientras tanto. |
| V. Backend y Frontend Desacoplados | PASS | FastAPI expone solo REST/JSON; Vue consume vía capa de servicios centralizada. |
| VI. Features Autocontenidas | PASS | Excluye explícitamente el motor de recomendaciones/cross-sell (OT-3.5) y la colocación de producto — quedan en 005-promociones-inteligentes (ya documentado en Assumptions del spec). |
| VII. Anclaje al Dataset Real | PASS | Clientes ya sembrados (Dunnhumby, `household_id`). El consentimiento de datos es un dato nuevo no cubierto por el dataset histórico — sintetizado con grandfathering explícito (`consentimiento_datos = true` por defecto en filas sembradas, ver `data-model.md`/Assumptions del spec). |
| VIII. Simplicidad Justificada | PASS | 2 columnas nuevas, sin tabla/motor/microservicio nuevo; el nivel de severidad reutiliza el mismo mecanismo de campaña + grupo de control ya definido para `en_riesgo`, sin duplicar lógica (DRY) para `inactivo`. |
| IX. Guardrails de IA sobre Specs | PASS | Este plan se presenta para revisión antes de generar `tasks.md`. |
| X. Calidad, Testing y Seguridad | PASS | Ver sección Testing arriba; JWT+RBAC en cada endpoint; secretos solo vía `.env`. |
| XI. Convenciones de Código | PASS | Capas router→service→repository en backend (mismo patrón que 001); el gating de consentimiento vive en la capa de servicio, no en triggers de base de datos (ver research.md). |
| XII. Usabilidad y Diseño de Interfaz | PASS | La lista de clientes en riesgo de fuga es filtrable por severidad, paginada, con el mismo panel de trabajo estandarizado ya usado en 001. |

No hay violaciones que requieran justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-clientes-fidelizacion/
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

**Criterio de organización**: el mismo ya fijado en 001 — por módulo de negocio dentro de `backend/src/modules/` y `frontend/src/modules/`, no por número de feature. `modules/clientes/` (reservado desde el `plan.md` de 001) es donde vive esta feature; no se crea ninguna carpeta nueva a nivel raíz.

```text
backend/
├── src/
│   ├── models/                      # se agregan/extienden: Cliente (+consentimiento), ClienteClv, ChurnScore (+severidad), NivelFidelizacion, Campana, Cupon, RedencionCupon, EventoCliente
│   ├── modules/
│   │   └── clientes/                # router.py, service.py, repository.py, schemas.py — perfil, CLV, churn, campañas, cupones
│   ├── jobs/                        # nuevo: scheduler.py (APScheduler), calcular_clv_churn_job.py (semanal), eventos_hito_job.py (diario) — ver research.md
│   └── integrations/                # sendgrid_client.py ya existe (creado en 001), se reutiliza sin cambios (DRY)
└── tests/
    ├── contract/                    # un test por endpoint en contracts/
    ├── integration/                 # un test por historia de usuario (P1-P5)
    └── unit/                        # cálculo de CLV compuesto, cálculo de ciclo de compra + severidad, gating de consentimiento

frontend/
├── src/
│   ├── services/                    # clientesApi.js (nuevo, mismo patrón que ventasApi.js de 001)
│   ├── modules/
│   │   └── clientes/                # pages/ClientesPage.vue, RiesgoFugaPage.vue, CampanasPage.vue; components/FormularioCliente.vue, TablaClientesRiesgo.vue (filtro por severidad), FormularioCampana.vue
└── tests/
    ├── unit/                        # composables, formateo de CLV/severidad
    └── component/                   # TablaClientesRiesgo, FormularioCampana
```

**Structure Decision**: Se reutiliza íntegramente la estructura web (`backend/`+`frontend/`) y el criterio de organización por módulo de negocio ya decididos en el `plan.md` de 001 — esta feature solo puebla `modules/clientes/` (ya reservado) y agrega `backend/src/jobs/` como carpeta nueva y transversal para los jobs periódicos (compartible a futuro por otras features que necesiten cálculo periódico sobre PostgreSQL, evitando duplicar el scheduler por módulo — Principio VIII).

## Complexity Tracking

*Sin violaciones — tabla no aplica para esta feature.*
