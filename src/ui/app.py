"""
Zedsu Control Center - Radical Minimal UI
Philosophy: Open and run. Settings only when needed. Get shit done.
"""
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox, scrolledtext, ttk

import keyboard
import pyautogui

from src.core.bot_engine import BotEngine
from src.core.vision import ScreenCaptureTool, capture_search_context, locate_image
from src.ui.components import AreaPicker, CoordinatePicker
from src.utils.config import (
    ASSETS_DIR, CAPTURES_DIR, COORDINATE_SPECS, CONFIG_FILE, IMAGE_ORDER,
    IMAGE_SPECS, LOG_FILE, RUNTIME_DIR,
    describe_area_binding, describe_coordinate_binding, describe_window_size,
    get_asset_records, get_optional_asset_records, get_required_asset_records,
    get_required_setup_issues, get_optional_setup_warnings,
    get_runtime_portability_report, is_coordinate_ready, is_asset_custom,
    load_config, resolve_path, save_config, set_coordinate_binding,
    set_asset_path, set_outcome_area_binding,
)
from src.utils.discord import send_discord
from src.utils.windows import (
    bring_window_to_foreground, find_window_by_title, get_foreground_window_title,
    get_window_rect, list_visible_window_titles,
)


# ============================================================
# DPI SCALING UTILITY
# ============================================================
def _get_dpi_scale(root):
    """Get DPI scale factor for the primary monitor. Returns 1.0 for 96 DPI, ~1.25 for 120 DPI, etc."""
    try:
        import ctypes
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        hwnd = user32.GetDesktopWindow()
        dc = user32.GetDC(hwnd)
        dpi = ctypes.windll.gdi32.GetDeviceCaps(dc, 88)  # LOGPIXELSX
        user32.ReleaseDC(hwnd, dc)
        return max(0.8, min(2.0, dpi / 96.0))
    except Exception:
        return 1.0


def _scaled_font(base_size, scale):
    """Return a scaled font tuple for tkinter."""
    scaled = max(7, int(round(base_size * scale)))
    return ("Segoe UI", scaled)


# ============================================================
# THEME - Clean, minimal, functional
# ============================================================
def _apply_theme(root, dpi_scale=1.0):
    """Apply minimal dark theme that works on all screens with DPI-aware font scaling."""
    try:
        style = ttk.Style(root)
        style.theme_use("clam")
    except tk.TclError:
        pass

    # Colors
    BG = "#1a1a2e"
    CARD_BG = "#16213e"
    ACCENT = "#0f3460"
    TEXT = "#e2e8f0"
    MUTED = "#94a3b8"
    GREEN = "#22c55e"
    RED = "#ef4444"
    YELLOW = "#eab308"
    BLUE = "#3b82f6"

    # Root
    root.configure(bg=BG)

    # Notebook (hidden - we don't use tabs)
    style.configure("TNotebook", background=BG, borderwidth=0)
    style.configure("TNotebook.Tab", background=BG, borderwidth=0, padding=0)
    style.map("TNotebook.Tab", background=[("selected", BG)], foreground=[("selected", TEXT)])

    # Frames
    style.configure("TFrame", background=BG)
    style.configure("Card.TFrame", background=CARD_BG)

    # Fonts (DPI-aware)
    fs = dpi_scale
    font_hero = ("Segoe UI", max(12, int(22 * fs)), "bold")
    font_status = ("Segoe UI", max(10, int(14 * fs)), "bold")
    font_label = ("Segoe UI", max(8, int(10 * fs)))
    font_muted = ("Segoe UI", max(7, int(9 * fs)))
    font_small = ("Segoe UI", max(7, int(8 * fs)))
    font_value = ("Segoe UI", max(9, int(12 * fs)), "bold")
    font_section = ("Segoe UI", max(9, int(10 * fs)), "bold")
    font_cons = ("Consolas", max(7, int(9 * fs)))

    # Labels
    style.configure("TLabel", background=BG, foreground=TEXT, font=font_label)
    style.configure("Hero.TLabel", background=BG, foreground=TEXT, font=font_hero)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=font_muted)
    style.configure("Status.TLabel", background=BG, foreground=TEXT, font=font_status)
    style.configure("Small.TLabel", background=BG, foreground=MUTED, font=font_small)
    style.configure("Value.TLabel", background=CARD_BG, foreground=TEXT, font=font_value)

    # Buttons
    btn_pad_x = max(8, int(12 * fs))
    btn_pad_y = max(4, int(8 * fs))
    font_btn = ("Segoe UI", max(8, int(10 * fs)), "bold")
    font_btn_large = ("Segoe UI", max(10, int(14 * fs)), "bold")

    style.configure("TButton", padding=(btn_pad_x, btn_pad_y), font=font_btn, background=CARD_BG, foreground=TEXT)
    style.configure("Start.TButton", padding=(btn_pad_x, btn_pad_y), font=font_btn_large,
                   foreground="white", background=GREEN)
    style.configure("Stop.TButton", padding=(btn_pad_x, btn_pad_y), font=font_btn_large,
                   foreground="white", background=RED)
    style.configure("Section.TButton", padding=(btn_pad_x, btn_pad_y), font=font_btn,
                   background=ACCENT, foreground=TEXT)
    style.configure("Icon.TButton", padding=(4, 3), font=font_small,
                   background=CARD_BG, foreground=MUTED)

    style.map("TButton", background=[("active", ACCENT), ("pressed", "#1a365d")],
              foreground=[("active", TEXT)])
    style.map("Start.TButton", background=[("active", "#16a34a"), ("pressed", "#15803d")])
    style.map("Stop.TButton", background=[("active", "#dc2626"), ("pressed", "#b91c1c")])

    # Labelframe
    style.configure("TLabelframe", background=CARD_BG, borderwidth=0)
    style.configure("TLabelframe.Label", background=CARD_BG, foreground=TEXT, font=font_section)
    style.configure("Card.TLabelframe", background=CARD_BG, borderwidth=0)
    style.configure("Card.TLabelframe.Label", background=CARD_BG, foreground=TEXT, font=font_section)

    # Entry
    style.configure("TEntry", fieldbackground=CARD_BG, foreground=TEXT, insertcolor=TEXT,
                   font=font_label)
    style.configure("TCombobox", fieldbackground=CARD_BG, foreground=TEXT,
                   background=CARD_BG, insertcolor=TEXT, font=font_label)
    style.map("TCombobox", fieldbackground=[("readonly", CARD_BG)],
               selectbackground=[("readonly", ACCENT)])

    # Checkbutton
    style.configure("TCheckbutton", background=CARD_BG, foreground=TEXT, font=font_muted)
    style.map("TCheckbutton", background=[("active", CARD_BG)])

    # Scrollbar
    style.configure("Vertical.TScrollbar", background=ACCENT, troughcolor=CARD_BG,
                   arrowcolor=TEXT)

    return {
        "BG": BG, "CARD_BG": CARD_BG, "ACCENT": ACCENT,
        "TEXT": TEXT, "MUTED": MUTED, "GREEN": GREEN, "RED": RED,
        "YELLOW": YELLOW, "BLUE": BLUE,
        "dpi_scale": dpi_scale,
        "fonts": {
            "hero": font_hero, "status": font_status, "label": font_label,
            "muted": font_muted, "small": font_small, "value": font_value,
            "section": font_section, "cons": font_cons,
        }
    }


# ============================================================
# COLLAPSIBLE FRAME WIDGET
# ============================================================
class CollapsibleFrame(ttk.Frame):
    """A frame that can be collapsed/expanded with a header button."""
    def __init__(self, parent, title, colors, default_open=False, **kwargs):
        super().__init__(parent, style="Card.TFrame", **kwargs)
        self.colors = colors
        self.is_open = default_open

        # Header with toggle button
        header = ttk.Frame(self, style="Card.TFrame")
        header.pack(fill=tk.X, padx=8, pady=(6, 4))

        self.toggle_btn = ttk.Button(
            header, text="▼" if default_open else "▶",
            command=self.toggle, style="Icon.TButton", width=2
        )
        self.toggle_btn.pack(side=tk.LEFT, padx=(0, 6))

        ttk.Label(header, text=title, style="Card.TLabelframe.Label").pack(side=tk.LEFT)

        # Content frame
        self.content_frame = ttk.Frame(self, style="Card.TFrame")
        if self.is_open:
            self.content_frame.pack(fill=tk.X, padx=8, pady=(0, 6))

    def toggle(self):
        self.is_open = not self.is_open
        self.toggle_btn.config(text="▼" if self.is_open else "▶")
        if self.is_open:
            self.content_frame.pack(fill=tk.X, padx=8, pady=(0, 6))
        else:
            self.content_frame.pack_forget()

    def get_content(self):
        return self.content_frame


# ============================================================
# MAIN APP
# ============================================================
class ZedsuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zedsu")
        self.root.configure(bg="#1a1a2e")

        # Default size - small and functional
        self.root.geometry("680x520")
        self.root.minsize(400, 320)

        self.is_running = False
        self.match_count = 0
        self.start_time = None
        self.config = load_config()
        self.engine = BotEngine(self)
        self.dpi_scale = _get_dpi_scale(self.root)
        self.colors = _apply_theme(self.root, self.dpi_scale)

        self.lockable_widgets = []
        self._setup_variables()
        self._build_ui()
        self._register_hotkey()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.refresh_runtime_status()
        self.log("Zedsu ready. Open Settings to configure, then press START.")
        self.root.after(2000, self.refresh_runtime_status_loop)

    def _setup_variables(self):
        self.window_title_var = tk.StringVar(value=self.config.get("game_window_title", ""))
        self.webhook_var = tk.StringVar(value=self.config.get("discord_webhook", ""))
        self.confidence_var = tk.StringVar(value=str(self.config.get("confidence", 0.8)))
        self.scan_interval_var = tk.StringVar(value=str(self.config.get("scan_interval", 1.5)))
        self.movement_duration_var = tk.StringVar(value=str(self.config.get("movement_duration", 300)))
        self.mode_var = tk.StringVar(value=self.config.get("match_mode", "full"))
        self.focus_required_var = tk.BooleanVar(value=self.config.get("window_focus_required", True))
        self.auto_focus_var = tk.BooleanVar(value=self.config.get("auto_focus_window", True))
        self.backend_var = tk.StringVar(value=self.config.get("detection_backend", "auto"))

        self.key_vars = {}
        for key_id, value in self.config.get("keys", {}).items():
            self.key_vars[key_id] = tk.StringVar(value=value)

    # ------------------------------------------------------------
    # UI BUILD
    # ------------------------------------------------------------
    def _build_ui(self):
        # Main scrollable container
        container = ttk.Frame(self.root)
        container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas = tk.Canvas(container, bg=self.colors["BG"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas, style="TFrame")

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._bind_mousewheel(canvas)

        # ---- Header ----
        header = ttk.Frame(scroll_frame, style="TFrame")
        header.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(header, text="ZEDSÜ", style="Hero.TLabel").pack(side=tk.LEFT)

        # Mode indicator
        mode_frame = ttk.Frame(header, style="TFrame")
        mode_frame.pack(side=tk.RIGHT)
        mode_text = "QUICK" if self.config.get("match_mode") == "quick" else "FULL"
        ttk.Label(mode_frame, text=f"Mode: {mode_text}", style="Muted.TLabel").pack()

        # ---- START/STOP Section ----
        self._build_control_section(scroll_frame)

        # ---- Status Section ----
        self._build_status_section(scroll_frame)

        # ---- Settings Section ----
        self._build_settings_section(scroll_frame)

        # ---- Assets Section ----
        self._build_assets_section(scroll_frame)

        # ---- Log Section ----
        self._build_log_section(scroll_frame)

        # ---- Footer ----
        footer = ttk.Frame(scroll_frame, style="TFrame")
        footer.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(footer, text="F1 = Toggle Bot | ESC = Stop", style="Small.TLabel").pack(side=tk.LEFT)
        btn_config = ttk.Button(footer, text="Open Config", command=lambda: self.open_path(CONFIG_FILE),
                               style="Icon.TButton")
        btn_config.pack(side=tk.RIGHT)
        self.lockable_widgets.append(btn_config)

    def _bind_mousewheel(self, canvas):
        def on_scroll(event):
            if event.delta:
                canvas.yview_scroll(int(-event.delta / 120), "units")
            elif hasattr(event, 'num'):
                if event.num == 4:
                    canvas.yview_scroll(-1, "units")
                elif event.num == 5:
                    canvas.yview_scroll(1, "units")
        canvas.bind_all("<MouseWheel>", on_scroll)
        canvas.bind_all("<Button-4>", on_scroll)
        canvas.bind_all("<Button-5>", on_scroll)

    def _build_control_section(self, parent):
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill=tk.X, pady=(0, 8))

        inner = ttk.Frame(card, style="Card.TFrame")
        inner.pack(fill=tk.X, padx=14, pady=14)

        # Status line
        self.status_label = ttk.Label(inner, text="IDLE", style="Status.TLabel")
        self.status_label.pack(anchor=tk.W)

        self.match_label = ttk.Label(inner, text="Matches: 0", style="Muted.TLabel")
        self.match_label.pack(anchor=tk.W, pady=(2, 8))

        # Buttons row
        btn_row = ttk.Frame(inner, style="Card.TFrame")
        btn_row.pack(fill=tk.X)

        self.btn_toggle = ttk.Button(
            btn_row, text="▶  START", style="Start.TButton",
            command=self.toggle_bot
        )
        self.btn_toggle.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.btn_stop = ttk.Button(
            btn_row, text="■  STOP", style="Stop.TButton",
            command=self.stop_bot, state="disabled"
        )
        self.btn_stop.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

    def _build_status_section(self, parent):
        self.status_panel = CollapsibleFrame(
            parent, "Runtime Status", self.colors, default_open=True
        )
        self.status_panel.pack(fill=tk.X, pady=(0, 8))
        content = self.status_panel.get_content()

        self.runtime_info_label = ttk.Label(content, text="Ready to run", style="Muted.TLabel")
        self.runtime_info_label.pack(anchor=tk.W)

    def _build_settings_section(self, parent):
        self.settings_panel = CollapsibleFrame(
            parent, "Settings", self.colors, default_open=False
        )
        self.settings_panel.pack(fill=tk.X, pady=(0, 8))
        content = self.settings_panel.get_content()

        # Window selection
        row = ttk.Frame(content, style="Card.TFrame")
        row.pack(fill=tk.X, pady=4)
        ttk.Label(row, text="Game Window:", style="TLabel").pack(side=tk.LEFT)
        self.cmb_windows = ttk.Combobox(row, textvariable=self.window_title_var, width=30)
        self.cmb_windows.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.lockable_widgets.append(self.cmb_windows)
        ttk.Button(row, text="↻", width=3, command=self.refresh_window_list,
                   style="Icon.TButton").pack(side=tk.LEFT, padx=(4, 0))
        self.lockable_widgets.append(row.winfo_children()[-1])

        # Behavior settings - compact row
        settings_row = ttk.Frame(content, style="Card.TFrame")
        settings_row.pack(fill=tk.X, pady=4)

        # Left column
        left = ttk.Frame(settings_row, style="Card.TFrame")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_setting_entry(left, "Confidence:", self.confidence_var, "0.10-1.00")
        self._build_setting_entry(left, "Scan (sec):", self.scan_interval_var, "0.2-10")
        self._build_setting_entry(left, "Move (sec):", self.movement_duration_var, "30-3600")

        # Right column
        right = ttk.Frame(settings_row, style="Card.TFrame")
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        # Mode
        mode_frame = ttk.Frame(right, style="Card.TFrame")
        mode_frame.pack(fill=tk.X, pady=2)
        ttk.Label(mode_frame, text="Match Mode:", style="TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(mode_frame, text="Full", variable=self.mode_var,
                       value="full").pack(side=tk.LEFT, padx=(8, 0))
        ttk.Radiobutton(mode_frame, text="Quick", variable=self.mode_var,
                       value="quick").pack(side=tk.LEFT)

        # Focus
        focus_frame = ttk.Frame(right, style="Card.TFrame")
        focus_frame.pack(fill=tk.X, pady=2)
        self.chk_focus = ttk.Checkbutton(focus_frame, text="Require game window focus",
                                         variable=self.focus_required_var)
        self.chk_focus.pack(side=tk.LEFT)
        self.lockable_widgets.append(self.chk_focus)

        self.chk_autofocus = ttk.Checkbutton(focus_frame, text="Auto-focus",
                                             variable=self.auto_focus_var)
        self.chk_autofocus.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(self.chk_autofocus)

        # Detection backend
        backend_frame = ttk.Frame(content, style="Card.TFrame")
        backend_frame.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(backend_frame, text="Detection:", style="TLabel").pack(side=tk.LEFT)
        ttk.Radiobutton(backend_frame, text="Auto", variable=self.backend_var,
                        value="auto").pack(side=tk.LEFT, padx=(4, 0))
        ttk.Radiobutton(backend_frame, text="OpenCV (fast)", variable=self.backend_var,
                        value="opencv").pack(side=tk.LEFT)
        ttk.Radiobutton(backend_frame, text="PyAutoGUI (compat)", variable=self.backend_var,
                        value="pyautogui").pack(side=tk.LEFT)
        ttk.Label(backend_frame, text="← OpenCV recommended", style="Muted.TLabel").pack(side=tk.RIGHT)

        # Combat Detection (Phase 5 Smart Combat)
        combat_frame = CollapsibleFrame(content, "Combat Detection", self.colors, default_open=False)
        combat_frame.pack(fill=tk.X, pady=(4, 0))
        combat_content = combat_frame.get_content()

        combat_intro = ttk.Label(
            combat_content, wraplength=580,
            text="Pixel-perfect combat detection using HSV color scanning. Pick each region by clicking the button "
                 "and selecting the area on your screen. Use FIRST-PERSON camera for best results.",
            style="Muted.TLabel"
        )
        combat_intro.pack(anchor=tk.W, pady=(4, 4))

        # Smart combat toggle
        smart_row = ttk.Frame(combat_content, style="Card.TFrame")
        smart_row.pack(fill=tk.X, pady=2)
        self.smart_combat_var = tk.BooleanVar(
            value=self.config.get("combat_settings", {}).get("smart_combat_enabled", True)
        )
        ttk.Checkbutton(smart_row, text="Enable Smart Combat (Phase 5) — intelligent state machine",
                        variable=self.smart_combat_var).pack(side=tk.LEFT)
        ttk.Label(smart_row, text="← recommended", style="Small.TLabel").pack(side=tk.LEFT, padx=(4, 0))

        # First-person camera toggle
        fp_row = ttk.Frame(combat_content, style="Card.TFrame")
        fp_row.pack(fill=tk.X, pady=2)
        self.first_person_var = tk.BooleanVar(
            value=self.config.get("combat_settings", {}).get("first_person", True)
        )
        ttk.Checkbutton(fp_row, text="First-Person Camera (recommended for detection)",
                        variable=self.first_person_var).pack(side=tk.LEFT)

        # Region pickers
        region_defs = [
            ("green_hp_bar", "Enemy HP Bar (green)"),
            ("red_dmg_numbers", "Damage Numbers (red)"),
            ("player_hp_bar", "Player HP Bar"),
            ("incombat_timer", "INCOMBAT Timer"),
            ("kill_icon", "Kill Icon (skull)"),
        ]
        self.combat_region_vars = {}
        regions = self.config.get("combat_regions", {})
        for region_key, label in region_defs:
            rrow = ttk.Frame(combat_content, style="Card.TFrame")
            rrow.pack(fill=tk.X, pady=1)
            ttk.Label(rrow, text=label, width=25).pack(side=tk.LEFT)
            ttk.Button(rrow, text="Pick Region",
                command=lambda k=region_key: self._pick_combat_region(k),
                style="Icon.TButton").pack(side=tk.LEFT)
            region = regions.get(region_key, {})
            status = "enabled" if region.get("enabled") else "not set"
            ttk.Label(rrow, text=f"[{status}]", style="Small.TLabel").pack(side=tk.LEFT, padx=(4, 0))

        # Test combat detection button
        test_row = ttk.Frame(combat_content, style="Card.TFrame")
        test_row.pack(fill=tk.X, pady=4)
        ttk.Button(test_row, text="Test Combat Detection",
                   command=self._test_combat_detection,
                   style="Section.TButton").pack(side=tk.LEFT)
        self.combat_debug_label = ttk.Label(test_row, text="", style="Small.TLabel")
        self.combat_debug_label.pack(side=tk.LEFT, padx=(8, 0))

        # YOLO Neural Detection (Phase 8)
        yolo_frame = CollapsibleFrame(content, "YOLO Neural Detection", self.colors, default_open=True)
        yolo_frame.pack(fill=tk.X, pady=(4, 0))
        yolo_content = yolo_frame.get_content()

        # Model status indicator (D-29)
        status_row = ttk.Frame(yolo_content, style="Card.TFrame")
        status_row.pack(fill=tk.X, pady=(4, 4))

        ttk.Label(status_row, text="Model Status:", style="TLabel").pack(side=tk.LEFT)
        self.yolo_status_label = ttk.Label(status_row, text="Checking...", style="Status.TLabel")
        self.yolo_status_label.pack(side=tk.LEFT, padx=(8, 0))
        self._update_yolo_status()

        # Dataset collection
        ttk.Separator(yolo_content, orient="horizontal").pack(fill=tk.X, pady=6)

        ttk.Label(yolo_content,
            text="Collect screenshots for YOLO training. "
                 "Place game in first-person view, click 'Capture' for each class.",
            style="Muted.TLabel").pack(anchor=tk.W, pady=(0, 4))

        # Output directory
        dir_row = ttk.Frame(yolo_content)
        dir_row.pack(fill=tk.X, pady=2)
        ttk.Label(dir_row, text="Output folder:", style="TLabel").pack(side=tk.LEFT)
        self._yolo_dataset_dir = tk.StringVar(
            value=os.path.join(os.path.dirname(__file__), "..", "..", "datasets", "yolo_train")
        )
        ttk.Entry(dir_row, textvariable=self._yolo_dataset_dir, width=32).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))

        # Class selector
        class_row = ttk.Frame(yolo_content)
        class_row.pack(fill=tk.X, pady=4)
        ttk.Label(class_row, text="Class:", style="TLabel").pack(side=tk.LEFT)

        self._yolo_capture_class = tk.StringVar(value="enemy_player")
        _yolo_class_options = [
            "enemy_player",    # Phase 8 critical
            "afk_cluster",
            "ultimate_bar",
            "solo_button",
            "br_mode_button",
            "return_to_lobby",
            "open_button",
            "continue_button",
            "combat_ready",
            "change_button",
        ]
        class_combo = ttk.Combobox(class_row,
            textvariable=self._yolo_capture_class,
            values=_yolo_class_options,
            state="readonly", width=18)
        class_combo.pack(side=tk.LEFT, padx=(8, 0))

        # Capture button
        cap_row = ttk.Frame(yolo_content)
        cap_row.pack(fill=tk.X, pady=4)
        ttk.Button(cap_row, text="Capture Screenshot",
                   command=self._capture_yolo_sample,
                   style="Section.TButton").pack(side=tk.LEFT)

        ttk.Label(cap_row,
            text=f"Target: 300+ images for enemy_player, 200+ for UI elements",
            style="Small.TLabel").pack(side=tk.LEFT, padx=(12, 0))

        # Training guide link
        guide_row = ttk.Frame(yolo_content, style="Card.TFrame")
        guide_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(guide_row,
            text="After collecting images: use LabelImg to annotate (YOLO format), "
                 "train with: yolo detect train ... imgsz=640, "
                 "export: yolo export ... imgsz=640 opset=11, "
                 "place .onnx in assets/models/yolo_gpo.onnx",
            style="Small.TLabel", wraplength=560, justify="left").pack(anchor=tk.W, pady=4)

        # HSV Color Filter
        hsv_frame = CollapsibleFrame(content, "HSV Color Filter", self.colors, default_open=False)
        hsv_frame.pack(fill=tk.X, pady=(4, 0))
        hsv_content = hsv_frame.get_content()

        hsv_intro = ttk.Label(hsv_content, wraplength=580,
            text="HSV pre-filter speeds up detection by checking color presence before template matching. "
                 "Enable and set ranges for Ultimate Bar or Return To Lobby to reduce CPU usage.",
            style="Muted.TLabel")
        hsv_intro.pack(anchor=tk.W, pady=(4, 6))

        self.hsv_vars = {}
        HSV_KEYS = ["ultimate", "return_to_lobby_alone"]
        for img_key in HSV_KEYS:
            meta = IMAGE_SPECS[img_key]
            hsv = self.config.get("hsv_settings", {}).get(img_key) or {}

            row = ttk.Frame(hsv_content, style="Card.TFrame")
            row.pack(fill=tk.X, pady=2)

            var_enabled = tk.BooleanVar(value=bool(hsv.get("enabled", False)))
            self.hsv_vars[(img_key, "enabled")] = var_enabled
            ttk.Checkbutton(row, text=meta["label"], variable=var_enabled,
                           command=lambda k=img_key: self._on_hsv_toggle(k)).pack(side=tk.LEFT)

            fields = [
                (f"{img_key}_h_min", "H:", 0, 179, "h_min"),
                (f"{img_key}_h_max", "H:", 0, 179, "h_max"),
                (f"{img_key}_s_min", "S:", 0, 255, "s_min"),
                (f"{img_key}_s_max", "S:", 0, 255, "s_max"),
                (f"{img_key}_v_min", "V:", 0, 255, "v_min"),
                (f"{img_key}_v_max", "V:", 0, 255, "v_max"),
            ]
            for fk, label, fmin, fmax, field_key in fields:
                lbl = ttk.Label(row, text=label, style="Muted.TLabel")
                lbl.pack(side=tk.LEFT, padx=(6, 0))
                var = tk.IntVar(value=int(hsv.get(field_key, fmin) if hsv else fmin))
                self.hsv_vars[(img_key, field_key)] = var
                entry = ttk.Entry(row, textvariable=var, width=4, justify="center")
                entry.pack(side=tk.LEFT)

            self._apply_hsv_row_state(var_enabled.get(), row)

        # Webhook
        webhook_row = ttk.Frame(content, style="Card.TFrame")
        webhook_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(webhook_row, text="Webhook:", style="TLabel").pack(side=tk.LEFT)
        self.ent_webhook = ttk.Entry(webhook_row, textvariable=self.webhook_var, show="*")
        self.ent_webhook.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(8, 0))
        self.lockable_widgets.append(self.ent_webhook)
        ttk.Button(webhook_row, text="Test", command=self.test_webhook,
                   style="Icon.TButton", width=5).pack(side=tk.LEFT, padx=(4, 0))
        self.lockable_widgets.append(webhook_row.winfo_children()[-1])

        # Key bindings - compact
        keys_label = ttk.Label(content, text="Key Bindings", style="Card.TLabelframe.Label")
        keys_label.pack(anchor=tk.W, pady=(6, 2))
        keys = [
            ("menu", "Menu:"), ("slot_1", "Slot 1:"),
            ("forward", "Forward:"), ("left", "Left:"),
            ("backward", "Back:"), ("right", "Right:"),
        ]
        for key_id, label in keys:
            kv_row = ttk.Frame(content, style="Card.TFrame")
            kv_row.pack(fill=tk.X, pady=1)
            ttk.Label(kv_row, text=label, width=9, style="TLabel").pack(side=tk.LEFT)
            entry = ttk.Entry(kv_row, textvariable=self.key_vars.setdefault(key_id, tk.StringVar(value="")))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.lockable_widgets.append(entry)

        # Coordinates
        coords_label = ttk.Label(content, text="Coordinates", style="Card.TLabelframe.Label")
        coords_label.pack(anchor=tk.W, pady=(6, 2))

        pos1 = self.config.get("pos_1")
        pos2 = self.config.get("pos_2")
        self.book_coord_label = ttk.Label(content, text=f"Stats Icon: {pos1 if is_coordinate_ready(pos1) else 'not set'}",
                                          style="Muted.TLabel")
        self.book_coord_label.pack(anchor=tk.W)
        self.lockable_widgets.append(self.book_coord_label)

        coord_btns = ttk.Frame(content, style="Card.TFrame")
        coord_btns.pack(fill=tk.X, pady=2)
        ttk.Button(coord_btns, text="Pick Stats Icon", command=lambda: self.pick_coord("pos_1"),
                   style="Section.TButton").pack(side=tk.LEFT)
        ttk.Button(coord_btns, text="Pick Upgrade Btn", command=lambda: self.pick_coord("pos_2"),
                   style="Section.TButton").pack(side=tk.LEFT, padx=(4, 0))
        self.lockable_widgets.extend(coord_btns.winfo_children())

        # Save + Export/Import buttons
        save_row = ttk.Frame(content, style="Card.TFrame")
        save_row.pack(fill=tk.X, pady=(6, 0))
        btn_save = ttk.Button(save_row, text="Save",
                              command=lambda: self.persist_form_to_config(show_feedback=True))
        btn_save.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_save)

        ttk.Button(save_row, text="Export Config",
                   command=self.export_config,
                   style="Icon.TButton").pack(side=tk.LEFT, padx=(4, 0))
        ttk.Button(save_row, text="Import Config",
                   command=self.import_config,
                   style="Icon.TButton").pack(side=tk.LEFT, padx=(4, 0))

    def _build_setting_entry(self, parent, label, var, hint):
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill=tk.X, pady=1)
        ttk.Label(row, text=label, width=11, style="TLabel").pack(side=tk.LEFT)
        entry = ttk.Entry(row, textvariable=var, width=10)
        entry.pack(side=tk.LEFT)
        ttk.Label(row, text=hint, style="Small.TLabel").pack(side=tk.LEFT, padx=(4, 0))
        self.lockable_widgets.append(entry)

    def _build_assets_section(self, parent):
        self.assets_panel = CollapsibleFrame(
            parent, "Assets", self.colors, default_open=False
        )
        self.assets_panel.pack(fill=tk.X, pady=(0, 8))
        content = self.assets_panel.get_content()

        # Asset status summary
        records = get_asset_records(self.config)
        ready = sum(1 for r in records if r["state"] == "custom")
        self.asset_summary_label = ttk.Label(
            content, text=f"{ready} / {len(records)} assets ready",
            style="Muted.TLabel"
        )
        self.asset_summary_label.pack(anchor=tk.W)

        # Quick action buttons
        action_row = ttk.Frame(content, style="Card.TFrame")
        action_row.pack(fill=tk.X, pady=4)
        ttk.Button(action_row, text="🎯 Capture All",
                   command=self.capture_all_assets,
                   style="Section.TButton").pack(side=tk.LEFT)
        ttk.Button(action_row, text="📁 Open Assets",
                   command=lambda: self.open_path(ASSETS_DIR),
                   style="Icon.TButton").pack(side=tk.LEFT, padx=(4, 0))
        self.lockable_widgets.extend(action_row.winfo_children())

        # Individual assets - compact grid
        self.asset_widgets = {}
        for key in IMAGE_ORDER:
            meta = IMAGE_SPECS[key]
            arow = ttk.Frame(content, style="Card.TFrame")
            arow.pack(fill=tk.X, pady=1)

            ttk.Label(arow, text=meta["label"], width=20, style="TLabel").pack(side=tk.LEFT)
            status = ttk.Label(arow, text="❌", style="TLabel", width=2)
            status.pack(side=tk.LEFT)
            self.asset_widgets[key] = {"status": status}

            btn_c = ttk.Button(arow, text="Capture",
                              command=lambda k=key: self.start_asset_capture(k),
                              style="Icon.TButton")
            btn_c.pack(side=tk.LEFT, padx=(4, 0))
            self.lockable_widgets.append(btn_c)

        self.refresh_asset_widgets()

    def _build_log_section(self, parent):
        self.log_panel = CollapsibleFrame(
            parent, "Log", self.colors, default_open=False
        )
        self.log_panel.pack(fill=tk.BOTH, expand=True, pady=(0, 0))
        content = self.log_panel.get_content()

        self.console = scrolledtext.ScrolledText(
            content, height=8, state="disabled",
            bg="#0f172a", fg="#e2e8f0", insertbackground="#e2e8f0",
            font=("Consolas", max(7, int(9 * self.dpi_scale))), relief=tk.FLAT,
        )
        self.console.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

        btn_clear_log = ttk.Button(content, text="Clear Log",
                                  command=self.clear_log, style="Icon.TButton")
        btn_clear_log.pack(anchor=tk.E, padx=4, pady=(0, 4))
        self.lockable_widgets.append(btn_clear_log)

    # ------------------------------------------------------------
    # CORE FUNCTIONS
    # ------------------------------------------------------------
    def _selected_window_title(self):
        return self.window_title_var.get().strip() or self.config.get("game_window_title", "").strip()

    def _selected_window_rect(self):
        title = self._selected_window_title()
        if not title:
            return None
        return get_window_rect(title)

    def persist_form_to_config(self, show_feedback=False):
        try:
            confidence = float(self.confidence_var.get().strip())
            scan_interval = float(self.scan_interval_var.get().strip())
            movement_duration = int(float(self.movement_duration_var.get().strip()))
        except ValueError:
            messagebox.showerror("Invalid Input", "Check confidence, scan interval, and movement duration values.")
            return False

        if not 0.1 <= confidence <= 1.0:
            messagebox.showerror("Invalid Confidence", "Must be between 0.10 and 1.00.")
            return False
        if not 0.2 <= scan_interval <= 10:
            messagebox.showerror("Invalid Scan", "Scan interval must be 0.2-10.")
            return False
        if not 30 <= movement_duration <= 3600:
            messagebox.showerror("Invalid Move", "Movement duration must be 30-3600.")
            return False

        self.config["game_window_title"] = self.window_title_var.get().strip()
        self.config["discord_webhook"] = self.webhook_var.get().strip()
        self.config["confidence"] = round(confidence, 2)
        self.config["scan_interval"] = round(scan_interval, 2)
        self.config["movement_duration"] = movement_duration
        self.config["match_mode"] = self.mode_var.get()
        self.config["window_focus_required"] = bool(self.focus_required_var.get())
        self.config["auto_focus_window"] = bool(self.auto_focus_var.get())
        self.config["detection_backend"] = self.backend_var.get()

        self._save_hsv_settings()

        # Combat settings (Phase 5)
        combat_settings = self.config.setdefault("combat_settings", {})
        combat_settings["smart_combat_enabled"] = bool(self.smart_combat_var.get())
        combat_settings["first_person"] = bool(self.first_person_var.get())

        new_keys = {}
        for key_id, variable in self.key_vars.items():
            value = variable.get().strip().lower()
            if value:
                new_keys[key_id] = value
        self.config["keys"] = new_keys

        save_config(self.config)
        self.config = load_config()
        self.refresh_runtime_status()

        if show_feedback:
            self.log("Settings saved.")
        return True

    def refresh_window_list(self, log_result=True):
        titles = list_visible_window_titles()
        current = self.window_title_var.get().strip()
        if current and current not in titles:
            titles.insert(0, current)
        self.cmb_windows["values"] = titles
        if log_result:
            self.log(f"Found {len(titles)} windows.")

    def refresh_asset_widgets(self):
        records = get_asset_records(self.config)
        ready = sum(1 for r in records if r["state"] == "custom")
        self.asset_summary_label.config(text=f"{ready} / {len(records)} assets ready")
        for record in records:
            key = record["key"]
            if key in self.asset_widgets:
                status = self.asset_widgets[key]["status"]
                if record["state"] == "custom":
                    status.config(text="✓", foreground=self.colors["GREEN"])
                else:
                    status.config(text="❌", foreground=self.colors["RED"])

    def _on_hsv_toggle(self, img_key):
        var_enabled = self.hsv_vars.get((img_key, "enabled"))
        if not var_enabled:
            return
        # Find the row frame for this asset (walk widget tree to find it)
        for widget in self.settings_panel.content_frame.winfo_children():
            if hasattr(widget, "winfo_children"):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Frame):
                        children = child.winfo_children()
                        if children and isinstance(children[0], ttk.Checkbutton):
                            check_text = children[0].cget("text")
                            if check_text == IMAGE_SPECS.get(img_key, {}).get("label", ""):
                                self._apply_hsv_row_state(var_enabled.get(), child)
                                break

    def _apply_hsv_row_state(self, enabled, row):
        for child in row.winfo_children():
            if isinstance(child, ttk.Entry):
                child.configure(state="normal" if enabled else "disabled")

    def _save_hsv_settings(self):
        HSV_KEYS = ["ultimate", "return_to_lobby_alone"]
        for img_key in HSV_KEYS:
            enabled = bool(self.hsv_vars.get((img_key, "enabled"), tk.BooleanVar()).get())
            if not enabled:
                self.config.setdefault("hsv_settings", {})[img_key] = {
                    "enabled": False,
                    "h_min": 0, "h_max": 179,
                    "s_min": 0, "s_max": 255,
                    "v_min": 0, "v_max": 255,
                }
                continue

            values = {}
            for field in ["h_min", "h_max", "s_min", "s_max", "v_min", "v_max"]:
                var = self.hsv_vars.get((img_key, field))
                if var:
                    try:
                        values[field] = max(0, min(255, int(var.get())))
                    except (ValueError, tk.TclError):
                        values[field] = 0

            # Clamp specific ranges
            values["h_min"] = min(values.get("h_min", 0), 179)
            values["h_max"] = min(values.get("h_max", 179), 179)
            values["enabled"] = True

            self.config.setdefault("hsv_settings", {})[img_key] = values

    def refresh_runtime_status(self):
        records = get_asset_records(self.config)
        required = get_required_asset_records(self.config)
        ready_count = sum(1 for r in required if r["state"] == "custom")

        window_title = self._selected_window_title()
        window_match = find_window_by_title(window_title) if window_title else None
        issues = list(get_required_setup_issues(self.config))

        if self.is_running:
            self.runtime_info_label.config(
                text=f"Running | Matches: {self.match_count}",
                foreground=self.colors["GREEN"]
            )
        elif issues:
            self.runtime_info_label.config(
                text=f"⚠ {len(issues)} setup issue(s) - open Settings",
                foreground=self.colors["YELLOW"]
            )
        elif window_match:
            self.runtime_info_label.config(
                text=f"✓ Ready | {ready_count}/{len(required)} assets | Window: {window_match[1][:30]}",
                foreground=self.colors["GREEN"]
            )
        else:
            self.runtime_info_label.config(
                text=f"⚠ Set game window in Settings",
                foreground=self.colors["YELLOW"]
            )

        self.refresh_asset_widgets()
        self.refresh_coordinate_labels()

    def refresh_runtime_status_loop(self):
        if self.root.winfo_exists():
            self.refresh_runtime_status()
            self.root.after(2000, self.refresh_runtime_status_loop)

    def refresh_coordinate_labels(self):
        pos1 = self.config.get("pos_1")
        pos2 = self.config.get("pos_2")
        self.book_coord_label.config(
            text=f"Stats Icon: {pos1 if is_coordinate_ready(pos1) else 'not set'} | "
                 f"Upgrade Btn: {pos2 if is_coordinate_ready(pos2) else 'not set'}"
        )

    def test_webhook(self):
        if not self.persist_form_to_config(show_feedback=False):
            return
        webhook = self.config.get("discord_webhook", "")
        if not webhook:
            messagebox.showwarning("Missing", "Enter a webhook URL first.")
            return
        self.log("Testing webhook...")
        threading.Thread(target=self._test_webhook_worker, args=(webhook,), daemon=True).start()

    def _test_webhook_worker(self, webhook):
        code = send_discord(webhook, "[Zedsu] Webhook test OK.")
        if code and 200 <= code < 300:
            self.root.after(0, lambda: self.log(f"Webhook OK ({code})"))
        else:
            self.root.after(0, lambda: self.log("Webhook failed.", is_error=True))

    def toggle_bot(self):
        if self.is_running:
            self.stop_bot()
            return
        if not self.persist_form_to_config(show_feedback=False):
            return

        blockers = list(get_required_setup_issues(self.config))
        window_title = self.config.get("game_window_title", "").strip()
        window_match = find_window_by_title(window_title) if window_title else None
        if self.config.get("window_focus_required", True) and not window_match:
            blockers.append(f"Game window not found: {window_title or '[empty]'}")

        portability = get_runtime_portability_report(self.config, window_rect=self._selected_window_rect())
        blockers.extend(portability["blockers"])

        if blockers:
            self.settings_panel.is_open = True
            self.settings_panel.toggle_btn.config(text="▼")
            self.settings_panel.content_frame.pack(fill=tk.X, padx=8, pady=(0, 6))
            messagebox.showwarning("Setup Incomplete", "\n".join(f"- {i}" for i in blockers))
            self.log("Setup incomplete: " + blockers[0], is_error=True)
            return

        self.is_running = True
        self.engine.start()
        self.start_time = time.time()
        self.set_running_state(True)
        self.btn_toggle.config(text="▶  RUNNING", state="disabled")
        self.btn_stop.config(state="normal")
        self.update_status("STARTING", self.colors["BLUE"])
        self.update_timer()
        self.log("Bot started.")
        self.root.after(200, self.hide_for_runtime)
        threading.Thread(target=self.engine.bot_loop, daemon=True).start()

    def stop_bot(self):
        self.engine.stop()
        self.is_running = False
        self.set_running_state(False)
        self.btn_toggle.config(text="▶  START", state="normal")
        self.btn_stop.config(state="disabled")
        self.update_status("STOPPING", self.colors["YELLOW"])
        self.log("Stopping...")
        self.restore_after_runtime()
        self.root.after(500, lambda: self.update_status("IDLE", self.colors["MUTED"]))

    def set_running_state(self, running):
        state = "disabled" if running else "normal"
        for w in self.lockable_widgets:
            try:
                w.configure(state=state)
            except tk.TclError:
                continue

    def update_status(self, text, color):
        self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))

    def update_match_count(self):
        self.match_label.config(text=f"Matches: {self.match_count}")

    def update_timer_ui(self, time_str):
        pass  # Minimal UI - don't show timer

    def update_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            self.match_label.config(text=f"Matches: {self.match_count} | {elapsed // 60}m")
            self.root.after(5000, self.update_timer)
        elif not self.is_running:
            self.match_label.config(text="Matches: 0")

    def hide_for_runtime(self):
        if not hasattr(self, 'was_hidden') or not self.was_hidden:
            self.was_hidden = True
            self.root.iconify()

    def restore_after_runtime(self):
        if hasattr(self, 'was_hidden') and self.was_hidden:
            self.was_hidden = False
            self.restore_main_window()

    def _register_hotkey(self):
        try:
            self.hotkey_handler = keyboard.add_hotkey("f1", self.toggle_bot_hotkey)
            self.log("F1 hotkey registered.")
        except Exception as exc:
            self.log(f"F1 unavailable: {exc}", is_error=True)

    def toggle_bot_hotkey(self):
        self.root.after(0, self.toggle_bot)

    def log(self, msg, is_error=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def update():
            self.console.configure(state="normal")
            color = "#fca5a5" if is_error else "#e2e8f0"
            tag = f"err_{time.time_ns()}"
            self.console.insert(tk.END, f"[{timestamp}] {msg}\n")
            end = self.console.index(tk.END)
            start = f"{end} linestart".replace("end-1c", end)
            self.console.tag_add(tag, f"{end} linestart", end)
            self.console.tag_config(tag, foreground=color)
            self.console.see(tk.END)
            self.console.configure(state="disabled")
        self.root.after(0, update)

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                prefix = "[ERROR] " if is_error else ""
                f.write(f"[{full_ts}] {prefix}{msg}\n")
        except Exception:
            pass

    def clear_log(self):
        def update():
            self.console.configure(state="normal")
            self.console.delete("1.0", tk.END)
            self.console.configure(state="disabled")
        self.root.after(0, update)

    def export_config(self):
        """Export current config (without assets) to a portable JSON file."""
        from tkinter import filedialog
        import json

        # First save current form state
        self.persist_form_to_config(show_feedback=False)

        # Export portable fields only
        export_keys = [
            "game_window_title", "discord_webhook", "confidence",
            "scan_interval", "match_mode", "movement_duration",
            "window_focus_required", "auto_focus_window",
            "keys", "coordinate_profiles", "outcome_area_profile",
            "coordinate_layout_version",
        ]
        export_data = {k: self.config.get(k) for k in export_keys if k in self.config}
        export_data["_exported_by"] = "Zedsu"
        export_data["_export_version"] = 1

        path = filedialog.asksaveasfilename(
            title="Export Config",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="zedsu_config.json",
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2)
            self.log(f"Config exported: {os.path.basename(path)}")
        except Exception as exc:
            self.log(f"Export failed: {exc}", is_error=True)

    def import_config(self):
        """Import a portable config JSON file."""
        from tkinter import filedialog
        import json

        path = filedialog.askopenfilename(
            title="Import Config",
            filetypes=[("JSON files", "*.json")],
            initialdir=os.path.dirname(CONFIG_FILE),
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            if data.get("_exported_by") != "Zedsu":
                messagebox.showwarning("Invalid File", "This doesn't look like a Zedsu config file.")
                return

            # Merge into current config
            for key, value in data.items():
                if key.startswith("_"):
                    continue
                if key in self.config:
                    self.config[key] = value

            save_config(self.config)
            self.config = load_config()

            # Update UI variables
            self.window_title_var.set(self.config.get("game_window_title", ""))
            self.webhook_var.set(self.config.get("discord_webhook", ""))
            self.confidence_var.set(str(self.config.get("confidence", 0.8)))
            self.scan_interval_var.set(str(self.config.get("scan_interval", 1.5)))
            self.movement_duration_var.set(str(self.config.get("movement_duration", 300)))
            self.mode_var.set(self.config.get("match_mode", "full"))
            self.focus_required_var.set(self.config.get("window_focus_required", True))
            self.auto_focus_var.set(self.config.get("auto_focus_window", True))
            for key_id, value in self.config.get("keys", {}).items():
                self.key_vars.setdefault(key_id, tk.StringVar(value=value))
                self.key_vars[key_id].set(value)

            self.refresh_runtime_status()
            self.log(f"Config imported from: {os.path.basename(path)}")
            messagebox.showinfo("Done", "Config imported. Click Save Settings to apply.")
        except Exception as exc:
            self.log(f"Import failed: {exc}", is_error=True)
            messagebox.showerror("Import Error", str(exc))

    def restore_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.after(50, self.root.focus_force)

    def open_path(self, path_value):
        if not path_value:
            return
        absolute_path = resolve_path(path_value)
        if os.path.isdir(absolute_path):
            os.startfile(absolute_path)
            return
        if os.path.exists(absolute_path):
            os.startfile(absolute_path)
            return
        messagebox.showwarning("Missing", f"Not found:\n{absolute_path}")

    # ------------------------------------------------------------
    # ASSET/COORDINATE PICKING
    # ------------------------------------------------------------
    def capture_all_assets(self):
        if self.is_running:
            messagebox.showwarning("Running", "Stop the bot first.")
            return
        if not self.persist_form_to_config(show_feedback=False):
            return

        self.capture_queue = list(IMAGE_ORDER)
        messagebox.showinfo(
            "Guided Capture",
            "Open the game. App will guide you through each asset capture.\n\nPress OK to start."
        )
        self.log("Starting guided capture...")
        self.assets_panel.is_open = True
        self.assets_panel.toggle_btn.config(text="▼")
        self.assets_panel.content_frame.pack(fill=tk.X, padx=8, pady=(0, 6))
        self._capture_next_asset()

    def _capture_next_asset(self):
        if not self.capture_queue:
            self.log("Capture complete.")
            self.refresh_asset_widgets()
            return
        key = self.capture_queue.pop(0)
        self.log(f"Capture: {IMAGE_SPECS[key]['label']}")
        self.start_asset_capture(key, queued=True)

    def start_asset_capture(self, key, queued=False):
        if self.is_running:
            return
        window_rect = self._selected_window_rect()

        def launch_tool(screenshot):
            ScreenCaptureTool(
                self.root, screenshot, key, ASSETS_DIR,
                on_complete=lambda path: self._complete_asset_capture(key, path, queued, window_rect),
                on_cancel=lambda: self._cancel_asset_capture(queued),
                save_name=IMAGE_SPECS[key]["filename"],
                title=IMAGE_SPECS[key]["label"],
            )

        self._begin_screen_tool(launch_tool)

    def _complete_asset_capture(self, key, path, queued, window_rect=None):
        set_asset_path(self.config, key, path, window_rect=window_rect,
                       window_title=self._selected_window_title(),
                       capture_source="guided_capture")
        save_config(self.config)
        self.config = load_config()
        self.restore_main_window()
        self.refresh_asset_widgets()
        self.log(f"Captured: {IMAGE_SPECS[key]['label']}")
        if queued:
            self.root.after(450, self._capture_next_asset)

    def _cancel_asset_capture(self, queued):
        self.restore_main_window()
        if queued:
            self.capture_queue = []
            self.log("Capture cancelled.", is_error=True)

    def _pick_combat_region(self, region_key):
        """Open screen capture tool to pick a combat detection region."""
        if self.is_running:
            return
        window_rect = self._selected_window_rect()

        def launch_tool(screenshot):
            from src.core.vision import ScreenCaptureTool
            ScreenCaptureTool(
                parent=self.root,
                screenshot=screenshot,
                key=region_key,
                assets_dir=ASSETS_DIR,
                on_complete=lambda result: self._complete_combat_region_pick(region_key, result, window_rect),
                on_cancel=self.restore_main_window,
                save_name=f"combat_region_{region_key}.png",
                title=region_key.replace("_", " ").title(),
            )
        self._begin_screen_tool(launch_tool)

    def _complete_combat_region_pick(self, region_key, result, window_rect=None):
        """Save the picked combat region as screen ratios."""
        from src.utils.config import set_combat_region
        if not result:
            self.restore_main_window()
            return
        l, t, r, b = result[0], result[1], result[2], result[3]
        w, h = window_rect[2] - window_rect[0], window_rect[3] - window_rect[1]
        x_ratio = (l - window_rect[0]) / w if w > 0 else 0
        y_ratio = (t - window_rect[1]) / h if h > 0 else 0
        w_ratio = (r - l) / w if w > 0 else 0
        h_ratio = (b - t) / h if h > 0 else 0
        set_combat_region(self.config, region_key, x_ratio, y_ratio, w_ratio, h_ratio)
        save_config(self.config)
        self.config = load_config()
        self.restore_main_window()
        self.log(f"Combat region saved: {region_key}")

    def _test_combat_detection(self):
        """Run one combat signal scan and display results."""
        try:
            from src.core.vision import get_combat_detector
            detector = get_combat_detector(self.config)
            signals = detector.scan_all_signals()
            lines = []
            lines.append(f"enemy_nearby={signals.get('enemy_nearby', False)} "
                         f"(green={signals.get('_green_ratio', 0):.5f})")
            lines.append(f"hit_confirmed={signals.get('hit_confirmed', False)} "
                         f"(red={signals.get('_red_ratio', 0):.5f})")
            lines.append(f"player_hp_low={signals.get('player_hp_low', False)} "
                         f"(green={signals.get('_player_green_ratio', 0):.5f})")
            lines.append(f"in_combat={signals.get('in_combat', False)} "
                         f"(white={signals.get('_incombat_ratio', 0):.5f})")
            lines.append(f"kill_confirmed={signals.get('kill_confirmed', False)} "
                         f"(white={signals.get('_kill_ratio', 0):.5f})")
            self.combat_debug_label.config(text=" | ".join(lines))
        except Exception as exc:
            self.combat_debug_label.config(text=f"Error: {exc}")

    def _update_yolo_status(self):
        """Update YOLO model status indicator (D-29: UI warning when missing)."""
        try:
            from src.core.vision import _get_yolo_detector
            detector = _get_yolo_detector()
            if detector.is_available():
                self.yolo_status_label.config(text="Model loaded", foreground="#22c55e")
            else:
                error = detector.get_load_error() or "not found"
                self.yolo_status_label.config(
                    text=f"Model not found — far-range detection disabled",
                    foreground="#ef4444"
                )
        except Exception as exc:
            self.yolo_status_label.config(text=f"Error: {exc}", foreground="#f97316")

    def _capture_yolo_sample(self):
        """Capture screenshot for YOLO training dataset."""
        import time as _time
        try:
            from src.core.vision import _mss_capture_haystack, _normalize_region, get_window_rect
        except Exception as exc:
            messagebox.showwarning("Import Error", f"Could not import vision module: {exc}")
            return

        window_title = str(self.config.get("game_window_title", ""))
        region_rect = get_window_rect(window_title) if window_title else None
        if not region_rect:
            messagebox.showwarning("Window Not Found", "Game window not detected.")
            return

        normalized = _normalize_region(region_rect)
        haystack_rgb, _ = _mss_capture_haystack(normalized)
        if haystack_rgb is None:
            messagebox.showwarning("Capture Failed", "Could not capture screen.")
            return

        # Save image as PNG
        output_dir = self._yolo_dataset_dir.get()
        os.makedirs(output_dir, exist_ok=True)

        import cv2
        class_name = self._yolo_capture_class.get()
        filename = f"{class_name}_{int(_time.time() * 1000)}.png"
        filepath = os.path.join(output_dir, filename)
        img_bgr = haystack_rgb[:, :, ::-1]  # RGB -> BGR
        cv2.imwrite(filepath, img_bgr)

        messagebox.showinfo("Captured",
            f"Saved: {filename}\n\n"
            f"Class: {class_name}\n\n"
            f"Next: open LabelImg and annotate this image.\n"
            f"Use classes.txt with: enemy_player, afk_cluster, ultimate_bar, etc.")

    def _begin_screen_tool(self, launch_tool, delay_ms=1300):
        self.root.iconify()
        def take_screenshot():
            try:
                screenshot = pyautogui.screenshot()
            except Exception as exc:
                self.restore_main_window()
                self.log(f"Screenshot failed: {exc}", is_error=True)
                return
            launch_tool(screenshot)
        self.root.after(delay_ms, take_screenshot)

    def on_close(self):
        if self.is_running:
            self.stop_bot()
        if self.hotkey_handler is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_handler)
            except Exception:
                pass
        self.root.destroy()
