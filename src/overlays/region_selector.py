"""
Region Selector Overlay — Phase 12.2

Tkinter drag-to-select overlay for visually picking a screen region.
Runs in a dedicated non-daemon thread so the HTTP handler can block and wait.

Key constraint: Tkinter event.x/event.y are canvas-local coordinates
(origin at top-left of the overlay window). Normalize directly as
local_x / win_width — do NOT use absolute screen coordinates.
"""

from __future__ import annotations

import threading
from typing import Optional

try:
    import tkinter as tk
except ImportError:
    tk = None  # type: ignore

from src.utils.windows import get_window_rect


class RegionSelectorOverlay:
    """
    Drag-to-select overlay for defining a screen region.

    Usage (from a dedicated thread):
        overlay = RegionSelectorOverlay(window_title="Roblox", region_name="combat_scan")
        overlay.run()          # blocks until overlay closes
        result = overlay.get_result()  # returns result dict or None on timeout

    Result dict shapes:
        {'action': 'confirm', 'area': [nx1, ny1, nx2, ny2], 'name': region_name}
        {'action': 'cancel'}
        {'action': 'error', 'message': 'Window not found'}
        None  (timeout)
    """

    def __init__(self, window_title: str, region_name: str = "combat_scan") -> None:
        if tk is None:
            raise RuntimeError("tkinter is not available — cannot create overlay")

        self.window_title = window_title
        self.region_name = region_name

        # Set by run()
        self._win_left: int = 0
        self._win_top: int = 0
        self._win_width: int = 0
        self._win_height: int = 0

        # Drag state
        self._dragging: bool = False
        self._started: bool = False
        self._sx: int = 0  # start x (local canvas coords)
        self._sy: int = 0  # start y (local canvas coords)
        self._ex: int = 0  # end x (local canvas coords)
        self._ey: int = 0  # end y (local canvas coords)

        # Canvas item IDs for live redraw
        self._rect_id: int | None = None
        self._label_bg_id: int | None = None
        self._label_text_id: int | None = None

        # Tkinter instances (set in run())
        self._tk_root: Optional[tk.Tk] = None
        self._overlay: Optional[tk.Toplevel] = None

        # Result
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
        root.withdraw()  # hide the helper root window
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
            # Clean up the Tk root that was created before rect check
            try:
                root.quit()
                root.destroy()
            except Exception:
                pass
            return

        self._win_left, self._win_top, self._win_right, self._win_bottom = rect
        self._win_width = self._win_right - self._win_left
        self._win_height = self._win_bottom - self._win_top

        # Overlay window positioned exactly over the game window
        overlay = tk.Toplevel(root)
        self._overlay = overlay
        overlay.geometry(f"{self._win_width}x{self._win_height}+{self._win_left}+{self._win_top}")
        overlay.overrideredirect(True)
        overlay.attributes("-topmost", True)
        overlay.attributes("-alpha", 0.25)  # transparent so game is visible through overlay
        overlay.configure(bg="#1a1a2e")

        # Canvas covers full overlay area
        canvas = tk.Canvas(
            overlay,
            bg="#1a1a2e",
            cursor="crosshair",
            width=self._win_width,
            height=self._win_height,
            highlightthickness=0,
        )
        canvas.pack()

        # Mouse bindings for drag
        canvas.bind("<Button-1>", self._on_press)
        canvas.bind("<B1-Motion>", self._on_drag)
        canvas.bind("<ButtonRelease-1>", self._on_release)

        # Keyboard bindings — bind on overlay and root to ensure focus works
        overlay.bind("<Return>", lambda _: self._confirm())
        overlay.bind("<Escape>", lambda _: self._cancel())
        root.bind("<Return>", lambda _: self._confirm())
        root.bind("<Escape>", lambda _: self._cancel())

        # Destroy binding — cancel if result not yet set (guards against overwrite)
        overlay.bind("<Destroy>", lambda _: self._on_destroy())

        # Force keyboard focus so Enter/Esc work immediately
        overlay.focus_force()
        canvas.focus_set()

        root.mainloop()

    def get_result(self, timeout: Optional[float] = None) -> Optional[dict]:
        """
        Blocking accessor. Waits on result_event until set or timeout.

        Returns:
            self.result_data if set, else None on timeout.
        """
        self.result_event.wait(timeout=timeout)
        return self.result_data

    # ------------------------------------------------------------------
    # Mouse handlers
    # ------------------------------------------------------------------

    def _on_press(self, event: tk.Event) -> None:
        """Record start of drag in local canvas coordinates."""
        self._sx = max(0, min(event.x, self._win_width))
        self._sy = max(0, min(event.y, self._win_height))
        self._ex = self._sx
        self._ey = self._sy
        self._dragging = True
        self._started = True

    def _on_drag(self, event: tk.Event) -> None:
        """Redraw live rectangle during drag."""
        if not self._dragging:
            return

        ex = max(0, min(event.x, self._win_width))
        ey = max(0, min(event.y, self._win_height))
        self._ex = ex
        self._ey = ey

        # Get canvas from event widget
        canvas = event.widget  # type: tk.Canvas

        # Delete previous items
        if self._rect_id is not None:
            canvas.delete(self._rect_id)
            self._rect_id = None
        if self._label_bg_id is not None:
            canvas.delete(self._label_bg_id)
            self._label_bg_id = None
        if self._label_text_id is not None:
            canvas.delete(self._label_text_id)
            self._label_text_id = None

        # Draw new rectangle (semi-transparent stipple fill)
        self._rect_id = canvas.create_rectangle(
            self._sx, self._sy, self._ex, self._ey,
            outline="#FF9500",
            width=2,
            fill="",
            stipple="gray50",
        )

        # Draw pixel dimension label
        w_px = abs(self._ex - self._sx)
        h_px = abs(self._ey - self._sy)
        label_text = f"{w_px} x {h_px}px"

        # Label background rect
        lx1 = min(self._sx, self._ex)
        ly1 = max(self._sy, self._ey)
        lx2 = lx1 + 80
        ly2 = ly1 + 18
        self._label_bg_id = canvas.create_rectangle(
            lx1, ly1, lx2, ly2,
            fill="#1A1A1A",
            outline="",
        )
        self._label_text_id = canvas.create_text(
            lx1 + 4, ly1 + 9,
            text=label_text,
            font=("Segoe UI", 10),
            fill="white",
            anchor="w",
        )

    def _on_release(self, event: tk.Event) -> None:
        """Finalize drag on mouse release."""
        self._dragging = False
        self._ex = max(0, min(event.x, self._win_width))
        self._ey = max(0, min(event.y, self._win_height))

    # ------------------------------------------------------------------
    # Confirm / Cancel
    # ------------------------------------------------------------------

    def _confirm(self) -> None:
        """Enter key handler — commit region if minimum size met."""
        # Guard: ignore if result already set
        if self.result_event.is_set():
            return

        # Ignore Enter without a drag
        if not self._started:
            return

        # 5x5 minimum threshold — discard accidental clicks
        w_px = abs(self._ex - self._sx)
        h_px = abs(self._ey - self._sy)
        if w_px < 5 or h_px < 5:
            return

        # Normalize using LOCAL canvas coords — use min/max so reverse drag works
        # min/max ensures x1<x2 and y1<y2 regardless of drag direction
        x1 = min(self._sx, self._ex)
        y1 = min(self._sy, self._ey)
        x2 = max(self._sx, self._ex)
        y2 = max(self._sy, self._ey)
        norm_x1 = max(0.0, min(x1 / self._win_width, 1.0))
        norm_y1 = max(0.0, min(y1 / self._win_height, 1.0))
        norm_x2 = max(0.0, min(x2 / self._win_width, 1.0))
        norm_y2 = max(0.0, min(y2 / self._win_height, 1.0))

        self.result_data = {
            "action": "confirm",
            "area": [norm_x1, norm_y1, norm_x2, norm_y2],
            "name": self.region_name,
        }
        self.result_event.set()
        self._close()

    def _cancel(self) -> None:
        """Esc / destroy handler — abort without mutation."""
        # Guard: ignore if already confirmed
        if self.result_event.is_set():
            return

        self.result_data = {"action": "cancel"}
        self.result_event.set()
        self._close()

    def request_cancel(self, message: str = "Region selection timed out") -> None:
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
        """
        Destroy Toplevel and root cleanly. Called from the Tk thread.
        """
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _root(self) -> tk.Tk:
        """Return the stored Tk root instance."""
        if self._tk_root is None:
            raise RuntimeError("Tk root not initialized — call run() first")
        return self._tk_root
