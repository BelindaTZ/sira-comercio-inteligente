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
