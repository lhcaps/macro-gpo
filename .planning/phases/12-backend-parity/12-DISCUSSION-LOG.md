# Phase 12: ZedsuBackend Feature Parity - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 12-backend-parity
**Areas discussed:** Region Selector, Discord Webhook, Combat Position Picker

---

## Scope Selection

| Option | Description | Selected |
|--------|-------------|----------|
| Top 3 only | Smart Region Selector, Discord Webhook, Combat Position Picker | |
| Top 5 | Top 3 + Hotkey Management + Walk Recording | |
| All major gaps | All 8 major features | |
| Full parity | All 18 features | ✓ |

**User's choice:** Top 3 features (Smart Region Selector, Discord Webhook, Combat Position Picker)
**Notes:** User provided detailed descriptions for each feature in Vietnamese.

---

## Area 1: Smart Region Selector (Vision Optimization)

| Question | Options Presented | Selected |
|----------|-----------------|----------|
| UI Type | Single-click selector (đơn giản) | |
| | Drag-to-select box (Bridger pattern) | ✓ |
| | Drag box + zoom lens (Bridger tối ưu) | |
| Multiple Regions? | Một vùng duy nhất | |
| | Nhiều vùng được đặt tên | ✓ |
| Integration | ZedsuBackend (recommended) | ✓ |
| | Tauri Frontend | |
| | Chỉ Backend, cổng qua command | |
| Storage | Nested trong config.json (recommended) | ✓ |
| | File riêng (assets/regions.json) | |
| Hotkey | F5 — Start/Stop toggle | |
| | F6 — Region selector | ✓ |
| | F7 — Settings window | |

**User's choices:**
- UI Type: **Drag-to-select box (Bridger pattern)** — Cân bằng giữa đơn giản và chính xác. Bỏ zoom lens để giảm complexity.
- Multiple Regions: **Nhiều vùng được đặt tên** — Cho phép user tạo regions khác nhau cho combat, lobby, etc.
- Integration: **ZedsuBackend** — Tích hợp trong backend thread, không phải Tauri frontend.
- Storage: **Nested trong config.json** — Giữ tất cả config ở một chỗ.
- Hotkey: **F6** — F5=Start/Stop, F6=Region selector, F9=Settings. Note: Phase 10 định nghĩa F1-F4, F6-F9 trống cho Phase 12.

---

## Area 2: Advanced Discord Webhook

| Question | Options Presented | Selected |
|----------|-----------------|----------|
| Enhancement Type | Basic — Event types + inline base64 | ✓ |
| | Enriched — Embeds + color + thumbnail + base64 | |
| Events | 3 events: match end, kill milestone, bot error | |
| | 5 events: + combat start, death | |
| Webhook Method | Giữ nguyên send_discord utility (recommended) | ✓ |
| | Di chuyển inline vào ZedsuBackend | |

**User's choices:**
- Enhancement Type: **Basic** — Inline base64, rich embed với title/description/color, đủ cho combat bot.
- Events: **5 events với UI toggle tab** — match_end, kill_milestone, combat_start, death, bot_error. Mỗi event có toggle riêng trong Settings UI tab.
- Webhook Method: **Giữ nguyên send_discord utility** — Không refactor, chỉ thêm event types và inline base64 support.

**User's specific requirement:** "Tôi muốn có 1 tab Discord trong UI để có thể thoải mái trong việc dán webhook hay là lựa chọn những thông tin nào được bật tắt" — Discord UI tab trong Settings với toggle controls cho từng event type.

---

## Area 3: Combat Position Picker

| Question | Options Presented | Selected |
|----------|-----------------|----------|
| Positions | Một position picker đa năng | |
| | Nhiều named positions (recommended) | ✓ |
| Coords Format | Absolute pixel coords | |
| | Relative coords [0-1] (recommended) | ✓ |
| Access | Hotkey + UI button | |
| | Chỉ trong Settings UI | ✓ |

**User's choices:**
- Positions: **Nhiều named positions** — Cho phép user tạo positions khác nhau (melee, skill_1, skill_2, etc.).
- Coords: **Relative coords [0-1]** — Scale được theo window resolution, giống Bridger pattern.
- Access: **Settings UI only** — Không có hotkey riêng, chỉ trigger từ Settings. Đơn giản hóa.

---

## Feature Gap Analysis (Full Comparison)

BridgerBackend vs ZedsuBackend:

| Feature | Bridger | Zedsu | Gap |
|---------|---------|--------|-----|
| OCR Region Selector | Full OcrRegionSelector class | Missing | **CRITICAL** |
| Combat Position Picker | PositionPicker class | Missing | **CRITICAL** |
| Hotkey Management | _register_hotkeys + rebind | Missing | **CRITICAL** |
| Walk Recording/Playback | Full CRUD commands | Missing | MAJOR |
| Audio Monitoring (RMS) | _cb_score callback | Missing | MAJOR |
| Tkinter Status Overlay | BridgerStatusOverlay | Missing | MAJOR |
| Global GUI Settings | global_gui_settings block | Missing | MAJOR |
| Focus Roblox Window | _focus_roblox_window | Missing | MAJOR |
| YOLO Training Pipeline | Missing | Full (Phase 11) | ZEDSUSCORE |
| Combat State Detection | Missing | Full (Phase 5) | ZEDSUSCORE |
| Pause/Resume | Missing | Commands (lines 575-583) | ZEDSUSCORE |

---

## Agent's Discretion

Areas deferred to Phase 12 planning:
- Chi tiết UI layout của Discord toggle tab
- Chi tiết xem region/position list hiển thị ở đâu trong Settings
- Cú pháp hotkey F6 implementation
- Số lượng tối đa regions/positions cho phép
- Chi tiết validation khi user nhập webhook URL
- Chi tiết "Test" button behavior cho Discord

---

## Deferred Ideas

### From Discussion
- **Walk recording/playback** — Useful for consistent movement patterns. Suggest: Phase 15 (after Phase 14 production build)
- **Audio RMS monitoring** — FPS combat bot doesn't need audio detection
- **Tkinter status overlay** — Will be replaced by Tauri HUD (Phase 13-14)
- **Hotkey management (backend-level)** — Phase 10 already has F1-F4, full hotkey management deferred to Phase 13
- **YouTube subscribe gating** — Not relevant to combat bot, permanently out of scope
- **Force close Roblox** — Nice-to-have safety feature, deferred to Phase 13 or 14
- **Monitor enumeration in /state** — Not needed for combat bot
- **Config reset to defaults** — Nice-to-have, deferred to Phase 14
- **Multi-detection method config** — Phase 8/11 already has YOLO + OpenCV layers
- **Per-stat tracking** — Combat bot doesn't have timeout streaks like fishing macro

### Scope Creep Redirected
- Full OCR with Tesseract — Zedsu uses YOLO, not OCR text recognition
- Automatic training — User prefers CLI for training (Phase 11 decision)

---

## Canonical References Established

- `src/zedsu_backend.py` — Primary implementation file (Tier 2)
- `bridger_source/src/BridgerBackend.py` — Reference patterns: OcrRegionSelector, PositionPicker, _cb_webhook
- `src/core/vision.py` — CombatSignalDetector integration point
- `src/utils/discord.py` — send_discord utility to extend
- `.planning/phases/09-3-tier-architecture/09-CONTEXT.md` — Architecture context
- `.planning/phases/10-rust-gui/10-CONTEXT.md` — Hotkey context (F1-F4 existing)
