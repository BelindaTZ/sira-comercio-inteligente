# Specification Quality Checklist: Clientes y Fidelización (CLV, Churn, Campañas por Hitos)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-05
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

- Validación ejecutada en una sola iteración, releyendo `constitution.md` completa (12 principios) y `domain-context.md` (OE-3, OT-3.1 a 3.4 y 3.6, OO-B.1 a B.3) antes de redactar.
- Alcance acotado explícitamente contra otras features ya definidas: el motor de recomendaciones/cross-sell (OT-3.5) y la colocación de producto (display/mailer) quedan en 005-promociones-inteligentes, no aquí — evita solapamiento entre specs (Principio VI, features autocontenidas).
- Se verificó contra el enunciado original: el punto de "cupón de cumpleaños" (FR-012/013), "cliente fiel que se va sin darse cuenta" (FR-009/010, ciclo individual no umbral fijo de 30 días) y "descuento de reactivación que puede traer a quien iba a volver igual" (FR-016 a FR-019, grupo de control + uplift real) están cubiertos explícitamente, no de forma implícita.
- Se documentó como Assumption, no como gap, que la fórmula exacta de ponderación del CLV es una decisión de research.md — el requisito duro de esta spec es que nunca sea gasto bruto puro (FR-005), consistente con el mismo patrón usado en 001 para el punto de reposición dinámico.
- No se detectaron violaciones de principios de la constitución.

## Ronda 2 (post-revisión del usuario)

- Se agregó captura explícita de consentimiento de tratamiento de datos (LOPDP) al alta de cliente (FR-001), con gating explícito hacia FR-005 (CLV) y FR-009/FR-010 (churn): un cliente sin consentimiento aceptado queda con registro básico, fuera de todo perfilado o campaña segmentada.
- Se agregó nivel de severidad de riesgo de fuga (en_riesgo / inactivo) a FR-010, con los umbrales exactos deferidos a `research.md`/`plan.md` (mismo patrón que la fórmula de CLV en FR-005) — la campaña de reactivación (FR-016) puede dirigirse a cualquiera de los dos niveles usando el mismo mecanismo de grupo de control/uplift ya definido, sin duplicar lógica.
- Se documentó el grandfathering de los clientes sembrados desde el dataset base (consentimiento por defecto true) como Assumption, evitando romper retroactivamente los cálculos de CLV/churn sobre datos históricos usados para pruebas.
- Se aplicó la DDL correspondiente en `01_operativo_postgres.sql`: `clientes.consentimiento_datos` + `fecha_consentimiento_datos`, `churn_score.severidad`.
- No se detectaron violaciones de principios de la constitución en esta ronda.

## Ronda 3 (contracts.md / quickstart.md)

- Se detectó que `domain-context.md` (OO-3.4.2) asignaba el cálculo de uplift a un actor "Analista de Marketing" sin rol RBAC propio sembrado en `01_operativo_postgres.sql`. Confirmado con el usuario: se resuelve sin agregar un rol nuevo — `Jefe_Marketing` ejecuta también esa acción (Principio VIII). `domain-context.md`, `spec.md` (Assumptions) y `contracts/clientes.md` ya quedaron sincronizados.
- `contracts/clientes.md` y `quickstart.md` completados sin otros gaps nuevos; el gap de "envío de cupón no registrado" ya se había resuelto en `data-model.md` (tabla `cupon_enviado`).

## Ronda 4 (checklist de privacidad)

- Se agregó `checklists/privacy.md` (dominio de riesgo específico de esta feature, mismo criterio que `security.md` en 001) y se encontró un gap real: el spec no permitía revocar el consentimiento de datos sin darse de baja por completo.
- Corregido: `FR-002` ahora incluye `consentimiento_datos` como campo editable vía `PATCH`, con el mismo gating de FR-001 aplicado hacia adelante — sin anonimizar el resto del perfil. Sincronizado en `spec.md`, `contracts/clientes.md`, `data-model.md` y `tasks.md`.
- No se detectaron más gaps en esta ronda.

## Ronda 5 (post-inicio de implementación — identificación por cédula en punto de venta)

- **Origen**: pregunta directa del usuario, tras completar Fases 1-2, antes de implementar User Story 1: cómo se identifica a un cliente afiliado en caja, dado que el spec original solo captura nombre/email/fecha de nacimiento (sin cédula), a diferencia de un programa de fidelización real en Ecuador.
- Agregado: `documento_identidad` opcional (único cuando se proporciona) en `FR-001`, un acceptance scenario nuevo en User Story 1, SC-008. `data-model.md`, `contracts/clientes.md` (POST/PATCH/GET) y `research.md` (decisión #6) actualizados.
- **Hallazgo adicional en la misma revisión**: `PuntoDeVentaPage.vue` (001, ya implementada y cerrada) nunca construyó un buscador de cliente — FR-008 de 001 dejó `household_id?` opcional desde el inicio, pero la UI dependía de la búsqueda que provee 002. Se agregó `T053` para construirla ahora, desde 002, sin reabrir el spec de 001.
- `tasks.md`: `T052` (migración), `T051`/`T053` (búsqueda/UI) nuevas; `T007`, `T012`, `T013`, `T016`, `T017` extendidas. No se detectaron violaciones de principios: `documento_identidad` sigue el mismo patrón ya usado en el proyecto para campos opcionales-pero-únicos (índice único parcial), y `email` se mantiene como clave de registro (decisión del usuario).

## Ronda 6 (Fase 8 — `/speckit-analyze` + polish, post-implementación US1-US5)

- **Origen**: T047 (`/speckit-analyze` sobre `spec.md`/`plan.md`/`tasks.md`) tras completar la implementación de las 5 historias de usuario (152 tests backend verdes, build de frontend limpio).
- **Resultado del análisis**: **0 issues CRITICAL/HIGH**, 0 violaciones de constitución, cobertura de FR **19/19** y de SC **8/8**. Hallazgos MEDIUM/LOW, de consistencia documental:
  - **C1 (MEDIUM) — resuelto**: FR-004 (datos demográficos opcionales) estaba implementado (`DatosDemograficosIn`, `ClientesService._upsert_demografico`) y probado en el alta (`test_alta_con_datos_demograficos`), pero sin traza explícita en `tasks.md` ni test de PATCH. Se agregó `test_patch_agrega_datos_demograficos` (contrato T008) y se anotó FR-004 en T007/T008 y en las notas de Fase 3.
  - **I1 (MEDIUM) — resuelto**: `plan.md` (Summary + Technical Context/Storage) decía "2 cambios aditivos" cuando el esquema final incluye las rondas 1-2 (diseño) más 5-7 (implementación). Se reescribió para remitir a `data-model.md` / `01_operativo_postgres.sql` como fuente canónica y enumerar las extensiones reales (todas aditivas, Principio VIII; migraciones `0006`-`0009` idempotentes).
  - **I2/I3/I4 (LOW)**: desviaciones ya documentadas en las notas de cada fase — jobs consolidados en la capa de servicio (`calcular_clv_churn_job.py` + `eventos_hito_job.py` en vez de 4 archivos), servicio/repo de campañas en archivos propios (`campanas_service.py`/`campanas_repository.py`), páginas de frontend directamente en `modules/clientes/` (sin subcarpeta `pages/`), tests de componente de frontend fuera de alcance (Principio X sólo exige la cobertura de cálculo del backend). Sin acción — coherentes con el criterio ya aplicado en 001.
  - **A1/D1/E1/U1 (LOW)**: SC-001 vs cadencia del job semanal (tolerancia aceptada), numeración de escenarios de US1, `GET /{household_id}/eventos` sin tarea propia (implementado junto a T037). Sin acción.
- **T048 — 7 escenarios de `quickstart.md` de punta a punta**: cubiertos por tests de integración reales (`httpx.AsyncClient` + PostgreSQL), todos verdes:
  - Esc. 1-2 → `test_us1_perfil_cliente.py` · Esc. 3 → `test_us2_clv.py` · Esc. 4 → `test_us3_churn.py`
  - Esc. 5 → `test_us4_cupon_hito.py` · Esc. 6 → `test_clientes_busqueda_documento.py` + `BuscadorCliente.vue` · Esc. 7 → `test_us5_reactivacion.py`
- **T049 — cobertura de Principio X** (verificada, completa):
  - Cálculo de CLV compuesto → `tests/unit/test_calculo_clv.py` (empate frecuente/margen-bajo vs único/margen-alto: nunca ordena por gasto bruto).
  - Ciclo de compra individual + severidad → `tests/unit/test_calculo_churn.py` (mismo `dias_desde_ultima` da veredicto distinto según el ciclo propio: nunca umbral fijo).
  - Gating de consentimiento → `tests/unit/test_gating_consentimiento.py` + confirmación end-to-end en `test_us1` (esc. 1) y `test_campana_reactivacion` (miembro sin consentimiento → 422).
  - Extra: `test_seleccion_cupon_hito.py` (producto ancla) y `test_calculo_uplift.py` (uplift = retorno tratado − control, nunca redención).
- No se detectaron violaciones de principios de la constitución en esta ronda.
