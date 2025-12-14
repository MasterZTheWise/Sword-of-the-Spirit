# main_menu.py
import tkinter as tk
from tkinter import ttk
from scripts.ui_common import MinSizeMixin

class MainMenu(ttk.Frame, MinSizeMixin):
    def __init__(self, parent, controller):
        super().__init__(parent)

        # Create a container that fills the frame
        container = ttk.Frame(self)
        container.pack(expand=True, fill="both")

        # Use grid with a single centered column/row
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        # Inner frame that will hold the actual widgets
        inner = ttk.Frame(container)
        inner.grid(row=0, column=0)

        # Now pack your widgets into `inner`
        ttk.Label(inner, text="Sword of the Spirit", font=("Arial",40)).pack(pady=10)
        ttk.Button(inner, text="Quiz", command=lambda: controller.show_frame("QuizMenu")).pack(pady=10)
        ttk.Button(inner, text="Verses", command=lambda: controller.show_frame("VersesMenu")).pack(pady=10)
        ttk.Button(inner, text="Settings", command=lambda: controller.show_frame("SettingsMenu")).pack(pady=10)
        
        self.enforce_minsize()
