# SIRA (Sistema Inteligente de Retail Adaptativo) Constitution

Identidad, misión y objetivos completos del sistema en `.specify/memory/domain-context.md` — esta constitución no los repite, los referencia.

## Core Principles

### I. Trazabilidad al BSC
Toda feature, endpoint o tabla nueva debe trazarse a al menos un Objetivo Operativo (OO) de `domain-context.md`, y este a su OT y OE. No se implementa funcionalidad que no resuelva un objetivo ahí documentado.

### II. Nivel Operativo = Registro Real (NON-NEGOTIABLE)
Toda operación de nivel operativo es un INSERT/UPDATE/DELETE sobre un registro concreto, ligado a un documento de negocio real (ticket de venta, nota de recepción, ajuste de inventario, apertura de caja, etc.). Nada de simulacros ni "estados" sin persistencia transaccional real en PostgreSQL.

### III. Separación de Motores por Responsabilidad
PostgreSQL = único motor operativo (OLTP). MinIO tiene tres responsabilidades en buckets separados: `landing-zone` (raw del Extract, nunca consultado como fuente de negocio), `producto-imagenes` (almacenamiento estático de imágenes de producto, servido directo a la app) y `comprobantes-venta` (PDF de comprobante de venta generado al confirmar cada venta, servido vía endpoint autenticado) — las tres son archivos estáticos servidos directo a la app, no datos transaccionales. ClickHouse = warehouse para agregaciones tácticas/estratégicas. Flujo ELT (no ETL): Extract → Load raw a MinIO (landing-zone) → Load a ClickHouse → Transform in-warehouse, orquestado por Airflow. Ninguna feature mezcla responsabilidades entre motores ni entre buckets.

### IV. RBAC de Dos Niveles Obligatorio
Toda funcionalidad nueva declara sus permisos en el esquema existente: rol→módulo y rol→módulo→tabla (select/insert/update/delete), respetando la FK compuesta que exige acceso al módulo antes del permiso de tabla. No se crean rutas de acceso paralelas.

### V. Backend y Frontend Desacoplados
El backend (FastAPI) expone únicamente API REST/JSON — no renderiza HTML. El frontend (Vue 3 + Vite) consume esa API y es el único responsable de la interfaz. Ninguna lógica de negocio vive en el frontend; ninguna lógica de presentación vive en el backend.

### VI. Features Autocontenidas
Cada spec en specs/NNN-feature/ es independiente y completa. Una feature no redefine lo ya fijado en esta constitución, en domain-context.md, ni en el modelo de datos operativo (01_operativo_postgres.sql) — los referencia.

### VII. Anclaje al Dataset Real
Toda prueba, seed o validación de datos usa el dataset Dunnhumby "The Complete Journey" (csv/), no datos inventados sueltos, salvo que el objetivo requiera un dato que el dataset no cubre (ej. medio_pago), documentado explícitamente como sintetizado.

### VIII. Simplicidad Justificada (DRY/KISS)
No se añade tabla, motor, microservicio o dependencia nueva sin justificarla contra el objetivo que resuelve. No se duplica lógica que ya existe en otra capa (DRY); se prefiere siempre la solución más simple que cumpla el requisito (KISS).

### IX. Guardrails de la IA sobre Specs (NON-NEGOTIABLE)
Ningún spec, plan, tasks, constitution.md o domain-context.md existente se borra o reescribe sin confirmación explícita del usuario. Cada hito (spec aprobado, plan aprobado, tasks aprobado) se valida con el usuario antes de avanzar al siguiente. Esta restricción aplica a documentos de especificación, no al código de implementación.

### X. Calidad, Testing y Seguridad
Testing: cobertura obligatoria de pruebas unitarias/integración en la lógica de negocio crítica de cada feature (cálculo de margen, CLV, churn, cuadre de caja, RBAC, forecasting) — no se exige 100% del proyecto, sí de estos módulos. Seguridad: credenciales y secretos solo vía `.env` (nunca hardcodeados), sanitización de toda entrada de usuario, autenticación JWT + autorización RBAC en cada endpoint. Rendimiento: operaciones CRUD estándar responden en <1s en entorno de desarrollo; reportes/dashboards agregados (ClickHouse) pueden tardar más, sin bloquear la interfaz (carga asíncrona).

### XI. Convenciones de Código y Arquitectura
Backend: snake_case (Python/SQL), arquitectura por capas (router → service → repository), sin lógica de negocio en los routers. Frontend: camelCase (JS/Vue), componentes + composables, sin llamadas directas a la API fuera de una capa de servicios centralizada.

### XII. Usabilidad y Diseño de Interfaz
Los filtros de búsqueda son reactivos/automáticos — sin botón "Buscar" o "Filtrar", se aplican al cambiar el criterio. Todo listado de registros usa paginación (nunca carga completa en una sola vista). Cada panel de trabajo (work panel) sigue un set estandarizado de acciones (Agregar, Editar, Eliminar, y las que correspondan a la entidad — ej. Anular para ventas, Aprobar para compras) con la misma ubicación/estilo en toda la aplicación.

**Diálogos**: toda confirmación (aceptar/rechazar) y toda entrada de un dato puntual (motivo, fecha, id que autoriza) se resuelve con un modal in-app del design-system — nunca con `window.confirm` / `window.prompt` / `window.alert`, que rompen la paleta y la tipografía. El helper compartido es `frontend/src/shared/ui/dialogs.js` (`confirm()` / `prompt()`), pintado por `<DialogHost>` (montado una vez en `App.vue`). Un selector siempre ofrece las opciones válidas existentes (`<select>` poblado desde el backend) en vez de un campo libre donde se pueda teclear un valor inexistente.

**Acciones que no llevan a nada**: ningún botón puede quedarse en un mensaje de "listo" sin efecto real. Toda acción o bien ejecuta su operación contra el backend, o bien navega a la pantalla/modal donde se resuelve (con el contexto ya cargado). Un botón que "recomienda" o "sugiere" algo debe abrir el flujo concreto (ej. "Solicitar reposición" → abre la orden de compra con el producto y la cantidad puestas).

**Exportación de reportes**: toda pantalla de reporte ofrece la descarga en **CSV, Excel y PDF** mediante el helper compartido `frontend/src/shared/exportar.js` (`opcionesExportacion()` → menú de 3 formatos). CSV y Excel salen del mismo arreglo de filas; PDF abre una vista imprimible. Para un reporte muy extenso (más de ~5 000 filas) sólo se ofrece CSV.

**Sistema de diseño de referencia**: `.specify/memory/design-system.md` ("Nordic Abyssal & Amethyst Intelligence") define la paleta, tipografía, spacing, elevación, formas y componentes oficiales — ninguna spec define su propia paleta o estilo de componente. Las 3 pantallas de referencia en `docs/diseno-ui/` (Dashboard Ejecutivo, Inventario & Alertas FIFO, Punto de Venta) son el estándar visual a replicar fielmente en cada feature — no se rediseña de cero por spec.

**Navegación**: barra horizontal superior fija (no sidebar lateral), con categorías de primer nivel (ej. Dashboard, Punto de Venta, Inventario & FIFO, Catálogo, Clientes/CRM, Comercial, Finanzas & BI, Sistema, Soporte). Una categoría con 4 o más sub-opciones se despliega en un mega-menú agrupado por columnas temáticas (ej. "Sistema" → Seguridad / Configuración / Integraciones), usando el color primario Abyssal Emerald (`#0a3632`) para la barra y panel blanco para el desplegable. Una categoría con menos de 4 sub-opciones se lista directo sin agrupar en columnas.

## Stack y Restricciones Técnicas

- Infraestructura fija: Docker Desktop + Airflow (DAGs) como orquestador.
- Backend: FastAPI (Python) — REST/JSON, JWT sobre el RBAC de PostgreSQL.
- Frontend: Vue 3 + Vite + Tailwind + vue-echarts.
- Motores de datos: PostgreSQL 16 (operativo), MinIO (landing zone), ClickHouse (warehouse), pgAdmin (visualización).
- Modelo operativo: 50 tablas / 9 módulos ya validado (01_operativo_postgres.sql).
- Control de versiones: Git + GitHub, sin estándar de commits obligatorio.
- Pagos: Stripe (modo test/sandbox) para tarjeta débito/crédito; catálogo `medio_pago` incluye además Efectivo, Transferencia Bancaria y Billetera Digital (sin integración externa).
- Email transaccional: SendGrid (cupones, notificaciones, recuperación de contraseña).
- Facturación: PDF local vía `reportlab` — sin integración real con el SRI.
- Forecasting/ML: `scikit-learn` / `statsmodels` (librerías locales, no APIs externas).
- Imágenes de producto: bucket MinIO `producto-imagenes` (o URL directa de Open Food Facts cuando aplica) — nunca en disco local.
- Detalle completo de servicios externos y su justificación en `domain-context.md` sección 9.

## Flujo de Trabajo (Spec Kit)

Para cada una de las 12 features (001-core-ventas-inventario, 002-clientes-fidelizacion, 003-precios-margenes, 004-pronostico-demanda, 005-promociones-inteligentes, 006-caja-mermas-fraude, 007-pagos-seguridad, 008-auth-administracion-sistema, 009-dashboards-multinivel, 010-plataforma-datos-tactico-estrategico, 011-recursos-humanos, 012-traslados-stock-entre-tiendas): /speckit-specify → (opcional /speckit-clarify) → /speckit-plan → /speckit-tasks → (opcional /speckit-analyze) → /speckit-implement. Ninguna feature avanza a plan sin spec aprobado, ni a implement sin tasks aprobado. Las features 009 y 010 quedan especificadas pero no implementadas hasta retomar la capa táctica/estratégica (ClickHouse + Airflow), actualmente en pausa — 010 construye esa plataforma y 009 solo la consume para dashboards. 011 y 012 no tienen ninguna dependencia de 009/010 y no quedan en espera.

## Governance

Esta constitución tiene prioridad sobre cualquier spec individual. Un cambio aquí obliga a revisar las specs ya creadas que dependan del principio modificado. Toda spec/plan/tasks debe verificar cumplimiento de estos principios antes de pasar a la siguiente fase.

**Version**: 1.5.0 | **Ratified**: 2026-09-04 | **Last Amended**: 2026-09-09
