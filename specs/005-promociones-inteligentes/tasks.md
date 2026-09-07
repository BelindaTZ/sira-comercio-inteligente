# Tasks: Promociones Inteligentes

**Input**: Design documents from `/specs/005-promociones-inteligentes/`
**Prerequisites**: plan.md, research.md, data-model.md, contracts/promociones.md, quickstart.md

**Tests**: Por Principio X, esta feature exige cobertura obligatoria en: el filtrado de reglas de asociación por soporte/confianza mínimos, la selección de la regla de mayor confianza cuando varias aplican, la clasificación ABC por valor de venta (Pareto), la exclusión de un candidato a liquidación con ajuste de precio pendiente en 003, y el anti-duplicado de cupón de afinidad — estas pruebas están incluidas explícitamente abajo, no son opcionales.

**Organización**: `modules/promociones/` es el módulo nuevo de esta feature (ya reservado desde el `plan.md` de 001); `modules/clientes/` (002) se extiende puntualmente para reutilizar el envío de cupones, y `modules/pricing/` (003) se consulta de solo lectura para la exclusión de candidatos — ninguno de los dos se recrea. Reutiliza infraestructura transversal ya construida en 001-004: FastAPI, SQLAlchemy async, Alembic, RBAC, `scheduler.py` (APScheduler), `DataTable.vue`/`WorkPanel.vue`.

## Format: `[ID] [P?] [Story] Descripción`

- **[P]**: Puede ejecutarse en paralelo (archivos distintos, sin dependencia entre sí)
- **[Story]**: A qué historia de usuario pertenece (US1-US4), o ninguna etiqueta si es Setup/Foundational/Polish

---

## Phase 1: Setup

- [X] T001 Crear el esqueleto de `backend/src/modules/promociones/` (`router.py`, `service.py`, `repository.py`, `schemas.py`, `analytics/__init__.py`, `analytics/afinidad.py`, `analytics/clasificacion_abc.py`), calcado de la estructura de capas ya usada en `pricing/` (003) y `forecasting/` (004).
- [X] T002 [P] Migración Alembic: crear `regla_afinidad`, `candidato_liquidacion`, `configuracion_promociones`; `ALTER TABLE campanas` para admitir `'afinidad'` en el `CHECK` de `categoria_sira` (ya extendida una vez en 002); `ALTER TABLE cupon_enviado ADD COLUMN regla_afinidad_id` (`data-model.md` completo), con seed inicial de `configuracion_promociones` (`soporte_minimo_regla`, `confianza_minima_regla`, `vigencia_cupon_afinidad_dias`, `rotacion_minima_liquidacion_semanal`, `descuento_liquidacion_pct`).
- [X] T003 [P] Agregar `mlxtend` como nueva dependencia backend (`research.md` Decisión 1).
- [X] T004 [P] Frontend: crear `frontend/src/modules/promociones/` (`pages/ReglasAfinidadPage.vue`, `LiquidacionPage.vue`, `ColocacionPromocionalPage.vue` vacíos) y `frontend/src/services/promocionesApi.js`.

## Phase 2: Foundational (Bloqueante — ninguna user story empieza sin esto)

- [X] T005 [P] Modelos SQLAlchemy: `ReglaAfinidad`, `CandidatoLiquidacion`, `ConfiguracionPromociones` en `models/`; extender `Campana` (nuevo valor de `categoria_sira`) y `CuponEnviado` (columna `regla_afinidad_id`).
- [X] T006 Registrar tres nuevos jobs en el `scheduler.py` ya existente (APScheduler, mismo mecanismo de 002-004): `calcular_afinidad_job` (mensual), `clasificar_abc_job` (mensual) y `generar_candidatos_liquidacion_job` (semanal), sin ejecutar todavía su lógica (se completa en Phase 3/5).
- [X] T007 [P] Extender el endpoint de "forzar corrida" de desarrollo ya usado en 003/004 para incluir estos tres jobs nuevos.
- [X] T008 Montar `promociones.router` en `main.py`; verificar en RBAC que los módulos `Marketing_CRM` y `Operaciones` (ya sembrados) cubren los endpoints de esta feature — sin rol ni módulo nuevo (`research.md` Decisión 10).

**Checkpoint**: Migraciones aplicadas, modelos disponibles, jobs registrados (sin lógica), router montado — listo para implementar historias de usuario.

---

## Phase 3: User Story 1 - Recomendación de cross-sell en el punto de venta a partir de afinidad de compra (Priority: P1) 🎯 MVP

**Goal**: Calcular mensualmente reglas de asociación de canasta y mostrar la recomendación de cross-sell de mayor confianza en el punto de venta cuando aplique.

**Independent Test**: forzar el cálculo mensual sobre datos con un par de productos claramente correlacionado, y verificar que al simular un cobro con uno de esos productos en el carrito, el sistema recomienda el otro.

### Tests para User Story 1 ⚠️

- [X] T009 [P] [US1] Unit test: filtrado de reglas de asociación por soporte/confianza mínimos configurados (`analytics/afinidad.py`, `research.md` Decisión 2).
- [X] T010 [P] [US1] Unit test: selección de la regla de mayor confianza cuando varias aplican al mismo producto del carrito (FR-005).
- [X] T011 [P] [US1] Contract test: `POST .../desactivar` y `GET recomendacion-cross-sell` — verificar el 409 al desactivar una regla ya no vigente, y `recomendacion_disponible: false` cuando no hay regla aplicable.
- [X] T012 [US1] Integration test: ciclo completo — calcular afinidad → consultar recomendación con el antecedente en el carrito → agregar el consecuente → la recomendación desaparece (Escenario 1 de `quickstart.md`).

### Implementación de User Story 1

- [X] T013 [P] [US1] `analytics/afinidad.py`: construir la matriz transacción×producto desde `venta_detalle` agrupado por `venta_id`, correr `apriori`/`association_rules` de `mlxtend` (`research.md` Decisión 1).
- [X] T014 [US1] `PromocionesRepository`: CRUD de `regla_afinidad` — marcar las `vigente` anteriores como `reemplazada` e insertar el nuevo conjunto calculado (`research.md` Decisión 3).
- [X] T015 [US1] `PromocionesService.calcular_afinidad()`: orquesta T013+T014 respetando los umbrales de `configuracion_promociones` (depende de T009), completa la lógica de `calcular_afinidad_job` (T006).
- [X] T016 [US1] `PromocionesService.desactivar_regla()` (depende de T011).
- [X] T017 [US1] `PromocionesService.recomendar_cross_sell(product_ids)`: busca reglas vigentes con antecedente en el carrito y consecuente fuera de él, devuelve la de mayor confianza (depende de T010).
- [X] T018 [US1] Endpoints: `GET reglas-afinidad`, `POST .../desactivar`, `GET recomendacion-cross-sell`, `POST reglas-afinidad/calcular` (dev) — `contracts/promociones.md`.
- [X] T019 [US1] `frontend/src/modules/promociones/pages/ReglasAfinidadPage.vue`: listado de reglas, acción de desactivar con motivo opcional.
- [X] T020 [US1] Frontend: extender `TicketVenta.vue` (`modules/pos/` de 001) — banner de recomendación de cross-sell al agregar productos al carrito, consultando `promocionesApi.js` directamente (sin pasar por `modules/ventas/` backend, `plan.md`).

**Checkpoint**: un cajero ve la recomendación de cross-sell en el punto de venta de punta a punta — MVP entregable de forma independiente.

---

## Phase 4: User Story 2 - Cupón de descuento enviado proactivamente por afinidad no aprovechada (Priority: P2)

**Goal**: Enviar automáticamente un cupón de descuento por correo cuando un cliente identificado compra el antecedente de una regla de afinidad vigente sin su consecuente.

**Independent Test**: con un cliente con consentimiento aceptado, registrar una compra que dispare la condición y verificar que recibe el cupón y que el envío queda registrado, sin duplicarse en una compra posterior dentro de la ventana de vigencia.

### Tests para User Story 2 ⚠️

- [X] T021 [P] [US2] Unit test: anti-duplicado de cupón de afinidad dentro de la ventana de vigencia configurada (FR-007, `research.md` Decisión 9).
- [X] T022 [US2] Integration test: venta que dispara el cupón de afinidad → un cliente sin consentimiento no recibe ningún cupón → la tasa de redención se calcula separada de la de cupones por hito (Escenario 3 de `quickstart.md`).

### Implementación de User Story 2

- [X] T023 [US2] `PromocionesService.evaluar_venta_para_afinidad(venta_id)`: detecta si la venta contiene el antecedente de una regla vigente sin el consecuente, verifica el consentimiento de datos del cliente (reutiliza el campo ya existente de 002) y la ventana anti-duplicado (depende de T017, T021).
- [X] T024 [US2] Extender `ClientesService` (`modules/clientes/`, 002) con un método reutilizable de envío de cupón para el nuevo tipo `afinidad` (campaña + `regla_afinidad_id`) — sin duplicar su lógica de envío por SendGrid ya existente.
- [X] T025 [US2] Enganchar `evaluar_venta_para_afinidad()` al cierre de una venta — extensión puntual de `modules/ventas/` (001) que llama al servicio de `promociones/`, mismo patrón de extensión ya usado en 004 para `inventario/compras` (depende de T023, T024).
- [X] T026 [US2] Endpoints: `GET cupones-afinidad`, `GET cupones-afinidad/tasa-redencion`, `POST cupones-afinidad/evaluar-venta/{id}` (dev).
- [X] T027 [US2] Frontend: extender la página de campañas ya existente de 002 (o `clientesApi.js`) para mostrar la tasa de redención de cupones de afinidad por separado de la de hitos.

**Checkpoint**: OT-3.5 queda completo (incluida la nueva OO-3.5.3) de punta a punta.

---

## Phase 5: User Story 3 - Clasificación por rotación y liquidación de productos de categoría C (Priority: P3)

**Goal**: Clasificar mensualmente el catálogo por rotación (A/B/C) y generar semanalmente, por tienda, candidatos a liquidación de categoría C que el Encargado de Tienda pueda ejecutar.

**Independent Test**: sembrar un producto con ventas bajas, ejecutar la clasificación, verificar que queda en C, que aparece como candidato en una tienda donde también rota poco, y que puede ejecutarse o quedar sin ejecutar.

### Tests para User Story 3 ⚠️

- [X] T028 [P] [US3] Unit test: clasificación ABC por valor de venta acumulado (Pareto) dentro de una categoría de producto (`research.md` Decisión 5).
- [X] T029 [P] [US3] Unit test: exclusión de un candidato a liquidación con una `propuesta_ajuste_precio` (003) en estado `pendiente` (FR-013, `research.md` Decisión 7).
- [X] T030 [US3] Contract test: `GET`/`PATCH liquidacion/reglas`, `GET liquidacion/candidatos`, `POST .../ejecutar` — verificar el 409 al ejecutar un candidato que ya no está `candidato`.
- [X] T031 [US3] Integration test: producto con rotación baja en toda la red → queda clasificado `C` → aparece como candidato en la tienda donde también rota poco → el Encargado de Tienda lo ejecuta (Escenario 4 de `quickstart.md`); y el Escenario 5 (exclusión por precio pendiente).

### Implementación de User Story 3

- [X] T032 [P] [US3] `analytics/clasificacion_abc.py`: cálculo Pareto por categoría sobre `venta_detalle` (depende de T028).
- [X] T033 [US3] `PromocionesService.clasificar_abc()`: orquesta T032, actualiza `productos.clasificacion_abc`, registra qué productos cambiaron de clasificación (FR-010), completa la lógica de `clasificar_abc_job` (T006).
- [X] T034 [US3] `PromocionesRepository`: consulta de solo lectura contra `propuesta_ajuste_precio` (003) para la exclusión de candidatos (depende de T029).
- [X] T035 [US3] `PromocionesService.generar_candidatos_liquidacion()`: productos `clasificacion_abc = 'C'` con rotación local por tienda bajo el umbral vigente, excluyendo los de T034; completa la lógica de `generar_candidatos_liquidacion_job` (T006) (depende de T033, T034).
- [X] T036 [US3] `PromocionesService.ejecutar_candidato()`.
- [X] T037 [US3] Endpoints: `GET clasificacion-abc`, `POST clasificacion-abc/calcular` (dev), `GET`/`PATCH liquidacion/reglas`, `GET liquidacion/candidatos`, `POST .../ejecutar`, `POST liquidacion/candidatos/calcular` (dev).
- [X] T038 [US3] `frontend/src/modules/promociones/pages/LiquidacionPage.vue`: listado de candidatos por tienda con acción de ejecutar; vista de productos reclasificados del mes.

**Checkpoint**: OT-2.2/OT-2.3 quedan cerrados, sin bloquear ningún flujo previo de 001/003 cuando hay conflicto de precio pendiente.

---

## Phase 6: User Story 4 - Registro de colocación de producto en anaquel destacado o mailer promocional (Priority: P4)

**Goal**: Registrar la colocación de un producto en anaquel destacado o mailer por tienda y semana, y poder comparar su efecto en ventas frente a un periodo sin colocación.

**Independent Test**: registrar una colocación y verificar que queda consultable junto con el efecto observado en ventas de esa semana frente a un periodo de referencia.

### Tests para User Story 4 ⚠️

- [X] T039 [US4] Integration test: registrar colocación → consultar el efecto de ventas con/sin colocación (Escenario 6 de `quickstart.md`).

### Implementación de User Story 4

- [X] T040 [US4] `PromocionesRepository`: CRUD sobre `promociones` (`product_id`, `tienda_id`, `display_location`, `mailer_location`, `semana`, `anio`) — tabla ya existente, sin migración nueva.
- [X] T041 [US4] `PromocionesService.registrar_colocacion()` / `.calcular_efecto_colocacion()` (ventas de la semana de colocación vs. periodo de referencia, sin atribución causal — FR-016).
- [X] T042 [US4] Endpoints: `GET`/`POST colocaciones`, `GET colocaciones/{id}/efecto`.
- [X] T043 [US4] `frontend/src/modules/promociones/pages/ColocacionPromocionalPage.vue`: formulario de registro y vista de efecto.

**Checkpoint**: la colocación registrada por esta feature es la misma que 004 ya lee como variable exógena — sin tabla duplicada.

---

## Phase 7: Polish

- [X] T044 Ejecutar `/speckit-analyze` sobre esta feature y corregir cualquier inconsistencia detectada entre spec/plan/tasks.
- [X] T045 Correr los 6 escenarios de `quickstart.md` de punta a punta contra el entorno local.
- [X] T046 Revisar cobertura de Principio X: confirmar que el filtrado de reglas por soporte/confianza (T009), la exclusión por precio pendiente (T029) y el anti-duplicado de cupón de afinidad (T021) tienen test unitario antes de cerrar la feature.
- [X] T047 Actualizar `checklists/requirements.md` con cualquier hallazgo de la revisión final (nueva "Ronda" si aplica).

## Dependencias clave

- Phase 2 (Foundational) bloquea todas las historias.
- US1 (T013-T020) es prerrequisito real de US2 (T023 depende de que exista `recomendar_cross_sell()`/reglas vigentes, T017) — US2 no puede evaluar afinidad no aprovechada sin reglas ya calculadas.
- US3 (clasificación ABC + liquidación) no depende de US1 ni de US2 — puede implementarse en paralelo una vez cerrada Phase 2.
- US4 (colocación promocional) no depende de ninguna otra historia de esta feature — puede implementarse en cualquier momento, incluso antes que US1-US3, aunque se numera al final por ser la prioridad más baja.
- La verificación de precio pendiente (T034, boundary con 003) es de solo lectura — no requiere ningún cambio en `modules/pricing/`, solo una consulta nueva desde `promociones/`.
