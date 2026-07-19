# Sistema de diseño — Portal del socio

> **Fuente:** valores extraídos por muestreo de píxeles directamente de los mockups en `docs/Diseño Preliminar.docx` (pantallas Dashboard, Workouts, Classes, Achievements, Account, Staff Portal). No son colores inventados ni aproximados a ojo — donde el valor es exacto se indica; donde es una lectura de texto con antialiasing (y por tanto una aproximación razonable, no un hex certero) se marca explícitamente como **aprox.**
>
> Aplica al **portal del socio** (web, con login). El kiosko táctil y el backoffice mantienen sus propias reglas de `tech-stack.md` (alto contraste / denso en tablas) y no necesitan adoptar esta paleta si no aplica.

## Paleta de color

### Primario

| Token | Hex | Uso |
|---|---|---|
| `navy-900` | `#1c294c` | Sidebar, logo, ítem de navegación activo, texto de marca |
| `navy-700` | `#3d4a68` | Encabezados de página (h1/h2) |

### Acento / estado (colores de las 4 stat cards del Dashboard)

| Token | Hex | Uso |
|---|---|---|
| `success-500` (verde-teal) | `#24c19f` | Card "Total Workouts", barra de progreso llena, badges "Unlocked" |
| `success-600` | `#00b78f` | Variante de barra de progreso (ligeramente más oscura que la card) |
| `warning-500` (naranja) | `#d5541c` | Card "Hours Trained", barra de progreso naranja |
| `accent-yellow` | `#e6e92b` | Card "Current Streak" |
| `accent-purple` | `#cd80e8` | Card "Weekly Goal" |

### Tints suaves (fondos de badges/pills — no usar los acentos sólidos como fondo de texto)

| Token | Hex | Uso |
|---|---|---|
| `purple-tint` | `#ece0f4` | Fondo de pill "95% match" (Classes) |
| `orange-tint` | `#f8dfd0` | Fondo de pill "88% match" |
| `yellow-tint` | `#fdffd8` / `#f9fcd2` | Fondo de pill "82% match" / ícono "Early Bird" |
| `teal-solid-badge` | `#50cfb4` | Pill "Premium Member" (Account) — este sí es sólido, no tint |

### Neutrales

| Token | Hex | Uso |
|---|---|---|
| `bg-page` | `#f5f6fb` | Fondo general de la página (fuera de las cards) |
| `bg-card` | `#ffffff` | Fondo de cards y sidebar |
| `text-heading` | `#3d4a68` | Títulos |
| `text-muted` | `#5a5570` *(aprox.)* | Subtítulos y texto secundario ("Track your fitness journey", "Welcome, Alex") |

### Sin dato en los mockups (resueltos por el equipo, 2026-07-11)

- **Rojo/error** — ninguna de las 8 pantallas muestra un estado de error o denegación en el portal del socio. **Resuelto:** se adopta el `red-600` estándar de Tailwind (`#dc2626`) como token `--color-member-error`, para credenciales inválidas, activación fallida, sesión expirada, etc.
- **Tipografía exacta** — no se puede extraer el nombre de la fuente desde una imagen rasterizada. **Resuelto:** se adopta `system-ui` (stack del sistema): cero dependencias nuevas, sin descargas externas (el kiosko debe funcionar sin internet) y visualmente consistente con el mockup. Es lo que ya usa el resto del frontend.

## Componentes recurrentes observados

- **Stat card:** fondo de color sólido (uno de los 4 acentos), esquinas redondeadas grandes (~`rounded-xl`/16px), ícono en la esquina superior derecha, número grande en negrita, texto pequeño de contexto debajo (ej. "+8 this week").
- **Card blanca de contenido:** fondo `bg-card`, borde sutil o sombra suave, esquinas redondeadas (~`rounded-lg`), padding generoso.
- **Barra de progreso:** track gris claro, relleno de color sólido según el contexto (verde para "on track", naranja para calorías, etc.), esquinas totalmente redondeadas (`rounded-full`).
- **Sidebar:** fondo blanco, ítem activo con fondo `navy-900` sólido y texto blanco, ítems inactivos con ícono + texto en gris oscuro.
- **Pill/badge:** fondo tint suave del color de acento correspondiente, texto del mismo tono pero más oscuro/saturado, esquinas totalmente redondeadas, padding pequeño.

## Tokens Tailwind (v4 — sintaxis CSS-first, no `tailwind.config.js`)

Tailwind v4 ya no usa `tailwind.config.js` para esto por defecto — los tokens se declaran directo en el CSS de entrada (`src/index.css`) dentro de un bloque `@theme`, y Tailwind genera las utilidades solo (`--color-member-navy` → clases `bg-member-navy`, `text-member-navy`, `border-member-navy`, etc.):

```css
@import "tailwindcss";

@theme {
  --color-member-navy: #1c294c;
  --color-member-navy-text: #3d4a68;
  --color-member-success: #24c19f;
  --color-member-success-dark: #00b78f;
  --color-member-warning: #d5541c;
  --color-member-yellow: #e6e92b;
  --color-member-purple: #cd80e8;
  --color-member-bg: #f5f6fb;
  --color-member-muted: #5a5570;

  --radius-card: 1rem;
}
```

Y en `vite.config.ts`, el plugin oficial en vez de PostCSS + `tailwind.config.js`:

```ts
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

**Duda abierta:** confirmar con el equipo si el kiosko/backoffice deben compartir estos tokens o si cada superficie mantiene su propia paleta (la constitución actual no fuerza unificación, solo dice que el backoffice "puede ser más denso").
