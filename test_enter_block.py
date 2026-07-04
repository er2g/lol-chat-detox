# -*- coding: utf-8 -*-
"""
Enter bloklama testi: 45 saniye boyunca Enter tuşunu yutar. Her basışta
350ms sonra ekrandan chat durumunu okur.

Eğer bloklamamıza rağmen chat ACILIYORSA -> LoL raw input kullanıyor,
LL-hook bloklaması oyuna işlemiyor demektir (Plan B gerekir).
Chat hep KAPALI kalıyorsa -> bloklama çalışıyor.
"""
import time
import ctypes
import threading

ctypes.windll.user32.SetProcessDPIAware()

import mss
import keyboard
import lol_chat_detector as detector


def on_enter():
    ts = time.strftime("%H:%M:%S")

    def check():
        time.sleep(0.35)
        with mss.mss() as sct:
            is_open, count = detector.decide(detector.grab_region_live(sct))
        durum = "ACIK (BLOKLAMA DELINDI!)" if is_open else "KAPALI (blok calisti)"
        print(f"[{ts}] Enter yakalandi+yutuldu -> chat: {durum} ({count}px)",
              flush=True)

    threading.Thread(target=check, daemon=True).start()


keyboard.add_hotkey("enter", on_enter, suppress=True)
print("Enter 45 saniye boyunca bloklaniyor - LoL icinde birkac kez Enter'a bas!",
      flush=True)
time.sleep(45)
print("test bitti", flush=True)
