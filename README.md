# LoL Chat Detox 🧼

League of Legends'ta sinirlenip chat'e küfür yazdığınız anda mesajınızı yakalar,
Gemini'ye gönderir ve küfrünüzü **resmi-edebi bir dille uzun uzun betimleyen**
nazik bir tebliğe çevirip onun yerine gönderir. Toksiklik azalır, komedi artar.

## Örnek

> **Siz:** `YA MASTER YI SENIN BEN O ELLERINI SIKEYIM`
>
> **Takımın gördüğü:** `MASTER YI, SU AN ELLERINE FIZIKSEL MUDAHALEDE BULUNMA
> ARZUSU DUYUYORUM CUNKU ALDIGIN KARARLAR BENDE DERIN BIR HAYAL KIRIKLIGI YARATTI`

> **Siz:** `top laneci arkadasim feedlemeyi birakir misin lutfen orospu cocugu`
>
> **Takımın gördüğü:** `ust koridordaki sayin mesai arkadasim, rakibe surekli
> teslim olarak oyunu zora sokmaniz bende derin bir husumet ve soy agaciniza
> dair agir sorgulamalar yaratiyor, lutfen durun.`

Toksik olmayan mesajlar (`gg wp` vb.) hiç değiştirilmeden gönderilir.

## Nasıl çalışıyor?

1. **Chat algılama** (`lol_chat_detector.py`): Ekranın sol altındaki chat giriş
   kutusunun mavi `[Takım]`/`[Genel]` etiketini piksel bazlı tarar. Milisaniyelik
   yanlış pozitifleri debounce (`StableState`) ile eler. Sadece LoL ön
   plandayken çalışır.
2. **Yakalama ve değiştirme** (`lol_chat_detox.py`): Global klavye kancasıyla
   chat açıkken yazdıklarınızı kaydeder. Enter'a bastığınızda tuşu yutar,
   metni Gemini'ye (`gemini-3.1-flash-lite`) gönderir, chat kutusunu temizler,
   çeviriyi yazar ve kendisi gönderir. Gemini'ye ulaşılamazsa mesaj **hiç
   gönderilmez** — öfkeli orijinal asla kaçmaz.
3. **Overlay** (`lol_chat_overlay.py`): Chat'in altında tıklama-geçirgen minik
   bir durum kutusu (yeşil = açık algılandı). Sistemin çalıştığını görmek için.
4. **Watcher** (`lol_watcher.pyw`): Windows başlangıcında sessizce çalışır;
   oyun süreci açılınca detox + overlay'i başlatır, kapanınca durdurur.

## Kurulum

```
pip install -r requirements.txt
setx GEMINI_API_KEY "ANAHTARINIZ"
```

Anahtar: https://aistudio.google.com/apikey

Otomatik başlatma için `lol_watcher.pyw`'ye işaret eden bir kısayolu
`shell:startup` klasörüne koyun (hedef: `pythonw.exe "...\lol_watcher.pyw"`).

Elle çalıştırma: `python lol_chat_detox.py` (çıkış: `Ctrl+Alt+Q`).

## Bilinen kısıtlar / notlar

- Piksel koordinatları **2560x1600** çözünürlüğe ve varsayılan HUD ölçeğine
  kalibredir. Farklı çözünürlükte `REGION` ve renk eşiği yeniden ölçülmeli.
- Oyun **borderless/windowed** modda olmalı (exclusive fullscreen'de ekran
  yakalama çalışmaz).
- Oyun içi chat kutusu **128 UTF-8 byte** kabul ediyor; uzun çeviriler
  ≤120 byte'lık parçalara bölünüp peş peşe gönderilir.
- LoL sentetik `Ctrl+V`'yi kabul etmiyor; metin karakter karakter yazılır
  (karakter başına 5 ms — daha hızlısını oyun yutuyor).
- Mesaj geçmişi `lol_mesaj_gecmisi.log`'a yazılır (orijinal + çeviri).
- ⚠️ Klavye kancası ve sentetik girdi kullanır; Vanguard'lı bir oyunda her
  otomasyonun teorik risk taşıdığını bilerek kendi sorumluluğunuzda kullanın.
  Rekabet avantajı sağlamaz, sadece sizi daha kibar gösterir.

## Neden?

Çünkü `/mute all` çözüm değil, kişisel gelişimdir bu.
