import tkinter as tk
from tkinter import ttk
from scripts.theme_manager import apply_theme
from scripts.main_menu import MainMenu
from scripts.quiz_menu import QuizMenu
from scripts.settings_menu import SettingsMenu
from scripts.verses_menu import VersesMenu
import ctypes
import os

APPID = "com.tnjpl.swordofthespirit"

class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Hide immediately so the window doesn't flash while building frames
        self.withdraw()

        self.title("Sword of the Spirit")

        container = ttk.Frame(self)
        container.pack(fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        for F, name in (
            (MainMenu, "MainMenu"),
            (SettingsMenu, "SettingsMenu"),
            (VersesMenu, "VersesMenu"),
            (QuizMenu, "QuizMenu"),
        ):
            frame = F(container, self)
            self.frames[name] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("MainMenu")
        apply_theme("MidnightIndigo", self)

        ico_path = os.path.join("assets", "icon.ico")
        self.iconbitmap(ico_path)
        icon = tk.PhotoImage(file="assets/icon1x1.png")
        self.iconphoto(False, icon)

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APPID)

        # Now that everything is built, show the window
        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.focus_force()

        # Center window after layout is ready
        self.after(0, self._center_window)

    def _center_window(self):
        self.update_idletasks()
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()
        try:
            frame.enforce_minsize()
        except Exception:
            pass


if __name__ == "__main__":
    app = App()
    app.mainloop()
