# Specification Quality Checklist: Promociones Inteligentes

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-06
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- Validación ejecutada releyendo `constitution.md` completa (12 principios) y `domain-context.md` (OE-3 completo: OT-3.5/OT-3.6; y el gap detectado en OE-2: OT-2.2/OT-2.3) antes de redactar.
- Se investigó el límite exacto con 002-clientes-fidelizacion: su propio spec.md ya documentaba explícitamente en Assumptions que "el motor de recomendaciones por afinidad de compra/cross-sell (OT-3.5) pertenece a la feature 005-promociones-inteligentes, junto con la colocación de producto en anaquel/mailer" — esta feature no reconstruye nada de 002 (OT-3.6, cupones por hito, ya cerrado ahí), solo reutiliza su infraestructura de campañas/cupones para un nuevo tipo de cupón (afinidad).
- **Gap de BSC incorporado — nueva OO-3.5.3**: ni `bsc-objetivos-estrategicos-tacticos.md` ni `oo-objetivos-operativos.md` tenían un Objetivo Operativo para el escenario narrado explícitamente en el enunciado original ("cuajada se hace siempre de cerveza sin alcohol y le mandan un descuento al móvil para que vaya a recogerla") — solo existían OO-3.5.1 (revisar reglas, mensual) y OO-3.5.2 (mostrar en punto de venta, diario), ninguno cubre un envío proactivo al cliente fuera de la tienda. Se agregó **OO-3.5.3 (Sistema): Enviar cupón de descuento personalizado cuando se detecta una oportunidad de afinidad no aprovechada — por evento**, bajo el OT-3.5 ya existente (sin crear un OT nuevo, a diferencia del precedente de OT-6.5 en la feature 001 que sí requirió un OT nuevo). Documentado en el spec (Assumptions) y pendiente de reflejar en `bsc-objetivos-estrategicos-tacticos.md`/`oo-objetivos-operativos.md` del proyecto una vez el usuario apruebe este spec.
- **Gap de feature dueña incorporado — OT-2.2 (clasificación ABC) y OT-2.3 (liquidación de categoría C)**: ambos OT existen desde el BSC inicial y el campo `clasificacion_abc` ya está reservado en `productos` desde 001 (`01_operativo_postgres.sql`), pero ninguna feature especificada hasta ahora (001-004) los tomó como propios — se verificó con grep sobre los 4 spec.md ya cerrados, sin resultado. Se asignan a 005 porque OO-2.3.2 describe literalmente la acción como "ejecutar liquidación/**promoción** local" — coincide directamente con el propósito de esta feature. Se decidió explícitamente dejar **fuera** de 005 a OT-2.4 (límites de stock máximo) y OT-2.5 (coordinación de stock entre tiendas): no son mecanismos de promoción sino de capacidad de almacenamiento y logística, y quedan como gap sin feature dueña, pendiente de una decisión del usuario en una futura ronda.
- Se detectó el mismo patrón de gap de rol RBAC que en 002/003/004 (OO-2.2.1 asigna la ejecución de la clasificación ABC a un actor "Analista de Operaciones" sin rol sembrado en el esquema — solo existen los 10 roles ya confirmados, sin ese rol). Resuelto igual que en 004: se convierte en job automático del sistema, dejando a Jefe_Operaciones como actor humano real vía OO-2.2.2 (ya existente: "revisar productos que cambiaron de categoría").
- Se verificó el límite con 003-precios-margenes para evitar que dos mecanismos independientes bajen el precio del mismo producto a la vez: un producto con una propuesta de ajuste de precio de 003 pendiente de aprobación no se ofrece como candidato a liquidación de categoría C (FR-013 / Edge Case).
- Se confirmó que `display_locations`, `mailer_locations` y `promociones` ya existen en el esquema (sembradas del dataset Dunnhumby, causal_data.csv) sin que ninguna feature las haya llenado hasta ahora — 004 solo las lee como variable exógena del pronóstico; esta feature es la que las crea/gestiona (User Story 4). No se duplica ninguna tabla entre 004 y 005.
- No se detectaron violaciones de principios de la constitución. La elección de algoritmo para las reglas de asociación (p. ej. Apriori/FP-Growth) se deja para `research.md`, no se fija en el spec (Principio VIII).


## Ronda 2 (corrección de FR-009 / User Story 3 — clasificación ABC es de catálogo, no por tienda)

Al diseñar `data-model.md` se detectó una inconsistencia entre el spec.md original y el esquema ya existente: el campo `clasificacion_abc` vive como columna simple en `productos` (sin dimensión de tienda) desde la feature 001, pero el spec.md redactado inicialmente describía la clasificación mensual como "por producto y tienda" (FR-009, Acceptance Scenario 1 de User Story 3) — lo que hubiera exigido una tabla nueva producto×tienda no prevista ni necesaria, y no coincide con la redacción de OO-2.2.1 ("clasificar el catálogo", sin mención de tienda). Se corrigió FR-009 y el Acceptance Scenario 1 de User Story 3 para que la clasificación ABC sea de catálogo/red (coincide con el esquema ya construido); la evaluación de rotación **local** por tienda se mantiene, pero solo en el paso de generación de candidatos a liquidación (Acceptance Scenario 2, FR-012), que no requiere persistir una clasificación ABC separada por tienda — solo compara la rotación reciente de esa tienda contra el umbral configurado.

## Ronda 3 (implementación — `/speckit-implement` + `/speckit-analyze` post-hoc)

- Feature implementada de punta a punta: módulo `backend/src/modules/promociones/` (router/service/repository/schemas + `analytics/afinidad.py` con `mlxtend`, `analytics/clasificacion_abc.py`), 4 tablas nuevas (`regla_afinidad`, `candidato_liquidacion`, `configuracion_promociones`, `cambio_clasificacion_abc`) + extensión aditiva de `campanas` (valor `afinidad`) y `cupon_enviado` (`regla_afinidad_id`), migración `0012` idempotente + RBAC (Marketing_CRM / Operaciones / Ventas). 3 jobs `APScheduler` (`calcular_afinidad_mensual`, `clasificar_abc_mensual`, `candidatos_liquidacion_semanal`) con endpoints dev de forzar corrida. Extensión puntual de `modules/ventas` (hook best-effort al confirmar una venta: dispara el cupón de afinidad, Principio II). Frontend: `modules/promociones/` (ReglasAfinidadPage, LiquidacionPage, ColocacionPromocionalPage), `promocionesApi.js`, banner de cross-sell en `TicketVenta.vue`.
- Dependencia nueva: `mlxtend` (Apriori + `association_rules`), agregada a `pyproject.toml`. Reutiliza `pandas` de 004.
- Cobertura de tests: 253 backend (226 previos + 27 nuevos). Principio X cubierto: `test_reglas_afinidad` (filtrado por soporte/confianza + regla de mayor confianza), `test_clasificacion_abc` (Pareto por valor de venta + exclusión por precio pendiente), `test_us2_cupon_afinidad` (anti-duplicado dentro de la ventana de vigencia). Los 6 escenarios de `quickstart.md` cubiertos por `test_us1_afinidad` … `test_us4_colocacion`.
- `/speckit-analyze` (post-hoc): 0 issues CRITICAL/HIGH; 16/16 FR con tarea; SC-001..SC-005 cubiertos. Hallazgos LOW: (a) `data-model.md §6` decía "sin tabla nueva" para ABC — se agregó `cambio_clasificacion_abc` como bitácora (NO la clasificación en sí, que sigue en `productos.clasificacion_abc` sin dimensión de tienda) para poder devolver `clasificacion_anterior`/`clasificacion_nueva` que exige el contrato de `GET /clasificacion-abc` y FR-010; no es la tabla producto×tienda que la Ronda 2 rechazó. (b) T024 pedía "extender ClientesService" — el envío del cupón de afinidad se implementó en PromocionesService reutilizando las mismas tablas de cupón de 002 y sendgrid_client, evitando acoplar dos repos.
