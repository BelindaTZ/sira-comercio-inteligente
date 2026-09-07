# Specification Quality Checklist: Core de Ventas e Inventario (Punto de Venta, Catálogo y Reposición)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-09-04
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

- Validación ejecutada en una sola iteración (sin marcadores [NEEDS CLARIFICATION]): el alcance ya venía acotado por decisiones previas registradas en `domain-context.md` (dataset sembrado, RBAC en 008, cuadre de caja/fraude en 006, pronóstico avanzado en 004, fidelización/CLV en 002), por lo que no hubo ambigüedades de scope, seguridad, UX o técnicas pendientes de resolver con el usuario.
- Se citan nombres de servicios ya aprobados en la constitución (pasarela de pago, catálogo abierto de productos) únicamente como restricción de negocio ya decidida a nivel de proyecto, no como detalle de implementación introducido en este spec.
- Segunda pasada (2026-09-05) tras revisión del usuario: se releyó `constitution.md` completa (los 12 principios, no solo `domain-context.md`) y se agregaron FR-027/028/029 + entidad Proveedor + escenarios de aceptación en User Story 1 y 3, cubriendo: (a) anulación de línea de venta antes de cobrar con confirmación de encargado (OE-6, OT-6.4, Principio I), (b) frecuencia de reposición pactada por proveedor y pedido especial por correo (OT-2.1, Principio I), y se documentó como limitación aceptada en Assumptions la imposibilidad de trazar FIFO por unidad física serializada (Principio II: el registro es real a nivel de lote, no de unidad). No se detectaron violaciones de principios tras esta segunda pasada.
- Tercera pasada (2026-09-05): se aclaró FR-003 (el cajero nunca captura ni ve los datos de la tarjeta; el ingreso ocurre en un paso separado dirigido al cliente, replicando la separación real caja/datáfono) y se agregaron FR-030/FR-031 (simulación visual del paso de tarjeta con retroalimentación aprobado/rechazado, y manejo de rechazo sin perder la venta en curso), más SC-008 y el escenario de aceptación correspondiente en User Story 1. Se dejó explícito en Assumptions que el diseño visual exacto de la simulación no es parte de este documento (va en design-system.md / plan). No se detectaron violaciones de principios.
- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`.

- Cuarta pasada (2026-09-05): FR-030/FR-031 y User Story 1 ampliados para distinguir 3 resultados de un cobro con tarjeta (aprobado / rechazado por el banco / error técnico de comunicación con la pasarela), evitando que un rechazo del cliente se confunda con una falla del sistema. Se agregaron el escenario de aceptación y el edge case correspondientes. No se detectaron violaciones de principios.

- Quinta pasada (2026-09-05): se reforzó la Assumption sobre FIFO/FEFO explicando el mecanismo real (la fecha de vencimiento se conoce por la recepción de mercadería, no por el código de barras — estándar GS1 para consumo masivo), sin cambiar ningún FR ni comportamiento, solo precisando el "por qué" de una limitación ya documentada.

## Notas — Ronda 6 (cuentas por pagar a proveedor + comprobante fiscal)

- Se agregó FR-032 a FR-036: RUC de proveedor, factura de proveedor (3-way match con orden+recepción), pago con doble autorización (empleado_registra ≠ empleado_autoriza, mismo patrón ya usado en FR-027), estado de factura derivado en capa de servicio, y distinción factura/nota de venta a consumidor final en el comprobante.
- Nuevas entidades: Factura de Proveedor, Pago a Proveedor. Entidades actualizadas: Proveedor (+RUC), Venta (+tipo de comprobante, identificación/razón social del comprador).
- Nuevos objetivos operativos en domain-context.md: OO-2.1.4, OO-2.1.5 (bajo OT-2.1 ya existente) y un nuevo OT-6.5 con OO-6.5.1/2/3 (Finanzas) — con visibilidad táctica (revisión semanal de Jefe de Finanzas) y estratégica (reporte mensual a Dirección General), a pedido explícito del usuario de que estos cambios no queden solo a nivel operativo.
- Verificado contra los 12 principios de la constitución: ninguna violación. El control de doble autorización reutiliza un patrón ya existente (Principio VIII, no se inventa un mecanismo nuevo). El estado derivado de la factura se calcula en la capa de servicio, no con triggers de base de datos (Principio XI).
- DDL: `01_operativo_postgres.sql` extendido con `proveedores.ruc`, tablas `facturas_proveedor` y `pagos_proveedor`, y 3 columnas nuevas en `ventas`.

## Notas — Ronda 7 (tasks.md)

- `tasks.md` generado: 78 tareas en 8 fases (Setup, Foundational, 5 user stories en orden de prioridad P1-P5, Polish). Incluye tests dirigidos a la lógica crítica que exige el Principio X (FIFO/FEFO, punto de reposición, cálculo de totales, RBAC/doble autorización) — no cobertura total del proyecto.
- Con esto, la especificación completa de la feature 001 queda cerrada: spec.md (36 FR, 10 SC), plan.md, research.md (10 decisiones), data-model.md (16 entidades), contracts/ (4 módulos), quickstart.md (6 escenarios), checklists/requirements.md + security.md, tasks.md (78 tareas).
- Pendiente explícito para la fase de implementación (no de spec): resolver el gap anotado en checklists/security.md (T073) sobre doble-request en dos pasos separados en el tiempo.

## Notas — Ronda 8 (impresión automática del comprobante + logotipo de marca)

- Gap detectado por el usuario antes de `/speckit-implement`: el spec ya exigía generar el comprobante PDF (FR-004) pero no que se presentara listo para imprimir/guardar de inmediato al confirmar la venta, ni ninguna guía de dónde/cómo usar el logotipo de Marzú Retail Group (no había ninguna mención de "logo" en `design-system.md`).
- Corregido: FR-004 extendido (presentación inmediata lista para imprimir/guardar), nuevo edge case (sin impresora física conectada → "Guardar como PDF"), nueva SC-011, y nota en Assumptions delegando el diseño visual/logo a `design-system.md` (mismo criterio ya usado para FR-030).
- `research.md` (decisión 7) documenta la mecánica técnica: `Content-Disposition: inline` + `window.open` en el frontend (sin librería de impresión), y que el logo requiere una versión rasterizada (PNG) para `reportlab` además de la vectorial (SVG) para la SPA.
- `design-system.md` recibió una nueva sección "Logotipo y Uso de Marca" fijando las 4 ubicaciones del logo (navbar, login, comprobante PDF, favicon) y los formatos requeridos — a la espera de que el usuario suba el archivo real antes de `/speckit-implement`.
- `contracts/ventas.md`, `tasks.md` (T029, T032) y `quickstart.md` (Escenario 1) actualizados para reflejar el nuevo comportamiento. No se detectaron violaciones de principios: reutiliza el mismo patrón de "visual detail deferred to design-system.md" ya establecido para FR-030, sin agregar ninguna dependencia nueva al proyecto.

## Notas — Ronda 9 (límites de stock máximo por categoría — OT-2.4)

- Gap de BSC incorporado tras el cierre inicial de 001-006: OT-2.4 (`oo-objetivos-operativos.md`, OO-2.4.1/2.4.2) no tenía feature dueña. Se decidió, junto con el usuario, dividir el gap OT-2.4/OT-2.5: OT-2.4 se incorpora aquí por ser una extensión mínima del mecanismo de alertas ya existente; OT-2.5 (coordinación entre tiendas/traslados) se especifica aparte en la feature nueva 012-traslados-stock-entre-tiendas, por tratarse de un flujo propio no reducible a una alerta.
- Agregado: FR-037 (definir/actualizar stock máximo por categoría/tienda), FR-038 (alerta `exceso_stock` al recibir por encima del máximo, sin bloquear la recepción), 2 nuevos acceptance scenarios en User Story 3, nuevo edge case, SC-012, nueva entidad `Stock Máximo por Categoría` (tabla `stock_maximo_categoria`, nueva).
- `data-model.md` (entidad 17 y extensión de la entidad 11), `contracts/inventario.md` (3 endpoints nuevos/extendidos) y `tasks.md` (T079-T083) actualizados. No se detectaron violaciones de principios: reutiliza `alertas_inventario` en vez de crear una tabla de alertas paralela, y sigue el mismo criterio de configuración simple (sin historial de versiones) ya usado para `umbral_merma_categoria` en 006.

## Notas — Ronda 10 (auditoría completa de cobertura OT/OO — OO-2.1.5, OO-6.5.2, OO-6.5.3, OT-4.4)

- **Origen**: antes de arrancar el batch de artefactos de 007-012, el usuario pidió una auditoría de las 108 OO del BSC contra los 12 `spec.md` existentes. Se cruzaron los códigos OO/OT reales contra el contenido de cada spec (no solo contra memoria de sesiones anteriores) y aparecieron 4 huecos: 3 reportes faltantes sobre datos ya modelados en esta feature (sin tabla nueva) y un OT completo (OT-4.4) sin ninguna feature dueña en las 12.
- **Hallazgo de drift documental**: `contracts/compras.md` ya citaba `OO-6.5.2` en el endpoint `GET /api/compras/facturas` desde antes de esta Ronda, pero ningún FR de `spec.md` lo respaldaba — quedó corregido con FR-040, sin cambiar el contrato existente.
- **OT-4.4 (disponibilidad 95% de productos de alta demanda)**: se incorpora en esta feature (no en una nueva) por ser inventario/reposición — reutiliza `productos.clasificacion_abc='A'` como definición de "alta demanda" (sin columna nueva en `productos`) y el mecanismo ya existente de `eventos_quiebre_stock` para el escalamiento inmediato (FR-043, columna aditiva `es_alta_demanda`); solo la verificación diaria de anaquel (FR-042) requirió una tabla nueva mínima, `verificacion_anaquel`.
- Agregado: FR-039 a FR-043, 5 acceptance scenarios nuevos en User Story 3, 2 edge cases, SC-013/SC-014, nueva entidad `Verificación de Anaquel`, 3 endpoints nuevos (`POST /api/inventario/verificacion-anaquel`, `GET /api/compras/facturas/resumen`, `GET /api/compras/reportes/automatico-vs-manual`) y extensión de `POST /api/inventario/quiebres`. `data-model.md`, `contracts/inventario.md`, `contracts/compras.md`, `tasks.md` (T084-T089) y `quickstart.md` (Escenario 8) actualizados. No se detectaron violaciones de principios.

## Notas — Ronda 11 (visibilidad proveedor↔producto)

- **Origen**: pregunta directa del usuario durante la Fase 5 de implementación, tras confirmarse (research.md #11) que FR-023 resuelve el proveedor de la sugerencia semanal buscando la última orden de compra del producto, sin exponer esa relación como consulta propia. No proviene de una auditoría BSC — es una mejora de usabilidad decidida junto con el usuario, no un gap de OO/OT preexistente.
- Agregado: FR-044, 1 acceptance scenario nuevo en User Story 3, SC-015, 2 endpoints de solo lectura nuevos (sin tabla ni catálogo maestro nuevo — se derivan de `ordenes_compra`/`orden_compra_detalle` ya existentes).
- `contracts/compras.md` (2 endpoints), `tasks.md` (T090-T093, aún no implementadas) y `quickstart.md` (Escenario 9) actualizados. No se detectaron violaciones de principios: reutiliza tablas existentes (Principio VIII, KISS) y datos reales de compras ya registradas (Principio II).
