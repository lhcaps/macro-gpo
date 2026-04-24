# Phase 12: ZedsuBackend Feature Parity - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 12 đảm bảo ZedsuBackend có đầy đủ features từ BridgerBackend. Mang 3 key capabilities từ Bridger vào Zedsu: region selector cho vision optimization, Discord webhook nâng cấp, và combat position picker. Tất cả tích hợp vào ZedsuBackend tier.

**Scope:** 3 features chính:
1. Smart Region Selector — drag-to-select box cho vision optimization
2. Advanced Discord Webhook — inline base64, multiple event types, UI toggle tab
3. Combat Position Picker — multiple named positions, relative coords

**Out of scope:**
- Full OCR với Tesseract (Zedsu dùng YOLO, không cần OCR text recognition)
- Walk recording/playback (future phase)
- Audio monitoring (FPS combat không cần audio)
- Tkinter status overlay (sẽ thay bằng Tauri HUD ở Phase 13-14)
- Hotkey management cho backend (Phase 10 đã có F1-F4, F6-F9 dùng cho Phase 12)
- YouTube subscribe gating (không cần cho combat bot)
- Force close Roblox, monitor enumeration, config reset (nice-to-have, defer)
</domain>

<decisions>
## Implementation Decisions

### 12a: Smart Region Selector (Vision Optimization)

**D-12a-01:** Drag-to-select box selector — Bridger pattern cơ bản. Chụp full-screen screenshot làm nền, cho user kéo thả chuột để chọn vùng, không có zoom lens.

**D-12a-02:** Multiple named regions — User có thể tạo nhiều regions với tên riêng (VD: `combat_center`, `lobby_scan`, `ultimate_bar`). Mỗi region lưu normalized coords [x1, y1, x2, y2] trong 0-1 range.

**D-12a-03:** Tích hợp trong ZedsuBackend (không phải Tauri frontend). Region selector chạy trong backend thread, kích hoạt qua command `select_region` + hotkey F6.

**D-12a-04:** Storage: Nested trong `config.json` dưới key `combat_regions: {region_name: [x1, y1, x2, y2]}`. Tất cả normalized coordinates [0-1] để scale theo mọi resolution.

**D-12a-05:** Hotkey F6 gọi region selector. User chọn tên region → kéo thả vùng → Enter confirm, Esc cancel.

**D-12a-06:** Combat regions được dùng bởi `CombatSignalDetector` và `_ZedsuBotEngine` — thay thế hardcoded pixel coords bằng configurable named regions.

**D-12a-07:** Backend endpoint `POST /command {action: "select_region", payload: {name: "region_name"}}` trigger region selector. Endpoint `POST /command {action: "get_regions"}` trả về dict tất cả regions.

### 12b: Advanced Discord Webhook

**D-12b-01:** Inline base64 screenshot — Không lưu file tạm. Chụp MSS screenshot → convert PNG → base64 encode → embed trực tiếp vào Discord message image field: `{"image": {"url": "data:image/png;base64,..."}}`. Không tạo file trên đĩa.

**D-12b-02:** 5 event types với UI toggle tab:
- `match_end` — Kết thúc match (existing)
- `kill_milestone` — Đạt 5/10/15/20 kills
- `combat_start` — Bắt đầu combat (INCOMBAT timer detected)
- `death` — Bị hạ gục
- `bot_error` — Bot gặp lỗi cần attention

**D-12b-03:** Rich embed format cho mỗi event:
```
{
  "title": "[EVENT_TYPE] Zedsu Bot",
  "description": "Event-specific message",
  "color": EVENT_COLOR (hex),
  "image": {"url": "data:image/png;base64,..."},
  "timestamp": ISO timestamp
}
```

**D-12b-04:** Event colors: match_end=0x16a34a (green), kill_milestone=0xf59e0b (amber), combat_start=0x3b82f6 (blue), death=0xef4444 (red), bot_error=0xdc2626 (dark red).

**D-12b-05:** UI toggle tab trong Settings: 5 switches cho 5 event types + 1 master toggle (Discord enable/disable) + text field cho webhook URL. Tất cả lưu vào `config.json`.

**D-12b-06:** Giữ nguyên `src/utils/discord.py send_discord()` utility. Backend gọi `send_discord()` với webhook URL từ config, message, và optional base64 string.

**D-12b-07:** Kill milestone thresholds: 5, 10, 15, 20 kills — configurable trong Settings. Default: 5, 10, 20.

### 12c: Combat Position Picker

**D-12c-01:** Multiple named positions — User có thể tạo nhiều positions với tên riêng (VD: `melee_skill`, `dash_skill`, `ultimate_skill`). Mỗi position lưu `{x, y}` normalized [0-1] relative to window rect.

**D-12c-02:** Single-click transparent overlay — Không cần drag. User mở picker → click vào vị trí trên màn hình → coords được capture tại thời điểm click. Đơn giản hơn Bridger's `PositionPicker`.

**D-12c-03:** Tích hợp trong ZedsuBackend, kích hoạt từ Settings UI (không có hotkey riêng — chỉ từ Settings).

**D-12c-04:** Storage: Nested trong `config.json` dưới key `combat_positions: {position_name: {x: 0.485, y: 0.198}}`. Coordinates relative to window rect [0-1] để scale theo mọi resolution.

**D-12c-05:** Command `POST /command {action: "pick_position", payload: {name: "position_name"}}` trigger position picker. Endpoint `POST /command {action: "get_positions"}` trả về dict tất cả positions.

**D-12c-06:** Backend resolve position sang absolute pixel coords khi cần click — dùng `resolve_coordinate()` callback pattern từ Phase 9.

### Agent's Discretion
- Chi tiết UI layout của Discord toggle tab (trong Tkinter hay Tauri settings) — defer đến Phase 12 planning
- Chi tiết xem region/position list hiển thị ở đâu trong Settings — defer đến Phase 12 planning
- Cú pháp hotkey F6 implementation (keyboard module trong backend thread) — defer đến Phase 12 planning
- Số lượng tối đa regions/positions cho phép — defer đến Phase 12 planning
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture (Phase 9)
- `.planning/phases/09-3-tier-architecture/09-CONTEXT.md` — 3-tier decisions: port 9761, IPC commands, callback pattern
- `.planning/phases/09-3-tier-architecture/09-02-PLAN.md` — ZedsuBackend plan (Tier 2 extraction)

### Backend Integration
- `src/zedsu_backend.py` — ZedsuBackend implementation: port 9761, /state, /command endpoints, BackendCallbacks, Phase 11 YOLO capture
- `src/zedsu_core_callbacks.py` — CoreCallbacks Protocol: resolve_coordinate, locate_image, etc.
- `src/core/vision.py` — Vision pipeline: CombatSignalDetector, locate_image, capture_search_context
- `src/core/vision_yolo.py` — YOLODetector: CLASS_NAMES, detect(), validation helpers
- `src/utils/discord.py` — send_discord() utility: keeps webhook URL + file_path, sends to Discord

### Bridger Reference
- `bridger_source/src/BridgerBackend.py` — Bridger Backend: OcrRegionSelector (lines 451-604), PositionPicker (lines 398-427), _cb_webhook (lines 180-233), hotkey management (lines 279-334)

### Rust GUI (Phase 10)
- `src/ZedsuFrontend/src/lib.rs` — Frontend: BackendManager, HTTP IPC, Tauri commands
- `.planning/phases/10-rust-gui/10-CONTEXT.md` — Phase 10 decisions: HUD layout, hotkey bindings

### Planning Context
- `.planning/ROADMAP.md` — Phase 12 goal, depends on Phase 9
- `.planning/STATE.md` — Current state: Phase 11 complete, Phase 12 pending
- `.planning/REQUIREMENTS.md` — OPER-29 to OPER-33 requirements (detection, YOLO, system tray)

### YOLO Training (Phase 11)
- `.planning/phases/11-yolo-training/11-CONTEXT.md` — Phase 11 decisions: capture mode, CLI training, model management
- `src/zedsu_backend.py` lines 264-387 — Phase 11 helpers: _get_yolo_dataset_stats, _validate_yolo_model, _yolo_capture_loop
</canonical_refs>

<code_context>
## Existing Code Insights

### From Phase 9 (3-tier Architecture)
- ZedsuBackend chạy port 9761, có `/state` (GET) và `/command` (POST) endpoints
- BackendCallbacks implements CoreCallbacks — tất cả vision/controller calls đi qua callbacks
- `_state_lock` thread-safe cho global state
- Config lưu trong `_app_config` dict, load từ `config.json`

### From Phase 10 (Rust GUI)
- F1-F4 đã mapped trong Rust lib.rs: F1=emergency_stop, F2=toggle_HUD, F3=toggle_start_stop, F4=show_settings
- F6-F9 available cho Phase 12
- Tauri commands: `send_action(action, payload)` gọi backend `/command`

### From Phase 11 (YOLO Training)
- ZedsuBackend đã có `_yolo_capture_loop()` trong background thread với `threading.Thread(daemon=True)`
- Pattern: `POST /command {action: "yolo_capture_start", payload: {class_name: "..."}}` hoạt động tốt
- YOLO capture dùng `get_asset_capture_context()` để get window region

### Bridger Patterns (Reference)
- OcrRegionSelector: Tkinter Canvas, screenshot bg, draggable box, normalized [0-1] coords
- PositionPicker: Transparent Toplevel, single-click, normalized to monitor ratio
- _cb_webhook: base64 PNG via mss → PIL → base64 → embed image field
- _run_region_selector: threading.Thread(daemon=True).start()

### Integration Points
- Region selector output → CombatSignalDetector._get_region_bounds() thay thế hardcoded coords
- Position picker output → resolve_coordinate() callback trả về absolute pixel coords
- Discord events → BackendCallbacks.discord() với event type string + base64 image string
- F6 hotkey → backend thread → Tkinter overlay → POST /command "select_region"
</code_context>

<specifics>
## Specific Ideas

- **Vision optimization goal:** Region selector giảm scan area từ full screen (1920x1080) xuống small region (VD: 200x100) → YOLO inference nhanh hơn, combat detection chính xác hơn

- **Discord UI tab:** Tkinter settings có notebook với tab "Discord" — webhook URL text entry + 5 event toggles + "Test" button

- **Position naming convention:** Default positions: `melee`, `skill_1`, `skill_2`, `skill_3`, `ultimate` — mapped trong `config.json` combat_positions

- **Region naming convention:** Default regions: `combat_scan`, `lobby_scan`, `hp_bar`, `ultimate_bar` — thay thế hardcoded `_SEARCH_HINT_RATIOS` trong vision.py

- **Relative coords vs absolute:** Dùng window-relative [0-1] vì window có thể resize/relocate — giống Bridger's `ocr_region` pattern

- **No zoom lens:** Đơn giản hóa Bridger's OcrRegionSelector bằng cách bỏ zoom lens — drag-to-select box đủ cho nhu cầu
</specifics>

<deferred>
## Deferred Ideas

### From Discussion
- **Walk recording/playback** — Hữu ích cho consistent movement patterns, nhưng out of scope cho Phase 12. Đề xuất: Phase 15 (after Phase 14 production build)
- **Audio RMS monitoring** — FPS combat bot không cần audio detection, out of scope
- **Tkinter status overlay GUI** — Sẽ thay bằng Tauri HUD (Phase 13-14), không cần backend overlay
- **Hotkey management (backend-level)** — Phase 10 đã có F1-F4, hotkey management đầy đủ defer đến Phase 13 (System Tray)
- **YouTube subscribe gating** — Không liên quan đến combat bot, out of scope vĩnh viễn
- **Force close Roblox** — Nice-to-have safety feature, defer đến Phase 13 hoặc Phase 14
- **Monitor enumeration in /state** — Không cần cho combat bot, defer
- **Config reset to defaults** — Nice-to-have, defer đến Phase 14
- **Multi-detection method config** (pixel tolerance, scan delays) — Phase 8/11 đã có YOLO, OpenCV layers đủ cho combat
- **Per-stat tracking** (timeout streak, etc.) — Combat bot không có timeout streaks như fishing macro, out of scope

### Reviewed Todos (not folded)
None — không có pending todos matched Phase 12 scope.
</deferred>

---

*Phase: 12-backend-parity*
*Context gathered: 2026-04-24*
