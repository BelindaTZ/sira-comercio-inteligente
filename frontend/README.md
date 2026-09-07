# SIRA — Frontend (SPA)

Vue 3 + Vite + Pinia + Vue Router + Tailwind CSS + vue-echarts.

## Puesta en marcha

```bash
cd frontend
npm install
cp .env.example .env      # VITE_API_BASE_URL, VITE_STRIPE_PUBLISHABLE_KEY
npm run dev               # http://localhost:5173  (proxy /api → :8000)
```

Scripts: `npm run build`, `npm run test` (Vitest), `npm run lint`, `npm run format`.

## Convenciones

- Sin lógica de negocio (Principio V): la SPA solo presenta y consume la API.
- Toda llamada HTTP pasa por `src/services/*Api.js` (Principio XI) — nunca `axios` suelto en un componente.
- Componentes + composables. Listados: `DataTable.vue` + `usePaginacion.js`; filtros: `useFiltrosReactivos.js` (reactivos, sin botón "Buscar" — Principio XII).
- Paleta/tipografía: `tailwind.config.js` traduce `design-system.md` ("Nordic Abyssal & Amethyst Intelligence"). Ninguna vista define su propio color.

## Estructura

| Carpeta | Contenido |
|---|---|
| `src/core/` | composables transversales (`usePaginacion`, `useFiltrosReactivos`) |
| `src/shared/` | componentes genéricos (`DataTable`, `WorkPanel`) |
| `src/services/` | capa centralizada de llamadas a la API |
| `src/modules/` | un paquete por módulo (`pos`, `inventario`, `catalogo`, `compras`) |
| `src/router/` | router principal |
