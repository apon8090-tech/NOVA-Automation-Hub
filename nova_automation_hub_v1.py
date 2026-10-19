import os
import shutil
import threading
import time
import webbrowser
import time
import json
import os
import re
from tkinter import filedialog, simpledialog, messagebox
from tkinter import messagebox
from pynput import mouse as pynput_mouse
from pynput import keyboard as pynput_keyboard
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import keyboard  # For detecting key presses (used in future enhancements)

print("NOVA: Imports completed successfully!")
APP_NAME = "NOVA AUTOMATION HUB"

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Move mouse to top-left corner to trigger PyAutoGUI fail-safe.
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    pyautogui = None
    PYAUTOGUI_AVAILABLE = False


BG = "#0b1020"
PANEL = "#121a2d"
PANEL_LIGHT = "#19243b"
TEXT = "#edf2ff"
MUTED = "#9aa8c7"
ACCENT = "#7c5cff"
ACCENT_HOVER = "#9278ff"
GREEN = "#2dd4a7"
RED = "#ff647c"
BORDER = "#263452"


class NovaAutomationHub:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1000x680")
        self.root.minsize(850, 600)
        # Floating sidebar state
        self.sidebar_collapsed = False
        self.edge_bar = None
        self.expanded_geometry = "1000x680"
        self.root.configure(bg=BG)

        self.click_stop = threading.Event()
        self.click_thread = None
        self.click_count = 0
        
        # Macro Recorder state
        self.macro_actions = []
        self.macro_recording = False
        self.macro_playing = False
        self.macro_stop_event = threading.Event()
        self.macro_mouse_listener = None
        self.macro_keyboard_listener = None
        self.macro_lock = threading.Lock()
        self.macro_start_time = 0.0
        self.macro_timer_id = None
        self.macro_thread = None

       
        # Saved Macro Library
        self.saved_macros = {}
        self.macro_library_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "nova_macro_library.json"
        )

        # Recent unsaved macros (24-hour retention)
        self.recent_macros = {}
        self.recent_macros_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "nova_recent_macros.json"
        )

        self._load_macro_library()
        self._load_recent_macros()



        self._setup_styles()
        self._build_ui()
        self._show_page("Dashboard")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
              # Global keyboard shortcuts 
        keyboard.add_hotkey(
            "ctrl+alt+shift+a",
            lambda: self.root.after(0, self._start_clicker)
        )
        keyboard.add_hotkey(
            "ctrl+alt+shift+s",
            lambda: self.root.after(0, self._stop_clicker)
        )
        keyboard.add_hotkey(
            "ctrl+alt+shift+d",
            lambda: self.root.after(0, self._show_dashboard_hotkey)
        )

    def _setup_styles(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Nova.TCombobox",
            fieldbackground=PANEL_LIGHT,
            background=PANEL_LIGHT,
            foreground=TEXT,
            arrowcolor=TEXT,
        )
        style.configure(
            "Nova.Horizontal.TProgressbar",
            troughcolor=PANEL_LIGHT,
            background=ACCENT,
            bordercolor=PANEL_LIGHT,
        )

    def _build_ui(self):
        self.shell = tk.Frame(self.root, bg=BG)
        self.shell.pack(fill="both", expand=True)

        sidebar = tk.Frame(self.shell, bg="#0e1628", width=220)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        logo = tk.Frame(sidebar, bg="#0e1628")
        logo.pack(fill="x", padx=20, pady=(24, 28))
        tk.Label(logo, text="✦ NOVA", font=("Segoe UI", 19, "bold"),
                 fg=TEXT, bg="#0e1628").pack(anchor="w")
        tk.Label(logo, text="AUTOMATION HUB", font=("Segoe UI", 8, "bold"),
                 fg=ACCENT_HOVER, bg="#0e1628").pack(anchor="w", pady=(3, 0))

        self.nav_buttons = {}
        nav_items = [
            ("Dashboard", "⌂  Dashboard"),
            ("Auto Clicker", "◉  Auto Clicker"),
            ("File Organizer", "▤  File Organizer"),
            ("Quick Tasks", "⚡  Quick Tasks"),
            ("Macro Recorder", "⏺  Macro Recorder"),
            ("Activity Log", "☷  Activity Log"),
            ("My Tasks", "▤  My Tasks"),
        ]
        for page, label in nav_items:
            btn = tk.Button(
                sidebar, text=label, anchor="w", relief="flat", bd=0,
                padx=18, pady=12, font=("Segoe UI", 10),
                bg="#0e1628", fg=MUTED, activebackground=PANEL_LIGHT,
                activeforeground=TEXT, cursor="hand2",
                command=lambda p=page: self._show_page(p)
            )
            btn.pack(fill="x", padx=10, pady=2)
            self.nav_buttons[page] = btn

        bottom = tk.Frame(sidebar, bg="#0e1628")
        bottom.pack(side="bottom", fill="x", padx=20, pady=20)
        tk.Label(bottom, text="●  LOCAL APP", fg=GREEN, bg="#0e1628",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(bottom, text="Your actions stay on this computer.",
                 fg=MUTED, bg="#0e1628", font=("Segoe UI", 8),
                 wraplength=175, justify="left").pack(anchor="w", pady=(6, 0))

        self.main = tk.Frame(self.shell, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)

        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", padx=28, pady=(24, 16))
        self.page_title = tk.Label(header, text="Dashboard", font=("Segoe UI", 22, "bold"),
                                   fg=TEXT, bg=BG)
        self.page_title.pack(side="left")
        
        tk.Button(
            header,
            text="➜",
            font=("Segoe UI", 12, "bold"),
            bg="#0e1628",
            fg=TEXT,
            activebackground=PANEL_LIGHT,
            activeforeground=TEXT,
            relief="flat",
            cursor="hand2",
            command=self._collapse_to_edge
        ).pack(side="right", padx=(8, 0))

        self.status_badge = tk.Label(header, text="● READY", font=("Segoe UI", 9, "bold"),
                                     fg=GREEN, bg=PANEL, padx=12, pady=7)
        self.status_badge.pack(side="right")

        self.content = tk.Frame(self.main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self.log_messages = []
        self._log("Nova is ready. Choose a tool from the left menu.")
    
    def _collapse_to_edge(self):
        if self.sidebar_collapsed:
            return

        self.expanded_geometry = self.root.geometry().split("+")[0]
        self.sidebar_collapsed = True

        self.shell.pack_forget()

        self.root.state("normal")
        self.root.update_idletasks()

        if self.edge_bar is not None:
            self.edge_bar.destroy()

        self.edge_bar = tk.Frame(
            self.root,
            bg="#0e1628",
            width=48,
            height=180
        )
        self.edge_bar.pack(fill="both", expand=True)
        self.edge_bar.pack_propagate(False)

        tk.Button(
            self.edge_bar,
            text="✦",
            font=("Segoe UI", 18, "bold"),
            bg="#0e1628",
            fg="#7c9cff",
            relief="flat",
            cursor="hand2",
            command=self._expand_from_edge
        ).pack(fill="both", expand=True)

        width = 48
        height = 180
        x = self.root.winfo_screenwidth() - width - 6
        y = (self.root.winfo_screenheight() - height) // 2

        self.root.geometry(f"{width}x{height}+{x}+{y}")
        self.root.overrideredirect(True)
        self.root.update_idletasks()

    def _expand_from_edge(self):
        if not self.sidebar_collapsed:
            return

        self.sidebar_collapsed = False

        if self.edge_bar is not None:
            self.edge_bar.destroy()
            self.edge_bar = None

        self.root.overrideredirect(False)
        self.root.minsize(850, 600)

        geometry = self.expanded_geometry or "1000x680"
        self.root.geometry(geometry)
        self.root.update_idletasks()

        self.shell.pack(fill="both", expand=True)

    def _clear_content(self):
        for child in self.content.winfo_children():
            child.destroy()

    def _show_page(self, page):
        for name, btn in self.nav_buttons.items():
            btn.configure(bg=PANEL_LIGHT if name == page else "#0e1628",
                          fg=TEXT if name == page else MUTED)
        self.page_title.configure(text=page)
        self._clear_content()
        if page == "Dashboard":
            self._dashboard_page()
        elif page == "Auto Clicker":
            self._clicker_page()
        elif page == "File Organizer":
            self._organizer_page()
        elif page == "Quick Tasks":
            self._quick_tasks_page()
        elif page == "Macro Recorder":
            self._macro_recorder_page()
        elif page == "My Tasks":
            self._my_tasks_page()
        elif page == "Activity Log":
            self._log_page()

    def _card(self, parent, title, description=None):
        frame = tk.Frame(parent, bg=PANEL, highlightbackground=BORDER, highlightthickness=1)
        frame.pack(fill="x", pady=(0, 12))
        inner = tk.Frame(frame, bg=PANEL)
        inner.pack(fill="both", expand=True, padx=18, pady=16)
        tk.Label(inner, text=title, font=("Segoe UI", 12, "bold"),
                 fg=TEXT, bg=PANEL).pack(anchor="w")
        if description:
            tk.Label(inner, text=description, font=("Segoe UI", 9),
                     fg=MUTED, bg=PANEL, justify="left", wraplength=680).pack(
                         anchor="w", pady=(5, 0))
        return inner

    def _button(self, parent, text, command, primary=True):
        return tk.Button(
            parent, text=text, command=command, relief="flat", bd=0,
            padx=16, pady=10, cursor="hand2", font=("Segoe UI", 9, "bold"),
            bg=ACCENT if primary else PANEL_LIGHT,
            fg="white" if primary else TEXT,
            activebackground=ACCENT_HOVER if primary else BORDER,
            activeforeground="white"
        )

    def _label(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w", pady=(12, 5))

    def _entry(self, parent, variable=None, width=40):
        return tk.Entry(parent, textvariable=variable, width=width,
                        bg=PANEL_LIGHT, fg=TEXT, insertbackground=TEXT,
                        relief="flat", font=("Segoe UI", 10),
                        highlightthickness=1, highlightbackground=BORDER,
                        highlightcolor=ACCENT)

   
    def _dashboard_page(self):
        # PRO welcome banner
        hero = tk.Frame(
            self.content,
            bg="#171f38",
            highlightbackground="#493b7a",
            highlightthickness=1
        )
        hero.pack(fill="x", pady=(0, 16))

        hero_inner = tk.Frame(hero, bg="#171f38")
        hero_inner.pack(fill="x", padx=22, pady=20)

        tk.Label(
            hero_inner,
            text="Welcome back, Md Abu Daian Apon",
            bg="#171f38",
            fg="#a995ff",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        tk.Label(
            hero_inner,
            text="Your automation, simplified.",
            bg="#171f38",
            fg=TEXT,
            font=("Segoe UI", 19, "bold")
        ).pack(anchor="w", pady=(8, 4))

        tk.Label(
            hero_inner,
            text="Manage your everyday tasks from one workspace.",
            bg="#171f38",
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(anchor="w")

        # Status summary cards
        summary = tk.Frame(self.content, bg=BG)
        summary.pack(fill="x", pady=(0, 16))

        summaries = [
            ("03", "AVAILABLE TOOLS", ACCENT_HOVER),
            ("READY", "SYSTEM STATUS", GREEN),
            ("LOCAL", "WORKSPACE", "#55c2ff"),
        ]

        for value, label, color in summaries:
            card = tk.Frame(
                summary,
                bg=PANEL,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            card.pack(side="left", fill="both", expand=True, padx=(0, 8))

            tk.Label(
                card,
                text=value,
                bg=PANEL,
                fg=color,
                font=("Segoe UI", 15, "bold")
            ).pack(anchor="w", padx=12, pady=(12, 3))

            tk.Label(
                card,
                text=label,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 8, "bold")
            ).pack(anchor="w", padx=12, pady=(0, 12))

        # Tools section
        section = tk.Frame(self.content, bg=BG)
        section.pack(fill="x", pady=(0, 8))

        tk.Label(
            section,
            text="YOUR TOOLS",
            bg=BG,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")

        tk.Label(
            section,
            text="SELECT A TOOL TO GET STARTED",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).pack(side="right")

        tools = [
            (
                "01",
                "AUTO CLICKER",
                "Automate repetitive mouse clicks.",
                "Auto Clicker",
                "#a995ff"
            ),
            (
                "02",
                "FILE ORGANIZER",
                "Sort files into type-based folders.",
                "File Organizer",
                "#55c2ff"
            ),
            (
                "03",
                "QUICK TASKS",
                "Open websites or type prepared text.",
                "Quick Tasks",
                GREEN
            ),
        ]

        for number, title, desc, page, color in tools:
            card = tk.Frame(
                self.content,
                bg=PANEL,
                highlightbackground=BORDER,
                highlightthickness=1
            )
            card.pack(fill="x", pady=4)

            row = tk.Frame(card, bg=PANEL)
            row.pack(fill="x", padx=14, pady=11)

            number_box = tk.Frame(
                row,
                bg=PANEL_LIGHT,
                width=42,
                height=42
            )
            number_box.pack(side="left", padx=(0, 12))
            number_box.pack_propagate(False)

            tk.Label(
                number_box,
                text=number,
                bg=PANEL_LIGHT,
                fg=color,
                font=("Segoe UI", 11, "bold")
            ).pack(expand=True)

            info = tk.Frame(row, bg=PANEL)
            info.pack(side="left", fill="x", expand=True)

            tk.Label(
                info,
                text=title,
                bg=PANEL,
                fg=TEXT,
                font=("Segoe UI", 10, "bold")
            ).pack(anchor="w")

            tk.Label(
                info,
                text=desc,
                bg=PANEL,
                fg=MUTED,
                font=("Segoe UI", 9),
                wraplength=390,
                justify="left"
            ).pack(anchor="w", pady=(3, 0))

            self._button(
                row,
                "OPEN  →",
                lambda p=page: self._show_page(p),
                False
            ).pack(side="right", padx=(8, 0))

        # Footer note
        footer = tk.Frame(self.content, bg=BG)
        footer.pack(fill="x", pady=(10, 0))

        tk.Label(
            footer,
            text="✦  NOVA AUTOMATION HUB",
            bg=BG,
            fg="#a995ff",
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        tk.Label(
            footer,
            text="Use automation responsibly.",
            bg=BG,
            fg=MUTED,
            font=("Segoe UI", 8)
        ).pack(side="right")

    def _clicker_page(self):
        card = self._card(self.content, "Auto Clicker", "Clicks at the current mouse pointer position. Keep the target app visible and test with a small click count first.")
        if not PYAUTOGUI_AVAILABLE:
            tk.Label(card, text="PyAutoGUI is not installed. Install it with:  pip install pyautogui",
                     bg=PANEL, fg=RED, font=("Segoe UI", 9), wraplength=650,
                     justify="left").pack(anchor="w", pady=(12, 0))

        self.delay_var = tk.StringVar(value="1.0")
        self.limit_var = tk.StringVar(value="10")
        self.click_status = tk.StringVar(value="Not running")
        self.click_count_var = tk.StringVar(value="Clicks: 0")

        self._label(card, "Delay between clicks (seconds; minimum 0.1)")
        self._entry(card, self.delay_var).pack(anchor="w", ipady=7, fill="x")
        self._label(card, "Maximum number of clicks (1–10000)")
        self._entry(card, self.limit_var).pack(anchor="w", ipady=7, fill="x")

        actions = tk.Frame(card, bg=PANEL)
        actions.pack(fill="x", pady=(16, 0))
        self._button(actions, "▶  START", self._start_clicker).pack(side="left")
        self._button(actions, "■  STOP", self._stop_clicker, False).pack(side="left", padx=8)
        tk.Label(card, textvariable=self.click_status, bg=PANEL, fg=GREEN,
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(15, 3))
        tk.Label(card, textvariable=self.click_count_var, bg=PANEL, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")
        tk.Label(card, text="Emergency stop: press STOP in this window, or move the pointer to the top-left corner.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=650,
                 justify="left").pack(anchor="w", pady=(12, 0))

    def _start_clicker(self):
        if not PYAUTOGUI_AVAILABLE:
            messagebox.showerror("Missing dependency", "Install PyAutoGUI first:\n\npip install pyautogui")
            return
        if self.click_thread and self.click_thread.is_alive():
            messagebox.showinfo("Already running", "The clicker is already running.")
            return
        try:
            delay = float(self.delay_var.get())
            limit = int(self.limit_var.get())
            if delay < 0.1 or not 1 <= limit <= 10000:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid settings", "Delay must be at least 0.1 seconds and click count must be 1–10000.")
            return
        if not messagebox.askyesno("Confirm auto-clicking",
                                   f"Click at the current mouse position {limit} times, every {delay:g} seconds?"):
            return
        self.click_stop.clear()
        self.click_count = 0
        self.click_status.set("Running…")
        self.status_badge.configure(text="● RUNNING", fg=GREEN)
        self._log(f"Auto Clicker started: max {limit} clicks, {delay:g}s delay.")
        self.click_thread = threading.Thread(target=self._click_worker, args=(delay, limit), daemon=True)
        self.click_thread.start()

    def _click_worker(self, delay, limit):
        try:
            for _ in range(limit):
                if self.click_stop.is_set():
                    break
                pyautogui.click()
                self.click_count += 1
                self.root.after(0, self.click_count_var.set, f"Clicks: {self.click_count}")
                if self.click_stop.wait(delay):
                    break
            result = "Stopped" if self.click_stop.is_set() else "Completed"
            self.root.after(0, self.click_status.set, result)
            self.root.after(0, self._log, f"Auto Clicker {result.lower()} after {self.click_count} clicks.")
        except Exception as exc:
            self.root.after(0, self.click_status.set, "Stopped (safety/error)")
            self.root.after(0, self._log, f"Auto Clicker stopped: {exc}")
        finally:
            self.root.after(0, lambda: self.status_badge.configure(text="● READY", fg=GREEN))

    def _stop_clicker(self):
        self.click_stop.set()
        self.click_status.set("Stopping…")
        self._log("Stop requested for Auto Clicker.")

    def _organizer_page(self):
        card = self._card(self.content, "File Organizer", "Choose a folder to sort its files into Images, Videos, Documents, Audio, Archives, and Other. It only processes files directly inside the selected folder, not subfolders.")
        self.folder_var = tk.StringVar(value="")
        row = tk.Frame(card, bg=PANEL)
        row.pack(fill="x", pady=(14, 0))
        self._entry(row, self.folder_var).pack(side="left", fill="x", expand=True, ipady=8)
        self._button(row, "BROWSE", self._browse_folder, False).pack(side="left", padx=(8, 0))
        self._button(card, "↗  ORGANIZE FILES", self._organize_files).pack(anchor="w", pady=(16, 0))
        tk.Label(card, text="Files are moved into subfolders. Review the selected folder before proceeding.",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 8), wraplength=650,
                 justify="left").pack(anchor="w", pady=(12, 0))

    def _browse_folder(self):
        folder = filedialog.askdirectory(title="Choose a folder to organize")
        if folder:
            self.folder_var.set(folder)

    @staticmethod
    def _category(filename):
        ext = os.path.splitext(filename)[1].lower()
        categories = {
            "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".tiff", ".svg"},
            "Videos": {".mp4", ".mov", ".avi", ".mkv", ".webm", ".wmv"},
            "Documents": {".pdf", ".doc", ".docx", ".txt", ".rtf", ".odt", ".xls", ".xlsx", ".ppt", ".pptx", ".csv"},
            "Audio": {".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a"},
            "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
            "Code": {".py", ".js", ".html", ".css", ".java", ".cpp", ".c", ".json", ".xml"},
        }
        for category, extensions in categories.items():
            if ext in extensions:
                return category
        return "Other"

    def _organize_files(self):
        folder = self.folder_var.get().strip()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Choose a folder", "Please choose a valid folder first.")
            return
        try:
            files = [name for name in os.listdir(folder)
                     if os.path.isfile(os.path.join(folder, name))]
        except OSError as exc:
            messagebox.showerror("Cannot read folder", str(exc))
            return
        if not files:
            messagebox.showinfo("Nothing to organize", "No files found directly inside this folder.")
            return
        if not messagebox.askyesno("Confirm file organization",
                                   f"Sort {len(files)} files in:\n{folder}\n\nFiles will be moved into category subfolders. Continue?"):
            return
        moved = 0
        errors = []
        for name in files:
            category = self._category(name)
            destination_folder = os.path.join(folder, category)
            try:
                os.makedirs(destination_folder, exist_ok=True)
                source = os.path.join(folder, name)
                destination = os.path.join(destination_folder, name)
                if os.path.exists(destination):
                    base, ext = os.path.splitext(name)
                    n = 1
                    while os.path.exists(os.path.join(destination_folder, f"{base}_{n}{ext}")):
                        n += 1
                    destination = os.path.join(destination_folder, f"{base}_{n}{ext}")
                shutil.move(source, destination)
                moved += 1
            except OSError as exc:
                errors.append(f"{name}: {exc}")
        self._log(f"File Organizer moved {moved} file(s) in {folder}.")
        message = f"Done! Organized {moved} file(s)."
        if errors:
            message += f"\n\n{len(errors)} file(s) could not be moved. Check Activity Log."
            for error in errors[:10]:
                self._log(f"Organizer error: {error}")
        messagebox.showinfo("Organization complete", message)

    def _quick_tasks_page(self):
        card = self._card(self.content, "Open a website", "Enter a web address. This opens your default browser.")
        self.url_var = tk.StringVar(value="https://www.google.com")
        self._label(card, "Website URL")
        self._entry(card, self.url_var).pack(fill="x", ipady=7)
        self._button(card, "🌐  OPEN WEBSITE", self._open_website).pack(anchor="w", pady=(12, 0))

        type_card = self._card(self.content, "Auto Type Text", "Copies text into the currently focused app by simulating keystrokes. After you click Start, switch to the intended text field during the 3-second countdown.")
        self.type_text = tk.Text(type_card, height=4, wrap="word", bg=PANEL_LIGHT,
                                 fg=TEXT, insertbackground=TEXT, relief="flat",
                                 font=("Segoe UI", 10), padx=10, pady=8)
        self.type_text.pack(fill="x", pady=(12, 0))
        self.type_text.insert("1.0", "Hello! This text was typed by Python.")
        self._button(type_card, "⌨  TYPE AFTER 3 SECONDS", self._type_text).pack(anchor="w", pady=(12, 0))
        if not PYAUTOGUI_AVAILABLE:
            tk.Label(type_card, text="Auto Type needs PyAutoGUI: pip install pyautogui",
                     bg=PANEL, fg=RED, font=("Segoe UI", 9)).pack(anchor="w", pady=(8, 0))

    def _open_website(self):
        url = self.url_var.get().strip()
        if not url.startswith(("https://", "http://")):
            messagebox.showerror("Invalid URL", "Please enter a URL starting with https:// or http://")
            return
        webbrowser.open(url)
        self._log(f"Opened website: {url}")

    def _type_text(self):
        if not PYAUTOGUI_AVAILABLE:
            messagebox.showerror("Missing dependency", "Install PyAutoGUI first:\n\npip install pyautogui")
            return
        text = self.type_text.get("1.0", "end-1c")
        if not text:
            messagebox.showinfo("No text", "Enter some text first.")
            return
        if not messagebox.askyesno("Confirm auto typing",
                                   "After you click Yes, you have 3 seconds to focus the intended text field. Continue?"):
            return
        self._log("Auto Type countdown started.")
        self.status_badge.configure(text="● COUNTDOWN", fg=ACCENT_HOVER)
        threading.Thread(target=self._type_worker, args=(text,), daemon=True).start()

    def _type_worker(self, text):
        try:
            time.sleep(3)
            pyautogui.write(text, interval=0.015)
            self.root.after(0, self._log, "Auto Type completed.")
        except Exception as exc:
            self.root.after(0, self._log, f"Auto Type stopped: {exc}")
        finally:
            self.root.after(0, lambda: self.status_badge.configure(text="● READY", fg=GREEN))

    def _log(self, message):
        stamp = time.strftime("%H:%M:%S")
        self.log_messages.append(f"[{stamp}] {message}")
        if len(self.log_messages) > 500:
            self.log_messages = self.log_messages[-500:]

    def _log_page(self):
        card = self._card(self.content, "Activity Log", "Recent actions performed by this app.")
        text = tk.Text(card, height=20, wrap="word", bg=PANEL_LIGHT, fg=TEXT,
                       insertbackground=TEXT, relief="flat", font=("Consolas", 9),
                       padx=10, pady=10)
        text.pack(fill="both", expand=True, pady=(12, 0))
        text.insert("1.0", "\n".join(self.log_messages))
        text.configure(state="disabled")
        self._button(card, "CLEAR LOG", self._clear_log, False).pack(anchor="w", pady=(10, 0))

    def _clear_log(self):
        self.log_messages = []
        self._log("Activity log cleared.")
        self._show_page("Activity Log")
    def _show_dashboard_hotkey(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._show_page("Dashboard")
    def _show_dashboard_hotkey(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self._show_page("Dashboard")
    def _macro_recorder_page(self):
            """Build the Macro Recorder page."""
            panel = tk.Frame(self.content, bg=BG)
            panel.pack(fill="both", expand=True, padx=10, pady=10)
    
            tk.Label(
                panel,
                text="MACRO RECORDER",
                font=("Segoe UI", 20, "bold"),
                bg=BG,
                fg=TEXT
            ).pack(anchor="w", pady=(0, 6))
    
            tk.Label(
                panel,
                text="Record mouse clicks, scrolling and keyboard actions.",
                font=("Segoe UI", 10),
                bg=BG,
                fg=MUTED
            ).pack(anchor="w", pady=(0, 20))
    
            card = tk.Frame(
                panel, bg=PANEL, padx=22, pady=22,
                highlightthickness=1, highlightbackground=PANEL_LIGHT
            )
            card.pack(fill="x", pady=(0, 14))
    
            self.macro_status_label = tk.Label(
                card,
                text="● READY",
                font=("Segoe UI", 13, "bold"),
                bg=PANEL,
                fg=GREEN
            )
            self.macro_status_label.pack(anchor="w", pady=(0, 8))
    
            self.macro_count_label = tk.Label(
                card,
                text=f"Recorded actions: {len(self.macro_actions)} / 500",
                font=("Segoe UI", 11),
                bg=PANEL,
                fg=TEXT
            )
            self.macro_count_label.pack(anchor="w", pady=(0, 6))
    
            tk.Label(
                card,
                text="Maximum recording: 60 seconds",
                font=("Segoe UI", 9),
                bg=PANEL,
                fg=MUTED
            ).pack(anchor="w", pady=(0, 18))
    
            buttons = tk.Frame(card, bg=PANEL)
            buttons.pack(anchor="w", fill="x")
    
            tk.Button(
                buttons, text="●  Record",
                command=self._start_macro_recording,
                bg="#c94b59", fg="white",
                activebackground="#a93c49",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left", padx=(0, 8))
    
            tk.Button(
                buttons, text="■  Stop Recording",
                command=self._stop_macro_recording,
                bg=PANEL_LIGHT, fg=TEXT,
                activebackground="#33415b",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left", padx=(0, 8))
    
            tk.Button(
                buttons, text="▶  Playback",
                command=self._start_macro_playback,
                bg="#287b65", fg="white",
                activebackground="#20634f",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left", padx=(0, 8))
    
            tk.Button(
                buttons, text="■  Stop Playback",
                command=self._stop_macro_playback,
                bg=PANEL_LIGHT, fg=TEXT,
                activebackground="#33415b",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left")
            
            tk.Button(
                buttons, text="💾  Save Macro",
                command=self._save_macro,
                bg="#365a91", fg="white",
                activebackground="#294775",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left", padx=(8, 0))

            tk.Button(
                buttons, text="📂  Load Macro",
                command=self._load_macro,
                bg="#6651a3", fg="white",
                activebackground="#504080",
                relief="flat", padx=16, pady=9,
                cursor="hand2"
            ).pack(side="left", padx=(8, 0))
            info = tk.Frame(panel, bg=BG)
            info.pack(fill="x", pady=8)
    
            tk.Label(
                info,
                text="IMPORTANT SAFETY NOTES",
                font=("Segoe UI", 10, "bold"),
                bg=BG, fg="#ffca70"
            ).pack(anchor="w", pady=(0, 8))
    
            tk.Label(
                info,
                text=(
                    "• Do not record passwords, private messages or sensitive information.\n"
                    "• Playback controls your real mouse and keyboard.\n"
                    "• Test macros in a harmless window before using them elsewhere.\n"
                    "• Avoid recording or replaying actions involving payments, deleting files,\n"
                    "  account changes, or other important operations."
                ),
                font=("Segoe UI", 10),
                bg=BG, fg=MUTED, justify="left"
            ).pack(anchor="w")
    
   
    def _macro_refresh_status(self, status=None, color=None):
        """Update the visible Macro Recorder status safely."""
        try:
            if not hasattr(self, "macro_status_label"):
                return

            if not self.macro_status_label.winfo_exists():
                return

            if status is not None:
                self.macro_status_label.configure(
                    text=status,
                    fg=color or TEXT
                )

            if hasattr(self, "macro_count_label"):
                if self.macro_count_label.winfo_exists():
                    with self.macro_lock:
                        count = len(self.macro_actions)

                    self.macro_count_label.configure(
                        text=f"Recorded actions: {count} / 500"
                    )

        except tk.TclError:
            # The page or its widgets may already have been destroyed.
            return

    
    def _macro_add_action(self, action):
            """Store one action, subject to recording limits."""
            if not self.macro_recording:
                return
    
            elapsed = time.monotonic() - self.macro_start_time
    
            if elapsed >= 60:
                self.root.after(0, self._stop_macro_recording)
                return
    
            action["time"] = elapsed
    
            with self.macro_lock:
                if len(self.macro_actions) >= 500:
                    self.root.after(0, self._stop_macro_recording)
                    return
    
                self.macro_actions.append(action)
                count = len(self.macro_actions)
    
            if count >= 500:
                self.root.after(0, self._stop_macro_recording)
            else:
                try:
                    self.root.after(0, self._macro_refresh_status)
                except tk.TclError:
                    pass
    
    def _start_macro_recording(self):
            """Start recording mouse and keyboard events."""
            if self.macro_recording or self.macro_playing:
                messagebox.showinfo(
                    "Macro Recorder",
                    "Stop the current recording or playback first."
                )
                return
    
            confirm = messagebox.askyesno(
                "Start Recording?",
                "The previous macro will be replaced.\n\n"
                "Mouse clicks, scrolling and keyboard keys may be recorded.\n"
                "Do not type passwords or private information.\n\n"
                "Start recording?"
            )
            if not confirm:
                return
    
            
            # Archive the previous task before clearing its actions
            self._archive_current_macro()

            with self.macro_lock:
                self.macro_actions.clear()

    
            self.macro_start_time = time.monotonic()
            self.macro_recording = True
    
            def on_click(x, y, button, pressed):
                self._macro_add_action({
                    "type": "mouse_button",
                    "x": x, "y": y,
                    "button": button,
                    "pressed": pressed
                })
    
            def on_scroll(x, y, dx, dy):
                self._macro_add_action({
                    "type": "scroll",
                    "x": x, "y": y,
                    "dx": dx, "dy": dy
                })
    
            def on_press(key):
                self._macro_add_action({
                    "type": "key",
                    "key": key,
                    "pressed": True
                })
    
            def on_release(key):
                self._macro_add_action({
                    "type": "key",
                    "key": key,
                    "pressed": False
                })
    
            try:
                self.macro_mouse_listener = pynput_mouse.Listener(
                    on_click=on_click,
                    on_scroll=on_scroll
                )
                self.macro_keyboard_listener = pynput_keyboard.Listener(
                    on_press=on_press,
                    on_release=on_release
                )
    
                self.macro_mouse_listener.start()
                self.macro_keyboard_listener.start()
    
                self._macro_refresh_status("● RECORDING", "#ff6978")
                self.macro_timer_id = self.root.after(
                    60000, self._stop_macro_recording
                )
    
            except Exception as exc:
                self.macro_recording = False
    
                for listener in (
                    self.macro_mouse_listener,
                    self.macro_keyboard_listener
                ):
                    if listener is not None:
                        try:
                            listener.stop()
                        except Exception:
                            pass
                    self.macro_mouse_listener = None
                    self.macro_keyboard_listener = None
                    self.macro_timer_id = None
                messagebox.showerror(
                    "Recording Error",
                    f"Could not start recording:\n{exc}"
                )
                self._macro_refresh_status("● ERROR", "#ff6978")
    
    def _stop_macro_recording(self):
            """Stop recording and release both listeners."""
            was_recording = self.macro_recording
            self.macro_recording = False
    
            timer_id = getattr(self, "macro_timer_id", None)
            if timer_id is not None:
                try:
                    self.root.after_cancel(timer_id)
                except (tk.TclError, ValueError):
                    pass
                self.macro_timer_id = None
    
            for listener in (
                self.macro_mouse_listener,
                self.macro_keyboard_listener
            ):
                if listener is not None:
                    try:
                        listener.stop()
                    except Exception:
                        pass
    
            self.macro_mouse_listener = None
            self.macro_keyboard_listener = None
    
            if was_recording:
                self._macro_refresh_status("● RECORDING STOPPED", GREEN)
    
    def _start_macro_playback(self):
            """Play the saved actions on a worker thread."""
            if self.macro_recording or self.macro_playing:
                messagebox.showinfo(
                    "Macro Recorder",
                    "Stop the current recording or playback first."
                )
                return
    
            with self.macro_lock:
                actions = list(self.macro_actions)
    
            if not actions:
                messagebox.showwarning(
                    "No Macro",
                    "Record some actions before starting playback."
                )
                return
    
            if not messagebox.askyesno(
                "Confirm Playback",
                f"Replay {len(actions)} recorded actions?\n\n"
                "This will control your real mouse and keyboard. "
                "Make sure the correct, safe window is active."
            ):
                return
    
            self.macro_playing = True
            self.macro_stop_event.clear()
            self._macro_refresh_status("▶ PLAYING", "#55c2ff")
    
            def playback_worker():
                mouse_controller = pynput_mouse.Controller()
                keyboard_controller = pynput_keyboard.Controller()
                previous_time = 0.0
    
                try:
                    for action in actions:
                        if self.macro_stop_event.is_set():
                            break
    
                        target_time = action["time"]
                        delay = max(0.0, target_time - previous_time)
    
                        if self.macro_stop_event.wait(delay):
                            break
    
                        kind = action["type"]
    
                        if kind == "mouse_button":
                            mouse_controller.position = (
                                action["x"], action["y"]
                            )
                            button = action["button"]
    
                            if action["pressed"]:
                                mouse_controller.press(button)
                            else:
                                mouse_controller.release(button)
    
                        elif kind == "scroll":
                            mouse_controller.position = (
                                action["x"], action["y"]
                            )
                            mouse_controller.scroll(
                                action["dx"], action["dy"]
                            )
    
                        elif kind == "key":
                            key = action["key"]
    
                            if action["pressed"]:
                                keyboard_controller.press(key)
                            else:
                                keyboard_controller.release(key)
    
                        previous_time = target_time
    
                except Exception as exc:
                    try:
                        self.root.after(
                            0,
                            lambda error=str(exc): messagebox.showerror(
                                "Playback Error", error
                            )
                        )
                    except tk.TclError:
                        pass
    
                finally:
                    try:
                        self.root.after(
                            0,
                            self._finish_macro_playback
                        )
                    except tk.TclError:
                        self.macro_playing = False

            self.macro_thread = threading.Thread(
                target=playback_worker, daemon=True
            )
            self.macro_thread.start()
    
    def _stop_macro_playback(self):
            """Request playback to stop."""
            self.macro_stop_event.set()
            self._macro_refresh_status("■ STOP REQUESTED", "#ffca70")
    
    def _macro_encode_action(self, action):
        item = {
            "time": float(action["time"]),
            "type": action["type"]
        }

        if action["type"] == "mouse_button":
            item.update({
                "x": int(action["x"]),
                "y": int(action["y"]),
                "button": action["button"].name,
                "pressed": bool(action["pressed"])
            })

        elif action["type"] == "scroll":
            item.update({
                "x": int(action["x"]),
                "y": int(action["y"]),
                "dx": int(action["dx"]),
                "dy": int(action["dy"])
            })

        elif action["type"] == "key":
            key = action["key"]

            if isinstance(key, pynput_keyboard.Key):
                key_data = {"kind": "special", "value": key.name}
            else:
                char = getattr(key, "char", None)
                if char is None and isinstance(key, str):
                    char = key
                if not isinstance(char, str) or len(char) != 1:
                    raise ValueError("Unsupported keyboard key.")
                key_data = {"kind": "char", "value": char}

            item.update({
                "key": key_data,
                "pressed": bool(action["pressed"])
            })
        else:
            raise ValueError("Unknown action type.")

        return item

    def _macro_decode_action(self, item):
        kind = item["type"]
        t = float(item["time"])

        if t < 0 or t > 60:
            raise ValueError("Invalid action timing.")

        if kind == "mouse_button":
            button = getattr(pynput_mouse.Button, item["button"], None)
            if button is None:
                raise ValueError("Unknown mouse button.")

            return {
                "type": kind, "time": t,
                "x": int(item["x"]), "y": int(item["y"]),
                "button": button,
                "pressed": bool(item["pressed"])
            }

        elif kind == "scroll":
            return {
                "type": kind, "time": t,
                "x": int(item["x"]), "y": int(item["y"]),
                "dx": int(item["dx"]), "dy": int(item["dy"])
            }

        elif kind == "key":
            key_data = item["key"]

            if key_data["kind"] == "special":
                key = getattr(
                    pynput_keyboard.Key, key_data["value"], None
                )
                if key is None:
                    raise ValueError("Unknown keyboard key.")
            elif key_data["kind"] == "char":
                key = key_data["value"]
                if not isinstance(key, str) or len(key) != 1:
                    raise ValueError("Invalid character key.")
            else:
                raise ValueError("Unknown key type.")

            return {
                "type": kind, "time": t, "key": key,
                "pressed": bool(item["pressed"])
            }

        raise ValueError("Unknown action type.")

    def _load_macro_library(self):
        self.saved_macros = {}

        if not os.path.exists(self.macro_library_file):
            return

        try:
            with open(self.macro_library_file, "r", encoding="utf-8") as file:
                data = json.load(file)

            if data.get("format") != "nova-library-v1":
                raise ValueError("Unsupported library format.")

            macros = data.get("macros", {})
            if not isinstance(macros, dict):
                raise ValueError("Invalid macro library.")

            for name, raw_actions in macros.items():
                if not isinstance(name, str) or not name.strip():
                    continue
                if not isinstance(raw_actions, list) or len(raw_actions) > 500:
                    continue

                decoded = []
                last_time = -1.0

                for item in raw_actions:
                    action = self._macro_decode_action(item)
                    if action["time"] < last_time:
                        raise ValueError("Action times are out of order.")
                    last_time = action["time"]
                    decoded.append(action)

                self.saved_macros[name] = raw_actions

        except (OSError, ValueError, TypeError, KeyError, AttributeError,
                json.JSONDecodeError) as exc:
            messagebox.showwarning(
                "Macro Library",
                f"Could not load the macro library:\n{exc}"
            )
    
    def _load_recent_macros(self):
        """Load recent macros and remove items older than 24 hours."""
        self.recent_macros = {}

        if not os.path.exists(self.recent_macros_file):
            return

        try:
            with open(
                self.recent_macros_file, "r", encoding="utf-8"
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                raise ValueError("Invalid recent macro file format.")

            now = time.time()

            for macro_id, item in data.items():
                if not isinstance(item, dict):
                    continue

                created_at = item.get("created_at")
                actions = item.get("actions")

                if not isinstance(created_at, (int, float)):
                    continue

                if not isinstance(actions, list) or len(actions) > 500:
                    continue

                if now - created_at >= 24 * 60 * 60:
                    continue

                self.recent_macros[macro_id] = {
                    "created_at": created_at,
                    "actions": actions
                }

            self._save_recent_macros()

        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            messagebox.showwarning(
                "Recent Macros",
                f"Could not load recent macros:\n{exc}"
            )

    def _save_recent_macros(self):
        """Persist recent macros to a separate JSON file."""
        try:
            with open(
                self.recent_macros_file, "w", encoding="utf-8"
            ) as file:
                json.dump(
                    self.recent_macros,
                    file,
                    indent=2,
                    ensure_ascii=False
                )
        except (OSError, TypeError, ValueError) as exc:
            messagebox.showerror(
                "Recent Macros",
                f"Could not save recent macros:\n{exc}"
            )

    def _cleanup_recent_macros(self):
        """Delete recent macros that have expired after 24 hours."""
        now = time.time()
        expiry_seconds = 24 * 60 * 60

        expired_ids = [
            macro_id
            for macro_id, item in self.recent_macros.items()
            if now - item.get("created_at", 0) >= expiry_seconds
        ]

        for macro_id in expired_ids:
            del self.recent_macros[macro_id]

        if expired_ids:
            self._save_recent_macros()
    
    def _archive_current_macro(self):
        """Keep the current unsaved macro in Recent Macros."""
        with self.macro_lock:
            actions = list(self.macro_actions)

        if not actions:
            return

        self._cleanup_recent_macros()

        macro_id = f"recent_{int(time.time() * 1000)}"

        self.recent_macros[macro_id] = {
            "created_at": time.time(),
            "actions": actions
        }

        self._save_recent_macros()

    def _write_macro_library(self):
        temp_path = self.macro_library_file + ".tmp"

        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump({
                "format": "nova-library-v1",
                "macros": self.saved_macros
            }, file, ensure_ascii=False, indent=2)

        os.replace(temp_path, self.macro_library_file)

    def _save_macro(self):
        if self.macro_recording or self.macro_playing:
            messagebox.showwarning(
                "Macro Busy", "Stop recording or playback before saving."
            )
            return

        with self.macro_lock:
            actions = list(self.macro_actions)

        if not actions:
            messagebox.showinfo("No Macro", "Record some actions first.")
            return

        name = simpledialog.askstring(
            "Save Macro", "Enter a name for this task:", parent=self.root
        )

        if name is None:
            return

        name = name.strip()
        if not name or len(name) > 60 or any(c in name for c in "\r\n"):
            messagebox.showwarning(
                "Invalid Name", "Enter a name of 1–60 characters."
            )
            return

        existing = next(
            (n for n in self.saved_macros if n.casefold() == name.casefold()),
            None
        )

        if existing and not messagebox.askyesno(
            "Replace Task", f'"{existing}" already exists. Replace it?'
        ):
            return

        if existing:
            name = existing

        try:
            self.saved_macros[name] = [
                self._macro_encode_action(a) for a in actions
            ]
            self._write_macro_library()
            self._my_tasks_page()
            messagebox.showinfo("Saved", f'"{name}" saved successfully.')
        except (OSError, ValueError, TypeError, AttributeError) as exc:
            messagebox.showerror("Save Error", str(exc))

    
    def _load_macro(self):
        """Load a macro from a JSON file."""
        filepath = filedialog.askopenfilename(
            title="Load Macro",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as file:
                actions = json.load(file)

            if not isinstance(actions, list):
                raise ValueError("The selected file does not contain a valid macro list.")

            with self.macro_lock:
                self.macro_actions = actions

            self._macro_refresh_status("✓ MACRO LOADED", GREEN)
            messagebox.showinfo(
                "Load Macro",
                f"Successfully loaded {len(actions)} actions."
            )

        except Exception as exc:
            messagebox.showerror("Load Macro Error", str(exc))


    def _my_tasks_page(self):
        panel = tk.Frame(self.content, bg=BG)
        panel.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(
            panel, text="My Tasks", font=("Segoe UI", 22, "bold"),
            bg=BG, fg="white"
        ).pack(anchor="w", pady=(0, 12))

        card = tk.Frame(panel, bg=PANEL, padx=14, pady=14)
        card.pack(fill="both", expand=True)

        if not self.saved_macros:
            tk.Label(
                card, text="No saved tasks yet. Record and save a macro.",
                bg=PANEL, fg="#9ca3af", font=("Segoe UI", 11)
            ).pack(anchor="w", pady=15)
            return

        for name in sorted(self.saved_macros, key=str.casefold):
            row = tk.Frame(card, bg="#202938", padx=10, pady=8)
            row.pack(fill="x", pady=4)

            tk.Label(
                row, text=f"{name}  ({len(self.saved_macros[name])} actions)",
                bg="#202938", fg="white", font=("Segoe UI", 10, "bold")
            ).pack(side="left", fill="x", expand=True)

            tk.Button(
                row, text="▶ Play",
                command=lambda n=name: self._play_saved_macro(n),
                bg="#18794e", fg="white", relief="flat"
            ).pack(side="left", padx=3)

            tk.Button(
                row, text="Rename",
                command=lambda n=name: self._rename_saved_macro(n),
                bg="#365a91", fg="white", relief="flat"
            ).pack(side="left", padx=3)

            tk.Button(
                row, text="Delete",
                command=lambda n=name: self._delete_saved_macro(n),
                bg="#8b3038", fg="white", relief="flat"
            ).pack(side="left", padx=3)

    def _play_saved_macro(self, name):
        if self.macro_recording or self.macro_playing:
            messagebox.showwarning(
                "Macro Busy", "Stop the current activity first."
            )
            return

        try:
            actions = [
                self._macro_decode_action(item)
                for item in self.saved_macros[name]
            ]
            with self.macro_lock:
                self.macro_actions = actions

            self._start_macro_playback()

        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            messagebox.showerror("Playback Error", str(exc))

    def _rename_saved_macro(self, old_name):
        new_name = simpledialog.askstring(
            "Rename Task", "Enter the new name:",
            initialvalue=old_name, parent=self.root
        )

        if new_name is None:
            return

        new_name = new_name.strip()

        if not new_name or len(new_name) > 60:
            messagebox.showwarning("Invalid Name", "Enter a valid task name.")
            return

        conflict = next(
            (n for n in self.saved_macros
             if n.casefold() == new_name.casefold() and n != old_name),
            None
        )

        if conflict:
            messagebox.showwarning("Name Exists", "That name is already used.") 
            return

        if new_name == old_name:
            return

        self.saved_macros[new_name] = self.saved_macros.pop(old_name)

        try:
            self._write_macro_library()
            self._my_tasks_page()
        except OSError as exc:
            messagebox.showerror("Rename Error", str(exc))

    def _delete_saved_macro(self, name):
        if not messagebox.askyesno(
            "Delete Task", f'Delete "{name}" permanently?'
        ):
            return

        previous = self.saved_macros.pop(name, None)
        if previous is None:
            return

        try:
            self._write_macro_library()
            self._my_tasks_page()
        except OSError as exc:
            self.saved_macros[name] = previous
            messagebox.showerror("Delete Error", str(exc))   

   
    def _collapse_to_edge(self):
        if self.sidebar_collapsed:
            return

        self.expanded_geometry = self.root.geometry().split("+")[0]
        self.sidebar_collapsed = True

        # Hide the main NOVA window without destroying its interface
        self.root.withdraw()

        width = 52
        height = 180
        x = self.root.winfo_screenwidth() - width - 8
        y = (self.root.winfo_screenheight() - height) // 2

        # Create a separate floating window
        self.edge_bar = tk.Toplevel(self.root)
        self.edge_bar.overrideredirect(True)
        self.edge_bar.configure(bg="#0e1628")
        self.edge_bar.geometry(f"{width}x{height}+{x}+{y}")
        self.edge_bar.attributes("-topmost", True)

        tk.Button(
            self.edge_bar,
            text="✦",
            font=("Segoe UI", 20, "bold"),
            bg="#0e1628",
            fg="#7c9cff",
            activebackground="#243451",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self._expand_from_edge
        ).pack(fill="both", expand=True, padx=4, pady=4)


    
    def _expand_from_edge(self):
        if not self.sidebar_collapsed:
            return

        self.sidebar_collapsed = False

        if self.edge_bar is not None:
            try:
                self.edge_bar.destroy()
            except tk.TclError:
                pass
            self.edge_bar = None

        self.root.deiconify()
        self.root.overrideredirect(False)
        self.root.geometry(self.expanded_geometry)
        self.root.minsize(850, 600)
        self.root.state("normal")
        self.root.update_idletasks()
        self.root.lift()


    def _finish_macro_playback(self):
        """Reset playback state on the Tkinter main thread."""
        self.macro_playing = False
        self._macro_refresh_status("■ PLAYBACK STOPPED", GREEN)
    
    def _on_close(self):
        self.click_stop.set()

        try:
            self._stop_macro_recording()
        except Exception as exc:
            print("Macro recording cleanup:", exc)

        try:
            self._stop_macro_playback()
        except Exception as exc:
            print("Macro playback cleanup:", exc)

        try:
            keyboard.unhook_all()
        except Exception as exc:
            print("Keyboard cleanup:", exc)

        self.root.destroy()

def main():
    root = tk.Tk()
    NovaAutomationHub(root)
    root.mainloop()


if __name__ == "__main__":
    main()
