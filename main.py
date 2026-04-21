import ctypes
import tkinter as tk

import pyautogui

from src.ui.app import ZedsuApp


def enable_high_dpi():
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


if __name__ == "__main__":
    enable_high_dpi()
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.05

    root = tk.Tk()
    app = ZedsuApp(root)
    root.mainloop()
