# scripts/quiz_menu.py
import random
import re
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import pythonbible as bible
from pythonbible import InvalidVerseError, get_verse_id, get_verse_text

from scripts.sheath import Sheath
from scripts.ui_common import MinSizeMixin
from difflib import SequenceMatcher


def _clean_text(s: str) -> str:
    if s is None:
        return ""
    s = re.sub(r"[^\w\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s.lower()


class QuizMenu(ttk.Frame, MinSizeMixin):
    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller
        self.sheath = Sheath("resources/verses.csv")

        # Outer container fills the frame
        outer = ttk.Frame(self)
        outer.pack(expand=True, fill="both")

        # Configure grid so row 1 (content) is centered
        outer.grid_rowconfigure(0, weight=1)  # top spacer
        outer.grid_rowconfigure(1, weight=0)  # content row
        outer.grid_rowconfigure(2, weight=1)  # bottom spacer
        outer.grid_columnconfigure(0, weight=1)

        # Content frame in the middle
        content = ttk.Frame(outer)
        content.grid(row=1, column=0)

        # Header
        ttk.Label(content, text="Quiz", font=("Arial", 30)).pack(pady=(12, 6))

        # Start button
        self.start_btn = ttk.Button(content, text="Start Quiz", command=self.start_quiz)
        self.start_btn.pack(pady=(0, 10))

        # Reference label
        self.ref_var = tk.StringVar(value="")
        self.ref_label = ttk.Label(content, textvariable=self.ref_var, font=("Arial", 12, "bold"))
        self.ref_label.pack(pady=6)
        self.ref_label.pack_forget()

        # Answer text with scrollbar
        text_frame = ttk.Frame(content)
        text_frame.pack(pady=6)
        self.answer_text = tk.Text(text_frame, height=8, wrap="word", undo=True)
        self.answer_text.pack(side="left", fill="x", expand=True)
        self.answer_text.bind("<KeyRelease>", self._on_text_change)
        self.answer_text.bind("<Control-a>", lambda e: self._select_all(e))
        self.answer_text.bind("<Control-A>", lambda e: self._select_all(e))
        self.answer_text.bind("<Control-c>", lambda e: "break")  # disable copy

        self._text_scroll = ttk.Scrollbar(text_frame, orient="vertical", command=self.answer_text.yview)
        self.answer_text.config(yscrollcommand=self._text_scroll.set)
        self._text_scroll.pack_forget()

        # Buttons
        self.submit_btn = ttk.Button(content, text="Submit", command=self._on_submit)
        self.submit_btn.pack(pady=6)
        self.submit_btn.pack_forget()

        self.fav_btn = ttk.Button(content, text="Mark Favorite", command=self._toggle_favorite)
        self.fav_btn.pack(pady=6)
        self.fav_btn.pack_forget()

        self.another_btn = ttk.Button(content, text="Another Verse", command=self._another_verse)
        self.another_btn.pack(pady=6)
        self.another_btn.pack_forget()

        self.result_var = tk.StringVar(value="")
        self.result_label = ttk.Label(content, textvariable=self.result_var, wraplength=700, justify="left")
        self.result_label.pack(pady=6)

        self.try_again_btn = ttk.Button(content, text="Try Again", command=self._try_again)
        self.try_again_btn.pack(pady=6)
        self.try_again_btn.pack_forget()

        self.return_btn = ttk.Button(content, text="Return to Main Menu", command=self._return_to_main)
        self.return_btn.pack(pady=6)
        self.return_btn.pack_forget()

        # State
        self.current_ref = None
        self.current_canonical = ""
        self._max_text_height = 18
        self._canonical_ready = False
        self._canonical_lock = threading.Lock()
        self._canonical_job_id = 0
        self._max_canonical_chars = 8000
        self._last_score = 0

        self.winfo_toplevel().bind("<Escape>", lambda e: self._return_to_main() if self._last_score >= 75 else None)
        self.enforce_minsize()


    # ----------------- UI helpers -----------------
    def _select_all(self, event):
        try:
            self.answer_text.tag_add("sel", "1.0", "end")
        except Exception:
            pass
        return "break"

    def _on_text_change(self, event=None):
        last_index = self.answer_text.index("end-1c")
        lines = int(last_index.split(".")[0])
        new_height = max(8, min(self._max_text_height, lines))
        self.answer_text.configure(height=new_height)

        if lines >= self._max_text_height:
            if not self._text_scroll.winfo_ismapped():
                self._text_scroll.pack(side="right", fill="y")
        else:
            if self._text_scroll.winfo_ismapped():
                self._text_scroll.pack_forget()

    def _strip_punct(self, s: str) -> str:
        """Return string with punctuation removed for comparison (keeps letters/numbers)."""
        if s is None:
            return ""
        return re.sub(r"[^\w\s]", "", s).lower()

    def _tokenize_for_diff(self, text: str):
        """
        Tokenize text into words, punctuation, and whitespace tokens.
        Use a raw regex string to avoid SyntaxWarning.
        """
        if text is None:
            return []
        # raw string to avoid invalid escape sequence warnings
        tokens = re.findall(r'(\w+|[^\w\s]|\s+)', text)
        return tokens
    

    def _annotate_in_text_widget(self, canonical: str, user_attempt: str):
        """
        Robust, defensive annotation:
        - punctuation/case-only differences -> 'cap' (yellow)
        - character-level differences -> 'wrong' (red overstrike) + 'added' (red)
        - omitted canonical tokens -> 'added'
        - extra user tokens -> 'wrong'
        This version carefully bounds all index accesses and always advances
        canon_pos/user_pos so it cannot loop forever.
        """
        # Make editable and clear
        try:
            self.answer_text.config(state="normal")
        except Exception:
            pass
        self.answer_text.delete("1.0", "end")

        # Tag styles
        self.answer_text.tag_configure("wrong", foreground="red", overstrike=1)
        self.answer_text.tag_configure("added", foreground="red")
        self.answer_text.tag_configure("cap", background="yellow")
        self.answer_text.tag_configure("normal", foreground="black")

        # Tokenize
        canon_tokens = self._tokenize_for_diff(canonical)
        user_tokens = self._tokenize_for_diff(user_attempt)

        # Build word lists (skip punctuation-only tokens for matching)
        def build_word_list(tokens):
            words = []
            idx_map = []
            for i, t in enumerate(tokens):
                if t.isspace():
                    continue
                if re.fullmatch(r'[^\w\s]', t):
                    continue
                words.append(t)
                idx_map.append(i)
            return words, idx_map

        canon_words, canon_map = build_word_list(canon_tokens)
        user_words, user_map = build_word_list(user_tokens)

        sm = SequenceMatcher(None, canon_words, user_words)

        canon_pos = 0   # index into canon_tokens
        user_pos = 0    # index into user_tokens

        def insert_token(tok, tag=None):
            if not tok:
                return
            start = self.answer_text.index("end-1c")
            self.answer_text.insert("end", tok)
            end = self.answer_text.index("end-1c")
            if tag:
                try:
                    self.answer_text.tag_add(tag, start, end)
                except Exception:
                    pass

        def insert_intervening(from_idx, to_idx, tokens):
            # Insert tokens[from_idx:to_idx] safely
            if from_idx < 0:
                from_idx = 0
            if to_idx > len(tokens):
                to_idx = len(tokens)
            for i in range(from_idx, to_idx):
                insert_token(tokens[i])
            return to_idx

        # Character-level annotate helper
        def annotate_token_chars(canon_tok, user_tok):
            if user_tok is None:
                insert_token(canon_tok, "added")
                return

            # punctuation/case-only difference -> cap
            if self._strip_punct(user_tok) == self._strip_punct(canon_tok) and user_tok != canon_tok:
                insert_token(canon_tok, "cap")
                return

            # char-level diff
            char_sm = SequenceMatcher(None, user_tok, canon_tok)
            for op, a0, a1, b0, b1 in char_sm.get_opcodes():
                if op == "equal":
                    insert_token(canon_tok[b0:b1], "normal")
                elif op == "replace":
                    # user chars crossed out, canonical chars added
                    if a0 < a1:
                        insert_token(user_tok[a0:a1], "wrong")
                    if b0 < b1:
                        insert_token(canon_tok[b0:b1], "added")
                elif op == "delete":
                    # user had extra chars
                    insert_token(user_tok[a0:a1], "wrong")
                elif op == "insert":
                    # canonical has extra chars
                    insert_token(canon_tok[b0:b1], "added")

        # Walk opcodes safely
        try:
            for opcode, a0, a1, b0, b1 in sm.get_opcodes():
                if opcode == "equal":
                    for wi in range(a0, a1):
                        if wi >= len(canon_map):
                            break
                        tok_index = canon_map[wi]
                        canon_pos = insert_intervening(canon_pos, tok_index, canon_tokens)
                        # find corresponding user token index safely
                        user_index_in_map = b0 + (wi - a0)
                        user_tok = ""
                        if 0 <= user_index_in_map < len(user_map):
                            user_tok_index = user_map[user_index_in_map]
                            user_tok = user_tokens[user_tok_index] if 0 <= user_tok_index < len(user_tokens) else ""
                        canon_tok = canon_tokens[canon_pos] if canon_pos < len(canon_tokens) else ""
                        if self._strip_punct(user_tok) == self._strip_punct(canon_tok) and user_tok != canon_tok:
                            insert_token(canon_tok, "cap")
                        else:
                            insert_token(canon_tok, "normal")
                        canon_pos += 1
                        # advance user_pos to at least after the user token we consumed
                        if 0 <= user_index_in_map < len(user_map):
                            user_pos = max(user_pos, user_map[user_index_in_map] + 1)
                elif opcode == "replace":
                    # pair up tokens as much as possible, but bound indices
                    pair_count = max(a1 - a0, b1 - b0)
                    for i in range(pair_count):
                        # canonical token (if exists)
                        canon_tok = None
                        if a0 + i < a1 and (a0 + i) < len(canon_map):
                            canon_tok_index = canon_map[a0 + i]
                            canon_pos = insert_intervening(canon_pos, canon_tok_index, canon_tokens)
                            if canon_pos < len(canon_tokens):
                                canon_tok = canon_tokens[canon_pos]
                        # user token (if exists)
                        user_tok = None
                        if b0 + i < b1 and (b0 + i) < len(user_map):
                            user_tok_index = user_map[b0 + i]
                            if 0 <= user_tok_index < len(user_tokens):
                                user_tok = user_tokens[user_tok_index]
                        # annotate
                        if canon_tok is not None and user_tok is not None:
                            annotate_token_chars(canon_tok, user_tok)
                            canon_pos += 1
                            user_pos = max(user_pos, (user_tok_index or 0) + 1)
                        elif canon_tok is not None and user_tok is None:
                            insert_token(canon_tok, "added")
                            canon_pos += 1
                        elif canon_tok is None and user_tok is not None:
                            insert_token(user_tok, "wrong")
                            user_pos = max(user_pos, (user_tok_index or 0) + 1)
                    # any extra user tokens in this replace block -> crossed out
                    for uj in range(b0 + pair_count, b1):
                        if uj < len(user_map):
                            uidx = user_map[uj]
                            if 0 <= uidx < len(user_tokens):
                                insert_token(user_tokens[uidx], "wrong")
                                user_pos = max(user_pos, uidx + 1)
                elif opcode == "delete":
                    for wi in range(a0, a1):
                        if wi >= len(canon_map):
                            break
                        canon_tok_index = canon_map[wi]
                        canon_pos = insert_intervening(canon_pos, canon_tok_index, canon_tokens)
                        if canon_pos < len(canon_tokens):
                            insert_token(canon_tokens[canon_pos], "added")
                            canon_pos += 1
                elif opcode == "insert":
                    for uj in range(b0, b1):
                        if uj >= len(user_map):
                            break
                        uidx = user_map[uj]
                        if 0 <= uidx < len(user_tokens):
                            insert_token(user_tokens[uidx], "wrong")
                            user_pos = max(user_pos, uidx + 1)
        except Exception:
            # If anything unexpected happens, fall back to inserting canonical text plainly
            insert_token(canonical, "added")

        # Insert any remaining canonical tokens
        canon_pos = insert_intervening(canon_pos, len(canon_tokens), canon_tokens)

        # Leave widget editable and place cursor at end
        try:
            self.answer_text.config(state="normal")
            self.answer_text.mark_set("insert", "end-1c")
            self.answer_text.see("insert")
        except Exception:
            pass

    # ----------------- Quiz flow -----------------
    def start_quiz(self):
        try:
            passages = self.sheath.getPassages()
            if not passages:
                messagebox.showwarning("No verses", "No verses found in the verses file.")
                return
            self.current_ref = random.choice(passages)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load verses: {e}")
            return

        # Prepare UI for a fresh attempt
        self._show_quiz_controls(show_submit_only=True)
        # Clear previous canonical and start background fetch
        with self._canonical_lock:
            self.current_canonical = ""
            self._canonical_ready = False
        self._load_canonical_async()
        # Hide start button (no restart)
        self.start_btn.pack_forget()

        root = self.winfo_toplevel()
        root.attributes("-fullscreen", True)
        try:
            root.protocol("WM_DELETE_WINDOW", lambda: None)  # disable close
        except:
            pass

    def _show_quiz_controls(self, show_submit_only=False):
        # Ensure the text widget is editable before clearing/using it
        try:
            self.answer_text.config(state="normal")
        except Exception:
            pass

        self.ref_var.set(self._format_ref_label(self.current_ref))
        self.ref_label.pack()
        self.answer_text.pack(side="left", fill="x", expand=True)
        # Clear any previous content and reset height
        self.answer_text.delete("1.0", "end")
        self._on_text_change()
        self.answer_text.focus_set()

        # Submit is visible immediately
        self.submit_btn.pack()

        # Favorite and Another only after submit
        if show_submit_only:
            self.fav_btn.pack_forget()
            self.another_btn.pack_forget()
        else:
            self.fav_btn.pack()
            self.another_btn.pack()

        self.result_var.set("")
        self._update_fav_button_label()


    def _format_ref_label(self, ref):
        try:
            book_name = getattr(ref.book, "name", str(ref.book))
            start = f"{book_name} {ref.start_chapter}:{ref.start_verse}"
            if getattr(ref, "end_chapter", None) and getattr(ref, "end_verse", None):
                if (ref.end_chapter != ref.start_chapter) or (ref.end_verse != ref.start_verse):
                    end = f"{ref.end_chapter}:{ref.end_verse}"
                    return f"{start} - {end}"
            return start
        except Exception:
            return "Unknown Reference"

    def _get_full_range_text(self, ref):
        """
        Return the concatenated verse text for the full range described by `ref`.
        Handles single-verse, multi-verse, and multi-chapter ranges by advancing
        chapter/verse until the end reference is reached or no further verses exist.
        """
        if ref is None:
            return ""

        texts = []
        book = ref.book
        ch = int(ref.start_chapter)
        v = int(ref.start_verse)
        end_ch = int(getattr(ref, "end_chapter", ref.start_chapter))
        end_v = int(getattr(ref, "end_verse", ref.start_verse))

        # Defensive: ensure end is not before start; if it is, treat as single verse
        try:
            if (end_ch < ch) or (end_ch == ch and end_v < v):
                end_ch, end_v = ch, v
        except Exception:
            end_ch, end_v = ch, v

        # Iterate from start to end inclusive
        while True:
            try:
                vid = get_verse_id(book, ch, v)
                verse_text = get_verse_text(vid) or ""
                texts.append(verse_text)
            except InvalidVerseError:
                # If verse number invalid in this chapter, try next chapter starting at verse 1
                ch += 1
                v = 1
                # Check whether next chapter exists by attempting verse 1; if not, stop
                try:
                    _ = get_verse_id(book, ch, 1)
                except Exception:
                    break
                # continue loop to attempt verse 1 of next chapter
                continue
            except Exception:
                # Any other error: stop collecting further verses
                break

            # If we've reached the requested end verse, stop
            if ch == end_ch and v == end_v:
                break

            # Advance to next verse
            v += 1
            # If next verse doesn't exist in this chapter, the next loop iteration will
            # catch InvalidVerseError and advance chapter/verse accordingly.

        # Join verses with a space so matching works across verse boundaries
        return " ".join(t for t in texts if t)

    def _fetch_canonical_text(self):
        """
        Fetch and store the cleaned canonical text for the current reference.
        Uses the full range if start != end.
        """
        try:
            full_text = self._get_full_range_text(self.current_ref)
        except Exception:
            full_text = ""

        # Clean and store for comparison
        self.current_canonical = _clean_text(full_text)

    def _on_submit(self):
        if not self.current_ref:
            messagebox.showwarning("No reference", "Start a quiz first.")
            return

        # Ensure canonical is ready
        with self._canonical_lock:
            ready = self._canonical_ready

        if not ready:
            self.result_var.set("Still loading verse text — please wait a moment and try Submit again.")
            return

        # Get user input and cleaned form
        user_text = self.answer_text.get("1.0", "end-1c")
        cleaned = _clean_text(user_text)
        if not cleaned:
            self.result_var.set("Please enter your attempt before submitting.")
            return

        # Compute similarity
        ratio = SequenceMatcher(None, self.current_canonical, cleaned).ratio()
        percent = int(ratio * 100)

        if percent >= 95:
            msg = f"Excellent! Similarity: {percent}%."
        elif percent >= 75:
            msg = f"Good! Similarity: {percent}%."
        else:
            msg = f"Keep practicing to get above a 75%. Similarity: {percent}%."

        self._last_score = percent

        # Hide Submit until user presses Try Again
        self.submit_btn.pack_forget()
        self.try_again_btn.pack()

        if percent >= 75:
            root = self.winfo_toplevel()
            root.attributes("-fullscreen", False)
            root.protocol("WM_DELETE_WINDOW", root.destroy)
            self.fav_btn.pack()
            self.another_btn.pack()
            self.return_btn.pack()
        else:
            self.fav_btn.pack_forget()
            self.another_btn.pack_forget()
            self.return_btn.pack_forget()



        # ----------------- Defensive annotator call (step 5) -----------------
        # Build full canonical (non-cleaned) for annotation and display, but truncate to safe size
        try:
            full_text = self._get_full_range_text(self.current_ref) or "(no text available)"
        except Exception:
            full_text = "(no text available)"

        # Truncate to avoid extremely long diffs that can freeze the UI
        if len(full_text) > self._max_canonical_chars:
            truncated = full_text[: self._max_canonical_chars] + " ..."
        else:
            truncated = full_text

        # Try to annotate; if annotation fails, fall back to showing canonical in the result label
        try:
            self._annotate_in_text_widget(truncated, user_text)
        except Exception as e:
            # Fallback: show canonical text in the result area and keep UI responsive
            self.result_var.set(msg + f"\n\nCanonical: {full_text}")
            # Reveal favorite and another buttons anyway
            self.fav_btn.pack()
            self.another_btn.pack()
            self._update_fav_button_label()
            return

        # If annotation succeeded, show the short feedback message and reveal post-submit controls
        self.result_var.set(msg)
        
        self._update_fav_button_label()

        self.enforce_minsize()

    def _try_again(self):
        # Clear the text field
        try:
            self.answer_text.config(state="normal")
        except Exception:
            pass
        self.answer_text.delete("1.0", "end")
        self._on_text_change()
        self.answer_text.focus_set()

        # Reset feedback
        self.result_var.set("")

        # Hide Try Again, show Submit again
        self.try_again_btn.pack_forget()
        self.submit_btn.pack()

    def _load_canonical_async(self):
        """
        Start a background fetch for the canonical text for the current_ref.
        Uses a job id so only the latest fetch result is accepted.
        Disables Submit until the fetch completes.
        """
        # increment job id and capture locally
        with self._canonical_lock:
            self._canonical_job_id += 1
            job_id = self._canonical_job_id
            self._canonical_ready = False

        # disable submit while loading and show loading message
        try:
            self.submit_btn.config(state="disabled")
        except Exception:
            pass
        self.result_var.set("Loading verse text...")

        def worker(ref, jid):
            try:
                full_text = self._get_full_range_text(ref) or ""
            except Exception:
                full_text = ""

            # Truncate to safe size to avoid huge diffs
            if len(full_text) > self._max_canonical_chars:
                full_text = full_text[: self._max_canonical_chars] + " ..."

            # Only accept result if job id still current
            with self._canonical_lock:
                if jid != self._canonical_job_id:
                    return
                self.current_canonical = _clean_text(full_text)
                self._canonical_ready = True

            # Re-enable submit on the main thread
            try:
                self.submit_btn.after(0, lambda: self.submit_btn.config(state="normal"))
                # Clear any loading message
                self.submit_btn.after(0, lambda: self.result_var.set(""))
            except Exception:
                pass

        threading.Thread(target=worker, args=(self.current_ref, job_id), daemon=True).start()

    def _another_verse(self):
        try:
            passages = self.sheath.getPassages()
            if not passages:
                messagebox.showwarning("No verses", "No verses found.")
                return
            if len(passages) == 1:
                self.current_ref = passages[0]
            else:
                new_ref = self.current_ref
                attempts = 0
                while new_ref == self.current_ref and attempts < 10:
                    new_ref = random.choice(passages)
                    attempts += 1
                self.current_ref = new_ref
        except Exception as e:
            messagebox.showerror("Error", f"Could not load verses: {e}")
            return

        # Make sure the text widget is editable and cleared for the new attempt
        try:
            self.answer_text.config(state="normal")
        except Exception:
            pass
        self.answer_text.delete("1.0", "end")
        self._on_text_change()

        # Prepare UI and fetch canonical for the new ref
        self._show_quiz_controls(show_submit_only=True)
        with self._canonical_lock:
            self.current_canonical = ""
            self._canonical_ready = False
        self._load_canonical_async()
        self.try_again_btn.pack_forget()



    # ----------------- Favorite handling -----------------
    def _update_fav_button_label(self):
        if not self.current_ref:
            self.fav_btn.config(text="Mark Favorite")
            return
        try:
            rows = self.sheath.findPassages([self.current_ref])
            if rows:
                with open(self.sheath.filename, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                line_idx = rows[0] + 1
                if 0 <= line_idx < len(lines):
                    parts = lines[line_idx].rstrip("\n").split(",")
                    current_status = parts[7].strip() if len(parts) > 7 else "False"
                    if current_status == "True":
                        self.fav_btn.config(text="Unmark Favorite")
                        return
        except Exception:
            pass
        self.fav_btn.config(text="Mark Favorite")

    def _toggle_favorite(self):
        if not self.current_ref:
            messagebox.showwarning("No reference", "Start a quiz first.")
            return
        try:
            rows = self.sheath.findPassages([self.current_ref])
            if not rows:
                messagebox.showerror("Error", "Could not locate the verse in the CSV.")
                return
            with open(self.sheath.filename, "r", encoding="utf-8") as f:
                lines = f.readlines()
            line_idx = rows[0] + 1
            parts = lines[line_idx].rstrip("\n").split(",")
            current_status = parts[7].strip() if len(parts) > 7 else "False"

            if current_status == "True":
                self.sheath.unsetFavorites([self.current_ref])
            else:
                self.sheath.setFavorites([self.current_ref])

            self._update_fav_button_label()
        except Exception as e:
            messagebox.showerror("Error", f"Could not toggle favorite: {e}")

    def _try_again(self):
        try:
            self.answer_text.config(state="normal")
        except Exception:
            pass
        self.answer_text.delete("1.0", "end")
        self._on_text_change()
        self.answer_text.focus_set()
        self.result_var.set("")
        self.submit_btn.pack()
        self.try_again_btn.pack_forget()

    def _return_to_main(self):
        root = self.winfo_toplevel()
        root.attributes("-fullscreen", False)
        self.controller.show_frame("MainMenu")