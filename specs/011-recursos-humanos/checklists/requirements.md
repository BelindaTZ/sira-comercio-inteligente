# Specification Quality Checklist: Recursos Humanos

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

## Notes — Feature nueva, agregada tras hallazgo en 008

- **Origen**: al especificar `008-auth-administracion-sistema` se detectó que OE-8 (RRHH) — OT-8.1 a OT-8.4, 8 OO, 4 tablas ya reservadas en el modelo de datos desde el diseño inicial (`capacitaciones`, `empleado_capacitacion`, `clima_laboral`, `plan_sucesion`) — no tenía ninguna feature dueña en el roadmap original de 10 features. Se documentó como hallazgo pendiente en `spec.md`/checklist de 008 y en `spec.md` de 009 (KPI de clima/rotación mostrado como "no disponible"). El usuario confirmó explícitamente crear esta feature 011 para cerrar el vacío, pidiendo mantenerla "lo justo y necesario" — sin ampliar el alcance más allá de las 4 OT ya definidas en el BSC.
- **Alcance deliberadamente acotado**: 4 User Stories, una por cada OT de OE-8, sin ninguna tabla nueva más allá de las 4 ya reservadas — se verificó que las 8 OO de OE-8 (`oo-objetivos-operativos.md`) caben completas en las tablas ya existentes, sin necesidad de expandir el modelo de datos de 50 tablas.
- **Sin gap de rol RBAC**: se verificó en `01_operativo_postgres.sql` que `Jefe_RRHH` y `Encargado_Tienda` ya están seedeados como roles — a diferencia de 002/003/004/009/010, esta feature no reaplica el patrón de "convertir en job automático por falta de rol". Es la primera feature de este proyecto sin ningún gap de RBAC que resolver.
- **Columna aditiva pendiente de diseño (no gap de BSC)**: `roles_puesto` no trae hoy una marca de "puesto crítico" (necesaria para OT-8.1 y como precondición de OT-8.4) — se deja documentado en Assumptions como columna aditiva a definir en `data-model.md`, mismo patrón ya usado en 007 (columna de duración de cobro). No es una inconsistencia del BSC, es un detalle de modelo de datos normal de la fase de planificación.
- **Sin dependencia de 009/010**: se verificó que ninguna de las 4 OT de OE-8 requiere el warehouse ni la plataforma ELT — es registro operativo directo sobre PostgreSQL (mismo patrón que 001-008), por lo que esta feature NO queda "en espera" como 009/010.
- **Tasa de rotación por consulta, no por tabla nueva**: se verificó que `empleados.fecha_baja` (existente desde 001) alcanza para calcular la tasa de rotación por tienda/periodo que pide OO-8.3.2, evitando duplicar el dato en una tabla nueva (Principio VIII).
- No se detectaron violaciones de principios de la constitución.
- **Reconciliación aplicada en la implementación (T034)**: `contracts/recursos-humanos.md` (versión original) listaba `Encargado_Tienda` como RBAC válido para `PATCH .../completar`, mientras que `data-model.md` (Extensión RBAC) y `research.md` (Decisión 5) le conceden acceso de **solo lectura** al módulo `RRHH`. Se resolvió a favor de `data-model.md`/`research.md` (fuente de verdad del RBAC y patrón de las features 005/007): el `Jefe_RRHH` registra la fecha de finalización (FR-004, sin actor explícito en el FR) y el `Encargado_Tienda` verifica el cumplimiento de su personal por el `GET .../cumplimiento-capacitacion` (FR-005, "consultar"). El contrato quedó actualizado para reflejarlo. La redacción del Acceptance Scenario US2.1 ("el Encargado de Tienda puede confirmar el cumplimiento") se interpreta como esa verificación de solo lectura.
