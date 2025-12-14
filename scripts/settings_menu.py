# settings_menu.py
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from scripts.theme_manager import themes, apply_theme
from scripts.ui_common import MinSizeMixin
import json

class SettingsMenu(ttk.Frame, MinSizeMixin):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Make this frame expand inside container
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Create a content frame and center it
        content = ttk.Frame(self, padding=20)
        content.grid(row=0, column=0)
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

       
        # Title
        ttk.Label(content, text="Settings Menu", font=("Arial", 30)).pack(pady=(0, 15))

        # Variables
        self.username_var = tk.StringVar()
        self.feature_var = tk.BooleanVar()
        self.theme_var = tk.StringVar(value="MidnightIndigo")
        self.volume_var = tk.IntVar(value=50)
        self.brightness_var = tk.DoubleVar(value=0.5)
        self.max_items_var = tk.IntVar(value=10)

        # Widgets
        ttk.Label(content, text="Username:").pack(anchor="w")
        ttk.Entry(content, textvariable=self.username_var).pack(fill="x", pady=5)

        ttk.Checkbutton(content, text="Enable Feature", variable=self.feature_var).pack(anchor="w", pady=5)

        ttk.Label(content, text="Theme:").pack(anchor="w")
        theme_dropdown = ttk.Combobox(
            content,
            textvariable=self.theme_var,
            values=list(themes.keys()),
            state="readonly"
        )
        theme_dropdown.pack(fill="x", pady=5)
        theme_dropdown.bind("<<ComboboxSelected>>", lambda e: apply_theme(self.theme_var.get(), controller))

        ttk.Label(content, text="Volume:").pack(anchor="w")
        ttk.Scale(content, from_=0, to=100, orient="horizontal", variable=self.volume_var).pack(fill="x", pady=5)

        ttk.Label(content, text="Brightness:").pack(anchor="w")
        ttk.Scale(content, from_=0.0, to=1.0, orient="horizontal", variable=self.brightness_var).pack(fill="x", pady=5)

        ttk.Label(content, text="Max Items:").pack(anchor="w")
        ttk.Spinbox(content, from_=1, to=100, textvariable=self.max_items_var).pack(fill="x", pady=5)

        # Buttons
        ttk.Button(content, text="Save Settings", command=self.save_settings).pack(pady=(15, 5))
        ttk.Button(content, text="Back", command=lambda: controller.show_frame("MainMenu")).pack(pady=10)
        
        
        self.enforce_minsize()



    def save_settings(self):
        settings_data = {
            "username": self.username_var.get(),
            "enable_feature": self.feature_var.get(),
            "theme": self.theme_var.get(),
            "volume": self.volume_var.get(),
            "brightness": self.brightness_var.get(),
            "max_items": self.max_items_var.get()
        }
        try:
            with open("settings.json", "w") as f:
                json.dump(settings_data, f, indent=4)
            messagebox.showinfo("Saved", "Settings saved to settings.json")
        except Exception as e:
            messagebox.showerror("Error", f"Could not save settings: {e}")