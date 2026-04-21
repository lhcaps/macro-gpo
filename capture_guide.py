import tkinter as tk

import pyautogui

from main import enable_high_dpi
from src.ui.app import ZedsuApp


if __name__ == "__main__":
    enable_high_dpi()
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05
    root = tk.Tk()
    app = ZedsuApp(root)
    root.after(600, lambda: (app.notebook.select(app.assets_tab), app.capture_all_assets()))
    root.mainloop()
