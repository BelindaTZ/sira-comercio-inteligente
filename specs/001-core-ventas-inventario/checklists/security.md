# Checklist: Calidad de Requisitos de Seguridad — 001-core-ventas-inventario

**Propósito**: validar que los requisitos de seguridad de esta feature están completos, claros y son verificables — no valida el código, valida lo que el spec exige. Generado siguiendo el patrón de `/speckit-checklist`.

**Enfoque**: manejo de datos de tarjeta, control de doble autorización (anti-fraude), separación de roles/RBAC en operaciones sensibles.

- [x] ¿Está explícito que el cajero nunca captura, ve ni almacena datos de tarjeta? (FR-003) — sí, y se especifica que el ingreso ocurre en un paso separado dirigido al cliente.
- [x] ¿Está definido qué pasa si el pago falla por error técnico vs. rechazo del banco, sin que se confundan? (FR-030) — sí, dos señales visuales distintas y dos valores de `resultado` distintos.
- [x] ¿Está especificado el control de doble persona para remover una línea de venta antes de cobrar? (FR-027) — sí, con CHECK a nivel de base de datos (`cajero_id <> autoriza_empleado_id`), no solo a nivel de aplicación.
- [x] ¿Está especificado el mismo control de doble persona para pagos a proveedor? (FR-034) — sí, mismo patrón (`empleado_registra_id <> empleado_autoriza_id`).
- [x] ¿Es medible/verificable el cumplimiento de estos controles, no solo descriptivo? — sí, SC-007 y SC-009 los hacen medibles al 100% sin excepciones.
- [ ] ¿Está definido qué pasa si el mismo empleado intenta registrar Y autorizar en un flujo de dos pasos separados en el tiempo (no en el mismo request)? — **Gap identificado**: el CHECK de base de datos cubre el caso de un solo request, pero no evita que el mismo empleado apruebe en dos pasos distintos si el frontend no valida la sesión activa. **Se deja para la fase de `/speckit-implement`**: el frontend debe impedir que el mismo usuario autenticado confirme su propia autorización, y el backend debe validar el JWT del segundo paso contra un `empleado_id` distinto — no requiere cambio de spec ni de esquema, es una regla de la capa de servicio.
- [x] ¿Los requisitos de seguridad dependen de un componente fuera de esta feature de forma explícita? — sí, documentado en Assumptions: RBAC/autenticación es de la feature 008, esta feature asume un usuario ya autenticado.
- [x] ¿Se evita construir mecanismos de seguridad propios donde ya existe uno probado? — sí, Stripe Payment Intents en vez de una simulación de cobro inventada (research.md #6).

## Notas

Un solo gap real encontrado (doble-request en dos pasos), y es de implementación, no de especificación — no bloquea avanzar a `tasks.md`. Se anota explícitamente para que quede trazable cuando se escriba la tarea correspondiente.
