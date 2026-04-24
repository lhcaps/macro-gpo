# Bridger Fishing Macro — Source Code

Reconstructed source code from decompiling `BridgerBackend.exe` (Python/PyInstaller) and `bridger.exe` (Rust/Tauri 2.x).

---

## Project Structure

```
bridger_source/
├── README.md              ← you are here
├── requirements.txt       ← Python dependencies
├── config.json            ← default configuration
├── start_bridger.bat     ← Windows launcher
├── src/
│   ├── BridgerBackend.py ← HTTP API server + GUI overlay
│   ├── bridger.py        ← FishingEngine (audio detection + minigame)
│   └── bridger.rs        ← Rust/Tauri frontend (reconstruction)
├── assets/
│   ├── pics/             ← OCR minigame templates (tpl_t.png, tpl_g.png, etc.)
│   │                        bite_template.wav (audio bite template)
│   └── tesseract/        ← Tesseract OCR binaries (optional)
└── pyz_modules/
    └── (1388 reconstructed PYZ module .py files)
```

---

## How It Works

```
bridger.exe (Rust/Tauri)
    │
    ├── Spawns BridgerBackend.exe as child process
    ├── Health-checks /health every 3 seconds → respawns on crash
    ├── IPC → send_to_python() → HTTP POST /command
    └── Displays web GUI + transparent overlay windows

BridgerBackend.exe (Python/HTTP)
    │
    ├── GET  /health        → health check
    ├── GET  /state         → full state + config + logs
    ├── POST /command       → all actions (start, stop, set_setting, ...)
    │
    ├── FishingEngine       ← bridger.py
    │   ├── Audio thread: WASAPI loopback → FFT cross-correlation → bite detection
    │   ├── Fishing loop:  focus Roblox → cast → wait for bite
    │   └── Minigame: OCR (Tesseract) / OpenCV / Pixel detection → press T/G/F/R
    │
    └── Tkinter Status Overlay (optional, --headless disables it)
```

---

## Quick Start

### 1. Install Python

Python **3.11 or 3.14** (or any 3.11+). Download from [python.org](https://www.python.org/downloads/).

### 2. Install Dependencies

```powershell
cd bridger_source
pip install -r requirements.txt
```

Or install individually:

```powershell
pip install numpy scipy pyautogui pyaudio pyaudiowpatch mss opencv-python Pillow pytesseract keyboard mouse requests
```

### 3. Install Tesseract OCR

Download from [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki).

Either:
- Install to `C:\Program Files\Tesseract-OCR\` (default path), **or**
- Copy the `tesseract/` folder to `bridger_source/assets/tesseract/`

### 4. Record the Bite Template

1. Open Roblox and start a fishing session.
2. Run `python -m src.bridger` to record the bite sound.
3. Save as `bridger_source/assets/pics/bite_template.wav`.

### 5. Capture OCR Templates (Optional)

For OpenCV/Numpy minigame detection, capture PNG screenshots of each T/G/F/R letter in the minigame prompt and save to `bridger_source/assets/pics/` as:
- `tpl_t.png`, `tpl_t_a.png`, `tpl_t_b.png`
- `tpl_g.png`, `tpl_g_a.png`, `tpl_g_b.png`
- `tpl_f.png`, `tpl_f_a.png`, `tpl_f_b.png`
- `tpl_r.png`, `tpl_r_a.png`, `tpl_r_b.png`

### 6. Run

```powershell
start_bridger.bat
```

Or directly:

```powershell
cd bridger_source/src
python BridgerBackend.py
```

For HTTP-only (no GUI overlay):

```powershell
python BridgerBackend.py --headless
```

---

## Key Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `detect_method` | `numpy` | Minigame detection: `numpy` (default, no Tesseract), `cv` (OpenCV), `pixel` (fastest) |
| `match_threshold` | `0.3` | Audio bite detection sensitivity (higher = more strict) |
| `rms_threshold` | `0.015` | RMS fallback threshold |
| `ocr_region` | `[0.474, 0.47, 0.531, 0.551]` | Screen region for OCR minigame letters (normalised 0-1) |
| `monitor_index` | `1` | Monitor index for screenshots (0 = all monitors combined) |
| `webhook_enabled` | `false` | Enable Discord webhook notifications |
| `timeout_streak_webhook` | `5` | Send webhook after this many consecutive timeouts |

---

## Hotkeys

| Key | Action |
|-----|--------|
| `F3` | Start / Stop macro |
| `F2` | Exit |
| `F1` | Select OCR region |

---

## Building the Rust Frontend (Optional)

To rebuild `bridger.exe` from `bridger.rs`:

```bash
cargo build --release
```

Requires Rust toolchain. The `Cargo.toml` dependencies:

```toml
[dependencies]
tauri = { version = "2", features = [] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
reqwest = { version = "0.12", features = ["blocking"] }
tokio = { version = "1", features = ["rt-multi-thread", "macros"] }
sysinfo = "0.32"
open = "5"
windows = { version = "0.58", features = ["Win32_UI_HiDpi"] }
```

---

## Detecting Methods

The macro supports three minigame detection methods:

### 1. Numpy (default, recommended)
- Fastest, no external dependencies
- Uses cosine-similarity fingerprint matching on binarised letters
- Requires template PNGs in `assets/pics/`

### 2. OpenCV Template Matching
- `cv_threshold` controls match confidence (0.0–1.0)
- Requires same template PNGs

### 3. Pixel Detection (fastest)
- No OCR or template matching required
- Searches for specific pixel colours at known offsets
- Most fragile — only works at exact reference resolution

### 4. Tesseract OCR
- Highest accuracy, slowest
- Requires Tesseract installation
- `ocr_tolerance` controls background brightness filter

---

## Discord Webhook

Enable in settings and provide a webhook URL. Events:
- Timeout streak detected
- Minigame started
- Arrow shard caught
- Fish reeled in

Each event can be independently enabled/disabled with ping.

---

## Rebuilding PyInstaller Executable

```powershell
cd bridger_source
py -3.14 -m PyInstaller --onefile --noconfirm `
    --add-data "assets;pics" `
    --add-data "assets/tesseract;tesseract" `
    --hidden-import numpy `
    --hidden-import scipy `
    --hidden-import cv2 `
    --hidden-import mss `
    --hidden-import pytesseract `
    --hidden-import keyboard `
    --hidden-import mouse `
    --hidden-import requests `
    --name BridgerBackend `
    src/BridgerBackend.py
```

---

## Architecture Notes

- The Rust frontend (`bridger.exe`) is **not needed** to run the macro from source.
  `BridgerBackend.py` includes a built-in Tkinter status overlay.
- The Rust frontend only provides: the web GUI, window management, backend process lifecycle,
  and transparent overlay windows.
- All fishing logic lives in `bridger.py` (FishingEngine).
- Communication between Rust and Python uses plain HTTP on port 9760 — no IPC overhead.
