/** @type {import('tailwindcss').Config} */
// Paleta y escalas oficiales "Nordic Abyssal & Amethyst Intelligence"
// (.specify/memory/design-system.md — ninguna feature define su propio color, Principio XII).
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        // --- Superficies / neutros (frontmatter design-system.md) ---
        surface: '#f8f9fb',
        'surface-dim': '#d8dadc',
        'surface-bright': '#f8f9fb',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f2f4f6',
        'surface-container': '#eceef0',
        'surface-container-high': '#e6e8ea',
        'surface-container-highest': '#e0e3e5',
        'surface-variant': '#e0e3e5',
        'on-surface': '#191c1e',
        'on-surface-variant': '#414847',
        'inverse-surface': '#2d3133',
        'inverse-on-surface': '#eff1f3',
        outline: '#717977',
        'outline-variant': '#c0c8c6',
        'surface-tint': '#3e6561',
        background: '#f8f9fb',
        'on-background': '#191c1e',
        // --- Primary: Abyssal Emerald (navegación maestra, headers, triggers) ---
        //     (valores exactos de docs/diseno-ui/.../code.html tailwind.config)
        primary: '#0a3632',
        'primary-dark': '#05201d',
        'primary-hover': '#0f4742',
        'primary-light': '#155751',
        'on-primary': '#ffffff',
        'primary-container': '#0a3632',
        'on-primary-container': '#779f9a',
        'inverse-primary': '#a5cfc9',
        // Chrome del shell (barra de navegación maestra) — tonos de la referencia POS.
        'shell-bar': '#072623',
        'shell-inset': '#092e2a',
        'shell-line': '#154640',
        'shell-pill': '#0c3934',
        'shell-pill-line': '#1b5c53',
        'primary-fixed': '#c0ebe4',
        'primary-fixed-dim': '#a5cfc9',
        'on-primary-fixed': '#00201d',
        'on-primary-fixed-variant': '#254d49',
        // --- Secondary: Amethyst (IA / predictivo / VIP · tab de navegación activo) ---
        secondary: '#7c3aed',
        'secondary-subtle': '#8b5cf6', // fin del gradiente del tab activo (referencia POS)
        'secondary-light': '#f6f0ff', // fondo de ítem seleccionado en el mega-menú
        'on-secondary': '#ffffff',
        'secondary-container': '#8a4cfc',
        'on-secondary-container': '#fffbff',
        'on-secondary-strong': '#4c1d95', // texto de ítem seleccionado en el mega-menú
        'secondary-fixed': '#eaddff',
        'secondary-fixed-dim': '#d2bbff',
        'on-secondary-fixed': '#25005a',
        'on-secondary-fixed-variant': '#5a00c6',
        'orchid-soft': '#f3e8ff', // chips/pills de IA
        // --- Tertiary: Mint Vitality (positivos, metas, salud de stock) ---
        tertiary: '#059669',
        'on-tertiary': '#ffffff',
        'tertiary-container': '#003825',
        'on-tertiary-container': '#30ab7c',
        'tertiary-fixed': '#85f8c4',
        'tertiary-fixed-dim': '#68dba9',
        'on-tertiary-fixed': '#002114',
        'on-tertiary-fixed-variant': '#005137',
        // --- Semánticos de retail (design-system.md §Colors) ---
        'damask-amber': '#d97706', // alertas FIFO / vencimientos / rotación lenta
        'damask-amber-bright': '#f59e0b',
        'crimson-ruby': '#e11d48', // quiebres / mermas / anomalías críticas
        error: '#ba1a1a',
        'on-error': '#ffffff',
        'error-container': '#ffdad6',
        'on-error-container': '#93000a',
      },
      fontFamily: {
        // design-system.md §Typography: títulos = Plus Jakarta, datos/microcopy = Inter
        display: ['"Plus Jakarta Sans"', '"Inter"', 'system-ui', 'sans-serif'],
        sans: ['"Inter"', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        // design-system.md §Shapes (roundedness: 1)
        sm: '0.125rem',
        DEFAULT: '0.25rem',
        md: '0.375rem',
        lg: '0.5rem',
        xl: '0.75rem',
        full: '9999px',
      },
      boxShadow: {
        // design-system.md §Elevation & Depth
        'tier-1': '0 1px 2px rgba(10,54,50,0.03), 0 4px 12px rgba(10,54,50,0.04)',
        'tier-2': '0 4px 8px rgba(10,54,50,0.04), 0 16px 36px -4px rgba(10,54,50,0.08)',
        'tier-3': '0 0 0 1px rgba(124,58,237,0.12), 0 8px 24px -4px rgba(124,58,237,0.08)',
      },
    },
  },
  plugins: [],
}
