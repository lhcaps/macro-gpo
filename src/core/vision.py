import os
import tkinter as tk

import pyautogui
from PIL import Image, ImageEnhance, ImageTk

from src.core.controller import human_click
from src.utils.config import resolve_path


def _normalize_region(region):
    if not region or len(region) != 4:
        return None

    left, top, right, bottom = [int(value) for value in region]
    width = right - left
    height = bottom - top
    if width <= 0 or height <= 0:
        return None
    return left, top, width, height


def locate_image(img_name, config, confidence=None, region=None):
    path = resolve_path(config.get("images", {}).get(img_name))
    if not path or not os.path.exists(path):
        return None

    conf = confidence if confidence is not None else config.get("confidence", 0.8)
    normalized_region = _normalize_region(region)
    attempts = (
        {"grayscale": True, "confidence": conf, "region": normalized_region},
        {"grayscale": False, "confidence": max(0.55, conf - 0.05), "region": normalized_region},
        {"grayscale": False, "confidence": max(0.5, conf - 0.15), "region": normalized_region},
    )

    for attempt in attempts:
        try:
            params = {key: value for key, value in attempt.items() if value is not None}
            result = pyautogui.locateOnScreen(path, **params)
            if result:
                return result
        except Exception:
            continue
    return None


def is_image_visible(img_name, config, confidence=None, region=None):
    return locate_image(img_name, config, confidence=confidence, region=region) is not None


def find_and_click(img_name, config, is_running_check, log_func, clicks=1, region=None, confidence=None):
    if not is_running_check():
        return False

    pos = locate_image(img_name, config, confidence=confidence, region=region)
    if not pos:
        return False

    center = pyautogui.center(pos)
    safe_offset = min(10, max(2, min(pos.width, pos.height) // 4))
    log_func(f"Detected {img_name}.")

    if not human_click(center.x, center.y, is_running_check, move=True, offset=safe_offset):
        return False

    for _ in range(max(0, clicks - 1)):
        if not human_click(center.x, center.y, is_running_check, move=False):
            return False
    return True


class ScreenCaptureTool:
    def __init__(
        self,
        parent,
        screenshot,
        key,
        assets_dir,
        on_complete,
        on_cancel=None,
        save_name=None,
        title=None,
    ):
        self.parent = parent
        self.screenshot = screenshot
        self.key = key
        self.assets_dir = assets_dir
        self.on_complete = on_complete
        self.on_cancel = on_cancel
        self.save_name = save_name or f"{key}.png"
        self.title = title or key.replace("_", " ").title()
        self.result_path = None

        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.configure(bg="black")
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

        enhancer = ImageEnhance.Brightness(self.screenshot)
        self.dimmed_screenshot = enhancer.enhance(0.35)
        self.tk_dimmed = ImageTk.PhotoImage(self.dimmed_screenshot)

        self.canvas = tk.Canvas(self.top, bg="black", highlightthickness=0, cursor="crosshair")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_dimmed)

        self.mag_size = 180
        self.mag_zoom = 4
        self.mag_canvas = tk.Canvas(
            self.top,
            width=self.mag_size,
            height=self.mag_size,
            highlightthickness=2,
            highlightbackground="#38bdf8",
            bg="black",
        )

        self.start_x = None
        self.start_y = None
        self.rect = None
        self.spotlight_item = None
        self.photo = None
        self.bright_tk = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.canvas.bind("<Motion>", self.update_magnifier)
        self.top.bind("<Escape>", lambda _: self.cancel())

        self.canvas.create_text(
            24,
            24,
            text=f"Capturing {self.title} | Drag to save | ESC to cancel",
            anchor=tk.NW,
            fill="white",
            font=("Segoe UI", 16, "bold"),
        )
        self.canvas.create_text(
            24,
            52,
            text="Tip: zoom into the exact button, avoid shadows and background clutter.",
            anchor=tk.NW,
            fill="#bfdbfe",
            font=("Segoe UI", 10),
        )

    def cancel(self):
        if callable(self.on_cancel):
            self.on_cancel()
        self.top.destroy()

    def update_magnifier(self, event):
        x, y = event.x, event.y
        mag_x = x + 30 if x + self.mag_size + 60 < self.top.winfo_screenwidth() else x - self.mag_size - 30
        mag_y = y + 30 if y + self.mag_size + 60 < self.top.winfo_screenheight() else y - self.mag_size - 30
        self.mag_canvas.place(x=mag_x, y=mag_y)

        box_size = self.mag_size // self.mag_zoom
        left = max(0, x - box_size // 2)
        top = max(0, y - box_size // 2)
        right = min(self.screenshot.width, left + box_size)
        bottom = min(self.screenshot.height, top + box_size)

        part = self.screenshot.crop((left, top, right, bottom))
        part = part.resize((self.mag_size, self.mag_size), Image.Resampling.NEAREST)

        self.photo = ImageTk.PhotoImage(part)
        self.mag_canvas.delete("all")
        self.mag_canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
        self.mag_canvas.create_line(self.mag_size // 2, 0, self.mag_size // 2, self.mag_size, fill="red")
        self.mag_canvas.create_line(0, self.mag_size // 2, self.mag_size, self.mag_size // 2, fill="red")

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        if self.spotlight_item:
            self.canvas.delete(self.spotlight_item)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline="#38bdf8", width=2)

    def on_drag(self, event):
        x, y = event.x, event.y
        self.canvas.coords(self.rect, self.start_x, self.start_y, x, y)

        left = min(self.start_x, x)
        top = min(self.start_y, y)
        right = max(self.start_x, x)
        bottom = max(self.start_y, y)

        if right - left > 2 and bottom - top > 2:
            bright_part = self.screenshot.crop((left, top, right, bottom))
            self.bright_tk = ImageTk.PhotoImage(bright_part)
            if self.spotlight_item:
                self.canvas.delete(self.spotlight_item)
            self.spotlight_item = self.canvas.create_image(left, top, anchor=tk.NW, image=self.bright_tk)
            self.canvas.tag_raise(self.rect)

        self.update_magnifier(event)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)

        if right - left < 3 or bottom - top < 3:
            return

        cropped = self.screenshot.crop((left, top, right, bottom))
        save_path = os.path.join(self.assets_dir, self.save_name)
        os.makedirs(self.assets_dir, exist_ok=True)
        cropped.save(save_path)

        self.result_path = save_path
        self.on_complete(self.result_path)
        self.top.destroy()
