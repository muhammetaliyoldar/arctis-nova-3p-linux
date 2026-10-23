# Arctis Nova 3P Wireless: Ubuntu Bluetooth Düzeltmeleri

SteelSeries Arctis Nova 3P Wireless kulaklığı Ubuntu'da (PipeWire + WirePlumber) Bluetooth ile sorunsuz kullanmak için gereken ayarlar ve rap / deep house için EasyEffects presetleri.

## Kurulum

```bash
sudo apt install -y git
git clone https://github.com/muhammetaliyoldar/arctis-nova-3p-linux.git
cd arctis-nova-3p-linux
./install.sh
```

Script sırasıyla şunları yapıyor:

1. **Kulaklığın bağlanır bağlanmaz kapanması:** Bluetooth codec listesini 19'dan sadece SBC'ye indiriyor ve HFP'yi kapatıyor.
2. **Cızırtı ve kopma:** Bilgisayarda Realtek `rtw88` WiFi kartı varsa sürücünün güç tasarrufunu kapatıyor.
3. **Otomatik bağlanma:** Oturum açıldıktan sonra kulaklığa kendisi bağlanmayı deneyen servisi kuruyor.
4. **EasyEffects:** Kurulu değilse EasyEffects'i ve LSP eklentilerini kuruyor. Presetleri ekliyor, kulaklık bağlanınca "Ana - HipHop House"un otomatik yüklenmesini ve EasyEffects'in her açılışta arka planda başlamasını ayarlıyor.
5. **Dynamic Music Pill:** Üst barda şarkıyı yönetmeye yarayan GNOME uzantısını indirip kuruyor ve ayarlarını (görünüm, görselleştirici, şeffaflık) yüklüyor.

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

### 2. Ses cızırtılı ya da kesik geliyor (sadece Realtek rtw88 WiFi kartlarında)

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
`install.sh` bu ayarı sadece bilgisayarda `rtw88` sürücüsü varsa kuruyor. Kurduktan sonra bilgisayarı yeniden başlatman gerekiyor.

Bilgisayarında bu kart var mı diye bakmak için:
```bash
journalctl -k -b | grep -c 'failed to leave lps'   # 0'dan büyükse bu sorun var
```

### 3. Bilgisayar açılırken kulaklık açıksa otomatik bağlanmıyor

Kulaklık açılınca bilgisayara bağlanmayı deniyor. Bilgisayar o sırada henüz açılmamışsa kulaklık vazgeçiyor, bilgisayar da kendisi tekrar denemiyor. `arctis-autoconnect.service` oturum açıldıktan sonra 2 dakika boyunca 10 saniyede bir kulaklığa bağlanmayı deniyor, bağlanınca da duruyor.

## EasyEffects presetleri

Presetlerin hepsinde aynı zincir var: **Equalizer → Compressor → Limiter**. Limiter -1 dB'de tavan yaptığı için bas ne kadar güçlü olursa olsun cızırtı ya da patlama olmuyor. Sadece LSP eklentileri kullanılıyor (`sudo apt install easyeffects lsp-plugins`).

| Preset | Karakter |
|---|---|
| **Ana - HipHop House** | Varsayılan. Kulaklık bağlanınca otomatik yükleniyor. 808 ve sub-bass güçlü, 250 Hz civarı kısıldığı için bas çamurlaşmadan vuruyor, vokal net, Bluetooth'un tizlerdeki sertliği yumuşatılmış. |
| **Deep House** | Sub-bass ve kick daha baskın, hi-hat'lerde daha fazla hava var. Compressor'ün attack'i yavaş, vuruşun ilk anı ezilmeden geçiyor. |
| **Rap - HipHop** | 808 en güçlü haliyle, vokal en önde, compressor daha agresif. |
| **Genel Muzik** | Her türe uyan hafif bir V eğrisi. Uzun dinlemede kulağı yormuyor. |

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
