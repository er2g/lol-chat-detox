# -*- coding: utf-8 -*-
"""
Kalıcı WH_KEYBOARD_LL Enter yakalayıcı.

Neden keyboard.add_hotkey(suppress=True) yetmez:
  send_enter_raw() suppress kancasını SÖKÜP Enter basıyordu.
  O aralıkta (veya rebind fail olursa) fiziksel Enter oyuna ANINDA sızıyordu.

Bu hook:
  - Fiziksel Enter (VK_RETURN) her zaman yutulur (keydown+keyup)
  - SendInput ile basılan (LLKHF_INJECTED) Enter serbest geçer
  - Kanca gönderim sırasında ASLA kaldırılmaz
"""
import ctypes
import ctypes.wintypes
import threading
import time

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105
WM_QUIT = 0x0012

HC_ACTION = 0
VK_RETURN = 0x0D
VK_V = 0x56
VK_CONTROL = 0x11
LLKHF_INJECTED = 0x10
LLKHF_EXTENDED = 0x01

user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

INPUT_KEYBOARD = 1
KEYEVENTF_KEYUP = 0x0002
KEYEVENTF_EXTENDEDKEY = 0x0001


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", ctypes.wintypes.WORD),
        ("wScan", ctypes.wintypes.WORD),
        ("dwFlags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("ki", KEYBDINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.wintypes.DWORD),
        ("union", INPUT_UNION),
    ]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long,
    ctypes.c_int,
    ctypes.wintypes.WPARAM,
    ctypes.wintypes.LPARAM,
)


class EnterHook:
    """AI modunda Enter'ı kalıcı engelle + callback."""

    def __init__(self, on_physical_enter):
        """
        on_physical_enter: keydown anında çağrılır (hook thread'inden DEĞİL,
        ayrı thread'den — uzun iş hook'u bloklamasın).
        """
        self._on_physical = on_physical_enter
        self._hook = None
        self._thread = None
        self._tid = None
        self._ready = threading.Event()
        self._proc = None  # GC olmasın diye tut
        self._active = False
        self._lock = threading.Lock()
        # Ardışık keydown spam (auto-repeat) tek tetik
        self._down = False

    @property
    def active(self):
        return self._active and self._hook is not None

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return True
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._run, name="enter-ll-hook", daemon=True)
            self._thread.start()
        ok = self._ready.wait(timeout=3.0)
        return ok and self.active

    def stop(self):
        with self._lock:
            tid = self._tid
            self._active = False
            if tid:
                user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            t = self._thread
        if t and t.is_alive():
            t.join(timeout=2.0)
        with self._lock:
            self._thread = None
            self._tid = None
            self._hook = None
            self._down = False

    def _run(self):
        self._tid = kernel32.GetCurrentThreadId()
        self._proc = LowLevelKeyboardProc(self._callback)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            self._ready.set()
            return
        self._active = True
        self._ready.set()

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        self._active = False

    def _callback(self, nCode, wParam, lParam):
        try:
            if nCode == HC_ACTION and self._active:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if kb.vkCode == VK_RETURN:
                    injected = bool(kb.flags & LLKHF_INJECTED)
                    if injected:
                        # Bizim SendInput — oyuna geçsin
                        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

                    # Fiziksel Enter: her zaman yut
                    is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)
                    if is_down:
                        if not self._down:
                            self._down = True
                            # Hook'u bloklamadan callback
                            threading.Thread(
                                target=self._safe_fire, daemon=True).start()
                        return 1  # block
                    if is_up:
                        self._down = False
                        return 1  # block keyup da
        except Exception:
            pass
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _safe_fire(self):
        try:
            self._on_physical()
        except Exception:
            pass

    @staticmethod
    def send_enter_injected(extended=False):
        """Hook'u kaldırmadan oyuna Enter bas (LLKHF_INJECTED)."""
        def _one(flags):
            inp = INPUT()
            inp.type = INPUT_KEYBOARD
            inp.union.ki = KEYBDINPUT(
                wVk=VK_RETURN,
                wScan=0x1C,
                dwFlags=flags,
                time=0,
                dwExtraInfo=0,
            )
            return inp

        f0 = KEYEVENTF_EXTENDEDKEY if extended else 0
        f1 = f0 | KEYEVENTF_KEYUP
        arr = (INPUT * 2)(_one(f0), _one(f1))
        user32.SendInput(2, ctypes.byref(arr), ctypes.sizeof(INPUT))
        time.sleep(0.01)


class PasteHook:
    """Kalıcı WH_KEYBOARD_LL Ctrl+V yakalayıcı.

    Neden gerekli: LoL, oyun DIŞINDA kopyalanan pano içeriğini sentetik Ctrl+V
    ile KABUL ETMİYOR (canlı test edildi). Ama SendInput ile karakter karakter
    yazma ÇALIŞIYOR. Bu hook fiziksel Ctrl+V'yi yakalar, yerine callback'i
    tetikler (pano metnini oyuna 'yazarak' yapıştırmak için).

      - should_handle() True ise: Ctrl+V yutulur (keydown+keyup) + callback
      - False ise: hiç dokunulmaz, Ctrl+V normal geçer
      - SendInput ile basılan (LLKHF_INJECTED) V hiç ellenmez (kendi yazımımız)
    """

    def __init__(self, should_handle, on_paste):
        """
        should_handle: hook thread'inde çağrılır, HIZLI olmalı; True dönerse yut.
        on_paste: ayrı thread'den çağrılır (uzun iş hook'u bloklamasın).
        """
        self._should = should_handle
        self._on_paste = on_paste
        self._hook = None
        self._thread = None
        self._tid = None
        self._ready = threading.Event()
        self._proc = None  # GC olmasın diye tut
        self._active = False
        self._lock = threading.Lock()
        self._down = False  # Ctrl+V yakaladık mı (auto-repeat/keyup için)

    @property
    def active(self):
        return self._active and self._hook is not None

    def start(self):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return True
            self._ready.clear()
            self._thread = threading.Thread(
                target=self._run, name="paste-ll-hook", daemon=True)
            self._thread.start()
        ok = self._ready.wait(timeout=3.0)
        return ok and self.active

    def stop(self):
        with self._lock:
            tid = self._tid
            self._active = False
            if tid:
                user32.PostThreadMessageW(tid, WM_QUIT, 0, 0)
            t = self._thread
        if t and t.is_alive():
            t.join(timeout=2.0)
        with self._lock:
            self._thread = None
            self._tid = None
            self._hook = None
            self._down = False

    def _run(self):
        self._tid = kernel32.GetCurrentThreadId()
        self._proc = LowLevelKeyboardProc(self._callback)
        self._hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL, self._proc, None, 0)
        if not self._hook:
            self._ready.set()
            return
        self._active = True
        self._ready.set()

        msg = ctypes.wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self._hook:
            user32.UnhookWindowsHookEx(self._hook)
            self._hook = None
        self._active = False

    def _callback(self, nCode, wParam, lParam):
        try:
            if nCode == HC_ACTION and self._active:
                kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                if kb.vkCode == VK_V and not (kb.flags & LLKHF_INJECTED):
                    is_down = wParam in (WM_KEYDOWN, WM_SYSKEYDOWN)
                    is_up = wParam in (WM_KEYUP, WM_SYSKEYUP)
                    if is_down:
                        if self._down:
                            return 1  # auto-repeat da yutulsun
                        ctrl = bool(user32.GetAsyncKeyState(VK_CONTROL) & 0x8000)
                        if ctrl:
                            try:
                                handle = bool(self._should())
                            except Exception:
                                handle = False
                            if handle:
                                self._down = True
                                threading.Thread(
                                    target=self._safe_fire, daemon=True).start()
                                return 1  # block
                    elif is_up and self._down:
                        self._down = False
                        return 1  # keyup da yut
        except Exception:
            pass
        return user32.CallNextHookEx(self._hook, nCode, wParam, lParam)

    def _safe_fire(self):
        try:
            self._on_paste()
        except Exception:
            pass
