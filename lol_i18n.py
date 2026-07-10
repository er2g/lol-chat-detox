# -*- coding: utf-8 -*-
"""UI strings: English + Turkish."""
import locale

LANGS = ("en", "tr")

# Gemini system prompts (language of *rewritten chat*, not UI)
PROMPT_EN = (
    "You are a League of Legends toxicity translator. Rewrite the player's "
    "toxic/flaming chat message into a long, formal, overly polite description "
    "of the same anger — NO swear words. Keep the same language as the original. "
    "Comedy should come from the serious bureaucratic tone.\n"
    "Rules:\n"
    "- If the message is NOT toxic (no insults/aggression), return it UNCHANGED\n"
    "- No profanity, insults, or obscenity; describe the anger in detail instead\n"
    "- Do not add jokes, cuteness, or emojis\n"
    "- Match casing: ALL CAPS stays ALL CAPS; lowercase stays lowercase\n"
    "- Single line, max 180 characters\n"
    "- Output ONLY the new message, no explanation\n\n"
    "Example 1: 'YA MASTER YI IM GONNA BREAK YOUR HANDS' -> "
    "'MASTER YI, I PRESENTLY FEEL A STRONG URGE TO PHYSICALLY INTERVENE WITH "
    "YOUR HANDS BECAUSE YOUR DECISIONS HAVE CAUSED ME PROFOUND DISAPPOINTMENT'\n"
    "Example 2: 'yasuo stop inting you dog' -> "
    "'esteemed yasuo, your continuous voluntary transfers of gold to the enemy "
    "inspire feelings that cannot be restated in polite company; please cease'\n\n"
    "Message: {msg}"
)

PROMPT_TR = (
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

_STRINGS = {
    "en": {
        "app_title": "LoL Chat Detox",
        "brand_sub": "Premium Control",
        "nav_dashboard": "Dashboard",
        "nav_mode": "Mode",
        "nav_ai": "AI / Gemini",
        "nav_homoglyph": "Glyph Map (JSON)",
        "nav_hotkeys": "Hotkeys",
        "nav_system": "System",
        "nav_logs": "Logs",
        "hdr_dashboard": "Dashboard",
        "hdr_dashboard_sub": "Live status and quick controls",
        "hdr_mode": "Mode",
        "hdr_mode_sub": "AI or Non-AI",
        "hdr_ai": "AI / Gemini",
        "hdr_ai_sub": "API key, model, prompt",
        "hdr_homoglyph": "Glyph Map",
        "hdr_homoglyph_sub": "Lookalike JSON editor",
        "hdr_hotkeys": "Hotkeys",
        "hdr_hotkeys_sub": "Global shortcuts",
        "hdr_system": "System",
        "hdr_system_sub": "Startup, overlay, language, files",
        "hdr_logs": "Logs",
        "hdr_logs_sub": "Engine output",
        "stat_detox": "Detox",
        "stat_mode": "Mode",
        "stat_game": "Game",
        "stat_chat": "Chat",
        "stat_hooks": "Hooks",
        "on": "ON",
        "off": "OFF",
        "open": "OPEN",
        "closed": "closed",
        "none": "none",
        "active": "active",
        "passive": "idle",
        "quick_controls": "Quick controls",
        "quick_hint": "Mode switches apply instantly — no restart needed.",
        "btn_toggle": "Toggle Detox",
        "btn_ai_mode": "Switch to AI",
        "btn_non_ai_mode": "Switch to Non-AI",
        "btn_save_all": "Save all settings",
        "live_log": "Live log",
        "mode_title": "Active mode",
        "mode_hint": "AI: Enter → Gemini rewrite.  Non-AI: Enter sends as-is, "
                     "trigger hotkey spoofs every letter.",
        "mode_non_ai": "Non-AI — Lookalike spoof",
        "mode_non_ai_desc": "No API required. Trigger hotkey rewrites all letters "
                            "to lookalike Unicode (Cyrillic/Greek/etc.).",
        "mode_ai": "AI — Gemini detox",
        "mode_ai_desc": "Trigger (default Enter) sends the message to Gemini and "
                        "replaces toxicity with formal long-winded phrasing.",
        "btn_save_mode": "Save & apply mode",
        "ai_title": "Gemini settings",
        "ai_hint": "Key is stored only on this PC in config.json. "
                   "https://aistudio.google.com/apikey",
        "api_key": "API Key",
        "model": "Model",
        "prompt_label": "Prompt  ({msg} = player message)",
        "btn_save_ai": "Save AI settings",
        "btn_default_prompt": "Default prompt",
        "homo_title": "Lookalike glyph map (JSON)",
        "homo_hint": 'Example: {"s":"ѕ","i":"і","a":"а"} — single-char keys, '
                     "non-empty values. Applied to the whole message in Non-AI mode.",
        "preview_label": "Preview text",
        "btn_save_homo": "Save JSON & apply",
        "btn_preview": "Preview",
        "btn_default_homo": "Reset to defaults",
        "hotkeys_title": "Hotkeys",
        "hotkeys_hint": "Format: ctrl+alt+q  ·  shift+enter  ·  enter\n"
                        "Non-AI trigger: spoof & send.  "
                        "AI trigger: Gemini detox (default enter).",
        "hk_exit": "Quit / close app",
        "hk_toggle": "Toggle detox on/off",
        "hk_trigger": "Non-AI spoof trigger",
        "hk_ai_trigger": "AI detox trigger",
        "btn_save_hotkeys": "Save hotkeys",
        "sys_title": "System",
        "chk_enabled": "Detox enabled by default",
        "chk_overlay": "In-game status overlay",
        "chk_game_only": "Keyboard hooks only while LoL is running",
        "chk_startup": "Start in background with Windows",
        "chk_minimized": "Start with window hidden",
        "sys_hint": "Startup uses Windows Task Scheduler (may need admin).",
        "btn_save_system": "Save system settings",
        "btn_minimize": "Minimize to taskbar",
        "btn_tray": "Send to background",
        "btn_quit": "Quit application",
        "files_title": "Files",
        "lang_title": "Language / Dil",
        "lang_hint": "UI language. Changing language can also load the matching "
                     "default AI prompt.",
        "btn_save_lang": "Apply language",
        "logs_title": "Engine logs",
        "titlebar_hint": "",
        "err_prompt_msg": "Prompt must contain {msg}.",
        "err_model": "Model name cannot be empty.",
        "err_json": "JSON error",
        "err_hotkey": "Invalid hotkey",
        "err_hotkey_empty": "cannot be empty.",
        "err_hotkeys_unique": "All hotkeys must be different.",
        "err_homo_obj": "JSON must be an object ({ })",
        "err_homo_key": "Keys must be a single character",
        "err_homo_val": "Values cannot be empty",
        "err_homo_empty": "Map cannot be empty",
        "saved": "Saved",
        "saved_ai": "AI settings saved",
        "saved_homo": "Glyph map saved",
        "saved_hotkeys": "Hotkeys applied",
        "saved_all": "All settings saved",
        "mode_set": "Mode",
        "detox_on": "Detox ON",
        "detox_off": "Detox OFF",
        "default_prompt_loaded": "Default prompt loaded",
        "default_homo_loaded": "Default map loaded (not saved yet)",
        "startup_ok": "Start with Windows enabled",
        "startup_off": "Startup task removed",
        "quit_confirm": "Quit LoL Chat Detox completely?",
        "quit_title": "Quit",
        "already_running": "LoL Chat Detox is already running.",
        "side_starting": "● starting…",
        "overlay_chat_open": "CHAT OPEN",
        "overlay_chat_closed": "CHAT CLOSED",
        "preview_default": "i will destroy your nexus idiot",
        "lang_applied": "Language applied — restart UI pages if needed",
        "warn_startup": "Startup",
    },
    "tr": {
        "app_title": "LoL Chat Detox",
        "brand_sub": "Premium Kontrol",
        "nav_dashboard": "Dashboard",
        "nav_mode": "Mod",
        "nav_ai": "AI / Gemini",
        "nav_homoglyph": "Harf Map (JSON)",
        "nav_hotkeys": "Kısayollar",
        "nav_system": "Sistem",
        "nav_logs": "Loglar",
        "hdr_dashboard": "Dashboard",
        "hdr_dashboard_sub": "Canlı durum ve hızlı kontroller",
        "hdr_mode": "Mod",
        "hdr_mode_sub": "AI veya Non-AI",
        "hdr_ai": "AI / Gemini",
        "hdr_ai_sub": "Anahtar, model, prompt",
        "hdr_homoglyph": "Harf Map",
        "hdr_homoglyph_sub": "Lookalike JSON editörü",
        "hdr_hotkeys": "Kısayollar",
        "hdr_hotkeys_sub": "Global kısayollar",
        "hdr_system": "Sistem",
        "hdr_system_sub": "Başlangıç, overlay, dil, dosyalar",
        "hdr_logs": "Loglar",
        "hdr_logs_sub": "Motor çıktısı",
        "stat_detox": "Detox",
        "stat_mode": "Mod",
        "stat_game": "Oyun",
        "stat_chat": "Chat",
        "stat_hooks": "Kancalar",
        "on": "AÇIK",
        "off": "KAPALI",
        "open": "AÇIK",
        "closed": "kapalı",
        "none": "yok",
        "active": "aktif",
        "passive": "pasif",
        "quick_controls": "Hızlı kontroller",
        "quick_hint": "Mod değişimi anında uygulanır — yeniden başlatma yok.",
        "btn_toggle": "Detox Aç/Kapa",
        "btn_ai_mode": "AI moda geç",
        "btn_non_ai_mode": "Non-AI moda geç",
        "btn_save_all": "Tümünü kaydet",
        "live_log": "Canlı log",
        "mode_title": "Aktif mod",
        "mode_hint": "AI: Enter → Gemini.  Non-AI: Enter düz gider, "
                     "tetikleyici tüm harfleri spoof'lar.",
        "mode_non_ai": "Non-AI — Lookalike sansür",
        "mode_non_ai_desc": "API gerekmez. Tetikleyici mesajın tüm harflerini "
                            "Kiril/Yunanca lookalike yapar.",
        "mode_ai": "AI — Gemini detox",
        "mode_ai_desc": "Tetikleyici (varsayılan Enter) mesajı Gemini'ye yollar; "
                        "küfür resmi-edebi tebliğe çevrilir.",
        "btn_save_mode": "Modu kaydet & uygula",
        "ai_title": "Gemini ayarları",
        "ai_hint": "Anahtar yalnızca bu PC'de config.json içinde saklanır. "
                   "https://aistudio.google.com/apikey",
        "api_key": "API Key",
        "model": "Model",
        "prompt_label": "Prompt  ({msg} = oyuncu mesajı)",
        "btn_save_ai": "AI ayarlarını kaydet",
        "btn_default_prompt": "Varsayılan prompt",
        "homo_title": "Lookalike harf haritası (JSON)",
        "homo_hint": 'Örnek: {"s":"ѕ","i":"і"} — tek karakter anahtar. '
                     "Non-AI modda tüm mesaja uygulanır.",
        "preview_label": "Önizleme metni",
        "btn_save_homo": "JSON kaydet & uygula",
        "btn_preview": "Önizle",
        "btn_default_homo": "Varsayılana dön",
        "hotkeys_title": "Kısayollar",
        "hotkeys_hint": "Biçim: ctrl+alt+q  ·  shift+enter  ·  enter\n"
                        "Non-AI tetik: sansürle gönder.  "
                        "AI tetik: Gemini detox.",
        "hk_exit": "Çıkış / uygulamayı kapat",
        "hk_toggle": "Detox aç/kapa",
        "hk_trigger": "Non-AI sansür tetikleyici",
        "hk_ai_trigger": "AI detox tetikleyici",
        "btn_save_hotkeys": "Kısayolları kaydet",
        "sys_title": "Sistem",
        "chk_enabled": "Detox varsayılan olarak açık",
        "chk_overlay": "Oyun içi durum overlay'i",
        "chk_game_only": "Klavye kancaları yalnızca LoL açıkken",
        "chk_startup": "PC açılınca arka planda başlat",
        "chk_minimized": "Başlangıçta pencereyi gizli aç",
        "sys_hint": "PC açılışı için Görev Zamanlayıcı kullanılır (yönetici gerekebilir).",
        "btn_save_system": "Sistem ayarlarını kaydet",
        "btn_minimize": "Görev çubuğuna küçült",
        "btn_tray": "Arka plana al",
        "btn_quit": "Uygulamadan çık",
        "files_title": "Dosyalar",
        "lang_title": "Dil / Language",
        "lang_hint": "Arayüz dili. Dil değişince eşleşen varsayılan AI prompt yüklenebilir.",
        "btn_save_lang": "Dili uygula",
        "logs_title": "Motor logları",
        "titlebar_hint": "",
        "err_prompt_msg": "Prompt içinde {msg} olmalı.",
        "err_model": "Model adı boş olamaz.",
        "err_json": "JSON hatası",
        "err_hotkey": "Geçersiz kısayol",
        "err_hotkey_empty": "boş olamaz.",
        "err_hotkeys_unique": "Kısayollar birbirinden farklı olmalı.",
        "err_homo_obj": "JSON bir nesne ({ }) olmalı",
        "err_homo_key": "Anahtar tek karakter olmalı",
        "err_homo_val": "Değer boş olamaz",
        "err_homo_empty": "Harita boş olamaz",
        "saved": "Kaydedildi",
        "saved_ai": "AI ayarları kaydedildi",
        "saved_homo": "Harf haritası kaydedildi",
        "saved_hotkeys": "Kısayollar uygulandı",
        "saved_all": "Tüm ayarlar kaydedildi",
        "mode_set": "Mod",
        "detox_on": "Detox AÇIK",
        "detox_off": "Detox KAPALI",
        "default_prompt_loaded": "Varsayılan prompt yüklendi",
        "default_homo_loaded": "Varsayılan harita yüklendi (henüz kaydetmedin)",
        "startup_ok": "PC açılışında başlatma açıldı",
        "startup_off": "Başlangıç görevi kaldırıldı",
        "quit_confirm": "LoL Chat Detox tamamen kapansın mı?",
        "quit_title": "Çıkış",
        "already_running": "LoL Chat Detox zaten çalışıyor.",
        "side_starting": "● başlatılıyor…",
        "overlay_chat_open": "CHAT AÇIK",
        "overlay_chat_closed": "CHAT KAPALI",
        "preview_default": "sikeyim orospu cocugu amk",
        "lang_applied": "Dil uygulandı",
        "warn_startup": "Başlangıç",
    },
}

_current = "en"


def detect_system_lang():
    try:
        loc = locale.getdefaultlocale()[0] or ""
    except Exception:
        loc = ""
    if loc.lower().startswith("tr"):
        return "tr"
    return "en"


def set_lang(lang: str):
    global _current
    _current = lang if lang in LANGS else "en"


def get_lang():
    return _current


def t(key: str, **kwargs) -> str:
    table = _STRINGS.get(_current) or _STRINGS["en"]
    s = table.get(key) or _STRINGS["en"].get(key) or key
    if kwargs:
        try:
            return s.format(**kwargs)
        except Exception:
            return s
    return s


def default_prompt(lang=None):
    lang = lang or _current
    return PROMPT_TR if lang == "tr" else PROMPT_EN
