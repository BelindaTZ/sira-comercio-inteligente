# Specification Quality Checklist: Pagos y Seguridad

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

- Validación ejecutada releyendo `constitution.md` completa (12 principios) y `domain-context.md` (OT-4.1 y OT-4.2 completos bajo OE-4, y OT-6.1 a OT-6.5 de OE-6 ya cerrados por 006) antes de redactar.
- **Investigación de alcance**: `domain-context.md` §8 no tenía ninguna línea explícita describiendo el alcance de "007-pagos-seguridad" (a diferencia de 006, que sí tenía una línea textual) — se determinó por descarte: OT-6.1 a OT-6.5 (OE-6) ya cerrados por 001/006; la memoria del proyecto confirma que Stripe/la simulación de pasarela ya se implementó en 001, no en esta feature; el único OT sin dueña que encajaba literalmente en "medios de pago" era OT-4.1 (OE-4), verificado por grep sin resultado en los 6 spec.md ya cerrados.
- **Hallazgo importante durante la investigación**: el `data-model.md` de 001 cita `OO-4.1.1` como ya cubierto (junto a FR-003/FR-030, la separación cajero/datáfono al cobrar) — pero el texto literal de OO-4.1.1 es "(Encargado de Tienda): Verificar que los datáfonos estén operativos — diario", una acción operativa diaria que 001 nunca implementó (solo citó el OT/OO como justificación de diseño de la separación de responsabilidades entre cajero y datáfono, no como la acción de verificación en sí). Es una decisión propia, no confirmada previamente con el usuario, justificada por el texto literal del OO y documentada aquí para que quede visible antes de la aprobación de este spec.
- **Gap de BSC incorporado — nueva OO-6.3.3**: ni `bsc-objetivos-estrategicos-tacticos.md` ni `oo-objetivos-operativos.md` tenían un Objetivo Operativo que produjera el KPI secundario de OE-6 ("Incidentes de seguridad de pago") — 006 solo registra incidentes de **fraude interno** (siempre con un empleado involucrado, tabla `incidentes_fraude`), no incidentes de seguridad de pago propiamente dichos (ej. sospecha de clonación de tarjeta por un datáfono comprometido, que no necesariamente implica a un empleado). Se agrega **OO-6.3.3 (Jefe de TI): Registrar y dar seguimiento a un incidente de seguridad de pago — por evento**, bajo el OT-6.3 ya existente (mismo patrón que OO-3.5.3 en 005: sin OT nuevo). Pendiente de reflejar en los documentos del BSC del proyecto una vez el usuario apruebe este spec.
- **Ronda 1 (ampliación de alcance a pedido del usuario) — OT-4.2 incorporado**: la primera versión de este spec dejaba OT-4.2 (reducir tiempo de cobro 20%) explícitamente fuera, como gap sin feature dueña (mismo tratamiento que OT-2.4/OT-2.5). El usuario pidió expresamente incorporarlo a esta feature en vez de dejarlo pendiente, razonando que comparte con OT-4.1 la naturaleza de "experiencia de cobro en el punto de venta" (misma OE-4). Se agregó la User Story 5 (P5) y FR-015 a FR-018. Se determinó que OO-4.2.1 ("Cajero: registrar venta usando el flujo rápido del sistema") ya está satisfecho estructuralmente por el flujo de venta de 001 — no requiere un FR nuevo; solo OO-4.2.2/4.2.3 (medir/revisar tiempo de cobro) necesitaban requisitos nuevos. Se documentó explícitamente que el cálculo de tiempo de cobro NO aplica a las ventas ya sembradas del dataset Dunnhumby (no traen un momento de inicio distinto del de confirmación) — solo a ventas registradas en vivo desde que esta feature esté disponible, respetando el Principio VII (Anclaje al Dataset Real, no fabricar un dato que el dataset no tiene). Se excluyen también las ventas anuladas del cálculo (Edge Case, FR-018).
- **Boundary con 006 verificado por grep**: el estado de conformidad de seguridad del datáfono (`activo`/`requiere_actualizacion`, trimestral, Jefe de TI) sigue siendo de 006; esta feature reutiliza la misma columna `datafonos.estado` para agregar la disponibilidad operativa diaria (`fuera_servicio`, Encargado de Tienda) — sin tabla ni columna duplicada. Se definió explícitamente la regla de precedencia entre ambos estados como Edge Case (un datáfono fuera de servicio se re-evalúa contra el estándar de seguridad de 006 al restablecerse, antes de marcarse operativo).
- **Boundary con 001 verificado**: la selección de medio de pago (FR-002 de 001) y la simulación de pasarela (FR-003/FR-030 de 001) no se reconstruyen; esta feature solo restringe qué medios de pago están disponibles (FR-007), agrega una advertencia previa al cobro cuando el datáfono está fuera de servicio (FR-004), y agrega el registro del momento de confirmación de la venta (FR-015) — extensiones puntuales del flujo de cobro ya existente.
- **Sin gap de rol RBAC**: los actores de esta feature (Encargado_Tienda, Jefe_TI, Jefe_Finanzas, Jefe_Comercial) ya tienen rol propio sembrado en el esquema.
- **Gap identificado y dejado fuera de esta feature — OT-2.4/OT-2.5**: siguen sin feature dueña (conversado con el usuario durante 006), sin relación con "pagos y seguridad" — no se resuelven aquí.
- No se detectaron violaciones de principios de la constitución. La decisión de si el incidente de seguridad de pago requiere o no un datáfono asociado (Edge Case), y el mecanismo exacto para registrar el momento de inicio/confirmación de una venta (columna nueva vs. otro mecanismo), se dejan para `data-model.md`.
