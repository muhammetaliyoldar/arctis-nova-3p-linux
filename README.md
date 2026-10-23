# Arctis Nova 3P Wireless: Ubuntu Bluetooth Düzeltmeleri

SteelSeries Arctis Nova 3P Wireless kulaklığı Ubuntu'da (PipeWire + WirePlumber) Bluetooth ile sorunsuz kullanmak için gereken ayarlar. Yanında Rap, Tekno/Rave, Deep House ve Genel için EasyEffects presetleri ve bunlar arasında tek tuşla geçiş var.

## Kurulum

```bash
sudo apt install -y git
git clone https://github.com/muhammetaliyoldar/arctis-nova-3p-linux.git
cd arctis-nova-3p-linux
./install.sh
```

Script sırasıyla şunları yapıyor:

1. **Kulaklığın bağlanır bağlanmaz kapanması:** Bluetooth codec listesini 19'dan sadece SBC'ye indiriyor ve HFP'yi kapatıyor.
2. **Güç tasarrufu (cızırtı ve kopma):** Bluetooth USB adaptörünün uykuya geçmesini her bilgisayarda kapatıyor. Bilgisayarda Realtek `rtw88` WiFi kartı varsa WiFi sürücüsünün ve NetworkManager'ın güç tasarrufunu da kapatıyor.
3. **Otomatik bağlanma:** Oturum açıldıktan sonra kulaklığa kendisi bağlanmayı deneyen servisi kuruyor.
4. **EasyEffects:** Kurulu değilse EasyEffects'i ve LSP eklentilerini kuruyor. 4 preseti ekliyor, kulaklık bağlanınca **Rap**'in otomatik yüklenmesini ve EasyEffects'in her açılışta arka planda başlamasını ayarlıyor.
5. **Hızlı preset geçişi:** Klavye kısayollarını ve üst bara preset menüsünü (EasyEffects Preset Selector uzantısı) kuruyor.
6. **Dynamic Music Pill:** Üst barda şarkıyı yönetmeye yarayan GNOME uzantısını indirip kuruyor ve ayarlarını (görünüm, görselleştirici, şeffaflık) yüklüyor.

Notlar:
- Scripti `sudo` ile **değil**, normal kullanıcı olarak çalıştır. Gerekirse sudo şifresini kendisi sorar.
- Tekrar çalıştırmak güvenli; zaten kurulu olanları baştan yazıyor.
- Music pill kurulduktan sonra üst barda görünmezse oturumu kapatıp aç. Wayland'de yeni kurulan uzantılar ancak bir sonraki oturumda yükleniyor.
- Kulaklığı önce Bluetooth'tan eşleştirmen iyi olur. Eşleştirmeden kurarsan, eşleştirdikten sonra scripti bir kez daha çalıştır; böylece otomatik preset yüklemesi de ayarlanır.
- Kaldırmak için: `./uninstall.sh`

## Belirtiler ve sebepleri

### 1. Kulaklık bağlanır bağlanmaz kapanıyor, ancak 3-4. denemede bağlanıyor

**Sebep:** Kulaklığın yazılımı (firmware). Bilgisayara bağlanınca hangi codec'leri desteklediğini soruyor. Ubuntu'daki PipeWire 19 farklı ses kanalıyla cevap veriyor: LDAC, aptX HD, aptX, aptX LL, FastStream, Opus, SBC. Kulaklık bunları tek tek incelerken LDAC/aptX'te donup kendini kapatıyor. `btmon` kaydında kapanma sebebi açıkça görünüyor:

```
AVDTP: Get All Capabilities -> LDAC, aptX HD, aptX ... (cevap gelmiyor)
Reason: Remote Device Terminated due to Power Off (0x15)
```

Telefonlar ve Windows sadece SBC/AAC sunduğu için orada bu sorun olmuyor.

**Çözüm:** WirePlumber'ın kulaklığa sadece **SBC** sunması. Arctis zaten SBC kullanıyor, yani ses kalitesinden bir şey kaybedilmiyor. Ek olarak, bağlantı kurulurken müzik ve mikrofon profillerinin çakışmasını önlemek için HFP/HSP (Bluetooth mikrofon) profili de kapatılıyor.

> ⚠️ Bu ayarı kurduğun bilgisayarda Bluetooth kulaklıkların **mikrofonu çalışmaz**, müzik ve ses normal çalışır. Kulaklığın kendisine dokunulmuyor; telefonda ve başka cihazlarda mikrofon eskisi gibi çalışır.

Dosyalar:
- WirePlumber 0.4 (Ubuntu 24.04): `~/.config/wireplumber/bluetooth.lua.d/51-arctis-a2dp-only.lua`
- WirePlumber 0.5+: `~/.config/wireplumber/wireplumber.conf.d/51-arctis-a2dp-only.conf`

Hangisinin kurulacağına `install.sh` kendisi karar veriyor. WirePlumber 0.4, `.conf` dosyalarını **okumaz**; internetteki çoğu rehber 0.5 formatını anlattığı için bu önemli.

### 2. Ses cızırtılı ya da kesik geliyor (güç tasarrufu)

Güç tasarrufu üç yerde kapatılıyor:

| Ayar | Dosya | Hangi bilgisayarda |
|---|---|---|
| Bluetooth USB adaptörü uykuya geçmesin | `/etc/modprobe.d/btusb.conf` | Hepsinde |
| Realtek WiFi firmware'i derin uykuya girmesin | `/etc/modprobe.d/rtw88.conf` | Sadece `rtw88` kartlarda |
| NetworkManager WiFi güç tasarrufu kapalı | `/etc/NetworkManager/conf.d/wifi-powersave-off.conf` | Sadece `rtw88` kartlarda |

Asıl sorun Realtek kartlarda:

**Sebep:** Bilgisayarın donanımı. Örneğin Realtek RTL8821CE gibi kartlarda WiFi ve Bluetooth tek çipte ve aynı anteni paylaşıyor. `rtw88` sürücüsü kartı derin güç tasarrufu moduna sokuyor, firmware de bu moddan çıkamıyor. Sonuç olarak WiFi ile Bluetooth anteni düzgün paylaşamıyor. Kernel logunda binlerce kez şu hata görünüyor:

```
rtw88_8821ce: firmware failed to leave lps state
rtw88_8821ce: failed to send h2c command
```

**Çözüm:** `/etc/modprobe.d/rtw88.conf` dosyası:
```
options rtw88_core disable_lps_deep=y
options rtw88_pci disable_aspm=y
```
`install.sh` bu ayarı ve NetworkManager ayarını sadece bilgisayarda `rtw88` sürücüsü varsa kuruyor. Kurduktan sonra bilgisayarı yeniden başlatman gerekiyor.

Bilgisayarında bu kart var mı diye bakmak için:
```bash
journalctl -k -b | grep -c 'failed to leave lps'   # 0'dan büyükse bu sorun var
```

### 3. Bilgisayar açılırken kulaklık açıksa otomatik bağlanmıyor

Kulaklık açılınca bilgisayara bağlanmayı deniyor. Bilgisayar o sırada henüz açılmamışsa kulaklık vazgeçiyor, bilgisayar da kendisi tekrar denemiyor. `arctis-autoconnect.service` oturum açıldıktan sonra 2 dakika boyunca 10 saniyede bir kulaklığa bağlanmayı deniyor, bağlanınca da duruyor.

## EasyEffects presetleri

| Kısayol | Preset | Karakter |
|---|---|---|
| `Ctrl+Alt+1` | **Rap** | Varsayılan, kulaklık bağlanınca otomatik yükleniyor. 808 sub'ı (50 Hz) göğüste hissediliyor, vokal en önde. Geniş bir bas yükseltmesi yerine dar bir 50 Hz yükseltmesi kullanıldığı için bas şişmiyor, sıkı vuruyor. |
| `Ctrl+Alt+2` | **Tekno - Rave** | Sürükleyen kick ve rumble, parlak synth ve hi-hat'ler. Orta frekanslar hafifçe oyuk, ses geniş ve enerjik. |
| `Ctrl+Alt+3` | **Deep House** | Derin ve sıcak sub (40 Hz), yumuşak tizler. Uzun setlerde kulağı yormuyor. |
| `Ctrl+Alt+4` | **Genel** | Her türe uyan hafif bir V eğrisi. |
| `Ctrl+Alt+0` | *sıradaki* | Presetler arasında sırayla geçiyor. |

Preset değişince ekranda bildirim çıkıyor. Ayrıca üst bardaki **EasyEffects Preset Selector** menüsünden fareyle de seçebilirsin. Terminalden geçmek için: `ee-preset Rap`, `ee-preset next`.

**Zincir:** Presetlerin hepsinde **Equalizer → Compressor → Limiter** var. Sadece LSP eklentileri kullanılıyor.
- **Equalizer:** Girişte, en yüksek yükseltme kadar ses kısılıyor. Böylece equalizer'ın kendisi clipping yapmıyor (`python3 files/easyeffects/make_presets.py --check` ile eğriler kontrol edilebilir).
- **Compressor:** Attack süresi en az 25 ms. Kick'in ve 808'in ilk vuruşu ezilmeden geçiyor.
- **Limiter:** -1 dB'de tavan yapıyor, ama sadece güvenlik ağı. EasyEffects 7.x'te limiter'ın release süresi en fazla 20 ms olabiliyor. 50 Hz'lik bir bas dalgası da 20 ms sürdüğü için limiter her devreye girdiğinde sesi bas dalgasının *içinde* açıp kısıyor ve basta bozulma yapıyor. Bu yüzden compressor'ün çıkış artırması (makeup) düşük tutuldu, sinyal limiter'a nadiren ulaşıyor. Ses biraz kısık gelirse kulaklığın tekerinden aç.
- `make_presets.py` değerleri EasyEffects şemasındaki aralıklara göre kontrol ediyor. Aralık dışı bir değer olursa preset üretilmiyor, çünkü EasyEffects böyle bir değeri hata vermeden reddedip eski değeri kullanmaya devam ediyor.

Presetleri değiştirmek için `files/easyeffects/make_presets.py` dosyasını düzenleyip `python3 files/easyeffects/make_presets.py` komutunu çalıştır, sonra `./install.sh`'ı tekrar çalıştır.

**Spotify ayarları:** Ses kalitesi "Çok yüksek", "Ses düzeyini normalleştir" kapalı ve uygulamanın ses çubuğu %100'de olsun. Sesi sistemden ya da kulaklığın tekerinden ayarla; compressor gelen sesin seviyesine göre çalıştığı için Spotify kısıkken presetler tasarlandığı gibi çalışmıyor.

## Dynamic Music Pill

[Dynamic Music Pill](https://github.com/Andbal23/dynamic-music-pill), Spotify'da ya da tarayıcıda çalan şarkıyı üst barda kapak resmi, görselleştirici ve kontrol tuşlarıyla gösteren bir GNOME uzantısı. `install.sh` uzantıyı extensions.gnome.org'dan GNOME sürümüne uygun haliyle indiriyor ve `files/gnome/dynamic-music-pill.ini` içindeki ayarları yüklüyor. Dinleme geçmişi bu dosyaya dahil değil.

## Sorun giderme

- **Kulaklık bağlı ama ses gelmiyor:** WirePlumber, EasyEffects açıkken yeniden başlatıldıysa EasyEffects'in kulaklığa olan ses bağlantısı kopar. Şu komut düzeltir:
  ```bash
  easyeffects -q; setsid -f easyeffects --gapplication-service
  ```
- **Kulaklık hâlâ kapanıyor:** Sorunu kaydetmek için ayrı bir terminalde `sudo btmon -w ~/bt-kayit.btsnoop` çalıştır, kulaklığı birkaç kez kapatıp aç, sonra `Ctrl+C` ile durdur. Kaydı `btmon -r ~/bt-kayit.btsnoop` ile okuyabilirsin.
- **Kulaklığa sunulan codec'leri görmek için:**
  ```bash
  journalctl -u bluetooth -b | grep 'Endpoint registered'
  ```
  Ayar çalışıyorsa sadece `sbc` görünmeli. Açılışta 19 satır görmen normal: onları giriş ekranı kaydediyor, oturum açılınca kapanıyorlar.

## Test edilen ortam

Ubuntu 24.04, kernel 7.0, PipeWire 1.0.5, WirePlumber 0.4.17, BlueZ 5.72, EasyEffects 7.1.6, Realtek RTL8821CE (WiFi + Bluetooth).

## Klasör yapısı

```
install.sh                         # tüm düzeltmeleri, presetleri ve uzantıları kurar
uninstall.sh                       # kurulanları kaldırır (presetler ve GNOME uzantıları kalır)
files/
├── bin/ee-preset                  # preset değiştirici (ee-preset <ad> | next)
├── easyeffects/
│   ├── make_presets.py            # presetleri üreten ve şema aralıklarını doğrulayan script
│   ├── output/*.json              # Rap, Tekno - Rave, Deep House, Genel
│   └── autostart/                 # EasyEffects'i oturum açılışında servis olarak başlatır
├── gnome/dynamic-music-pill.ini   # Dynamic Music Pill ayarları (dconf)
├── modprobe/                      # btusb.conf, rtw88.conf
├── networkmanager/                # wifi-powersave-off.conf
├── systemd/                       # arctis-autoconnect.service + .sh (kullanıcı servisi)
└── wireplumber/                   # 51-arctis-a2dp-only.lua (0.4) ve .conf (0.5+)
```

## Proje durumu

Repo 23 Ekim 2026'da oluşturuldu ve aynı gün dört commit ile bugünkü hâline getirildi. Yukarıdaki test ortamında günlük kullanımda. Repoda henüz bir lisans dosyası yok.
