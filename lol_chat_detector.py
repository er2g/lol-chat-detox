# -*- coding: utf-8 -*-
"""
LoL chat açık/kapalı algılayıcı.

Mantık: Chat açıkken sol altta beliren giriş kutusundaki mavi kanal etiketi
("[Takım]" / "[Herkes]", ~RGB(64,193,255)) taranır. Etiket 2560x1600
çözünürlükte X[48-97] Y[1163-1178] bölgesinde; tarama kutusu tolerans için
biraz geniş tutuldu.

Kullanım:
    python lol_chat_detector.py            # canlı izleme (Ctrl+C ile çık)
    python lol_chat_detector.py test <png> # kayıtlı ekran görüntüsünde dene
"""
import sys
import time
import ctypes

# Fiziksel çözünürlükte yakalama için (DPI ölçeklemesini atla)
ctypes.windll.user32.SetProcessDPIAware()

# Tarama bölgesi (2560x1600 içindir; [Herkes] için sağa pay bırakıldı)
REGION = {"left": 30, "top": 1155, "width": 150, "height": 32}

# Mavi etiket renk kuralı ve eşik
MIN_BLUE_PIXELS = 25

class StableState:
    """Milisaniyelik parlamaları eler: durum ancak art arda N karede
    aynı okuma gelirse değişir."""

    def __init__(self, open_frames=3, close_frames=2):
        self.open_frames = open_frames
        self.close_frames = close_frames
        self.state = False
        self._streak = 0

    def update(self, raw_open):
        if raw_open == self.state:
            self._streak = 0
            return self.state
        self._streak += 1
        needed = self.open_frames if raw_open else self.close_frames
        if self._streak >= needed:
            self.state = raw_open
            self._streak = 0
        return self.state


_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000


def is_lol_foreground():
    """Ön plandaki pencere LoL oyun istemcisi mi?"""
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return False
    pid = ctypes.c_ulong()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    h = kernel32.OpenProcess(_PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
    if not h:
        return False
    try:
        buf = ctypes.create_unicode_buffer(260)
        size = ctypes.c_ulong(260)
        if not kernel32.QueryFullProcessImageNameW(h, 0, buf, ctypes.byref(size)):
            return False
        return buf.value.lower().endswith("league of legends.exe")
    finally:
        kernel32.CloseHandle(h)


def is_label_pixel(r, g, b):
    return b > 180 and (b - r) > 60 and (b - g) > 40


def count_blue(pixels):
    """pixels: (r,g,b) üçlüleri listesi. Mavi piksel sayısı ve satır dağılımı döner."""
    count = 0
    rows = set()
    w = REGION["width"]
    for i, (r, g, b) in enumerate(pixels):
        if is_label_pixel(r, g, b):
            count += 1
            rows.add(i // w)
    return count, rows


def decide(pixels):
    count, rows = count_blue(pixels)
    # Metin ince ve yataydır: 4-24 satıra yayılmalı. Kocaman mavi blob
    # (skill efekti) tüm kutuyu kaplar, onu ele.
    row_span = (max(rows) - min(rows) + 1) if rows else 0
    is_open = count >= MIN_BLUE_PIXELS and 4 <= row_span <= 24
    return is_open, count


def grab_region_live(sct):
    img = sct.grab(REGION)
    # BGRA -> (r,g,b) listesi
    raw = img.raw
    return [(raw[i + 2], raw[i + 1], raw[i]) for i in range(0, len(raw), 4)]


def test_mode(path):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    box = (REGION["left"], REGION["top"],
           REGION["left"] + REGION["width"], REGION["top"] + REGION["height"])
    pixels = list(im.crop(box).getdata())
    is_open, count = decide(pixels)
    durum = "ACIK" if is_open else "KAPALI"
    print(f"{path}: chat {durum} (mavi piksel: {count})")
    return is_open


def live_mode():
    import mss
    print("LoL chat algilayici basladi (Ctrl+C ile cik)...")
    prev = None
    with mss.mss() as sct:
        while True:
            is_open, count = decide(grab_region_live(sct))
            if is_open != prev:
                ts = time.strftime("%H:%M:%S")
                durum = "ACIK  [yazma modu]" if is_open else "KAPALI"
                print(f"[{ts}] CHAT {durum} (mavi piksel: {count})")
                prev = is_open
            time.sleep(0.1)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_mode(sys.argv[2])
    else:
        live_mode()
