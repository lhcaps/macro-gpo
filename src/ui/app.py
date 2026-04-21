import os
import shutil
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, scrolledtext, ttk

import keyboard
import pyautogui
from PIL import Image, ImageTk

from src.core.bot_engine import BotEngine
from src.core.vision import ScreenCaptureTool, locate_image
from src.ui.components import AreaPicker, CoordinatePicker
from src.utils.config import (
    ASSETS_DIR,
    CAPTURES_DIR,
    COORDINATE_SPECS,
    CONFIG_FILE,
    IMAGE_ORDER,
    IMAGE_SPECS,
    LOG_FILE,
    RUNTIME_DIR,
    get_asset_records,
    get_optional_asset_records,
    get_optional_setup_warnings,
    get_required_asset_records,
    get_required_setup_issues,
    is_coordinate_ready,
    is_asset_custom,
    load_config,
    resolve_path,
    save_config,
    set_asset_path,
)
from src.utils.discord import send_discord
from src.utils.windows import (
    bring_window_to_foreground,
    find_window_by_title,
    get_foreground_window_title,
    get_window_rect,
    list_visible_window_titles,
)


class ZedsuApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Zedsu Control Center")
        self.root.geometry("1180x860")
        self.root.minsize(1040, 780)

        self.is_running = False
        self.match_count = 0
        self.start_time = None
        self.config = load_config()
        self.engine = BotEngine(self)

        self.asset_rows = {}
        self.asset_previews = {}
        self.lockable_widgets = []
        self.capture_queue = []
        self.hotkey_handler = None
        self.was_hidden_for_runtime = False
        self.assets_canvas = None

        self._setup_variables()
        self._apply_theme()
        self._build_ui()
        self._register_hotkey()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.refresh_window_list(log_result=False)
        self.refresh_asset_panel()
        self.refresh_coordinate_labels()
        self.refresh_runtime_summary()
        self.log("Control center ready. Complete the setup checklist, then press START or F1.")
        self.root.after(1200, self.refresh_runtime_summary_loop)

    def _setup_variables(self):
        self.window_title_var = tk.StringVar(value=self.config.get("game_window_title", ""))
        self.webhook_var = tk.StringVar(value=self.config.get("discord_webhook", ""))
        self.confidence_var = tk.StringVar(value=str(self.config.get("confidence", 0.8)))
        self.scan_interval_var = tk.StringVar(value=str(self.config.get("scan_interval", 1.5)))
        self.movement_duration_var = tk.StringVar(value=str(self.config.get("movement_duration", 300)))
        self.mode_var = tk.StringVar(value=self.config.get("match_mode", "full"))
        self.focus_required_var = tk.BooleanVar(value=self.config.get("window_focus_required", True))
        self.auto_focus_var = tk.BooleanVar(value=self.config.get("auto_focus_window", True))

        self.key_vars = {}
        for key_id, value in self.config.get("keys", {}).items():
            self.key_vars[key_id] = tk.StringVar(value=value)

    def _apply_theme(self):
        self.root.configure(bg="#e2e8f0")
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TNotebook", background="#e2e8f0", borderwidth=0)
        style.configure("TNotebook.Tab", padding=(14, 8), font=("Segoe UI", 10, "bold"))
        style.map(
            "TNotebook.Tab",
            background=[("selected", "#f8fafc"), ("active", "#dbeafe")],
            foreground=[("selected", "#0f172a"), ("active", "#0f172a")],
        )
        style.configure("TFrame", background="#e2e8f0")
        style.configure("Card.TFrame", background="#f8fafc")
        style.configure("TLabel", background="#e2e8f0", foreground="#0f172a", font=("Segoe UI", 10))
        style.configure("Hero.TLabel", background="#e2e8f0", foreground="#0f172a", font=("Segoe UI", 23, "bold"))
        style.configure("Section.TLabel", background="#e2e8f0", foreground="#0f172a", font=("Segoe UI", 15, "bold"))
        style.configure("Muted.TLabel", background="#e2e8f0", foreground="#475569", font=("Segoe UI", 10))
        style.configure("Value.TLabel", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 18, "bold"))
        style.configure("SmallValue.TLabel", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 12, "bold"))
        style.configure("TButton", padding=(10, 7), font=("Segoe UI", 10))
        style.configure(
            "Accent.TButton",
            padding=(12, 8),
            font=("Segoe UI", 10, "bold"),
            foreground="white",
            background="#0284c7",
        )
        style.map(
            "Accent.TButton",
            background=[("pressed", "#0369a1"), ("active", "#0ea5e9")],
            foreground=[("pressed", "white"), ("active", "white")],
        )
        style.configure("TLabelframe", background="#f8fafc", borderwidth=1)
        style.configure("TLabelframe.Label", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 10, "bold"))
        style.configure("Card.TLabelframe", background="#f8fafc", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background="#f8fafc", foreground="#0f172a", font=("Segoe UI", 10, "bold"))
        style.configure("TCheckbutton", background="#f8fafc", font=("Segoe UI", 10))
        style.configure("TRadiobutton", background="#f8fafc", font=("Segoe UI", 10))
        style.configure("TEntry", padding=6)
        style.configure("TCombobox", padding=4)
        style.configure(
            "Ready.Horizontal.TProgressbar",
            troughcolor="#cbd5e1",
            background="#0ea5e9",
            bordercolor="#cbd5e1",
            lightcolor="#0ea5e9",
            darkcolor="#0284c7",
            thickness=10,
        )

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=12)

        self.dashboard_tab = ttk.Frame(self.notebook, padding=16)
        self.setup_tab = ttk.Frame(self.notebook, padding=16)
        self.assets_tab = ttk.Frame(self.notebook, padding=16)
        self.controls_tab = ttk.Frame(self.notebook, padding=16)

        self.notebook.add(self.dashboard_tab, text=" Dashboard ")
        self.notebook.add(self.setup_tab, text=" Setup ")
        self.notebook.add(self.assets_tab, text=" Assets ")
        self.notebook.add(self.controls_tab, text=" Controls ")

        self._build_dashboard_tab()
        self._build_setup_tab()
        self._build_assets_tab()
        self._build_controls_tab()

    def _build_dashboard_tab(self):
        ttk.Label(self.dashboard_tab, text="Zedsu", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            self.dashboard_tab,
            text="A guided control center for setup, capture, monitoring, and one-click runtime.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 14))

        cards = ttk.Frame(self.dashboard_tab)
        cards.pack(fill=tk.X)

        runtime_card = ttk.LabelFrame(cards, text=" Runtime ", style="Card.TLabelframe", padding=14)
        runtime_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        ttk.Label(runtime_card, text="Status", style="Muted.TLabel").pack(anchor=tk.W)
        self.status_label = ttk.Label(runtime_card, text="IDLE", style="Value.TLabel")
        self.status_label.pack(anchor=tk.W, pady=(0, 8))
        self.runtime_mode_label = ttk.Label(
            runtime_card,
            text="Flow: equip melee -> 5x M1 -> dynamic move -> repeat",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        )
        self.runtime_mode_label.pack(anchor=tk.W, fill=tk.X, pady=(0, 8))

        runtime_stats = ttk.Frame(runtime_card, style="Card.TFrame")
        runtime_stats.pack(fill=tk.X)
        runtime_stats.columnconfigure((0, 1, 2), weight=1)

        self._build_stat_tile(runtime_stats, 0, "Matches", "0", "match_value")
        self._build_stat_tile(runtime_stats, 1, "Uptime", "00:00:00", "timer_value")
        self._build_stat_tile(runtime_stats, 2, "Assets", "0 / 8 ready", "assets_value")

        ttk.Separator(runtime_card, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=12)

        ttk.Label(runtime_card, text="Last action", style="Muted.TLabel").pack(anchor=tk.W)
        self.last_action_label = ttk.Label(
            runtime_card,
            text="Waiting for setup...",
            style="SmallValue.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        )
        self.last_action_label.pack(anchor=tk.W, fill=tk.X)

        control_row = ttk.Frame(runtime_card, style="Card.TFrame")
        control_row.pack(fill=tk.X, pady=(16, 0))

        self.btn_toggle = ttk.Button(control_row, text="START BOT", style="Accent.TButton", command=self.toggle_bot)
        self.btn_toggle.pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn_save_all = ttk.Button(control_row, text="Save Settings", command=lambda: self.persist_form_to_config(show_feedback=True))
        btn_save_all.pack(side=tk.LEFT, padx=(10, 0))
        self.lockable_widgets.append(btn_save_all)

        quick_row = ttk.Frame(runtime_card, style="Card.TFrame")
        quick_row.pack(fill=tk.X, pady=(10, 0))

        btn_capture_all = ttk.Button(quick_row, text="Capture All Assets", command=self.capture_all_assets)
        btn_capture_all.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_capture_all)

        btn_assets_folder = ttk.Button(quick_row, text="Open Assets Folder", command=lambda: self.open_path(ASSETS_DIR))
        btn_assets_folder.pack(side=tk.LEFT, padx=(8, 0))

        btn_runtime_folder = ttk.Button(quick_row, text="Open Runtime Folder", command=lambda: self.open_path(str(RUNTIME_DIR)))
        btn_runtime_folder.pack(side=tk.LEFT, padx=(8, 0))

        readiness_card = ttk.LabelFrame(cards, text=" Readiness Checklist ", style="Card.TLabelframe", padding=14)
        readiness_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.window_summary_label = ttk.Label(readiness_card, text="Window: not checked", style="SmallValue.TLabel", wraplength=360)
        self.window_summary_label.pack(anchor=tk.W, pady=(0, 10))

        self.setup_summary_label = ttk.Label(readiness_card, text="Setup pending", style="SmallValue.TLabel", wraplength=360)
        self.setup_summary_label.pack(anchor=tk.W, pady=(0, 12))

        self.readiness_meter_label = ttk.Label(
            readiness_card,
            text="Readiness: 0 / 4 checkpoints",
            style="Muted.TLabel",
            wraplength=360,
        )
        self.readiness_meter_label.pack(anchor=tk.W)

        self.readiness_progress = ttk.Progressbar(
            readiness_card,
            maximum=100,
            mode="determinate",
            style="Ready.Horizontal.TProgressbar",
        )
        self.readiness_progress.pack(fill=tk.X, pady=(6, 10))

        self.combat_summary_label = ttk.Label(
            readiness_card,
            text="Combat verification: using fallback heuristic until the combat asset is captured.",
            style="Muted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        )
        self.combat_summary_label.pack(anchor=tk.W, pady=(0, 12))

        ttk.Label(readiness_card, text="What to do next", style="Muted.TLabel").pack(anchor=tk.W)
        self.checklist_label = ttk.Label(
            readiness_card,
            text=(
                "1. Set the game window title.\n"
                        "2. Capture all eight assets.\n"
                "3. Set the Statistics Icon and Melee Upgrade Button coordinates."
            ),
            wraplength=360,
            justify=tk.LEFT,
        )
        self.checklist_label.pack(anchor=tk.W, fill=tk.X, pady=(4, 10))

        ttk.Label(readiness_card, text="Quick tips", style="Muted.TLabel").pack(anchor=tk.W)
        tips_text = (
            "Use windowed or borderless mode.\n"
            "Keep the game visible while capturing assets.\n"
            "Lower confidence slightly if detection misses a button."
        )
        ttk.Label(readiness_card, text=tips_text, wraplength=360, justify=tk.LEFT).pack(anchor=tk.W, fill=tk.X, pady=(4, 0))

        log_card = ttk.LabelFrame(self.dashboard_tab, text=" Live Log ", style="Card.TLabelframe", padding=10)
        log_card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        self.console = scrolledtext.ScrolledText(
            log_card,
            height=20,
            state="disabled",
            bg="#0f172a",
            fg="#e2e8f0",
            insertbackground="#e2e8f0",
            font=("Consolas", 10),
            relief=tk.FLAT,
        )
        self.console.pack(fill=tk.BOTH, expand=True)

    def _build_stat_tile(self, parent, column, title, value, attribute_name):
        tile = ttk.LabelFrame(parent, text=f" {title} ", style="Card.TLabelframe", padding=10)
        tile.grid(row=0, column=column, sticky="nsew", padx=(0 if column == 0 else 8, 0))
        value_label = ttk.Label(tile, text=value, style="Value.TLabel")
        value_label.pack(anchor=tk.W)
        setattr(self, attribute_name, value_label)

    def _build_setup_tab(self):
        ttk.Label(self.setup_tab, text="Setup Wizard", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            self.setup_tab,
            text="Everything needed for first-run onboarding lives here: window matching, detection tuning, and Discord.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 14))

        top_row = ttk.Frame(self.setup_tab)
        top_row.pack(fill=tk.X)

        window_card = ttk.LabelFrame(top_row, text=" Game Window ", style="Card.TLabelframe", padding=14)
        window_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        ttk.Label(window_card, text="Window title or partial match").pack(anchor=tk.W)
        self.cmb_windows = ttk.Combobox(window_card, textvariable=self.window_title_var)
        self.cmb_windows.pack(fill=tk.X, pady=(6, 8))
        self.lockable_widgets.append(self.cmb_windows)

        window_buttons = ttk.Frame(window_card, style="Card.TFrame")
        window_buttons.pack(fill=tk.X)

        btn_refresh_windows = ttk.Button(window_buttons, text="Refresh Window List", command=self.refresh_window_list)
        btn_refresh_windows.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_refresh_windows)

        btn_use_active = ttk.Button(window_buttons, text="Use Active Window In 3s", command=self.capture_active_window_title)
        btn_use_active.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(btn_use_active)

        ttk.Label(
            window_card,
            text="Tip: open the game first, then use the 3-second helper to capture the exact title.",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 0))

        behavior_card = ttk.LabelFrame(top_row, text=" Bot Behavior ", style="Card.TLabelframe", padding=14)
        behavior_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self._build_labeled_entry(behavior_card, "Confidence", self.confidence_var, "0.10 to 1.00")
        self._build_labeled_entry(behavior_card, "Scan interval (sec)", self.scan_interval_var, "0.2 to 10")
        self._build_labeled_entry(behavior_card, "Active movement (sec)", self.movement_duration_var, "30 to 3600")

        self.chk_focus = ttk.Checkbutton(
            behavior_card,
            text="Require the game window before sending input",
            variable=self.focus_required_var,
        )
        self.chk_focus.pack(anchor=tk.W, pady=(6, 0))
        self.lockable_widgets.append(self.chk_focus)

        self.chk_autofocus = ttk.Checkbutton(
            behavior_card,
            text="Auto-focus the game window when possible",
            variable=self.auto_focus_var,
        )
        self.chk_autofocus.pack(anchor=tk.W, pady=(4, 0))
        self.lockable_widgets.append(self.chk_autofocus)

        middle_row = ttk.Frame(self.setup_tab)
        middle_row.pack(fill=tk.X, pady=(14, 0))

        mode_card = ttk.LabelFrame(middle_row, text=" Match Mode ", style="Card.TLabelframe", padding=14)
        mode_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        ttk.Radiobutton(mode_card, text="Full Match", variable=self.mode_var, value="full").pack(anchor=tk.W)
        ttk.Label(
            mode_card,
            text="Safer default. Stay in the match and keep the bot active until the end screen appears.",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 8))

        ttk.Radiobutton(mode_card, text="Quick Leave", variable=self.mode_var, value="quick").pack(anchor=tk.W)
        ttk.Label(
            mode_card,
            text="Leaves faster when the return-to-lobby button becomes available.",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(4, 0))

        discord_card = ttk.LabelFrame(middle_row, text=" Discord Webhook ", style="Card.TLabelframe", padding=14)
        discord_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        ttk.Label(discord_card, text="Webhook URL (optional)").pack(anchor=tk.W)
        webhook_row = ttk.Frame(discord_card, style="Card.TFrame")
        webhook_row.pack(fill=tk.X, pady=(6, 8))

        self.ent_webhook = ttk.Entry(webhook_row, textvariable=self.webhook_var, show="*")
        self.ent_webhook.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.lockable_widgets.append(self.ent_webhook)

        self.btn_show_webhook = ttk.Button(webhook_row, text="Show", width=7, command=self.toggle_webhook_visibility)
        self.btn_show_webhook.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(self.btn_show_webhook)

        self.btn_test_webhook = ttk.Button(webhook_row, text="Test", width=7, command=self.test_webhook)
        self.btn_test_webhook.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(self.btn_test_webhook)

        ttk.Label(
            discord_card,
            text="If you skip this, the bot still works. You just will not receive Discord match updates.",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        ).pack(anchor=tk.W)

        bottom_row = ttk.Frame(self.setup_tab)
        bottom_row.pack(fill=tk.X, pady=(14, 0))

        btn_save_setup = ttk.Button(bottom_row, text="Save Setup", command=lambda: self.persist_form_to_config(show_feedback=True))
        btn_save_setup.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_save_setup)

        btn_open_config = ttk.Button(bottom_row, text="Open Config File", command=lambda: self.open_path(CONFIG_FILE))
        btn_open_config.pack(side=tk.LEFT, padx=(8, 0))

    def _build_labeled_entry(self, parent, label_text, variable, hint_text):
        container = ttk.Frame(parent, style="Card.TFrame")
        container.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(container, text=label_text, width=20).pack(side=tk.LEFT)
        entry = ttk.Entry(container, textvariable=variable)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(container, text=hint_text, style="Muted.TLabel").pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(entry)

    def _build_assets_tab(self):
        ttk.Label(self.assets_tab, text="Asset Studio", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            self.assets_tab,
            text="Capture or import each template once. The app blocks startup until all required assets are truly ready.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 14))

        summary_card = ttk.LabelFrame(self.assets_tab, text=" Asset Status ", style="Card.TLabelframe", padding=14)
        summary_card.pack(fill=tk.X)

        self.asset_summary_label = ttk.Label(summary_card, text="0 / 8 assets ready", style="Value.TLabel")
        self.asset_summary_label.pack(side=tk.LEFT)

        summary_text = ttk.Frame(summary_card, style="Card.TFrame")
        summary_text.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(18, 0))

        self.asset_summary_detail_label = ttk.Label(
            summary_text,
            text="Startup still requires 7 core assets. The 8th asset improves combat verification and is included in the total count.",
            style="Muted.TLabel",
            wraplength=420,
            justify=tk.LEFT,
        )
        self.asset_summary_detail_label.pack(anchor=tk.W)

        self.assets_progress = ttk.Progressbar(
            summary_text,
            maximum=100,
            mode="determinate",
            style="Ready.Horizontal.TProgressbar",
        )
        self.assets_progress.pack(fill=tk.X, pady=(8, 0))

        summary_actions = ttk.Frame(summary_card, style="Card.TFrame")
        summary_actions.pack(side=tk.RIGHT)

        btn_test_detect = ttk.Button(summary_actions, text="Test Detect", command=self.test_asset_detection)
        btn_test_detect.pack(side=tk.LEFT, padx=(0, 8))
        self.lockable_widgets.append(btn_test_detect)

        btn_import_folder = ttk.Button(summary_actions, text="Import Asset Folder", command=self.import_asset_folder)
        btn_import_folder.pack(side=tk.LEFT, padx=(0, 8))
        self.lockable_widgets.append(btn_import_folder)

        btn_capture_all = ttk.Button(summary_actions, text="Guided Capture", command=self.capture_all_assets)
        btn_capture_all.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_capture_all)

        btn_refresh_assets = ttk.Button(summary_actions, text="Refresh", command=lambda: self.refresh_asset_panel(reload_config=True))
        btn_refresh_assets.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(btn_refresh_assets)

        btn_open_assets = ttk.Button(summary_actions, text="Open Assets Folder", command=lambda: self.open_path(ASSETS_DIR))
        btn_open_assets.pack(side=tk.LEFT, padx=(8, 0))

        canvas_holder = ttk.Frame(self.assets_tab)
        canvas_holder.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        canvas = tk.Canvas(canvas_holder, bg="#e2e8f0", highlightthickness=0)
        self.assets_canvas = canvas
        scrollbar = ttk.Scrollbar(canvas_holder, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        self.assets_scroll_frame = scroll_frame
        scroll_frame.bind("<Configure>", lambda _: canvas.configure(scrollregion=canvas.bbox("all")))
        self.assets_canvas_window = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        canvas.bind("<Configure>", lambda event: canvas.itemconfigure(self.assets_canvas_window, width=event.width))
        self.root.bind_all("<MouseWheel>", self._on_assets_mousewheel, add="+")
        self.root.bind_all("<Button-4>", self._on_assets_mousewheel_linux_up, add="+")
        self.root.bind_all("<Button-5>", self._on_assets_mousewheel_linux_down, add="+")

        for key in IMAGE_ORDER:
            meta = IMAGE_SPECS[key]
            row = ttk.LabelFrame(scroll_frame, text=f" {meta['label']} ", style="Card.TLabelframe", padding=10)
            row.pack(fill=tk.X, pady=6)

            info = ttk.Frame(row, style="Card.TFrame")
            info.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

            desc = ttk.Label(info, text=meta["description"], style="Muted.TLabel", wraplength=540, justify=tk.LEFT)
            desc.pack(anchor=tk.W)

            if not meta.get("required", True):
                ttk.Label(
                    info,
                    text="Recommended combat asset: improves melee equip confirmation without blocking startup.",
                    style="Muted.TLabel",
                    wraplength=540,
                    justify=tk.LEFT,
                ).pack(anchor=tk.W, pady=(4, 0))

            status_label = ttk.Label(info, text="Status: pending", style="SmallValue.TLabel")
            status_label.pack(anchor=tk.W, pady=(6, 0))

            path_label = ttk.Label(info, text="Path: -", wraplength=540, justify=tk.LEFT)
            path_label.pack(anchor=tk.W, pady=(2, 8))

            button_row = ttk.Frame(info, style="Card.TFrame")
            button_row.pack(anchor=tk.W)

            btn_choose = ttk.Button(button_row, text="Choose Image", command=lambda asset_key=key: self.browse_asset(asset_key))
            btn_choose.pack(side=tk.LEFT)
            self.lockable_widgets.append(btn_choose)

            btn_capture = ttk.Button(button_row, text="Capture", command=lambda asset_key=key: self.start_asset_capture(asset_key))
            btn_capture.pack(side=tk.LEFT, padx=(8, 0))
            self.lockable_widgets.append(btn_capture)

            preview = ttk.Label(row, text="No preview", anchor=tk.CENTER)
            preview.pack(side=tk.RIGHT, padx=(12, 0))

            self.asset_rows[key] = {
                "status": status_label,
                "path": path_label,
                "preview": preview,
            }

        settings_row = ttk.Frame(scroll_frame)
        settings_row.pack(fill=tk.X, pady=(12, 0))

        coords_card = ttk.LabelFrame(settings_row, text=" Combat Setup Coordinates ", style="Card.TLabelframe", padding=14)
        coords_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        ttk.Label(
            coords_card,
            text="Pick these from an in-match screen after the ultimate UI appears.",
            style="Muted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(0, 10))

        self.book_coord_label = ttk.Label(
            coords_card,
            text=f"{COORDINATE_SPECS['pos_1']['label']}: not set",
            style="SmallValue.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        )
        self.book_coord_label.pack(anchor=tk.W)
        ttk.Label(
            coords_card,
            text=COORDINATE_SPECS["pos_1"]["description"],
            style="Muted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 0))
        btn_book = ttk.Button(
            coords_card,
            text=f"Pick {COORDINATE_SPECS['pos_1']['label']}",
            command=lambda: self.pick_coord("pos_1"),
        )
        btn_book.pack(anchor=tk.W, pady=(8, 10))
        self.lockable_widgets.append(btn_book)

        self.str_coord_label = ttk.Label(
            coords_card,
            text=f"{COORDINATE_SPECS['pos_2']['label']}: not set",
            style="SmallValue.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        )
        self.str_coord_label.pack(anchor=tk.W)
        ttk.Label(
            coords_card,
            text=COORDINATE_SPECS["pos_2"]["description"],
            style="Muted.TLabel",
            wraplength=360,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(2, 0))
        btn_str = ttk.Button(
            coords_card,
            text=f"Pick {COORDINATE_SPECS['pos_2']['label']}",
            command=lambda: self.pick_coord("pos_2"),
        )
        btn_str.pack(anchor=tk.W, pady=(8, 0))
        self.lockable_widgets.append(btn_str)

        combat_card = ttk.LabelFrame(settings_row, text=" Combat Verification ", style="Card.TLabelframe", padding=14)
        combat_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 8))

        self.combat_asset_status_label = ttk.Label(
            combat_card,
            text="Combat asset: fallback heuristic",
            style="SmallValue.TLabel",
            wraplength=300,
            justify=tk.LEFT,
        )
        self.combat_asset_status_label.pack(anchor=tk.W)

        ttk.Label(
            combat_card,
            text=(
                "When the Combat Equipped Indicator is captured, the melee loop confirms the real combat HUD first. "
                "If it is missing, the bot falls back to the older slot-1 heuristic."
            ),
            style="Muted.TLabel",
            wraplength=320,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

        ttk.Label(
            combat_card,
            text="Runtime loop: confirm equip -> 5x M1 -> dynamic random move -> repeat.",
            style="Muted.TLabel",
            wraplength=320,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(10, 0))

        combat_buttons = ttk.Frame(combat_card, style="Card.TFrame")
        combat_buttons.pack(anchor=tk.W, pady=(10, 0))

        btn_choose_combat = ttk.Button(
            combat_buttons,
            text="Choose Combat Asset",
            command=lambda: self.browse_asset("combat_ready"),
        )
        btn_choose_combat.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_choose_combat)

        btn_capture_combat = ttk.Button(
            combat_buttons,
            text="Capture Combat Asset",
            command=lambda: self.start_asset_capture("combat_ready"),
        )
        btn_capture_combat.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(btn_capture_combat)

        outcome_card = ttk.LabelFrame(settings_row, text=" Result Screenshot Area ", style="Card.TLabelframe", padding=14)
        outcome_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(8, 0))

        self.area_label = ttk.Label(outcome_card, text="Area: full screen", style="SmallValue.TLabel", wraplength=360, justify=tk.LEFT)
        self.area_label.pack(anchor=tk.W)

        area_buttons = ttk.Frame(outcome_card, style="Card.TFrame")
        area_buttons.pack(anchor=tk.W, pady=(8, 0))

        btn_pick_area = ttk.Button(area_buttons, text="Pick Area", command=self.pick_area)
        btn_pick_area.pack(side=tk.LEFT)
        self.lockable_widgets.append(btn_pick_area)

        btn_clear_area = ttk.Button(area_buttons, text="Clear Area", command=self.clear_area)
        btn_clear_area.pack(side=tk.LEFT, padx=(8, 0))
        self.lockable_widgets.append(btn_clear_area)

    def _build_controls_tab(self):
        ttk.Label(self.controls_tab, text="Controls And Utilities", style="Hero.TLabel").pack(anchor=tk.W)
        ttk.Label(
            self.controls_tab,
            text="Remap keys for your layout, open important folders, and inspect runtime logs quickly.",
            style="Muted.TLabel",
        ).pack(anchor=tk.W, pady=(0, 14))

        keys_card = ttk.LabelFrame(self.controls_tab, text=" Keyboard Mapping ", style="Card.TLabelframe", padding=14)
        keys_card.pack(fill=tk.X)

        key_specs = [
            ("menu", "Menu button"),
            ("slot_1", "Slot 1"),
            ("forward", "Move forward"),
            ("backward", "Move backward"),
            ("left", "Move left"),
            ("right", "Move right"),
        ]

        for key_id, label in key_specs:
            row = ttk.Frame(keys_card, style="Card.TFrame")
            row.pack(fill=tk.X, pady=4)
            ttk.Label(row, text=label, width=20).pack(side=tk.LEFT)
            entry = ttk.Entry(row, textvariable=self.key_vars.setdefault(key_id, tk.StringVar(value="")))
            entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.lockable_widgets.append(entry)

        btn_save_keys = ttk.Button(keys_card, text="Save Hotkeys", command=lambda: self.persist_form_to_config(show_feedback=True))
        btn_save_keys.pack(anchor=tk.W, pady=(10, 0))
        self.lockable_widgets.append(btn_save_keys)

        utils_card = ttk.LabelFrame(self.controls_tab, text=" Utilities ", style="Card.TLabelframe", padding=14)
        utils_card.pack(fill=tk.X, pady=(14, 0))

        util_buttons = [
            ("Open Config", lambda: self.open_path(CONFIG_FILE)),
            ("Open Log", lambda: self.open_path(LOG_FILE)),
            ("Open Captures", lambda: self.open_path(CAPTURES_DIR)),
            ("Open Runtime Folder", lambda: self.open_path(str(RUNTIME_DIR))),
        ]

        for index, (label, command) in enumerate(util_buttons):
            button = ttk.Button(utils_card, text=label, command=command)
            button.grid(row=0, column=index, padx=(0 if index == 0 else 8, 0), pady=4, sticky="w")

        help_card = ttk.LabelFrame(self.controls_tab, text=" Operating Notes ", style="Card.TLabelframe", padding=14)
        help_card.pack(fill=tk.BOTH, expand=True, pady=(14, 0))

        help_text = (
            "1. Run the game in windowed or borderless mode.\n"
            "2. Refresh the window list and verify the title.\n"
            "3. Use Guided Capture to collect all eight tracked assets, including the combat-equip indicator.\n"
            "4. Set the Statistics Icon and Melee Upgrade Button coordinates once.\n"
            "5. Press START BOT or F1.\n\n"
            "Combat runtime flow is now: verify melee equip, spam 5 M1s, then dynamic move and repeat.\n\n"
            "The bot writes config.json, debug_log.txt, captures, and assets next to the executable when packaged."
        )
        ttk.Label(help_card, text=help_text, justify=tk.LEFT, wraplength=900).pack(anchor=tk.W)

    def _register_hotkey(self):
        try:
            self.hotkey_handler = keyboard.add_hotkey("f1", self.toggle_bot_hotkey)
            self.log("F1 hotkey registered.")
        except Exception as exc:
            self.hotkey_handler = None
            self.log(f"F1 hotkey unavailable: {exc}", is_error=True)

    def toggle_bot_hotkey(self):
        self.root.after(0, self.toggle_bot)

    def persist_form_to_config(self, show_feedback=False):
        try:
            confidence = float(self.confidence_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Confidence", "Confidence must be a number between 0.10 and 1.00.")
            return False

        try:
            scan_interval = float(self.scan_interval_var.get().strip())
        except ValueError:
            messagebox.showerror("Invalid Scan Interval", "Scan interval must be a number between 0.2 and 10.")
            return False

        try:
            movement_duration = int(float(self.movement_duration_var.get().strip()))
        except ValueError:
            messagebox.showerror("Invalid Movement Duration", "Active movement must be a number between 30 and 3600.")
            return False

        if not 0.1 <= confidence <= 1.0:
            messagebox.showerror("Invalid Confidence", "Confidence must stay between 0.10 and 1.00.")
            return False
        if not 0.2 <= scan_interval <= 10:
            messagebox.showerror("Invalid Scan Interval", "Scan interval must stay between 0.2 and 10 seconds.")
            return False
        if not 30 <= movement_duration <= 3600:
            messagebox.showerror("Invalid Movement Duration", "Active movement must stay between 30 and 3600 seconds.")
            return False

        self.config["game_window_title"] = self.window_title_var.get().strip()
        self.config["discord_webhook"] = self.webhook_var.get().strip()
        self.config["confidence"] = round(confidence, 2)
        self.config["scan_interval"] = round(scan_interval, 2)
        self.config["movement_duration"] = movement_duration
        self.config["match_mode"] = self.mode_var.get()
        self.config["window_focus_required"] = bool(self.focus_required_var.get())
        self.config["auto_focus_window"] = bool(self.auto_focus_var.get())

        new_keys = {}
        for key_id, variable in self.key_vars.items():
            value = variable.get().strip().lower()
            if value:
                new_keys[key_id] = value
        self.config["keys"] = new_keys

        save_config(self.config)
        self.config = load_config()
        self.refresh_coordinate_labels()
        self.refresh_asset_panel()
        self.refresh_runtime_summary()

        if show_feedback:
            self.log("Settings saved.")
        return True

    def refresh_window_list(self, log_result=True):
        titles = list_visible_window_titles()
        current_title = self.window_title_var.get().strip()
        if current_title and current_title not in titles:
            titles.insert(0, current_title)
        self.cmb_windows["values"] = titles
        if log_result:
            self.log(f"Window list refreshed ({len(titles)} visible windows).")
        self.refresh_runtime_summary()

    def capture_active_window_title(self):
        if self.is_running:
            messagebox.showwarning("Bot Running", "Stop the bot before changing the active game window.")
            return
        self.log("Switch to the game window now. Capturing the active window title in 3 seconds.")
        self.root.iconify()
        self.root.after(3200, self._finish_capture_active_window)

    def _finish_capture_active_window(self):
        title = get_foreground_window_title()
        self.restore_main_window()

        if title and title != self.root.title():
            self.window_title_var.set(title)
            self.persist_form_to_config(show_feedback=False)
            self.log(f"Captured active window title: {title}")
        else:
            self.log("Could not capture a game window title. Try again with the game focused.", is_error=True)

    def toggle_webhook_visibility(self):
        if self.ent_webhook.cget("show") == "*":
            self.ent_webhook.config(show="")
            self.btn_show_webhook.config(text="Hide")
        else:
            self.ent_webhook.config(show="*")
            self.btn_show_webhook.config(text="Show")

    def test_webhook(self):
        if not self.persist_form_to_config(show_feedback=False):
            return

        webhook = self.config.get("discord_webhook", "")
        if not webhook:
            messagebox.showwarning("Missing Webhook", "Enter a Discord webhook URL first.")
            return

        self.log("Sending webhook test...")

        def worker():
            status_code = send_discord(webhook, "[Zedsu] Webhook test successful.")
            if status_code and 200 <= status_code < 300:
                self.root.after(0, lambda: self.log(f"Webhook test succeeded ({status_code})."))
            else:
                self.root.after(0, lambda: self.log("Webhook test failed. Check the URL and Discord permissions.", is_error=True))

        threading.Thread(target=worker, daemon=True).start()

    def refresh_asset_panel(self, reload_config=False):
        if reload_config:
            self.config = load_config()
        records = get_asset_records(self.config)
        required_records = get_required_asset_records(self.config)
        optional_records = get_optional_asset_records(self.config)
        ready_count = 0

        for record in records:
            widgets = self.asset_rows[record["key"]]
            status_text, color = self._describe_asset_state(record["state"], required=record["required"])
            widgets["status"].config(text=f"Status: {status_text}", foreground=color)
            widgets["path"].config(text=f"Path: {record['path']}")
            self._update_preview(record["key"], record["absolute_path"])

            if record["state"] == "custom" and record["required"]:
                ready_count += 1

        optional_ready = sum(1 for record in optional_records if record["state"] == "custom")
        total_ready = ready_count + optional_ready
        total_records = max(1, len(records))
        if optional_records:
            if optional_ready == len(optional_records):
                detail = (
                    f"All {len(records)} assets are ready. Core startup checks are satisfied, and combat verification will"
                    " prefer the captured HUD indicator."
                )
            else:
                detail = (
                    "Core startup checks use the 7 main assets separately. "
                    "The 8th combat verification asset is still optional but tracked in the total count."
                )
            self.asset_summary_detail_label.config(text=detail)
            self.combat_asset_status_label.config(
                text=f"Combat asset: {optional_ready} / {len(optional_records)} ready"
            )
        self.asset_summary_label.config(text=f"{total_ready} / {len(records)} assets ready")
        self.assets_progress.config(value=(total_ready / total_records) * 100)
        self.assets_value.config(text=f"{total_ready} / {len(records)} ready")
        self.refresh_runtime_summary()

    def _describe_asset_state(self, state, required=True):
        if state == "custom":
            return "Ready", "#15803d"
        if state == "placeholder":
            if required:
                return "Placeholder - capture needed", "#b45309"
            return "Recommended - capture for melee confirmation", "#b45309"
        return "Missing", "#b91c1c"

    def _update_preview(self, key, absolute_path):
        widget = self.asset_rows[key]["preview"]
        if not absolute_path or not os.path.exists(absolute_path):
            widget.config(text="Missing", image="")
            widget.image = None
            return

        try:
            with Image.open(absolute_path) as raw_image:
                preview = raw_image.copy()
            preview.thumbnail((140, 78))
            photo = ImageTk.PhotoImage(preview)
            widget.config(image=photo, text="")
            widget.image = photo
            self.asset_previews[key] = photo
        except Exception:
            widget.config(text="Preview error", image="")
            widget.image = None

    def browse_asset(self, key):
        if self.is_running:
            return

        selected = filedialog.askopenfilename(
            title=f"Choose image for {IMAGE_SPECS[key]['label']}",
            initialdir=ASSETS_DIR,
            filetypes=(
                ("Image files", "*.png;*.jpg;*.jpeg;*.bmp;*.webp"),
                ("PNG image", "*.png"),
                ("All files", "*.*"),
            ),
        )
        if not selected:
            return

        self.import_single_asset(key, selected)

    def import_single_asset(self, key, source_path):
        destination = resolve_path(os.path.join("src", "assets", IMAGE_SPECS[key]["filename"]))
        os.makedirs(os.path.dirname(destination), exist_ok=True)

        try:
            with Image.open(source_path) as image:
                converted = image.convert("RGBA") if image.mode not in ("RGB", "RGBA") else image.copy()
                save_image = converted.convert("RGB") if converted.mode == "RGBA" else converted
                save_image.save(destination, format="PNG")
        except Exception:
            try:
                shutil.copy2(source_path, destination)
            except Exception as exc:
                self.log(f"Could not import asset for {IMAGE_SPECS[key]['label']}: {exc}", is_error=True)
                return False

        set_asset_path(self.config, key, destination)
        save_config(self.config)
        self.config = load_config()
        self.refresh_asset_panel()
        self.log(f"Imported asset: {IMAGE_SPECS[key]['label']}")
        return True

    def import_asset_folder(self):
        if self.is_running:
            return

        folder = filedialog.askdirectory(title="Choose a folder containing your asset images")
        if not folder:
            return

        imported = []
        missing = []

        for key in IMAGE_ORDER:
            filename = IMAGE_SPECS[key]["filename"]
            source_path = os.path.join(folder, filename)
            if os.path.exists(source_path):
                if self.import_single_asset(key, source_path):
                    imported.append(filename)
            else:
                missing.append(filename)

        self.refresh_asset_panel(reload_config=True)

        if imported:
            self.log(f"Imported {len(imported)} asset file(s) from folder.")
        if missing:
            self.log(f"Missing in selected folder: {', '.join(missing)}", is_error=True)

    def test_asset_detection(self):
        if not self.persist_form_to_config(show_feedback=False):
            return

        title = self.config.get("game_window_title", "").strip()
        match = find_window_by_title(title)
        if not match:
            self.log("Cannot test detection because the game window was not found.", is_error=True)
            return

        self.log(f"Testing asset detection in window: {match[1]}")

        def worker():
            if self.config.get("auto_focus_window", True):
                bring_window_to_foreground(title)
                time.sleep(0.6)

            region = get_window_rect(title)
            foreground = get_foreground_window_title() or "[unknown]"
            screenshot_path = None

            try:
                if region:
                    left, top, right, bottom = region
                    image = pyautogui.screenshot(region=(left, top, right - left, bottom - top))
                    screenshot_path = os.path.join(CAPTURES_DIR, "asset_test_window.png")
                    image.save(screenshot_path)
            except Exception as exc:
                self.root.after(0, lambda: self.log(f"Could not save test screenshot: {exc}", is_error=True))

            findings = []
            for key in IMAGE_ORDER:
                result = locate_image(key, self.config, region=region)
                findings.append((key, result))

            def finish():
                self.log(f"Foreground during test: {foreground}")
                self.log(f"Window region during test: {region}")
                if screenshot_path:
                    self.log(f"Saved test screenshot: {screenshot_path}")

                found_any = False
                for key, result in findings:
                    label = IMAGE_SPECS[key]["label"]
                    if result:
                        found_any = True
                        self.log(f"[DETECTED] {label} at {result}")
                    else:
                        self.log(f"[MISS] {label}")

                if not found_any:
                    self.log(
                        "No assets matched in the current Roblox window. "
                        "This usually means the window is covered, the lobby state is different, or the imported crops are from another scale.",
                        is_error=True,
                    )

            self.root.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()

    def capture_all_assets(self):
        if self.is_running:
            messagebox.showwarning("Bot Running", "Stop the bot before starting guided capture.")
            return

        if not self.persist_form_to_config(show_feedback=False):
            return

        self.capture_queue = list(IMAGE_ORDER)
        self.notebook.select(self.assets_tab)
        messagebox.showinfo(
            "Guided Capture",
            "Open the game window and keep the relevant UI visible.\n\nThe app will guide you through every required asset first, then the optional combat verification asset.",
        )
        self.log("Guided capture started.")
        self._capture_next_asset()

    def _capture_next_asset(self):
        if not self.capture_queue:
            self.log("Guided capture completed.")
            self.refresh_asset_panel()
            return

        next_key = self.capture_queue.pop(0)
        if IMAGE_SPECS[next_key].get("required", True):
            self.log(f"Capture step: {IMAGE_SPECS[next_key]['label']}")
        else:
            self.log(f"Capture step: {IMAGE_SPECS[next_key]['label']} (recommended combat verification asset)")
        self.start_asset_capture(next_key, queued=True)

    def start_asset_capture(self, key, queued=False):
        if self.is_running:
            return

        def launch_tool(screenshot):
            ScreenCaptureTool(
                self.root,
                screenshot,
                key,
                ASSETS_DIR,
                on_complete=lambda path: self._complete_asset_capture(key, path, queued),
                on_cancel=lambda: self._cancel_asset_capture(queued),
                save_name=IMAGE_SPECS[key]["filename"],
                title=IMAGE_SPECS[key]["label"],
            )

        self.log(f"Prepare the screen for {IMAGE_SPECS[key]['label']}. Capture opens in a moment.")
        self._begin_screen_tool(launch_tool)

    def _complete_asset_capture(self, key, path, queued):
        set_asset_path(self.config, key, path)
        save_config(self.config)
        self.config = load_config()
        self.restore_main_window()
        self.refresh_asset_panel()
        self.log(f"Captured asset: {IMAGE_SPECS[key]['label']}")
        if queued:
            self.root.after(450, self._capture_next_asset)

    def _cancel_asset_capture(self, queued):
        self.restore_main_window()
        if queued:
            self.capture_queue = []
            self.log("Guided capture cancelled.", is_error=True)

    def pick_coord(self, key):
        if self.is_running:
            return

        label = COORDINATE_SPECS.get(key, {}).get("label", key)
        self.log(f"Pick coordinate for {label}.")

        def launch_tool(screenshot):
            CoordinatePicker(
                self.root,
                screenshot,
                on_complete=lambda result: self._complete_coord_pick(key, result),
                on_cancel=self.restore_main_window,
            )

        self._begin_screen_tool(launch_tool)

    def _complete_coord_pick(self, key, result):
        self.config[key] = result
        save_config(self.config)
        self.config = load_config()
        self.restore_main_window()
        self.refresh_coordinate_labels()
        self.refresh_runtime_summary()
        label = COORDINATE_SPECS.get(key, {}).get("label", key)
        self.log(f"Coordinate saved for {label}: {result}")

    def pick_area(self):
        if self.is_running:
            return

        self.log("Pick the outcome screenshot area.")

        def launch_tool(screenshot):
            AreaPicker(
                self.root,
                screenshot,
                on_complete=self._complete_area_pick,
                on_cancel=self.restore_main_window,
            )

        self._begin_screen_tool(launch_tool)

    def _complete_area_pick(self, result):
        self.config["outcome_area"] = result
        save_config(self.config)
        self.config = load_config()
        self.restore_main_window()
        self.refresh_coordinate_labels()
        self.log(f"Result screenshot area saved: {result}")

    def clear_area(self):
        self.config["outcome_area"] = None
        save_config(self.config)
        self.config = load_config()
        self.refresh_coordinate_labels()
        self.log("Result screenshot area cleared.")

    def _begin_screen_tool(self, launch_tool, delay_ms=1300):
        self.root.iconify()

        def take_screenshot():
            try:
                screenshot = pyautogui.screenshot()
            except Exception as exc:
                self.restore_main_window()
                self.log(f"Screen capture failed: {exc}", is_error=True)
                return
            launch_tool(screenshot)

        self.root.after(delay_ms, take_screenshot)

    def restore_main_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.after(50, self.root.focus_force)

    def _pointer_inside_assets_canvas(self):
        if not self.assets_canvas or not self.assets_canvas.winfo_exists():
            return False

        if self.notebook.select() != str(self.assets_tab):
            return False

        pointer_x = self.root.winfo_pointerx()
        pointer_y = self.root.winfo_pointery()
        left = self.assets_canvas.winfo_rootx()
        top = self.assets_canvas.winfo_rooty()
        right = left + self.assets_canvas.winfo_width()
        bottom = top + self.assets_canvas.winfo_height()
        return left <= pointer_x <= right and top <= pointer_y <= bottom

    def _on_assets_mousewheel(self, event):
        if not self._pointer_inside_assets_canvas():
            return

        if event.delta == 0:
            return

        units = int(-event.delta / 120)
        if units == 0:
            units = -1 if event.delta > 0 else 1
        self.assets_canvas.yview_scroll(units, "units")

    def _on_assets_mousewheel_linux_up(self, _event):
        if self._pointer_inside_assets_canvas():
            self.assets_canvas.yview_scroll(-1, "units")

    def _on_assets_mousewheel_linux_down(self, _event):
        if self._pointer_inside_assets_canvas():
            self.assets_canvas.yview_scroll(1, "units")

    def hide_for_runtime(self):
        if self.was_hidden_for_runtime:
            return
        self.was_hidden_for_runtime = True
        self.root.iconify()

    def restore_after_runtime(self):
        if not self.was_hidden_for_runtime:
            return
        self.was_hidden_for_runtime = False
        self.restore_main_window()

    def refresh_coordinate_labels(self):
        pos1 = self.config.get("pos_1")
        pos2 = self.config.get("pos_2")
        area = self.config.get("outcome_area")

        self.book_coord_label.config(
            text=f"{COORDINATE_SPECS['pos_1']['label']}: {pos1 if is_coordinate_ready(pos1) else 'not set'}"
        )
        self.str_coord_label.config(
            text=f"{COORDINATE_SPECS['pos_2']['label']}: {pos2 if is_coordinate_ready(pos2) else 'not set'}"
        )
        self.area_label.config(text=f"Area: {area if area else 'full screen'}")

    def refresh_runtime_summary_loop(self):
        if self.root.winfo_exists():
            self.refresh_runtime_summary()
            self.root.after(1200, self.refresh_runtime_summary_loop)

    def refresh_runtime_summary(self):
        records = get_asset_records(self.config)
        required_records = get_required_asset_records(self.config)
        optional_records = get_optional_asset_records(self.config)
        ready_count = sum(1 for record in required_records if record["state"] == "custom")
        window_title = self.window_title_var.get().strip() or self.config.get("game_window_title", "").strip()
        window_match = find_window_by_title(window_title) if window_title else None

        issues = get_required_setup_issues(self.config)
        warnings = get_optional_setup_warnings(self.config)

        if self.config.get("window_focus_required", True):
            if window_match:
                self.window_summary_label.config(text=f"Window: ready ({window_match[1]})")
            else:
                self.window_summary_label.config(text="Window: not found. Open the game or update the title.")
        else:
            self.window_summary_label.config(text="Window: focus requirement disabled")

        readiness_checks = 4
        readiness_done = 0
        if window_match or not self.config.get("window_focus_required", True):
            readiness_done += 1
        if ready_count == len(required_records):
            readiness_done += 1
        if is_coordinate_ready(self.config.get("pos_1")):
            readiness_done += 1
        if is_coordinate_ready(self.config.get("pos_2")):
            readiness_done += 1

        if not issues and (window_match or not self.config.get("window_focus_required", True)):
            self.setup_summary_label.config(text="Setup status: ready to run")
        else:
            pending = len(issues) + (1 if self.config.get("window_focus_required", True) and not window_match else 0)
            self.setup_summary_label.config(text=f"Setup status: {pending} item(s) need attention")

        checklist_lines = []
        if self.config.get("window_focus_required", True) and not window_match:
            checklist_lines.append("1. Open the game and verify the window title.")

        for index, issue in enumerate(issues, start=len(checklist_lines) + 1):
            checklist_lines.append(f"{index}. {issue}")

        if not checklist_lines:
            checklist_lines.append("1. Setup complete. You can start the bot now.")
            if warnings:
                checklist_lines.append("2. Optional: review the warnings below for extra polish.")

        self.checklist_label.config(text="\n".join(checklist_lines))
        optional_ready = sum(1 for record in optional_records if record["state"] == "custom")
        total_ready = ready_count + optional_ready
        self.assets_value.config(text=f"{total_ready} / {len(records)} ready")
        self.readiness_meter_label.config(text=f"Readiness: {readiness_done} / {readiness_checks} checkpoints")
        self.readiness_progress.config(value=(readiness_done / readiness_checks) * 100)
        if optional_records and optional_ready == len(optional_records):
            combat_summary = "Combat verification: using the captured combat asset before every 5-hit burst."
        else:
            combat_summary = "Combat verification: using fallback slot heuristics until the combat asset is captured."
        self.combat_summary_label.config(text=combat_summary)

        mode_text = "QUICK LEAVE" if self.config.get("match_mode") == "quick" else "FULL MATCH"
        self.runtime_mode_label.config(
            text=f"Mode: {mode_text} | Flow: equip melee -> 5x M1 -> dynamic move -> repeat"
        )

    def update_status(self, text, color):
        self.root.after(0, lambda: self.status_label.config(text=text, foreground=color))

    def update_match_count(self):
        self.root.after(0, lambda: self.match_value.config(text=str(self.match_count)))

    def update_timer_ui(self, time_str):
        self.root.after(0, lambda: self.timer_value.config(text=time_str))

    def update_timer(self):
        if self.is_running and self.start_time:
            elapsed = int(time.time() - self.start_time)
            time_str = f"{elapsed // 3600:02}:{(elapsed % 3600) // 60:02}:{elapsed % 60:02}"
            self.timer_value.config(text=time_str)
            self.root.after(1000, self.update_timer)
        elif not self.is_running:
            self.timer_value.config(text="00:00:00")

    def toggle_bot(self):
        if self.is_running:
            self.stop_bot()
            return

        if not self.persist_form_to_config(show_feedback=False):
            return

        blockers = list(get_required_setup_issues(self.config))
        window_title = self.config.get("game_window_title", "").strip()
        if self.config.get("window_focus_required", True) and not find_window_by_title(window_title):
            blockers.append(f"Open the game window that matches: {window_title or '[empty title]'}")

        if blockers:
            self.notebook.select(self.setup_tab if "window" in blockers[0].lower() else self.assets_tab)
            self.log("Cannot start until setup is complete.", is_error=True)
            messagebox.showwarning("Setup Incomplete", "\n".join(f"- {item}" for item in blockers))
            return

        self.is_running = True
        self.engine.start()
        self.start_time = time.time()
        self.set_running_state(True)
        self.btn_toggle.config(text="STOP BOT")
        self.update_status("STARTING", "#2563eb")
        self.update_timer()
        if not is_asset_custom(self.config, "combat_ready"):
            self.log(
                "Combat Equipped Indicator is not captured yet. Starting with fallback melee-slot heuristics.",
                is_error=True,
            )
        self.log("Bot started.")
        self.root.after(200, self.hide_for_runtime)
        threading.Thread(target=self.engine.bot_loop, daemon=True).start()

    def stop_bot(self):
        self.engine.stop()
        self.is_running = False
        self.set_running_state(False)
        self.btn_toggle.config(text="START BOT")
        self.update_status("STOPPING", "#b45309")
        self.log("Stopping bot...")
        self.restore_after_runtime()
        self.root.after(500, lambda: self.update_status("IDLE", "#475569"))

    def set_running_state(self, running):
        state = "disabled" if running else "normal"
        for widget in self.lockable_widgets:
            try:
                widget.configure(state=state)
            except tk.TclError:
                continue

    def log(self, msg, is_error=False):
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        def update_console():
            color = "#fca5a5" if is_error else "#e2e8f0"
            self.console.configure(state="normal")
            start_index = self.console.index(tk.END)
            self.console.insert(tk.END, f"[{timestamp}] {msg}\n")
            end_index = self.console.index(tk.END)
            tag_name = f"log_{time.time_ns()}"
            self.console.tag_add(tag_name, start_index, end_index)
            self.console.tag_config(tag_name, foreground=color)
            self.console.see(tk.END)
            self.console.configure(state="disabled")
            self.last_action_label.config(text=msg)

        self.root.after(0, update_console)

        try:
            with open(LOG_FILE, "a", encoding="utf-8") as file:
                prefix = "[ERROR] " if is_error else ""
                file.write(f"[{full_timestamp}] {prefix}{msg}\n")
        except Exception:
            pass

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

        messagebox.showwarning("Path Missing", f"Could not find:\n{absolute_path}")

    def on_close(self):
        if self.is_running:
            self.stop_bot()

        if self.hotkey_handler is not None:
            try:
                keyboard.remove_hotkey(self.hotkey_handler)
            except Exception:
                pass

        self.root.destroy()
