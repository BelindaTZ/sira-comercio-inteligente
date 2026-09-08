# Specification Quality Checklist: Traslados de Stock entre Tiendas

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

## Notes — Feature nueva, agregada tras dividir el gap OT-2.4/OT-2.5

- **Origen**: OT-2.4 y OT-2.5 (`oo-objetivos-operativos.md`, OE-2 Operaciones/Compras) quedaron sin feature dueña desde el cierre de 006, señalado en su momento a nivel informativo. Al retomarlo antes de arrancar el batch de artefactos de 007-011, el usuario decidió dividirlos: OT-2.4 (límites de stock máximo) se incorporó como extensión mínima de 001 (Ronda 9, reutiliza `alertas_inventario`); OT-2.5 (coordinación entre tiendas/traslados), por ser un flujo propio con su propio ciclo de vida, se especifica aquí como feature nueva.
- **Alcance deliberadamente acotado**: 3 User Stories, una por cada capa del flujo (consultar → solicitar/aprobar → recibir), sin ninguna tabla nueva — usa `traslados_stock`, ya reservada en el módulo Inventario del DDL desde el diseño original pero sin ningún consumidor hasta ahora.
- **Sin gap de rol RBAC**: se verificó que `Jefe_Operaciones` y `Encargado_Tienda` ya están seedeados — no reaplica el patrón de "convertir en job automático por falta de rol" usado en 002/003/004/009/010.
- **Sin dependencia de 009/010**: es registro operativo directo sobre PostgreSQL, mismo patrón que 001-008 y 011 — no queda "en espera".
- **Boundary explícito con 001**: reutiliza `productos`/`inventario`/`lotes` sin duplicar modelos (Principio VIII); el movimiento de stock usa el mecanismo ya existente de `movimientos_inventario` con un tipo nuevo, no una tabla paralela. Se documentó explícitamente que esta feature no interactúa con la alerta de stock máximo de 001 (Ronda 9) — son mecanismos independientes.
- No se detectaron violaciones de principios de la constitución.

## Ronda 1 (post-implementación — alineación de convenciones reales del proyecto)

`plan.md` planteó, antes de implementar, tres cosas que no coinciden con las convenciones ya fijadas por 001-011: módulo backend anidado `modules/operaciones/traslados/` (el resto del proyecto usa módulos planos, `modules/<feature>/`), un store Pinia en TypeScript `frontend/src/stores/traslados.ts` (el proyecto no usa Pinia stores ni `.ts` en ningún otro módulo — solo `services/<feature>Api.js` + estado local en componentes Vue) y un base path nominal `/api/v1/operaciones` con error `{"detail": "..."}` (el proyecto real usa `/api/<módulo>` sin versión de API y `{"error": {"code","message","details"?}}`, fijado desde 001). La implementación siguió correctamente las convenciones reales en los tres casos — sin esto ser una decisión nueva, es simplemente lo que ya regía desde 001. Se corrigieron `plan.md`, `contracts/traslados-stock-entre-tiendas.md`, `quickstart.md` y las tareas T002/T004/T017/T029/T040 de `tasks.md` para reflejar las rutas y archivos reales (`backend/src/modules/traslados/`, `frontend/src/services/trasladosApi.js`, `/api/traslados/...` y `/api/compras/sugerencias`), sin cambio de alcance ni de FR.
