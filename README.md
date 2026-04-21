# Zedsu

Zedsu is a Windows automation tool for Grand Piece Online Battle Royale. The project now ships with a guided control center designed for first-run setup, asset capture, validation, and safer runtime handling.

## What Is Improved

- Auto-creates `config.json`, `src/assets`, `captures`, and `debug_log.txt` at runtime
- Blocks startup until the required templates and auto-punch coordinates are ready
- Guided asset capture flow for all eight tracked assets, with seven core assets plus one combat-equip verification asset
- Window-title matching with refresh and "use active window" helper
- Window-relative coordinate binding so combat clicks follow the current Roblox client instead of one fixed desktop position
- Scale-aware asset matching with lightweight fallback resizing and window-size warnings
- Safer stop behavior, focus checks, and interruptible loops
- Combat loop now prefers a captured melee/combat indicator, then falls back to slot heuristics if needed
- Cleaner dashboard with readiness checklist, runtime stats, and live logs
- Better support for standalone `exe` builds

## Quick Start From Source

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:

   ```bash
   python main.py
   ```

3. Complete setup in this order:

- Open GPO in windowed or borderless mode
- Go to the `Setup` tab and set the game window title
- Go to the `Assets` tab and run `Guided Capture`
- Capture the optional `Combat Equipped Indicator` if you want the most reliable melee confirmation
- Pick the `Statistics Icon` and `Melee Upgrade Button` coordinates on the setup you actually plan to run
- Optionally add a Discord webhook
- Press `START BOT` or `F1`

## Combat Flow

After the match starts and the ultimate bar is visible, the bot:

1. Opens the menu and applies the configured melee/stat setup
2. Confirms melee/combat is equipped using the captured combat asset when available
3. Spams 5 M1 hits
4. Performs a short dynamic random movement burst
5. Repeats until post-match buttons appear

## Guided Capture Only

If you want to jump straight into template setup:

```bash
python capture_guide.py
```

## Build A Standalone EXE

Install PyInstaller first:

```bash
pip install pyinstaller
```

Then build:

```bash
python build_exe.py
```

The output will be created at:

```text
dist/Zedsu.exe
```

When the EXE starts for the first time, it will automatically create the config, asset, log, and capture folders next to itself.

## Notes

- `pydirectinput` works best with windowed or borderless mode
- Template images should ideally be captured from the same Roblox client size you plan to use while running
- The app now keeps coordinate picks relative to the Roblox client, so changing monitor position is safer, but major UI scale changes still deserve a quick re-capture pass
- A 15-inch laptop is fine as long as the Roblox client stays readable; once the client drops below roughly `960x540`, detection becomes less reliable
- The optional `Combat Equipped Indicator` should be captured from a state where melee is already equipped
- Lower `Confidence` slightly if image matching is too strict
- Discord webhook is optional
