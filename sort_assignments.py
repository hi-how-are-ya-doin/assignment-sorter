import os
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import time
import json
from datetime import datetime

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False

# ── CONFIG ────────────────────────────────────────────────────────────────────

CONFIG_PATH  = os.path.expanduser("~/.assignment_sorter.json")
HISTORY_PATH = os.path.expanduser("~/.assignment_sorter_history.json")

DEFAULT_CLASSES = {
    "Biology":    ["bio", "biology", "cell", "genetics"],
    "Math":       ["math", "calc", "algebra", "geometry", "statistics"],
    "Politics":   ["politics", "policy", "government", "congress"],
    "Business":   ["business", "biz", "econ", "economics"],
    "English":    ["english", "essay", "lit", "writing"],
    "Accounting": ["accounting", "ledger", "balance", "journal"],
}
DEFAULT_TYPES = {
    "Homework":   ["hw", "homework", "assignment"],
    "Notes":      ["note", "notes", "lecture"],
    "Quiz":       ["quiz", "quizzes"],
    "Exam":       ["exam", "test", "midterm", "final"],
    "Lab":        ["lab", "experiment"],
    "Project":    ["project", "presentation", "slides"],
    "Discussion": ["discussion", "db", "board", "reflection"],
    "Syllabus":   ["syllabus"],
}
EXT_FALLBACK = {
    "PDFs":        [".pdf"],
    "Documents":   [".doc", ".docx", ".odt", ".rtf", ".txt"],
    "Spreadsheets":[".xls", ".xlsx", ".csv"],
    "Slides":      [".ppt", ".pptx"],
    "Photos":      [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic", ".bmp"],
    "Videos":      [".mp4", ".mov", ".avi", ".mkv", ".webm"],
    "Audio":       [".mp3", ".wav", ".flac", ".aac", ".ogg"],
    "Archives":    [".zip", ".tar", ".gz", ".rar", ".7z"],
    "Code":        [".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".sh"],
}

def load_config():
    defaults = {
        "classes":      DEFAULT_CLASSES.copy(),
        "types":        DEFAULT_TYPES.copy(),
        "watch_folder": "",
        "output_folder":"",
        "auto_watch":   False,
        "theme":        "dark",
    }
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                data = json.load(f)
                defaults.update(data)
        except Exception:
            pass
    return defaults

def save_config(data):
    with open(CONFIG_PATH, "w") as f:
        json.dump(data, f, indent=2)

def load_history():
    if os.path.exists(HISTORY_PATH):
        try:
            with open(HISTORY_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(history):
    with open(HISTORY_PATH, "w") as f:
        json.dump(history[-500:], f, indent=2)

# ── DETECTION ─────────────────────────────────────────────────────────────────

def keyword_detect(filename, kw_dict):
    name = filename.lower()
    for key, kws in kw_dict.items():
        if any(k.lower() in name for k in kws):
            return key
    return None

def ext_detect(filename):
    ext = os.path.splitext(filename)[1].lower()
    for folder, exts in EXT_FALLBACK.items():
        if ext in exts:
            return folder
    return "Other"

def move_file(src_path, output_folder, classes, types):
    filename = os.path.basename(src_path)
    if filename.startswith(".") or filename.endswith((".crdownload", ".tmp", ".part")):
        return None
    cls = keyword_detect(filename, classes)
    typ = keyword_detect(filename, types)
    used_ext = False
    if cls is None:
        cls = ext_detect(filename)
        used_ext = True
    typ = typ or "Misc"
    dest_dir = os.path.join(output_folder, cls, typ)
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, filename)
    if os.path.exists(dest):
        base, ext = os.path.splitext(filename)
        dest = os.path.join(dest_dir, f"{base}_copy{ext}")
    shutil.copy2(src_path, dest)
    return (filename, cls, typ, used_ext, dest)

# ── WATCHDOG ──────────────────────────────────────────────────────────────────

class DownloadHandler(FileSystemEventHandler):
    def __init__(self, output_folder, callback, get_dicts):
        self.output_folder = output_folder
        self.callback      = callback
        self.get_dicts     = get_dicts

    def on_created(self, event):
        if event.is_directory: return
        time.sleep(1.5)
        try:
            classes, types = self.get_dicts()
            result = move_file(event.src_path, self.output_folder, classes, types)
            if result:
                self.callback(result, "auto")
        except Exception as e:
            self.callback(None, "error", str(e))

# ── COLORS ────────────────────────────────────────────────────────────────────

C = {
    "bg":       "#080b10",
    "surface":  "#0e1117",
    "card":     "#131820",
    "border":   "#1e2535",
    "glow":     "#1a2540",
    "accent":   "#4f9eff",
    "accent2":  "#7bb8ff",
    "green":    "#2ea84a",
    "green2":   "#4ec76a",
    "orange":   "#e8933a",
    "orange2":  "#f5a85a",
    "red":      "#e8453a",
    "red2":     "#ff6b5a",
    "purple":   "#9d6fff",
    "purple2":  "#b48fff",
    "teal":     "#2eb8a0",
    "teal2":    "#4ed4be",
    "text":     "#dce8f5",
    "muted":    "#7a8ba0",
    "dim":      "#3a4a5a",
}

# ── MANAGE WINDOW ─────────────────────────────────────────────────────────────

class ManageWindow(tk.Toplevel):
    def __init__(self, parent, classes, types, on_save):
        super().__init__(parent)
        self.title("Manage Folders & Keywords")
        self.geometry("680x600")
        self.configure(bg=C["bg"])
        self.resizable(False, False)
        self.classes = {k: list(v) for k, v in classes.items()}
        self.types   = {k: list(v) for k, v in types.items()}
        self.on_save = on_save
        self._build()

    def _build(self):
        hdr = tk.Frame(self, bg=C["glow"], height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="⚙  Manage Folders & Keywords",
                 font=("Helvetica Neue", 13, "bold"),
                 fg=C["text"], bg=C["glow"]).pack(side="left", padx=20, pady=12)

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        cols = tk.Frame(self, bg=C["bg"])
        cols.pack(fill="both", expand=True, padx=20, pady=14)
        self._section(cols, "📚  Class Folders", self.classes, C["accent"], "left")
        tk.Frame(cols, bg=C["border"], width=1).pack(side="left", fill="y", padx=14)
        self._section(cols, "📝  Assignment Types", self.types, C["purple"], "left")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")
        foot = tk.Frame(self, bg=C["surface"])
        foot.pack(fill="x", padx=20, pady=12)
        tk.Button(foot, text="Cancel", font=("Helvetica Neue", 9),
                  fg=C["muted"], bg=C["card"], relief="flat",
                  padx=14, pady=7, cursor="hand2", bd=0,
                  command=self.destroy).pack(side="right", padx=(8, 0))
        tk.Button(foot, text="✓  Save Changes",
                  font=("Helvetica Neue", 10, "bold"),
                  fg="white", bg=C["green"], activebackground=C["green2"],
                  relief="flat", padx=16, pady=8, cursor="hand2", bd=0,
                  command=self._save).pack(side="right")

    def _section(self, parent, title, data_dict, accent, side):
        frame = tk.Frame(parent, bg=C["bg"])
        frame.pack(side=side, fill="both", expand=True)
        tk.Label(frame, text=title, font=("Helvetica Neue", 10, "bold"),
                 fg=accent, bg=C["bg"]).pack(anchor="w", pady=(0, 6))

        lb_wrap = tk.Frame(frame, bg=C["border"])
        lb_wrap.pack(fill="x")
        lb = tk.Listbox(lb_wrap, bg=C["card"], fg=C["text"], font=("Menlo", 9),
                        relief="flat", bd=0, selectbackground=C["glow"],
                        selectforeground=accent, height=9, activestyle="none")
        lb.pack(fill="x", padx=1, pady=1)
        for key in data_dict:
            lb.insert("end", key)

        kw_label = tk.Label(frame, text="Select a folder to view keywords",
                            font=("Helvetica Neue", 8), fg=C["dim"], bg=C["bg"],
                            wraplength=250, justify="left")
        kw_label.pack(anchor="w", pady=(5, 2))

        def on_select(e):
            sel = lb.curselection()
            if sel:
                key = lb.get(sel[0])
                kws = data_dict.get(key, [])
                kw_label.configure(
                    text=f"Keywords: {', '.join(kws)}" if kws else "Keywords: (none yet)")
        lb.bind("<<ListboxSelect>>", on_select)

        def add_row(lbl):
            tk.Label(frame, text=lbl, font=("Helvetica Neue", 8),
                     fg=C["muted"], bg=C["bg"]).pack(anchor="w", pady=(8, 2))
            row = tk.Frame(frame, bg=C["bg"])
            row.pack(fill="x")
            ef = tk.Frame(row, bg=C["border"])
            ef.pack(side="left", fill="x", expand=True, padx=(0, 4))
            var = tk.StringVar()
            e = tk.Entry(ef, textvariable=var, font=("Menlo", 9),
                         bg=C["card"], fg=C["text"], relief="flat",
                         insertbackground=accent, bd=0)
            e.pack(fill="x", padx=1, pady=1, ipady=5)
            return row, var, e

        row1, name_var, name_e = add_row("New folder name:")
        def add_item(e=None):
            name = name_var.get().strip()
            if not name: return
            if name in data_dict:
                messagebox.showwarning("Duplicate", f'"{name}" already exists.', parent=self)
                return
            data_dict[name] = []
            lb.insert("end", name)
            name_var.set("")
            lb.selection_clear(0, "end")
            lb.selection_set("end")
            lb.see("end")
            kw_label.configure(text="Keywords: (none yet)")
        name_e.bind("<Return>", add_item)
        tk.Button(row1, text="+", font=("Helvetica Neue", 12, "bold"),
                  fg="white", bg=accent, activebackground=accent,
                  relief="flat", padx=9, pady=3, cursor="hand2", bd=0,
                  command=add_item).pack(side="left")

        row2, kw_var, kw_e = add_row("Add keyword to selected:")
        def add_keyword(e=None):
            sel = lb.curselection()
            if not sel:
                messagebox.showwarning("No Selection", "Select a folder first.", parent=self)
                return
            kw = kw_var.get().strip().lower()
            if not kw: return
            key = lb.get(sel[0])
            if kw not in data_dict[key]:
                data_dict[key].append(kw)
            kw_label.configure(text=f"Keywords: {', '.join(data_dict[key])}")
            kw_var.set("")
        kw_e.bind("<Return>", add_keyword)
        tk.Button(row2, text="+", font=("Helvetica Neue", 12, "bold"),
                  fg="white", bg=accent, activebackground=accent,
                  relief="flat", padx=9, pady=3, cursor="hand2", bd=0,
                  command=add_keyword).pack(side="left")

        def delete_item():
            sel = lb.curselection()
            if not sel: return
            key = lb.get(sel[0])
            if messagebox.askyesno("Delete", f'Remove "{key}"?', parent=self):
                del data_dict[key]
                lb.delete(sel[0])
                kw_label.configure(text="Select a folder to view keywords")
        tk.Button(frame, text="🗑  Delete Selected",
                  font=("Helvetica Neue", 8), fg=C["red"], bg=C["bg"],
                  activeforeground=C["red2"], activebackground=C["bg"],
                  relief="flat", padx=0, pady=4, cursor="hand2", bd=0,
                  command=delete_item).pack(anchor="w", pady=(6, 0))

    def _save(self):
        self.on_save(self.classes, self.types)
        self.destroy()

# ── HISTORY WINDOW ────────────────────────────────────────────────────────────

class HistoryWindow(tk.Toplevel):
    def __init__(self, parent, history, on_clear):
        super().__init__(parent)
        self.title("Sort History")
        self.geometry("660x500")
        self.configure(bg=C["bg"])
        self.resizable(True, True)
        self.on_clear = on_clear
        self._build(history)

    def _build(self, history):
        hdr = tk.Frame(self, bg=C["glow"], height=50)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="🕘  Sort History",
                 font=("Helvetica Neue", 13, "bold"),
                 fg=C["text"], bg=C["glow"]).pack(side="left", padx=20, pady=12)
        tk.Label(hdr, text=f"{len(history)} entries",
                 font=("Helvetica Neue", 9), fg=C["muted"],
                 bg=C["glow"]).pack(side="right", padx=20)

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # Filter bar
        filter_row = tk.Frame(self, bg=C["surface"])
        filter_row.pack(fill="x", padx=20, pady=(10, 0))
        tk.Label(filter_row, text="Filter:", font=("Helvetica Neue", 9),
                 fg=C["muted"], bg=C["surface"]).pack(side="left", padx=(0, 6))
        self.filter_var = tk.StringVar()
        ef = tk.Frame(filter_row, bg=C["border"])
        ef.pack(side="left", fill="x", expand=True)
        filter_entry = tk.Entry(ef, textvariable=self.filter_var,
                                font=("Menlo", 9), bg=C["card"], fg=C["text"],
                                relief="flat", insertbackground=C["accent"], bd=0)
        filter_entry.pack(fill="x", padx=1, pady=1, ipady=5)

        wrap = tk.Frame(self, bg=C["border"])
        wrap.pack(fill="both", expand=True, padx=20, pady=(10, 0))
        inner = tk.Frame(wrap, bg=C["card"])
        inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.txt = tk.Text(inner, bg=C["card"], fg=C["muted"], font=("Menlo", 9),
                           relief="flat", padx=16, pady=12, state="disabled",
                           wrap="word", cursor="arrow")
        self.txt.pack(fill="both", expand=True)
        self.txt.tag_config("ext",    foreground=C["teal"])
        self.txt.tag_config("manual", foreground=C["accent"])
        self.txt.tag_config("auto",   foreground=C["green"])
        self.txt.tag_config("dim",    foreground=C["dim"])

        foot = tk.Frame(self, bg=C["surface"])
        foot.pack(fill="x", padx=20, pady=10)
        tk.Button(foot, text="🗑  Clear History",
                  font=("Helvetica Neue", 9), fg=C["red"], bg=C["card"],
                  activeforeground=C["red2"], activebackground=C["border"],
                  relief="flat", padx=12, pady=6, cursor="hand2", bd=0,
                  command=self._clear).pack(side="left")
        tk.Button(foot, text="Close", font=("Helvetica Neue", 9),
                  fg=C["muted"], bg=C["card"], relief="flat",
                  padx=12, pady=6, cursor="hand2", bd=0,
                  command=self.destroy).pack(side="right")

        self.history = history
        self._render(history)
        self.filter_var.trace_add("write", lambda *_: self._filter())

    def _render(self, entries):
        self.txt.configure(state="normal")
        self.txt.delete("1.0", "end")
        if not entries:
            self.txt.insert("end", "No history yet.", "dim")
        else:
            for entry in reversed(entries):
                tag = entry.get("tag", "manual")
                marker = "  [ext]" if entry.get("ext") else ""
                line = f"[{entry['ts']}]  {entry['file']}  →  {entry['cls']} / {entry['typ']}{marker}\n"
                self.txt.insert("end", line, tag)
        self.txt.configure(state="disabled")

    def _filter(self):
        q = self.filter_var.get().lower()
        filtered = [e for e in self.history
                    if q in e['file'].lower() or q in e['cls'].lower() or q in e['typ'].lower()] if q else self.history
        self._render(filtered)

    def _clear(self):
        if messagebox.askyesno("Clear History", "Delete all sort history?", parent=self):
            self.on_clear()
            self.history = []
            self._render([])

# ── MAIN APP ──────────────────────────────────────────────────────────────────

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Assignment Sorter")
        self.geometry("780x740")
        self.minsize(660, 640)
        self.configure(bg=C["bg"])

        self.cfg = load_config()
        self.classes = self.cfg["classes"]
        self.types   = self.cfg["types"]
        self.history = load_history()

        self.source_var      = tk.StringVar(value=self.cfg.get("watch_folder", ""))
        self.output_var      = tk.StringVar(value=self.cfg.get("output_folder", ""))
        self.auto_watch_var  = tk.BooleanVar(value=self.cfg.get("auto_watch", False))

        self.watch_active = False
        self.observer     = None
        self.total_sorted = 0
        self.ext_sorted   = 0

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._build()

        # Auto-start watch if it was on when last closed
        if self.auto_watch_var.get():
            self.after(600, self._start_watch)

    # ── BUILD ─────────────────────────────────────────────────────────────────

    def _build(self):
        # Header bar
        hdr = tk.Frame(self, bg=C["glow"], height=58)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(hdr, text="📂", font=("Helvetica Neue", 20),
                 fg=C["accent"], bg=C["glow"]).place(x=20, y=14)
        tk.Label(hdr, text="Assignment Sorter",
                 font=("Helvetica Neue", 16, "bold"),
                 fg=C["text"], bg=C["glow"]).place(x=52, y=16)
        self.badge = tk.Label(hdr, text="● IDLE",
                              font=("Helvetica Neue", 9, "bold"),
                              fg=C["dim"], bg=C["glow"])
        self.badge.place(relx=1.0, x=-20, y=22, anchor="ne")

        tk.Frame(self, bg=C["border"], height=1).pack(fill="x")

        # Stat cards
        cards = tk.Frame(self, bg=C["bg"])
        cards.pack(fill="x", padx=18, pady=(14, 0))
        self._stat_card(cards, "📁", "Total Sorted",  "0",   "count",      C["accent"]).pack(side="left", fill="x", expand=True, padx=(0,7))
        self._stat_card(cards, "👁", "Watching",      "Off", "watch_status",C["green"]).pack(side="left", fill="x", expand=True, padx=(0,7))
        self._stat_card(cards, "🔗", "By Extension",  "0",   "ext_count",  C["teal"]).pack(side="left",  fill="x", expand=True, padx=(0,7))
        self._stat_card(cards, "🕘", "This Session",  "0",   "session",    C["purple"]).pack(side="left", fill="x", expand=True)

        # Folder pickers
        pickers = tk.Frame(self, bg=C["bg"])
        pickers.pack(fill="x", padx=18, pady=(12, 0))
        self._folder_card(pickers, "👁  Watch Folder",   "Monitors this folder for new files",
                          self.source_var, self._pick_source).pack(side="left", fill="x", expand=True, padx=(0,7))
        self._folder_card(pickers, "📤  Output Folder",  "Sorted subfolders appear here",
                          self.output_var, self._pick_output).pack(side="left", fill="x", expand=True)

        # Auto-watch toggle
        aw_row = tk.Frame(self, bg=C["bg"])
        aw_row.pack(fill="x", padx=18, pady=(10, 0))
        cb = tk.Checkbutton(aw_row, text="  Auto-start watching when app opens",
                            variable=self.auto_watch_var,
                            font=("Helvetica Neue", 9), fg=C["muted"], bg=C["bg"],
                            activeforeground=C["text"], activebackground=C["bg"],
                            selectcolor=C["card"], relief="flat", bd=0, cursor="hand2")
        cb.pack(side="left")

        # Buttons
        btns = tk.Frame(self, bg=C["bg"])
        btns.pack(fill="x", padx=18, pady=(12, 0))
        self._btn(btns, "⚡  Sort Now",        C["accent"],  C["accent2"],  self._sort_now).pack(side="left", padx=(0,7))
        self.watch_btn = self._btn(btns, "👁  Start Watching", C["green"], C["green2"], self._toggle_watch)
        self.watch_btn.pack(side="left", padx=(0,7))
        self._btn(btns, "⚙  Manage Folders",  C["orange"],  C["orange2"],  self._open_manage).pack(side="left", padx=(0,7))
        self._btn(btns, "🕘  History",         C["purple"],  C["purple2"],  self._open_history).pack(side="left", padx=(0,7))
        self._btn(btns, "📂  Open Output",     C["teal"],    C["teal2"],    self._open_output).pack(side="left")

        # Log
        log_hdr = tk.Frame(self, bg=C["bg"])
        log_hdr.pack(fill="x", padx=18, pady=(16, 5))
        tk.Label(log_hdr, text="ACTIVITY LOG",
                 font=("Helvetica Neue", 8, "bold"),
                 fg=C["dim"], bg=C["bg"]).pack(side="left")
        legend = tk.Frame(log_hdr, bg=C["bg"])
        legend.pack(side="right")
        for col, lbl in [(C["accent"], "Manual"), (C["green"], "Auto"), (C["teal"], "Extension")]:
            tk.Frame(legend, bg=col, width=7, height=7).pack(side="left", padx=(6,2))
            tk.Label(legend, text=lbl, font=("Helvetica Neue", 8),
                     fg=C["muted"], bg=C["bg"]).pack(side="left")
        tk.Button(log_hdr, text="Clear", font=("Helvetica Neue", 8),
                  fg=C["dim"], bg=C["bg"], activeforeground=C["muted"],
                  activebackground=C["bg"], relief="flat", cursor="hand2", bd=0,
                  command=self._clear_log).pack(side="right", padx=(0, 8))

        log_outer = tk.Frame(self, bg=C["border"])
        log_outer.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        log_inner = tk.Frame(log_outer, bg=C["card"])
        log_inner.pack(fill="both", expand=True, padx=1, pady=1)
        self.log = tk.Text(log_inner, bg=C["card"], fg=C["muted"],
                           font=("Menlo", 9), relief="flat", padx=16, pady=14,
                           state="disabled", wrap="word", cursor="arrow",
                           selectbackground=C["border"])
        self.log.pack(fill="both", expand=True)
        self.log.tag_config("auto",   foreground=C["green"])
        self.log.tag_config("manual", foreground=C["accent"])
        self.log.tag_config("ext",    foreground=C["teal"])
        self.log.tag_config("error",  foreground=C["red"])
        self.log.tag_config("info",   foreground=C["dim"])

        self._log("Ready — folders loaded from last session.", "info") if self.source_var.get() else self._log("Ready — select folders to get started.", "info")

    # ── WIDGETS ───────────────────────────────────────────────────────────────

    def _stat_card(self, parent, icon, label, value, key, color):
        card = tk.Frame(parent, bg=C["card"], highlightthickness=1,
                        highlightbackground=C["border"])
        card.configure(padx=14, pady=11)
        tk.Label(card, text=icon, font=("Helvetica Neue", 13),
                 fg=color, bg=C["card"]).pack(anchor="w")
        val = tk.Label(card, text=value,
                       font=("Helvetica Neue", 20, "bold"),
                       fg=C["text"], bg=C["card"])
        val.pack(anchor="w", pady=(1, 0))
        tk.Label(card, text=label, font=("Helvetica Neue", 8),
                 fg=C["muted"], bg=C["card"]).pack(anchor="w")
        setattr(self, f"stat_{key}", val)
        return card

    def _folder_card(self, parent, label, sublabel, var, cmd):
        card = tk.Frame(parent, bg=C["card"], highlightthickness=1,
                        highlightbackground=C["border"])
        card.configure(padx=14, pady=10)
        tk.Label(card, text=label, font=("Helvetica Neue", 9, "bold"),
                 fg=C["text"], bg=C["card"]).pack(anchor="w")
        tk.Label(card, text=sublabel, font=("Helvetica Neue", 8),
                 fg=C["muted"], bg=C["card"]).pack(anchor="w")
        row = tk.Frame(card, bg=C["card"])
        row.pack(fill="x", pady=(6, 0))
        ef = tk.Frame(row, bg=C["border"])
        ef.pack(side="left", fill="x", expand=True, padx=(0, 8))
        tk.Entry(ef, textvariable=var, font=("Menlo", 8),
                 bg=C["surface"], fg=C["text"], relief="flat",
                 insertbackground=C["accent"], bd=0
                 ).pack(fill="x", padx=1, pady=1, ipady=6)
        tk.Button(row, text="Browse", font=("Helvetica Neue", 8, "bold"),
                  fg=C["accent"], bg=C["surface"],
                  activeforeground=C["text"], activebackground=C["border"],
                  relief="flat", padx=12, pady=5, cursor="hand2", bd=0,
                  command=cmd).pack(side="right")
        return card

    def _btn(self, parent, text, color, hover, cmd):
        f = tk.Frame(parent, bg=color)
        tk.Button(f, text=text, font=("Helvetica Neue", 9, "bold"),
                  fg="white", bg=color, activeforeground="white",
                  activebackground=hover, relief="flat",
                  padx=14, pady=9, cursor="hand2", bd=0,
                  command=cmd).pack(padx=1, pady=1)
        return f

    # ── ACTIONS ───────────────────────────────────────────────────────────────

    def _pick_source(self):
        p = filedialog.askdirectory()
        if p: self.source_var.set(p)

    def _pick_output(self):
        p = filedialog.askdirectory()
        if p: self.output_var.set(p)

    def _get_dicts(self): return self.classes, self.types

    def _log(self, msg, tag="info"):
        self.log.configure(state="normal")
        self.log.insert("end", msg + "\n", tag)
        self.log.see("end")
        self.log.configure(state="disabled")

    def _clear_log(self):
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def _validate(self):
        src = self.source_var.get().strip()
        out = self.output_var.get().strip()
        if not src or not out:
            messagebox.showwarning("Missing Folders", "Please select both folders first.")
            return None, None
        if not os.path.exists(src):
            messagebox.showerror("Not Found", "Watch folder does not exist.")
            return None, None
        return src, out

    def _record(self, filename, cls, typ, used_ext, tag):
        entry = {
            "ts":   datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "file": filename, "cls": cls, "typ": typ,
            "ext":  used_ext, "tag": tag,
        }
        self.history.append(entry)
        save_history(self.history)

    def _handle_result(self, result, tag):
        if result is None: return
        filename, cls, typ, used_ext, _ = result
        ts  = datetime.now().strftime("%H:%M:%S")
        actual_tag = "ext" if used_ext else tag
        marker = "  [ext]" if used_ext else ""
        msg = f"[{ts}]  {filename}  →  {cls} / {typ}{marker}"
        self.after(0, lambda m=msg, t=actual_tag: self._log(m, t))
        self.total_sorted += 1
        if used_ext:
            self.ext_sorted += 1
            self.after(0, lambda: self.stat_ext_count.configure(text=str(self.ext_sorted)))
        self.after(0, lambda: self.stat_count.configure(text=str(self.total_sorted)))
        self.after(0, lambda: self.stat_session.configure(text=str(self.total_sorted)))
        self._record(filename, cls, typ, used_ext, actual_tag)

    def _sort_now(self):
        src, out = self._validate()
        if not src: return
        def run():
            # Only grab files sitting directly in the watch folder (not in subfolders)
            # Also skip any file that already lives inside the output folder
            out_real = os.path.realpath(out)
            files = [
                f for f in os.listdir(src)
                if os.path.isfile(os.path.join(src, f))
                and not os.path.realpath(os.path.join(src, f)).startswith(out_real)
            ]
            if not files:
                self.after(0, lambda: self._log("No unsorted files found in the watch folder.", "info"))
                return
            count = 0
            for f in files:
                result = move_file(os.path.join(src, f), out, self.classes, self.types)
                if result:
                    self._handle_result(result, "manual")
                    count += 1
            self.after(0, lambda c=count: self._log(f"─── Done — {c} file(s) sorted ───", "info"))
        threading.Thread(target=run, daemon=True).start()

    def _toggle_watch(self):
        self._stop_watch() if self.watch_active else self._start_watch()

    def _start_watch(self):
        if not WATCHDOG_AVAILABLE:
            messagebox.showerror("Missing Package",
                "Install first:\npip3 install watchdog --break-system-packages")
            return
        src, out = self._validate()
        if not src: return

        def cb(result, tag, err=None):
            if tag == "error":
                self.after(0, lambda: self._log(f"Error: {err}", "error"))
            else:
                self._handle_result(result, tag)

        handler = DownloadHandler(out, cb, self._get_dicts)
        self.observer = Observer()
        self.observer.schedule(handler, src, recursive=False)
        self.observer.start()
        self.watch_active = True

        self.watch_btn.configure(bg=C["red"])
        for w in self.watch_btn.winfo_children():
            w.configure(bg=C["red"], activebackground=C["red2"],
                        text="⏹  Stop Watching")
        self.badge.configure(text="● WATCHING", fg=C["green2"])
        self.stat_watch_status.configure(text="On", fg=C["green2"])
        self._log(f"Watching: {src}", "info")

    def _stop_watch(self):
        if self.observer:
            self.observer.stop(); self.observer.join(); self.observer = None
        self.watch_active = False
        self.watch_btn.configure(bg=C["green"])
        for w in self.watch_btn.winfo_children():
            w.configure(bg=C["green"], activebackground=C["green2"],
                        text="👁  Start Watching")
        self.badge.configure(text="● IDLE", fg=C["dim"])
        self.stat_watch_status.configure(text="Off", fg=C["muted"])
        self._log("Watching stopped.", "info")

    def _open_output(self):
        out = self.output_var.get().strip()
        if not out:
            messagebox.showwarning("No Output Folder", "Set an output folder first.")
            return
        if not os.path.exists(out):
            messagebox.showerror("Not Found", "Output folder doesn't exist yet.")
            return
        os.system(f'xdg-open "{out}"')

    def _open_manage(self):
        def on_save(new_classes, new_types):
            self.classes = new_classes
            self.types   = new_types
            self._save_cfg()
            self._log("✓ Folders & keywords saved.", "manual")
        ManageWindow(self, self.classes, self.types, on_save)

    def _open_history(self):
        def on_clear():
            self.history = []
            save_history([])
        HistoryWindow(self, self.history, on_clear)

    def _save_cfg(self):
        self.cfg.update({
            "classes":       self.classes,
            "types":         self.types,
            "watch_folder":  self.source_var.get().strip(),
            "output_folder": self.output_var.get().strip(),
            "auto_watch":    self.auto_watch_var.get(),
        })
        save_config(self.cfg)

    def _on_close(self):
        self._save_cfg()
        if self.observer:
            self.observer.stop()
        self.destroy()

if __name__ == "__main__":
    App().mainloop()
