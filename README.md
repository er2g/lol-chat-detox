# LoL Chat Detox 🧼

**English** · [Türkçe](README.tr.md)

Turn toxic League of Legends chat into comedy — either with **Gemini AI** (formal long-winded rewrites) or **Non-AI lookalike glyphs** (every letter spoofed with Cyrillic/Greek lookalikes).

> **You type:** `YA MASTER YI IM GONNA BREAK YOUR HANDS`  
> **Team sees:** `MASTER YI, I PRESENTLY FEEL A STRONG URGE TO PHYSICALLY INTERVENE WITH YOUR HANDS BECAUSE YOUR DECISIONS HAVE CAUSED ME PROFOUND DISAPPOINTMENT`

Non-toxic lines (`gg wp`) pass through unchanged in AI mode.

---

## Features

| Feature | Description |
|--------|-------------|
| **AI mode** | Intercepts Enter, rewrites via Gemini, never lets the original flame through if the API fails |
| **Non-AI mode** | Enter sends raw; configurable trigger (default `Shift+Enter`) spoofs all letters |
| **Single premium app** | Detox engine + overlay + settings + startup in one process / one EXE |
| **EN / TR UI** | Full English + Turkish interface (System → Language) |
| **Configurable hotkeys** | Quit, toggle, Non-AI trigger, AI trigger |
| **Glyph JSON map** | Edit the lookalike alphabet live |
| **Safe data dir** | Config/logs in `%APPDATA%\LoLChatDetox\` (not next to the EXE) |
| **Hard Enter hook** | Permanent low-level Enter capture in AI mode (no suppress race) |

---

## Download (Windows)

1. Open **[Releases](https://github.com/er2g/lol-chat-detox/releases)**
2. Download the latest `LoLDetox.exe` (or zip)
3. Run it (optionally `install.bat` as admin for start-with-Windows)
4. Pick **English** or **Türkçe** under **System → Language**

Or from source:

```bash
git clone https://github.com/er2g/lol-chat-detox.git
cd lol-chat-detox
pip install -r requirements.txt
python lol_app.py
```

Gemini key (AI mode only): https://aistudio.google.com/apikey  
Paste it in **AI / Gemini** in the app (stored locally in config).

---

## Modes

| Mode | Default send | Spoof / detox |
|------|----------------|---------------|
| **Non-AI** | `Enter` → send as typed | Trigger (default `Shift+Enter`) → lookalike rewrite |
| **AI** | Trigger (default `Enter`) → Gemini rewrite | Original is blocked until rewritten |

Toggle detox: `Ctrl+Alt+D` (default)  
Quit: `Ctrl+Alt+Q` (default)  
Hotkeys are editable in the app.

---

## How it works

1. Pixel-scans the blue chat channel tag when LoL is foreground  
2. Records keys while chat is open  
3. On trigger: rewrites (AI or glyphs), clears the box, types the result, sends  
4. Optional overlay shows chat open/closed  

---

## Requirements

- **Windows 10/11**
- League in **borderless / windowed** (not exclusive fullscreen)
- Chat detector calibrated for **2560×1600** default HUD (other resolutions need region tweak in `lol_chat_detector.py`)
- AI mode: Gemini API key  

```
pip install -r requirements.txt
```

Build single EXE:

```bash
python -m PyInstaller LoLDetox.spec --noconfirm
```

Output: `dist/LoLDetox.exe`

---

## Config location

```
%APPDATA%\LoLChatDetox\
  config.json
  lol_detox.log
  lol_mesaj_gecmisi.log   (message history)
```

---

## Disclaimer

Uses a keyboard hook and synthetic input. On a Vanguard-protected client, **any automation is at your own risk**. This does not provide a competitive advantage — it only makes you look more polite (or more cursed).

---

## Project layout

```
lol_app.py           # Premium UI + tray lifecycle
lol_engine.py        # Detox engine
lol_enter_hook.py    # Permanent WH_KEYBOARD_LL Enter capture
lol_homoglyph.py     # Non-AI lookalike rewrite
lol_config.py        # Settings + AppData paths
lol_i18n.py          # English / Turkish strings
lol_chat_detector.py # Chat open/closed pixel detector
```

---

## License

Use at your own risk. Not affiliated with Riot Games.

---

Because `/mute all` is not personal growth.
