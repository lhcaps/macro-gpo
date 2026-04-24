---
phase: 13
slug: zedsu-operator-shell-redesign
status: draft
shadcn_initialized: false
preset: none
created: 2026-04-25
---

# Phase 13 — UI Design Contract

> Visual and interaction contract for the Zedsu Operator Shell. Generated from user design brief (2026-04-25). All values are locked — executors implement, not reinterpret.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | None (pure HTML/CSS/JS — no build step) |
| Preset | Custom tactical operator console |
| Component library | None (custom components only) |
| Icon library | Lucide Icons (SVG, CDN or bundled) |
| Font — Display/Headings | Space Grotesk (Google Fonts) |
| Font — Body/UI | Geist Sans (Google Fonts) |
| Font — Mono/Telemetry | JetBrains Mono (Google Fonts) |
| CSS Strategy | CSS custom properties (design tokens), single index.html + CSS files |

---

## Spacing Scale

Declared values (multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| `--space-1` | 4px | Icon gaps, micro-padding |
| `--space-2` | 8px | Compact element spacing |
| `--space-3` | 12px | Tight card padding |
| `--space-4` | 16px | Default element padding |
| `--space-5` | 20px | Card internal padding |
| `--space-6` | 24px | Section padding |
| `--space-8` | 32px | Layout gaps |
| `--space-10` | 40px | Major section breaks |
| `--space-12` | 48px | Page-level spacing |

**Exceptions:** None — 4px base grid strictly enforced.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Display (page title) | 28px | 700 | 1.2 |
| Heading (section) | 20px | 600 | 1.3 |
| Subheading (card title) | 16px | 600 | 1.4 |
| Body (default) | 14px | 400 | 1.5 |
| Label (form labels) | 13px | 500 | 1.4 |
| Small (muted text) | 12px | 400 | 1.4 |
| Mono (logs, telemetry) | 12px | 400 | 1.5 |
| HUD stat | 11px mono | 400 | 1.2 |

---

## Color

### Background Layers

| Role | Hex | Usage |
|------|-----|-------|
| App base | `#090B10` | Page/window background |
| Surface | `#101522` | Cards, panels, sidebar |
| Elevated | `#151B2B` | Hover states, dropdowns, popovers |
| Border | `rgba(255,255,255,0.08)` | Card borders, dividers |

### Text

| Role | Hex | Usage |
|------|-----|-------|
| Primary | `#F4F7FB` | Main content, headings |
| Secondary | `#9AA7BD` | Labels, subtitles |
| Muted | `#667085` | Placeholders, disabled, timestamps |

### Status / Semantic

| Role | Hex | Usage |
|------|-----|-------|
| Idle | `#9AA7BD` | IDLE state |
| Scanning | `#3B82F6` | SCANNING state |
| Approach | `#EAB308` | APPROACH state |
| Engaged | `#EF4444` | ENGAGED state, error |
| Fleeing | `#F97316` | FLEEING state |
| Spectating | `#EAB308` | SPECTATING state |
| Post-match | `#22C55E` | POST_MATCH state |
| Running (OK) | `#22C55E` | Running status |
| Warning | `#F59E0B` | Degraded, warnings |
| Error | `#EF4444` | Error state, destructive |
| Cyan accent | `#67E8F9` | Primary accent, interactive highlights |
| Discord violet | `#8B5CF6` | Discord-specific elements |
| AI blue | `#60A5FA` | Combat AI telemetry elements |

### Anti-pattern enforcement

| Rule | Reason |
|------|--------|
| NO pure black `#000` as background | Harsh contrast, not operator-grade |
| NO pure gray `#888` as text | Insufficient contrast |
| NO gradient purple-blue backgrounds | Generic AI slop |
| NO pure white text on dark | Eye strain |
| Accent `#67E8F9` reserved for: active nav item, primary CTA, status dot | Prevent overuse |

---

## Component Tokens

### Border Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 4px | Badges, small chips |
| `--radius-md` | 8px | Buttons, inputs |
| `--radius-lg` | 12px | Cards, panels |
| `--radius-xl` | 16px | Modals, large dialogs |

### Shadow

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.3)` | Subtle elevation |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | Cards |
| `--shadow-lg` | `0 8px 24px rgba(0,0,0,0.5)` | Modals, popovers |

### Transitions

| Token | Value | Usage |
|-------|-------|-------|
| `--transition-fast` | `80ms ease-out` | Button press |
| `--transition-base` | `160ms ease-out` | Panel enter |
| `--transition-slow` | `220ms ease-out` | Dropdown, popover |

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA (Start) | `Start Bot` |
| Primary CTA (Stop) | `Stop Bot` |
| Danger CTA (Emergency Stop) | `Emergency Stop` |
| CTA (Restart Backend) | `Restart Backend` |
| Empty state heading | `No active match` |
| Empty state body | `Start the bot to begin tracking combat events.` |
| Error state heading | `Connection lost` |
| Error state body | `Backend is not responding. Try restarting the backend.` |
| Destructive confirmation | `Emergency Stop: This will halt all bot actions immediately. Continue?` |
| Toast (save success) | `Settings saved` |
| Toast (save error) | `Failed to save — check logs` |
| Toast (backend restart) | `Backend restarting...` |
| Toast (webhook test) | `Test sent` or `Webhook not configured` |
| Tray tooltip | `Zedsu — {STATUS}` |

---

## Layout

### Shell Layout (Main Window — 900x700px default)

```
┌─────────────────────────────────────────────────────┐
│ Top Command Bar (48px fixed)                       │
├────────────┬──────────────────────────────────────┤
│ Sidebar    │ Main Panel                           │
│ (200px)   │ (flexible)                           │
│            │                                      │
│ Overview   │ Cards / tables / forms               │
│ Combat AI  │                                      │
│ Detection  │                                      │
│ Positions  │                                      │
│ Discord   │                                      │
│ YOLO      │                                      │
│ Telemetry │                                      │
│ Logs      │                                      │
│ ──────    │                                      │
│ Settings  │                                      │
└────────────┴──────────────────────────────────────┘
```

### HUD Overlay (Separate Window — ~360x120px)

```
┌──────────────────────────────────────────┐
│ ● RUNNING | ENGAGED | 42ms  │ Match #12 │
│ Kills 3 | 08:42 | Intent: engage     │
│ Crowd 0.78                             │
└──────────────────────────────────────────┘
```

### Responsive
- Shell: min-width 800px, sidebar collapses to icons at 900px
- HUD: fixed compact size, positions dynamically via corner settings
- No mobile — desktop operator tool only

---

## Components

### Cards

| Component | Description |
|-----------|-------------|
| `MetricCard` | Single metric display: label + value + optional trend |
| `SectionCard` | Grouped content: title + content slot + optional actions |
| `StatusBadge` | Pill badge: dot + label (color-coded by status) |
| `HealthBadge` | Backend health indicator: dot + label (OK/Warning/Error) |

### Navigation

| Component | Description |
|-----------|-------------|
| `SidebarNav` | Left sidebar, 200px, collapsible to 56px icon-only |
| `NavItem` | Single nav entry: icon + label + active indicator (cyan left border) |
| `TopCommandBar` | Fixed top bar: status pill + match info + primary actions |

### Forms

| Component | Description |
|-----------|-------------|
| `SettingRow` | Label + control + optional description (horizontal layout) |
| `Toggle` | Styled checkbox toggle, cyan when on |
| `SegmentedControl` | Tab-like button group for mutually exclusive options |
| `Input` | Text input with border, focus ring in cyan |
| `DangerButton` | Red background, white text, for destructive actions |

### Data Display

| Component | Description |
|-----------|-------------|
| `RegionRow` | Region name + status + test/pick/reset actions |
| `PositionRow` | Position name + enabled toggle + pick/delete actions |
| `LogViewer` | Scrollable log output with filter controls |
| `EventTimeline` | Vertical timeline of recent events |

### Overlays

| Component | Description |
|-----------|-------------|
| `Toast` | Bottom-right notification, auto-dismiss 3s |
| `ConfirmDialog` | Modal confirmation for destructive actions |
| `HUDOverlay` | Compact HUD rendered in separate Tauri window |

---

## Motion

| Interaction | Animation |
|------------|-----------|
| Card/panel enter | `opacity 0→1 + translateY(8px→0), 160-220ms ease-out` |
| Dropdown open | Scale from origin point, 160ms ease-out |
| Button press | `scale(0.98), 80ms` |
| Toast enter | `translateX(100%→0), 200ms ease-out` |
| Toast exit | `translateX(0→100%), 200ms ease-out` (same direction) |
| HUD status pulse | ONLY for error/warning: `opacity pulse 1→0.6→1, 1.5s`, NOT continuous |
| Nav sidebar collapse | `width 200px→56px, 220ms ease-out` |

**Rules:**
- No bounce/elastic easing
- No continuous animations on operational screens
- No scroll animations
- HUD pulse ONLY on error/warning states

---

## Shell Pages

### Overview (Default/Landing)
- Runtime: Bot status, Backend health (HealthBadge), Uptime, Active window, Setup issues count
- Current Match: Match #, Combat state (StatusBadge), Kills, Elapsed time, Last event
- Combat AI: Intent, Crowd risk %, Target memory, Last death reason
- Detection: HSV regions health, YOLO model availability, Detection latency
- Discord: Webhook configured, Events enabled, Last send status
- **Setup CTA:** If setup issues > 0: prominent "Fix setup issues" button

### Combat AI
- Telemetry: enable/disable, open runs folder, snapshot on death
- Target Memory: enable/disable, lost grace seconds, switch penalty
- Situation Model: crowd risk threshold slider, nearby/visible enemy counts
- Movement Policy: scored/random fallback toggle, repeated action penalty slider
- Death Classifier: enable/disable, last death reason display

### Combat Detection
- Smart Combat: enable toggle, first-person camera toggle, test button
- Regions: list of RegionRow components for each combat region
  - Status: enabled (green dot) / missing (red dot) / invalid (amber dot)
  - Actions: test region, pick region, reset

### Positions
- List of PositionRow components for each combat position (9 total)
- Each: label, enabled toggle, pick position, resolve/test, delete

### Discord
- Webhook: has_webhook indicator (green check / red X), test button
- Events: individual toggles for match_end, kill_milestone, combat_start, death, bot_error
- Kill milestones: chip editor (default: 5, 10, 20)
- **NEVER display webhook URL after save**

### YOLO
- Model: available indicator, quality score, model path
- Capture: capture class, capture count, Start/Stop capture button
- Models: list of available models, activate button

### Logs
- Live log viewer (auto-scroll)
- Filter: All / Info / Warn / Error
- Actions: Copy diagnostics, Open log folder, Clear view

### Settings (System)
- Backend: Restart Backend button, Stop button
- Config: Export config, Import config
- About: Version, Uptime

---

## HUD Contract

### Compact Mode (~360x80px)
```
┌──────────────────────────────────────────┐
│ ● RUNNING  ENGAGED           42ms        │
│ Match #12   Kills 3         08:42        │
└──────────────────────────────────────────┘
```
- Row 1: Status dot + State + Detection latency
- Row 2: Match # + Kills + Elapsed

### Expanded Mode (~360x120px)
```
┌──────────────────────────────────────────┐
│ ● RUNNING  ENGAGED           42ms       │
│ Match #12   Kills 3         08:42       │
│ Intent: engage · Crowd 0.78             │
│ YOLO: OK                                │
└──────────────────────────────────────────┘
```
- Row 3 (expanded only): Intent + Crowd risk + YOLO status

### Positioning
- Corner settings: top-right (default), top-left, bottom-right, bottom-left
- Formula: `x = monitor.x + monitor.width - hud.width - margin(16px)`, `y = monitor.y + margin(16px)`
- Opacity: slider 70-100%, default 90%
- Position saved to config.json: `hud.corner`, `hud.opacity`

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|---------|-------------|-------------|
| Lucide Icons | SVG icons | Not required (no external registry) |
| Google Fonts | Space Grotesk, Geist Sans, JetBrains Mono | Not required (CDN fonts, no user data) |

No third-party component libraries. No shadcn/ui. Pure HTML/CSS/JS.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending

---

*Phase: 13-zedsu-operator-shell-redesign*
*UI Design Contract generated: 2026-04-25*
