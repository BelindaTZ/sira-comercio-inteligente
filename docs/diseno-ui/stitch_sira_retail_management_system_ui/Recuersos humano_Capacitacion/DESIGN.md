---
name: Nordic Abyssal & Amethyst Intelligence
colors:
  surface: '#f8f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f8f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#414847'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#717977'
  outline-variant: '#c0c8c6'
  surface-tint: '#3e6561'
  primary: '#00201d'
  on-primary: '#ffffff'
  primary-container: '#0a3632'
  on-primary-container: '#779f9a'
  inverse-primary: '#a5cfc9'
  secondary: '#712ae2'
  on-secondary: '#ffffff'
  secondary-container: '#8a4cfc'
  on-secondary-container: '#fffbff'
  tertiary: '#002014'
  on-tertiary: '#ffffff'
  tertiary-container: '#003825'
  on-tertiary-container: '#30ab7c'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#c0ebe4'
  primary-fixed-dim: '#a5cfc9'
  on-primary-fixed: '#00201d'
  on-primary-fixed-variant: '#254d49'
  secondary-fixed: '#eaddff'
  secondary-fixed-dim: '#d2bbff'
  on-secondary-fixed: '#25005a'
  on-secondary-fixed-variant: '#5a00c6'
  tertiary-fixed: '#85f8c4'
  tertiary-fixed-dim: '#68dba9'
  on-tertiary-fixed: '#002114'
  on-tertiary-fixed-variant: '#005137'
  background: '#f8f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: plusJakartaSans
    fontSize: 40px
    fontWeight: '700'
    lineHeight: 48px
    letterSpacing: -0.025em
  headline-xl:
    fontFamily: plusJakartaSans
    fontSize: 30px
    fontWeight: '700'
    lineHeight: 38px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: plusJakartaSans
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.015em
  headline-md:
    fontFamily: plusJakartaSans
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: plusJakartaSans
    fontSize: 16px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  body-sm:
    fontFamily: inter
    fontSize: 13px
    fontWeight: '400'
    lineHeight: 18px
  tabular-metric:
    fontFamily: inter
    fontSize: 28px
    fontWeight: '600'
    lineHeight: 34px
    letterSpacing: -0.02em
  tabular-data:
    fontFamily: inter
    fontSize: 13px
    fontWeight: '500'
    lineHeight: 18px
  label-md:
    fontFamily: inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: inter
    fontSize: 11px
    fontWeight: '600'
    lineHeight: 14px
    letterSpacing: 0.04em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  space-2xs: 0.125rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 0.75rem
  space-base: 1rem
  space-lg: 1.5rem
  space-xl: 2rem
  space-2xl: 3rem
  gutter-mobile: 1rem
  gutter-desktop: 1.5rem
  sidebar-collapsed: 4.5rem
  sidebar-expanded: 16.5rem
---

## Brand & Style

This design system delivers an architectural, high-end enterprise retail experience designed for Marzú Retail Group. It deliberately rejects generic enterprise blues in favor of an authoritative Deep Abyssal Emerald paired with sharp Amethyst and soft orchid accents for algorithmic intelligence, predictive inventory, and high-value CRM insights.

The aesthetic fuses Apple-grade frosted glass minimalism with dense, disciplined Swiss data hierarchy. Interfaces must feel luminous, precise, and tranquil—evoking the surgical clarity of luxury retail operations rather than raw spreadsheet logistics. Every viewport balances generous pearlescent negative space with tightly structured tabular modules, crisp perimeter microrings, and atmospheric diffusion.

## Colors

The palette establishes an immediate distinction between standard operational mechanics and forward-looking retail intelligence:

- **Primary (`#0a3632` - Abyssal Emerald)**: Used for master navigation, core interactive triggers, anchor headers, and high-level platform status. Conveys longevity, authority, and financial solidity.
- **Secondary (`#7c3aed` - Amethyst)**: Dedicated exclusively to AI forecasting, predictive analytics, smart merchandising suggestions, and VIP clienteling metrics. Accompanied by **Orchid Soft (`#f3e8ff`)** for contextual chips, pill backgrounds, and micro-highlights.
- **Tertiary (`#059669` - Mint Vitality)**: Positives, target achievements, surplus, and prime inventory health.
- **Retail Semantic Warnings**:
  - **Damask Amber (`#d97706` / `#f59e0b`)**: FIFO alerts, impending batch expirations, slow-moving stock warnings.
  - **Crimson Ruby (`#e11d48`)**: Stockouts, shrinkages, critical shrink anomalies, cold-chain disruptions.
- **Surfaces & Glass**:
  - **Base Canvas**: Pearl Silk (`#f5f7f9`).
  - **Cards & Sheets**: Pure White (`#ffffff`) or Frosted Milk (`rgba(255, 255, 255, 0.78)`) overlaid with `backdrop-filter: blur(16px)`.
  - **Hairline Dividers & Microrings**: `rgba(10, 54, 50, 0.08)` and `rgba(15, 23, 42, 0.06)`. Never use harsh black borders.

## Typography

Typography pairs Plus Jakarta Sans for titles and structural identity with Inter for data density, microcopy, and tabular processing.

- All inventory metrics, cash flows, SKU volumes, and timestamps must activate OpenType tabular figures (`font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1, "cv05" 1`) to ensure strict column alignment in inventory matrices.
- Uppercase styling is reserved exclusively for micro-labels (`label-sm`), category badges, and SKU tags, always paired with expanded letter spacing (+0.04em) to prevent clutter.
- Maintain a minimum contrast ratio of 7:1 for body copy against light backgrounds by pairing neutral dark slate (`#1e293b`) against `#ffffff` and `#f5f7f9`.

## Layout & Spacing

The platform follows a responsive 12-column dynamic grid governed by an 8px rhythmic scale, shifting to an essential 4px step inside high-density data tables and toolbars.

- **Desktop (1280px+)**: Dual-pane or triple-pane operational cockpit. Primary left sidebar operates in either collapsed icon mode (72px) or full state (264px). Main stage uses fluid columns with 24px gutters and 32px external margins. Detail slide-over drawers anchor right at a fixed 480px width.
- **Tablet (768px - 1279px)**: Sidebar converts to a collapsed rail; metric cards collapse to 2-column or 3-column rows with 16px gutters.
- **Mobile (<768px)**: Single column reflow; tab bar navigation affixed to bottom; data grids switch to sticky-first-column scroll or structured card lists.
- Vertical density is strictly compartmentalized: KPI overview headers use generous padding (`space-xl`), while inventory log tables compress down to 36px/44px row heights with `space-sm` vertical cell padding.

## Elevation & Depth

Depth is articulated through translucency, layered diffusion, and subtle refraction rather than blunt, dark shadows.

- **Tier 0 (Base Canvas)**: Solid `#f5f7f9`. Flat, zero elevation.
- **Tier 1 (Surface Cards & Workspaces)**: Solid `#ffffff` or `rgba(255, 255, 255, 0.85)` with `backdrop-filter: blur(12px)`. Outlined with a 1px hairline border in `rgba(10, 54, 50, 0.07)`. Elevation is rendered using a subtle dual-layer shadow:
  `box-shadow: 0 1px 2px rgba(10, 54, 50, 0.03), 0 4px 12px rgba(10, 54, 50, 0.04);`
- **Tier 2 (Floating Modals & Flyout Sheets)**: Solid `#ffffff` or `rgba(255, 255, 255, 0.94)`. Perimeter border `rgba(10, 54, 50, 0.1)`. Shadow:
  `box-shadow: 0 4px 8px rgba(10, 54, 50, 0.04), 0 16px 36px -4px rgba(10, 54, 50, 0.08);`
- **Tier 3 (Predictive/Amethyst AI Accent Nodes)**: Specialized cards driven by smart retail engines carry an ambient violet glow underneath the card edge:
  `box-shadow: 0 0 0 1px rgba(124, 58, 237, 0.12), 0 8px 24px -4px rgba(124, 58, 237, 0.08);`

## Shapes

The design uses a restrained, modern architectural curvature (`roundedness: 1`). Enterprise tools handle dense transactional matrices, meaning excessive border radii waste valuable screen surface.

- **Primary Cards & Containers**: 8px (`rounded-lg`).
- **Buttons, Inputs, Metric Badges**: 6px.
- **Status Chips, Avatar Indicators, Micro-Pills**: Fully rounded pill shapes (`9999px`) to create clear contrast against the clean geometric grid of cards and tables.
- **Data Modals & Drawers**: 12px (`rounded-xl`) on exposed free corners.

## Components

### Buttons
- **Primary Operational**: Solid Abyssal Emerald (`#0a3632`), text `#ffffff`, 6px corner radius. Hover shifts to `#0e4a44` with a 1px translucent inner glow (`inset 0 1px 0 rgba(255, 255, 255, 0.2)`). Active state applies a subtle scale transition (`transform: scale(0.98)`).
- **AI / Predictive Action**: Solid Amethyst (`#7c3aed`), text `#ffffff`. Hover moves to `#6d28d9`. Used specifically for automated replenishment triggers, smart forecasting, or customer cluster generation.
- **Secondary / Ghost**: Background `rgba(255, 255, 255, 0.8)`, border 1px `rgba(10, 54, 50, 0.12)`, text `#0a3632`. Hover: background `#ffffff`, border `rgba(10, 54, 50, 0.25)`.

### Chips & Semantic Badges
- **FIFO / Expiration Alert**: Background `#fef3c7`, text `#b45309`, border 1px `rgba(217, 119, 6, 0.2)`.
- **Stockout / Shrinkage Risk**: Background `#ffe4e6`, text `#be123c`, border 1px `rgba(225, 29, 72, 0.2)`.
- **Healthy Stock / Target Met**: Background `#d1fae5`, text `#047857`, border 1px `rgba(5, 150, 105, 0.2)`.
- **Smart / AI Insight**: Background `#f3e8ff`, text `#6b21a8`, border 1px `rgba(124, 58, 237, 0.2)`.

### Form Fields & Inputs
- Standard height: 38px for dense enterprise entry, 44px for primary filter bars.
- Background: `#ffffff`. Border: 1px solid `rgba(15, 23, 42, 0.12)`. Text: `#0f172a`.
- Focus state: Border transitions to `#0a3632` accompanied by a smooth focus ring: `0 0 0 3px rgba(10, 54, 50, 0.1)`. For search boxes that query AI projections, the focus ring tint turns to `rgba(124, 58, 237, 0.15)`.

### Checkboxes & Radios
- Size: 16x16px. Border: 1.5px solid `rgba(10, 54, 50, 0.24)`.
- Checked state: Fill `#0a3632`, checkmark icon in pure white `#ffffff`.

### Data Grids & Tables
- Table headers: 36px height, uppercase `label-sm`, text color `#64748b`, background `#f8fafc`, bottom border 1px solid `rgba(10, 54, 50, 0.08)`.
- Rows: 44px height, background alternating or hover-highlighted with `rgba(10, 54, 50, 0.02)`. Divider 1px solid `rgba(15, 23, 42, 0.05)`. Tabular numeric values are right-aligned.

### Cards & KPI Tiles
- Card containers use frosted white or solid `#ffffff` with hairline borders.
- KPI layout: Top-anchored micro-label with auxiliary icon, followed by large tabular figure (`tabular-metric`), followed by a bottom trend indicator containing a semantic pill and comparative microcopy (e.g., "+12.4% vs last cycle").