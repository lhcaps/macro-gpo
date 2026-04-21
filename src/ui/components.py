import tkinter as tk

from PIL import ImageTk


class CoordinatePicker:
    def __init__(self, parent, screenshot, on_complete, on_cancel=None):
        self.parent = parent
        self.screenshot = screenshot
        self.on_complete = on_complete
        self.on_cancel = on_cancel

        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="crosshair", bg="black")
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

        self.tk_img = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.top, cursor="crosshair", highlightthickness=0, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        self.canvas.create_text(
            20,
            20,
            text="Click once to save this coordinate | ESC to cancel",
            anchor=tk.NW,
            fill="#f8fafc",
            font=("Segoe UI", 16, "bold"),
        )

        self.canvas.bind("<Button-1>", self.on_click)
        self.top.bind("<Escape>", lambda _: self.cancel())

    def cancel(self):
        if callable(self.on_cancel):
            self.on_cancel()
        self.top.destroy()

    def on_click(self, event):
        self.on_complete([event.x_root, event.y_root])
        self.top.destroy()


class AreaPicker:
    def __init__(self, parent, screenshot, on_complete, on_cancel=None):
        self.parent = parent
        self.screenshot = screenshot
        self.on_complete = on_complete
        self.on_cancel = on_cancel

        self.top = tk.Toplevel(parent)
        self.top.attributes("-fullscreen", True)
        self.top.attributes("-topmost", True)
        self.top.config(cursor="crosshair", bg="black")
        self.top.protocol("WM_DELETE_WINDOW", self.cancel)

        self.tk_img = ImageTk.PhotoImage(self.screenshot)
        self.canvas = tk.Canvas(self.top, cursor="crosshair", highlightthickness=0, bg="black")
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.tk_img)

        self.start_x = None
        self.start_y = None
        self.rect = None

        self.canvas.bind("<ButtonPress-1>", self.on_press)
        self.canvas.bind("<B1-Motion>", self.on_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_release)
        self.top.bind("<Escape>", lambda _: self.cancel())

        self.canvas.create_text(
            20,
            20,
            text="Drag to save the screenshot area | ESC to cancel",
            anchor=tk.NW,
            fill="#f8fafc",
            font=("Segoe UI", 16, "bold"),
        )

    def cancel(self):
        if callable(self.on_cancel):
            self.on_cancel()
        self.top.destroy()

    def on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect:
            self.canvas.delete(self.rect)
        self.rect = self.canvas.create_rectangle(self.start_x, self.start_y, 1, 1, outline="#38bdf8", width=2)

    def on_drag(self, event):
        self.canvas.coords(self.rect, self.start_x, self.start_y, event.x, event.y)

    def on_release(self, event):
        end_x, end_y = event.x, event.y
        left = min(self.start_x, end_x)
        top = min(self.start_y, end_y)
        right = max(self.start_x, end_x)
        bottom = max(self.start_y, end_y)

        if right - left < 5 or bottom - top < 5:
            return

        self.on_complete([left, top, right, bottom])
        self.top.destroy()
