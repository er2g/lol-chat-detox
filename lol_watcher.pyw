# -*- coding: utf-8 -*-
"""
LoL detox watcher: Windows başlangıcında sessizce çalışır, 5 saniyede bir
oyun process'ine bakar. Oyun (League of Legends.exe) açılınca detox'u
başlatır, oyun kapanınca durdurur. Konsol penceresi açmaz (pythonw).
"""
import os
import sys
import time
import ctypes
import ctypes.wintypes
import subprocess

FROZEN = getattr(sys, "frozen", False)
DIR = os.path.dirname(
    sys.executable if FROZEN else os.path.abspath(__file__))
if FROZEN:
    # exe dağıtımı: kardeş exe'leri çalıştır
    CHILDREN = [
        [os.path.join(DIR, "LoLDetox.exe")],
        [os.path.join(DIR, "LoLOverlay.exe")],
    ]
else:
    PYTHONW = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    CHILDREN = [
        [PYTHONW, os.path.join(DIR, "lol_chat_detox.py")],
        [PYTHONW, os.path.join(DIR, "lol_chat_overlay.py")],
    ]
GAME_EXE = "league of legends.exe"

TH32CS_SNAPPROCESS = 0x2


class PROCESSENTRY32W(ctypes.Structure):
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


def game_running():
    k32 = ctypes.windll.kernel32
    snap = k32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == -1:
        return False
    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        if not k32.Process32FirstW(snap, ctypes.byref(entry)):
            return False
        while True:
            if entry.szExeFile.lower() == GAME_EXE:
                return True
            if not k32.Process32NextW(snap, ctypes.byref(entry)):
                return False
    finally:
        k32.CloseHandle(snap)


def main():
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "lol_detox_watcher_tek")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        return  # zaten çalışan watcher var

    procs = {i: None for i in range(len(CHILDREN))}
    while True:
        running = game_running()
        for i, cmd in enumerate(CHILDREN):
            if procs[i] is not None and procs[i].poll() is not None:
                procs[i] = None  # kendi kendine kapanmış
            if running and procs[i] is None:
                procs[i] = subprocess.Popen(cmd, cwd=DIR)
            elif not running and procs[i] is not None:
                procs[i].terminate()
                procs[i] = None
        time.sleep(5)


if __name__ == "__main__":
    main()
