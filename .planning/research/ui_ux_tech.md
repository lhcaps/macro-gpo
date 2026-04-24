# UI/UX and Tech Stack Research - Zedsu v2

**Project:** Zedsu - Grand Piece Online Battle Royale Macro
**Researched:** April 2026
**Overall Confidence:** MEDIUM-HIGH

---

## Executive Summary

Zedsu v2 needs a UX overhaul that balances "simple but not ugly" per user feedback. This research evaluates framework options, UI patterns, and migration strategies. **Key recommendation: Incrementally upgrade to CustomTkinter (ctk) now** for immediate visual improvement without disrupting the existing bot_engine/state machine architecture. Defer full framework migration to v3 unless major refactoring is planned.

The current codebase has good bones—working window binding, coordinate profiles, and a functional state machine. The UI is the weak point, and it's the lowest-effort, highest-impact change available.

---

## 1. Framework Comparison

### Comparison Matrix

| Framework | Startup | EXE Impact | System Tray | Hot Reload | Learning Curve | Maintenance |
|-----------|---------|------------|-------------|------------|----------------|-------------|
| **Tkinter** (current) | ~100ms | ~5-10 MB | Manual/wxiconify | No | Low | Built-in |
| **CustomTkinter (ctk)** | ~120ms | ~5-10 MB | Manual | No | Low | Active (2026) |
| **PyQt6/PySide6** | ~300ms | ~50-80 MB | Built-in | No | Medium-High | Active |
| **DearPyGui** | ~80ms | ~20-30 MB | Limited | No | Medium | Active |
| **Eel** | ~500ms | ~60-100 MB | Manual | Yes | Medium | Unmaintained |
| **Flet** | ~1-2s | ~30-50 MB | Built-in | Yes | Low-Medium | Very Active |

### Detailed Analysis

#### Tkinter (Current)
**Status:** Built-in Python stdlib
**Pros:**
- Zero installation overhead
- Fastest startup possible for Python GUI
- Full control over window management (iconify, tray, etc.)
- Works with pystray for system tray
- Proven with PyInstaller (current build works)

**Cons:**
- Dated "Windows 95" appearance by default
- Requires manual theming (current dark theme is custom-built)
- No native HiDPI scaling without manual DPI handling
- Limited widget set compared to Qt

**Verdict:** Keep as fallback. Upgrade path available.

#### CustomTkinter (ctk) ⭐ RECOMMENDED for v2
**Status:** Actively maintained (Feb 2026), 13K+ GitHub stars
**Pros:**
- Drop-in replacement for most Tkinter widgets
- Modern, clean appearance out of the box
- Built-in dark/light themes
- Same API as Tkinter (easy migration)
- HiDPI support built-in
- No new dependencies (same `tkinter` base)
- Can keep existing window management code

**Cons:**
- Known rendering performance issues with complex interfaces
- Widgets can render one-by-one during initialization
- Resize events can cause lag

**Verdict:** **Best immediate upgrade path.** Same dependencies, modern look, minimal code changes. The rendering slowness is manageable with proper initialization ordering.

#### PyQt6/PySide6
**Status:** Professional Qt bindings, actively maintained
**Pros:**
- Professional-grade UI components
- Built-in system tray, notifications, menus
- Signal/slot pattern for clean event handling
- Modern styling with Qt Stylesheets (QSS)

**Cons:**
- 50-80 MB EXE size increase
- 300ms+ startup time
- Complex licensing (PyQt6 GPL/commercial, PySide6 LGPL)
- Steep learning curve for Qt-specific patterns
- Massive change to existing architecture

**Verdict:** Consider for v3 if professional distribution is planned. Not worth the migration cost for v2.

#### DearPyGui
**Status:** GPU-accelerated, actively maintained
**Pros:**
- Fastest rendering (GPU-accelerated)
- Real-time dashboard capability
- Excellent for data visualization
- Sub-millisecond draw calls

**Cons:**
- Gaming/immediate-mode UI paradigm (different from traditional GUI)
- Limited native widgets (not a traditional app feel)
- System tray support is limited/experimental
- Would require complete UI rewrite

**Verdict:** Interesting for a debug/performance overlay, but not suitable as primary UI framework.

#### Eel
**Status:** **Unmaintained** - no active development
**Pros:**
- Web technologies for UI (HTML/CSS/JS flexibility)
- Hot reload during development
- Modern styling possible

**Cons:**
- **Project is effectively abandoned**
- Large EXE footprint (bundles Chrome)
- 500ms+ startup time
- Memory leaks documented in v0.18.1
- Complex build setup with modern frontend tools

**Verdict:** Do not use. Unmaintained + heavy dependencies = technical debt.

#### Flet
**Status:** Very active development, Flutter-based
**Pros:**
- Cross-platform by default
- Modern UI with minimal code
- Built-in system tray, notifications
- Hot reload in development

**Cons:**
- 1-2 second startup time (Flutter initialization)
- 30-50 MB EXE impact
- Complete rewrite required
- Different paradigm from Tkinter

**Verdict:** Good for future cross-platform expansion, but startup time is unacceptable for a macro that users want "instant-on."

---

## 2. Minimal-Beautiful UI Design

### What Makes a Macro UI Feel "Professional"

Based on gaming macro and automation tool research:

| Aspect | Janky | Professional |
|--------|-------|--------------|
| **Borders** | Thick 3D beveled borders | Subtle 1px borders or no borders with depth colors |
| **Spacing** | Uneven, cramped | Consistent padding (8px grid system) |
| **Colors** | Pure black, harsh whites, random accent colors | Dark gray (#1C1C1E), muted text, strategic accent |
| **Buttons** | Default Tkinter gray, beveled | Rounded corners (8px), color-coded states |
| **Typography** | Varying sizes, no hierarchy | Clear hierarchy: 14px labels, 11px metadata |
| **Icons** | None or pixelated | Simple monochrome SVG or emoji icons |
| **Animations** | None or jarring | Subtle fade transitions, smooth state changes |

### Dark Theme Best Practices (2026)

**Color Palette for Automation Tools:**
```
Background:      #1C1C1E (not pure black - reduces eye strain)
Surface:         #2C2C2E (cards, panels)
Elevated:        #3A3A3C (buttons, inputs)
Border:          rgba(255, 255, 255, 0.08)
Text Primary:    #FFFFFF
Text Secondary:  #A1A1A6
Text Muted:      #6E6E73
```

**Accent Color Usage (limit to 5% of UI):**
```
Success/Run:     #30D158 (green)
Error/Stop:      #FF453A (red)
Warning:         #FFD60A (yellow)
Info/Active:     #0A84FF (blue)
```

### Color Coding for Bot States

| State | Color | Usage |
|-------|-------|-------|
| **Idle/Stopped** | Gray (#6E6E73) | Default state, nothing happening |
| **Running** | Green (#30D158) | Bot active, scanning |
| **In Match** | Blue (#0A84FF) | Combat detected, actively playing |
| **Warning** | Yellow (#FFD60A) | Low confidence detection, retrying |
| **Error** | Red (#FF453A) | Critical failure, needs attention |
| **Iconified** | Orange (#FF9F0A) | Window minimized to tray |

### Minimal HUD Design Principles

1. **Information Hierarchy:**
   - Primary: Bot state (big, colored, center-top)
   - Secondary: Match count, time in match (smaller, below)
   - Tertiary: Last action (single line, bottom)

2. **Compact Layout:**
   - No wasted space, but breathing room between sections
   - 8px grid for spacing consistency
   - Single-column layout for macro UIs (wider than tall)

3. **At-a-Glance Readability:**
   - State should be identifiable from 3 meters away
   - Color communicates state before text is read
   - No scrolling required for essential info

---

## 3. System Tray and Runtime UX

### Recommended System Tray Implementation

**Using pystray (cross-platform, well-maintained):**

```python
from pystray import Icon, Menu, MenuItem
from PIL import Image, ImageDraw

def create_tray_icon(status="idle"):
    # Generate colored icon based on status
    image = Image.new('RGB', (64, 64))
    draw = ImageDraw.Draw(image)
    colors = {
        "idle": (110, 110, 115),
        "running": (48, 209, 88),
        "error": (255, 69, 58)
    }
    draw.ellipse((8, 8, 56, 56), fill=colors.get(status, colors["idle"]))
    return image

def setup_tray(app):
    icon = Icon("Zedsu")
    icon.icon = create_tray_icon("idle")
    icon.menu = Menu(
        MenuItem("Zedsu - Idle", None, enabled=False),
        MenuItem("Start", lambda: app.start()),
        MenuItem("Stop", lambda: app.stop()),
        MenuItem("Show Window", lambda: app.deiconify()),
        Menu.SEPARATOR,
        MenuItem("Exit", lambda: app.quit())
    )
    return icon
```

### Tray Menu Actions

| Menu Item | Action | Rationale |
|-----------|--------|----------|
| Status display | Disabled label | Shows current state without clicking |
| Start/Stop | Toggle bot | Primary control |
| Show Window | `deiconify()` | Restore from minimized |
| Exit | Full shutdown | Clean quit, not just hide |

### Balloon Notifications

Windows toast notifications for:
- Match started (optional, can spam)
- Match ended with stats (useful)
- Critical errors requiring attention (important)
- "Started" / "Stopped" confirmations (helpful)

### Additional UX Enhancements Macro Users Want

1. **Quick toggle hotkey** - F1 already works, but visual indicator would help
2. **Match statistics on exit** - "Session stats: X matches, Y minutes"
3. **Pause instead of stop** - Maintain state for quick resume
4. **Run count limits** - Stop after N matches (anti-AFK detection)
5. **Screenshot on death** - Debug why bot died

---

## 4. Performance Dashboard

### Minimal Status Display During Combat

**Recommended minimal metrics:**

| Metric | Display | Update Frequency |
|--------|---------|-----------------|
| **Bot State** | LOBBY / COMBAT / DEAD / WAITING | Real-time |
| **Match #** | "Match 5" | On match start |
| **Time in Match** | "2:34" (MM:SS) | Every second |
| **Detection FPS** | "~15 fps" | Every 5 seconds |
| **Last Action** | "Clicked LOBBY_BTN at (450, 320)" | On action |

### Suggested UI Layout

```
┌─────────────────────────────────────────┐
│  ● COMBAT           Match 5  ⏱ 2:34    │  <- Status bar
├─────────────────────────────────────────┤
│  [▶ START]                              │  <- Big button
├─────────────────────────────────────────┤
│  Last: Clicked LOBBY_BTN @ (450, 320)  │  <- Single log line
└─────────────────────────────────────────┘
```

### What NOT to Show

- Full scrolling log (clutter, no value during combat)
- Asset thumbnails (take space, obvious)
- Coordinate grids (debug info, not user info)
- Detailed config panels (setup only, not runtime)

---

## 5. Migration Architecture

### Current State Assessment

```
src/
├── core/
│   ├── bot_engine.py    1018 lines  ⚠️ Needs refactoring (state machine)
│   ├── vision.py         541 lines  ⚠️ Uses pyautogui (consider replacing)
│   └── controller.py      37 lines  ✓ Works fine
├── ui/
│   ├── app.py           1029 lines  ⚠️ All UI in one file
│   └── components.py     109 lines  ✓ Good separation
├── utils/
│   ├── config.py         858 lines  ⚠️ Complex but functional
│   ├── windows.py          ? lines  ✓ Window detection works
│   ├── discord.py          ? lines  ✓ Webhook works
│   └── run_analysis.py     ? lines  ✓ Debug tool
└── main.py                27 lines  ✓ Clean entry point
```

### Tech Debt Priorities

| Priority | Component | Issue | Recommended Action |
|----------|-----------|-------|-------------------|
| **HIGH** | `vision.py` | Uses pyautogui (slow, screenshot-heavy) | Consider mss + OpenCV for faster capture |
| **HIGH** | `app.py` | 1029 lines, all UI in one file | Split into views/pages |
| **MEDIUM** | `bot_engine.py` | 1018 lines, state machine mixed with UI calls | Extract pure state machine |
| **MEDIUM** | `config.py` | 858 lines, complex but works | Add type hints, docstrings |
| **LOW** | `components.py` | Good separation already | Extend as needed |

### Migration Strategy: Incremental

#### Phase 1: UI Facelift (Immediate, Low Risk)
1. Install `customtkinter`
2. Replace tkinter imports with ctk
3. Update widget instantiation (`tk.Button` → `ctk.CTkButton`)
4. Apply new dark theme colors
5. Test existing functionality

**Expected time:** 1-2 days
**Impact:** High visual improvement, zero behavior change

#### Phase 2: UI Refactor (Short-term, Medium Risk)
1. Split `app.py` into:
   ```
   ui/
   ├── views/
   │   ├── main_view.py      # Status + Start/Stop
   │   ├── settings_view.py  # Configuration panel
   │   └── log_view.py       # Debug log
   ├── __init__.py
   └── app.py                # Controller, navigation
   ```
2. Apply MVC-like pattern
3. Keep business logic in core/

**Expected time:** 3-5 days
**Impact:** Maintainable code, same appearance

#### Phase 3: Vision Upgrade (Medium-term, Medium Risk)
1. Replace pyautogui with `mss` + `OpenCV`
2. Benefits: 3-5x faster screenshot capture
3. Keep same detection interface

**Expected time:** 2-3 days
**Impact:** Faster bot, more responsive

#### Phase 4: State Machine Extraction (Long-term, Low Risk)
1. Extract BotEngine into pure state machine
2. Use `python-statemachine` library or custom implementation
3. UI becomes pure observer

**Expected time:** 5-7 days
**Impact:** Testable logic, clean architecture

---

## 6. IRUS Neural UI Reference

### What Works from IRUS

| Pattern | Zedsu Should Adopt |
|---------|-------------------|
| **Tabbed interface** | Settings / Log / Debug tabs |
| **JSON config storage** | Already using config.json ✓ |
| **Colored state indicators** | Red/Blue/Green status colors |
| **Progress indication** | Loading states for asset capture |
| **Debug overlay** | Optional debug canvas for detection viz |

### What to Avoid

- Over-complex settings hierarchy
- Too many tabs (3-4 max)
- Bloated asset storage
- Slow loading of YOLO models (Zedsu uses template matching, different)

---

## 7. Recommended Stack for v2

### Immediate (v2.0)

| Component | Choice | Rationale |
|-----------|--------|-----------|
| **UI Framework** | CustomTkinter 5.x | Modern look, same deps, easy migration |
| **System Tray** | pystray | Well-maintained, cross-platform |
| **Notifications** | win10toast or plyer | Lightweight Windows toasts |
| **Build Tool** | PyInstaller | Already working, don't fix what isn't broken |

### Future Considerations (v3.0)

| Component | Consider | Notes |
|-----------|----------|-------|
| **Vision** | mss + OpenCV | Faster than pyautogui |
| **State Machine** | python-statemachine | Cleaner bot logic |
| **Build** | Nuitka | Smaller EXE, faster startup |

### Anti-Recommendations (Avoid)

| Option | Why Not |
|--------|---------|
| **Eel** | Unmaintained, heavy |
| **Flet** | Slow startup (1-2s), complete rewrite |
| **PyQt6** | Heavy deps, licensing complexity |
| **DearPyGui** | Not a traditional app UI |

---

## 8. Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Framework Comparison | MEDIUM-HIGH | Multiple sources agree, some metrics estimated |
| UI Design Patterns | HIGH | Well-documented best practices |
| System Tray | HIGH | pystray is standard, documented |
| Migration Strategy | MEDIUM | Based on code structure analysis |
| Performance Metrics | MEDIUM | Exact numbers vary by system |

---

## 9. Open Questions

1. **pyautogui replacement:** Is mss + OpenCV significantly faster for template matching? Need benchmark.
2. **CustomTkinter rendering:** Does the one-by-one widget rendering issue affect UX in practice? Need testing.
3. **Config migration:** Will config.json format remain compatible across UI changes?
4. **Global hotkey priority:** Does F1 work reliably when game is focused? User testing needed.

---

## 10. Sources

| Source | Confidence | Used For |
|--------|------------|----------|
| CustomTkinter GitHub (TomSchimansky) | HIGH | Framework capabilities |
| python-statemachine docs | HIGH | State machine patterns |
| LayoutScene Dark Mode Guide 2026 | HIGH | UI design principles |
| pystray documentation | HIGH | System tray implementation |
| PyInstaller vs Nuitka benchmarks (x321.org) | MEDIUM | Build size comparison |
| Framework comparison articles (Medium/Stackademic) | MEDIUM | General framework analysis |
| DearPyGui official docs | HIGH | Performance characteristics |
