# Specification Quality Checklist: Caja, Mermas y Fraude

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

- Validación ejecutada releyendo `constitution.md` completa (12 principios) y `domain-context.md` §8 (línea explícita: "006 solo cubre el cuadre de caja de ventas, no las cuentas por pagar a proveedor" — OT-6.5 ya cerrada en 001) antes de redactar.
- **Boundary con 001-core-ventas-inventario verificado por grep** sobre el spec.md ya cerrado de 001: la venta y su medio de pago, el registro/validación de mermas por causa (OT-5.4) y el registro de ajustes de inventario con su diferencia calculada ya están cubiertos ahí — 001 incluso reserva explícitamente el caso de un ajuste de inventario con diferencia negativa grande como "investigación de causa/fraude pertenece a 006-caja-mermas-fraude, no a esta feature" (edge case textual de 001). Esta feature no reconstruye ninguno de esos flujos, solo los consume (FR-010) y agrega el cuadre de caja física, que 001 nunca cubrió.
- **Tablas reutilizadas sin llenar hasta ahora**: `apertura_caja`, `cierre_caja` (con columna GENERATED `diferencia` y su índice parcial `WHERE diferencia <> 0`), `datafonos` e `incidentes_fraude` ya existen en `01_operativo_postgres.sql` desde 001, reservadas sin que ninguna feature las tomara como propias hasta esta.
- **OT-5.5 asignado a esta feature**: 001 cubre OT-5.3 (rotación FIFO) y OT-5.4 (registro/validación de merma por causa) pero no OT-5.5 (umbral de merma aceptable y su seguimiento agregado) — verificado por grep sobre 001-004, sin dueño previo. Se incorpora aquí porque el propio nombre de la feature ("mermas") lo indica directamente y no encaja en ninguna feature restante (007-010 son pagos/seguridad, auth/administración y dashboards/analítica).
- **Primera feature de la serie sin gap de rol RBAC**: se verificaron los 5 actores de OT-6.1 a OT-6.4 y OT-5.5 (Cajero, Encargado_Tienda, Jefe_Finanzas, Jefe_TI, Jefe_Operaciones) contra los 10 roles ya sembrados en el esquema — a diferencia de 002, 003, 004 y 005 (cada una con su propio gap resuelto), ninguno de estos actores carece de rol propio. No se requirió ninguna resolución de gap en esta feature.
- **Escalamiento a RRHH (OO-6.2.2) modelado sin módulo operativo propio de RRHH**: OE-8 (RRHH) es estratégico/táctico en este proyecto, sin una feature operativa dueña de un flujo de tickets propio. "Escalar a RRHH" se modela como abrir un `incidentes_fraude` con el empleado identificado (visible desde el módulo Finanzas), no como un flujo de aprobación hacia un sistema de RRHH fuera del alcance del proyecto.
- **Protocolo de escalamiento (OO-6.4.1) modelado como texto de referencia versionado**, no como un motor de flujo de aprobación multi-paso — mantiene el alcance simple (Principio VIII) mientras cumple el requisito de que exista un documento consultable dentro del sistema, no solo una política verbal o externa a él.
- **Umbral de merma (OT-5.5) modelado como alerta de gestión, no como restricción dura**: superarlo nunca bloquea una venta, una recepción de mercadería ni ningún otro flujo operativo — mismo criterio ya usado para las alertas de reposición de 001 (FR-019 / Edge Case).
- Se verificó que un incidente de fraude sobre un empleado ya dado de baja no queda bloqueado ni se cierra automáticamente (FR-016 / Edge Case) — el ciclo de vida del incidente es independiente del ciclo de vida del empleado en el sistema.
- **OT-2.4 (límites de stock máximo) y OT-2.5 (coordinación de stock entre tiendas) permanecen fuera de esta feature** — no son mecanismos de caja, mermas ni fraude; siguen sin feature dueña. Tema ya conversado directamente con el usuario fuera de este documento, sin resolución tomada aún.
- No se detectaron violaciones de principios de la constitución.

## Ronda 1 (corrección de nomenclatura del módulo backend — `finanzas/` → `caja/`)

Al redactar el batch completo (plan/research/data-model/contracts/quickstart/tasks) se usó `backend/src/modules/finanzas/` como nombre del módulo nuevo, tomado por asociación directa del nombre del módulo RBAC ya sembrado (`Finanzas`, "Caja, cuadre, seguridad de pagos"). Una verificación cruzada contra el `plan.md` de 001-core-ventas-inventario mostró que esa feature ya reservó explícitamente la carpeta `modules/caja/` para "feature 006 (a futuro)" en su Project Structure (mismo patrón ya seguido sin excepción por 002→`clientes/`, 003→`pricing/`, 004→`forecasting/`, 005→`promociones/`) — y también reservó `modules/pagos/` para 007, confirmando que el nombre de carpeta de cada feature backend queda fijado desde el `plan.md` de 001, no se decide de nuevo en cada feature. Se corrigió `plan.md`, `tasks.md`, `contracts/caja-mermas-fraude.md` y `quickstart.md` de esta feature: `modules/finanzas/` → `modules/caja/`, `FinanzasRepository`/`FinanzasService` → `CajaRepository`/`CajaService`, `finanzasApi.js` → `cajaApi.js`, `/api/finanzas/...` → `/api/caja/...` (colapsando el segmento duplicado en `/api/finanzas/caja/apertura` → `/api/caja/apertura`). El nombre del módulo RBAC (`Finanzas`, tabla `modulos`) no cambia — es una entidad distinta del nombre de carpeta de código, y ambas ya convivían con nombres distintos en features previas (ej. 005: carpeta `promociones/` bajo el módulo RBAC `Marketing_CRM`/`Operaciones`).
