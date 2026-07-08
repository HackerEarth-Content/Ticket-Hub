---
name: HE Helpdesk Dashboard
description: Live HubSpot support-ops dashboard for HackerEarth's helpdesk team
colors:
  accent-blue: "#0939e6"
  accent-indigo: "#5f59ff"
  accent-orange: "#ff5722"
  accent-aqua: "#1baf7a"
  accent-yellow: "#eda100"
  accent-green: "#008300"
  accent-red: "#e34948"
  accent-magenta: "#e87ba4"
  status-good: "#0ca30c"
  status-warning: "#fab219"
  status-serious: "#ec835a"
  status-critical: "#d03b3b"
  status-neutral: "#8a8f98"
  surface: "#ffffff"
  surface-2: "#f3f5f9"
  plane: "#f7f9fc"
  ink: "#020202"
  ink-2: "#545459"
  ink-3: "#898781"
  line: "#e3e6ed"
typography:
  title:
    fontFamily: "Inter Variable, ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif"
    fontSize: "21px"
    fontWeight: 650
    letterSpacing: "-0.015em"
  card-title:
    fontFamily: "{typography.title.fontFamily}"
    fontSize: "13.5px"
    fontWeight: 650
    letterSpacing: "-0.005em"
  body:
    fontFamily: "{typography.title.fontFamily}"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.45
  label:
    fontFamily: "{typography.title.fontFamily}"
    fontSize: "11.5px"
    fontWeight: 600
  stat-value:
    fontFamily: "JetBrains Mono Variable, ui-monospace, SF Mono, Cascadia Code, monospace"
    fontSize: "22px"
    fontWeight: 600
    letterSpacing: "-0.01em"
rounded:
  swatch: "2px"
  chip: "4px"
  skeleton: "6px"
  xs: "7px"
  sm: "8px"
  pill: "9px"
  md: "12px"
  full: "100px"
spacing:
  xs: "4px"
  sm: "10px"
  md: "14px"
  lg: "18px"
  xl: "24px"
components:
  card:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "18px 18px 16px"
  card-hover:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
  stat-tile:
    backgroundColor: "{colors.surface}"
    rounded: "{rounded.md}"
    padding: "13px 14px"
  tab-active:
    textColor: "{colors.ink}"
  period-pill-active:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
---

# Design System: HE Helpdesk Dashboard

## 1. Overview

**Creative North Star: "The Control Room"**

This is the instrument panel a support lead glances at between tickets, not
a page anyone lingers on for its own sake. Every surface is built to answer
one question fast: tabular numbers align in mono type so magnitudes compare
at a glance, a single fixed 8-hue accent system (lifted directly from
HackerEarth's production brand CSS, not invented for this project) carries
identity across every chart without ever being reassigned by value, and a
near-flat shadow system gives just enough lift to separate a card from the
page — never enough to feel decorative. Dark mode is a first-class target,
not an afterthought filter: every token has a confirmed dark counterpart.

This system explicitly rejects the generic-admin-template look (boxy,
low-density, dated) and anything that trades clarity for flourish —
gradients, glassmorphism, or chrome that competes with the data it's
supposed to be presenting. Where the dashboard is honest about gaps in the
underlying data (a CSAT response that couldn't be matched to a ticket, a
priority that had to be inferred), that honesty is a design feature, not a
rough edge to hide.

**Key Characteristics:**
- Fixed categorical color order, never cycled, never value-dependent
- Tabular-numeral mono type for every metric that gets scanned/compared
- Near-flat elevation: a hairline border does most of the separation work,
  shadow is a light assist
- Sharp corners kept soft (8–12px), never fully squared, never pill-heavy
- Dense but airy: 14px base gap, generous internal card padding relative to
  its border weight

## 2. Colors

The palette is not composed for this project — it's inherited verbatim from
HackerEarth's own production brand CSS, which is why it reads as confident
rather than generated: these are colors a real design team already chose.

### Primary
- **Signal Blue** (`#0939e6`, dark: `#3987e5`): the interactive/action color
  — focus rings, links, the active period-selector pill's accent underline,
  first slot in every categorical sequence.

### Secondary / Categorical set
Assigned in this fixed order and never reshuffled — position 1 is always
Signal Blue, position 2 is always Aqua, and so on, across every chart in the
product (module distribution, source distribution, reporter pie, customer
breakdowns):
1. **Signal Blue** (`#0939e6`)
2. **Aqua** (`#1baf7a`) — the "created vs. resolved" secondary series color
3. **Amber** (`#eda100`)
4. **Forest Green** (`#008300`)
5. **Indigo** (`#5f59ff`)
6. **Red** (`#e34948`) — reserved for categorical position 6, distinct from
   Status Critical below; don't reuse it as a status color
7. **Magenta** (`#e87ba4`) — also the Service Health section's heading accent
8. **Orange** (`#ff5722`) — also the Backline Operations section's accent

### Status (reserved, never reused as categorical)
- **Good** (`#0ca30c`): live-sync dot, healthy values.
- **Warning** (`#fab219`): stale sync, approaching-threshold values.
- **Serious** (`#ec835a`): elevated live-wait chips (24–48h).
- **Critical** (`#d03b3b`): SLA breach, live-wait > 48h, error banners.
- **Neutral** (`#8a8f98`): unassigned/unknown states.

### Neutral
- **Ink** (`#020202` / dark `#ffffff`): primary text.
- **Ink-2** (`#545459` / dark `#c3c2b7`): secondary text, active nav labels.
- **Ink-3** (`#898781` / dark `#8a8f98`): tertiary text, card subtitles, chart
  ticks — the most-used neutral in the system.
- **Surface** (`#ffffff` / dark `#18181b`): card background.
- **Surface-2** (`#f3f5f9` / dark `#1f2027`): the page's own background is
  actually one step further out (`--plane`); surface-2 sits between plane
  and surface for toolbars, pills, table hover.
- **Plane** (`#f7f9fc` / dark `#020109`): the page background beneath every
  card.
- **Line** (`#e3e6ed` / dark `#2c2c33`): every hairline border in the system.

### Named Rules
**The Fixed-Slot Rule.** Categorical color is assigned by array position at
render time, computed from a stable sort (usually volume descending), never
by a value-to-color hash. Two charts showing the same category must show it
in the same color only if that category happens to land in the same sorted
position — the rule is positional stability within one chart's own render,
not cross-chart identity binding.

**The Reserved Status Rule.** The five `--status-*` tokens never appear in a
categorical sequence and the eight categorical accents never carry
state/severity meaning. `--accent-red` (categorical slot 6) and
`--status-critical` are visually close but semantically separate — an SLA
breach is always `--status-critical`, never `--accent-red`, even though a
chart legend might independently use `--accent-red` for an unrelated series.

## 3. Typography

**Body/UI Font:** Inter Variable (with `ui-sans-serif, system-ui,
-apple-system, "Segoe UI", sans-serif`)
**Numeric/Mono Font:** JetBrains Mono Variable (with `ui-monospace, "SF
Mono", "Cascadia Code", monospace`)

**Character:** One geometric-humanist sans for everything a person reads as
language, one monospace for everything a person reads as a number to
compare against another number. The pairing exists to make scanning a table
of stat tiles fast, not for typographic flourish — there is no display/serif
layer in this system at all, deliberately: nothing here is a headline
moment.

### Hierarchy
- **Title** (650, 21px, `-0.015em` tracking): the single `<h1>` in the app
  header. Appears once per page load.
- **Card title** (650, 13.5px, `-0.005em`): every card/table's own heading —
  this is the true "headline" density of the product, repeated dozens of
  times per screen.
- **Body** (400, 14px, 1.45 line-height): default text color and size for
  the whole document; most UI text never overrides this.
- **Card sub / label** (600, 11.5px, `ink-3`): card subtitles, stat-tile
  labels, chart axis ticks (at 11px). The most-repeated text style in the
  system.
- **Stat value** (mono, 600, 22px, `-0.01em`, `tabular-nums`): the one place
  size jumps up — a KPI number inside a stat tile. Always mono, always
  tabular, so a column of stat tiles aligns digit-for-digit.
- **Table numeric cell** (mono, 12px, `tabular-nums`, right-aligned): every
  `<td class="num">` in every table.

### Named Rules
**The Tabular Rule.** Any number that will ever sit near another comparable
number — a stat tile, a table column, a chart tick — renders in
`--font-mono` with `font-variant-numeric: tabular-nums`. Prose numbers
(a sentence like "24 tickets today") stay in the body sans.

## 4. Elevation

Flat by default, lifted only on hover. Cards and stat tiles carry a
two-layer ambient shadow (`--shadow`) that's barely perceptible at rest — a
1px hairline border (`--line`) does most of the actual separation from the
page background. On hover, cards get a stronger shadow (`--shadow-hover`)
plus a 1px upward `translateY`, signaling interactivity without a color
change. There is no "raised" resting state anywhere in the system; a card
that looks lifted at rest would compete with the one thing that's actually
supposed to draw the eye — the data.

### Shadow Vocabulary
- **Ambient** (`0 1px 2px rgba(20,24,38,.05), 0 6px 16px -8px rgba(20,24,38,.08)`
  — dark: `0 1px 2px rgba(0,0,0,.35), 0 6px 20px -8px rgba(0,0,0,.45)`): the
  resting shadow for every `.card` and `.stat`.
- **Hover** (`0 2px 4px rgba(20,24,38,.06), 0 14px 28px -10px rgba(20,24,38,.14)`
  — dark: `0 2px 4px rgba(0,0,0,.4), 0 16px 32px -10px rgba(0,0,0,.55)`):
  triggered on `.card:hover`, paired with `transform: translateY(-1px)`.
- **Popover** (`0 8px 24px rgba(20,24,38,.14)`): the custom date-range picker
  — the one floating/overlay element in the system, needs more separation
  than a hovered card since it sits above other content, not just lifted
  off the page.
- **Tooltip** (`0 4px 16px rgba(20,24,38,.12)`): `.chart-tooltip`, every
  Recharts hover tooltip in the system — lighter than Popover since it
  tracks the pointer rather than sitting fixed above content.

### Named Rules
**The Border-Does-The-Work Rule.** Shadow is an assist, not the primary
separator. If `--line` were removed, cards would nearly disappear at rest —
that's intentional; the ambient shadow alone is not meant to carry
separation on its own.

## 5. Components

### Buttons
- **Shape:** 7–9px radius depending on context (period pills use 7px inner /
  9px outer; icon buttons use 9px).
- **Primary (period-pill active / apply-btn):** `--accent-blue` background
  (apply-btn) or `--surface` background with `--shadow` (active period
  pill) — two different "primary" treatments depending on whether the
  button sits inside a segmented control (period pills: white-on-selected)
  or stands alone (apply: blue-on-white).
- **Ghost (icon-btn, table-toggle):** transparent/surface-2 background,
  `--ink-2` text, no border emphasis until hover.
- **Hover / Focus:** ghost buttons darken text to `--ink`; bordered buttons
  (sign-in) tint their border toward `--accent-blue` at 40% and pick up
  `--shadow`. Focus-visible everywhere gets a 2px `--accent-blue` outline,
  2px offset, 4px radius — never removed, never replaced with a box-shadow
  substitute.

### Cards / Containers
- **Corner Style:** 12px (`--radius`), the system's one card radius.
- **Background:** `--surface`, always — cards never sit at `--surface-2`;
  that tone is reserved for toolbars/pills/hover states one level down from
  a card.
- **Shadow Strategy:** see Elevation — ambient at rest, hover lift on
  interactive cards only (module/status distribution cards with
  drill-downs).
- **Border:** 1px `--line`, always present, doing most of the visual
  separation.
- **Internal Padding:** `18px 18px 16px` — slightly less at the bottom to
  balance the `card-head`'s own `margin-bottom: 14px`.

### Tabs (signature component)
- **Style:** underline-indicator tabs, not filled/pill tabs. Each tab
  carries its own `--tab-accent` custom property (set inline per tab,
  matching that section's heading color elsewhere in the app), so the
  active underline color changes per section rather than using one fixed
  accent for all tabs.
- **Default:** `--ink-3` text, transparent underline.
- **Active:** `--ink` text (label), underline fills with `--tab-accent`, the
  tab's own subtitle line tints toward `--tab-accent` at 75%.
- **Hover (inactive):** text steps up one shade to `--ink-2`; no underline
  preview.

### Stat Tiles
- **Corner Style:** 12px, same as cards — a stat tile is a card, just
  smaller and metric-first.
- **Layout:** label (11.5px, `--ink-3`) above value (22px mono, `--ink`)
  above an optional foot note (11px, `--ink-3`); an optional inline `.unit`
  span rides next to the value at 13px.
- **State color:** value text can override to `--status-good` or
  `--status-critical` (`.value.warn` / `.value.good`) when the metric itself
  is a pass/fail signal (e.g. SLA breach count) — the only place text color
  substitutes for the neutral ink default.

### Chips
- Small pill badges (status dots + label) used for sync freshness and live
  chip states — 3px/8px padding, `--status-good`/`--status-warning` dot,
  never a chip without an accompanying text label (color alone never carries
  the state).

### Tables
- Hairline row dividers (`--line`), no zebra striping. Row hover tints to
  `--surface-2`. Numeric columns are right-aligned and mono (see Typography
  → The Tabular Rule). Header cells are 10.5px uppercase `--ink-3` with
  0.05em tracking — the one place in the system that uses an uppercase
  label style, reserved for table headers only.

### Charts (Recharts-based)
- **Categorical charts** (pie, bar-list distributions): fixed 8-slot
  accent order (see Colors → The Fixed-Slot Rule), 2px surface-color gap
  between adjacent segments/bars, tail beyond 8 categories folds into a
  single "Other" slice/bar rather than generating a 9th hue.
- **Trend charts** (area/line): 2px stroke, ~16% fill opacity gradient
  fading to 0%, Y-axis domain always anchored at literal `0` (never
  `"auto"` on both ends) to prevent axis ticks from drifting negative on
  small-magnitude data.
- **Tooltips:** `--surface` background, `--line` border, `--radius-sm`
  (9px in practice via `.chart-tooltip`) corners, a floating shadow
  distinct from the card-hover shadow. Value leads in `--ink` bold; series
  name/swatch follows, never the reverse.

## 6. Do's and Don'ts

### Do:
- **Do** assign categorical color by fixed array position (blue → aqua →
  amber → green → indigo → red → magenta → orange), every time, across
  every chart.
- **Do** render every comparable number — stat tiles, table numeric
  columns, chart ticks — in `--font-mono` with `tabular-nums`.
- **Do** anchor every Y-axis at literal `0`; never let both ends of a
  numeric domain read `"auto"`.
- **Do** surface data-quality caveats in the UI itself (an "unmatched"
  count, a "no linked contact" note) rather than hiding them for visual
  cleanliness — this is a stated product principle, not just a style choice.
- **Do** keep dark mode a fully specified peer of light mode, not a filter —
  every token pair (light/dark) is defined explicitly in `theme.css`.

### Don't:
- **Don't** use generic Bootstrap-admin-template styling — boxy corners,
  low information density, dated shadows. (PRODUCT.md anti-reference.)
- **Don't** use decorative gradients, glassmorphism, or gradient text
  anywhere in the product. (PRODUCT.md anti-reference — this is an ops
  tool, not a marketing page.)
- **Don't** fold more than 8 categories into a single chart by generating a
  9th hue — fold the tail into "Other" instead.
- **Don't** reuse a `--status-*` color as a categorical series color, or
  vice versa — they're visually adjacent (`--accent-red` /
  `--status-critical`) on purpose but must stay semantically separate.
- **Don't** give a card or stat tile a "raised" resting shadow — elevation
  only increases on hover, never at rest.
- **Don't** hide a chart legend for 2+ series, even in a tight card — color
  is never the only way to distinguish categories.
