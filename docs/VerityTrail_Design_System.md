# VerityTrail Design System (v1.0)

**For:** Taiwo's AI coding agent, and any human building the VerityTrail frontend.
**Companion to:** `VerityTrail_Frontend_Supabase_Guide.md`. That guide defines behaviour, data and copy. This file defines **how everything looks and feels**: tokens, components, states, layouts, print styles.
**Rule of precedence:** if this file and the guide disagree about *copy strings, data, or behaviour*, the guide wins. If they disagree about *appearance*, this file wins. Record any conflict in `docs/DECISIONS.md`.

---

## 0. How to use this file (read first, agent)

1. Build **tokens first** (Section 3), then **primitives** (Section 6), then **domain components** (Section 7), then **screens** (Section 8). Do not hard-code a hex value, pixel size, shadow or duration in a component. Every visual value comes from a token.
2. Every colour pair in Section 3.1 has a **measured contrast ratio**. Add the contrast unit test in Section 12 in the first commit that adds tokens. Never "eyeball" a new colour. If you need one that is not here, add it to the token file, add it to the test, and note it in `docs/DECISIONS.md`.
3. **Never communicate meaning with colour alone.** Every colour that carries meaning (removed, added, matched, priority, status, confidence, review state) also carries a **text label and an icon**. This is a product requirement (NFR04), not a style preference.
4. **Use the exact copy strings** from guide Section 2.3 (`src/lib/copy.ts`). This file never overrides them.
5. Mobile first. The primary audience uses mid-range Android phones, often outdoors, often on slow connections. Design the 360 px layout first and enhance upward.
6. When a component here lists states (default, hover, focus-visible, active, disabled, loading, error, selected), build **all** of them. A component with missing states is not done.

---

## 1. Design intent

### 1.1 Who and what
VerityTrail helps civic groups, media houses and election observers in Nigeria see exactly what changed between two versions of an election-related notice, find where their own materials still repeat the old wording, and record a human decision with evidence attached.

The screen the product lives or dies on is the **evidence view**: old wording, new wording, the affected passage, side by side, exact and quotable.

### 1.2 The one memorable idea: "the ledger"
The interface should feel like a **careful reviewer's working paper**: calm, exact, annotated. Quoted source text looks like a document (serif, generous leading, quiet page-like surface). Everything that is *the tool talking* (labels, buttons, AI drafts, status) is sans-serif and visually separate. A reader must be able to tell at a glance: **"this is the document's text"** versus **"this is the tool's commentary"**.

That separation is the signature. Spend boldness there. Keep everything else quiet.

### 1.3 Principles
| # | Principle | What it means in practice |
|---|---|---|
| P1 | **Evidence over decoration** | No gradients, no illustrations, no hero art. Structure (borders, labels, spacing) exists to explain content. |
| P2 | **Neutral, never official** | No flag colours as stripes, no seals, no coats of arms, no INEC-style marks. Green is a restrained brand colour, never a "verified" colour. Nothing may suggest institutional endorsement. |
| P3 | **Text carries meaning, colour supports it** | Added / Removed / Changed, High / Normal, Ready / Failed are always words plus an icon. Colour reinforces; it never replaces. |
| P4 | **Source text and tool text look different** | Serif for quoted document text. Sans for UI. Violet dashed block for AI. Magenta for demo data. |
| P5 | **Quiet by default** | One saturated thing per area. Diff marks are the only strong colours on the evidence screen. |
| P6 | **Readable in sunlight on a cheap phone** | 16 px body minimum, high contrast, 44 px touch targets, no pale-on-pale pairs. |
| P7 | **Honest states** | Loading, queued, partial, failed, empty and "no matches" each have their own distinct design. Never a spinner that hides a failure. Never "all current". |
| P8 | **Sentence case, plain words** | No ALL-CAPS labels, no tracked-out eyebrows, no decorative arrows on buttons, no middle-dot meta strings. Name things the way a civic-group volunteer would. |

### 1.4 Things this system deliberately avoids
- Cream backgrounds with terracotta accents, near-black with acid accents, newspaper hairline layouts (generic "AI design" looks).
- Identical rounded cards with the same grey shadow on everything. Radius and shadow here **scale with the element's importance** (Sections 3.6 and 3.7).
- Fade-and-slide-up entrances on sections, hover lift on every card. Motion only answers a user action (Section 3.10).
- Green or red meaning "good" or "bad". Nothing in this tool judges a document good or bad.
- Green, white, green stripe patterns anywhere (flag association).
- Monospace for decoration. Mono is used **only** for hashes and IDs, where character alignment matters.

---

## 2. Brand

### 2.1 Wordmark
- Text: **VerityTrail** (one word, capital V and T, no space).
- Font: Inter, weight 600, size 20/24, letter-spacing `-0.01em`.
- Colour: `#FFFFFF` on the brand header. On white surfaces (export, login card): `--color-brand-800`.
- Never a logo lockup with a flag, seal, shield, map of Nigeria, ballot box or check mark.

### 2.2 Optional glyph (the "diff mark")
A 20 × 20 SVG shown left of the wordmark with 8 px gap. Two horizontal bars, offset, representing old and new:
```svg
<svg width="20" height="20" viewBox="0 0 20 20" fill="none" aria-hidden="true">
  <rect x="1.5" y="4.5" width="13" height="4" rx="1" stroke="currentColor" stroke-width="1.5"/>
  <rect x="5.5" y="11.5" width="13" height="4" rx="1" fill="currentColor"/>
</svg>
```
`currentColor` = white on the header. If the glyph is not wanted, ship the wordmark only. The glyph is decorative, always `aria-hidden`.

### 2.3 Favicon and metadata
- Favicon: the glyph, white on `#0B4A36`, 32 × 32 rounded square (radius 6).
- `theme-color` meta: `#0B4A36`.
- `<title>` template: `"%s · VerityTrail"` (the guide requires this exact template).

### 2.4 Brand voice (for any copy you must write)
Plain verbs, sentence case, active voice. A button says what it does ("Compare versions", "Save decision"), never "Submit". Errors say what happened and how to fix it, with no apology and no blame. Never say "latest official version" or "all materials are current". Never imply legal authority.

---

## 3. Foundations (tokens)

All tokens are CSS custom properties in `src/styles/tokens.css`, surfaced to Tailwind in `tailwind.config.ts` (Section 4). Naming: `--color-<role>-<step>` for scales, `--color-<semantic>` for roles.

### 3.1 Colour

#### 3.1.1 Neutral scale ("ink")
Cool slate. Used for text, borders, surfaces.

| Token | Hex | Use |
|---|---|---|
| `--color-ink-50` | `#F8FAFC` | App canvas (page background) |
| `--color-ink-100` | `#F1F5F9` | Sunken surfaces, table headers, code/hash backgrounds |
| `--color-ink-200` | `#E2E8F0` | Dividers, disabled backgrounds, progress track |
| `--color-ink-300` | `#CBD5E1` | Card borders, decorative separators (**not** control borders) |
| `--color-ink-400` | `#94A3B8` | Decorative icons only. **Never text, never control borders.** |
| `--color-ink-500` | `#64748B` | **Control borders** (inputs, checkboxes), placeholder text (on white or canvas only) |
| `--color-ink-600` | `#5B6B80` | Tertiary text (hints, timestamps) |
| `--color-ink-700` | `#475569` | Secondary text, "Normal" priority badge, icon default |
| `--color-ink-800` | `#334155` | Strong secondary text, hover borders |
| `--color-ink-900` | `#111827` | Primary text, tooltips |
| `--color-white` | `#FFFFFF` | Card/surface background |

#### 3.1.2 Brand scale (deep forest green)
Restrained. Header, primary buttons, links, selected-row tint. **Never** a "good / verified / approved" signal.

| Token | Hex | Use |
|---|---|---|
| `--color-brand-50` | `#ECF3EF` | Selected row, brand-tint banners, hover on ghost button |
| `--color-brand-100` | `#D5E6DC` | Header text on brand, active tint, grid "ok" border |
| `--color-brand-200` | `#B3D1C0` | Muted text/icons on brand header, tag borders |
| `--color-brand-300` | `#8DB8A0` | Reserved. Not used in UI v1. |
| `--color-brand-400` | `#5E9A7C` | Reserved. Not used in UI v1. |
| `--color-brand-500` | `#2F7A5C` | Reserved. Not used in UI v1. |
| `--color-brand-600` | `#1A6A4E` | Reserved. Not used in UI v1. |
| `--color-brand-700` | `#0F5F46` | Header nav hover, primary button hover alt |
| `--color-brand-800` | `#0B4A36` | **Primary brand**: header, primary button, links |
| `--color-brand-900` | `#073426` | Primary button hover and pressed |
| `--color-brand-950` | `#04221A` | Primary button active (pressed) |

#### 3.1.3 Semantic surface and text roles
| Token | Value | Use |
|---|---|---|
| `--color-canvas` | `ink-50` | `<body>` background |
| `--color-surface` | `white` | Cards, dialogs, inputs |
| `--color-surface-sunken` | `ink-100` | Table header, inset blocks, hash pills |
| `--color-surface-evidence` | `#FFFFFF` | Evidence text panes (a "page" in the ledger) |
| `--color-text` | `ink-900` | Primary text |
| `--color-text-secondary` | `ink-700` | Secondary text |
| `--color-text-tertiary` | `ink-600` | Hints, timestamps, captions |
| `--color-text-on-brand` | `white` | Text on brand-800/900 |
| `--color-text-link` | `brand-800` | Links (always underlined, see 3.2.5) |
| `--color-border` | `ink-300` | Card and section borders (decorative) |
| `--color-border-control` | `ink-500` | Inputs, checkboxes, radios, dropzone, secondary buttons |
| `--color-border-control-hover` | `ink-700` | Hover state for control borders |
| `--color-overlay` | `rgba(15, 23, 42, 0.55)` | Dialog and drawer scrim |

#### 3.1.4 Diff and evidence colours
Used **only** inside `DiffText`, `ChangeTypeLabel`, evidence panes and the export brief. Red/blue (not red/green) for colour-blind safety, and so green stays brand-only.

| Token | Hex | Role | Text treatment (always in addition to colour) |
|---|---|---|---|
| `--color-removed-fg` | `#B91C1C` | Removed/old text | **bold + line-through** + hidden "[removed: …]" |
| `--color-removed-bg` | `#FEE2E2` | Removed/old background | |
| `--color-removed-border` | `#FCA5A5` | Decorative edge | |
| `--color-added-fg` | `#1D4ED8` | Added/new text | **bold + solid underline** + hidden "[added: …]" |
| `--color-added-bg` | `#DBEAFE` | Added/new background | |
| `--color-added-border` | `#93C5FD` | Decorative edge | |
| `--color-matched-fg` | `#92400E` | Matched passage terms | **dotted underline** + hidden "[matched: …]" |
| `--color-matched-bg` | `#FEF3C7` | Matched background | |
| `--color-matched-border` | `#FCD34D` | Decorative edge | |
| `--color-moved-fg` | `#334155` | Moved text (change flagged `moved`) | **dashed underline** + chip "Moved" |
| `--color-moved-bg` | `#E2E8F0` | | |

#### 3.1.5 Priority
| Token | Hex | Use |
|---|---|---|
| `--color-priority-high-bg` | `#9A3412` | "High" badge fill (white text) |
| `--color-priority-high-fg` | `#FFFFFF` | |
| `--color-priority-high-tint` | `#FFEDD5` | Row tint for a high-priority group header (optional) |
| `--color-priority-high-tint-fg` | `#9A3412` | Text on the tint |
| `--color-priority-normal-fg` | `ink-700` | "Normal" badge text and border |

High is **orange**, not red, because red already means "removed" on this screen.

#### 3.1.4b Confidence bands
| Band | Bg | Text | Icon | Label |
|---|---|---|---|---|
| `strong` | `#ECF3EF` | `#0B4A36` | `SignalHigh` | "Strong match" |
| `likely` | `#E8EEF7` | `#1E3A5F` | `SignalMedium` | "Likely match" |
| `uncertain` | `#FEF3C7` | `#92400E` | `SignalLow` | "Uncertain match — review carefully" |

Border = 1px solid, same hue as text at about 30% (use the exact hexes in the token file: strong `#B3D1C0`, likely `#B7C6DE`, uncertain `#FCD34D`).

#### 3.1.5b Feedback (status) colours
| Role | Fg | Bg | Border (≥ 3:1 vs its bg) | Icon |
|---|---|---|---|---|
| `info` | `#075985` | `#F0F9FF` | `#0369A1` | `Info` |
| `warning` | `#92400E` | `#FFFBEB` | `#B45309` | `AlertTriangle` |
| `danger` | `#991B1B` | `#FEF2F2` | `#B91C1C` | `AlertOctagon` |
| `neutral` | `#334155` | `#F1F5F9` | `#64748B` | `Info` |
| `brand` | `#0B4A36` | `#ECF3EF` | `#0B4A36` | `Info` |

There is **no "success" green** feedback role. Success states ("Decision saved", "Ready") use the neutral role with a `Check` icon and plain text. Green is reserved for brand identity so it can never read as an endorsement.

Danger button fill: `#991B1B` (white text 8.31:1). Danger hover: `#7F1D1D`.

#### 3.1.6 Special-purpose colours
| Token | Hex | Use |
|---|---|---|
| `--color-ai-fg` | `#6D28D9` | AI draft label and icon |
| `--color-ai-bg` | `#F5F3FF` | AI draft block background |
| `--color-ai-border` | `#7C3AED` | AI draft dashed border |
| `--color-ai-fg-strong` | `#5B21B6` | AI draft body headings |
| `--color-demo-fg` | `#A21CAF` | Demo data badge text/border |
| `--color-demo-bg` | `#FDF4FF` | Demo badge background |
| `--color-demo-solid` | `#A21CAF` | Demo badge solid variant (white text) |
| `--color-focus` | `#1D4ED8` | Focus ring on light surfaces |
| `--color-focus-on-dark` | `#FDE68A` | Focus ring on brand/dark surfaces |
| `--color-disabled-bg` | `ink-200` | Disabled control fill |
| `--color-disabled-fg` | `ink-600` | Disabled text (WCAG exempts disabled controls; still keep ≥ 3:1) |

#### 3.1.7 Contrast table (measured, WCAG 2.x relative luminance)
Targets: normal text ≥ 4.5:1, large text (≥ 24 px, or ≥ 18.66 px bold) ≥ 3:1, non-text UI (control borders, icons, focus) ≥ 3:1.

| Pair | Ratio | Pass |
|---|---:|---|
| text `#111827` on white | 17.74 | AAA |
| text `#111827` on canvas `#F8FAFC` | 16.96 | AAA |
| secondary `#475569` on white / canvas / sunken | 7.58 / 7.24 / 6.92 | AAA |
| tertiary `#5B6B80` on white / canvas / sunken | 5.44 / 5.20 / 4.97 | AA |
| control border `#64748B` on white / canvas | 4.76 / 4.55 | AA (non-text ≥ 3) |
| card border `#CBD5E1` on white | 1.48 | **decorative only** (never the sole identifier of a control) |
| white on brand-800 | 10.26 | AAA |
| white on brand-900 | 13.74 | AAA |
| white on brand-700 | 7.65 | AAA |
| brand-800 on white (links) | 10.26 | AAA |
| brand-800 on brand-50 / brand-100 | 9.10 / 7.90 | AAA |
| brand-100 on brand-800 (header text) | 7.90 | AAA |
| brand-200 on brand-800 (muted header text) | 6.25 | AA |
| focus blue `#1D4ED8` on white / on brand-50 | 6.70 / 5.95 | AA (non-text) |
| focus amber `#FDE68A` on brand-800 | 8.24 | AA (non-text) |
| removed `#B91C1C` on `#FEE2E2` | 5.30 | AA |
| added `#1D4ED8` on `#DBEAFE` | 5.49 | AA |
| matched `#92400E` on `#FEF3C7` | 6.37 | AA |
| white on high-priority `#9A3412` | 7.31 | AAA |
| AI `#6D28D9` on `#F5F3FF` | 6.48 | AA |
| AI border `#7C3AED` on `#F5F3FF` / white | 5.20 / 5.70 | AA (non-text) |
| demo `#A21CAF` on `#FDF4FF` | 5.89 | AA |
| white on demo solid `#A21CAF` | 6.32 | AA |
| warning `#92400E` on `#FFFBEB` | 6.84 | AA |
| warning border `#B45309` on `#FFFBEB` | 4.84 | AA (non-text) |
| danger `#991B1B` on `#FEF2F2` | 7.60 | AAA |
| danger border `#B91C1C` on `#FEF2F2` | 5.91 | AA (non-text) |
| white on danger button `#991B1B` | 8.31 | AAA |
| info `#075985` on `#F0F9FF` | 7.09 | AAA |
| likely band `#1E3A5F` on `#E8EEF7` | 9.86 | AAA |
| grid unreadable `#991B1B` on `#FEE2E2` | 6.80 | AA |
| disabled `#64748B` on `#E2E8F0` | 3.86 | exempt (still ≥ 3) |

#### 3.1.8 Colour rules
1. **Do not use Tailwind opacity modifiers on token colours** (`bg-brand-800/50`). Hex variables do not support them, and ad-hoc blends escape the contrast test. Add a named token instead.
2. Brand green appears only on: header, primary buttons, links, selected-row tint, `strong` band, focus-adjacent tints, the Overview stat accents. **Never** inside the three evidence panes' diff area.
3. Only diff colours are strongly saturated on the evidence screen. Chrome around it stays neutral.
4. No gradients anywhere. No decorative blur.
5. Dark mode is **out of scope for v1**. Tokens are semantic (`--color-text`, `--color-surface`) so a future `[data-theme="dark"]` remap is possible without touching components. Set `color-scheme: light` on `:root`.

### 3.2 Typography

#### 3.2.1 Typefaces (three roles, loaded with `next/font`)
| Role | Family | Fallback stack | Weights | Used for |
|---|---|---|---|---|
| **UI sans** | **Inter** (variable, `latin` subset, `display: swap`) | `ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` | 400, 500, 600, 700 | All interface text, labels, buttons, AI draft block |
| **Evidence serif** | **Source Serif 4** (variable, optical size on, `latin` + `latin-ext`) | `"Iowan Old Style", "Palatino Linotype", Georgia, "Times New Roman", serif` | 400, 600 (700 for `<strong>` inside quotes) | **Quoted document text only**: old/new wording, affected passage, evidence drawer, export brief |
| **Mono** | **JetBrains Mono** (variable, `latin`) | `ui-monospace, SFMono-Regular, Menlo, Consolas, monospace` | 400, 500 | SHA-256 hashes, IDs (alert ID, pack ID, run ID) **only** |

CSS variables: `--font-sans`, `--font-serif`, `--font-mono`. Inter's `latin-ext` is required for Yoruba/Igbo diacritics in titles (`ẹ`, `ọ`, `ṣ`, `ụ`, combining dot below). Test with "Ọ̀rọ̀ ìforúkọsílẹ̀". Enable Inter `font-feature-settings: "cv11", "ss03"` **off** (keep defaults); enable `font-variant-numeric: tabular-nums` on tables, counts, timestamps and progress percentages.

Rule: if text is a **verbatim quote from an uploaded document**, it is serif. If the tool wrote it (label, summary, rationale, message), it is sans. No exceptions. This is the ledger signature.

#### 3.2.2 Type scale
Base size is **16 px** and never below on mobile for body copy. Sizes are in px, line-height in px, with the Tailwind class name to define.

| Token / class | Size / line | Weight | Tracking | Family | Use |
|---|---|---|---|---|---|
| `text-display` | 32 / 40 (mobile 26 / 32) | 600 | -0.02em | sans | Page `<h1>` |
| `text-h2` | 24 / 32 (mobile 22 / 30) | 600 | -0.015em | sans | Section headings |
| `text-h3` | 20 / 28 | 600 | -0.01em | sans | Card and pane headings |
| `text-h4` | 16 / 24 | 600 | 0 | sans | Sub-headings, dialog sections |
| `text-body-lg` | 18 / 28 | 400 | 0 | sans | Lead paragraphs (Overview intro, empty states) |
| `text-body` | 16 / 24 | 400 | 0 | sans | Default body |
| `text-body-sm` | 14 / 20 | 400 | 0 | sans | Table cells, helper text, metadata |
| `text-label` | 14 / 20 | 500 | 0 | sans | Form labels, nav items, tab triggers, button (sm/md) text |
| `text-label-lg` | 16 / 24 | 600 | 0 | sans | Large button text |
| `text-caption` | 12 / 16 | 500 | 0.01em | sans | Chip text only. **Minimum size in the product.** |
| `text-evidence` | 17 / 28 | 400 | 0 | **serif** | Quoted wording in panes |
| `text-evidence-sm` | 15 / 24 | 400 | 0 | **serif** | Quoted wording in table/inbox snippets, drawer context lines |
| `text-evidence-print` | 11pt / 1.5 | 400 | 0 | **serif** | Export brief |
| `text-mono` | 13 / 20 | 400 | 0 | mono | Hashes and IDs |

Rules:
- **No all-caps** labels, anywhere. Sentence case only. No tracked-out eyebrows.
- Serif gets more leading than sans (28 on 17 = 1.65; sans body is 1.5).
- Never go below 12 px. Chip text at 12 px must be weight 500+.
- Prose max line length: **72 ch**. Evidence panes: **68 ch** (they are narrower anyway). Never let a paragraph span a full 1280 px container.
- Headings: one `<h1>` per page; ordered heading levels; never skip. Visual size is independent of level (use the class, not the tag, to size).
- Numbers in tables, counts and timestamps: `tabular-nums`.
- Long unbroken strings (hashes, filenames, URLs): `overflow-wrap: anywhere`.
- `text-wrap: balance` on headings; `text-wrap: pretty` on body paragraphs.

#### 3.2.3 Hashes and IDs
Display the **first 8 characters** of a SHA-256 in a `HashPill`: mono 13/20, ink-700 on ink-100, radius 4, padding 2 × 6, with a copy button (icon, 28 × 28, aria-label "Copy full hash"). Full hash available in a tooltip and a `title`-independent expandable ("Show full hash"). IDs (alert/run/pack) same pill, first 8 chars.

#### 3.2.4 Dates and times
Three **separately labelled** values everywhere (a product requirement): **Published**, **Uploaded**, **Compared**.
- Published date (a date only): `1 Sep 2026`. No time, no timezone, because it is a calendar date.
- Uploaded / Compared / Decided (timestamps): `19 Nov 2026, 14:05 WAT`. Render with `Intl.DateTimeFormat("en-NG", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Africa/Lagos", timeZoneName: "short" })`. If the browser prints `GMT+1` instead of `WAT`, post-process to `WAT`.
- Relative time ("5 minutes ago") may appear **only** as secondary text next to the absolute time, never alone.
- Exports: ISO-8601 UTC in data fields; human-readable WAT in the brief header, with the UTC value in parentheses.
- Put all formatting in `src/lib/format.ts`; components never call `toLocaleString` directly.

#### 3.2.5 Links
Underlined always (not colour alone), `text-decoration-thickness: 1px`, `text-underline-offset: 3px`. Colour `brand-800`; hover: `brand-900` and thickness 2px; visited: same as unvisited (these are app routes); focus-visible: the focus ring. External links (`source_url`) add an `ExternalLink` icon (14 px, aria-hidden), `rel="noopener noreferrer nofollow"`, `target="_blank"`, and visually hidden text "(opens in a new tab)".

### 3.3 Spacing
4 px base unit. Use only these steps (Tailwind's default scale already matches; do not add others):

| Token | px | Typical use |
|---|---:|---|
| `0.5` | 2 | Hairline nudges (icon optical alignment) |
| `1` | 4 | Icon-to-text in chips |
| `1.5` | 6 | Chip vertical padding |
| `2` | 8 | Gap between related controls |
| `3` | 12 | Input horizontal padding, compact card padding |
| `4` | 16 | **Default card padding (mobile)**, gap between form fields |
| `5` | 20 | Card padding (desktop) |
| `6` | 24 | Dialog padding, section gap inside a page |
| `8` | 32 | Page horizontal padding (desktop), gap between page sections |
| `10` | 40 | Control height (md) |
| `12` | 48 | Control height (lg) |
| `16` | 64 | Large vertical rhythm, empty-state padding |
| `20` | 80 | Reserved |

Rhythm rules:
- Related items: 8. Items in a group: 12–16. Groups within a card: 24. Cards within a page: 24 (mobile 16). Page sections: 32 (mobile 24).
- A label sits 6 px above its control; helper text 6 px below; error text 6 px below with the helper replaced (not stacked).
- Page padding: **16** (< 640), **24** (640–1023), **32** (≥ 1024).

### 3.4 Layout, breakpoints and grid
| Name | Min width | Notes |
|---|---:|---|
| (base) | 360 | Design target for the smallest supported phone |
| `sm` | 640 | Large phones, landscape |
| `md` | 768 | Tablets: tables become tables again |
| `lg` | 1024 | Desktop nav replaces menu button |
| `evidence` | 1200 | **Three-pane evidence view** (below this: tabs) |
| `xl` | 1280 | |
| `2xl` | 1536 | Max container stops growing |

Containers (centered, `margin-inline: auto`):
- `container-page`: max 1280 px (Overview, Sources, Collection, Export)
- `container-wide`: max 1440 px (Inbox, Evidence)
- `container-narrow`: max 720 px (Login card, forms, empty states, "not part of a workspace" page)
- `container-prose`: max 72 ch (policy text, NotClaimedPanel body)

Grid: CSS grid, 12 columns at ≥ `lg`, gap 24; 4 columns below with gap 16. Prefer simple flex and 2/3-column grids to a literal 12-col implementation. Never use fixed pixel widths for content columns; use `minmax(0, 1fr)` to prevent overflow.

Rules:
- Body never scrolls horizontally at any width ≥ 320. Wide tables scroll inside `overflow-x-auto` wrappers with a visible focus-able scroll region (`tabindex="0"`, `role="region"`, `aria-label`).
- Use `100dvh` (not `100vh`) for full-height layouts and sheets. Mobile browser chrome moves.
- Sticky elements: header (56 px), inbox filter bar (below header, `top: 56px`), drawer headers. Never stack more than two sticky layers.
- Respect safe areas: `padding-bottom: env(safe-area-inset-bottom)` on bottom sheets and the bottom toast stack.

### 3.5 Borders
| Token | Value | Use |
|---|---|---|
| `border-hairline` | 1px solid `--color-border` | Cards, table rows, section dividers |
| `border-control` | 1px solid `--color-border-control` | Inputs, selects, secondary buttons, checkboxes (2px on checkbox/radio) |
| `border-control-strong` | 2px solid `--color-border-control` | Dropzone, selected radio card (brand-800) |
| `border-dashed-ai` | 1.5px dashed `--color-ai-border` | AI block only |
| `border-dashed-drop` | 2px dashed `--color-border-control` | Dropzone idle |
| `border-focus` | see 3.8 | |

The AI block is the **only** element with a violet dashed border. The dropzone is the **only** element with a grey dashed 2px border. Distinct shapes, distinct meaning.

### 3.6 Radii (scale with importance)
| Token | px | Use |
|---|---:|---|
| `rounded-xs` | 2 | Diff `<mark>` segments |
| `rounded-sm` | 4 | Chips, hash pills, checkbox, tooltip arrow corners |
| `rounded-md` | 6 | **Controls**: buttons, inputs, selects, tabs |
| `rounded-lg` | 10 | **Cards**, banners, AI block, panes |
| `rounded-xl` | 14 | Dialogs, drawers (top corners on mobile sheets), popovers |
| `rounded-2xl` | 20 | Reserved |
| `rounded-full` | 9999 | Count badges, avatars, radio dot, progress bar, spinner |

Chips are deliberately **squarer (4 px)** than buttons (6 px) so a status chip is never mistaken for a button. Count badges (numbers in nav) are the only pills.

### 3.7 Elevation (shadows)
Shadows are tinted with the ink colour `rgb(15 23 42)`, never pure black. Elevation encodes **layer**, not decoration: things that float above the page get stronger shadows. Cards at rest use a border and a whisper of shadow. Nothing animates its shadow on hover except interactive cards (3.7 note).

| Token | Value | Use |
|---|---|---|
| `shadow-none` | `none` | Flat, sunken, inline elements |
| `shadow-xs` | `0 1px 1px rgb(15 23 42 / 0.05)` | Buttons (primary/secondary), cards at rest |
| `shadow-sm` | `0 1px 2px rgb(15 23 42 / 0.06), 0 1px 3px rgb(15 23 42 / 0.08)` | Interactive card hover, raised card |
| `shadow-md` | `0 2px 4px -1px rgb(15 23 42 / 0.06), 0 4px 8px -2px rgb(15 23 42 / 0.10)` | Tooltips, sticky filter bar when scrolled |
| `shadow-lg` | `0 4px 6px -2px rgb(15 23 42 / 0.05), 0 12px 24px -4px rgb(15 23 42 / 0.14)` | Dropdown menus, select lists, popovers, toasts |
| `shadow-xl` | `0 8px 10px -6px rgb(15 23 42 / 0.08), 0 24px 48px -12px rgb(15 23 42 / 0.24)` | Dialogs |
| `shadow-drawer` | `-8px 0 24px -8px rgb(15 23 42 / 0.18)` | Evidence drawer (right edge) |
| `shadow-sheet` | `0 -8px 24px -8px rgb(15 23 42 / 0.18)` | Bottom sheets on mobile |
| `shadow-header` | `0 1px 0 rgb(7 52 38 / 0.6), 0 2px 6px rgb(15 23 42 / 0.12)` | App header |
| `shadow-sticky` | `0 1px 0 rgb(15 23 42 / 0.08), 0 4px 8px -4px rgb(15 23 42 / 0.08)` | Sticky bars once content scrolls under them |
| `shadow-inset` | `inset 0 1px 1px rgb(15 23 42 / 0.04)` | Text inputs (optional subtle depth) |
| `shadow-focus` | `0 0 0 2px #FFFFFF, 0 0 0 5px #1D4ED8` | Focus ring on light surfaces |
| `shadow-focus-dark` | `0 0 0 2px #0B4A36, 0 0 0 5px #FDE68A` | Focus ring on brand/dark surfaces |

Elevation map: **0** canvas · **1** card (xs + border) · **2** raised/interactive card hover (sm) · **3** sticky bars (md/sticky) · **4** floating menus and toasts (lg) · **5** modal layers (xl, drawer, sheet).

Interactive card hover: border goes `ink-300 → ink-500` and shadow `xs → sm`, 120 ms. No translate, no scale.

### 3.8 Focus
Visible keyboard focus on **every** interactive element, ≥ 3:1 against adjacent colours, never removed.
- Default (light surfaces): `outline: none; box-shadow: var(--shadow-focus);` that is a 2 px white gap then a 3 px `#1D4ED8` ring. Works on white, canvas and tints.
- On brand header and other dark surfaces: `--shadow-focus-dark` (2 px brand gap then 3 px amber ring).
- Because box-shadow is clipped by `overflow: hidden` parents and does not render in Windows High Contrast, **also** set `outline: 2px solid transparent; outline-offset: 2px` so forced-colours mode draws a real outline.
- Use `:focus-visible` (not `:focus`) so mouse clicks don't show rings, but text inputs always show focus.
- Inside scroll containers where the ring would be clipped (tables, tabs, lists), use an **inset** ring: `box-shadow: inset 0 0 0 3px #1D4ED8`.
- Focus is **moved deliberately**: after dialog open → first focusable (or title); after dialog close → returns to the trigger; after route change → the `<h1>` (set `tabindex="-1"` and call `.focus()`); after a submit error → the error summary or first invalid field.

### 3.9 Z-index
| Token | Value | Layer |
|---|---:|---|
| `z-base` | 0 | Content |
| `z-sticky` | 10 | Sticky filter bars, table headers |
| `z-header` | 20 | App header |
| `z-dropdown` | 30 | Select lists, menus, popovers |
| `z-overlay` | 40 | Scrim |
| `z-modal` | 50 | Dialogs, drawers, sheets |
| `z-toast` | 60 | Toasts |
| `z-tooltip` | 70 | Tooltips |
| `z-skip` | 100 | Skip-to-content link |

Radix portals into `body`; assign these classes to `Portal` content explicitly.

### 3.10 Motion
Motion only **answers a user action** (opening, expanding, confirming) or shows **live progress**. There are **no** entrance animations on page load, no scroll-triggered reveals, no hover lifts.

| Token | Value | Use |
|---|---|---|
| `duration-instant` | 80 ms | Button press, checkbox toggle |
| `duration-fast` | 120 ms | Hover colour/border/shadow transitions |
| `duration-base` | 200 ms | Dialog, tooltip, popover, accordion open |
| `duration-slow` | 320 ms | Drawer and sheet slide, toast slide |
| `ease-standard` | `cubic-bezier(0.2, 0, 0, 1)` | Default |
| `ease-enter` | `cubic-bezier(0, 0, 0, 1)` | Things appearing |
| `ease-exit` | `cubic-bezier(0.3, 0, 1, 1)` | Things leaving (use 70% of the enter duration) |

Specifics:
- Colour/border/shadow transitions: `transition-property: color, background-color, border-color, box-shadow; duration-fast; ease-standard`. Never `transition: all`.
- Dialog: scrim fades 0→1 (200 ms); content fades and scales from 0.98→1 (200 ms). Exit: fade out 140 ms.
- Drawer: translateX(100%)→0, 320 ms, `ease-enter`. Exit 220 ms.
- Mobile bottom sheet: translateY(100%)→0, 320 ms.
- Accordion/expanding inbox row: height via Radix Collapsible CSS variable, 200 ms.
- Progress bar fill: `width` transition 400 ms linear between polled values (so it doesn't jump).
- Spinner: 700 ms linear infinite rotation, 16/20/24 px, `Loader2` icon.
- Skeleton shimmer: 1.4 s linear infinite background-position sweep (ink-100 → ink-200 → ink-100).
- The single "moment": when a decision saves, the `Check` icon in the success toast **draws** (stroke-dashoffset, 240 ms). Nothing else is decorative.
- **`prefers-reduced-motion: reduce`**: all durations collapse to 0.01 ms; spinner replaced by static text "Working…" with a static icon; skeleton shimmer off (flat ink-100); progress fill transition off; the check-draw becomes instant. Progress must remain understandable through text and the `aria-live` region.

### 3.11 Opacity and states
Do not use opacity to build colours. Allowed: `opacity: 1` default; disabled text uses `--color-disabled-fg`, never `opacity-50`. Scrim uses `--color-overlay`.

### 3.12 Iconography
- Library: **lucide-react** only. No emoji as icons. No mixed icon sets.
- Sizes: **14** (inline in chips/links/captions), **16** (buttons sm/md, table cells), **20** (buttons lg, banners, nav, inputs), **24** (empty-state/section icons), **40** (empty-state hero icon in a 72 px circle).
- Stroke width: **2** at 14–16, **1.75** at 20–24, **1.5** at 40.
- Colour: `currentColor`. Default `ink-700`.
- **Decorative icons** (next to text): `aria-hidden="true"`. **Icon-only buttons**: the button has `aria-label`; the icon is `aria-hidden`.
- Alignment: icons sit on the text's optical centre; in a flex row with `items-center` and a 4–8 px gap.
- Meaning-to-icon map (use consistently):

| Meaning | Icon |
|---|---|
| Added in newer version | `PlusCircle` |
| Removed in newer version | `MinusCircle` |
| Changed | `Replace` (fallback `ArrowLeftRight`) |
| Moved | `MoveRight` (fallback `ArrowRightLeft`) |
| High priority | `ChevronsUp` |
| Normal priority | `Minus` |
| Strong / Likely / Uncertain match | `SignalHigh` / `SignalMedium` / `SignalLow` |
| Potentially affected | `Target` |
| AI draft | `Sparkles` |
| Demo data | `FlaskConical` |
| Date changed / Number changed | `CalendarClock` / `Hash` |
| Obligation wording changed | `Scale` |
| Negation changed | `Ban` |
| Queued / Extracting | `Clock` / `Loader2` |
| Ready | `Check` |
| Incomplete | `AlertTriangle` |
| Failed / Rejected | `XOctagon` / `ShieldX` |
| Provenance unverified / verified / conflicting | `ShieldQuestion` / `ShieldCheck` / `ShieldAlert` |
| Upload | `UploadCloud` |
| File | `FileText` |
| Download | `Download` |
| Print | `Printer` |
| Copy | `Copy` |
| External link | `ExternalLink` |
| Expand / Collapse | `ChevronDown` / `ChevronUp` |
| Close | `X` |
| Retry | `RotateCcw` |
| Unreviewed / Confirmed impact / Dismissed / Needs more information | `Circle` / `ClipboardCheck` / `CircleSlash` / `HelpCircle` |
| Info / Warning / Danger | `Info` / `AlertTriangle` / `AlertOctagon` |
| Page of a document | `FileText` with page number |
| Filters | `ListFilter` |
| Menu | `Menu` |
| Delete (workspace data) | `Trash2` |

---

## 4. Implementation files for tokens

### 4.1 `src/styles/tokens.css`
```css
:root {
  color-scheme: light;

  /* Neutrals */
  --color-white: #FFFFFF;
  --color-ink-50: #F8FAFC;  --color-ink-100: #F1F5F9; --color-ink-200: #E2E8F0;
  --color-ink-300: #CBD5E1; --color-ink-400: #94A3B8; --color-ink-500: #64748B;
  --color-ink-600: #5B6B80; --color-ink-700: #475569; --color-ink-800: #334155;
  --color-ink-900: #111827;

  /* Brand */
  --color-brand-50: #ECF3EF;  --color-brand-100: #D5E6DC; --color-brand-200: #B3D1C0;
  --color-brand-300: #8DB8A0; --color-brand-400: #5E9A7C; --color-brand-500: #2F7A5C;
  --color-brand-600: #1A6A4E; --color-brand-700: #0F5F46; --color-brand-800: #0B4A36;
  --color-brand-900: #073426; --color-brand-950: #04221A;

  /* Semantic */
  --color-canvas: var(--color-ink-50);
  --color-surface: var(--color-white);
  --color-surface-sunken: var(--color-ink-100);
  --color-surface-evidence: #FFFFFF;
  --color-text: var(--color-ink-900);
  --color-text-secondary: var(--color-ink-700);
  --color-text-tertiary: var(--color-ink-600);
  --color-text-on-brand: var(--color-white);
  --color-text-link: var(--color-brand-800);
  --color-border: var(--color-ink-300);
  --color-border-control: var(--color-ink-500);
  --color-border-control-hover: var(--color-ink-700);
  --color-overlay: rgb(15 23 42 / 0.55);
  --color-disabled-bg: var(--color-ink-200);
  --color-disabled-fg: var(--color-ink-600);

  /* Diff */
  --color-removed-fg: #B91C1C; --color-removed-bg: #FEE2E2; --color-removed-border: #FCA5A5;
  --color-added-fg: #1D4ED8;   --color-added-bg: #DBEAFE;   --color-added-border: #93C5FD;
  --color-matched-fg: #92400E; --color-matched-bg: #FEF3C7; --color-matched-border: #FCD34D;
  --color-moved-fg: #334155;   --color-moved-bg: #E2E8F0;

  /* Priority */
  --color-priority-high-bg: #9A3412; --color-priority-high-fg: #FFFFFF;
  --color-priority-high-tint: #FFEDD5; --color-priority-high-tint-fg: #9A3412;
  --color-priority-normal-fg: var(--color-ink-700);

  /* Confidence */
  --color-band-strong-bg: #ECF3EF; --color-band-strong-fg: #0B4A36; --color-band-strong-border: #B3D1C0;
  --color-band-likely-bg: #E8EEF7; --color-band-likely-fg: #1E3A5F; --color-band-likely-border: #B7C6DE;
  --color-band-uncertain-bg: #FEF3C7; --color-band-uncertain-fg: #92400E; --color-band-uncertain-border: #FCD34D;

  /* Feedback */
  --color-info-fg: #075985;    --color-info-bg: #F0F9FF;    --color-info-border: #0369A1;
  --color-warning-fg: #92400E; --color-warning-bg: #FFFBEB; --color-warning-border: #B45309;
  --color-danger-fg: #991B1B;  --color-danger-bg: #FEF2F2;  --color-danger-border: #B91C1C;
  --color-danger-solid: #991B1B; --color-danger-solid-hover: #7F1D1D;
  --color-neutral-fg: #334155; --color-neutral-bg: #F1F5F9; --color-neutral-border: #64748B;

  /* Special */
  --color-ai-fg: #6D28D9; --color-ai-fg-strong: #5B21B6; --color-ai-bg: #F5F3FF; --color-ai-border: #7C3AED;
  --color-demo-fg: #A21CAF; --color-demo-bg: #FDF4FF; --color-demo-solid: #A21CAF;
  --color-focus: #1D4ED8; --color-focus-on-dark: #FDE68A;

  /* Radii */
  --radius-xs: 2px; --radius-sm: 4px; --radius-md: 6px; --radius-lg: 10px; --radius-xl: 14px; --radius-full: 9999px;

  /* Shadows */
  --shadow-xs: 0 1px 1px rgb(15 23 42 / 0.05);
  --shadow-sm: 0 1px 2px rgb(15 23 42 / 0.06), 0 1px 3px rgb(15 23 42 / 0.08);
  --shadow-md: 0 2px 4px -1px rgb(15 23 42 / 0.06), 0 4px 8px -2px rgb(15 23 42 / 0.10);
  --shadow-lg: 0 4px 6px -2px rgb(15 23 42 / 0.05), 0 12px 24px -4px rgb(15 23 42 / 0.14);
  --shadow-xl: 0 8px 10px -6px rgb(15 23 42 / 0.08), 0 24px 48px -12px rgb(15 23 42 / 0.24);
  --shadow-drawer: -8px 0 24px -8px rgb(15 23 42 / 0.18);
  --shadow-sheet: 0 -8px 24px -8px rgb(15 23 42 / 0.18);
  --shadow-header: 0 1px 0 rgb(7 52 38 / 0.6), 0 2px 6px rgb(15 23 42 / 0.12);
  --shadow-sticky: 0 1px 0 rgb(15 23 42 / 0.08), 0 4px 8px -4px rgb(15 23 42 / 0.08);
  --shadow-inset: inset 0 1px 1px rgb(15 23 42 / 0.04);
  --shadow-focus: 0 0 0 2px #FFFFFF, 0 0 0 5px #1D4ED8;
  --shadow-focus-dark: 0 0 0 2px #0B4A36, 0 0 0 5px #FDE68A;
  --shadow-focus-inset: inset 0 0 0 3px #1D4ED8;

  /* Motion */
  --duration-instant: 80ms; --duration-fast: 120ms; --duration-base: 200ms; --duration-slow: 320ms;
  --ease-standard: cubic-bezier(0.2, 0, 0, 1);
  --ease-enter: cubic-bezier(0, 0, 0, 1);
  --ease-exit: cubic-bezier(0.3, 0, 1, 1);

  /* Layout */
  --header-h: 56px;
  --filter-bar-h: 64px;
  --page-pad: 16px;
}
@media (min-width: 640px)  { :root { --page-pad: 24px; } }
@media (min-width: 1024px) { :root { --page-pad: 32px; } }
```

### 4.2 `tailwind.config.ts` (Tailwind v3 syntax)
If the project uses Tailwind v4, move the same keys into an `@theme { … }` block in `globals.css`; names stay identical.
```ts
import type { Config } from "tailwindcss";

const v = (name: string) => `var(--${name})`;

const config: Config = {
  content: ["./src/**/*.{ts,tsx,mdx}"],
  theme: {
    screens: {
      xs: "360px", sm: "640px", md: "768px", lg: "1024px",
      evidence: "1200px", xl: "1280px", "2xl": "1536px",
    },
    // Replace (not extend) colours so off-system hexes cannot be used by accident.
    colors: {
      transparent: "transparent", current: "currentColor", white: v("color-white"),
      ink: Object.fromEntries([50,100,200,300,400,500,600,700,800,900].map(n => [n, v(`color-ink-${n}`)])),
      brand: Object.fromEntries([50,100,200,300,400,500,600,700,800,900,950].map(n => [n, v(`color-brand-${n}`)])),
      canvas: v("color-canvas"), surface: v("color-surface"), sunken: v("color-surface-sunken"),
      evidence: v("color-surface-evidence"),
      text: { DEFAULT: v("color-text"), secondary: v("color-text-secondary"), tertiary: v("color-text-tertiary"),
              onbrand: v("color-text-on-brand"), link: v("color-text-link") },
      line: { DEFAULT: v("color-border"), control: v("color-border-control"), "control-hover": v("color-border-control-hover") },
      removed: { fg: v("color-removed-fg"), bg: v("color-removed-bg"), line: v("color-removed-border") },
      added:   { fg: v("color-added-fg"),   bg: v("color-added-bg"),   line: v("color-added-border") },
      matched: { fg: v("color-matched-fg"), bg: v("color-matched-bg"), line: v("color-matched-border") },
      moved:   { fg: v("color-moved-fg"),   bg: v("color-moved-bg") },
      high:    { bg: v("color-priority-high-bg"), fg: v("color-priority-high-fg"),
                 tint: v("color-priority-high-tint"), tintfg: v("color-priority-high-tint-fg") },
      band: {
        "strong-bg": v("color-band-strong-bg"), "strong-fg": v("color-band-strong-fg"), "strong-line": v("color-band-strong-border"),
        "likely-bg": v("color-band-likely-bg"), "likely-fg": v("color-band-likely-fg"), "likely-line": v("color-band-likely-border"),
        "uncertain-bg": v("color-band-uncertain-bg"), "uncertain-fg": v("color-band-uncertain-fg"), "uncertain-line": v("color-band-uncertain-border"),
      },
      info:    { fg: v("color-info-fg"),    bg: v("color-info-bg"),    line: v("color-info-border") },
      warning: { fg: v("color-warning-fg"), bg: v("color-warning-bg"), line: v("color-warning-border") },
      danger:  { fg: v("color-danger-fg"),  bg: v("color-danger-bg"),  line: v("color-danger-border"),
                 solid: v("color-danger-solid"), "solid-hover": v("color-danger-solid-hover") },
      neutral: { fg: v("color-neutral-fg"), bg: v("color-neutral-bg"), line: v("color-neutral-border") },
      ai:      { fg: v("color-ai-fg"), strong: v("color-ai-fg-strong"), bg: v("color-ai-bg"), line: v("color-ai-border") },
      demo:    { fg: v("color-demo-fg"), bg: v("color-demo-bg"), solid: v("color-demo-solid") },
      focus:   { DEFAULT: v("color-focus"), dark: v("color-focus-on-dark") },
      disabled:{ bg: v("color-disabled-bg"), fg: v("color-disabled-fg") },
      overlay: v("color-overlay"),
    },
    fontFamily: {
      sans: ["var(--font-sans)", "ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Helvetica Neue", "Arial", "sans-serif"],
      serif: ["var(--font-serif)", "Iowan Old Style", "Palatino Linotype", "Georgia", "Times New Roman", "serif"],
      mono: ["var(--font-mono)", "ui-monospace", "SFMono-Regular", "Menlo", "Consolas", "monospace"],
    },
    fontSize: {
      display:        ["2rem",      { lineHeight: "2.5rem",   letterSpacing: "-0.02em",  fontWeight: "600" }],
      h2:             ["1.5rem",    { lineHeight: "2rem",     letterSpacing: "-0.015em", fontWeight: "600" }],
      h3:             ["1.25rem",   { lineHeight: "1.75rem",  letterSpacing: "-0.01em",  fontWeight: "600" }],
      h4:             ["1rem",      { lineHeight: "1.5rem",   fontWeight: "600" }],
      "body-lg":      ["1.125rem",  { lineHeight: "1.75rem" }],
      body:           ["1rem",      { lineHeight: "1.5rem" }],
      "body-sm":      ["0.875rem",  { lineHeight: "1.25rem" }],
      label:          ["0.875rem",  { lineHeight: "1.25rem",  fontWeight: "500" }],
      "label-lg":     ["1rem",      { lineHeight: "1.5rem",   fontWeight: "600" }],
      caption:        ["0.75rem",   { lineHeight: "1rem",     letterSpacing: "0.01em", fontWeight: "500" }],
      evidence:       ["1.0625rem", { lineHeight: "1.75rem" }],
      "evidence-sm":  ["0.9375rem", { lineHeight: "1.5rem" }],
      mono:           ["0.8125rem", { lineHeight: "1.25rem" }],
    },
    borderRadius: {
      none: "0", xs: v("radius-xs"), sm: v("radius-sm"), md: v("radius-md"),
      lg: v("radius-lg"), xl: v("radius-xl"), full: v("radius-full"),
    },
    boxShadow: {
      none: "none", xs: v("shadow-xs"), sm: v("shadow-sm"), md: v("shadow-md"), lg: v("shadow-lg"), xl: v("shadow-xl"),
      drawer: v("shadow-drawer"), sheet: v("shadow-sheet"), header: v("shadow-header"), sticky: v("shadow-sticky"),
      inset: v("shadow-inset"), focus: v("shadow-focus"), "focus-dark": v("shadow-focus-dark"), "focus-inset": v("shadow-focus-inset"),
    },
    zIndex: { base: "0", sticky: "10", header: "20", dropdown: "30", overlay: "40", modal: "50", toast: "60", tooltip: "70", skip: "100" },
    transitionDuration: { instant: "80ms", fast: "120ms", base: "200ms", slow: "320ms" },
    transitionTimingFunction: { standard: "cubic-bezier(0.2,0,0,1)", enter: "cubic-bezier(0,0,0,1)", exit: "cubic-bezier(0.3,0,1,1)" },
    extend: {
      maxWidth: { page: "1280px", wide: "1440px", narrow: "720px", prose: "72ch", evidence: "68ch" },
      minHeight: { control: "40px", "control-lg": "48px", "touch": "44px" },
      keyframes: {
        shimmer: { "0%": { backgroundPosition: "-200% 0" }, "100%": { backgroundPosition: "200% 0" } },
        spin: { to: { transform: "rotate(360deg)" } },
        "dialog-in": { from: { opacity: "0", transform: "scale(0.98)" }, to: { opacity: "1", transform: "scale(1)" } },
        "scrim-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "drawer-in": { from: { transform: "translateX(100%)" }, to: { transform: "translateX(0)" } },
        "sheet-in": { from: { transform: "translateY(100%)" }, to: { transform: "translateY(0)" } },
        "check-draw": { from: { strokeDashoffset: "24" }, to: { strokeDashoffset: "0" } },
      },
      animation: {
        shimmer: "shimmer 1.4s linear infinite", spin: "spin 700ms linear infinite",
        "dialog-in": "dialog-in 200ms cubic-bezier(0,0,0,1)", "scrim-in": "scrim-in 200ms linear",
        "drawer-in": "drawer-in 320ms cubic-bezier(0,0,0,1)", "sheet-in": "sheet-in 320ms cubic-bezier(0,0,0,1)",
        "check-draw": "check-draw 240ms cubic-bezier(0.2,0,0,1) forwards",
      },
    },
  },
  plugins: [],
};
export default config;
```
Because `colors` is **replaced**, classes like `bg-red-500` will not compile. That is intentional: it keeps the palette closed.

### 4.3 `src/app/globals.css` (base layer)
```css
@import "../styles/tokens.css";
@tailwind base; @tailwind components; @tailwind utilities;

@layer base {
  html { -webkit-text-size-adjust: 100%; scroll-padding-top: calc(var(--header-h) + var(--filter-bar-h) + 16px); }
  body {
    background: var(--color-canvas); color: var(--color-text);
    font-family: var(--font-sans), ui-sans-serif, system-ui, sans-serif;
    font-size: 1rem; line-height: 1.5; -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
    min-height: 100dvh;
  }
  h1, h2, h3 { text-wrap: balance; }
  p, li { text-wrap: pretty; }
  :where(a) { color: var(--color-text-link); text-decoration: underline; text-decoration-thickness: 1px; text-underline-offset: 3px; }
  :where(a):hover { color: var(--color-brand-900); text-decoration-thickness: 2px; }

  /* Focus: never removed */
  :where(a, button, input, select, textarea, summary, [tabindex]:not([tabindex="-1"]), [role="tab"], [role="radio"], [role="checkbox"]):focus-visible {
    outline: 2px solid transparent; outline-offset: 2px; box-shadow: var(--shadow-focus);
  }
  :where(input, textarea, select):focus { outline: 2px solid transparent; outline-offset: 2px; box-shadow: var(--shadow-focus); }
  .on-dark :focus-visible { box-shadow: var(--shadow-focus-dark); }
  .focus-inset:focus-visible { box-shadow: var(--shadow-focus-inset); }

  ::selection { background: var(--color-brand-100); color: var(--color-ink-900); }
  [hidden] { display: none !important; }
  table { font-variant-numeric: tabular-nums; }
  .tnum { font-variant-numeric: tabular-nums; }
  .break-anywhere { overflow-wrap: anywhere; }

  @media (pointer: coarse) { /* bigger touch targets */
    .btn-sm { min-height: 40px; }
    .control { min-height: 44px; }
  }
  @media (prefers-reduced-motion: reduce) {
    *, *::before, *::after { animation-duration: 0.01ms !important; animation-iteration-count: 1 !important;
      transition-duration: 0.01ms !important; scroll-behavior: auto !important; }
    .skeleton { animation: none !important; background: var(--color-ink-100) !important; }
  }
  @media (forced-colors: active) {
    :where(a, button, input, select, textarea):focus-visible { outline: 3px solid Highlight; }
    mark.diff { forced-color-adjust: none; }
  }
}

@layer components {
  .container-page   { max-width: 1280px; margin-inline: auto; padding-inline: var(--page-pad); }
  .container-wide   { max-width: 1440px; margin-inline: auto; padding-inline: var(--page-pad); }
  .container-narrow { max-width: 720px;  margin-inline: auto; padding-inline: var(--page-pad); }
  .sr-only-focusable:not(:focus):not(:focus-within) { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }
  .skeleton { background: linear-gradient(90deg, var(--color-ink-100) 0%, var(--color-ink-200) 50%, var(--color-ink-100) 100%);
              background-size: 200% 100%; animation: shimmer 1.4s linear infinite; border-radius: var(--radius-md); }
}
```
(The skeleton uses a gradient strictly as a loading shimmer; it is the one allowed gradient in the product.)

### 4.4 Fonts (`src/app/layout.tsx`)
```ts
import { Inter, Source_Serif_4, JetBrains_Mono } from "next/font/google";
export const sans  = Inter({ subsets: ["latin", "latin-ext"], variable: "--font-sans", display: "swap" });
export const serif = Source_Serif_4({ subsets: ["latin", "latin-ext"], variable: "--font-serif", display: "swap", axes: ["opsz"] });
export const mono  = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
// <html lang="en" className={`${sans.variable} ${serif.variable} ${mono.variable}`}>
```
Set `lang="en"` on `<html>`. When displaying a material whose `language` is not `en`, wrap its quoted text in an element with the matching `lang` attribute (e.g. `lang="yo"`, `lang="ha"`, `lang="ig"`) so screen readers and hyphenation behave.

---

## 5. Global layout patterns

### 5.1 App shell
```
┌──────────────────────────────────────────────────────────────────────────┐
│ [skip to content]  (visible only on focus)                               │
├──────────────────────────────────────────────────────────────────────────┤
│ HEADER 56px, brand-800, shadow-header, sticky, z-header                  │
│ [glyph] VerityTrail   Overview Sources Collection Inbox Export   [user ▾]│
├──────────────────────────────────────────────────────────────────────────┤
│ <main id="main" tabindex="-1">                                           │
│   breadcrumbs (detail pages only)                                        │
│   <h1> + page actions                                                    │
│   page content on canvas                                                 │
├──────────────────────────────────────────────────────────────────────────┤
│ FOOTER: NotClaimedPanel link · coverage sentence · version               │
└──────────────────────────────────────────────────────────────────────────┘
```
- Landmarks: `<header role="banner">`, `<nav aria-label="Primary">`, `<main>`, `<footer>`.
- Header content is at most 1440 px wide, centered, using the same page padding.
- **< 1024 px**: nav collapses to a `Menu` icon button (44 × 44, `aria-label="Open menu"`, `aria-expanded`) that opens a left-side sheet (width `min(86vw, 320px)`, brand-900 background, nav items stacked 48 px tall). The wordmark stays visible. The user menu moves to the bottom of the sheet.
- **Nav item** (desktop): height 40, padding 0 12, radius 6, text-label, colour `brand-100`; hover: bg `brand-700`, text white; `aria-current="page"` (active): bg `brand-900`, text white, plus a 2 px white underline bar (inset 12 px from the sides, 4 px from the bottom) so active is not colour-only; focus: `shadow-focus-dark`.
- **User menu**: trigger shows display name (truncate at 20 ch) and role as text ("Curator"). Menu (Radix DropdownMenu): shows email, role, "Sign out". Panel: white, radius xl, shadow-lg, min-w 240, padding 8; items 40 high, radius 6, hover bg ink-100.
- **Count badge on "Inbox"** (unreviewed alerts): pill, bg white, text brand-800, text-caption, min-w 20, h 20, padding 0 6, `aria-label="N unreviewed alerts"` and visible number.
- **Demo workspace banner**: when the active workspace contains `is_demo` data, show a full-width strip under the header: bg `demo-bg`, bottom border 1px `demo-fg`, text `demo-fg` text-body-sm weight 500, `FlaskConical` icon, text "Demo data: these documents are examples, not official notices." Never dismissible.

### 5.2 Page header block
```
Breadcrumbs (14px, ink-700)
<h1> Title (text-display)                              [Primary action] [Secondary]
Lead sentence (text-body-lg, ink-700, max 72ch)
```
Margin: breadcrumbs → h1 8px; h1 → lead 8px; header block → content 24px (mobile 16px). Page actions wrap below the title on mobile, stacked full-width buttons.

### 5.3 Footer
Background `ink-100`, top border `border-hairline`, padding 24 vertical. Left: "What this tool does not claim" as a real link to the `NotClaimedPanel` section (guide requires this link in the Evidence footer and the Overview panel). Center/second line: the coverage sentence in text-body-sm tertiary: "Coverage is limited to the versions and materials you selected". Right: app version in mono 13. On mobile these stack, left-aligned.

