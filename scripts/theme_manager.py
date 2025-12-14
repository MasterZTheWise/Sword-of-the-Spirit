from tkinter import ttk
import json
import os

THEME_FILE = "resources/themes.json"

def load_themes():
    if not os.path.exists(THEME_FILE):
        raise FileNotFoundError(f"{THEME_FILE} not found")

    with open(THEME_FILE, "r") as f:
        return json.load(f)

themes = load_themes()

def apply_theme(theme_name, root):

    theme = themes.get(theme_name, themes["MidnightIndigo"])

    style = ttk.Style()
    style.theme_use("clam")  # ensures colors apply

    # --- Root background ---
    root.configure(bg=theme["bg"])

    # --- TFrame ---
    style.configure(
        "TFrame",
        background=theme["frame_background"],
        bordercolor=theme["frame_bordercolor"],
        borderwidth=theme["frame_borderwidth"],
        relief=theme["frame_relief"],
        padding=theme["frame_padding"],
    )

    # --- TLabel ---
    style.configure(
        "TLabel",
        background=theme["label_background"],
        foreground=theme["label_foreground"],
        font=theme["label_font"],
        anchor=theme["label_anchor"],
        justify=theme["label_justify"],
        padding=theme["label_padding"],
    )

    # --- TButton ---
    style.configure(
        "TButton",
        background=theme["button_background"],
        foreground=theme["button_foreground"],
        font=theme["button_font"],
        relief=theme["button_relief"],
        padding=theme["button_padding"],
        lightcolor=theme["button_lightcolor"],
        darkcolor=theme["button_darkcolor"],
    )
    style.map(
        "TButton",
        background=[("active", theme["button_lightcolor"])],
        foreground=[("active", theme["button_foreground"])],
    )

    # --- TEntry ---
    style.configure(
        "TEntry",
        fieldbackground=theme["entry_fieldbackground"],
        foreground=theme["entry_foreground"],
        background=theme["entry_background"],
        bordercolor=theme["entry_bordercolor"],
    )

    # --- TCheckbutton ---
    style.configure(
        "TCheckbutton",
        background=theme["check_background"],
        foreground=theme["check_foreground"],
        font=theme["check_font"],
    )

    # --- TCombobox ---
    style.configure(
        "TCombobox",
        fieldbackground=theme["combo_fieldbackground"],
        background=theme["combo_background"],
        foreground=theme["combo_foreground"],
    )

    # --- TScale ---
    style.configure(
        "TScale",
        background=theme["scale_background"],
        troughcolor=theme["scale_troughcolor"],
    )

    # --- TSpinbox ---
    style.configure(
        "TSpinbox",
        fieldbackground=theme["spin_fieldbackground"],
        background=theme["spin_background"],
        foreground=theme["spin_foreground"],
    )

    # --- TNotebook ---
    style.configure(
        "TNotebook",
        background=theme["note_background"],
    )
    style.configure(
        "TNotebook.Tab",
        background=theme["note_tab_background"],
        foreground=theme["note_tab_foreground"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", theme["note_tab_active"])],
        foreground=[("selected", theme["note_tab_foreground"])],
    )
