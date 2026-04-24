"""
Position Picker Overlay — Phase 12.3

Tkinter click-to-capture overlay for picking a single screen position.
Runs in a dedicated non-daemon thread so the HTTP handler can block and wait.
Single-shot: one click closes the overlay immediately.
"""

from __future__ import annotations

import threading
from typing import Optional

try:
    import tkinter as tk
except ImportError:
    tk = None  # type: ignore

from src.utils.windows import get_window_rect


class PositionPickerOverlay:
    """
    Single-shot click-to-capture overlay for picking a screen position.

    Usage (from a dedicated thread):
        overlay = PositionPickerOverlay(window_title="Roblox", position_name="melee")
        overlay.run()          # blocks until overlay closes
        result = overlay.get_result()  # returns result dict or None on timeout

    Result dict shapes:
        {'action': 'confirm', 'x': 0.5, 'y': 0.3, 'name': 'melee'}
        {'action': 'cancel'}
        {'action': 'error', 'message': 'Window not found'}
        {'action': 'error', 'message': 'Click outside game window'}
        None  (timeout)
    """

    def __init__(self, window_title: str, position_name: str) -> None:
        if tk is None:
            raise RuntimeError("tkinter is not available — cannot create overlay")

        self.window_title = window_title
        self.position_name = position_name

        self._win_left: int = 0
        self._win_top: int = 0
        self._win_width: int = 0
        self._win_height: int = 0

        self._tk_root: Optional[tk.Tk] = None
        self._overlay: Optional[tk.Toplevel] = None

        self.result_data: Optional[dict] = None
        self.result_event = threading.Event()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(self) -> None:
        """
        Dedicated thread entry point. Creates Tkinter root + overlay in
        THIS thread. Blocks until root.quit() is called.

        If get_window_rect() returns None, sets error result and exits cleanly.
        If result_event was already set (e.g. emergency_stop before Tk root exists),
        exits immediately without creating any Tk window.
        """
        # Race guard: if request_cancel() was called before we got here,
        # exit without creating any Tk window.
        if self.result_event.is_set():
            return

        root = tk.Tk()
        root.withdraw()
        self._tk_root = root

        # Race guard: emergency_stop may have fired while Tk was initializing
        if self.result_event.is_set():
            self._close()
            return

        rect = get_window_rect(self.window_title)

        # Race guard: check again after window rect lookup
        if self.result_event.is_set():
            self._close()
            return

        if rect is None:
            self.result_data = {"action": "error", "message": "Window not found"}
            self.result_event.set()
            try:
                root.quit()
                root.destroy()
            except Exception:
                pass
            return

        self._win_left, self._win_top, self._win_right, self._win_bottom = rect
        self._win_width = self._win_right - self._win_left
        self._win_height = self._win_bottom - self._win_top

        overlay = tk.Toplevel(root)
        self._overlay = overlay
        overlay.geometry(f"{self._win_width}x{self._win_height}+{self._win_left}+{self._win_top}")
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.25)
        overlay.configure(bg="#1a1a2e")

        canvas = tk.Canvas(
            overlay,
            bg="#1a1a2e",
            cursor="crosshair",
            width=self._win_width,
            height=self._win_height,
            highlightthickness=0,
        )
        canvas.pack()

        canvas.bind("<Button-1>", self._on_click)
        overlay.bind("<Escape>", lambda _: self._cancel())
        root.bind("<Escape>", lambda _: self._cancel())
        overlay.bind("<Destroy>", lambda _: self._on_destroy())

        overlay.focus_force()
        canvas.focus_set()

        root.mainloop()

    def get_result(self, timeout: Optional[float] = None) -> Optional[dict]:
        """
        Blocking accessor. Waits on result_event until set or timeout.
        Returns self.result_data if set, else None on timeout.
        """
        self.result_event.wait(timeout=timeout)
        return self.result_data

    # ------------------------------------------------------------------
    # Click handler
    # ------------------------------------------------------------------

    def _on_click(self, event: tk.Event) -> None:
        """
        Single-shot click handler. Validates bounds, normalizes, and confirms.
        Out-of-bounds clicks are explicitly rejected with error — NOT silently clamped.
        """
        if self.result_event.is_set():
            return

        if (
            event.x < 0 or event.x > self._win_width
            or event.y < 0 or event.y > self._win_height
        ):
            self.result_data = {"action": "error", "message": "Click outside game window"}
            self.result_event.set()
            self._close()
            return

        norm_x = max(0.0, min(1.0, event.x / self._win_width))
        norm_y = max(0.0, min(1.0, event.y / self._win_height))

        self.result_data = {
            "action": "confirm",
            "x": norm_x,
            "y": norm_y,
            "name": self.position_name,
        }
        self.result_event.set()
        self._close()

    # ------------------------------------------------------------------
    # Cancel / Close
    # ------------------------------------------------------------------

    def _cancel(self) -> None:
        """Esc / destroy handler — abort without mutation."""
        if self.result_event.is_set():
            return

        self.result_data = {"action": "cancel"}
        self.result_event.set()
        self._close()

    def request_cancel(self, message: str = "Position selection timed out") -> None:
        """
        Thread-safe cancellation from the HTTP handler thread.
        Uses root.after(0, ...) to schedule _close() on the Tk thread.
        """
        if self.result_event.is_set():
            return
        self.result_data = {"action": "error", "message": message}
        self.result_event.set()
        if self._tk_root is not None:
            self._tk_root.after(0, self._close)

    def _close(self) -> None:
        """Destroy Toplevel and root cleanly. Called from the Tk thread."""
        try:
            if self._overlay is not None:
                self._overlay.destroy()
                self._overlay = None
        except Exception:
            pass
        try:
            if self._tk_root is not None:
                self._tk_root.quit()
                self._tk_root.destroy()
                self._tk_root = None
        except Exception:
            pass

    def _on_destroy(self) -> None:
        """
        Toplevel Destroy event. Cancels only if result not yet set.
        This prevents Destroy from overwriting an already-confirmed result.
        """
        if not self.result_event.is_set():
            self._cancel()
