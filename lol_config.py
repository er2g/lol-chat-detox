# -*- coding: utf-8 -*-
"""
LoL Chat Detox ayar yönetimi.

Veri dizini (config + loglar):  %APPDATA%\\LoLChatDetox\\
Exe/script dizini karışmaz — masaüstü temiz kalır.
"""
import os
import sys
import json
import copy
import shutil

# Kod / exe'nin bulunduğu yer (startup komutu için)
APP_DIR = os.path.dirname(
    sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))

# Kullanıcı verisi — Roaming AppData
DATA_DIR = os.path.join(
    os.environ.get("APPDATA") or os.path.expanduser("~"),
    "LoLChatDetox",
)

# Geriye uyumluluk: eski kod BASE_DIR = veri klasörü sanır
BASE_DIR = DATA_DIR

CONFIG_PATH = os.path.join(DATA_DIR, "config.json")
LOG_PATH = os.path.join(DATA_DIR, "lol_detox.log")
HISTORY_PATH = os.path.join(DATA_DIR, "lol_mesaj_gecmisi.log")

_DATA_FILES = ("config.json", "lol_detox.log", "lol_mesaj_gecmisi.log")


def _ensure_data_dir():
    """Klasörü oluştur; eski konumdaki (exe yanı / masaüstü) dosyaları bir kez taşı."""
    os.makedirs(DATA_DIR, exist_ok=True)

    legacy_dirs = []
    # exe / script yanı
    if APP_DIR and os.path.isdir(APP_DIR):
        legacy_dirs.append(APP_DIR)
    # masaüstü (kullanıcı exe'yi oraya koymuş olabilir)
    desk = os.path.join(os.path.expanduser("~"), "Desktop")
    if os.path.isdir(desk) and desk not in legacy_dirs:
        legacy_dirs.append(desk)
    desk_tr = os.path.join(os.path.expanduser("~"), "Masaüstü")
    if os.path.isdir(desk_tr) and desk_tr not in legacy_dirs:
        legacy_dirs.append(desk_tr)

    for name in _DATA_FILES:
        dest = os.path.join(DATA_DIR, name)
        if os.path.isfile(dest):
            continue
        for d in legacy_dirs:
            src = os.path.join(d, name)
            if os.path.isfile(src):
                try:
                    shutil.copy2(src, dest)
                except OSError:
                    pass
                break

    # Taşıma başarılıysa masaüstü / exe yanındaki kopyaları temizle (sadece veri dosyaları)
    for d in legacy_dirs:
        if os.path.normcase(os.path.abspath(d)) == os.path.normcase(
                os.path.abspath(DATA_DIR)):
            continue
        for name in _DATA_FILES:
            path = os.path.join(d, name)
            dest = os.path.join(DATA_DIR, name)
            if os.path.isfile(path) and os.path.isfile(dest):
                try:
                    os.remove(path)
                except OSError:
                    pass


_ensure_data_dir()

# Default AI prompt is English for global installs; Turkish via lol_i18n.default_prompt("tr")
import lol_i18n as _i18n  # noqa: E402

DEFAULT_PROMPT = _i18n.PROMPT_EN

DEFAULT_HOMOGLYPH = {
    "a": "а", "b": "Ь", "c": "с", "ç": "ҫ", "d": "ԁ", "e": "е", "f": "ƒ",
    "g": "ɡ", "ğ": "ǥ", "h": "һ", "i": "і", "ı": "ӏ", "j": "ј", "k": "к",
    "l": "ⅼ", "m": "м", "n": "ո", "o": "о", "ö": "ӧ", "p": "р", "q": "ԛ",
    "r": "ɾ", "s": "ѕ", "ş": "ʂ", "t": "т", "u": "υ", "ü": "ϋ", "v": "ν",
    "w": "ԝ", "x": "х", "y": "у", "z": "ᴢ",
    "A": "А", "B": "В", "C": "С", "Ç": "Ҫ", "D": "Ⅾ", "E": "Е", "F": "Ϝ",
    "G": "Ԍ", "Ğ": "Ǥ", "H": "Н", "I": "Ι", "İ": "І", "J": "Ј", "K": "К",
    "L": "Ⅼ", "M": "М", "N": "Ν", "O": "О", "Ö": "Ӧ", "P": "Р", "Q": "Ԛ",
    "R": "Я", "S": "Ѕ", "Ş": "Ȿ", "T": "Т", "U": "Ս", "Ü": "Ϋ", "V": "Ѵ",
    "W": "Ԝ", "X": "Х", "Y": "У", "Z": "Ζ",
}

MODES = ("ai", "non_ai")

DEFAULTS = {
    "language": "en",  # "en" | "tr"
    "mode": "non_ai",
    "enabled": True,
    "prompt": DEFAULT_PROMPT,
    "model": "gemini-3.1-flash-lite",
    "api_key": "",
    "exit_hotkey": "ctrl+alt+q",
    "toggle_hotkey": "ctrl+alt+d",
    "trigger_hotkey": "shift+enter",
    "ai_trigger_hotkey": "enter",
    "non_ai_auto_enter": False,  # Non-AI: shift gerekmeden sadece Enter ile sansür
    "paste_enabled": True,       # LoL dışından Ctrl+C → oyunda Ctrl+V (yazarak)
    "overlay_enabled": True,
    "run_only_when_game": True,
    "start_with_windows": False,
    "start_minimized": False,
    "homoglyph_map": copy.deepcopy(DEFAULT_HOMOGLYPH),
}

_BOOL_KEYS = {
    "enabled", "overlay_enabled", "run_only_when_game",
    "start_with_windows", "start_minimized",
    "non_ai_auto_enter", "paste_enabled",
}
_STR_KEYS = {
    "language", "mode", "prompt", "model", "api_key",
    "exit_hotkey", "toggle_hotkey", "trigger_hotkey", "ai_trigger_hotkey",
}


def _clean_homoglyph(hm):
    cleaned = {}
    if not isinstance(hm, dict):
        return copy.deepcopy(DEFAULT_HOMOGLYPH)
    for a, b in hm.items():
        if isinstance(a, str) and isinstance(b, str) and len(a) == 1 and b:
            cleaned[a] = b
    return cleaned or copy.deepcopy(DEFAULT_HOMOGLYPH)


def load_config():
    cfg = copy.deepcopy(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        data = {}
    if not isinstance(data, dict):
        data = {}

    for k in _STR_KEYS:
        v = data.get(k)
        if not isinstance(v, str):
            continue
        if k == "api_key":
            cfg[k] = v
        elif v.strip():
            cfg[k] = v

    for k in _BOOL_KEYS:
        if k in data:
            cfg[k] = bool(data[k])

    if "homoglyph_map" in data:
        cfg["homoglyph_map"] = _clean_homoglyph(data.get("homoglyph_map"))

    if cfg["mode"] not in MODES:
        cfg["mode"] = DEFAULTS["mode"]
    if "language" not in data:
        cfg["language"] = _i18n.detect_system_lang()
    elif cfg.get("language") not in ("en", "tr"):
        cfg["language"] = "en"
    return cfg


def save_config(cfg):
    """cfg kısmi olabilir; eksikler mevcut/default ile doldurulur."""
    current = load_config()
    merged = copy.deepcopy(current)
    for k in DEFAULTS:
        if k in cfg:
            merged[k] = cfg[k]

    if merged.get("mode") not in MODES:
        merged["mode"] = DEFAULTS["mode"]

    out = {}
    for k in _STR_KEYS:
        out[k] = str(merged.get(k, DEFAULTS[k]))
    for k in _BOOL_KEYS:
        out[k] = bool(merged.get(k, DEFAULTS[k]))
    out["homoglyph_map"] = _clean_homoglyph(merged.get("homoglyph_map"))

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def config_mtime():
    try:
        return os.path.getmtime(CONFIG_PATH)
    except OSError:
        return 0


def resolve_api_key(cfg=None):
    """config -> env -> registry."""
    if cfg is None:
        cfg = load_config()
    k = (cfg.get("api_key") or "").strip()
    if k:
        return k
    k = os.environ.get("GEMINI_API_KEY", "").strip()
    if k:
        return k
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            return winreg.QueryValueEx(h, "GEMINI_API_KEY")[0]
    except OSError:
        return ""


TASK_NAME = "LoLChatDetox"


def _startup_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --background'
    py = sys.executable
    app = os.path.join(APP_DIR, "lol_app.py")
    if py.lower().endswith("python.exe"):
        pyw = py[:-10] + "pythonw.exe"
        if os.path.isfile(pyw):
            py = pyw
    return f'"{py}" "{app}" --background'


def is_start_with_windows():
    import subprocess
    r = subprocess.run(
        ["schtasks", "/query", "/tn", TASK_NAME],
        capture_output=True, text=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    return r.returncode == 0


def set_start_with_windows(enabled: bool):
    import subprocess
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if not enabled:
        subprocess.run(
            ["schtasks", "/delete", "/f", "/tn", TASK_NAME],
            capture_output=True, creationflags=flags,
        )
        return True, "Startup task removed"

    cmd = _startup_command()
    r = subprocess.run(
        ["schtasks", "/create", "/f", "/tn", TASK_NAME,
         "/sc", "onlogon", "/rl", "highest", "/tr", cmd],
        capture_output=True, text=True, creationflags=flags,
    )
    if r.returncode != 0:
        r2 = subprocess.run(
            ["schtasks", "/create", "/f", "/tn", TASK_NAME,
             "/sc", "onlogon", "/rl", "limited", "/tr", cmd],
            capture_output=True, text=True, creationflags=flags,
        )
        if r2.returncode != 0:
            err = (r2.stderr or r.stderr or "unknown error").strip()
            return False, f"Could not create startup task: {err}"
    return True, "Start with Windows enabled"
