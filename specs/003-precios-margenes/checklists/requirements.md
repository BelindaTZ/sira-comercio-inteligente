# Specification Quality Checklist: Precios Dinámicos, Márgenes y Comparación de Competencia

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

- Validación ejecutada releyendo `constitution.md` completa y `domain-context.md` (OE-1 completo: OT-1.1 a OT-1.4; y OT-4.3 de OE-4, incorporada aquí por decisión del usuario al no tener feature dueña) antes de redactar.
- Investigación previa (vía subagente) sobre `specs/001-core-ventas-inventario/` para evitar solapamiento: se confirmó que 001 solo cubre la clasificación ancla/nicho al alta (FR-012) y la actualización de costo/precio sin historial (FR-010) — el resto de OE-1 (pricing dinámico, margen mínimo, descuento manual, reportes) estaba sin dueño y libre para esta feature.
- Se detectó que las tablas `historial_precios` y `margenes_objetivo` ya existían en `01_operativo_postgres.sql` desde el esquema base, sin que 001 las usara — quedan asignadas a esta feature.
- Se detectó y resolvió con el usuario un gap real: OT-1.3 (margen mínimo) dependía de un "descuento manual en punto de venta" que 001 nunca implementó. Se explicó el mecanismo (control detectivo, no preventivo — reutiliza `venta_detalle.retail_disc` con motivo obligatorio) y el usuario confirmó extender el flujo de venta de 001 en vez de solo reportar sobre datos que nunca se generarían.
- Se detectó el mismo gap de rol que en 002: `domain-context.md` asigna varias OO a un actor "Analista de Pricing" sin rol RBAC propio. Se aplicó la misma decisión ya tomada para "Analista de Marketing": `Jefe_Comercial` ejecuta también esas acciones, sin agregar un rol nuevo.
- Se verificó contra el enunciado original: "saben exactamente qué margen tienen en cada producto... un requesón alegre/triste" (FR-001 a FR-008, margen objetivo diferenciado por ancla/nicho), "Stevia está tirando dinero en una economía de márgenes ajustados" (FR-009 a FR-012, descuento manual con detección), y "si ki-requesón tiene un precio ligeramente mayor, pierdes la venta" (FR-014 a FR-016, comparación de precio vs. competencia) — los tres puntos quedan cubiertos explícitamente.
- No se detectaron violaciones de principios de la constitución.

## Ronda 2 (corrección de US3 — autorización de descuento manual)

- Se corrigió una decisión de la ronda anterior: el control de descuento manual se había modelado como puramente detectivo (reporte + revisión posterior, sin autorización previa), siguiendo la redacción literal del BSC ("reportar"/"revisar"). El usuario aportó práctica real del sector retail (el descuento manual en caja casi siempre exige autorización de supervisor con PIN, sin excepción por monto, para evitar fraude tipo "sweethearting") y confirmó exigirla.
- `FR-009` ahora exige autorización de un Encargado_Tienda (o superior) distinto de quien aplica el descuento, sin excepción de monto — mismo patrón `CHECK` ya usado en `FR-027` de 001 (remoción de línea) y `FR-034` (pago a proveedor). `FR-010` (detección de margen bajo mínimo) se mantiene como control detectivo adicional, ahora aplicado sobre descuentos ya autorizados, no en su lugar.
- Sincronizado en las historias de usuario (US3), Acceptance Scenarios, Edge Cases, Key Entities, Success Criteria (SC-004) y Assumptions de `spec.md`. No requirió cambios en `domain-context.md` — OO-1.3.1/OO-1.3.2 ya eran compatibles con esta lectura.
- No se detectaron más violaciones de principios de la constitución.

## Ronda 3 (corrección de FR-014/FR-016 — Open Prices para productos en vivo con barcode real)

- El usuario aportó investigación real sobre cómo el sector retail obtiene precios de competencia (scraping, plataformas pagas como Prisync/Price2Spy/Dealavo, verificadores de campo, paneles Nielsen/IRI) y preguntó explícitamente si la comparación de precios se limitaba al dataset — se le explicó que el catálogo sembrado (~92,331 productos Dunnhumby) tiene barcode sintético (Principio VII, rango GS1 20-29 "uso interno") y por lo tanto no puede matchear contra ningún catálogo de competencia real.
- El usuario hizo una segunda pregunta más precisa: esa limitación del dataset, ¿aplica también a los productos que se agreguen manualmente/en vivo después? La respuesta es no — los productos agregados en vivo por la UI (FR-013 de 001) llevan código de barras real, el mismo que ya se usa para autocompletar con Open Food Facts. Esto abrió la puerta a una fuente de datos real y gratuita para esos productos: **Open Prices** (prices.openfoodfacts.org), un proyecto de la misma organización que Open Food Facts (ya aprobada en el Stack), de lectura pública y gratuita sin cuenta.
- Se verificó que esta adición no requiere una enmienda formal a la constitución: no viola Principio III (Separación de Motores — es una llamada HTTP a un servicio externo ya documentado, no un motor de datos nuevo) ni Principio VII (Anclaje al Dataset Real — ese principio rige semillas/pruebas, no una consulta en vivo de un dato real para un producto ya 100% real).
- `precio_competencia` pasa de un booleano `es_sintetico` a un campo `fuente_captura` (`manual` / `open_prices` / `sintetico`) porque ahora hay dos fuentes no-sintéticas distintas. Se agregó la entidad `competidores` (nombre, tipo, ciudad) y los campos `competidor_id` (nullable), `tienda_id` (nullable, relevancia geográfica) y `es_promocional` a `precio_competencia`, recogiendo directamente la investigación de mercado del usuario sobre cómo las herramientas reales del sector capturan por competidor nombrado y por zona.
- Actualizado: `domain-context.md` (línea de "Comparación de precios con competencia" en sección 9, ya no dice "no existe API pública/legal"; nueva línea de Open Prices; resumen de 003 en sección 8), `spec.md` (FR-014, FR-015, Key Entities, Assumptions), `research.md` (Decisión 5 reescrita, Decisión 6 ampliada), `data-model.md` (nueva entidad Competidor, entidad Precio de Referencia de Competencia reescrita, tabla de trazabilidad), y el DDL ya aplicado en `01_operativo_postgres.sql` (nueva tabla `competidores`, `precio_competencia` con `competidor_id`/`tienda_id`/`es_promocional`/`fuente_captura` en vez de `es_sintetico`) — ningún otro módulo dependía todavía de la versión anterior de esa tabla, así que se corrigió directamente sin necesidad de una migración incremental.
- No se detectaron más violaciones de principios de la constitución.

## Ronda 4 (implementación — `/speckit-implement` + `/speckit-analyze` post-hoc)

- Feature implementada de punta a punta: módulo `backend/src/modules/pricing/` (router/service/repository/schemas), 7 modelos SQLAlchemy nuevos/activados, migración `0010_feature003_precios_margenes` (idempotente, espeja el bloque "EXTENSIÓN — Feature 003" del DDL + RBAC), 2 jobs `APScheduler` (`propuestas_ajuste_semanal`, `alertas_competencia_semanal`), cliente `open_prices_client`, extensión de `modules/ventas` (descuento manual autorizado + margen real por línea al confirmar) y de `modules/catalogo` (captura Open Prices al alta en vivo). Frontend: `modules/pricing/` (MargenesPage, PropuestasPrecioPage, ReporteMargenPage, CompetenciaPage + FormularioReglaAjuste, TablaMargenBajo), `pricingApi.js`, modal de autorización de descuento en `TicketVenta.vue`.
- Cobertura de tests: 202 backend (150 previos + 52 nuevos), 0 fallos. Principio X cubierto con lógica pura aislada en `src/shared/pricing.py` y sus tests: `test_calculo_margen_real`, `test_margen_efectivo_ancla_nicho`, `test_formula_ajuste_precio`, `test_autorizacion_descuento`, `test_desviacion_competencia`. Los 7 escenarios de `quickstart.md` quedan cubiertos por los tests de integración `test_us1_margen_real` … `test_us5_competencia`.
- `/speckit-analyze` (post-hoc): 0 issues CRITICAL/HIGH; 16/16 FR con tarea; hallazgo MEDIO I1 remediado en la misma corrida — el margen real de una línea ahora se calcula sobre el precio después de TODOS los descuentos (`retail_disc + coupon_disc + coupon_match_disc`), no sólo el descuento manual, alineando el cálculo con el Edge Case de `spec.md` (cupón de 002 + descuento manual de 003). Hallazgo LOW I2 (historial de precio "por tienda" vs. `tienda_id = NULL` en el MVP) ya estaba reconciliado en `research.md §1`. SC-001 es una métrica de resultado (el reporte expone las categorías sin margen objetivo; no se fuerza por código).

