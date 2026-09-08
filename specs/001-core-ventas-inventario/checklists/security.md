# Checklist: Calidad de Requisitos de Seguridad — 001-core-ventas-inventario

**Propósito**: validar que los requisitos de seguridad de esta feature están completos, claros y son verificables — no valida el código, valida lo que el spec exige. Generado siguiendo el patrón de `/speckit-checklist`.

**Enfoque**: manejo de datos de tarjeta, control de doble autorización (anti-fraude), separación de roles/RBAC en operaciones sensibles.

- [x] ¿Está explícito que el cajero nunca captura, ve ni almacena datos de tarjeta? (FR-003) — sí, y se especifica que el ingreso ocurre en un paso separado dirigido al cliente.
- [x] ¿Está definido qué pasa si el pago falla por error técnico vs. rechazo del banco, sin que se confundan? (FR-030) — sí, dos señales visuales distintas y dos valores de `resultado` distintos.
- [x] ¿Está especificado el control de doble persona para remover una línea de venta antes de cobrar? (FR-027) — sí, con CHECK a nivel de base de datos (`cajero_id <> autoriza_empleado_id`), no solo a nivel de aplicación.
- [x] ¿Está especificado el mismo control de doble persona para pagos a proveedor? (FR-034) — sí, mismo patrón (`empleado_registra_id <> empleado_autoriza_id`).
- [x] ¿Es medible/verificable el cumplimiento de estos controles, no solo descriptivo? — sí, SC-007 y SC-009 los hacen medibles al 100% sin excepciones.
- [x] ¿Está definido qué pasa si el mismo empleado intenta registrar Y autorizar en un flujo de dos pasos separados en el tiempo (no en el mismo request)? — **Resuelto en `/speckit-implement` (T073)**: el endpoint que **finaliza** la acción de dos personas se autentica como el autorizador y valida contra el JWT que su `empleado_id` sea el `autoriza_empleado_id`/`empleado_autoriza_id` declarado y que sea distinto de quien registró — `DELETE /api/ventas/{id}/lineas/{id}` ([ventas/router.py](../../../backend/src/modules/ventas/router.py) L130-132) y `POST /api/compras/facturas/{id}/pagos` ([compras/router.py](../../../backend/src/modules/compras/router.py) L221-227). Frontend: `FormularioPagoProveedor.vue` reorientado (el usuario en sesión es el autorizador). Regresión: `test_ventas_remocion.py::test_remover_linea_nombrando_a_un_tercero_ausente_devuelve_403` y `test_compras_pagos.py::test_pago_autorizado_en_nombre_de_un_ausente_da_403`. Sin cambio de spec ni de esquema.
- [x] ¿Los requisitos de seguridad dependen de un componente fuera de esta feature de forma explícita? — sí, documentado en Assumptions: RBAC/autenticación es de la feature 008, esta feature asume un usuario ya autenticado.
- [x] ¿Se evita construir mecanismos de seguridad propios donde ya existe uno probado? — sí, Stripe Payment Intents en vez de una simulación de cobro inventada (research.md #6).

## Notas

Un solo gap real encontrado (doble-request en dos pasos), y era de implementación, no de especificación — no bloqueó avanzar a `tasks.md`. **Cerrado en T073** (Fase 8 · Polish): guard de sesión en los dos endpoints que finalizan una acción de dos personas + 2 tests de regresión. Checklist al 8/8.
