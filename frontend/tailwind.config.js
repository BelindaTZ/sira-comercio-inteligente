/** @type {import('tailwindcss').Config} */
// Paleta oficial "Nordic Abyssal & Amethyst Intelligence"
// (.specify/memory/design-system.md — ninguna feature define su propio color, Principio XII)
export default {
  content: ['./index.html', './src/**/*.{vue,js}'],
  theme: {
    extend: {
      colors: {
        surface: '#f8f9fb',
        'surface-dim': '#d8dadc',
        'surface-container-lowest': '#ffffff',
        'surface-container-low': '#f2f4f6',
        'surface-container': '#eceef0',
        'surface-container-high': '#e6e8ea',
        'surface-container-highest': '#e0e3e5',
        'on-surface': '#191c1e',
        'on-surface-variant': '#414847',
        outline: '#717977',
        'outline-variant': '#c0c8c6',
        primary: '#00201d',
        'on-primary': '#ffffff',
        'primary-container': '#0a3632',
        'on-primary-container': '#779f9a',
        'inverse-primary': '#a5cfc9',
        secondary: '#712ae2',
        'on-secondary': '#ffffff',
        'secondary-container': '#8a4cfc',
        'tertiary-container': '#003825',
        'on-tertiary-container': '#30ab7c',
        error: '#ba1a1a',
        'on-error': '#ffffff',
        'error-container': '#ffdad6',
        'on-error-container': '#93000a',
        background: '#f8f9fb',
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans"', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
