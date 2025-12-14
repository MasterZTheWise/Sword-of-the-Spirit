import threading
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
from scripts.theme_manager import themes, apply_theme
from scripts.sheath import Sheath
from scripts.ui_common import AddVerseDialog, MinSizeMixin
import pythonbible as bible
from pythonbible import InvalidVerseError, get_verse_id, get_verse_text
import json

class VersesMenu(ttk.Frame, MinSizeMixin):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.sheath = Sheath("resources/verses.csv")

        ttk.Label(self, text="Verses", font=("Arial", 30)).pack(pady=10)

        # Main container for two lists + move buttons
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)

        # WIP list
        wip_frame = ttk.Frame(main_frame)
        wip_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(wip_frame, text="Works in Progress").pack()
        self.wip_list = tk.Listbox(wip_frame, width=50, height=20, exportselection=False)
        wip_scroll = ttk.Scrollbar(wip_frame, orient="vertical", command=self.wip_list.yview)
        self.wip_list.config(yscrollcommand=wip_scroll.set)
        self.wip_list.pack(side="left", fill="both", expand=True)
        wip_scroll.pack(side="right", fill="y")

        # Middle buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(side="left", padx=10)

        ttk.Button(btn_frame, text="→", command=self.move_to_memorized).pack(pady=5)
        ttk.Button(btn_frame, text="←", command=self.move_to_wip).pack(pady=5)

        # Memorized list
        mem_frame = ttk.Frame(main_frame)
        mem_frame.pack(side="left", fill="both", expand=True)

        ttk.Label(mem_frame, text="Memorized").pack()
        self.mem_list = tk.Listbox(mem_frame, width=50, height=20, exportselection=False)
        mem_scroll = ttk.Scrollbar(mem_frame, orient="vertical", command=self.mem_list.yview)
        self.mem_list.config(yscrollcommand=mem_scroll.set)
        self.mem_list.pack(side="left", fill="both", expand=True)
        mem_scroll.pack(side="right", fill="y")

        try:
            self.wip_list.config(selectbackground="#4a90e2", selectforeground="#ffffff")
            self.mem_list.config(selectbackground="#4a90e2", selectforeground="#ffffff")
        except Exception:
            pass

        # Preview text (selectable/copyable). Block typing but allow selection.
        self.verse_display = tk.Text(self, height=8, wrap="word", state="normal")
        self.verse_display.pack(fill="x", padx=20, pady=10)
        self.verse_display.bind("<Key>", self._preview_key_handler)

        # Bind selection events (selection pins preview)
        self.wip_list.bind("<<ListboxSelect>>", self._on_listbox_select)
        self.mem_list.bind("<<ListboxSelect>>", self._on_listbox_select)

        # Action buttons (apply to whichever list has selection)
        action_frame = ttk.Frame(self)
        action_frame.pack(pady=10)

        ttk.Button(action_frame, text="Add Verse", command=self.add_verse).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Remove Selected", command=self.remove_selected).pack(side="left", padx=5)
        ttk.Button(action_frame, text="Toggle Favorite", command=self.toggle_favorite).pack(side="left", padx=5)

        ttk.Button(action_frame, text="Back to Main Menu",
                   command=lambda: controller.show_frame("MainMenu")).pack(side="left", padx=5)

        # Internal maps
        self.passages = []        # full list from sheath.getPassages()
        self.wip_indices = []     # indices into self.passages that are WIP
        self.mem_indices = []     # indices into self.passages that are Memorized

        # Load verses into lists
        self.load_verses()
        self.enforce_minsize()

    # ----------------- Loading / formatting -----------------
    def format_range_label(self, ref, favorite=False):
        start = f"{ref.book.name} {ref.start_chapter}:{ref.start_verse}"
        if (ref.end_chapter != ref.start_chapter) or (ref.end_verse != ref.start_verse):
            end = f"{ref.end_chapter}:{ref.end_verse}"
            if getattr(ref, "end_book", None):
                end_book = ref.end_book.name if hasattr(ref.end_book, "name") else str(ref.end_book)
                end = f"{end_book} {end}"
            label = f"{start}-{end}"
        else:
            label = start
        if favorite:
            label = "⭐ " + label
        return label

    def load_verses(self):
        """Load passages from sheath and populate both listboxes and index maps."""
        self.wip_list.delete(0, tk.END)
        self.mem_list.delete(0, tk.END)

        # reset maps
        self.passages = []
        self.wip_indices = []
        self.mem_indices = []

        try:
            # canonical list of NormalizedReference objects
            self.passages = self.sheath.getPassages()

            # read CSV metadata (WIP and Favorite flags) in file order
            metadata = []
            with open(self.sheath.filename, "r", encoding="utf-8") as f:
                rows = [r.rstrip("\n") for r in f.readlines()]
            if rows and rows[0].lower().startswith("book,"):
                rows = rows[1:]

            for row in rows:
                parts = row.split(",")
                while len(parts) < 8:
                    parts.append("")
                wip_flag = parts[6].strip() if len(parts) > 6 else "0"
                fav_flag = parts[7].strip() if len(parts) > 7 else "False"
                metadata.append((wip_flag, fav_flag == "True"))

            # iterate passages and metadata in parallel (file order)
            for idx, ref in enumerate(self.passages):
                wip_flag, is_fav = metadata[idx] if idx < len(metadata) else ("0", False)
                label = self.format_range_label(ref, is_fav)
                if wip_flag == "0" or wip_flag == "":
                    self.wip_indices.append(idx)
                    self.wip_list.insert(tk.END, label)
                else:
                    self.mem_indices.append(idx)
                    self.mem_list.insert(tk.END, label)
        except Exception as e:
            self.wip_list.insert(tk.END, f"Error loading verses: {e}")

    # ----------------- Selection mapping -----------------
    def get_selected_ref(self):
        """Return the currently selected reference from either list (or None)."""
        if self.wip_list.curselection():
            sel = self.wip_list.curselection()[0]
            return self.passages[self.wip_indices[sel]]
        if self.mem_list.curselection():
            sel = self.mem_list.curselection()[0]
            return self.passages[self.mem_indices[sel]]
        return None

    # ----------------- Selection-driven preview -----------------
    def _on_listbox_select(self, event):
        """Clear selection in the other list and update the preview."""
        widget = event.widget
        # If selection came from WIP, clear Memorized; if from Memorized, clear WIP
        if widget is self.wip_list:
            # clear mem selection without triggering its handler loop
            if self.mem_list.curselection():
                self.mem_list.selection_clear(0, tk.END)
        elif widget is self.mem_list:
            if self.wip_list.curselection():
                self.wip_list.selection_clear(0, tk.END)

        # Update preview based on the new selection
        self.on_selection_change()

    def on_selection_change(self):
        """Show the selected passage in the preview (concatenated full range)."""
        ref = self.get_selected_ref()
        if ref:
            self._fetch_and_show_full_range(ref)
        else:
            # clear preview if nothing selected
            self.verse_display.config(state="normal")
            self.verse_display.delete("1.0", tk.END)

    def _fetch_and_show_full_range(self, ref):
        """Background fetch of the full range text (concatenated) and update preview."""
        def fetch_and_show():
            try:
                verse_texts = []
                start_ch = ref.start_chapter
                end_ch = ref.end_chapter or start_ch

                for ch in range(start_ch, end_ch + 1):
                    if ch == ref.start_chapter:
                        v_start = ref.start_verse
                    else:
                        v_start = 1

                    if ch == ref.end_chapter:
                        v_end_target = ref.end_verse
                    else:
                        v_end_target = None

                    v = v_start
                    while True:
                        try:
                            vid = get_verse_id(ref.book, ch, v)
                        except InvalidVerseError:
                            break
                        except Exception:
                            break

                        try:
                            vtext = get_verse_text(vid)
                        except Exception:
                            vtext = None

                        if vtext:
                            verse_texts.append(vtext.strip())

                        if v_end_target is not None and v >= v_end_target:
                            break
                        v += 1

                display_text = " ".join(verse_texts).replace("\n", " ").strip()
                if not display_text:
                    display_text = "(no text available)"

                def update_ui():
                    # keep Text widget editable only for selection/copy; block typing via key binding
                    self.verse_display.config(state="normal")
                    self.verse_display.delete("1.0", tk.END)
                    self.verse_display.insert(tk.END, display_text)
                    # do not disable; allow selection and copy
                self.after(0, update_ui)
            except Exception:
                pass

        t = threading.Thread(target=fetch_and_show, daemon=True)
        t.start()

    def _preview_key_handler(self, event):
        """
        Allow Ctrl+A / Cmd+A and Ctrl+C / Cmd+C for selection and copy.
        Block other typing into the preview text.
        """
        # event.state bitmask: check for Control or Command modifiers
        ctrl = (event.state & 0x4) != 0        # Control on many platforms
        meta = (event.state & 0x8) != 0        # sometimes Meta/Command
        keysym = event.keysym.lower()

        # Allow Ctrl/Cmd + A (select all) and Ctrl/Cmd + C (copy)
        if (ctrl or meta) and keysym in ("a", "c"):
            return None  # allow default handling

        # Allow navigation keys so user can move caret for selection with keyboard
        if keysym in ("left", "right", "up", "down", "home", "end", "prior", "next"):
            return None

        # Block all other key input
        return "break"

    # ----------------- Action methods -----------------
    def add_verse(self):
        """
        Open AddVerseDialog and add the returned NormalizedReference.
        Place the new passage in the same list as the current selection:
        - if a Memorized item is selected -> setMemStatus([ref], [1])
        - otherwise -> setMemStatus([ref], [0]) (WIP)
        """
        dialog = AddVerseDialog(self)
        ref = dialog.result
        if not ref:
            return

        try:
            # Add the passage first (sheath may append it)
            self.sheath.addPassages([ref])
            # Determine target mem status based on current selection
            # If a memorized item is selected, put new passage in Memorized
            if self.mem_list.curselection():
                self.sheath.setMemStatus([ref], [1])
            else:
                # default to WIP if WIP selected or nothing selected
                self.sheath.setMemStatus([ref], [0])

            # Reload lists and try to select the newly added passage
            self.load_verses()

            # Re-select the newly added passage if found
            try:
                new_idx = self.passages.index(ref)
                if new_idx in self.wip_indices:
                    listbox = self.wip_list
                    list_index = self.wip_indices.index(new_idx)
                elif new_idx in self.mem_indices:
                    listbox = self.mem_list
                    list_index = self.mem_indices.index(new_idx)
                else:
                    return

                # clear other list selection and select the new item
                if listbox is self.wip_list:
                    self.mem_list.selection_clear(0, tk.END)
                else:
                    self.wip_list.selection_clear(0, tk.END)

                listbox.selection_clear(0, tk.END)
                listbox.selection_set(list_index)
                listbox.see(list_index)

                if hasattr(self, "on_selection_change"):
                    self.on_selection_change()
            except ValueError:
                # nothing to do if not found
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Could not add verse: {e}")

            dialog = AddVerseDialog(self)
            ref = dialog.result
            if ref:
                try:
                    self.sheath.addPassages([ref])
                    self.load_verses()
                except Exception as e:
                    messagebox.showerror("Error", f"Could not add verse: {e}")

    def edit_selected(self):
        """
        Open AddVerseDialog prepopulated with the currently selected verse.
        Replace the old passage with the edited one and preserve the memorization status
        (WIP vs Memorized) of the original passage.
        """
        ref = self.get_selected_ref()
        if not ref:
            messagebox.showwarning("No selection", "Please select a verse to edit.")
            return

        # Determine original mem status (0 = WIP, 1 = Memorized)
        original_mem_status = 0
        try:
            # If the selected index is in mem_indices, it's memorized
            passage_idx = self.passages.index(ref)
            if passage_idx in self.mem_indices:
                original_mem_status = 1
            else:
                original_mem_status = 0
        except Exception:
            # fallback: assume WIP
            original_mem_status = 0

        # Open dialog with initial values
        dialog = AddVerseDialog(self, initial_ref=ref)
        new_ref = dialog.result
        if new_ref is None:
            return  # user cancelled

        try:
            # Remove old and add new passage
            # If your Sheath has an update method, prefer that to preserve ordering/metadata
            self.sheath.removePassages([ref])
            self.sheath.addPassages([new_ref])

            # Ensure the new passage has the same mem status as the original
            self.sheath.setMemStatus([new_ref], [original_mem_status])

            # Reload lists
            self.load_verses()

            # Re-select the edited passage in the appropriate list
            try:
                new_passage_idx = self.passages.index(new_ref)
                if new_passage_idx in self.wip_indices:
                    listbox = self.wip_list
                    list_index = self.wip_indices.index(new_passage_idx)
                elif new_passage_idx in self.mem_indices:
                    listbox = self.mem_list
                    list_index = self.mem_indices.index(new_passage_idx)
                else:
                    # not found; clear selections
                    self.wip_list.selection_clear(0, tk.END)
                    self.mem_list.selection_clear(0, tk.END)
                    if hasattr(self, "on_selection_change"):
                        self.on_selection_change()
                    return

                # Clear other list selection, set selection in the correct list, and ensure it's visible
                if listbox is self.wip_list:
                    self.mem_list.selection_clear(0, tk.END)
                else:
                    self.wip_list.selection_clear(0, tk.END)

                listbox.selection_clear(0, tk.END)
                listbox.selection_set(list_index)
                listbox.see(list_index)

                # Update preview
                if hasattr(self, "on_selection_change"):
                    self.on_selection_change()
            except ValueError:
                # fallback: clear selection and update preview
                self.wip_list.selection_clear(0, tk.END)
                self.mem_list.selection_clear(0, tk.END)
                if hasattr(self, "on_selection_change"):
                    self.on_selection_change()

        except Exception as e:
            messagebox.showerror("Error", f"Could not edit verse: {e}")

            """
            Open the AddVerseDialog prepopulated with the currently selected verse.
            Replace the old passage with the edited one and preserve selection.
            """
            # Get currently selected ref
            ref = self.get_selected_ref()
            if not ref:
                messagebox.showwarning("No selection", "Please select a verse to edit.")
                return

            # Open dialog with initial_ref set
            dialog = AddVerseDialog(self, initial_ref=ref)
            new_ref = dialog.result
            if new_ref is None:
                return  # user cancelled

            try:
                # Replace the old passage with the new one in the sheath
                # Use sheath API: remove old, add new (preserves file-based canonical ordering if addPassages appends)
                # If your Sheath supports an update method, use that instead.
                self.sheath.removePassages([ref])
                self.sheath.addPassages([new_ref])

                # Reload lists
                self.load_verses()

                # Re-select the edited passage in the appropriate list (if present)
                try:
                    new_passage_idx = self.passages.index(new_ref)
                    if new_passage_idx in self.wip_indices:
                        listbox = self.wip_list
                        list_index = self.wip_indices.index(new_passage_idx)
                    elif new_passage_idx in self.mem_indices:
                        listbox = self.mem_list
                        list_index = self.mem_indices.index(new_passage_idx)
                    else:
                        # not found; clear selections
                        self.wip_list.selection_clear(0, tk.END)
                        self.mem_list.selection_clear(0, tk.END)
                        if hasattr(self, "on_selection_change"):
                            self.on_selection_change()
                        return

                    # Clear other list selection, set selection in the correct list, and ensure it's visible
                    if listbox is self.wip_list:
                        self.mem_list.selection_clear(0, tk.END)
                    else:
                        self.wip_list.selection_clear(0, tk.END)

                    listbox.selection_clear(0, tk.END)
                    listbox.selection_set(list_index)
                    listbox.see(list_index)

                    # Update preview
                    if hasattr(self, "on_selection_change"):
                        self.on_selection_change()
                except ValueError:
                    # fallback: clear selection and update preview
                    self.wip_list.selection_clear(0, tk.END)
                    self.mem_list.selection_clear(0, tk.END)
                    if hasattr(self, "on_selection_change"):
                        self.on_selection_change()

            except Exception as e:
                messagebox.showerror("Error", f"Could not edit verse: {e}")

    def remove_selected(self):
        ref = self.get_selected_ref()
        if not ref:
            messagebox.showwarning("No selection", "Please select a verse to remove.")
            return
        confirm = messagebox.askyesno("Confirm Delete", f"Remove {ref.book.name} {ref.start_chapter}:{ref.start_verse}?")
        if confirm:
            self.sheath.removePassages([ref])
            self.load_verses()

    def toggle_favorite(self):
        """
        Toggle favorite for the currently selected passage while preserving selection.
        """
        # Get currently selected ref (from either list)
        ref = self.get_selected_ref()
        if not ref:
            messagebox.showwarning("No selection", "Please select a verse.")
            return

        try:
            # Remember the identity of the passage in self.passages (index)
            try:
                passage_idx = self.passages.index(ref)
            except ValueError:
                # fallback: try to locate via sheath.findPassages
                rows = self.sheath.findPassages([ref])
                if not rows:
                    messagebox.showerror("Error", "Could not locate the selected passage.")
                    return
                passage_idx = rows[0]

            # Toggle favorite using sheath helpers
            # Read CSV line to determine current favorite state (if your sheath doesn't provide a getter)
            with open(self.sheath.filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            # sheath.findPassages returns file-row index (0-based for data rows) — adjust if needed
            # Try to find the CSV row that corresponds to passage_idx
            csv_row_idx = passage_idx  # if your sheath.getPassages() preserves file order
            # If your sheath.findPassages returns a different mapping, prefer that:
            try:
                rows = self.sheath.findPassages([ref])
                if rows:
                    csv_row_idx = rows[0]
            except Exception:
                pass

            # Read the CSV line and check favorite column (safe parsing)
            line_idx = csv_row_idx + 1  # account for header row if present
            current_status = "False"
            if 0 <= line_idx < len(lines):
                parts = lines[line_idx].rstrip("\n").split(",")
                current_status = parts[7].strip() if len(parts) > 7 else "False"

            # Toggle using sheath API
            if current_status == "True":
                self.sheath.unsetFavorites([ref])
            else:
                self.sheath.setFavorites([ref])

            # Reload lists (this repopulates self.passages, wip_indices, mem_indices)
            self.load_verses()

            # After reload, find the passage object again and re-select it
            try:
                # find the passage object in self.passages (NormalizedReference equality should work)
                new_passage_idx = self.passages.index(ref)
                # determine which list it belongs to
                if new_passage_idx in self.wip_indices:
                    listbox = self.wip_list
                    list_index = self.wip_indices.index(new_passage_idx)
                elif new_passage_idx in self.mem_indices:
                    listbox = self.mem_list
                    list_index = self.mem_indices.index(new_passage_idx)
                else:
                    # not found in either list — just clear selection
                    self.wip_list.selection_clear(0, tk.END)
                    self.mem_list.selection_clear(0, tk.END)
                    if hasattr(self, "on_selection_change"):
                        self.on_selection_change()
                    return

                # Clear other list selection, set selection in the correct list, and ensure it's visible
                if listbox is self.wip_list:
                    self.mem_list.selection_clear(0, tk.END)
                else:
                    self.wip_list.selection_clear(0, tk.END)

                listbox.selection_clear(0, tk.END)
                listbox.selection_set(list_index)
                listbox.see(list_index)

                # Update preview/other UI
                if hasattr(self, "on_selection_change"):
                    self.on_selection_change()
            except ValueError:
                # If we can't find it, just clear selections and update UI
                self.wip_list.selection_clear(0, tk.END)
                self.mem_list.selection_clear(0, tk.END)
                if hasattr(self, "on_selection_change"):
                    self.on_selection_change()

        except Exception as e:
            messagebox.showerror("Error", f"Could not toggle favorite: {e}")

    def move_to_memorized(self):
        """Move selected verse from WIP to Memorized (uses get_selected_ref())."""
        # ensure a WIP item is selected
        if not self.wip_list.curselection():
            messagebox.showwarning("No selection", "Select a verse in WIP.")
            return

        # get the currently selected ref (works with your get_selected_ref())
        ref = self.get_selected_ref()
        if not ref:
            return

        # update memorization status and refresh lists
        self.sheath.setMemStatus([ref], [1])
        self.load_verses()

        # clear WIP selection and try to select the moved item in Memorized
        try:
            self.wip_list.selection_clear(0, tk.END)
            new_index = self.mem_indices.index(self.passages.index(ref))
            self.mem_list.selection_clear(0, tk.END)
            self.mem_list.selection_set(new_index)
        except Exception:
            # if we can't find it, just clear selection
            self.wip_list.selection_clear(0, tk.END)

        # update preview/selection-driven UI
        if hasattr(self, "on_selection_change"):
            self.on_selection_change()

    def move_to_wip(self):
        """Move selected verse from Memorized to WIP (uses get_selected_ref())."""
        if not self.mem_list.curselection():
            messagebox.showwarning("No selection", "Select a verse in Memorized.")
            return

        ref = self.get_selected_ref()
        if not ref:
            return

        self.sheath.setMemStatus([ref], [0])
        self.load_verses()

        try:
            self.mem_list.selection_clear(0, tk.END)
            new_index = self.wip_indices.index(self.passages.index(ref))
            self.wip_list.selection_clear(0, tk.END)
            self.wip_list.selection_set(new_index)
        except Exception:
            self.mem_list.selection_clear(0, tk.END)

        if hasattr(self, "on_selection_change"):
            self.on_selection_change()