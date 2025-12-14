import tkinter as tk
from tkinter import ttk, simpledialog, messagebox
import pythonbible as bible
import sys

class MinSizeMixin:
    """
    Mixin to compute the requested size of a frame and set the toplevel minsize.
    This version attempts to include window decorations (title bar, icon, buttons, borders).
    """

    def enforce_minsize(self):
        """Instance method wrapper for the static helper."""
        MinSizeMixin.enforce_minsize_for_frame(self)

    @staticmethod
    def _get_windows_decoration():
        """
        Use Windows system metrics to compute decoration sizes:
        returns (decoration_width, decoration_height)
        where decoration_width is extra width added by borders + titlebar buttons/icon,
        and decoration_height is extra height added by titlebar + top/bottom borders.
        """
        try:
            import ctypes
            SM_CXSIZEFRAME = 32
            SM_CYSIZEFRAME = 33
            SM_CYCAPTION = 4
            SM_CXFRAME = 32  # alias for some versions
            SM_CYFRAME = 33

            user32 = ctypes.windll.user32
            # outer frame thickness (left+right)
            frame_x = user32.GetSystemMetrics(SM_CXSIZEFRAME) * 2
            # top+bottom frame thickness
            frame_y = user32.GetSystemMetrics(SM_CYSIZEFRAME) * 2
            # caption (title bar) height
            caption = user32.GetSystemMetrics(SM_CYCAPTION)
            # total decoration height = caption + top/bottom frame
            dec_h = caption + frame_y
            # width contribution: left+right frame + space for icon/buttons (approx)
            # We cannot get exact width of buttons/icon via GetSystemMetrics, so include a small extra
            dec_w = frame_x + 150  # 120px buffer for icon + buttons + title text area
            return int(dec_w), int(dec_h)
        except Exception:
            return None

    @staticmethod
    def _measure_decoration_by_difference(frame):
        """
        Fallback: measure decoration by creating a temporary toplevel if needed,
        or by comparing the toplevel size to the frame's requested size.
        Returns (decoration_width, decoration_height).
        """
        try:
            toplevel = frame.winfo_toplevel()
            # Ensure geometry info is up to date
            frame.update_idletasks()
            toplevel.update_idletasks()

            # requested sizes for the client frame
            client_w = frame.winfo_reqwidth()
            client_h = frame.winfo_reqheight()

            # current toplevel outer size
            outer_w = toplevel.winfo_width() or toplevel.winfo_reqwidth()
            outer_h = toplevel.winfo_height() or toplevel.winfo_reqheight()

            # If outer is smaller than client (rare), use reqwidth/reqheight of toplevel
            if outer_w < client_w:
                outer_w = toplevel.winfo_reqwidth()
            if outer_h < client_h:
                outer_h = toplevel.winfo_reqheight()

            dec_w = max(0, outer_w - client_w)
            dec_h = max(0, outer_h - client_h)

            # If measurement seems zero (e.g., not yet mapped), provide a conservative default
            if dec_w == 0 and dec_h == 0:
                dec_w = 120
                dec_h = 40

            return int(dec_w), int(dec_h)
        except Exception:
            # conservative defaults
            return 120, 40

    @staticmethod
    def enforce_minsize_for_frame(frame):
        """
        Compute required size for `frame` and set the toplevel minsize including decorations.
        Call after layout (update_idletasks) and after dynamic content changes.
        """
        try:
            frame.update_idletasks()
        except Exception:
            pass

        try:
            req_w = frame.winfo_reqwidth()
            req_h = frame.winfo_reqheight()
        except Exception:
            return

        # Try platform-specific decoration measurement
        dec_w = dec_h = 0
        if sys.platform.startswith("win"):
            win_dec = MinSizeMixin._get_windows_decoration()
            if win_dec:
                dec_w, dec_h = win_dec
        if dec_w == 0 and dec_h == 0:
            # fallback measurement by difference
            dec_w, dec_h = MinSizeMixin._measure_decoration_by_difference(frame)

        # Add a small padding so icon/title/buttons don't clip
        pad_w, pad_h = 12, 8

        min_w = max(1, req_w + dec_w + pad_w)
        min_h = max(1, req_h + dec_h + pad_h)

        try:
            toplevel = frame.winfo_toplevel()
            toplevel.minsize(min_w, min_h)
        except Exception:
            pass



class AddVerseDialog(tk.Toplevel):
    def __init__(self, parent, theme=None, apply_theme_fn=None, initial_ref=None):
        super().__init__(parent)
        self.withdraw()  # Hide the window until it's ready
        self.parent = parent
        self.result = None
        self.initial_ref = initial_ref

        # Build UI first
        self.title("Add Verse" if initial_ref is None else "Edit Verse")
        self.resizable(False, False)

        frm = ttk.Frame(self, padding=12)
        frm.grid(row=0, column=0, sticky="nsew")

        # Book combobox
        ttk.Label(frm, text="Book:").grid(row=0, column=0, sticky="w", padx=(0,6), pady=4)
        self.book_var = tk.StringVar()
        book_names = [getattr(b, "name", str(b)) for b in bible.Book]
        self.book_combo = ttk.Combobox(frm, textvariable=self.book_var, values=book_names, state="readonly", width=25)
        self.book_combo.grid(row=0, column=1, columnspan=3, pady=4, sticky="w")
        if book_names:
            self.book_combo.set(book_names[0])

        # Start chapter/verse
        ttk.Label(frm, text="Start Chapter:").grid(row=1, column=0, sticky="w", padx=(0,6), pady=4)
        self.start_ch_var = tk.IntVar(value=1)
        ttk.Entry(frm, textvariable=self.start_ch_var, width=8).grid(row=1, column=1, sticky="w", pady=4)

        ttk.Label(frm, text="Start Verse:").grid(row=1, column=2, sticky="w", padx=(12,6), pady=4)
        self.start_v_var = tk.IntVar(value=1)
        ttk.Entry(frm, textvariable=self.start_v_var, width=8).grid(row=1, column=3, sticky="w", pady=4)

        # End chapter/verse (optional)
        ttk.Label(frm, text="End Chapter (optional):").grid(row=2, column=0, sticky="w", padx=(0,6), pady=4)
        self.end_ch_var = tk.IntVar(value=0)
        ttk.Entry(frm, textvariable=self.end_ch_var, width=8).grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(frm, text="End Verse (optional):").grid(row=2, column=2, sticky="w", padx=(12,6), pady=4)
        self.end_v_var = tk.IntVar(value=0)
        ttk.Entry(frm, textvariable=self.end_v_var, width=8).grid(row=2, column=3, sticky="w", pady=4)

        # Buttons
        btn_frame = ttk.Frame(frm)
        btn_frame.grid(row=3, column=0, columnspan=4, pady=(10,0))
        ok_btn = ttk.Button(btn_frame, text="Add" if initial_ref is None else "Save", command=self.on_ok)
        ok_btn.pack(side="left", padx=6)
        cancel_btn = ttk.Button(btn_frame, text="Cancel", command=self.on_cancel)
        cancel_btn.pack(side="left", padx=6)

        # Bind Enter/Escape
        self.bind("<Return>", lambda e: self.on_ok())
        self.bind("<Escape>", lambda e: self.on_cancel())

        # If editing, populate fields from initial_ref
        if initial_ref is not None:
            try:
                # set book by matching name
                book_name = getattr(initial_ref.book, "name", str(initial_ref.book))
                if book_name in book_names:
                    self.book_combo.set(book_name)
                else:
                    # fallback: try partial match
                    for bn in book_names:
                        if bn.lower().startswith(book_name.lower()):
                            self.book_combo.set(bn)
                            break
                self.start_ch_var.set(initial_ref.start_chapter)
                self.start_v_var.set(initial_ref.start_verse)
                # If end values are present and different, set them; otherwise leave as 0 to indicate same
                if getattr(initial_ref, "end_chapter", None) and initial_ref.end_chapter != initial_ref.start_chapter:
                    self.end_ch_var.set(initial_ref.end_chapter)
                else:
                    self.end_ch_var.set(0)
                if getattr(initial_ref, "end_verse", None) and initial_ref.end_verse != initial_ref.start_verse:
                    self.end_v_var.set(initial_ref.end_verse)
                else:
                    self.end_v_var.set(0)
            except Exception:
                pass

        # Ensure layout computed and set a sensible size before showing
        self.update_idletasks()
        req_w = max(self.winfo_reqwidth(), 420)
        req_h = max(self.winfo_reqheight(), 160)
        try:
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            x = px + (pw // 2) - (req_w // 2)
            y = py + (ph // 2) - (req_h // 2)
            self.geometry(f"{req_w}x{req_h}+{max(0, x)}+{max(0, y)}")
        except Exception:
            self.geometry(f"{req_w}x{req_h}")
        try:
            self.minsize(req_w, req_h)
        except Exception:
            pass

        # Make modal and on-top
        try:
            self.transient(parent)
            self.grab_set()
            self.lift()
            self.focus_force()
            self.attributes("-topmost", True)
            self.after(50, lambda: self.attributes("-topmost", True))
        except Exception:
            pass

        self.update_idletasks()  # Ensure layout is calculated
        w = self.winfo_width()
        h = self.winfo_height()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.deiconify()         # Show the window now that it's ready
        self.lift()              # Bring to front
        self.focus_force()       # Grab focus
        # Wait for dialog to close
        self.wait_window(self)

    def on_ok(self):
        book_name = self.book_var.get().strip()
        if not book_name:
            messagebox.showwarning("Missing book", "Please select a book.")
            return

        try:
            start_ch = int(self.start_ch_var.get())
            start_v = int(self.start_v_var.get())
        except Exception:
            messagebox.showwarning("Invalid start", "Start chapter and verse must be integers.")
            return

        try:
            end_ch = int(self.end_ch_var.get())
        except Exception:
            end_ch = 0
        try:
            end_v = int(self.end_v_var.get())
        except Exception:
            end_v = 0

        if end_ch == 0:
            end_ch = start_ch
        if end_v == 0:
            end_v = start_v

        # Resolve book enum from selected name
        book_enum = None
        for b in bible.Book:
            if getattr(b, "name", "") == book_name:
                book_enum = b
                break
        if book_enum is None:
            messagebox.showerror("Invalid book", f"Could not resolve book '{book_name}'.")
            return

        try:
            ref = bible.NormalizedReference(book_enum, start_ch, start_v, end_ch, end_v, None)
        except Exception as e:
            messagebox.showerror("Invalid reference", f"Could not create reference: {e}")
            return

        self.result = ref
        self.destroy()

    def on_cancel(self):
        self.result = None
        self.destroy()
