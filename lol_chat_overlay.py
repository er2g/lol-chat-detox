# -*- coding: utf-8 -*-
"""
LoL chat algılayıcı test overlay'i.

Chat giriş kutusunun hemen altında click-through minik bir durum kutusu
gösterir: yeşil = ACIK, koyu = KAPALI. Borderless (penceresiz) modda çalışır.

Kullanım:
    python lol_chat_overlay.py [sure_saniye]   # varsayılan 300 (5 dk)
"""
import sys
import time
import ctypes

ctypes.windll.user32.SetProcessDPIAware()

import tkinter as tk
import mss
import lol_chat_detector as detector

# Overlay konumu: chat giriş kutusunun (y 1155-1187) hemen altı
POS_X, POS_Y = 30, 1200
WIDTH, HEIGHT = 190, 34
POLL_MS = 100

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020  # fare olaylarını alta geçir (click-through)
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080


def make_click_through(root):
    hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
    style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_NOACTIVATE | WS_EX_TOOLWINDOW
    ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)


def main():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "lol_overlay_tek")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return  # zaten çalışan overlay var

    # süre verilmezse sonsuz çalışır (watcher oyun kapanınca öldürür)
    duration = float(sys.argv[1]) if len(sys.argv) > 1 else None
    deadline = (time.time() + duration) if duration else None

    root = tk.Tk()
    root.overrideredirect(True)
    root.attributes("-topmost", True)
    root.attributes("-alpha", 0.85)
    root.geometry(f"{WIDTH}x{HEIGHT}+{POS_X}+{POS_Y}")

    label = tk.Label(root, text="...", font=("Segoe UI", 11, "bold"),
                     fg="white", bg="#222222")
    label.pack(fill="both", expand=True)

    root.update_idletasks()
    make_click_through(root)

    sct = mss.mss()
    stable = detector.StableState(open_frames=3, close_frames=2)

    visible = True

    def tick():
        nonlocal visible
        if deadline and time.time() > deadline:
            root.destroy()
            return
        if not detector.is_lol_foreground():
            if visible:
                root.withdraw()  # LoL ön planda değil: gizle
                visible = False
            root.after(300, tick)
            return
        if not visible:
            root.deiconify()
            root.update_idletasks()
            make_click_through(root)  # deiconify stilleri sıfırlayabilir
            visible = True
        raw_open, count = detector.decide(detector.grab_region_live(sct))
        is_open = stable.update(raw_open)
        if is_open:
            label.config(text=f"CHAT ACIK ({count})", bg="#1e7d32")
        else:
            label.config(text="CHAT KAPALI", bg="#333333")
        root.attributes("-topmost", True)  # oyun üstünü kapatmasın
        root.after(POLL_MS, tick)

    tick()
    root.mainloop()
    if sys.stdout is not None:  # pythonw altında konsol yok
        print("overlay kapandi")


if __name__ == "__main__":
    main()
