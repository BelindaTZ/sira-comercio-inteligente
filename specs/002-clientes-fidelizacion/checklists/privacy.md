# Checklist: Calidad de Requisitos de Privacidad — 002-clientes-fidelizacion

**Propósito**: validar que los requisitos de protección de datos personales (LOPDP) de esta feature están completos, claros y son verificables — no valida el código, valida lo que el spec exige. Generado siguiendo el patrón de `/speckit-checklist` (mismo criterio que `security.md` de 001: dominio de riesgo específico de esta feature).

**Enfoque**: consentimiento de tratamiento de datos, gating de perfilado, anonimización real en la baja, minimización de datos.

- [x] ¿Está explícito que el consentimiento se captura en el momento del alta, no después? (FR-001) — sí, campo obligatorio del `POST /api/clientes`.
- [x] ¿Está definido qué pasa si el cliente rechaza el consentimiento — se bloquea el alta o solo el perfilado? (FR-001, Edge Case) — sí, el alta nunca se bloquea por esto; solo excluye al cliente de CLV/churn/campañas.
- [x] ¿El gating de consentimiento aplica a los tres lugares donde importa (CLV, churn, segmentación de campañas), no solo a uno? (research.md §4) — sí, filtro `consentimiento_datos = true` en los tres repositories/jobs.
- [x] ¿La baja de cliente es una anonimización real (datos irreversibles) y no un simple flag reversible? (FR-003, research.md §5) — sí, UPDATE que sobrescribe nombre/email/teléfono/fecha de nacimiento; sin campo "activo=false" como único cambio.
- [x] ¿La anonimización preserva la integridad referencial en vez de un DELETE físico que rompería el historial? (FR-003) — sí, `household_id` se conserva explícitamente.
- [x] ¿Los datos demográficos (edad, ingreso, estado civil, etc.) están marcados como opcionales y nunca bloquean el alta? (FR-004) — sí, explícito en el FR y en `data-model.md`.
- [x] ¿Está documentado por qué los clientes ya sembrados del dataset tienen consentimiento por defecto, para que no se lea como un descuido de privacidad? (Assumptions de spec.md, research.md §5) — sí, grandfathering explícito con justificación.
- [x] ¿Puede un cliente que ya dio su consentimiento revocarlo después, sin tener que darse de baja por completo? — **Resuelto**: `FR-002` se extendió para incluir `consentimiento_datos` entre los campos editables vía `PATCH /api/clientes/{id}`; revocar excluye al cliente del gating de FR-001 hacia adelante (sin tocar su historial ya calculado) sin anonimizar nombre/email/teléfono ni requerir la baja completa (FR-003). Confirmado por el usuario.

## Notas

Un gap real encontrado y ya corregido en `spec.md` (FR-002), `contracts/clientes.md`, `data-model.md` y `tasks.md` — a diferencia del gap de `security.md` (001), este sí requería un cambio de requisito, no solo una regla de la capa de servicio.
