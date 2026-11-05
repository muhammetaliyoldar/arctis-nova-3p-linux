# Arctis Nova 3P Wireless: Ubuntu Bluetooth Düzeltmeleri

SteelSeries Arctis Nova 3P Wireless kulaklığı Ubuntu'da (PipeWire + WirePlumber) Bluetooth ile sorunsuz kullanmak için gereken ayarlar. Yanında Rap, Tekno/Rave, Deep House ve Genel için EasyEffects presetleri ve bunlar arasında tek tuşla geçiş var.

## Kurulum

```bash
sudo apt install -y git
git clone https://github.com/muhammetaliyoldar/arctis-nova-3p-linux.git
cd arctis-nova-3p-linux
./install.sh
```

Script başta hangi parçaların kurulacağını soruyor (Enter = evet, `h` = hayır):

1. **Bağlantı düzeltmeleri:** Üç şey kuruyor.
   - **Kulaklığın bağlanır bağlanmaz kapanması:** Bluetooth codec listesini 19'dan sadece SBC'ye indiriyor.
   - **Güç tasarrufu (cızırtı ve kopma):** Bluetooth USB adaptörünün uykuya geçmesini her bilgisayarda kapatıyor. Bilgisayarda Realtek `rtw88` WiFi kartı varsa WiFi sürücüsünün ve NetworkManager'ın güç tasarrufunu da kapatıyor.
   - **Otomatik bağlanma:** Oturum açıldıktan sonra kulaklığa kendisi bağlanmayı deneyen servisi kuruyor.
2. **Bluetooth mikrofonu kapatılsın mı?** Sadece 1. soruya evet dersen soruluyor. Evet (varsayılan) HFP/HSP'yi kapatıyor; bugüne kadar test edilen ayar bu. Hayır dersen mikrofon açık kalıyor, ama kopmalar geri gelebilir (aşağıda "Belirtiler" altında 1. maddeye bak).
3. **Ses presetleri:** Kurulu değilse EasyEffects'i ve LSP eklentilerini kuruyor. 4 preseti ekliyor, kulaklık bağlanınca **Rap**'in otomatik yüklenmesini ve EasyEffects'in her açılışta arka planda başlamasını ayarlıyor. Ctrl+Alt kısayollarını ve üst bara preset menüsünü (EasyEffects Preset Selector uzantısı) da bu kuruyor.
4. **Spotify'daki türe göre otomatik preset:** Sadece 3. soruya evet dersen soruluyor. Spotify'da şarkı değişince türüne bakıp Rap / Tekno - Rave / Deep House / Genel arasında kendisi geçiyor (ayrıntı aşağıda "Spotify'daki türe göre otomatik preset" altında).
5. **Dynamic Music Pill:** Sadece GNOME varsa soruluyor. Üst barda şarkıyı yönetmeye yarayan uzantıyı indirip kuruyor ve ayarlarını (görünüm, görselleştirici, şeffaflık) yüklüyor.

Notlar:
- Scripti `sudo` ile **değil**, normal kullanıcı olarak çalıştır. Gerekirse sudo şifresini kendisi sorar.
- İstemediğin parçaya `h` de. Örneğin sadece ses presetlerini kurmak için 1., 4. ve 5. soruya `h`, 3. soruya Enter yeterli.
- Terminal yoksa ya da cevap verilmezse hepsi evet sayılıyor.
- Tekrar çalıştırmak güvenli; zaten kurulu olanları baştan yazıyor. Mikrofon seçimini değiştirmek için de scripti tekrar çalıştırman yeterli: seçilen dosya kurulurken öbürü siliniyor.
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

**Çözüm:** WirePlumber'ın kulaklığa sadece **SBC** sunması. Arctis zaten SBC kullanıyor, yani ses kalitesinden bir şey kaybedilmiyor. Ek olarak, kurulumda mikrofonu kapatmayı seçersen (varsayılan), bağlantı kurulurken müzik ve mikrofon profillerinin çakışmasını önlemek için HFP/HSP (Bluetooth mikrofon) profili de kapatılıyor.

> ⚠️ **Mikrofon kapalıyken** (varsayılan, test edilen ayar) bu bilgisayarda Bluetooth kulaklıkların **mikrofonu çalışmaz**, müzik ve ses normal çalışır.
>
> **Mikrofon açıkken** sadece SBC ayarı kuruluyor. Bu seçenek henüz **test edilmedi**. Açılışta A2DP ve HFP aynı anda kurulmaya çalışınca bağlantılar çakışıp kulaklık kapanıyordu; bu kopmalar geri gelebilir. Öyle olursa scripti tekrar çalıştırıp mikrofonu kapat. Ayrıca mikrofon açıkken bir uygulama mikrofonu açınca kulaklık mikrofon profiline geçer ve ses telefon görüşmesi kalitesine düşer (Bluetooth'un sınırı).
>
> İki seçenekte de ayar sadece kurulduğu Linux bilgisayarı etkiler. Kulaklığın kendisine, Windows'a, Mac'e ya da telefona dokunulmuyor; oralarda mikrofon eskisi gibi çalışır.

Dosyalar:

| | Mikrofon kapalı (varsayılan) | Mikrofon açık |
|---|---|---|
| WirePlumber 0.4 (Ubuntu 24.04) | `~/.config/wireplumber/bluetooth.lua.d/51-arctis-a2dp-only.lua` | `~/.config/wireplumber/bluetooth.lua.d/51-arctis-sbc-only.lua` |
| WirePlumber 0.5+ | `~/.config/wireplumber/wireplumber.conf.d/51-arctis-a2dp-only.conf` | `~/.config/wireplumber/wireplumber.conf.d/51-arctis-sbc-only.conf` |

Hangisinin kurulacağına `install.sh` kendisi karar veriyor. Birini kurarken öbürünü siliyor. WirePlumber 0.4, `.conf` dosyalarını **okumaz**; internetteki çoğu rehber 0.5 formatını anlattığı için bu önemli.

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

Presetleri değiştirmek için `files/easyeffects/make_presets.py` dosyasını düzenleyip `python3 files/easyeffects/make_presets.py` komutunu çalıştır, sonra `./install.sh`'ı tekrar çalıştır. Aynı komut Windows (`files/equalizer-apo/`) ve kulaklık (`files/headset/`) dosyalarını da aynı eğrilerden yeniden üretiyor.

**Spotify ayarları:** Ses kalitesi "Çok yüksek", "Ses düzeyini normalleştir" kapalı ve uygulamanın ses çubuğu %100'de olsun. Sesi sistemden ya da kulaklığın tekerinden ayarla; compressor gelen sesin seviyesine göre çalıştığı için Spotify kısıkken presetler tasarlandığı gibi çalışmıyor.

### Spotify'daki türe göre otomatik preset

Spotify masaüstü uygulamasında şarkı değişince servis sanatçı ve şarkı adını alıyor (Linux'un medya oynatıcı arayüzü MPRIS üzerinden) ve türü buluyor:
1. Deezer'de şarkıyı arıyor. Albümün türü "Rap/Hip Hop" ise **Rap**.
2. Albüm elektronikse (Electro, Techno/House, Dance) ya da şarkı Deezer'de yoksa MusicBrainz'deki sanatçı etiketlerine bakıyor. techno, tech house, rave, trance, hardstyle → **Tekno - Rave**. house (deep house, melodic house vb.) → **Deep House**. hip hop, rap, trap, drill, grime → **Rap**.
3. Bunların dışındaki her şey (pop, rock, Türk pop, drum and bass vb.) → **Genel**.

Spotify'ın kendi API'si Şubat 2026'dan beri kişisel uygulamalara tür bilgisi vermiyor; o yüzden Deezer ve MusicBrainz kullanılıyor. İkisi de hesap ya da anahtar istemiyor. Bu servislere sadece sanatçı ve şarkı adı gidiyor.

- Sonuç albüm başına `~/.cache/spotify-genre-preset.json` dosyasına yazılıyor; aynı albüm bir daha sorulmuyor. Yanlış bulunan bir albümü düzeltmek için bu dosyadan o satırı sil (ya da dosyayı sil).
- Preset sadece tür değişince değişiyor, bildirim de o zaman çıkıyor. Kısayolla (`Ctrl+Alt+1..4`) elle seçtiğin preset, tür değişene kadar korunuyor.
- İnternet yoksa ya da servisler cevap vermezse preset değişmiyor; o albüm sonraki şarkıda tekrar deneniyor.
- Ne yaptığını izlemek için: `journalctl --user -u spotify-genre-preset -f` (her şarkı için "Sanatçı - Şarkı: Preset" satırı yazıyor).
- Geçici olarak kapatmak için: `systemctl --user stop spotify-genre-preset`. Tamamen kapatmak için `./install.sh`'ı tekrar çalıştırıp bu soruya `h` de.

Sınırlar:
- Tür şarkıya değil albüme (Deezer) ya da sanatçıya (MusicBrainz) göre bulunuyor. Rapçinin pop şarkısı da Rap olur.
- MusicBrainz'de sanatçı adla aranıyor. Deezer'de bulunamayan ve adı başka bir sanatçıyla aynı olan şarkılarda yanlış sanatçı seçilebiliyor. Türkçe rapte Deezer kapsamı iyi olduğu için bu nadiren gerekiyor.
- Sadece Spotify masaüstü uygulaması izleniyor; tarayıcıdaki Spotify ya da YouTube izlenmiyor.
- Test: 10 örnek şarkının 10'u doğru (Ben Fero, Motive, Lvbel C5, Travis Scott → Rap; Charlotte de Witte, Amelie Lens → Tekno - Rave; Kerri Chandler, Lane 8 → Deep House; Sezen Aksu, Duman → Genel). Servis, sahte bir Spotify ile uçtan uca denendi; gerçek Spotify ile henüz denenmedi.

## Diğer cihazlar: Windows ve kulaklığın kendi EQ'su

Linux'taki ayarlar diğer cihazlara taşınmıyor. Aynı 4 eğri iki yoldan başka cihazlarda kullanılabilir. EQ'yu tek yerde aç: kulaklığın EQ'su ile EasyEffects ya da Equalizer APO aynı anda açıksa yükseltmeler toplanır (örn. Rap'te 50 Hz +5 dB iki kez = +10 dB), bas patlar.

### Kulaklığın kendi EQ'su (her cihazda geçerli)

- Nova 3P'nin içinde 10 bantlı parametrik EQ var. Ayar kulaklıkta saklanıyor, yani hangi cihaza bağlanırsa bağlansın aynı ses geliyor; o cihaza bir şey kurmak gerekmiyor (telefon, PS5, iş bilgisayarı).
- SteelSeries 2.4GHz ve Bluetooth için ayrı EQ profili tutuyor; güç tuşuyla mod değişince o modun profili kendiliğinden devreye giriyor.
- Bu EQ'yu SteelSeries GG (Windows/macOS, Engine sekmesi) ya da telefondaki Arctis Companion uygulaması ayarlıyor. Linux'tan da açık kaynak [HeadsetControl](https://github.com/Sapd/HeadsetControl) ile yazılabiliyor (Linux, Windows, macOS'ta çalışıyor).
- `files/headset/*.txt` dosyaları HeadsetControl'ün bant biçiminde: her bant `frekans,kazanç,Q,tip`, bantlar `;` ile ayrılıyor. GG'de ya da Companion'da elle girmek istersen değerler aynı.

Kurulum ve yazma (Ubuntu):

```bash
sudo add-apt-repository ppa:sapd/headsetcontrol
sudo apt update && sudo apt install headsetcontrol
# USB-C alıcıyı tak, kulaklığı 2.4GHz modunda aç
headsetcontrol --parametric-equalizer "$(cat files/headset/Rap.txt)"
# Düz (EQ'suz) hale döndürmek için:
headsetcontrol --parametric-equalizer reset
```

Windows'ta HeadsetControl'ün kurulum dosyası GitHub Releases sayfasında.

Sınırlar:
- HeadsetControl kulaklığa USB-C alıcı üzerinden ulaşıyor; Bluetooth üzerinden çalışmıyor. Kulaklık açık ve 2.4GHz modunda olmalı.
- Alıcı üzerinden yazılan EQ'nun sadece 2.4GHz profiline mi, Bluetooth profiline de mi gittiği henüz **test edilmedi**. Denemek için: yazdıktan sonra kulaklığı Bluetooth'a geçir, Linux'ta EasyEffects'i kapat (`easyeffects -q`) ve dinle. Bas belirgin şekilde artmışsa Bluetooth profili de değişmiş demektir; o zaman Linux'ta EasyEffects ile birlikte kullanma.
- Kulaklıkta compressor ve limiter yok, girişte ses kısma (preamp) da yok. Linux'taki zincirin sadece EQ kısmı taşınıyor; çok yüksek seste basta bozulma duyarsan kulaklıkta düz EQ'ya dön.
- 20 Hz altı desteklenmiyor; Genel'deki 18 Hz'lik filtre kulaklıkta 20 Hz'e çekiliyor (duyulur fark yok).
- GG ya da Companion'da EQ'yu değiştirirsen kulaklıktaki ayar onunla değişir.

### Windows: Equalizer APO

- `files/equalizer-apo/*.txt` dosyaları [Equalizer APO](https://sourceforge.net/projects/equalizerapo/) biçiminde. Girişteki ses kısma (Preamp) Linux'takiyle aynı, eğri clipping yapmıyor. Compressor ve limiter yok.

Adımlar:
1. Equalizer APO'yu kur; kurulumda açılan Configurator'da kulaklığı (Bluetooth ve/veya USB alıcı cihazı) işaretle, sonra yeniden başlat.
2. `files/equalizer-apo/` içindeki 4 dosyayı `C:\Program Files\EqualizerAPO\config\` klasörüne kopyala.
3. Aynı klasördeki `config.txt`'nin içeriğini tek satır yap: `Include: Rap.txt`
4. Preset değiştirmek için bu satırdaki dosya adını değiştirip kaydet; Equalizer APO dosyayı kendisi yeniden yüklüyor.

### macOS

Hazır dosya yok; en kolayı kulaklığın kendi EQ'su (yukarıda) ya da GG.

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
install.sh                         # düzeltmeleri, presetleri ve uzantıları (istediğini seçerek) kurar
uninstall.sh                       # kurulanları kaldırır (presetler ve GNOME uzantıları kalır)
LICENSE                            # MIT
files/
├── bin/
│   ├── ee-preset                  # preset değiştirici (ee-preset <ad> | next)
│   └── spotify-genre-preset       # Spotify'daki türe göre preseti değiştiren servis
├── easyeffects/
│   ├── make_presets.py            # presetleri (EasyEffects, Equalizer APO, kulaklık) üreten ve şema aralıklarını doğrulayan script
│   ├── output/*.json              # Rap, Tekno - Rave, Deep House, Genel
│   └── autostart/                 # EasyEffects'i oturum açılışında servis olarak başlatır
├── equalizer-apo/*.txt            # Windows Equalizer APO karşılıkları (make_presets.py üretir)
├── gnome/dynamic-music-pill.ini   # Dynamic Music Pill ayarları (dconf)
├── headset/*.txt                  # kulaklığın kendi EQ'su için HeadsetControl bantları (make_presets.py üretir)
├── modprobe/                      # btusb.conf, rtw88.conf
├── networkmanager/                # wifi-powersave-off.conf
├── systemd/                       # arctis-autoconnect (otomatik bağlanma) ve spotify-genre-preset (tür takibi) kullanıcı servisleri
└── wireplumber/                   # 51-arctis-a2dp-only (mikrofon kapalı) ve 51-arctis-sbc-only (mikrofon açık); her biri .lua (0.4) ve .conf (0.5+)
```

## Proje durumu

Repo 23 Ekim 2026'da oluşturuldu ve aynı gün dört commit ile bugünkü hâline getirildi. Yukarıdaki test ortamında günlük kullanımda.

## Lisans

[MIT](LICENSE)
