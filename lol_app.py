# -*- coding: utf-8 -*-
"""
LoL Chat Detox — tek premium uygulama.

  python lol_app.py              # arayüz
  python lol_app.py --background # arka planda (PC açılışı)

PyInstaller: LoLDetox.spec → dist/LoLDetox.exe
"""
import os
import sys
import json
import copy
import time
import ctypes
import ctypes.wintypes
import threading
import queue

ctypes.windll.user32.SetProcessDPIAware()

import tkinter as tk
from tkinter import ttk, messagebox

import lol_config
from lol_engine import DetoxEngine
import lol_homoglyph
import lol_chat_detector as detector
import lol_i18n
from lol_i18n import t

# ── tema ──────────────────────────────────────────────
BG = "#0f1115"
BG2 = "#161a22"
BG3 = "#1c2230"
CARD = "#1a1f2b"
BORDER = "#2a3344"
FG = "#e8ecf4"
FG_DIM = "#8b95a8"
FG_MUTED = "#5c677a"
ACCENT = "#6c5ce7"
ACCENT2 = "#00cec9"
GREEN = "#00b894"
RED = "#ff6b6b"
ORANGE = "#fdcb6e"
SIDEBAR_W = 200


def _font(size=10, weight="normal"):
    return ("Segoe UI", size, weight)


# Eski / takılı kalmış kopyalar
_KILL_NAMES = {
    "loldetox.exe",
    "loldetoxwatcher.exe",
    "loloverlay.exe",
    "loldetoxsettings.exe",
}

TH32CS_SNAPPROCESS = 0x2


class _PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", ctypes.wintypes.DWORD),
        ("cntUsage", ctypes.wintypes.DWORD),
        ("th32ProcessID", ctypes.wintypes.DWORD),
        ("th32DefaultHeapID", ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID", ctypes.wintypes.DWORD),
        ("cntThreads", ctypes.wintypes.DWORD),
        ("th32ParentProcessID", ctypes.wintypes.DWORD),
        ("pcPriClassBase", ctypes.wintypes.LONG),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


def kill_other_instances():
    """Açılışta eski LoLDetox / watcher / overlay process'lerini öldür."""
    import ctypes.wintypes  # noqa: F401 — _PROCESSENTRY32W için
    k32 = ctypes.windll.kernel32
    my_pid = os.getpid()
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return
    killed = 0
    try:
        entry = _PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(_PROCESSENTRY32W)
        if not k32.Process32FirstW(snap, ctypes.byref(entry)):
            return
        while True:
            name = entry.szExeFile.lower()
            pid = entry.th32ProcessID
            if pid != my_pid and name in _KILL_NAMES:
                h = k32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
                if h:
                    if k32.TerminateProcess(h, 0):
                        killed += 1
                    k32.CloseHandle(h)
            if not k32.Process32NextW(snap, ctypes.byref(entry)):
                break
    finally:
        k32.CloseHandle(snap)
    if killed:
        time.sleep(0.4)
    return killed


class OverlayWindow:
    """Ana Tk üzerinde click-through durum kutusu."""

    POS_X, POS_Y = 30, 1200
    WIDTH, HEIGHT = 200, 36

    def __init__(self, root, engine: DetoxEngine):
        self.root = root
        self.engine = engine
        self.win = None
        self.label = None
        self.visible = False
        self._job = None

    def ensure(self):
        if self.win is not None:
            return
        w = tk.Toplevel(self.root)
        w.overrideredirect(True)
        w.attributes("-topmost", True)
        w.attributes("-alpha", 0.88)
        w.geometry(f"{self.WIDTH}x{self.HEIGHT}+{self.POS_X}+{self.POS_Y}")
        w.configure(bg="#222")
        lab = tk.Label(w, text="...", font=_font(10, "bold"),
                       fg="white", bg="#222")
        lab.pack(fill="both", expand=True)
        w.update_idletasks()
        self._click_through(w)
        w.withdraw()  # varsayılan gizli — sadece LoL ön planda göster
        self.win = w
        self.label = lab
        self.visible = False

    def _click_through(self, w):
        GWL_EXSTYLE = -20
        WS_EX_LAYERED = 0x00080000
        WS_EX_TRANSPARENT = 0x00000020
        WS_EX_NOACTIVATE = 0x08000000
        WS_EX_TOOLWINDOW = 0x00000080
        hwnd = ctypes.windll.user32.GetParent(w.winfo_id())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)

    def hide(self):
        if self.win is not None and self.visible:
            self.win.withdraw()
            self.visible = False

    def show(self):
        self.ensure()
        if not self.visible:
            self.win.deiconify()
            self.win.update_idletasks()
            self._click_through(self.win)
            self.visible = True

    def destroy(self):
        if self._job:
            try:
                self.root.after_cancel(self._job)
            except Exception:
                pass
        if self.win is not None:
            try:
                self.win.destroy()
            except Exception:
                pass
        self.win = None
        self.label = None
        self.visible = False

    def tick(self):
        st = self.engine.status()
        # Sadece League of Legends.exe ÖN PLANDAYKEN göster.
        # Process arka planda açık diye overlay masaüstünde kalmamalı.
        try:
            lol_fg = detector.is_lol_foreground()
        except Exception:
            lol_fg = False
        want = (
            bool(st.get("overlay_enabled"))
            and self.engine._running
            and lol_fg
        )
        if not want:
            self.hide()
        else:
            self.show()
            if self.label is not None:
                if st.get("chat_open"):
                    mode = st.get("mode", "?")
                    self.label.config(
                        text=f"{t('overlay_chat_open')} · {mode.upper()}",
                        bg="#1e7d32")
                else:
                    en = "ON" if st.get("enabled") else "OFF"
                    self.label.config(
                        text=f"{t('overlay_chat_closed')} · {en}",
                        bg="#333333")
                try:
                    self.win.attributes("-topmost", True)
                except Exception:
                    pass
        self._job = self.root.after(200, self.tick)


class App:
    def __init__(self, start_background=False):
        self.root = tk.Tk()
        self.root.title(t("app_title"))
        self.root.geometry("980x700")
        self.root.minsize(880, 600)
        self.root.configure(bg=BG)
        # Özel başlık çubuğu — Windows çerçevesini kapat
        self.root.overrideredirect(True)
        try:
            self.root.iconbitmap(default="")
        except Exception:
            pass

        self.msg_q = queue.Queue()
        self.engine = DetoxEngine(
            on_log=lambda line: self.msg_q.put(("log", line)),
            on_status=lambda st: self.msg_q.put(("status", st)),
        )
        self.cfg = lol_config.load_config()
        lol_i18n.set_lang(self.cfg.get("language", "en"))
        # sync real startup task state
        self.cfg["start_with_windows"] = lol_config.is_start_with_windows()

        self._page = "dashboard"
        self._widgets = {}
        self._status = self.engine.status()
        self._log_buffer = []
        self._drag_x = 0
        self._drag_y = 0
        self._is_maximized = False
        self._geom_before_max = None

        self._build_ui()
        self._apply_rounded_shadow()
        self.overlay = OverlayWindow(self.root, self.engine)
        self.engine.start()
        self.overlay.tick()
        self._poll_queue()
        self._refresh_status_ui()

        # X = tam kapanış
        self.root.protocol("WM_DELETE_WINDOW", self._quit_app)
        self.root.bind("<Map>", self._on_map)
        if start_background or self.cfg.get("start_minimized"):
            self.root.withdraw()
        else:
            self.root.deiconify()
            self._center_window()

    def _hwnd(self):
        self.root.update_idletasks()
        wid = self.root.winfo_id()
        parent = ctypes.windll.user32.GetParent(wid)
        return parent or wid

    def _center_window(self):
        self.root.update_idletasks()
        w, h = 980, 700
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _apply_rounded_shadow(self):
        """Win11 DWM: koyu başlık hissi (opsiyonel)."""
        try:
            hwnd = self._hwnd()
            # DWMWA_USE_IMMERSIVE_DARK_MODE = 20
            val = ctypes.c_int(1)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
        except Exception:
            pass

    def _on_map(self, _event=None):
        # minimize sonrası geri gelince borderless kalsın
        try:
            self.root.overrideredirect(True)
        except Exception:
            pass

    # ── custom titlebar ───────────────────────────────
    def _build_titlebar(self, parent):
        bar = tk.Frame(parent, bg=BG2, height=40)
        bar.pack(fill="x", side="top")
        bar.pack_propagate(False)

        left = tk.Frame(bar, bg=BG2)
        left.pack(side="left", fill="y", padx=12)
        tk.Label(left, text="◈", bg=BG2, fg=ACCENT2,
                 font=_font(12, "bold")).pack(side="left", pady=8)
        tk.Label(left, text=f"  {t('app_title')}", bg=BG2, fg=FG,
                 font=_font(10, "bold")).pack(side="left", pady=8)

        # sürükle
        for w in (bar, left):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._do_drag)
            w.bind("<Double-Button-1>", self._toggle_max)

        # sağ kontroller: küçült | simge (tray) | kapat
        right = tk.Frame(bar, bg=BG2)
        right.pack(side="right", fill="y")

        def winbtn(text, cmd, hover_bg, hover_fg=FG):
            b = tk.Label(
                right, text=text, bg=BG2, fg=FG_DIM,
                font=_font(11), width=4, cursor="hand2",
            )
            b.pack(side="left", fill="y")
            b.bind("<Enter>", lambda e, bb=b, h=hover_bg, f=hover_fg: bb.config(bg=h, fg=f))
            b.bind("<Leave>", lambda e, bb=b: bb.config(bg=BG2, fg=FG_DIM))
            b.bind("<Button-1>", lambda e: cmd())
            return b

        winbtn("─", self._minimize_taskbar, BG3)       # görev çubuğuna küçült
        winbtn("▢", self._toggle_max, BG3)             # max / restore
        winbtn("↓", self._minimize_tray, BG3)          # arka plan (motor çalışır)
        winbtn("✕", self._quit_app, "#c0392b", "#fff")  # tam kapat

        return bar

    def _start_drag(self, event):
        if self._is_maximized:
            return
        self._drag_x = event.x_root - self.root.winfo_x()
        self._drag_y = event.y_root - self.root.winfo_y()

    def _do_drag(self, event):
        if self._is_maximized:
            return
        x = event.x_root - self._drag_x
        y = event.y_root - self._drag_y
        self.root.geometry(f"+{x}+{y}")

    def _minimize_taskbar(self):
        """Görev çubuğuna küçült (simge durumuna al)."""
        try:
            # borderless pencerede iconify bozulabiliyor → WinAPI
            hwnd = self._hwnd()
            SW_MINIMIZE = 6
            ctypes.windll.user32.ShowWindow(hwnd, SW_MINIMIZE)
        except Exception:
            self.root.iconify()

    def _minimize_tray(self):
        """Arka plana al (pencere gizlenir, motor çalışır)."""
        self.root.withdraw()

    def _toggle_max(self, _event=None):
        if not self._is_maximized:
            self._geom_before_max = self.root.geometry()
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            # görev çubuğu payı
            self.root.geometry(f"{sw}x{sh - 40}+0+0")
            self._is_maximized = True
        else:
            if self._geom_before_max:
                self.root.geometry(self._geom_before_max)
            else:
                self._center_window()
            self._is_maximized = False

    def _restore_window(self):
        """Arka plandan geri getir."""
        self.root.deiconify()
        self.root.overrideredirect(True)
        self.root.lift()
        try:
            hwnd = self._hwnd()
            SW_RESTORE = 9
            ctypes.windll.user32.ShowWindow(hwnd, SW_RESTORE)
            ctypes.windll.user32.SetForegroundWindow(hwnd)
        except Exception:
            pass

    # ── layout ────────────────────────────────────────
    def _build_ui(self):
        # özel titlebar en üstte
        self._build_titlebar(self.root)

        shell = tk.Frame(self.root, bg=BG)
        shell.pack(fill="both", expand=True)

        # sidebar
        side = tk.Frame(shell, bg=BG2, width=SIDEBAR_W)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        brand = tk.Frame(side, bg=BG2)
        brand.pack(fill="x", pady=(16, 14), padx=16)
        tk.Label(brand, text="LoL Detox", bg=BG2, fg=FG,
                 font=_font(14, "bold")).pack(anchor="w")
        tk.Label(brand, text=t("brand_sub"), bg=BG2, fg=ACCENT2,
                 font=_font(8)).pack(anchor="w")

        self.nav_btns = {}
        for key, label_key in [
            ("dashboard", "nav_dashboard"),
            ("mode", "nav_mode"),
            ("ai", "nav_ai"),
            ("homoglyph", "nav_homoglyph"),
            ("hotkeys", "nav_hotkeys"),
            ("system", "nav_system"),
            ("logs", "nav_logs"),
        ]:
            label = t(label_key)
            b = tk.Button(
                side, text=f"  {label}", anchor="w",
                bg=BG2, fg=FG_DIM, activebackground=BG3,
                activeforeground=FG, relief="flat", bd=0,
                font=_font(10), cursor="hand2",
                command=lambda k=key: self._show_page(k),
            )
            b.pack(fill="x", padx=8, pady=2, ipady=8)
            self.nav_btns[key] = b

        tk.Frame(side, bg=BG2).pack(fill="both", expand=True)
        self.side_status = tk.Label(
            side, text=t("side_starting"), bg=BG2, fg=FG_MUTED,
            font=_font(8), anchor="w", justify="left")
        self.side_status.pack(fill="x", padx=16, pady=16)

        # main
        main = tk.Frame(shell, bg=BG)
        main.pack(side="left", fill="both", expand=True)
        self.header = tk.Frame(main, bg=BG)
        self.header.pack(fill="x", padx=28, pady=(20, 8))
        self.header_title = tk.Label(
            self.header, text="Dashboard", bg=BG, fg=FG, font=_font(18, "bold"))
        self.header_title.pack(side="left")
        self.header_sub = tk.Label(
            self.header, text="", bg=BG, fg=FG_DIM, font=_font(9))
        self.header_sub.pack(side="left", padx=12, pady=(6, 0))

        self.content = tk.Frame(main, bg=BG)
        self.content.pack(fill="both", expand=True, padx=28, pady=(0, 20))

        self.pages = {}
        self.pages["dashboard"] = self._page_dashboard(self.content)
        self.pages["mode"] = self._page_mode(self.content)
        self.pages["ai"] = self._page_ai(self.content)
        self.pages["homoglyph"] = self._page_homoglyph(self.content)
        self.pages["hotkeys"] = self._page_hotkeys(self.content)
        self.pages["system"] = self._page_system(self.content)
        self.pages["logs"] = self._page_logs(self.content)

        self._show_page("dashboard")

    def _card(self, parent, **kw):
        f = tk.Frame(parent, bg=CARD, highlightbackground=BORDER,
                     highlightthickness=1, **kw)
        return f

    def _section_title(self, parent, text):
        tk.Label(parent, text=text, bg=CARD, fg=FG,
                 font=_font(11, "bold")).pack(anchor="w", padx=16, pady=(14, 6))

    def _hint(self, parent, text):
        tk.Label(parent, text=text, bg=CARD, fg=FG_MUTED,
                 font=_font(8), wraplength=640, justify="left").pack(
            anchor="w", padx=16, pady=(0, 10))

    def _btn(self, parent, text, cmd, accent=False, danger=False):
        bg = ACCENT if accent else (RED if danger else BG3)
        b = tk.Button(
            parent, text=text, command=cmd, bg=bg, fg=FG,
            activebackground=ACCENT2 if accent else BG2,
            activeforeground=FG, relief="flat", bd=0,
            font=_font(9, "bold"), cursor="hand2", padx=16, pady=8,
        )
        return b

    # ── pages ─────────────────────────────────────────
    def _page_dashboard(self, parent):
        page = tk.Frame(parent, bg=BG)

        # status cards row
        row = tk.Frame(page, bg=BG)
        row.pack(fill="x", pady=(0, 12))
        self.stat_labels = {}
        for key, title_key in [
            ("enabled", "stat_detox"),
            ("mode", "stat_mode"),
            ("game", "stat_game"),
            ("chat", "stat_chat"),
            ("hooks", "stat_hooks"),
        ]:
            title = t(title_key)
            c = self._card(row)
            c.pack(side="left", fill="both", expand=True, padx=(0, 10))
            tk.Label(c, text=title, bg=CARD, fg=FG_MUTED,
                     font=_font(8)).pack(anchor="w", padx=14, pady=(12, 0))
            lab = tk.Label(c, text="—", bg=CARD, fg=FG,
                           font=_font(13, "bold"))
            lab.pack(anchor="w", padx=14, pady=(2, 14))
            self.stat_labels[key] = lab

        # quick actions
        act = self._card(page)
        act.pack(fill="x", pady=(0, 12))
        self._section_title(act, t("quick_controls"))
        self._hint(act, t("quick_hint"))

        bar = tk.Frame(act, bg=CARD)
        bar.pack(fill="x", padx=16, pady=(0, 16))

        self.btn_toggle = self._btn(bar, t("btn_toggle"), self._quick_toggle, accent=True)
        self.btn_toggle.pack(side="left", padx=(0, 8))
        self._btn(bar, t("btn_ai_mode"), lambda: self._quick_mode("ai")).pack(
            side="left", padx=(0, 8))
        self._btn(bar, t("btn_non_ai_mode"), lambda: self._quick_mode("non_ai")).pack(
            side="left", padx=(0, 8))
        self._btn(bar, t("btn_save_all"), self._save_all, accent=True).pack(
            side="left", padx=(0, 8))

        # live log snippet
        logc = self._card(page)
        logc.pack(fill="both", expand=True)
        self._section_title(logc, t("live_log"))
        self.dash_log = tk.Text(
            logc, height=10, bg=BG3, fg=FG_DIM, insertbackground=FG,
            relief="flat", font=("Consolas", 9), wrap="word",
            state="disabled")
        self.dash_log.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        return page

    def _page_mode(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="x")
        self._section_title(c, t("mode_title"))
        self._hint(c, t("mode_hint"))

        self.mode_var = tk.StringVar(value=self.cfg.get("mode", "non_ai"))
        for val, title, desc in [
            ("non_ai", t("mode_non_ai"), t("mode_non_ai_desc")),
            ("ai", t("mode_ai"), t("mode_ai_desc")),
        ]:
            fr = tk.Frame(c, bg=BG3, highlightbackground=BORDER, highlightthickness=1)
            fr.pack(fill="x", padx=16, pady=6)
            rb = tk.Radiobutton(
                fr, text=title, variable=self.mode_var, value=val,
                bg=BG3, fg=FG, selectcolor=BG2, activebackground=BG3,
                activeforeground=FG, font=_font(10, "bold"),
                command=self._on_mode_radio,
            )
            rb.pack(anchor="w", padx=12, pady=(10, 2))
            tk.Label(fr, text=desc, bg=BG3, fg=FG_MUTED,
                     font=_font(8), wraplength=700, justify="left").pack(
                anchor="w", padx=28, pady=(0, 12))

        # Non-AI otomatik sansür: shift gerekmeden sadece Enter
        self.var_auto_censor = tk.BooleanVar(
            value=bool(self.cfg.get("non_ai_auto_enter", False)))
        tk.Checkbutton(
            c, text=t("auto_censor_chk"), variable=self.var_auto_censor,
            bg=CARD, fg=FG, selectcolor=BG2, activebackground=CARD,
            activeforeground=FG, font=_font(10), anchor="w",
            command=self._on_auto_censor_toggle,
        ).pack(fill="x", padx=16, pady=(6, 0))
        self._hint(c, t("auto_censor_hint"))

        self._btn(c, t("btn_save_mode"), self._apply_mode_page,
                  accent=True).pack(anchor="w", padx=16, pady=(8, 16))
        return page

    def _on_auto_censor_toggle(self):
        self.cfg["non_ai_auto_enter"] = bool(self.var_auto_censor.get())
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=True)
        self.cfg = lol_config.load_config()
        self._toast(t("auto_censor_on") if self.cfg["non_ai_auto_enter"]
                    else t("auto_censor_off"))

    def _page_ai(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="both", expand=True)
        self._section_title(c, t("ai_title"))
        self._hint(c, t("ai_hint"))

        row = tk.Frame(c, bg=CARD)
        row.pack(fill="x", padx=16, pady=4)
        tk.Label(row, text=t("api_key"), bg=CARD, fg=FG_DIM,
                 font=_font(9)).pack(anchor="w")
        self.api_entry = tk.Entry(
            row, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
            font=("Consolas", 10), show="•")
        self.api_entry.pack(fill="x", ipady=8, pady=(4, 0))
        self.api_entry.insert(0, self.cfg.get("api_key", ""))

        row2 = tk.Frame(c, bg=CARD)
        row2.pack(fill="x", padx=16, pady=(12, 4))
        tk.Label(row2, text=t("model"), bg=CARD, fg=FG_DIM,
                 font=_font(9)).pack(anchor="w")
        self.model_entry = tk.Entry(
            row2, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
            font=("Consolas", 10))
        self.model_entry.pack(fill="x", ipady=8, pady=(4, 0))
        self.model_entry.insert(0, self.cfg.get("model", ""))

        tk.Label(c, text=t("prompt_label"), bg=CARD, fg=FG_DIM,
                 font=_font(9)).pack(anchor="w", padx=16, pady=(12, 4))
        self.prompt_box = tk.Text(
            c, height=14, bg=BG3, fg=FG, insertbackground=FG,
            relief="flat", font=("Consolas", 9), wrap="word")
        self.prompt_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self.prompt_box.insert("1.0", self.cfg.get("prompt", ""))

        bar = tk.Frame(c, bg=CARD)
        bar.pack(fill="x", padx=16, pady=(0, 16))
        self._btn(bar, t("btn_save_ai"), self._save_ai, accent=True).pack(
            side="left")
        self._btn(bar, t("btn_default_prompt"), self._reset_prompt).pack(
            side="left", padx=8)
        return page

    def _page_homoglyph(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="both", expand=True)
        self._section_title(c, t("homo_title"))
        self._hint(c, t("homo_hint"))

        self.homo_box = tk.Text(
            c, height=18, bg=BG3, fg=FG, insertbackground=FG,
            relief="flat", font=("Consolas", 10), wrap="none")
        self.homo_box.pack(fill="both", expand=True, padx=16, pady=(0, 8))
        self._load_homo_json()

        prev = tk.Frame(c, bg=CARD)
        prev.pack(fill="x", padx=16, pady=(0, 8))
        tk.Label(prev, text=t("preview_label"), bg=CARD, fg=FG_DIM,
                 font=_font(9)).pack(anchor="w")
        self.preview_in = tk.Entry(
            prev, bg=BG3, fg=FG, insertbackground=FG, relief="flat",
            font=("Consolas", 10))
        self.preview_in.pack(fill="x", ipady=6, pady=(4, 4))
        self.preview_in.insert(0, t("preview_default"))
        self.preview_out = tk.Label(
            prev, text="", bg=BG3, fg=ACCENT2, font=("Consolas", 11),
            anchor="w", justify="left", wraplength=700)
        self.preview_out.pack(fill="x", ipady=8, padx=0)

        bar = tk.Frame(c, bg=CARD)
        bar.pack(fill="x", padx=16, pady=(0, 16))
        self._btn(bar, t("btn_save_homo"), self._save_homo, accent=True).pack(
            side="left")
        self._btn(bar, t("btn_preview"), self._preview_homo).pack(side="left", padx=8)
        self._btn(bar, t("btn_default_homo"), self._reset_homo).pack(side="left")
        return page

    def _page_hotkeys(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="x")
        self._section_title(c, t("hotkeys_title"))
        self._hint(c, t("hotkeys_hint"))

        grid = tk.Frame(c, bg=CARD)
        grid.pack(fill="x", padx=16, pady=(0, 16))

        def field(r, label, key):
            tk.Label(grid, text=label, bg=CARD, fg=FG_DIM,
                     font=_font(9)).grid(row=r, column=0, sticky="w", pady=6)
            e = tk.Entry(grid, bg=BG3, fg=FG, insertbackground=FG,
                         relief="flat", font=("Consolas", 10), width=24)
            e.grid(row=r, column=1, sticky="w", padx=12, ipady=6)
            e.insert(0, self.cfg.get(key, lol_config.DEFAULTS.get(key, "")))
            return e

        self.exit_hk = field(0, t("hk_exit"), "exit_hotkey")
        self.toggle_hk = field(1, t("hk_toggle"), "toggle_hotkey")
        self.trigger_hk = field(2, t("hk_trigger"), "trigger_hotkey")
        self.ai_trigger_hk = field(3, t("hk_ai_trigger"), "ai_trigger_hotkey")
        self._btn(c, t("btn_save_hotkeys"), self._save_hotkeys,
                  accent=True).pack(anchor="w", padx=16, pady=(0, 16))
        return page

    def _page_system(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="x")
        self._section_title(c, t("sys_title"))

        self.var_overlay = tk.BooleanVar(value=bool(self.cfg.get("overlay_enabled", True)))
        self.var_game_only = tk.BooleanVar(value=bool(self.cfg.get("run_only_when_game", True)))
        self.var_startup = tk.BooleanVar(value=bool(self.cfg.get("start_with_windows", False)))
        self.var_min = tk.BooleanVar(value=bool(self.cfg.get("start_minimized", False)))
        self.var_enabled = tk.BooleanVar(value=bool(self.cfg.get("enabled", True)))
        self.var_paste = tk.BooleanVar(value=bool(self.cfg.get("paste_enabled", True)))

        def chk(text, var):
            tk.Checkbutton(
                c, text=text, variable=var, bg=CARD, fg=FG,
                selectcolor=BG2, activebackground=CARD, activeforeground=FG,
                font=_font(10), anchor="w",
            ).pack(fill="x", padx=16, pady=4)

        chk(t("chk_enabled"), self.var_enabled)
        chk(t("chk_paste"), self.var_paste)
        chk(t("chk_overlay"), self.var_overlay)
        chk(t("chk_game_only"), self.var_game_only)
        chk(t("chk_startup"), self.var_startup)
        chk(t("chk_minimized"), self.var_min)

        self._hint(c, t("sys_hint"))

        bar = tk.Frame(c, bg=CARD)
        bar.pack(fill="x", padx=16, pady=16)
        self._btn(bar, t("btn_save_system"), self._save_system,
                  accent=True).pack(side="left")
        self._btn(bar, t("btn_minimize"), self._minimize_taskbar).pack(
            side="left", padx=8)
        self._btn(bar, t("btn_tray"), self._minimize_tray).pack(
            side="left", padx=8)
        self._btn(bar, t("btn_quit"), self._quit_app, danger=True).pack(
            side="left")

        # language
        langc = self._card(page)
        langc.pack(fill="x", pady=(12, 0))
        self._section_title(langc, t("lang_title"))
        self._hint(langc, t("lang_hint"))
        self.lang_var = tk.StringVar(value=self.cfg.get("language", "en"))
        lr = tk.Frame(langc, bg=CARD)
        lr.pack(fill="x", padx=16, pady=(0, 8))
        for code, label in (("en", "English"), ("tr", "Türkçe")):
            tk.Radiobutton(
                lr, text=label, variable=self.lang_var, value=code,
                bg=CARD, fg=FG, selectcolor=BG2, activebackground=CARD,
                activeforeground=FG, font=_font(10),
            ).pack(side="left", padx=(0, 18))
        self._btn(langc, t("btn_save_lang"), self._apply_language,
                  accent=True).pack(anchor="w", padx=16, pady=(0, 16))

        info = self._card(page)
        info.pack(fill="x", pady=(12, 0))
        self._section_title(info, t("files_title"))
        tk.Label(
            info,
            text=f"Data: {lol_config.DATA_DIR}\n"
                 f"Config: {lol_config.CONFIG_PATH}\n"
                 f"Log: {lol_config.LOG_PATH}\n"
                 f"History: {lol_config.HISTORY_PATH}",
            bg=CARD, fg=FG_DIM, font=("Consolas", 8), justify="left",
        ).pack(anchor="w", padx=16, pady=(0, 16))
        return page

    def _page_logs(self, parent):
        page = tk.Frame(parent, bg=BG)
        c = self._card(page)
        c.pack(fill="both", expand=True)
        self._section_title(c, t("logs_title"))
        self.log_text = tk.Text(
            c, bg=BG3, fg=FG_DIM, insertbackground=FG, relief="flat",
            font=("Consolas", 9), wrap="word", state="disabled")
        self.log_text.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        return page

    # ── navigation ────────────────────────────────────
    def _show_page(self, key):
        self._page = key
        titles = {
            "dashboard": (t("hdr_dashboard"), t("hdr_dashboard_sub")),
            "mode": (t("hdr_mode"), t("hdr_mode_sub")),
            "ai": (t("hdr_ai"), t("hdr_ai_sub")),
            "homoglyph": (t("hdr_homoglyph"), t("hdr_homoglyph_sub")),
            "hotkeys": (t("hdr_hotkeys"), t("hdr_hotkeys_sub")),
            "system": (t("hdr_system"), t("hdr_system_sub")),
            "logs": (t("hdr_logs"), t("hdr_logs_sub")),
        }
        title, sub = titles.get(key, (key, ""))
        self.header_title.config(text=title)
        self.header_sub.config(text=sub)
        for k, fr in self.pages.items():
            if k == key:
                fr.pack(fill="both", expand=True)
            else:
                fr.pack_forget()
        for k, b in self.nav_btns.items():
            if k == key:
                b.config(bg=BG3, fg=FG)
            else:
                b.config(bg=BG2, fg=FG_DIM)

    # ── actions ───────────────────────────────────────
    def _collect_from_forms(self):
        """UI alanlarından cfg birleştir (homoglyph parse ayrı)."""
        cfg = copy.deepcopy(self.cfg)
        if hasattr(self, "mode_var"):
            cfg["mode"] = self.mode_var.get()
        if hasattr(self, "api_entry"):
            cfg["api_key"] = self.api_entry.get().strip()
            cfg["model"] = self.model_entry.get().strip() or cfg["model"]
            cfg["prompt"] = self.prompt_box.get("1.0", "end").strip()
        if hasattr(self, "exit_hk"):
            cfg["exit_hotkey"] = self.exit_hk.get().strip().lower()
            cfg["toggle_hotkey"] = self.toggle_hk.get().strip().lower()
            cfg["trigger_hotkey"] = self.trigger_hk.get().strip().lower()
            cfg["ai_trigger_hotkey"] = self.ai_trigger_hk.get().strip().lower()
        if hasattr(self, "var_overlay"):
            cfg["overlay_enabled"] = self.var_overlay.get()
            cfg["run_only_when_game"] = self.var_game_only.get()
            cfg["start_with_windows"] = self.var_startup.get()
            cfg["start_minimized"] = self.var_min.get()
            cfg["enabled"] = self.var_enabled.get()
            cfg["paste_enabled"] = self.var_paste.get()
        if hasattr(self, "var_auto_censor"):
            cfg["non_ai_auto_enter"] = self.var_auto_censor.get()
        return cfg

    def _parse_homo(self):
        raw = self.homo_box.get("1.0", "end").strip()
        data = json.loads(raw)
        if not isinstance(data, dict):
            raise ValueError("JSON bir nesne ({{ }}) olmalı")
        cleaned = {}
        for a, b in data.items():
            if not (isinstance(a, str) and len(a) == 1):
                raise ValueError(f"Anahtar tek karakter olmalı: {a!r}")
            if not isinstance(b, str) or not b:
                raise ValueError(f"Değer boş olamaz: {a!r}")
            cleaned[a] = b
        if not cleaned:
            raise ValueError("Harita boş olamaz")
        return cleaned

    def _load_homo_json(self):
        self.homo_box.delete("1.0", "end")
        self.homo_box.insert(
            "1.0",
            json.dumps(self.cfg.get("homoglyph_map", {}),
                       ensure_ascii=False, indent=2))

    def _toast(self, msg, ok=True):
        self.header_sub.config(text=msg, fg=GREEN if ok else RED)
        self.root.after(3500, lambda: self.header_sub.config(
            text="", fg=FG_DIM))

    def _quick_toggle(self):
        self.engine.set_enabled(not self.engine.enabled)
        self.cfg["enabled"] = self.engine.enabled
        if hasattr(self, "var_enabled"):
            self.var_enabled.set(self.engine.enabled)
        self._toast(t("detox_on") if self.engine.enabled else t("detox_off"))

    def _quick_mode(self, mode):
        self.mode_var.set(mode)
        self.cfg["mode"] = mode
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=True)
        self.cfg = lol_config.load_config()
        self._toast(f"{t('mode_set')}: {mode}")

    def _on_mode_radio(self):
        # anlık uygula
        self._quick_mode(self.mode_var.get())

    def _apply_mode_page(self):
        self._on_mode_radio()

    def _save_ai(self):
        prompt = self.prompt_box.get("1.0", "end").strip()
        if "{msg}" not in prompt:
            messagebox.showerror("Error", t("err_prompt_msg"))
            return
        model = self.model_entry.get().strip()
        if not model:
            messagebox.showerror("Error", t("err_model"))
            return
        self.cfg["api_key"] = self.api_entry.get().strip()
        self.cfg["model"] = model
        self.cfg["prompt"] = prompt
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=False)
        self.cfg = lol_config.load_config()
        self._toast(t("saved_ai"))

    def _reset_prompt(self):
        self.prompt_box.delete("1.0", "end")
        self.prompt_box.insert("1.0", lol_i18n.default_prompt())

    def _save_homo(self):
        try:
            cleaned = self._parse_homo()
        except Exception as e:
            messagebox.showerror(t("err_json"), str(e))
            return
        self.cfg["homoglyph_map"] = cleaned
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=False)
        self.cfg = lol_config.load_config()
        self._load_homo_json()
        self._preview_homo()
        self._toast(t("saved_homo"))

    def _preview_homo(self):
        try:
            cleaned = self._parse_homo()
        except Exception as e:
            self.preview_out.config(text=f"Hata: {e}", fg=RED)
            return
        cfg = {"homoglyph_map": cleaned}
        src = self.preview_in.get()
        out = lol_homoglyph.rewrite_homoglyph(src, cfg)
        self.preview_out.config(text=out, fg=ACCENT2)

    def _reset_homo(self):
        self.cfg["homoglyph_map"] = copy.deepcopy(lol_config.DEFAULT_HOMOGLYPH)
        self._load_homo_json()
        self._toast(t("default_homo_loaded"))

    def _save_hotkeys(self):
        import keyboard
        exit_hk = self.exit_hk.get().strip().lower()
        toggle_hk = self.toggle_hk.get().strip().lower()
        trig_hk = self.trigger_hk.get().strip().lower()
        ai_hk = self.ai_trigger_hk.get().strip().lower()
        pairs = (
            ("Çıkış", exit_hk),
            ("Aç/Kapa", toggle_hk),
            ("Non-AI tetikleyici", trig_hk),
            ("AI tetikleyici", ai_hk),
        )
        for name, v in pairs:
            if not v:
                messagebox.showerror("Error", f"{name} {t('err_hotkey_empty')}")
                return
            try:
                keyboard.parse_hotkey(v)
            except ValueError:
                messagebox.showerror("Error", f"{t('err_hotkey')}: {v}")
                return
        vals = [exit_hk, toggle_hk, trig_hk, ai_hk]
        if len(set(vals)) != len(vals):
            messagebox.showerror("Error", t("err_hotkeys_unique"))
            return
        self.cfg["exit_hotkey"] = exit_hk
        self.cfg["toggle_hotkey"] = toggle_hk
        self.cfg["trigger_hotkey"] = trig_hk
        self.cfg["ai_trigger_hotkey"] = ai_hk
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=True)
        self.cfg = lol_config.load_config()
        self._toast(t("saved_hotkeys"))

    def _save_system(self):
        self.cfg["enabled"] = self.var_enabled.get()
        self.cfg["overlay_enabled"] = self.var_overlay.get()
        self.cfg["run_only_when_game"] = self.var_game_only.get()
        self.cfg["start_minimized"] = self.var_min.get()
        self.cfg["paste_enabled"] = self.var_paste.get()
        want_startup = self.var_startup.get()
        ok, msg = lol_config.set_start_with_windows(want_startup)
        self.cfg["start_with_windows"] = lol_config.is_start_with_windows()
        self.var_startup.set(self.cfg["start_with_windows"])
        lol_config.save_config(self.cfg)
        self.engine.apply_config(lol_config.load_config(), rebind=True)
        self.engine.set_enabled(self.cfg["enabled"])
        self.cfg = lol_config.load_config()
        if ok:
            self._toast(msg)
        else:
            messagebox.showwarning(t("warn_startup"), msg)
            self._toast(msg, ok=False)

    def _apply_language(self):
        lang = self.lang_var.get()
        if lang not in lol_i18n.LANGS:
            lang = "en"
        self.cfg["language"] = lang
        # Offer language-matched default prompt when switching
        self.cfg["prompt"] = lol_i18n.default_prompt(lang)
        lol_config.save_config(self.cfg)
        lol_i18n.set_lang(lang)
        messagebox.showinfo(
            t("lang_title"),
            t("lang_applied") + "\n\n"
            "Please restart the app for full UI language refresh.\n"
            "Tam arayüz dili için uygulamayı yeniden başlatın.",
        )
        self._toast(t("lang_applied"))

    def _save_all(self):
        """Tüm formları kaydetmeye çalış."""
        try:
            if hasattr(self, "homo_box"):
                self.cfg["homoglyph_map"] = self._parse_homo()
        except Exception as e:
            messagebox.showerror("Homoglyph JSON", str(e))
            return
        cfg = self._collect_from_forms()
        cfg["homoglyph_map"] = self.cfg.get("homoglyph_map", cfg.get("homoglyph_map"))
        if cfg.get("mode") == "ai" and "{msg}" not in (cfg.get("prompt") or ""):
            messagebox.showerror("Error", t("err_prompt_msg"))
            return
        if hasattr(self, "lang_var"):
            cfg["language"] = self.lang_var.get()
        want_startup = cfg.get("start_with_windows", False)
        ok, msg = lol_config.set_start_with_windows(want_startup)
        cfg["start_with_windows"] = lol_config.is_start_with_windows()
        lol_config.save_config(cfg)
        self.cfg = lol_config.load_config()
        self.engine.apply_config(self.cfg, rebind=True)
        self.engine.set_enabled(self.cfg["enabled"])
        self.mode_var.set(self.cfg["mode"])
        self.var_startup.set(self.cfg["start_with_windows"])
        if ok:
            self._toast(t("saved_all"))
        else:
            self._toast(f"{t('saved')}; startup: {msg}", ok=False)

    # ── status / log UI ───────────────────────────────
    def _poll_queue(self):
        try:
            while True:
                kind, payload = self.msg_q.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "status":
                    self._status = payload
                    if payload.get("request_quit"):
                        # çıkış kısayolu → tam kapanış
                        self.root.after(0, self._quit_app)
                    self._refresh_status_ui()
        except queue.Empty:
            pass
        self.root.after(120, self._poll_queue)

    def _append_log(self, line):
        self._log_buffer.append(line)
        self._log_buffer = self._log_buffer[-200:]
        for widget in (getattr(self, "dash_log", None),
                       getattr(self, "log_text", None)):
            if widget is None:
                continue
            widget.config(state="normal")
            widget.insert("end", line + "\n")
            widget.see("end")
            # trim
            if float(widget.index("end-1c").split(".")[0]) > 300:
                widget.delete("1.0", "50.0")
            widget.config(state="disabled")

    def _refresh_status_ui(self):
        st = self._status or self.engine.status()
        def set_stat(key, text, color=FG):
            lab = self.stat_labels.get(key)
            if lab:
                lab.config(text=text, fg=color)

        set_stat("enabled",
                 t("on") if st.get("enabled") else t("off"),
                 GREEN if st.get("enabled") else RED)
        set_stat("mode", (st.get("mode") or "?").upper(), ACCENT2)
        set_stat("game",
                 t("open") if st.get("game_running") else t("none"),
                 GREEN if st.get("game_running") else FG_MUTED)
        set_stat("chat",
                 t("open") if st.get("chat_open") else t("closed"),
                 GREEN if st.get("chat_open") else FG_MUTED)
        set_stat("hooks",
                 t("active") if st.get("hooks_active") else t("passive"),
                 GREEN if st.get("hooks_active") else ORANGE)

        side = []
        side.append(f"● detox {'on' if st.get('enabled') else 'off'}")
        side.append(f"  mode: {st.get('mode')}")
        side.append(f"  game: {'yes' if st.get('game_running') else 'no'}")
        self.side_status.config(
            text="\n".join(side),
            fg=GREEN if st.get("enabled") else FG_MUTED)

    def _quit_app(self, _event=None):
        """Full quit: engine + overlay."""
        try:
            self.overlay.destroy()
        except Exception:
            pass
        try:
            self.engine.stop()
        except Exception:
            pass
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def run(self):
        self.root.mainloop()


def _take_single_instance():
    """Eski kopyaları öldür, sonra mutex al. Takılı kopya kalmasın."""
    kill_other_instances()
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    # Eski mutex adları da dahil — orphaned mutex sorun çıkarmasın diye
    # yeni ad + biraz bekle
    time.sleep(0.15)
    k32.CreateMutexW(None, False, "lol_chat_detox_app_tek_v2")
    # Hâlâ başka kopya varsa (kill edemedik) tekrar dene
    if ctypes.get_last_error() == 183:
        kill_other_instances()
        time.sleep(0.3)
        k32.CreateMutexW(None, False, "lol_chat_detox_app_tek_v2")
        if ctypes.get_last_error() == 183:
            # Son çare: yine de devam et (kullanıcı açmak istedi)
            return True
    return True


def main():
    background = "--background" in sys.argv or "-b" in sys.argv
    _take_single_instance()
    app = App(start_background=background)
    app.run()


if __name__ == "__main__":
    main()
