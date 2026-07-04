# -*- coding: utf-8 -*-
"""
LoL Chat Detox ayar yönetimi. Ayarlar exe/script'in yanındaki config.json
dosyasında durur; dosya yoksa varsayılanlar kullanılır.
"""
import os
import sys
import json

BASE_DIR = os.path.dirname(
    sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_PROMPT = (
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

DEFAULTS = {
    "prompt": DEFAULT_PROMPT,
    "model": "gemini-3.1-flash-lite",
    "exit_hotkey": "ctrl+alt+q",
    "toggle_hotkey": "ctrl+alt+d",
}


def load_config():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            data = json.load(f)
        for k in DEFAULTS:
            if isinstance(data.get(k), str) and data[k].strip():
                cfg[k] = data[k]
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump({k: cfg[k] for k in DEFAULTS}, f, ensure_ascii=False, indent=2)


def config_mtime():
    try:
        return os.path.getmtime(CONFIG_PATH)
    except OSError:
        return 0
