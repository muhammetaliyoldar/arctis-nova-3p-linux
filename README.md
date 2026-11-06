# Arctis Nova 3P Wireless: Ubuntu Bluetooth Düzeltmeleri

SteelSeries Arctis Nova 3P Wireless kulaklığı Ubuntu'da (PipeWire + WirePlumber) Bluetooth ile sorunsuz kullanmak için gereken ayarlar. Yanında Genel, 24 ana tür ve 38 alt tür için toplam 63 EasyEffects preseti var (5 ana tür Türkçe; alt türlerin bir kısmı da Türkçe). Çalan şarkının türüne göre preset kendiliğinden değişiyor, istersen tek tuşla elle de geçebilirsin. Windows ve macOS için de türe göre EQ (tür takibi + menü) sürümü var; ikisi henüz gerçek cihazda denenmedi. Ayrıntı için "Diğer cihazlar" bölümüne bak.

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
3. **Ses presetleri:** Kurulu değilse EasyEffects'i ve LSP eklentilerini, ayrıca Calf eklentilerini (`calf-plugins`) kuruyor (apt, sudo ister). 63 preseti ekliyor (100 türlük sürümden kalan presetleri ve v1'in Rap, Tekno - Rave, House - Disco presetlerini EasyEffects'te eski-presetler klasörüne alıyor; kendi presetlerine dokunmuyor), açılışta ve kulaklık bağlanınca **Genel**'in otomatik yüklenmesini ve EasyEffects'in her açılışta arka planda başlamasını ayarlıyor. Ctrl+Alt kısayollarını da bu kuruyor. Üst bar preset menüsü olarak 4. soruya hayır dersen EasyEffects Preset Selector uzantısı, evet dersen kendi menümüz kuruluyor.
4. **Spotify'daki türe göre otomatik preset:** Sadece 3. soruya evet dersen soruluyor. Spotify'da şarkı değişince türüne bakıp o türün presetine kendisi geçiyor. Ardından en çok dinlenen türlerin kaynağını soruyor: 1) bu bilgisayardaki dinlemelerin, 2) Spotify hesabın (Enter: Spotify bağlıysa 2, değilse 1; sonra menüden değişir). Ayrıca üst bara çalan türü, kilidi ve en çok dinlenen türleri gösteren kendi menümüzü kuruyor (ayrıntı aşağıda "Spotify'daki türe göre otomatik preset" altında; Spotify hesabını bağlamak için "Spotify hesabını bağlama" bölümüne bak).
5. **Dynamic Music Pill:** Sadece GNOME varsa soruluyor. Üst barda şarkıyı yönetmeye yarayan uzantıyı indirip kuruyor ve ayarlarını (görünüm, görselleştirici, şeffaflık) yüklüyor.

Notlar:
- Scripti `sudo` ile **değil**, normal kullanıcı olarak çalıştır. Gerekirse sudo şifresini kendisi sorar.
- İstemediğin parçaya `h` de. Örneğin sadece ses presetlerini kurmak için 1., 4. ve 5. soruya `h`, 3. soruya Enter yeterli.
- Terminal yoksa ya da cevap verilmezse hepsi evet sayılıyor.
- Hepsini hazır cevapla kurmak için: `printf 'h\n\n\n\nh\n' | ./install.sh` (bağlantı düzeltmeleri hayır, presetler evet, tür takibi evet, kaynak modu varsayılan, Music Pill hayır).
- Tekrar çalıştırmak güvenli; zaten kurulu olanları baştan yazıyor. Mikrofon seçimini değiştirmek için de scripti tekrar çalıştırman yeterli: seçilen dosya kurulurken öbürü siliniyor.
- Music pill kurulduktan sonra üst barda görünmezse oturumu kapatıp aç. Wayland'de yeni kurulan uzantılar ancak bir sonraki oturumda yükleniyor.
- Kulaklığı önce Bluetooth'tan eşleştirmen iyi olur. Eşleştirmeden kurarsan, eşleştirdikten sonra scripti bir kez daha çalıştır; böylece otomatik preset yüklemesi de ayarlanır.
- Kaldırmak için: `./uninstall.sh`

Windows ve macOS kurulumu aşağıda "Diğer cihazlar" bölümünde.

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

63 preset var: **Genel**, 24 ana tür (`files/genres.json`) ve 38 alt tür (aşağıda "Alt türler"). **Genel** varsayılan; açılışta ve (tür takibi kurulu değilse) kulaklık bağlanınca yükleniyor; tür takibi kuruluysa kulaklık kopup bağlanınca çalan şarkının preseti kalıyor, sadece kulaklık düzeltmesi tabanı var. Türlerin hepsi aynı kulaklık düzeltmesi tabanı üstüne kendi farklarını ekliyor.

Her ana türün eğrisi, o gruptaki en çok dinlenen alt türün eski eğrisinden başlıyor: Pop ← Synthpop, House ← genel/tech house eğrisi (kick 55 Hz, tiz biraz daha kısık; eski French House eğrisi Fransız House alt türünde), Bass Müziği ← UK Garage, Latin ← Latin Pop, Türk Halk - Sanat ← Türk Halk; diğerleri kendi adlı eski eğrisi. En çok dinlenen türlerden altısı (Türkçe Rap, Hip Hop, Elektronik, Bass Müziği, Indie, Folk - Akustik) dinlenen sanatçıların prodüktör ve mix mühendislerinin anlattıklarına göre 0.5-1 dB ayarlandı; hiçbiri henüz kulakla denenmedi.

Dosya adında "/" olamadığı için birleşik adlar " - " ile yazılıyor: "Türk Halk - Sanat", "Folk - Akustik", "Ambient - Lo-fi".

Aşağıdaki 38 alt tür dışındaki alt türler preset olarak kaldırıldı ama tanınmaya devam ediyor: MusicBrainz'deki kelimeler ana türe yönleniyor (örn. "uk garage" → Bass Müziği, "dream pop" → Indie).

| Ana tür | İçine katılanlar |
|---|---|
| Türkçe Rap | Türkçe rap ve trap (alt tür listesindeki sanatçılar kendi alt türünde çalar) |
| Hip Hop | Trap, Drill, Boom Bap, Phonk, Grime, Pop Rap |
| Pop | Synthpop, Electropop, Dance Pop, Hyperpop, K-pop, J-pop |
| Türkçe Pop | Türkçe pop |
| Rock | Hard Rock, Klasik Rock, Punk, Grunge, Post-Punk, Blues |
| Türkçe Rock | Anadolu Rock |
| Metal | Heavy Metal, Thrash Metal, Death Metal, Metalcore, Nu Metal |
| Indie | Türkçe Indie, Indie Rock, Indie Pop, Dream Pop, Shoegaze, Psikedelik |
| R&B | Alternatif R&B, Neo Soul, Soul, Funk, Gospel |
| House | Tech House, Progressive House, French House, Nu-Disco, Disco |
| Deep House | Afro House |
| Techno | Hard Techno, Melodic Techno, Trance, Psytrance |
| Bass Müziği | Drum & Bass, Jungle, Dubstep, UK Garage |
| EDM | Hardstyle, Future Bass |
| Elektronik | Synthwave, Downtempo, Trip Hop |
| Ambient - Lo-fi | Ambient, Lo-fi Hip Hop |
| Latin | Reggaeton, Latin Pop, Salsa, Bachata, Cumbia, Meksika Müziği |
| Afrobeats | Amapiano |
| Reggae | Dancehall |
| Arabesk | Arap Müziği, Fantezi |
| Türk Halk - Sanat | Türk Halk, Türk Sanat |
| Folk - Akustik | Folk, Akustik, Country, Indie Folk |
| Caz | Smooth Jazz, Bossa Nova |
| Klasik | Opera, Neoklasik, Film Müziği |

Türkçe türler: Türkçe Rap, Türkçe Pop, Türkçe Rock, Arabesk, Türk Halk - Sanat. Türkçe Indie ve Anadolu Rock ayrı tür değil (Indie ve Türkçe Rock'a katıldı). Türkçe Rap, Türkçe Pop ve Türkçe Rock'ın alt türleri ile Türk Halk - Sanat'ın alt türleri ayrıca preset olarak var (aşağıda "Alt türler").

Tür farkları türlerin bilinen frekans karakterine göre tasarlandı, kulakla denenmedi. En çok tahmine dayalı olanlar: Arabesk, Türk Halk - Sanat, Afrobeats ve Latin.

Kısayollar: `Ctrl+Alt+1..7` üst bar menüsündeki 1.-7. satır (sıra dinlemene göre değişiyor); `Ctrl+Alt+0` menüde sıradaki preset. Tür takibi kurulu değilse menü yerine `files/genres.json`'daki varsayılan 5 tür + Genel kullanılıyor.

Preset değişince ekranda bildirim çıkıyor. Ayrıca üst bardaki menüden fareyle de seçebilirsin (tür takibi kuruluysa kendi menümüz, değilse EasyEffects Preset Selector). Terminalden geçmek için: `ee-preset "Türkçe Rap"`, `ee-preset next`.

**Zincir:** Presetlerin hepsinde **Equalizer → Compressor → Limiter** var; compressor her türde aynı değil: kimisinde kapalı, kimisinde hafif yapıştırma, rapte punch ayarı var. Equalizer, Compressor ve Limiter LSP eklentisi. Beş preset araya Calf eklentisi alıyor: Türkçe Trap, Cloud Rap ve Festival Trap'e **Bass Enhancer**, Türkçe Deneysel Rap ve Anadolu Klasikleri'ne **Stereo Tools** (Equalizer → Bass Enhancer / Stereo Tools → Compressor → Limiter). `install.sh` bunlar için `calf-plugins` paketini kuruyor; Calf yoksa EasyEffects o eklentiyi atlıyor, preset yine yükleniyor. Windows'a (Equalizer APO), macOS'a (CamillaDSP) ve kulaklığın kendi EQ'suna yalnız EQ taşınıyor.
- **Equalizer:** Her presette aynı kulaklık düzeltmesi tabanı var: 105 Hz bas rafı +2.5, 160 Hz -4 (kulaklığın 100-250 Hz'teki çamur tümseği), 500 Hz +2, 4.3 kHz +4 (kulaklığın 4-5 kHz çukuru: vokal ve atak), 9 kHz -3.5 (8-10 kHz sertliği). Nova 3P'nin yayımlanmış ölçümü yok; taban, kardeş modeller Nova 3 ve Nova 5'in AutoEq/rtings ölçümlerinin Harman OE 2018 hedefinden farkına göre yumuşatıldı. SBC codec 12 kHz üstünü bozduğu için oraya yükseltme yok. Türler tabanın üstüne kendi bantlarını ekliyor (en fazla 2 Bell). Filtreler "APO (DR)" modunda; Windows'taki Equalizer APO ile birebir aynı eğri. Girişteki ses kısma otomatik: eğrinin tepesi + 1 dB. Böylece equalizer'ın kendisi clipping yapmıyor (`python3 files/easyeffects/make_presets.py --check` ile eğriler kontrol edilebilir).
- **Compressor:** Attack 30 ms, sidechain 100 Hz high-pass: 808 bütün mixi pompalamasın. Kick'in ve 808'in ilk vuruşu ezilmeden geçiyor. Techno, house, bass müziği, EDM, pop, rock, metal, indie gibi türlerde kapalı, çünkü bu türlerin masterları zaten çok sıkıştırılmış; ikinci compressor onları ezer. Klasik, caz ve akustikte de kapalı, dinamik korunuyor. R&B, soul, reggae, Arabesk gibi dinamik kayıtlarda hafif yapıştırma açık.
- **Limiter:** -1 dB'de tavan yapıyor, ama sadece güvenlik ağı. EasyEffects 7.x'te limiter'ın release süresi en fazla 20 ms olabiliyor. 50 Hz'lik bir bas dalgası da 20 ms sürdüğü için limiter her devreye girdiğinde sesi bas dalgasının *içinde* açıp kısıyor ve basta bozulma yapıyor. Bu yüzden compressor'de çıkış artırması (makeup) yok ve EQ girişi eğrinin tepesi + 1 dB kadar kısılıyor; sinyal limiter'a nadiren ulaşıyor. Ses biraz kısık gelirse kulaklığın tekerinden aç.
- Bu eğriler ölçüm ve kaynaklara göre tasarlandı, kulakla henüz denenmedi. Bas az gelirse ilgili Bell kazancını `make_presets.py`'de artırıp scripti ve `./install.sh`'ı tekrar çalıştır.
- `make_presets.py` değerleri EasyEffects şemasındaki aralıklara göre kontrol ediyor. Aralık dışı bir değer olursa preset üretilmiyor, çünkü EasyEffects böyle bir değeri hata vermeden reddedip eski değeri kullanmaya devam ediyor.

Presetleri değiştirmek için `files/easyeffects/make_presets.py` dosyasını düzenleyip `python3 files/easyeffects/make_presets.py` komutunu çalıştır, sonra `./install.sh`'ı tekrar çalıştır. Aynı komut Windows (`files/equalizer-apo/`) ve kulaklık (`files/headset/`) dosyalarını da aynı eğrilerden yeniden üretiyor.

**Spotify ayarları:** Ses kalitesi "Çok yüksek", "Ses düzeyini normalleştir" kapalı ve uygulamanın ses çubuğu %100'de olsun. Sesi sistemden ya da kulaklığın tekerinden ayarla; compressor gelen sesin seviyesine göre çalıştığı için Spotify kısıkken presetler tasarlandığı gibi çalışmıyor.

### Alt türler

38 alt tür ayrı preset:

- **Türkçe Rap:** Türkçe Trap, Türkçe Boom Bap, Türkçe Melodik Rap, Türkçe Sert Rap, Türkçe Old School, Türkçe Deneysel Rap
- **Hip Hop:** Yabancı Melodik Rap, Alternatif Hip Hop, Cloud Rap
- **Indie:** Neo-Psikedelik, Indie Elektronik, Rüya Pop
- **Bass Müziği:** Liquid DnB, Neurofunk - Jump Up, Dubstep - Riddim, Melodik Dubstep, Festival Trap
- **Elektronik:** Hypertechno, Darksynth, Art Pop Elektronik
- **House:** Fransız House, Disko Funk, Tropikal House, Lo-fi House
- **Türk Halk - Sanat:** Akustik Türkü, Modern Türkü, Oyun Havası
- **Folk - Akustik:** Folk Pop, Singer-Songwriter, Country - Americana
- **Türkçe Pop:** Alternatif Pop, Akustik Pop, Hareketli Pop, 90'lar Pop
- **Türkçe Rock:** Anadolu Psych, Anadolu Klasikleri, Türkçe Sert Rock, Türkçe Pop Rock

Tanımlar `files/easyeffects/make_presets.py` içindeki `SUBGENRES`'te; `files/genres.json`'da `"subgenres"` olarak (ad, ana tür, sanatçılar, keywords) duruyor.

- **Nasıl tanınır:** İki yolla. (a) Sanatçı listesi: çalan sanatçı bir alt türün listesindeyse (kullanıcının dinledikleri + alt türün bilinen adları) servis ağ sorgusu yapmadan o alt türün presetini çalıyor. (b) Listede yoksa ana tür eskisi gibi (Deezer + MusicBrainz) bulunuyor, sonra sanatçının MusicBrainz etiketleri oy sırasıyla taranıyor; o ana türün bir alt türünün anahtar kelimesini içeren ilk etiket alt türü seçiyor (en uzun kelime kazanır; ör. "liquid funk" → Liquid DnB, "cloud rap" → Cloud Rap). Amaç: yeni keşfedilen sanatçılar da doğru alt türe düşsün. Türk sanatçılarda MusicBrainz etiketi az, orada asıl yol liste. Hiçbir kelime eşleşmezse ana tür çalıyor. Sebep: hiçbir tür kaynağı (Spotify artık tür vermiyor, MusicBrainz) Türkçe trap ile boom bap'i ayırmıyor. Servisin Türkçe tanıyamayıp Hip Hop'a düşürdüğü Türk rapçiler (Jefe, Harim, Laçin, PAN, Istanbul Trip, Murda vb.) ilgili Türkçe Rap alt türünün listesinde.
- **Ana tür kelime düzeltmeleri:** Bass Müziği'ne "trap edm", "festival trap", "hybrid trap" eklendi (Hip Hop'un "trap" kelimesini yeniyor), Elektronik'e "witch house" (House'a düşmesin), Türk Halk - Sanat'a "classical turkish" (Klasik'e düşmesin).
- **Düşme kuralı:** Alt türün preset dosyası yoksa ana türün presetine, o da yoksa Genel'e düşüyor. Ara katman yok.
- **Menü:** Menü ve "en çok dinlenen" sıralaması ana tür düzeyinde kalıyor. Çalan alt tür üst barda (panel etiketi) ve menünün en altında geçici satır olarak görünüyor.
- **Eğriler:** Kullanıcının kendi parçalarının EQ öncesi ölçümünden çıkarıldı (Türkçe Rap alt türü başına 4 parça, Hip Hop 14, Indie 10 parça; 808/kick tepe frekansı, spektrum, dinamik). Hip Hop ve Indie alt türlerinin farkları kendi ana türünün ortalamasına göre. Kısaca: Trap derin 808 (40 Hz) + vokal 1.5 kHz, compressor yok, Bass Enhancer; Boom Bap kick gövdesi 60 Hz + snare/vokal 2.2 kHz, punch compressor; Melodik yumuşak bas + 300 Hz sıcaklık, hafif yapıştırma; Sert kick yumruğu 65 Hz, tiz yormasın diye kısık, compressor yok; Old School olmayan sub şişirilmez (high-pass 30 Hz), 70 Hz ağırlık, 13 kHz hışırtı kısılır, punch; Deneysel derin sub 40 Hz + biraz stereo genişlik (Stereo Tools); Yabancı Melodik Rap 808 tam 50 Hz + vokal 2 kHz öne, hafif yapıştırma; Alternatif Hip Hop sub şişirilmez (high-pass 25 Hz), kick/bas gövdesi 70 Hz + 1.5 kHz orta; Cloud Rap derin sub 40 Hz + Bass Enhancer, koyu tiz biraz açılır, compressor yok; Neo-Psikedelik bas grubu 80 Hz, alt-orta sıcak, tiz yumuşak; Indie Elektronik derin sub 40 Hz, koyu tiz biraz açılır; Rüya Pop bas az, 250 Hz sıcaklık, tiz parıltısı açık, hafif yapıştırma (tek parça ölçümünden). Yeni 26 alt tür için ölçüm Deezer'ın 30 sn önizlemelerinden, EQ öncesi alındı (Spotify'a dokunulmadı; alt tür başına 5-6 parça, farklar kendi ana türünün ölçülen ortalamasına göre):
  - **Bass Müziği:** Liquid DnB gövde 65 Hz, sıcaklık kalır, parıltı açık; Neurofunk - Jump Up sub reese'in altında ayrı durur, 2-5 kHz sertlik alınır; Dubstep - Riddim en derin sub + 40 Hz, tiz yormasın; Melodik Dubstep drop'ta sub dolar, koyu tiz biraz açılır; Festival Trap Türkçe Trap gibi 808 göğüste + Bass Enhancer, hat ve siren yormasın.
  - **Elektronik:** Hypertechno kick temeli, parlaklık yormasın; Darksynth gövde yığılması alınır, oyuk orta biraz dolar; Art Pop Elektronik olmayan sub şişirilmez, sıcaklık kalır, yumuşak üst orta açılır.
  - **House:** Fransız House eski ana House eğrisi (kick/bas 63-80 Hz, 315-400 Hz kesik); Disko Funk bas gitar gövdesi ve funk gitar öne, hafif yapıştırma; Tropikal House ince alt biraz dolar, yumuşak üst orta açılır; Lo-fi House çamur alınır, koyu kaynak daha da boğulmaz.
  - **Türk Halk - Sanat:** Akustik Türkü olmayan bas şişirilmez, bağlama gövdesi öne, koyu tiz biraz açılır; Modern Türkü kick/bas gitar göğüste, vokal bandın üstünde; Oyun Havası düm/davul vuruşu göğüste, klarnet/zurna tizi yormasın.
  - **Folk - Akustik:** Folk Pop stomp/kick göğüste, orta inceltilmez; Singer-Songwriter yakınlık tümseği alınır, nefes ve tel sesi açılır, dinamik korunur; Country - Americana kick ve bas gövdesi öne.
  - **Türkçe Pop:** Alternatif Pop sub biraz dolar, gövde yığılması alınır; Akustik Pop gitar/ses gövdesi öne, sub şişirilmez; Hareketli Pop kick göğüste, el çırpma ve sibilans yormasın; 90'lar Pop kick/synth bas gövdesi, olmayan sub şişirilmez, hafif yapıştırma.
  - **Türkçe Rock:** Anadolu Psych bas groove 65 Hz; Anadolu Klasikleri ince bas, koyu tiz daha boğulmaz, stereo biraz daraltılır (Stereo Tools); Türkçe Sert Rock kick yumruğu, gitar çamuru alınır, cızırtı yormasın; Türkçe Pop Rock gövde fazlası alınır, vokal önde, hafif yapıştırma.

  Kulakla yalnız Türkçe Trap onaylandı; diğer 37 alt tür henüz denenmedi.
- **Sanatçı eklemek:** `make_presets.py`'de `SUBGENRES` içindeki ilgili sanatçı listesine ekle (anahtar kelime de aynı yerde, SUBGENRES'in son listesine eklenir), `python3 files/easyeffects/make_presets.py` çalıştır, `./install.sh`'ı tekrar çalıştır. Aynı sanatçı iki alt türde olamaz, aynı ana türün alt türlerinde aynı anahtar kelime de iki kez olamaz (`check_catalog` engelliyor).

### Spotify'daki türe göre otomatik preset

Spotify masaüstü uygulamasında şarkı değişince servis sanatçı ve şarkı adını alıyor (Linux'un medya oynatıcı arayüzü MPRIS üzerinden), türü buluyor ve o türün presetine geçiyor. Tür bulunamazsa **Genel** kalıyor.

**Tür nasıl bulunuyor:** Deezer albüm türü ve MusicBrainz sanatçı etiketleri kullanılıyor. İkisi de hesap ya da anahtar istemiyor. Spotify'ın kendi API'si Şubat 2026'dan beri kişisel uygulamalara tür bilgisi vermiyor; o yüzden bu iki servis var. Servislere sadece sanatçı ve şarkı adı gidiyor.
- Etiketlerden oyu en yüksek 5 etiket içinde Deezer'ın üst düzey türlerine karşılık gelen geniş türlerden (Pop, Elektronik, Rock, Indie, Hip Hop, EDM...) daha özel bir tür varsa o seçiliyor (House, Techno, Deep House, Bass Müziği, Ambient - Lo-fi, Türkçe türler). Örnek: "electronic, uk garage" → Bass Müziği. Daha özel tür yoksa geniş tür kalıyor.
- Deezer türü etiketten farklı bir aileden ve kesinse (rap, R&B, metal, caz...) ona güveniliyor. Pop, dans, elektronik, alternatif, rock gibi geniş Deezer türlerinde etiket daha özel türü seçiyor.
- **Türkçe:** sanatçı ya da şarkı adında ğ, ı, ş, İ varsa, MusicBrainz'de "turkish" etiketi varsa ya da sanatçının ülkesi TR ise, bulunan tür Türkçe karşılığına çevriliyor (Hip Hop → Türkçe Rap, Pop → Türkçe Pop, Rock → Türkçe Rock, Folk - Akustik → Türk Halk - Sanat).
- Ad farkları (Siyasiyabend = "Siya siyabend", AGAB = "Aga B") ve "- Live Session" gibi ekler tolere ediliyor. Hiçbir yerde bulunamayan underground isimler Genel'e düşer.

**Üst bar menüsü:** Kendi uzantımız (`arctis-preset-menu`), tür takibi kurulunca EasyEffects Preset Selector'ın yerine geçiyor (Selector kapatılıyor). Simgenin yanında yüklü preset yazıyor (menüde noktalı olan; elle seçtiğinde o); kilitliyken simge kilit oluyor. Menü simgenin ortasından açılıyor. En çok dinlenen 5 tür (sabitlediklerin dahil) dinlenme sırasıyla var, altında her zaman **Genel**; çalan tür (alt tür dahil) bunlarda yoksa en altta geçici bir satır olarak görünüyor. En fazla 7 satır.

Menüde beş alt menü daha var:
- **Kaynak:** "Bu cihazdaki dinlemelerim" / "Spotify hesabım (tüm cihazlar)". Hesap seçiliyken giriş yoksa "Spotify hesabını bağla…" terminalde girişi açıyor. Eski girişte "son çalınanlar" izni yoksa "Spotify hesabını yeniden bağla…" çıkıyor.
- **Dönem:** son 1 gün / 1 hafta / 1 ay (varsayılan) / 3 ay / 6 ay / 1 yıl. En çok dinlenen 5 tür ve istatistik bu döneme göre hesaplanıyor (aşağıdaki tablo).
- **İstatistik:** Seçili kaynak ve dönemde ana türlerin yüzdesi; ilk satır verinin nereden geldiğini yazıyor. %1'in altındaki türler yazılmıyor.
- **Menüde sabitle:** 24 tür alfabetik. İşaretlediğin tür hemen menüye giriyor: 5 türün en az dinleneninin yerine geçiyor, ikinci sabitlediğin ondan önceki türün yerine, böyle sırayla. Menü yine dinlenme sırasında; hiç dinlemediğin sabit tür en altta. 5 tür sabitlersen menü tamamen sabit; 6.'yı işaretlersen en eski sabitlediğin çıkıyor. Seçerken menü kapanmıyor. Hem sabitlenip hem gizlenen tür menüde görünüyor.
- **Menüde gizle:** İşaretlenen türler en çok dinlenenler listesine girmiyor, yerine sıradaki geliyor. Çalınca yine kendi presetiyle çalıyor, istatistikte de görünüyor.

Uzantıyı X11'de yüklemek ya da yenilemek için Alt+F2 → `r` → Enter; Wayland'de oturumu kapatıp aç.

**Kilit:** Menüde ayrı bir kilit anahtarı yok; her satırın yanında kilit simgesi var.
- Bir satırın kilidine basınca o preset uygulanıyor ve kilitleniyor: türü ne olursa olsun sonraki bütün şarkılar o presette çalıyor. Aynı kilide tekrar basınca kilit açılıyor.
- Kilitliyken başka bir satıra tıklarsan kilit o satıra taşınıyor.
- Kulaklık yeniden bağlanıp Genel yüklense de, bir sonraki şarkıda kilitli presete geri dönülüyor.

**Elle seçim:** Kilit yokken menüden ya da kısayolla seçtiğin preset sadece o şarkı boyunca kalıyor. Sonraki şarkıda türün presetine otomatik dönülüyor.

**"En çok dinlenen" listesi** için iki kaynak modu var:

| Mod | Liste |
|---|---|
| Cihaz | Bu bilgisayarda seçili dönemde çalan şarkıların türü. Her şarkı saatlik geçmişe yazılıyor (`~/.local/state/spotify-genre-preset/gecmis.json`, 1 yıldan eskisi siliniyor). Dönemde hiç dinleme yoksa tüm zamanların sayımı kullanılıyor |
| Hesap | Telefon dahil tüm cihazlar. 1 ay, 6 ay ve 1 yıl için Spotify'ın kendi ~4 hafta / ~6 ay / ~1 yıl listesindeki en çok dinlenen 50 parça (6 saatte bir). Spotify 1 gün, 1 hafta ve 3 ay vermiyor: bunlar için servis "son çalınanlar"ı (son 50 parça) yarım saatte bir çekip geçmişi kendisi biriktiriyor. Geçmiş dönemi henüz kapsamıyorsa (ör. 3 ay için ilk 3 ay) dönemi kapsayan en kısa Spotify listesi kullanılıyor. Hata olursa yarım saat sonra tekrar deneniyor |

Mod kurulumda soruluyor, sonra menüdeki **Kaynak**'tan değişiyor. Ayarlar `~/.config/spotify-genre-preset/config.json`, durum `~/.local/state/spotify-genre-preset/state.json` dosyasında.

#### Spotify hesabını bağlama

Uygulamanın sahibinin Spotify Premium'u olmalı (Spotify'ın Şubat 2026 kuralı).

1. https://developer.spotify.com/dashboard adresinde **Create app** de. Redirect URI tam olarak `http://127.0.0.1:8888/callback` olmalı (localhost değil). "Web API"yi işaretle, **Save** de, Client ID'yi kopyala.
2. `spotify-genre-preset --login` komutunu çalıştır (Client ID'yi kendisi soruyor) ya da menüden "Spotify hesabını bağla…" de. Tarayıcıda Kabul et; "Spotify hesabı bağlandı" yazısını görünce `systemctl --user restart spotify-genre-preset` çalıştır. Sadece yenileme anahtarı `~/.config/spotify-genre-preset/spotify.json` dosyasına 600 izinle kaydediliyor; istenen yetkiler `user-top-read` (en çok dinlenenler) ve `user-read-recently-played` (son çalınanlar). Bu ikinci yetki sonradan eklendi; eski girişle 1 gün / 1 hafta / 3 ay Spotify listesine düşer, bir kez yeniden giriş yap (Client ID kayıtlıysa tekrar sorulmaz).
3. Diğer bilgisayarlarında aynı Client ID ile bir kez giriş yap. Dosyayı kopyalama: Spotify anahtarı yenileyince eski kopya geçersiz kalabilir.

Bir başkası ya kendi uygulamasını açar ya da sen onu uygulamanın User Management sekmesine (ad + Spotify e-postası) eklersin ve senin Client ID'nle giriş yapar. Uygulama başına en fazla 5 kişi.

- Sonuç albüm başına `~/.cache/spotify-genre-preset.json` dosyasına yazılıyor; aynı albüm bir daha sorulmuyor. `./install.sh` her çalıştığında bu önbellek sıfırlanıyor, çünkü tür eşlemesi değişmiş olabilir. Yanlış bulunan bir albümü düzeltmek için bu dosyadan o satırı sil (ya da dosyayı sil).
- Preset sadece tür değişince değişiyor, bildirim de o zaman çıkıyor. Elle seçtiğin preset o şarkı bitene kadar korunuyor; kilitliysen hiç değişmiyor.
- İnternet yoksa ya da servisler cevap vermezse preset değişmiyor; o albüm sonraki şarkıda tekrar deneniyor.
- Ne yaptığını izlemek için: `journalctl --user -u spotify-genre-preset -f` (her şarkı için "Sanatçı - Şarkı: Preset" satırı yazıyor).
- Geçici olarak kapatmak için: `systemctl --user stop spotify-genre-preset`. Tamamen kapatmak için `./install.sh`'ı tekrar çalıştırıp bu soruya `h` de.

Sınırlar:
- Tür şarkıya değil albüme (Deezer) ya da sanatçıya (MusicBrainz) göre bulunuyor. Rapçinin pop şarkısı da rap türüne gider.
- MusicBrainz'de sanatçı adla aranıyor. Deezer'de bulunamayan ve adı başka bir sanatçıyla aynı olan şarkılarda yanlış sanatçı seçilebiliyor. Türkçe rapte Deezer kapsamı iyi olduğu için bu nadiren gerekiyor.
- Sadece Spotify masaüstü uygulaması izleniyor; tarayıcıdaki Spotify ya da YouTube izlenmiyor.
- Test: servis birim testleri 61/61, giriş 7/7. Kilit, elle seçim ve kulaklık yeniden bağlanınca geri dönme gibi davranışlar sahte Spotify ile uçtan uca 3 senaryoda denendi. Menü, ekransız ayrı bir GNOME Shell 46'da sanal fareyle denendi. Spotify girişi ve hesaptan en çok dinlenen 50 parçanın çekilmesi gerçek hesapla denendi.
- Gerçek hesapla top 50 sınıflandırması: Türkçe Rap (Kayra, Lil Zey, Kamufle, Sürveyan, AGAB, Sansar Salvo...), Hip Hop (Gorillaz), Indie (Lana Del Rey, Tame Impala, Mac DeMarco), Pop (Metronomy), House (Daft Punk, The Blaze, French 79, Parcels, L'Impératrice), Bass Müziği (Fred again..), Reggae (Genjah), Türkçe Pop (M Lisa, Sezen Aksu), Techno (Charlotte de Witte), Metal (Metallica), Arabesk (Müslüm Gürses). Underground isimlerin bir kısmı (hacibab, memzst...) Genel'e düşüyor.

## Diğer cihazlar: Windows, macOS ve kulaklığın kendi EQ'su

Bağlantı düzeltmeleri ve EasyEffects zinciri (compressor, limiter, Calf) yalnız Linux'ta. Aynı eğriler (63 preset) üç yoldan başka cihazlarda kullanılabilir: Windows'ta Equalizer APO, macOS'ta CamillaDSP, her cihazda kulaklığın kendi EQ'su. EQ'yu tek yerde aç: kulaklığın EQ'su ile EasyEffects, Equalizer APO ya da CamillaDSP aynı anda açıksa yükseltmeler toplanır (örn. +3 dB'lik bir bas yükseltmesi iki kez = +6 dB), bas patlar.

### Kulaklığın kendi EQ'su (her cihazda geçerli)

- Nova 3P'nin içinde 10 bantlı parametrik EQ var. Ayar kulaklıkta saklanıyor, yani hangi cihaza bağlanırsa bağlansın aynı ses geliyor; o cihaza bir şey kurmak gerekmiyor (telefon, PS5, iş bilgisayarı).
- SteelSeries 2.4GHz ve Bluetooth için ayrı EQ profili tutuyor; güç tuşuyla mod değişince o modun profili kendiliğinden devreye giriyor.
- Bu EQ'yu SteelSeries GG (Windows/macOS, Engine sekmesi) ya da telefondaki Arctis Companion uygulaması ayarlıyor. Linux'tan da açık kaynak [HeadsetControl](https://github.com/Sapd/HeadsetControl) ile yazılabiliyor (Linux, Windows, macOS'ta çalışıyor).
- Kulaklık düzeltmesi tabanı da bu dosyalarda var; her dosya 7-9 bant, yani 10 sınırının altında.
- `files/headset/*.txt` dosyaları HeadsetControl'ün bant biçiminde: her bant `frekans,kazanç,Q,tip`, bantlar `;` ile ayrılıyor. GG'de ya da Companion'da elle girmek istersen değerler aynı.

Kurulum ve yazma (Ubuntu):

```bash
sudo add-apt-repository ppa:sapd/headsetcontrol
sudo apt update && sudo apt install headsetcontrol
# USB-C alıcıyı tak, kulaklığı 2.4GHz modunda aç
headsetcontrol --parametric-equalizer "$(cat "files/headset/Türkçe Rap.txt")"
# Düz (EQ'suz) hale döndürmek için:
headsetcontrol --parametric-equalizer reset
```

Windows'ta HeadsetControl'ün kurulum dosyası GitHub Releases sayfasında.

Sınırlar:
- HeadsetControl kulaklığa USB-C alıcı üzerinden ulaşıyor; Bluetooth üzerinden çalışmıyor. Kulaklık açık ve 2.4GHz modunda olmalı.
- Alıcı üzerinden yazılan EQ'nun sadece 2.4GHz profiline mi, Bluetooth profiline de mi gittiği henüz **test edilmedi**. Denemek için: yazdıktan sonra kulaklığı Bluetooth'a geçir, Linux'ta EasyEffects'i kapat (`easyeffects -q`) ve dinle. Bas belirgin şekilde artmışsa Bluetooth profili de değişmiş demektir; o zaman Linux'ta EasyEffects ile birlikte kullanma.
- Kulaklıkta compressor ve limiter yok, girişte ses kısma (preamp) da yok. Linux'taki zincirin sadece EQ kısmı taşınıyor; çok yüksek seste basta bozulma duyarsan kulaklıkta düz EQ'ya dön.
- 20 Hz altı desteklenmiyor; presetlerdeki en düşük filtre 20 Hz olduğu için bir şey kaybolmuyor.
- GG ya da Companion'da EQ'yu değiştirirsen kulaklıktaki ayar onunla değişir.

### Windows: Equalizer APO

> Ubuntu'da yazıldı, gerçek bir Windows cihazında **henüz denenmedi**.

Ne yapar: Linux'taki tür takibinin aynısı. Spotify'da çalan şarkı Windows'un medya oturumundan (SMTC) 2 saniyede bir okunuyor, türün preseti Equalizer APO'nun `config.txt` dosyasına yazılıyor, APO dosyayı kendisi yeniden yüklüyor. `config.txt`'nin ilk satırındaki yorum yüklü presetin adı.

Önce:
- [Equalizer APO](https://sourceforge.net/projects/equalizerapo/) kurulu olmalı. Configurator'da kulaklığın iki cihazı da (Bluetooth ve USB alıcı) işaretli olmalı ve bilgisayar yeniden başlatılmış olmalı.
- SteelSeries GG'de Sonar kapalı, Engine'deki EQ (Bluetooth ve 2.4GHz profili) düz olmalı; yoksa EQ'lar toplanır.

Kurulum: normal kullanıcı olarak (yönetici olarak **değil**):

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

- APO config klasörüne yazma izni için bir kez yönetici onayı istiyor.
- Python 3.11+ yoksa winget ile Python 3.12 kuruyor.
- Dosyaları `%LOCALAPPDATA%\spotify-genre-preset` klasörüne koyuyor (venv, presets, program); pystray, Pillow ve winrt paketlerini kuruyor.
- Eski `config.txt`'yi `config.txt.arctis-yedek` olarak yedekliyor.
- Spotify hesabını bağlamayı öneriyor.
- Başlangıç klasörüne "Arctis Preset" kısayolu ekleyip uygulamayı başlatıyor.

Kullanım: Tepside kulaklık simgesi var, kilitliyken turuncu. Üzerine gelince yüklü preset görünüyor, sağ tıklayınca menü açılıyor. Menü GNOME menüsüyle aynı:
- En çok dinlenen 5 tür, Genel ve çalan alt tür.
- Kilitle alt menüsü (GNOME'daki satır başı kilit düğmesinin yerine).
- Kaynak, Dönem, İstatistik, Menüde sabitle, Menüde gizle.
- Çıkış.

Günlük: `%LOCALAPPDATA%\spotify-genre-preset\gunluk.txt`. Denemek için (Spotify çalarken) `install.ps1`'in sonunda yazdırdığı `--dene` komutunu aynen kullan.

Kaldırma: `powershell -ExecutionPolicy Bypass -File uninstall.ps1`. Uygulamayı, kısayolu ve program dosyalarını siliyor, `config.txt`'yi geri koyuyor. Ayarlar, Spotify girişi ve dinleme geçmişi kalıyor; Equalizer APO ve Python kaldırılmıyor.

Sınırlar:
- Yalnız EQ ve preamp taşınıyor; Linux zincirindeki compressor, limiter, Bass Enhancer ve stereo genişlik yok.
- Spotify girişi her cihazda ayrı yapılıyor (aynı Client ID kullanılabilir).

Elle kullanım (otomatik sürümü istemiyorsan): `files/equalizer-apo/*.txt` dosyalarını `C:\Program Files\EqualizerAPO\config\` klasörüne kopyala, aynı klasördeki `config.txt`'nin içeriğini tek satır yap: `Include: Türkçe Rap.txt`. Preset değiştirmek için dosya adını değiştirip kaydet; Equalizer APO dosyayı kendisi yeniden yüklüyor.

### macOS

> Ubuntu'da yazıldı, gerçek bir Mac'te **henüz denenmedi**. İlk denemede iki şeye bak: kulaklıkta ses geliyor mu (mikrofon izni) ve kulaklık takılıp çıkarılınca çıkış doğru cihaza geçiyor mu.

Ses zinciri: sistem çıkışı BlackHole 2ch (sanal ses kartı) → CamillaDSP (EQ) → kulaklık. Kulaklık, adında "Arctis" geçen çıkış cihazı (Bluetooth ya da USB-C alıcı). Presetler `files/camilladsp/*.yml` (`make_presets.py` üretiyor, eğriler Equalizer APO'dakiyle aynı).

Önce:
- Homebrew kurulu olmalı.
- Kulaklığın kendi EQ'su (GG/Companion) düz olmalı; yoksa EQ'lar toplanır.

Kurulum: normal kullanıcı olarak (`sudo` ile **değil**):

```bash
bash install-mac.sh
```

- Homebrew ile `blackhole-2ch` (yönetici şifresi soruyor), `switchaudio-osx` ve `python@3.12` kuruyor.
- CamillaDSP v4.1.3'ü GitHub'dan indiriyor (Apple Silicon ya da Intel'e göre kendisi seçiyor).
- venv'e rumps 0.4.0 kuruyor.
- Dosyalar `~/Library/Application Support/spotify-genre-preset` klasörüne gidiyor.
- Spotify hesabını bağlamayı öneriyor.
- LaunchAgent ekliyor: oturum açılınca başlıyor; menüden Çıkış dersen yeniden başlatılmıyor, çökerse başlatılıyor.

Nasıl davranır:
- Kulaklık ses çıkışı olunca (bağlanınca macOS kendisi seçiyor) CamillaDSP başlıyor ve çıkış BlackHole'a alınıyor. Kulaklık gidince çıkış önceki cihaza dönüyor.
- Başka bir çıkışı kendin seçersen EQ devreden çıkıyor, uygulama karışmıyor.
- CamillaDSP kulaklığı açamazsa (önce 48 kHz, sonra 44.1 kHz dener) ses EQ'suz olarak kulaklıktan geliyor.
- Uygulama kapanırken çıkış BlackHole'dan geri alınıyor.
- Çalan şarkı Spotify'ın AppleScript'inden 2 saniyede bir okunuyor.
- Ses tuşları EQ öncesi seviyeyi (BlackHole) değiştiriyor; kulaklığın kendi tekerleği her zaman çalışıyor.

Menü çubuğu: 🎧 ve yüklü preset adı, kilitliyken 🔒. Menü Windows'takiyle aynı öğelerden oluşuyor.

İzinler: İlk açılışta macOS iki izin sorabilir: Python'un Spotify'ı denetlemesi ve mikrofon erişimi (CamillaDSP sesi BlackHole'dan kaydediyor). Mikrofon izni yoksa kulaklıkta ses **kesilir** ve hata mesajı çıkmaz. Çözüm: Sistem Ayarları > Gizlilik ve Güvenlik > Mikrofon'da Python'u aç. Listede yoksa:

```bash
tccutil reset Microphone
launchctl kickstart -k gui/$(id -u)/com.github.muhammetaliyoldar.spotify-genre-preset
```

Günlük: `~/Library/Application Support/spotify-genre-preset/gunluk.txt`. Denemek için (Spotify çalarken) `install-mac.sh`'nin sonunda yazdırdığı `--dene` komutunu kullan.

Kaldırma: `bash uninstall-mac.sh`. LaunchAgent'ı, CamillaDSP'yi, program dosyalarını ve presetleri siliyor. Ayarlar, Spotify girişi ve dinleme geçmişi kalıyor; Homebrew paketleri kaldırılmıyor. Çıkış hâlâ BlackHole'daysa uyarıyor.

Sınırlar: Yalnız EQ ve preamp taşınıyor (compressor, limiter, Bass Enhancer, stereo yok).

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

Windows (`install.ps1`) ve macOS (`install-mac.sh`) sürümleri henüz gerçek bir Windows ya da Mac cihazında denenmedi. Yalnızca Ubuntu'da, taklit edilen testlerle denendi.

## Klasör yapısı

```
install.sh                         # düzeltmeleri, presetleri ve uzantıları (istediğini seçerek) kurar
uninstall.sh                       # kurulanları kaldırır (presetler ve GNOME uzantıları kalır)
install.ps1                        # Windows: tür takibi + tepsi menüsü kurar
uninstall.ps1                      # Windows: tür takibini ve tepsi menüsünü kaldırır
install-mac.sh                     # macOS: BlackHole + CamillaDSP + menü çubuğu kurar
uninstall-mac.sh                   # macOS: bunları kaldırır
LICENSE                            # MIT
files/
├── bin/
│   ├── ee-preset                  # preset değiştirici (ee-preset <ad> | next)
│   └── spotify-genre-preset       # Spotify'daki türe göre preseti değiştiren servis (Linux ön yüzü: MPRIS + EasyEffects)
├── camilladsp/*.yml               # macOS CamillaDSP karşılıkları (make_presets.py üretir)
├── core/
│   ├── genre_core.py              # tür bulma, Spotify hesabı, geçmiş, dönem, istatistik, menü mantığı; platformdan bağımsız, Linux, Windows ve macOS ortak kullanıyor
│   └── tray_menu.py               # Windows ve macOS'un ortak menü ağacı ve şarkı takip döngüsü
├── easyeffects/
│   ├── make_presets.py            # presetleri (EasyEffects, Equalizer APO, CamillaDSP, kulaklık) üreten ve şema aralıklarını doğrulayan script
│   ├── output/*.json              # 63 preset
│   └── autostart/                 # EasyEffects'i oturum açılışında servis olarak başlatır
├── equalizer-apo/*.txt            # Windows Equalizer APO karşılıkları (make_presets.py üretir)
├── genres.json                    # 24 ana türün kataloğu ve alt türleri (subgenres: ad, ana tür, sanatçılar, keywords): ad, aile, MusicBrainz anahtar kelimeleri, Deezer eşlemesi, Türkçe karşılıklar, varsayılan 5, genel türler, eski adların ana türe eşlemesi (make_presets.py üretir)
├── gnome/
│   ├── dynamic-music-pill.ini     # Dynamic Music Pill ayarları (dconf)
│   └── arctis-preset-menu@muhammetaliyoldar/  # üst bar menüsü: preset, kilit, kaynak, dönem, istatistik, sabitle/gizle (tür takibiyle kurulur)
├── headset/*.txt                  # kulaklığın kendi EQ'su için HeadsetControl bantları (make_presets.py üretir)
├── mac/
│   └── spotify-genre-preset.py    # macOS ön yüzü (AppleScript + CamillaDSP + rumps menü çubuğu)
├── modprobe/                      # btusb.conf, rtw88.conf
├── networkmanager/                # wifi-powersave-off.conf
├── systemd/                       # arctis-autoconnect (otomatik bağlanma) ve spotify-genre-preset (tür takibi) kullanıcı servisleri
├── windows/
│   └── spotify-genre-preset.pyw   # Windows ön yüzü (SMTC + Equalizer APO + pystray tepsi menüsü)
└── wireplumber/                   # 51-arctis-a2dp-only (mikrofon kapalı) ve 51-arctis-sbc-only (mikrofon açık); her biri .lua (0.4) ve .conf (0.5+)
```

## Proje durumu

Repo 23 Ekim 2026'da oluşturuldu. Linux (Ubuntu) tarafı yukarıdaki test ortamında günlük kullanımda. 6 Kasım 2026'da Windows (Equalizer APO + tepsi menüsü) ve macOS (BlackHole + CamillaDSP + menü çubuğu) sürümleri eklendi. Üçü de aynı tür takibi çekirdeğini (`files/core/genre_core.py`) kullanıyor. Windows ve macOS sürümleri henüz gerçek cihazda denenmedi.

## Lisans

[MIT](LICENSE)
