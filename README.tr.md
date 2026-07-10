# LoL Chat Detox 🧼

[English](README.md) · **Türkçe**

League of Legends chat’indeki toksik mesajları ya **Gemini ile resmi-edebi tebliğe** çevirir (AI), ya da **tüm harfleri lookalike** Unicode karakterlere spoof’lar (Non-AI).

> **Siz:** `YA MASTER YI SENIN BEN O ELLERINI SIKEYIM`  
> **Takım:** `MASTER YI, SU AN ELLERINE FIZIKSEL MUDAHALEDE BULUNMA ARZUSU DUYUYORUM...`

Toksik olmayan satırlar (`gg wp`) AI modunda olduğu gibi gider.

---

## Özellikler

- **AI / Non-AI** modlar, anında geçiş  
- Tek premium uygulama (motor + overlay + ayarlar + başlangıç)  
- **EN / TR** arayüz (Sistem → Dil)  
- Ayarlanabilir kısayollar (çıkış, aç/kapa, Non-AI tetik, AI tetik)  
- Harf map JSON editörü  
- Veri: `%APPDATA%\LoLChatDetox\`  
- Kalıcı LL Enter kancası (AI modunda sızıntı yok)

---

## İndirme

1. **[Releases](https://github.com/er2g/lol-chat-detox/releases)**  
2. `LoLDetox.exe` indir  
3. Çalıştır; dil için **Sistem → Language / Dil**

Kaynak:

```bash
pip install -r requirements.txt
python lol_app.py
```

API: https://aistudio.google.com/apikey  

---

## Modlar

| Mod | Enter | Tetikleyici |
|-----|--------|-------------|
| **Non-AI** | Olduğu gibi gönder | Varsayılan `Shift+Enter` → lookalike |
| **AI** | (varsayılan) Gemini detox | Orijinal yutulur, çeviri gider |

---

## Uyarı

Klavye kancası + sentetik girdi kullanır. Vanguard ortamında **kendi sorumluluğunuzda**. Rekabet avantajı vermez.

---

`/mute all` çözüm değil, kişisel gelişimdir bu.
