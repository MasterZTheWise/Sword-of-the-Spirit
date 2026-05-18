# settings_menu.py
# This module provides the settings interface for configuring application preferences

import tkinter as tk  # Import tkinter for GUI components
from tkinter import ttk, messagebox, colorchooser  # Import themed widgets, message boxes, and color picker
from scripts.theme_manager import themes, apply_theme  # Import theme management functions
from scripts.ui_common import MinSizeMixin  # Import mixin for minimum window size enforcement
import json  # Import JSON for saving/loading settings
import os  # Import OS utilities for file operations

THEME_FILE = "resources/themes.json"  # Path to themes configuration file

class SettingsMenu(ttk.Frame, MinSizeMixin):  # Define SettingsMenu class inheriting from Frame and MinSizeMixin
    def __init__(self, parent, controller):  # Constructor takes parent widget and controller reference
        super().__init__(parent)  # Initialize parent Frame class
        self.controller = controller  # Store reference to main application controller

        # Make this frame expand inside container
        self.grid_rowconfigure(0, weight=1)  # Make row 0 expandable
        self.grid_columnconfigure(0, weight=1)  # Make column 0 expandable

        # Create a scrollable content area
        canvas = tk.Canvas(self, highlightthickness=0)  # Create canvas for scrolling
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)  # Create vertical scrollbar
        scrollable_frame = ttk.Frame(canvas)  # Create frame inside canvas

        scrollable_frame.bind(  # Bind to configure event
            "<Configure>",  # When frame size changes
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))  # Update scroll region
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")  # Create window in canvas
        canvas.configure(yscrollcommand=scrollbar.set)  # Link canvas to scrollbar

        # Bind mouse wheel scrolling to canvas
        def _on_mousewheel(event):  # Function to handle mouse wheel events
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")  # Scroll canvas based on wheel movement
        
        # Bind mouse wheel to canvas and scrollable frame
        canvas.bind_all("<MouseWheel>", _on_mousewheel)  # Bind to canvas
        scrollable_frame.bind("<MouseWheel>", _on_mousewheel)  # Bind to frame
        
        # Store canvas reference to unbind later if needed
        self.canvas = canvas  # Store canvas reference

        canvas.pack(side="left", fill="both", expand=True)  # Pack canvas to fill space
        scrollbar.pack(side="right", fill="y")  # Pack scrollbar on right side

        # Create main content frame inside scrollable area
        content = ttk.Frame(scrollable_frame, padding=20)  # Create content frame with padding
        content.pack(fill="both", expand=True)  # Pack content frame

        # Title
        ttk.Label(content, text="Settings Menu", font=("Arial", 30)).pack(pady=(0, 15))  # Create title label

        # ========== General Settings Section ==========
        general_frame = ttk.LabelFrame(content, text="General Settings", padding=10)  # Create general settings section
        general_frame.pack(fill="x", pady=10)  # Pack to fill horizontally

        # Variables for general settings
        self.quiz_interval_var = tk.IntVar(value=30)  # Quiz interval in minutes (default 30)
        self.countdown_timer_var = tk.IntVar(value=60)  # Countdown timer in seconds (default 60)
        self.force_on_top_var = tk.BooleanVar(value=False)  # Force window on top (default False)
        self.pass_accuracy_var = tk.IntVar(value=75)  # Required pass accuracy percentage (default 75%)
        self.suggest_random_var = tk.BooleanVar(value=True)  # Suggest random verses (default True)
        self.auto_startup_var = tk.BooleanVar(value=False)  # Auto-launch on startup (default False)

        # Quiz interval setting
        ttk.Label(general_frame, text="Quiz Interval (minutes):").pack(anchor="w")  # Quiz interval label
        ttk.Spinbox(general_frame, from_=1, to=1440, textvariable=self.quiz_interval_var).pack(fill="x", pady=5)  # Spinbox (1-1440 minutes)

        # Countdown timer setting
        ttk.Label(general_frame, text="Countdown Timer (seconds):").pack(anchor="w")  # Countdown timer label
        ttk.Spinbox(general_frame, from_=10, to=600, textvariable=self.countdown_timer_var).pack(fill="x", pady=5)  # Spinbox (10-600 seconds)

        # Force window on top checkbox
        ttk.Checkbutton(general_frame, text="Force Window On Top", variable=self.force_on_top_var).pack(anchor="w", pady=5)  # Checkbox for window on top

        # Pass accuracy percentage setting
        ttk.Label(general_frame, text="Pass Accuracy Required (%):").pack(anchor="w")  # Pass accuracy label
        ttk.Spinbox(general_frame, from_=50, to=100, textvariable=self.pass_accuracy_var).pack(fill="x", pady=5)  # Spinbox (50-100%)

        # Suggest random verses checkbox
        ttk.Checkbutton(general_frame, text="Suggest Random Verses", variable=self.suggest_random_var).pack(anchor="w", pady=5)  # Checkbox for random verses

        # Auto-launch on startup checkbox
        ttk.Checkbutton(general_frame, text="Launch on Computer Startup", variable=self.auto_startup_var).pack(anchor="w", pady=5)  # Checkbox for auto-launch

        # ========== Theme Management Section ==========
        theme_frame = ttk.LabelFrame(content, text="Theme Management", padding=10)  # Create theme management section
        theme_frame.pack(fill="both", expand=True, pady=10)  # Pack to fill space

        # Load existing themes
        self.themes = self.load_themes()  # Load themes from JSON file
        self.current_theme_name = tk.StringVar()  # Variable to store current theme name
        self.current_theme = {}  # Dictionary to store current theme being edited

        # Store references to frames that need theme updates
        self.theme_frames = [general_frame, theme_frame]  # List of frames to update with theme colors

        # Theme selection and management
        theme_select_frame = ttk.Frame(theme_frame)  # Frame for theme selection controls
        theme_select_frame.pack(fill="x", pady=5)  # Pack horizontally

        ttk.Label(theme_select_frame, text="Select Theme:").pack(side="left", padx=5)  # Label for theme dropdown
        self.theme_combo = ttk.Combobox(theme_select_frame, textvariable=self.current_theme_name, values=list(self.themes.keys()), state="readonly")  # Dropdown of theme names
        self.theme_combo.pack(side="left", fill="x", expand=True, padx=5)  # Pack to fill space
        self.theme_combo.bind("<<ComboboxSelected>>", self.load_selected_theme)  # Bind selection event to load theme

        ttk.Button(theme_select_frame, text="Apply", command=self.apply_selected_theme).pack(side="left", padx=2)  # Apply theme button
        ttk.Button(theme_select_frame, text="New", command=self.create_new_theme).pack(side="left", padx=2)  # Create new theme button
        ttk.Button(theme_select_frame, text="Delete", command=self.delete_theme).pack(side="left", padx=2)  # Delete theme button
        ttk.Button(theme_select_frame, text="Save", command=self.save_current_theme).pack(side="left", padx=2)  # Save theme button

        # Theme editor section
        editor_frame = ttk.Frame(theme_frame)  # Frame for theme color editor
        editor_frame.pack(fill="both", expand=True, pady=10)  # Pack to fill space

        # Create a notebook for organizing theme properties
        self.theme_notebook = ttk.Notebook(editor_frame)  # Create tabbed notebook
        self.theme_notebook.pack(fill="both", expand=True)  # Pack to fill space

        # Dictionary to store color variables for each property
        self.color_vars = {}  # Initialize dictionary for color variables

        # Define theme property categories
        self.theme_categories = {  # Dictionary organizing theme properties by category
            "General": ["bg"],  # General background color
            "Frame": ["frame_background", "frame_bordercolor", "frame_borderwidth", "frame_relief", "frame_padding"],  # Frame properties
            "Label": ["label_background", "label_foreground", "label_font", "label_anchor", "label_justify", "label_padding"],  # Label properties
            "Button": ["button_background", "button_foreground", "button_font", "button_relief", "button_padding", "button_lightcolor", "button_darkcolor"],  # Button properties
            "Entry": ["entry_fieldbackground", "entry_foreground", "entry_background", "entry_bordercolor"],  # Entry field properties
            "Checkbutton": ["check_background", "check_foreground", "check_font"],  # Checkbutton properties
            "Combobox": ["combo_fieldbackground", "combo_background", "combo_foreground"],  # Combobox properties
            "Scale": ["scale_background", "scale_troughcolor"],  # Scale slider properties
            "Spinbox": ["spin_fieldbackground", "spin_background", "spin_foreground"],  # Spinbox properties
            "Notebook": ["note_background", "note_tab_background", "note_tab_foreground", "note_tab_active"]  # Notebook tab properties
        }

        # Create tabs for each category
        for category, properties in self.theme_categories.items():  # Iterate through categories
            tab = ttk.Frame(self.theme_notebook, padding=10)  # Create tab frame
            self.theme_notebook.add(tab, text=category)  # Add tab to notebook
            self.create_property_editors(tab, properties)  # Create color editors for properties

        # Initialize with first theme if available
        if self.themes:  # If themes exist
            first_theme = list(self.themes.keys())[0]  # Get first theme name
            self.current_theme_name.set(first_theme)  # Set as current theme
            self.load_selected_theme()  # Load the theme

        # ========== Action Buttons ==========
        button_frame = ttk.Frame(content)  # Frame for action buttons
        button_frame.pack(fill="x", pady=10)  # Pack horizontally

        ttk.Button(button_frame, text="Save All Settings", command=self.save_settings).pack(side="left", padx=5)  # Save all settings button
        ttk.Button(button_frame, text="Back", command=lambda: controller.show_frame("MainMenu")).pack(side="left", padx=5)  # Back to main menu button

        self.enforce_minsize()  # Set minimum window size

    def create_property_editors(self, parent, properties):  # Method to create color/property editors
        """Create editor widgets for theme properties"""
        for prop in properties:  # Iterate through properties
            prop_frame = ttk.Frame(parent)  # Create frame for each property
            prop_frame.pack(fill="x", pady=3)  # Pack horizontally

            # Format property name for display
            display_name = prop.replace("_", " ").title()  # Convert underscores to spaces and capitalize
            ttk.Label(prop_frame, text=f"{display_name}:", width=25).pack(side="left")  # Create property label

            # Determine if this is a color property or other type
            if any(color_word in prop.lower() for color_word in ["color", "background", "foreground"]):  # If property is a color
                # Color property - create StringVar and color picker
                var = tk.StringVar(value="#FFFFFF")  # Create StringVar with default white color
                self.color_vars[prop] = var  # Store variable in dictionary

                entry = ttk.Entry(prop_frame, textvariable=var, width=15)  # Create entry to display hex color
                entry.pack(side="left", padx=5)  # Pack entry

                # Color preview frame
                color_preview = tk.Frame(prop_frame, width=30, height=20, relief="solid", borderwidth=1)  # Create frame to show color preview
                color_preview.pack(side="left", padx=5)  # Pack preview frame
                color_preview.configure(bg=var.get())  # Set background to current color

                # Update preview when color changes
                def update_preview(event=None, preview=color_preview, v=var):  # Helper function to update preview
                    try:  # Try to update color
                        preview.configure(bg=v.get())  # Set preview background to new color
                    except:  # If invalid color
                        pass  # Ignore error
                var.trace("w", lambda *args, preview=color_preview, v=var: update_preview(preview=preview, v=v))  # Trace variable changes

                # Color picker button
                ttk.Button(prop_frame, text="Pick Color", command=lambda v=var, preview=color_preview: self.pick_color(v, preview)).pack(side="left", padx=2)  # Color picker button

            else:  # If property is not a color (font, padding, etc.)
                # Non-color property - create StringVar and entry
                var = tk.StringVar(value="")  # Create StringVar with empty default
                self.color_vars[prop] = var  # Store variable in dictionary

                entry = ttk.Entry(prop_frame, textvariable=var, width=30)  # Create entry for property value
                entry.pack(side="left", padx=5)  # Pack entry

    def pick_color(self, var, preview):  # Method to open color picker dialog
        """Open color picker and update variable and preview"""
        color = colorchooser.askcolor(initialcolor=var.get(), title="Choose Color")  # Open color picker dialog
        if color[1]:  # If user selected a color (not cancelled)
            var.set(color[1])  # Set variable to hex color value
            preview.configure(bg=color[1])  # Update preview frame background

    def load_themes(self):  # Method to load themes from JSON file
        """Load themes from JSON file"""
        try:  # Try to load themes
            if os.path.exists(THEME_FILE):  # If theme file exists
                with open(THEME_FILE, "r") as f:  # Open file for reading
                    return json.load(f)  # Parse and return JSON data
            return {}  # Return empty dictionary if file doesn't exist
        except Exception as e:  # Catch exceptions
            messagebox.showerror("Error", f"Could not load themes: {e}")  # Show error message
            return {}  # Return empty dictionary

    def save_themes(self):  # Method to save themes to JSON file
        """Save themes to JSON file"""
        try:  # Try to save themes
            os.makedirs(os.path.dirname(THEME_FILE), exist_ok=True)  # Create resources directory if it doesn't exist
            with open(THEME_FILE, "w") as f:  # Open file for writing
                json.dump(self.themes, f, indent=4)  # Write themes as formatted JSON
        except Exception as e:  # Catch exceptions
            messagebox.showerror("Error", f"Could not save themes: {e}")  # Show error message

    def load_selected_theme(self, event=None):  # Method to load selected theme into editor
        """Load the selected theme into the editor"""
        theme_name = self.current_theme_name.get()  # Get selected theme name
        if theme_name and theme_name in self.themes:  # If theme exists
            self.current_theme = self.themes[theme_name].copy()  # Copy theme data to current theme

            # Update all color variables
            for prop, var in self.color_vars.items():  # Iterate through all property variables
                if prop in self.current_theme:  # If property exists in theme
                    var.set(str(self.current_theme[prop]))  # Set variable to theme value
                else:  # If property doesn't exist
                    var.set("")  # Set to empty string
            
            # Update LabelFrame backgrounds to match theme
            self.update_frame_backgrounds()  # Call method to update frame colors

    def update_frame_backgrounds(self):  # Method to update LabelFrame backgrounds with theme color
        """Update the background colors of LabelFrames to match the current theme"""
        if "frame_background" in self.current_theme:  # If theme has frame background defined
            bg_color = self.current_theme["frame_background"]  # Get background color from theme
            try:  # Try to update frame colors
                for frame in self.theme_frames:  # Iterate through stored frame references
                    frame.configure(style="Themed.TLabelframe")  # Apply custom style
                # Configure the custom style with theme background
                style = ttk.Style()  # Get style object
                style.configure("Themed.TLabelframe", background=bg_color)  # Set frame background
                style.configure("Themed.TLabelframe.Label", background=bg_color)  # Set label background
            except Exception as e:  # Catch exceptions
                pass  # Silently ignore style errors

    def save_current_theme(self):  # Method to save current theme being edited
        """Save the current theme to the themes dictionary"""
        theme_name = self.current_theme_name.get()  # Get current theme name
        if not theme_name:  # If no theme name
            messagebox.showwarning("No Theme", "Please select or create a theme first.")  # Show warning
            return  # Exit method

        # Update current theme with values from editors
        for prop, var in self.color_vars.items():  # Iterate through all properties
            value = var.get()  # Get property value
            if value:  # If value is not empty
                # Try to convert to appropriate type
                if prop.endswith("width") or prop.endswith("padding"):  # If numeric property
                    try:  # Try to convert to number
                        self.current_theme[prop] = int(value) if value.isdigit() else value  # Convert to int or keep as string
                    except:  # If conversion fails
                        self.current_theme[prop] = value  # Keep as string
                else:  # For other properties
                    self.current_theme[prop] = value  # Store value as-is

        # Save to themes dictionary
        self.themes[theme_name] = self.current_theme.copy()  # Copy current theme to themes dictionary
        self.save_themes()  # Save themes to JSON file
        self.theme_combo['values'] = list(self.themes.keys())  # Update dropdown with new theme list
        self.update_frame_backgrounds()  # Update frame colors with new theme
        messagebox.showinfo("Saved", f"Theme '{theme_name}' saved successfully!")  # Show success message

    def create_new_theme(self):  # Method to create a new theme
        """Create a new theme"""
        # Prompt for theme name
        from tkinter import simpledialog  # Import simple dialog for input
        name = simpledialog.askstring("New Theme", "Enter theme name:")  # Ask for theme name
        if not name:  # If user cancelled
            return  # Exit method

        if name in self.themes:  # If theme name already exists
            if not messagebox.askyesno("Theme Exists", f"Theme '{name}' already exists. Overwrite?"):  # Ask to confirm overwrite
                return  # Exit if user says no

        # Create default theme structure
        self.current_theme = {  # Initialize new theme with default values
            "bg": "#FFFFFF",  # Default white background
            "frame_background": "#F0F0F0", "frame_bordercolor": "#CCCCCC", "frame_borderwidth": 1, "frame_relief": "flat", "frame_padding": 5,  # Frame defaults
            "label_background": "#F0F0F0", "label_foreground": "#000000", "label_font": ("Arial", 10), "label_anchor": "w", "label_justify": "left", "label_padding": 2,  # Label defaults
            "button_background": "#E0E0E0", "button_foreground": "#000000", "button_font": ("Arial", 10), "button_relief": "raised", "button_padding": 5, "button_lightcolor": "#F0F0F0", "button_darkcolor": "#A0A0A0",  # Button defaults
            "entry_fieldbackground": "#FFFFFF", "entry_foreground": "#000000", "entry_background": "#F0F0F0", "entry_bordercolor": "#CCCCCC",  # Entry defaults
            "check_background": "#F0F0F0", "check_foreground": "#000000", "check_font": ("Arial", 10),  # Checkbutton defaults
            "combo_fieldbackground": "#FFFFFF", "combo_background": "#F0F0F0", "combo_foreground": "#000000",  # Combobox defaults
            "scale_background": "#F0F0F0", "scale_troughcolor": "#CCCCCC",  # Scale defaults
            "spin_fieldbackground": "#FFFFFF", "spin_background": "#F0F0F0", "spin_foreground": "#000000",  # Spinbox defaults
            "note_background": "#F0F0F0", "note_tab_background": "#E0E0E0", "note_tab_foreground": "#000000", "note_tab_active": "#FFFFFF"  # Notebook defaults
        }

        self.themes[name] = self.current_theme.copy()  # Add theme to dictionary
        self.current_theme_name.set(name)  # Set as current theme
        self.theme_combo['values'] = list(self.themes.keys())  # Update dropdown
        self.load_selected_theme()  # Load theme into editor
        messagebox.showinfo("Created", f"Theme '{name}' created!")  # Show success message

    def delete_theme(self):  # Method to delete a theme
        """Delete the selected theme"""
        theme_name = self.current_theme_name.get()  # Get current theme name
        if not theme_name:  # If no theme selected
            messagebox.showwarning("No Theme", "Please select a theme to delete.")  # Show warning
            return  # Exit method

        if theme_name not in self.themes:  # If theme doesn't exist
            messagebox.showwarning("Not Found", "Theme not found.")  # Show warning
            return  # Exit method

        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Delete theme '{theme_name}'?"):  # Ask for confirmation
            return  # Exit if user says no

        del self.themes[theme_name]  # Remove theme from dictionary
        self.save_themes()  # Save updated themes to file
        self.theme_combo['values'] = list(self.themes.keys())  # Update dropdown
        self.current_theme_name.set("")  # Clear current theme
        self.current_theme = {}  # Clear current theme data

        # Clear all editors
        for var in self.color_vars.values():  # Iterate through all variables
            var.set("")  # Clear variable

        messagebox.showinfo("Deleted", f"Theme '{theme_name}' deleted.")  # Show success message

    def apply_selected_theme(self):  # Method to apply selected theme to application
        """Apply the selected theme to the application"""
        theme_name = self.current_theme_name.get()  # Get selected theme name
        if not theme_name or theme_name not in self.themes:  # If no theme selected or doesn't exist
            messagebox.showwarning("No Theme", "Please select a valid theme.")  # Show warning
            return  # Exit method

        apply_theme(theme_name, self.controller)  # Apply theme using theme manager
        self.update_frame_backgrounds()  # Update frame colors in settings menu
        messagebox.showinfo("Applied", f"Theme '{theme_name}' applied!")  # Show success message

    def save_settings(self):  # Method to save all general settings to JSON file
        """Save general settings to JSON file"""
        settings_data = {  # Create dictionary of all settings
            "quiz_interval_minutes": self.quiz_interval_var.get(),  # Quiz interval value
            "countdown_timer_seconds": self.countdown_timer_var.get(),  # Countdown timer value
            "force_window_on_top": self.force_on_top_var.get(),  # Force on top value
            "pass_accuracy_percent": self.pass_accuracy_var.get(),  # Pass accuracy value
            "suggest_random_verses": self.suggest_random_var.get(),  # Suggest random value
            "auto_launch_on_startup": self.auto_startup_var.get(),  # Auto-launch value
            "current_theme": self.current_theme_name.get()  # Current theme name
        }
        try:  # Try to save settings
            with open("settings.json", "w") as f:  # Open settings file for writing
                json.dump(settings_data, f, indent=4)  # Write settings as formatted JSON
            messagebox.showinfo("Saved", "Settings saved successfully!")  # Show success message
        except Exception as e:  # Catch exceptions
            messagebox.showerror("Error", f"Could not save settings: {e}")  # Show error message