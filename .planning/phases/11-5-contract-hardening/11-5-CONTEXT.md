# Phase 11.5: Contract & Runtime Hardening - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 11.5 lock contract giữa 3-tier: Frontend ↔ Backend ↔ Core. Không thêm feature mới. Chỉ fix 11 blockers đã verify từ brutal code review. Sau khi Phase 11.5 hoàn tất, Phase 12 (Region Selector, Discord Webhook, Position Picker) mới nên build trên nền contract đã khóa.

**Scope:** 11 critical blockers:
1. Frontend F1/F3 command mismatch vs backend
2. /health semantics lẫn process health với bot running state
3. /state HUD path sai (frontend đọc combat_state từ nested path không tồn tại)
4. Backend auto-starts core on launch (nên idle)
5. ThreadingHTTPServer không phải real threading
6. BackendCallbacks.safe_find_and_click signature mismatch
7. BackendCallbacks.click_saved_coordinate dùng locate_image chưa import
8. requirements.txt thiếu mss, numpy
9. YOLO ONNX parser sai output shape + không có NMS
10. validate_model_on_dataset không đọc recursive dataset
11. Config schema Phase 12 chưa khớp schema hiện tại

**Out of scope:**
- Thêm feature mới (Phase 12 territory)
- Refactor combat FSM logic
- Thay đổi detection algorithms
- Thay đổi build/packaging (Phase 14 territory)
- Thay đổi system tray (Phase 13 territory)
</domain>

<decisions>
## Implementation Decisions

### 11.5a: Backend Command Contract

**D-11.5a-01:** Backend command canonical set:
- `start` — launch core in daemon thread (backend idle until start)
- `stop` — signal stop, wait for thread join
- `toggle` — start if idle, stop if running (F3 maps to this)
- `emergency_stop` — stop + release all pressed keys + mark IDLE (F1 maps to this)
- `pause` — set pause event
- `resume` — clear pause event
- `reload_config` — reload from config.json
- `update_config` — merge partial config
- `get_config` — return stripped config (no secrets)

**D-11.5a-02:** Frontend F1 → `emergency_stop`, F3 → `toggle`. Không dùng `start`/`stop` trực tiếp từ hotkey.

**D-11.5a-03:** `emergency_stop` phải mạnh hơn `stop`: set `_running = False`, release pydirectinput keys, stop core loop, mark state IDLE.

### 11.5b: /health Semantics

**D-11.5b-01:** GET /health trả:
```json
{
  "status": "ok",
  "backend": "ok",
  "core": "idle|running|paused|error",
  "uptime_sec": 123,
  "version": "0.1.0"
}
```
Backend alive khi HTTP server chạy, không phụ thuộc bot running/stopped.

**D-11.5b-02:** Frontend health thread chỉ respawn khi HTTP không respond hoặc process chết.

### 11.5c: /state Canonical HUD Format

**D-11.5c-01:** Backend /state trả canonical `hud` object:
```json
{
  "backend": {"status": "ok", "uptime_sec": 123, "restart_count": 0},
  "core": {"state": "idle", "running": false},
  "hud": {
    "combat_state": "IDLE",
    "kills": 0,
    "match_count": 0,
    "detection_ms": 0,
    "elapsed_sec": 0,
    "status_color": "#475569"
  },
  "vision": {},
  "yolo_model": {},
  "config": {}
}
```

**D-11.5c-02:** Frontend get_hud_state() chỉ đọc `state.hud.combat_state`, không đọc `state.combat.combat_state`.

### 11.5d: Backend No Auto-Run on Launch

**D-11.5d-01:** Backend `main()` chỉ load config + start HTTP server. Không gọi `_launch_core()` tự động. Bot loop chỉ start khi nhận command `start` hoặc `toggle`.

**D-11.5d-02:** Backend có thể preload detector/model nhưng không chạy automation loop.

### 11.5e: ThreadingHTTPServer

**D-11.5e-01:** Dùng `http.server.ThreadingHTTPServer` thay vì self-made ThreadingMixIn:
```python
from http.server import ThreadingHTTPServer
server = ThreadingHTTPServer((HOST, PORT), ZedsuHandler)
```

### 11.5f: safe_find_and_click Signature Fix

**D-11.5f-01:** BackendCallbacks.safe_find_and_click phải gọi:
```python
return find_and_click(image_key, _app_config, self.is_running, self.log, confidence=confidence)
```
Đúng thứ tự: img_name, config, is_running_check, log_func, confidence.

### 11.5g: click_saved_coordinate Fix

**D-11.5g-01:** `click_saved_coordinate` phải import `locate_image` đúng cách:
```python
from src.core.vision import locate_image
result = locate_image(key, _app_config, None)
```
Hiện tại dùng `find_and_click` nhưng bên trong gọi `locate_image` chưa được import đúng scope.

### 11.5h: requirements.txt

**D-11.5h-01:** Thêm mss và numpy vào runtime dependencies. Build script đã hidden-import nhưng requirements.txt không có.

### 11.5i: YOLO ONNX Parser + NMS

**D-11.5i-01:** YOLO parser phải xử lý đúng YOLOv8/YOLO11 ONNX output format:
- Output thường dạng `(1, 84, 8400)` hoặc `(1, 14, 8400)` với 10 classes
- Transpose khi output.shape[0] không phải batch dimension
- Dùng `np.squeeze(output)` để bỏ batch dim
- Sau đó transpose nếu cần: `output.T`

**D-11.5i-02:** Thêm NMS sau detection:
```python
indices = cv2.dnn.NMSBoxes(boxes, scores, score_threshold, nms_threshold)
```
Để tránh duplicate boxes gây nhiễu combat signal.

### 11.5j: validate_model_on_dataset Recursive

**D-11.5j-01:** Validation đọc `os.listdir()` không recursive — sai nếu script tạo subfolder per class. Phải dùng `os.walk()` hoặc `rglob` để tìm tất cả ảnh trong train/images/ và val/images/.

### 11.5k: Config Schema Migration

**D-11.5k-01:** Thêm `combat_regions_v2` và `combat_positions` vào DEFAULT_CONFIG mà không phá `combat_regions` legacy:
```json
"combat_regions_v2": {},
"combat_positions": {},
"discord_events": {
  "enabled": false,
  "webhook_url": "",
  "events": {
    "match_end": true,
    "kill_milestone": true,
    "combat_start": false,
    "death": true,
    "bot_error": true
  },
  "kill_milestones": [5, 10, 20]
}
```

**D-11.5k-02:** Migration helper: đọc legacy `combat_regions` → convert sang `combat_regions_v2` format.
</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture (Phase 9)
- `.planning/phases/09-3-tier-architecture/09-CONTEXT.md` — 3-tier decisions: port 9761, IPC commands, callback pattern
- `.planning/phases/09-3-tier-architecture/09-02-PLAN.md` — ZedsuBackend plan (Tier 2 extraction)

### Backend Implementation
- `src/zedsu_backend.py` — ZedsuBackend: /state, /command endpoints, BackendCallbacks, ThreadingMixIn, _launch_core
- `src/zedsu_core.py` — ZedsuCore: ZedsuCore class, get_state(), start/stop/pause/resume
- `src/zedsu_core_callbacks.py` — CoreCallbacks Protocol

### Frontend Implementation (Phase 10)
- `src/ZedsuFrontend/src/lib.rs` — Frontend: BackendManager, send_command("emergency_stop"), send_command("toggle"), get_hud_state

### Vision
- `src/core/vision.py` — find_and_click signature: (img_name, config, is_running_check, log_func, clicks, ...)
- `src/core/vision_yolo.py` — YOLODetector: detect(), validate_model_on_dataset(), parse ONNX output

### Config
- `src/utils/config.py` — DEFAULT_CONFIG, load_config, save_config, get_combat_region

### Build
- `build_exe.py` — Build script với hidden-import mss, numpy
- `requirements.txt` — (verify xem có mss, numpy không)

### Bridger Reference
- `bridger_source/src/BridgerBackend.py` — OcrRegionSelector, PositionPicker, _cb_webhook pattern
</canonical_refs>

<code_context>
## Existing Code Insights

### Blocker 1: Frontend F1/F3 Command Mismatch (VERIFIED)

Frontend lib.rs lines 403-408 gọi:
```rust
mgr.send_command("emergency_stop", None);  // F1
mgr.send_command("toggle", None);          // F3
```

Backend zedsu_backend.py do_POST xử lý: `start`, `stop`, `restart_backend`, `reload_config`, `save_config`, `pause`, `resume`, các command YOLO — **KHÔNG CÓ** `toggle` hoặc `emergency_stop`.

Impact: F1 và F3 trả HTTP 400. Nguy hiểm nhất là F1 (emergency stop) fail.

### Blocker 2: /health Semantics (VERIFIED)

Backend lines 455-459:
```python
alive = _core_instance is not None and _core_instance._running
self._send_json({"status": "ok" if alive else "down"})
```

Sai: backend process vẫn khỏe khi bot idle/stopped. `/health` phải trả `ok` khi HTTP server alive, không phải khi bot running.

### Blocker 3: HUD Path Mismatch (VERIFIED)

Backend /state trả (line 500-506):
```json
"combat": core_state.get("combat", {}),
"stats": {
  "combat_state": core_state.get("combat_state", "IDLE"),
  "kills": core_state.get("kills", 0),
}
```

Frontend get_hud_state() đọc (lib.rs lines 318-323):
```rust
let combat_state = state.combat.get("combat_state")...
```

Nhưng backend trả `state.combat` là `core_state.get("combat", {})` — dict trống hoặc có combat debug info, KHÔNG có `combat_state`. Frontend luôn đọc `None` → fallback "IDLE".

### Blocker 4: Backend Auto-Start (VERIFIED)

Backend main() lines 718-722:
```python
_launch_core()  # Gọi ngay khi backend start
```

Backend nên idle, chỉ start khi có command `start`.

### Blocker 5: ThreadingHTTPServer (VERIFIED)

Backend lines 691-696:
```python
class ThreadingMixIn:
    daemon_threads = True
    blocking_mode = False
```

Đây không phải `socketserver.ThreadingMixIn`. Server không truly threaded. Dùng `http.server.ThreadingHTTPServer` thật sự.

### Blocker 6: safe_find_and_click Signature (VERIFIED)

Backend line 173-177:
```python
def safe_find_and_click(self, image_key, confidence=None):
    return find_and_click(image_key, _app_config, confidence)
```

Nhưng vision.py find_and_click signature (line 651-660):
```python
def find_and_click(img_name, config, is_running_check, log_func, clicks=1, ...):
```

Backend gọi thiếu `is_running_check` và `log_func`. Callback `self.is_running` và `self.log` phải được truyền.

### Blocker 7: click_saved_coordinate Import (VERIFIED)

Backend line 208-219:
```python
def click_saved_coordinate(self, key, label, clicks=1):
    from src.core.vision import find_and_click  # import find_and_click
    result = locate_image(key, _app_config, None)  # NHƯNG locate_image KHÔNG được import!
```

`locate_image` không có trong import scope.

### Blocker 8: requirements.txt (PARTIAL)

Build script build_exe.py có hidden-import mss, numpy. Nhưng requirements.txt chưa kiểm tra. Cần verify trực tiếp.

### Blocker 9: YOLO Parser (VERIFIED)

vision_yolo.py lines 146-165:
```python
if output.shape[0] == 84:  # chỉ handle 84
    output = output.T
# Với 10 classes + 4 coords = 14, format thường là 1x14x8400
# Parser không xử lý đúng batch dimension
```

Không có NMS. Duplicate boxes gây nhiễu.

### Blocker 10: validate_model_on_dataset Recursive (VERIFIED)

vision_yolo.py line 336:
```python
image_files = [f for f in os.listdir(val_dir) if ...]
```

Dùng `os.listdir` không recursive. Nếu train_yolo.py tạo subfolder per class (train/images/enemy_player/*.png), validation đọc 0 ảnh.

### Blocker 11: Config Schema (DEFERRED to Phase 12)

Config hiện có `combat_regions` dạng `{"green_hp_bar": {"x_ratio": ...}}`. Phase 12 muốn `combat_regions_v2` dạng `{"combat_scan": {"area": [...]}}`. Schema conflict. Cần migration plan trong Phase 11.5.
</code_context>

<specifics>
## Specific Ideas

- **ThreadingHTTPServer:** Python 3.7+ có `http.server.ThreadingHTTPServer` built-in
- **Emergency stop:** Phải gọi `_core_instance.stop()` và set `_running = False` trước khi stop
- **YOLO batch dim:** YOLOv8 ONNX thường output `(1, num_features, num_predictions)` — squeeze + transpose
- **NMS:** `cv2.dnn.NMSBoxes(bboxes, scores, 0.25, 0.45)` — standard thresholds
- **Recursive validation:** Dùng `glob.glob(os.path.join(val_dir, "**/*.png"), recursive=True)` hoặc `os.walk()`
- **Config migration:** Helper function `migrate_combat_regions()` chuyển legacy → v2
</specifics>

<deferred>
## Deferred Ideas

### From Brutal Review
- **InputController abstraction** trong core cho emergency stop safety — defer đến Phase 12 hoặc Phase 14
- **Combat event structured emission** (structured events dict thay vì log string) — defer đến Phase 12
- **Vision state first-class reporting** (last_scan_ms, detection_backend, fallback_reason) — defer đến Phase 12
- **Frontend stdout/stderr handling** (Stdio::null() hoặc drain threads) — defer đến Phase 13
- **HUD placement theo monitor size runtime** — defer đến Phase 13
- **Training script deterministic split** — defer đến Phase 12
- **Validation per-class F1** — defer đến Phase 12
- **FSM disengage counter increment** — defer đến Phase 12 (small fix, not blocking)
- **spectating_icon key existence** — defer đến Phase 12

### Out of Scope
- Phase 12 feature work (Region Selector, Discord Webhook, Position Picker)
- System tray v3 (Phase 13)
- Production packaging (Phase 14)
- YOLO training data collection
- Combat strategy changes
</deferred>
