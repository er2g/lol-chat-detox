# -*- coding: utf-8 -*-
"""
LoL Chat Detox motoru — UI'dan bağımsız, thread-safe start/stop/reload.

AI Enter yakalama: kalıcı WH_KEYBOARD_LL (lol_enter_hook).
SendInput ile gönderim — kanca asla sökülmez.
"""
import os
import sys
import json
import time
import ctypes
import ctypes.wintypes
import threading
import urllib.request

import keyboard
import mss

import lol_chat_detector as detector
import lol_config
import lol_homoglyph
from lol_enter_hook import EnterHook, PasteHook

PASTE_MODE = False
CHAT_BYTE_LIMIT = 120

IGNORED = {
    "enter", "esc", "tab", "shift", "sag shift", "sol shift", "ctrl",
    "left ctrl", "right ctrl", "alt", "alt gr", "caps lock", "up", "down",
    "left", "right", "home", "end", "delete", "insert", "page up",
    "page down", "windows", "left windows", "right windows",
}

TH32CS_SNAPPROCESS = 0x2
GAME_EXE = "league of legends.exe"

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


def split_chunks(text, limit=CHAT_BYTE_LIMIT):
    chunks, cur = [], ""
    for w in text.split(" "):
        cand = (cur + " " + w).strip()
        if len(cand.encode("utf-8")) <= limit:
            cur = cand
            continue
        if cur:
            chunks.append(cur)
        while len(w.encode("utf-8")) > limit:
            part = w.encode("utf-8")[:limit].decode("utf-8", errors="ignore")
            chunks.append(part)
            w = w[len(part):]
        cur = w
    if cur:
        chunks.append(cur)
    return chunks


def set_clipboard(text):
    CF_UNICODETEXT = 13
    GMEM_MOVEABLE = 0x2
    k32 = ctypes.windll.kernel32
    u32 = ctypes.windll.user32
    k32.GlobalAlloc.restype = ctypes.c_void_p
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.SetClipboardData.argtypes = [ctypes.c_uint, ctypes.c_void_p]
    data = text.encode("utf-16-le") + b"\x00\x00"
    if not u32.OpenClipboard(0):
        raise OSError("pano acilamadi")
    try:
        u32.EmptyClipboard()
        h = k32.GlobalAlloc(GMEM_MOVEABLE, len(data))
        p = k32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        k32.GlobalUnlock(h)
        u32.SetClipboardData(CF_UNICODETEXT, h)
    finally:
        u32.CloseClipboard()


def get_clipboard():
    """Panodaki Unicode metni oku (yoksa ""). Yapıştırma özelliği için."""
    CF_UNICODETEXT = 13
    k32 = ctypes.windll.kernel32
    u32 = ctypes.windll.user32
    k32.GlobalLock.restype = ctypes.c_void_p
    k32.GlobalLock.argtypes = [ctypes.c_void_p]
    k32.GlobalUnlock.argtypes = [ctypes.c_void_p]
    u32.GetClipboardData.restype = ctypes.c_void_p
    u32.GetClipboardData.argtypes = [ctypes.c_uint]
    if not u32.OpenClipboard(0):
        return ""
    try:
        h = u32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        p = k32.GlobalLock(h)
        if not p:
            return ""
        try:
            return ctypes.c_wchar_p(p).value or ""
        finally:
            k32.GlobalUnlock(h)
    finally:
        u32.CloseClipboard()


class DetoxEngine:
    def __init__(self, on_log=None, on_status=None):
        self._on_log = on_log
        self._on_status = on_status
        self.cfg = lol_config.load_config()
        self.lock = threading.RLock()
        self._enter_gate = threading.Lock()
        self.buffer = []
        self.chat_open = False
        self.injecting = False
        self._pass_enter = False  # sentetik Enter için
        self.enabled = bool(self.cfg.get("enabled", True))
        self.game_is_running = False
        self.hooks_active = False
        self._running = False
        self._stop = threading.Event()
        self._threads = []
        self._hotkey_handles = []
        self.enter_hotkey = None  # eski keyboard hotkey — kullanılmıyor (AI enter)
        self.trigger_hotkey = None  # non-ai veya özel ai trigger
        self._enter_hook = None  # kalıcı LL Enter yakalayıcı
        self._paste_hook = None  # kalıcı LL Ctrl+V yakalayıcı (dış pano yapıştır)
        self._key_hook = None
        self.last_log_lines = []
        self.BASE_DIR = lol_config.DATA_DIR
        self.LOG_PATH = lol_config.LOG_PATH
        self.HISTORY_PATH = lol_config.HISTORY_PATH

    # --- logging / status ---
    def log(self, msg):
        line = f"[{time.strftime('%H:%M:%S')}] {msg}"
        self.last_log_lines.append(line)
        self.last_log_lines = self.last_log_lines[-80:]
        if sys.stdout is not None:
            try:
                print(line, flush=True)
            except Exception:
                pass
        try:
            with open(self.LOG_PATH, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError:
            pass
        if self._on_log:
            try:
                self._on_log(line)
            except Exception:
                pass
        self._emit_status()

    def _emit_status(self):
        if not self._on_status:
            return
        try:
            self._on_status(self.status())
        except Exception:
            pass

    def status(self):
        return {
            "running": self._running,
            "enabled": self.enabled,
            "mode": self.cfg.get("mode", "non_ai"),
            "chat_open": self.chat_open,
            "game_running": self.game_is_running,
            "hooks_active": self.hooks_active,
            "overlay_enabled": bool(self.cfg.get("overlay_enabled", True)),
            "model": self.cfg.get("model", ""),
            "has_api_key": bool(lol_config.resolve_api_key(self.cfg)),
        }

    # --- lifecycle ---
    def start(self):
        if self._running:
            return
        self._stop.clear()
        self._running = True
        self.cfg = lol_config.load_config()
        self.enabled = bool(self.cfg.get("enabled", True))
        t1 = threading.Thread(target=self._detector_loop, daemon=True, name="detox-detect")
        t2 = threading.Thread(target=self._game_loop, daemon=True, name="detox-game")
        self._threads = [t1, t2]
        t1.start()
        t2.start()
        self._sync_hooks()
        self.log(f"motor basladi (mod={self.cfg.get('mode')})")
        self._emit_status()

    def stop(self):
        self._running = False
        self._stop.set()
        self._unbind_hooks()
        self.log("motor durdu")
        self._emit_status()

    def apply_config(self, cfg=None, rebind=True):
        with self.lock:
            old = self.cfg
            self.cfg = cfg if cfg is not None else lol_config.load_config()
            if "enabled" in self.cfg:
                self.enabled = bool(self.cfg["enabled"])
            need = rebind and (
                old.get("mode") != self.cfg.get("mode")
                or old.get("exit_hotkey") != self.cfg.get("exit_hotkey")
                or old.get("toggle_hotkey") != self.cfg.get("toggle_hotkey")
                or old.get("trigger_hotkey") != self.cfg.get("trigger_hotkey")
                or old.get("ai_trigger_hotkey") != self.cfg.get("ai_trigger_hotkey")
                or old.get("non_ai_auto_enter") != self.cfg.get("non_ai_auto_enter")
                or old.get("run_only_when_game") != self.cfg.get("run_only_when_game")
            )
        if need:
            self._sync_hooks()
        self.log(f"ayarlar uygulandi (mod={self.cfg.get('mode')}, enabled={self.enabled})")
        self._emit_status()

    def set_mode(self, mode):
        if mode not in lol_config.MODES:
            return
        with self.lock:
            self.cfg["mode"] = mode
        lol_config.save_config(self.cfg)
        self.apply_config(self.cfg, rebind=True)

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        with self.lock:
            self.cfg["enabled"] = self.enabled
        lol_config.save_config(self.cfg)
        self.log(f"detox {'ACIK' if self.enabled else 'KAPALI'}")
        self._emit_status()

    # --- hooks ---
    def _remove_hotkey(self, handle):
        if handle is None:
            return
        try:
            keyboard.remove_hotkey(handle)
        except (KeyError, ValueError, Exception):
            pass

    def _stop_enter_hook(self):
        if self._enter_hook is not None:
            try:
                self._enter_hook.stop()
            except Exception:
                pass
            self._enter_hook = None

    def _stop_paste_hook(self):
        if self._paste_hook is not None:
            try:
                self._paste_hook.stop()
            except Exception:
                pass
            self._paste_hook = None

    def _unbind_hooks(self):
        for h in self._hotkey_handles:
            self._remove_hotkey(h)
        self._hotkey_handles = []
        self._remove_hotkey(self.enter_hotkey)
        self._remove_hotkey(self.trigger_hotkey)
        self.enter_hotkey = None
        self.trigger_hotkey = None
        self._stop_enter_hook()
        self._stop_paste_hook()
        if self._key_hook is not None:
            try:
                keyboard.unhook(self._key_hook)
            except Exception:
                pass
            self._key_hook = None
        self.hooks_active = False

    def _bind_hooks(self):
        self._unbind_hooks()
        cfg = self.cfg
        try:
            self._hotkey_handles = [
                keyboard.add_hotkey(cfg["exit_hotkey"], self._on_exit_hotkey),
                keyboard.add_hotkey(cfg["toggle_hotkey"], self._on_toggle_hotkey),
            ]
            mode = cfg.get("mode", "non_ai")
            if mode == "ai":
                ai_hk = (cfg.get("ai_trigger_hotkey") or "enter").strip().lower()
                if ai_hk == "enter":
                    # KRİTİK: keyboard suppress YOK — kalıcı LL hook.
                    # Eski yol send_enter_raw'da suppress söküyordu → Enter sızıyordu.
                    self._enter_hook = EnterHook(self._on_ai_trigger)
                    if not self._enter_hook.start():
                        raise RuntimeError("Enter LL-hook baslatilamadi")
                    self.log("Enter LL-hook AKTIF (fiziksel enter her zaman yutulur)")
                else:
                    self.trigger_hotkey = keyboard.add_hotkey(
                        ai_hk, self._on_ai_trigger, suppress=True)
            else:
                trig = (cfg.get("trigger_hotkey") or "shift+enter").strip().lower()
                auto_enter = bool(cfg.get("non_ai_auto_enter"))
                # Otomatik sansür: shift gerekmeden sadece Enter → LL hook.
                # (trigger "enter" yazıldıysa da aynı yol.)
                if auto_enter or trig == "enter":
                    self._enter_hook = EnterHook(self._on_non_ai_trigger)
                    if not self._enter_hook.start():
                        raise RuntimeError("Enter LL-hook baslatilamadi")
                    self.log("Non-AI otomatik sansür AKTIF (her Enter yakalanır)")
                else:
                    self.trigger_hotkey = keyboard.add_hotkey(
                        trig, self._on_non_ai_trigger, suppress=True)
            # Dış pano yapıştırma kancası (mod bağımsız — chat açıkken Ctrl+V)
            self._paste_hook = PasteHook(self._should_paste, self._on_paste)
            if not self._paste_hook.start():
                self._paste_hook = None
                self.log("! Ctrl+V yapistirma kancasi baslatilamadi")
            self._key_hook = keyboard.on_press(self._on_key)
            self.hooks_active = True
            self.log(
                f"klavye kancalari aktif (mod={mode}, "
                f"trigger={cfg.get('trigger_hotkey') if mode != 'ai' else cfg.get('ai_trigger_hotkey')})"
            )
        except Exception as e:
            self.hooks_active = False
            self._stop_enter_hook()
            self._stop_paste_hook()
            self.log(f"! kanca hatasi: {e}")

    def _sync_hooks(self):
        want = True
        if self.cfg.get("run_only_when_game", True) and not self.game_is_running:
            want = False
        if not self._running:
            want = False
        if want and not self.hooks_active:
            self._bind_hooks()
        elif not want and self.hooks_active:
            self._unbind_hooks()
            self.log("klavye kancalari kapandi (oyun yok / motor kapali)")
        elif want and self.hooks_active:
            # zaten açık — config rebind için _bind_hooks apply_config'ten gelir
            pass
        self._emit_status()

    def _on_exit_hotkey(self):
        self.log("cikis kisayolu — detox kapatiliyor")
        self.set_enabled(False)
        if self._on_status:
            try:
                self._on_status({**self.status(), "request_quit": True})
            except Exception:
                pass

    def _on_toggle_hotkey(self):
        self.set_enabled(not self.enabled)
        try:
            import winsound
            winsound.Beep(880 if self.enabled else 330, 180)
        except Exception:
            pass

    # --- game / detector loops ---
    def _game_loop(self):
        while not self._stop.is_set():
            running = game_running()
            if running != self.game_is_running:
                self.game_is_running = running
                self.log(f"oyun {'ACIK' if running else 'KAPALI'}")
                self._sync_hooks()
                self._emit_status()
            time.sleep(2)

    def _detector_loop(self):
        sct = mss.mss()
        stable = detector.StableState(open_frames=3, close_frames=2)
        while not self._stop.is_set():
            try:
                if detector.is_lol_foreground():
                    raw_open, _ = detector.decide(detector.grab_region_live(sct))
                else:
                    raw_open = False
                is_open = stable.update(raw_open)
                if is_open != self.chat_open:
                    self.log(f"chat {'ACIK' if is_open else 'KAPALI'}")
                    if not is_open:
                        with self.lock:
                            self.buffer = []
                    self.chat_open = is_open
                    self._emit_status()
            except Exception as e:
                self.log(f"! detector: {e}")
            time.sleep(0.05)

    # --- rewrite ---
    def rewrite_with_gemini(self, text):
        api_key = lol_config.resolve_api_key(self.cfg)
        if not api_key:
            raise RuntimeError("Gemini API anahtari yok")
        url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
               f"{self.cfg['model']}:generateContent?key={api_key}")
        prompt = self.cfg["prompt"].replace("{msg}", text)
        body = json.dumps({
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 200},
        }).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        out = out.replace("\n", " ").strip().strip('"').strip()
        letters = [c for c in text if c.isalpha()]
        if letters:
            upper_ratio = sum(c.isupper() for c in letters) / len(letters)
            if upper_ratio > 0.8:
                out = out.replace("i", "İ").replace("ı", "I").upper()
            elif upper_ratio < 0.2:
                out = out.replace("İ", "i").replace("I", "ı").lower()
        return out

    def rewrite_text(self, text):
        if self.cfg.get("mode") == "non_ai":
            return lol_homoglyph.rewrite_homoglyph(text, self.cfg), "non_ai"
        return self.rewrite_with_gemini(text), "ai"

    def log_history(self, original, detoxed, kind="detox"):
        try:
            with open(self.HISTORY_PATH, "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} [{kind}]\n"
                        f"  ORJINAL: {original}\n"
                        f"  SONUC  : {detoxed}\n")
        except OSError:
            pass

    def send_enter_raw(self):
        """Oyuna Enter bas — kancayı ASLA sökme.
        LL-hook varken: SendInput (injected) serbest geçer.
        Hook yokken: keyboard.send.
        """
        with self._enter_gate:
            self._pass_enter = True
            try:
                if self._enter_hook is not None and self._enter_hook.active:
                    EnterHook.send_enter_injected()
                else:
                    keyboard.send("enter")
            finally:
                # kısa gecikme: injected keyup bitsin
                time.sleep(0.02)
                self._pass_enter = False

    def process_and_send(self, text):
        try:
            self.log(f"yakalanan: {text!r} (mod={self.cfg.get('mode')})")
            self.injecting = True
            if PASTE_MODE:
                keyboard.send("ctrl+a")
                keyboard.send("backspace")
            for _ in range(len(text) + 5):
                keyboard.send("backspace")

            try:
                new_text, kind = self.rewrite_text(text)
            except Exception as e:
                self.log(f"! rewrite hatasi ({e}), mesaj gonderilmiyor")
                return
            self.log(f"{kind}: {new_text!r}")
            self.log_history(text, new_text, kind=kind)

            chunks = split_chunks(new_text)
            for i, chunk in enumerate(chunks):
                if i > 0:
                    self.send_enter_raw()
                    time.sleep(0.25)
                if PASTE_MODE:
                    set_clipboard(chunk)
                    keyboard.send("ctrl+v")
                else:
                    keyboard.write(chunk, delay=0.005)
                time.sleep(0.2 + len(chunk) * 0.004)
                self.send_enter_raw()
                time.sleep(0.15)
            if len(chunks) > 1:
                self.log(f"{len(chunks)} parcada gonderildi")
        finally:
            self.injecting = False

    # --- dış pano yapıştırma (Ctrl+V) ---
    def _should_paste(self):
        """PasteHook (hook thread) tarafından çağrılır — HIZLI olmalı.
        Sadece chat açıkken ve yapıştırma açıkken devral; yoksa Ctrl+V normal
        geçsin. injecting sırasında (kendi yazımımız) devralma."""
        return (
            bool(self.cfg.get("paste_enabled", True))
            and self.chat_open
            and not self.injecting
        )

    def _on_paste(self):
        """Ctrl+V yakalandı — pano metnini oyuna yazarak yapıştır."""
        if self.injecting:
            return
        text = get_clipboard()
        if not text:
            return
        threading.Thread(
            target=self._paste_text, args=(text,), daemon=True,
            name="detox-paste",
        ).start()

    def _paste_text(self, text):
        # Chat tek satır: yeni satırları boşluğa çevir (erken göndermesin).
        text = text.replace("\r", " ").replace("\n", " ")
        text = "".join(ch for ch in text if ch >= " " or ch == "\t").strip()
        if not text:
            return
        with self._enter_gate:
            self.injecting = True
            try:
                preview = text[:40] + ("…" if len(text) > 40 else "")
                self.log(f"yapistir: {preview!r} ({len(text)} krkt)")
                keyboard.write(text, delay=0.005)
                # Buffer'ı ekranla eşle: Enter'da detox doğru sayıda backspace atsın
                with self.lock:
                    self.buffer.extend(list(text))
            finally:
                time.sleep(0.03)
                self.injecting = False

    def _take_buffer(self):
        with self.lock:
            text = "".join(self.buffer).strip()
            self.buffer = []
        return text

    def _start_detox(self, text, source):
        if not text:
            return False
        threading.Thread(
            target=self.process_and_send, args=(text,), daemon=True,
            name=f"detox-{source}",
        ).start()
        return True

    def _on_ai_trigger(self):
        """AI modu tetikleyicisi (varsayılan Enter — LL hook)."""
        if self._pass_enter or self.injecting:
            return
        if not self.enabled or not self.chat_open:
            self.send_enter_raw()
            return
        text = self._take_buffer()
        if not text:
            self.log("enter: buffer BOS")
            self.send_enter_raw()
            return
        self._start_detox(text, "ai")

    def _on_non_ai_trigger(self):
        """Non-AI sansür tetikleyicisi (varsayılan shift+enter)."""
        if self._pass_enter or self.injecting:
            return
        if not self.enabled or not self.chat_open:
            self.send_enter_raw()
            return
        text = self._take_buffer()
        if not text:
            self.log("trigger: buffer BOS")
            self.send_enter_raw()
            return
        self._start_detox(text, "non_ai")

    def _on_key(self, event):
        if self.injecting or not self.enabled or not self.chat_open:
            return
        name = event.name
        if name is None or name in IGNORED:
            # Non-AI + shift+enter tetikleyicide: shift'siz düz Enter "ham gönder"
            # demektir → buffer'ı temizle. AMA otomatik sansür (düz Enter tetik)
            # açıksa Enter'ı _on_non_ai_trigger devralır; burada temizleME.
            auto_enter = (
                bool(self.cfg.get("non_ai_auto_enter"))
                or (self.cfg.get("trigger_hotkey") or "").strip().lower() == "enter"
            )
            if (name == "enter"
                    and self.cfg.get("mode") == "non_ai"
                    and not auto_enter
                    and not keyboard.is_pressed("shift")):
                with self.lock:
                    self.buffer = []
            return
        with self.lock:
            if name == "backspace":
                if self.buffer:
                    self.buffer.pop()
            elif name == "space":
                self.buffer.append(" ")
            elif len(name) == 1:
                if keyboard.is_pressed("shift"):
                    self.buffer.append(name.upper())
                else:
                    self.buffer.append(name)
