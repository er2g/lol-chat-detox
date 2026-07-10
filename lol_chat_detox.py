# -*- coding: utf-8 -*-
"""Geriye uyumluluk: headless motor. Tercih edilen giriş: lol_app.py / LoLDetox.exe"""
import sys
import time
import ctypes

ctypes.windll.user32.SetProcessDPIAware()

from lol_engine import DetoxEngine


def main():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "lol_chat_detox_tek")
    if ctypes.get_last_error() == 183:
        print("zaten calisan bir kopya var")
        sys.exit(0)

    engine = DetoxEngine()
    engine.start()
    print("headless detox. Cikis: Ctrl+C veya exit hotkey.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    engine.stop()


if __name__ == "__main__":
    main()
