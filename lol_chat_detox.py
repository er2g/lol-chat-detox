# -*- coding: utf-8 -*-
"""
LoL chat detox: chat'e yazdığın mesajı Enter'a bastığın anda yakalar,
Gemini ile pozitif/küfürsüz hale çevirir ve onun yerine onu gönderir.

Kullanım:
    set GEMINI_API_KEY=...   (ya da ortam değişkeni olarak kalıcı ekle)
    python lol_chat_detox.py

Çıkış: Ctrl+Alt+Q
"""
import os
import sys
import json
import time
import ctypes
import threading
import urllib.request

ctypes.windll.user32.SetProcessDPIAware()

import mss
import keyboard
import lol_chat_detector as detector

MODEL = "gemini-3.1-flash-lite"  # gerekirse ListModels ile doğrula
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lol_detox.log")


def _get_api_key():
    k = os.environ.get("GEMINI_API_KEY", "")
    if k:
        return k
    # setx ile kaydedilmiş ama bu terminale henüz yansımamış olabilir
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as h:
            return winreg.QueryValueEx(h, "GEMINI_API_KEY")[0]
    except OSError:
        return ""


API_KEY = _get_api_key()

# True: pano + Ctrl+V ile anında yapıştır; False: harf harf yaz
# (LoL sentetik Ctrl+V'yi kabul etmiyor, canlı test edildi -> False)
PASTE_MODE = False

# Oyunun chat kutusu 128 UTF-8 byte alıyor (canlı ölçüldü); pay bırak
CHAT_BYTE_LIMIT = 120


def split_chunks(text, limit=CHAT_BYTE_LIMIT):
    """Metni kelime sınırlarından, her parça <= limit UTF-8 byte olacak
    şekilde böler."""
    chunks, cur = [], ""
    for w in text.split(" "):
        cand = (cur + " " + w).strip()
        if len(cand.encode("utf-8")) <= limit:
            cur = cand
            continue
        if cur:
            chunks.append(cur)
        # tek kelime bile limiti aşıyorsa byte-güvenli sert kes
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


HISTORY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "lol_mesaj_gecmisi.log")


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')} p{os.getpid()}] {msg}"
    if sys.stdout is not None:  # pythonw altında konsol yok
        print(line, flush=True)
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def log_history(original, detoxed):
    try:
        with open(HISTORY_PATH, "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"  ORJINAL: {original}\n"
                    f"  DETOX  : {detoxed}\n")
    except OSError:
        pass

PROMPT = (
    "Sen bir League of Legends oyuncusunun kufur tercumanisin. Oyuncunun "
    "toksik/kufurlu mesajindaki kufru ve ofkeyi, kufur icermeyen, resmi-edebi "
    "bir dille UZUN UZUN BETIMLEYEREK ayni dilde yeniden yaz. Yani kufru "
    "sansurlemek yerine, ne demek istedigini kibar ve detayli bir aciklamaya "
    "cevir; komiklik bu ciddi-betimleyici tondan gelsin. Kurallar:\n"
    "- Mesaj zaten toksik DEGILSE (kufur, hakaret, agresyon yoksa) HICBIR "
    "degisiklik yapma, mesaji oldugu gibi geri yaz\n"
    "- Kufur, hakaret, mustehcen kelime OLMAYACAK; ama ofkenin icerigi "
    "detayli sekilde tarif EDILECEK\n"
    "- Espriyi kendin ekleme, sirf betimlemenin ciddiyetinden gelsin; "
    "sevecenlik, tatlilik, opucuk falan YOK\n"
    "- Orijinal BUYUK HARFLE yazildiysa sen de BUYUK HARF kullan; kucuk "
    "harfle yazildiysa kucuk harf kullan\n"
    "- Tek satir, en fazla 180 karakter\n"
    "- SADECE yeni mesaji yaz, aciklama ekleme\n\n"
    "Ornek 1: 'YA MASTER YI SENIN BEN O ELLERINI SIKEYIM' -> "
    "'MASTER YI, SU AN ELLERINE FIZIKSEL MUDAHALEDE BULUNMA ARZUSU DUYUYORUM "
    "CUNKU ALDIGIN KARARLAR BENDE DERIN BIR HAYAL KIRIKLIGI YARATTI'\n"
    "Ornek 2: 'amk yasuosu bi engel olsana' -> 'sevgili yasuo, rakibi "
    "engelleme konusundaki kayitsizligin bende agza alinmayacak kelimelerle "
    "ifade edilebilecek duygular uyandiriyor'\n\n"
    "Mesaj: {msg}"
)

# --- durum ---
chat_open = False
buffer = []
injecting = False
enter_hotkey = None
lock = threading.Lock()

# event.name -> karakter olmayan tuşlar (yok sayılacaklar)
IGNORED = {
    "enter", "esc", "tab", "shift", "sag shift", "sol shift", "ctrl",
    "left ctrl", "right ctrl", "alt", "alt gr", "caps lock", "up", "down",
    "left", "right", "home", "end", "delete", "insert", "page up",
    "page down", "windows", "left windows", "right windows",
}


def rewrite_with_gemini(text):
    url = (f"https://generativelanguage.googleapis.com/v1beta/models/"
           f"{MODEL}:generateContent?key={API_KEY}")
    body = json.dumps({
        "contents": [{"parts": [{"text": PROMPT.format(msg=text)}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 200},
    }).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=6) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # tek satıra indir, tırnak temizle
    out = out.replace("\n", " ").strip().strip('"').strip()
    # büyük/küçük harf stilini orijinale göre zorla (model tutarsız kalıyor)
    letters = [c for c in text if c.isalpha()]
    if letters:
        upper_ratio = sum(c.isupper() for c in letters) / len(letters)
        # Türkçe i/İ ve ı/I dönüşümlerini önce elle yap: Python'un lower()'ı
        # 'İ' için "i + ayrık nokta" (U+0307) üretiyor, oyunda bozuk görünüyor
        if upper_ratio > 0.8:
            out = out.replace("i", "İ").replace("ı", "I").upper()
        elif upper_ratio < 0.2:
            out = out.replace("İ", "i").replace("I", "ı").lower()
    return out


def send_enter_raw():
    """Suppress hotkey'ini geçici kaldırıp gerçek Enter gönder."""
    global enter_hotkey
    keyboard.remove_hotkey(enter_hotkey)
    keyboard.send("enter")
    enter_hotkey = keyboard.add_hotkey("enter", on_enter, suppress=True)


def process_and_send(text):
    global injecting
    try:
        log(f"yakalanan: {text!r}")
        injecting = True
        # eski metni sil
        if PASTE_MODE:
            keyboard.send("ctrl+a")
            keyboard.send("backspace")
        # sigorta: ctrl+a işlemediyse kalan metni de temizle (boş kutuda zararsız)
        for _ in range(len(text) + 5):
            keyboard.send("backspace")
        injecting = False

        try:
            new_text = rewrite_with_gemini(text)
        except Exception as e:
            log(f"! Gemini hatasi ({e}), mesaj gonderilmiyor")
            return
        log(f"detox: {new_text!r}")
        log_history(text, new_text)

        injecting = True
        chunks = split_chunks(new_text)
        for i, chunk in enumerate(chunks):
            if i > 0:
                send_enter_raw()  # chat'i tekrar aç
                time.sleep(0.25)
            if PASTE_MODE:
                set_clipboard(chunk)
                keyboard.send("ctrl+v")
            else:
                keyboard.write(chunk, delay=0.005)  # delay=0'i LoL yutuyor
            # oyun karakterleri kendi karesinde işliyor; Enter'i erken
            # basarsak mesaj yarıda gider. Uzunlukla orantılı bekle.
            time.sleep(0.2 + len(chunk) * 0.004)
            send_enter_raw()  # gönder
            time.sleep(0.15)
        if len(chunks) > 1:
            log(f"{len(chunks)} parcada gonderildi")
    finally:
        injecting = False


def on_enter():
    global buffer
    if injecting:
        return
    if not chat_open:
        # chat kapalı: Enter chat'i açsın, aynen ilet
        send_enter_raw()
        return
    with lock:
        text = "".join(buffer).strip()
        buffer = []
    if not text:
        log("enter: chat acik ama buffer BOS (tus kaydi calismiyor olabilir!)")
        send_enter_raw()  # boş mesaj: chat'i kapatır, karışmayalım
        return
    threading.Thread(target=process_and_send, args=(text,), daemon=True).start()


def on_key(event):
    global buffer
    if injecting or not chat_open:
        return
    name = event.name
    if name is None or name in IGNORED:
        return
    with lock:
        if name == "backspace":
            if buffer:
                buffer.pop()
        elif name == "space":
            buffer.append(" ")
        elif len(name) == 1:
            if keyboard.is_pressed("shift"):
                buffer.append(name.upper())
            else:
                buffer.append(name)
            if len(buffer) == 1:
                log("tus kaydi basladi")


def detector_loop():
    global chat_open, buffer
    sct = mss.mss()
    stable = detector.StableState(open_frames=3, close_frames=2)
    while True:
        if detector.is_lol_foreground():
            raw_open, _ = detector.decide(detector.grab_region_live(sct))
        else:
            raw_open = False  # LoL ön planda değilse hiç karışma
        is_open = stable.update(raw_open)
        if is_open != chat_open:
            log(f"chat {'ACIK' if is_open else 'KAPALI'}")
        if not is_open and chat_open:
            with lock:
                buffer = []  # chat Esc/tıklama ile kapandı, taslağı unut
        chat_open = is_open
        time.sleep(0.05)


def main():
    global enter_hotkey
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    k32.CreateMutexW(None, False, "lol_chat_detox_tek")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        log("zaten calisan bir kopya var, cikiliyor")
        sys.exit(0)
    if not API_KEY:
        log("HATA: GEMINI_API_KEY bulunamadi (env + registry bakildi)!")
        sys.exit(1)
    threading.Thread(target=detector_loop, daemon=True).start()
    keyboard.on_press(on_key)
    enter_hotkey = keyboard.add_hotkey("enter", on_enter, suppress=True)
    log(f"detox aktif (model: {MODEL}). Cikis: Ctrl+Alt+Q")
    keyboard.wait("ctrl+alt+q")
    log("kapatildi")


if __name__ == "__main__":
    main()
