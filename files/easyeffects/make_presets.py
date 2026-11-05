#!/usr/bin/env python3
"""EasyEffects 7.x presetlerini ve tür kataloğunu (../genres.json) üretir: Genel + 100 tür.

Kullanım: python3 make_presets.py [çıktı_klasörü] [--check]
  --check: her presetin EQ eğrisinin tepe noktalarını yazdırır (dosya yazmaz)
Aynı EQ eğrilerini ../equalizer-apo (Windows) ve ../headset (kulaklığın kendi EQ'su,
headsetcontrol) klasörlerine de yazar; compressor/limiter oralara taşınmaz. Katalogdan çıkmış
türlerin eski dosyaları bu iki klasörden ve varsayılan çıktı klasöründen (output) silinir;
başka bir çıktı klasörü verilirse orada silme yapılmaz.

Katalog (GENRES): her tür bir ailenin şablonundan (FAMILIES) ve küçük farklardan oluşur.
genres.json'u Spotify servisi ve üst bar menüsü okur: MusicBrainz etiketinde en uzun eşleşen
anahtar kelimenin türü seçilir, bu yüzden genel türler kısa ("rock"), özel türler uzun
("hard rock") kelime taşır; aynı kelime iki türde olamaz. Deezer tür numarası -> tür (deezer),
aile -> o ailenin Türkçe türü (turkish_variant) ve sabit modun 5 türü (defaults) de oradadır.

Zincir: Equalizer -> Compressor -> Limiter
- EQ: her presette aynı kulaklık düzeltmesi (nova()) + türün bantları (en fazla 2 Bell: nova
  kulaklıkta 7 bant tutar, kulaklık 10 bant alır). Filtreler "APO (DR)" modunda: Equalizer APO
  ve response_db ile birebir aynı eğri. 12 kHz üstüne yükseltme yok (SBC orayı bozuyor).
- Compressor üç tipten biri: kapalı (zaten sıkıştırılmış masterlar: techno, house, DnB, EDM, pop,
  rock, metal, indie...; ikinci bir compressor onları ezer. Klasik, caz ve akustikte dinamik
  korunur), hafif yapıştırma (1.5-1.8:1; R&B, soul, reggae, arabesk gibi dinamik kayıtlar) ya da
  punch (rap). Attack >= 30 ms (kick/808'in ilk vuruşu ezilmez), sidechain 100 Hz high-pass
  (808 tüm mix'i pompalamaz).
- Limiter: EasyEffects 7.x'te release en fazla 20 ms; 50 Hz'lik bir dalga da 20 ms
  sürdüğü için limiter devreye girdiğinde basta bozulma yapar. Bu yüzden EQ girişi
  eğrinin tepesi + 1 dB kadar kısılır, makeup yok: limiter sadece güvenlik ağıdır.
Dosya yazmadan önce katalog ve presetler doğrulanır (check_catalog); hata varsa hiçbir şey yazılmaz.
"""
import json
import math
import os
import sys


def band(type_, freq, gain=0.0, q=0.7, slope="x1"):
    return {"type": type_, "mode": "APO (DR)", "slope": slope, "solo": False,
            "mute": False, "gain": gain, "frequency": freq, "q": q, "width": 4.0}


def equalizer(bands, input_gain):
    ch = {f"band{i}": b for i, b in enumerate(bands)}
    return {"bypass": False, "num-bands": len(bands), "mode": "IIR",
            "input-gain": input_gain, "output-gain": 0.0, "split-channels": False,
            "balance": 0.0, "pitch-left": 0.0, "pitch-right": 0.0,
            "left": ch, "right": json.loads(json.dumps(ch))}


def compressor(threshold=-18.0, ratio=1.5, attack=30.0, release=300.0, knee=-6.0, bypass=False):
    return {"bypass": bypass, "input-gain": 0.0, "output-gain": 0.0,
            "dry": -100.0, "wet": 0.0, "mode": "Downward",
            "attack": attack, "release": release, "release-threshold": -100.0,
            "threshold": threshold, "ratio": ratio, "knee": knee, "makeup": 0.0,
            "boost-amount": 6.0, "boost-threshold": -72.0, "stereo-split": False,
            "sidechain": {"type": "Feed-forward", "mode": "RMS", "source": "Middle",
                          "stereo-split-source": "Left/Right", "preamp": 0.0,
                          "reactivity": 10.0, "lookahead": 0.0},
            "hpf-mode": "12 dB/oct", "hpf-frequency": 100.0,
            "lpf-mode": "off", "lpf-frequency": 20000.0}


def limiter(input_gain=0.0):
    return {"bypass": False, "input-gain": input_gain, "output-gain": 0.0,
            "mode": "Herm Thin", "oversampling": "None", "dithering": "None",
            "lookahead": 5.0, "attack": 5.0, "release": 20.0, "threshold": -1.0,
            "gain-boost": False, "sidechain-preamp": 0.0, "stereo-link": 100.0,
            "alr": False, "alr-attack": 5.0, "alr-release": 50.0, "alr-knee": 0.0,
            "external-sidechain": False}


OFF = compressor(bypass=True)
GLUE = compressor(threshold=-18.0, ratio=1.5)  # hafif yapıştırma
SLOW = compressor(threshold=-18.0, ratio=1.8, release=400.0, knee=-9.0)  # uzun setlerde pompalamaz
PUNCH = compressor(threshold=-16.0, ratio=1.8, release=200.0)  # vuruşlar arasında toparlanır


def preset(bands, comp):
    """input-gain aşağıda, PRESETS tanımlandıktan sonra eğrinin tepesinden hesaplanır."""
    return {"output": {"blocklist": [],
                       "plugins_order": ["equalizer#0", "compressor#0", "limiter#0"],
                       "equalizer#0": equalizer(bands, 0.0),
                       "compressor#0": comp, "limiter#0": limiter()}}


def nova(ls=2.5, mud=-4.0, mid=2.0, presence=4.0, air=-3.5, hp=20.0):
    """Kulaklık düzeltmesi. Nova 3P'nin yayımlanmış ölçümü yok; kardeş modeller Nova 3 ve
    Nova 5'in (AutoEq/rtings) Harman OE 2018'e göre farkından yumuşatıldı: 100-250 Hz
    tümseği kesilir, 4-5 kHz çukuru doldurulur, 8-10 kHz sertliği alınır. SBC 12 kHz
    üstünü zaten bozduğu için oraya hiç yükseltme yok."""
    return [band("Hi-pass", hp, q=0.7, slope="x2"), band("Lo-shelf", 105.0, ls, 0.7),
            band("Bell", 160.0, mud, 0.7), band("Bell", 500.0, mid, 1.0),
            band("Bell", 4300.0, presence, 2.5), band("Bell", 9000.0, air, 1.2)]


# Aile şablonu: nova() ayarları, eklenen Bell'ler (Hz, dB, Q), compressor.
# "v1" yazanlar önceki sürümün aile presetleri; o eğriler aynen korunur.
FAMILIES = {
    # v1 Rap: 808 sub'ı göğüste, sözler önde, Türkçe "s/ş" sesleri yumuşak; çamur daha çok kesilir
    "rap": (dict(mud=-4.5, air=-4.5, hp=22.0), [(50, 3.0, 0.9)], PUNCH),
    # v1 Tekno - Rave: kick/rumble ve synth atağı; master zaten -7..-9 LUFS
    "techno": (dict(ls=2.0, mid=1.0, presence=2.5, air=-4.0, hp=25.0), [(55, 2.0, 1.0)], OFF),
    # v1 House - Disco: kick gövdesi ve bas yürüyüşü; sidechain pompalaması müziğin parçası
    "house": (dict(mud=-3.0), [(90, 2.0, 1.0)], OFF),
    # v1 Drum & Bass: reese/sub 45 Hz, breakbeat atağı; en yüksek masterlar (-6.5 LUFS)
    "bass": (dict(ls=1.5, presence=3.0), [(45, 2.5, 1.0)], OFF),
    # synth bas ve pad'ler, orta tempo: sıcak 60 Hz, çamur ve sertlik alınır
    "electronic": (dict(mud=-3.5, air=-3.5), [(60, 2.0, 0.9)], OFF),
    # drone ve pad'ler: derin ama hafif sub, uzun dinlemede yormayan orta-tiz
    "ambient": (dict(ls=2.0, presence=2.5, air=-3.0), [(45, 1.5, 0.8)], OFF),
    # v1 Pop: masterlar ~6 DR; sadece hafif sub ve yumuşak sibilans
    "pop": (dict(air=-4.0), [(50, 1.5, 0.9)], OFF),
    # K-pop/J-pop masterları pop'tan da parlak: 4 kHz dolgusu azaltılır
    "asian": (dict(presence=3.0, air=-4.0), [(50, 2.0, 0.9)], OFF),
    # v1 Indie: sıcak bas, vokal ve synth dokusu; kaynak çoğu zaman zaten ezilmiş
    "indie": (dict(mud=-3.0, presence=3.0, air=-4.0), [(80, 1.5, 0.9)], OFF),
    # bant kaydı sıcaklığı: bas gitar 100 Hz'te önde, fuzz ve tape tizleri yumuşak
    "psych": (dict(mud=-2.5, mid=2.5, presence=3.0, air=-4.0), [(100, 2.0, 0.9)], OFF),
    # v1 Rock: kick/bas gövdesi 85 Hz, gitar ısırığı 2 kHz
    "rock": (dict(mud=-3.5, presence=3.5, air=-4.0), [(85, 1.5, 1.0), (2000, 1.0, 1.0)], OFF),
    # distorsiyonlu gitarın 500 Hz kutu sesi ve 6-9 kHz cızırtısı alınır; kick 80 Hz
    "metal": (dict(mud=-3.5, mid=1.0, presence=3.0, air=-5.0), [(80, 2.0, 1.0)], OFF),
    # v1 R&B: yumuşak sub ve vokal varlığı; hafif yapıştırma
    "rnb": (dict(mud=-3.0, presence=3.0), [(60, 2.0, 0.8)], GLUE),
    # kontrbas sıcaklığı korunur (çamur az kesilir), zil parıltısı açık; dinamiğe dokunulmaz
    "jazz": (dict(ls=2.0, mud=-2.5, presence=3.0, air=-2.5), [(80, 1.0, 0.9)], OFF),
    # doğal tını ve tam dinamik; keman/soprano sertliğine karşı 4 kHz dolgusu az
    "classical": (dict(ls=2.0, mud=-3.0, presence=3.0, air=-2.0), [], OFF),
    # v1 Akustik: doğal tını, daha az bas, zil parıltısı korunur
    "acoustic": (dict(ls=2.0, mud=-3.0, air=-2.5), [], OFF),
    # akustik gitar gövdesi 250 Hz; keman/banjo parlaklığı yumuşak
    "folk": (dict(ls=2.0, mud=-3.0, presence=3.5, air=-3.0), [(250, 1.0, 1.0)], OFF),
    # önde vokal, akustik/elektro gitar; kick/bas gövdesi 85 Hz
    "country": (dict(ls=2.0, mud=-3.0, presence=3.5, air=-3.0), [(85, 1.5, 1.0)], OFF),
    # orta frekanslı gitar ve armonika, sıcak bas; eski kayıtlar: hafif yapıştırma
    "blues": (dict(ls=2.5, mud=-2.5, mid=2.5, presence=3.0, air=-3.0), [(90, 1.5, 1.0)], GLUE),
    # dembow kick + 808, 55 Hz; masterlar pop kadar yüksek
    "latin": (dict(air=-4.0), [(55, 2.5, 0.9)], OFF),
    # mix'in merkezi bas gitar (60-100 Hz), skank gitar ve vokal; kayıtlar dinamik
    "reggae": (dict(mud=-3.0, presence=3.0, air=-3.5), [(70, 2.5, 0.9)], GLUE),
    # senkoplu kick/bas 60 Hz, parlak shaker'lar yumuşatılır
    "african": (dict(mud=-3.5, air=-4.0), [(60, 2.0, 0.9)], OFF),
    # darbuka düm'ü 90 Hz, ud/vokal gövdesi 500 Hz, kanun/yaylı parlaklığı yumuşak
    "arabic": (dict(mud=-3.0, mid=2.5, presence=3.0, air=-3.5), [(90, 1.5, 1.0)], GLUE),
    # Türk sanat: fasıl heyeti ve vokal; eski kayıtlarda ince bas biraz ısıtılır
    "turkish": (dict(ls=2.5, mud=-2.5, mid=2.5, presence=3.0, air=-3.0), [], GLUE),
}

# (ad, aile, MusicBrainz anahtar kelimeleri, aileden farklar: nova() ayarları, "bells", "comp")
GENRES = [
    ("Türkçe Rap", "rap", ["turkish hip hop", "turkish rap", "turkish trap", "türkçe rap"], {}),
    ("Hip Hop", "rap", ["hip hop", "hip-hop", "hiphop", "rap", "g-funk"], {}),
    ("Trap", "rap", ["trap"], {"hp": 20.0, "bells": [(45, 3.0, 0.9)]}),  # uzun 808 daha derine iner
    # kayan 808'in harmonikleri 150 Hz'i doldurur
    ("Drill", "rap", ["drill"], {"mud": -5.0, "bells": [(48, 3.0, 0.8)]}),
    # örnek kick'in gövdesi 70 Hz (sub değil); plak örnekleri zaten donuk, tiz az kesilir
    ("Boom Bap", "rap", ["boom bap", "boom-bap", "east coast hip hop", "golden age hip hop", "jazz rap"],
     {"mud": -3.5, "air": -3.5, "bells": [(70, 2.5, 1.0)]}),
    # kırpılmış master (compressor sadece pompalar), sert cowbell
    ("Phonk", "rap", ["phonk", "memphis rap"], {"presence": 3.0, "bells": [(45, 3.0, 0.9)], "comp": OFF}),
    # alçak geçirgenli örnekler, yumuşak kick: sıcaklık ve tiz korunur
    ("Lo-fi Hip Hop", "rap", ["lo-fi hip hop", "lofi", "chillhop"],
     {"ls": 3.0, "mud": -3.0, "air": -2.5, "bells": [(60, 2.0, 0.8)], "comp": GLUE}),
    ("Grime", "rap", ["grime"], {"bells": [(55, 3.0, 1.0)]}),  # 140 BPM kare dalga bas
    ("Pop Rap", "rap", ["pop rap", "melodic rap"], {"air": -4.0, "bells": [(50, 2.5, 0.9)]}),

    ("Techno", "techno", ["techno", "rave"], {}),
    # distorsiyonlu kick'in 150-200 Hz'i ve sert tizler alınır
    ("Hard Techno", "techno", ["hard techno", "industrial techno", "schranz"],
     {"mud": -4.5, "air": -4.5, "bells": [(55, 2.5, 1.0)]}),
    # derin sub, pad ve arpejler: daha açık orta-tiz
    ("Melodic Techno", "techno", ["melodic techno", "melodic house"],
     {"presence": 3.0, "air": -3.0, "bells": [(50, 2.0, 0.9)]}),
    # supersaw lead'ler 3-8 kHz, kick 60 Hz
    ("Trance", "techno", ["trance"], {"mid": 1.5, "presence": 3.0, "air": -3.5, "bells": [(60, 2.0, 1.0)]}),
    # kick 55 Hz + hemen ardından yuvarlanan bas 100 Hz; çok sayıda tiz efekt
    ("Psytrance", "techno", ["psytrance", "psy-trance", "psychedelic trance", "goa trance"],
     {"mud": -3.5, "air": -4.5, "bells": [(55, 2.0, 1.0), (100, 1.5, 1.2)]}),
    # reverse-bass kick: 60 Hz + 150-300 Hz gövde; screech lead'ler sert
    ("Hardstyle", "techno", ["hardstyle", "hard dance", "rawstyle", "gabber"],
     {"mud": -3.0, "mid": 1.5, "air": -4.5, "bells": [(60, 2.5, 1.0)]}),

    ("House", "house", ["house", "lo-fi house", "latin house"], {}),
    # v1 Deep House: derin, sıcak sub ve yumuşak tizler; hafif yapıştırma, uzun setlerde yormaz
    ("Deep House", "house", ["deep house", "organic house"],
     {"air": -2.5, "bells": [(60, 2.0, 0.8)], "comp": SLOW}),
    ("Tech House", "house", ["tech house"], {"air": -4.0, "bells": [(60, 2.0, 0.9)]}),  # yuvarlanan sub bas
    # konga/perküsyon gövdesi 250 Hz, organik tizler
    ("Afro House", "house", ["afro house"],
     {"mud": -2.5, "air": -3.0, "bells": [(55, 2.0, 0.9), (250, 1.0, 1.0)]}),
    ("Progressive House", "house", ["progressive house"], {"presence": 3.5, "bells": [(55, 2.0, 0.9)]}),
    # filtrelenmiş disco örnekleri orta frekansta yaşar
    ("French House", "house", ["french house", "french touch", "filter house"],
     {"mid": 2.5, "bells": [(90, 2.0, 1.0), (1000, 1.0, 1.0)]}),
    # melodik disco bası 100 Hz, canlı gitar ve yaylılar
    ("Nu-Disco", "house", ["nu-disco", "nu disco", "indie dance", "disco house"],
     {"mud": -2.5, "air": -3.0, "bells": [(100, 1.5, 1.0)]}),
    # 70'lerin dinamik kayıtları: hafif yapıştırma
    ("Disco", "house", ["disco"], {"mud": -2.5, "air": -3.0, "bells": [(90, 1.5, 1.0)], "comp": GLUE}),

    ("Drum & Bass", "bass", ["drum and bass", "drum & bass", "drum n bass", "dnb", "liquid funk", "neurofunk"],
     {}),
    # kesik amen breakleri: snare gövdesi ve çıtırtısı önde
    ("Jungle", "bass", ["jungle"], {"mid": 2.5, "presence": 3.5, "bells": [(50, 2.5, 1.0)]}),
    # wobble/growl 200 Hz-2 kHz, çok sert tizler
    ("Dubstep", "bass", ["dubstep", "brostep"], {"mud": -3.5, "mid": 1.5, "air": -4.5, "bells": [(50, 2.5, 1.0)]}),
    # 2-step davullar ve vokal kesitleri
    ("UK Garage", "bass", ["uk garage", "2-step", "speed garage", "bassline"],
     {"presence": 3.5, "bells": [(55, 2.0, 1.0)]}),
    ("Future Bass", "bass", ["future bass"], {"air": -4.5, "bells": [(50, 2.0, 0.9)]}),  # parlak supersaw akorlar

    ("Elektronik", "electronic", ["electronic", "electronica", "electro", "idm"], {}),
    # big room kick 55 Hz, -5 LUFS masterlar
    ("EDM", "electronic", ["edm", "big room", "electro house", "electronic dance"],
     {"ls": 2.0, "presence": 3.0, "air": -4.5, "bells": [(55, 2.5, 1.0)]}),
    # analog synth bas 80 Hz, gated snare, parlak arpejler
    ("Synthwave", "electronic", ["synthwave", "retrowave", "outrun", "vaporwave", "darksynth"],
     {"mud": -3.0, "mid": 2.5, "air": -3.0, "bells": [(80, 1.5, 0.9)]}),

    ("Ambient", "ambient", ["ambient", "new age", "meditation"], {}),
    ("Downtempo", "ambient", ["downtempo", "chill", "lounge"],
     {"ls": 2.5, "mud": -3.0, "presence": 3.0, "bells": [(60, 2.0, 0.8)], "comp": SLOW}),
    # ağır breakbeat ve derin sub, 90'ların dinamik kayıtları
    ("Trip Hop", "ambient", ["trip hop", "trip-hop"],
     {"ls": 2.5, "mud": -3.5, "presence": 3.0, "bells": [(50, 2.5, 0.8)], "comp": GLUE}),

    ("Pop", "pop", ["pop"], {}),
    # vokal gövdesi önde, parlak Türkçe sibilans yumuşak
    ("Türkçe Pop", "pop", ["turkish pop", "türkçe pop"], {"mid": 2.5, "presence": 3.5, "air": -4.5}),
    ("Dance Pop", "pop", ["dance"], {"ls": 2.0, "bells": [(55, 2.0, 1.0)]}),  # dört vuruşlu kick
    ("Synthpop", "pop", ["synthpop", "synth-pop", "synth pop", "techno-pop", "new wave"],
     {"mud": -3.0, "mid": 2.5, "bells": [(80, 1.5, 0.9)]}),  # synth bas 80 Hz
    ("Electropop", "pop", ["electropop", "electro-pop", "electro pop"], {"mud": -3.5, "bells": [(55, 2.0, 0.9)]}),
    # aşırı yüksek, distorsiyonlu master ve tiz vokaller
    ("Hyperpop", "pop", ["hyperpop", "digicore"], {"presence": 3.0, "air": -5.0, "bells": [(50, 2.0, 0.9)]}),

    ("K-pop", "asian", ["k-pop", "kpop", "korean pop"], {}),
    # J-rock etkisi: kick/bas gövdesi, daha az sub
    ("J-pop", "asian", ["j-pop", "jpop", "japanese pop", "anime", "city pop"],
     {"ls": 2.0, "bells": [(85, 1.5, 1.0)]}),
    ("Bollywood", "asian", ["bollywood", "filmi", "bhangra"],
     {"mid": 2.5, "bells": [(70, 2.0, 0.9)]}),  # dhol ve önde vokal

    ("Indie", "indie", ["indie", "lo-fi"], {}),
    ("Türkçe Indie", "indie", ["turkish indie", "turkish alternative"], {"mid": 2.5, "presence": 3.5}),
    ("Indie Rock", "indie", ["indie rock"], {"presence": 3.5, "bells": [(80, 1.5, 0.9), (2000, 1.0, 1.0)]}),
    ("Indie Pop", "indie", ["indie pop", "bedroom pop", "jangle pop"],
     {"ls": 2.0, "presence": 3.5, "air": -3.5, "bells": [(70, 1.0, 0.9)]}),
    # yankıya gömülü vokal ve gitar: parıltı korunur, sertleştirilmez
    ("Dream Pop", "indie", ["dream pop", "chillwave", "baroque pop"],
     {"mud": -2.5, "presence": 2.5, "air": -3.0, "bells": [(70, 1.5, 0.8)]}),
    # fuzz gitar duvarı: kutu sesi ve cızırtı alınır
    ("Shoegaze", "indie", ["shoegaze", "nu gaze"], {"mid": 1.0, "presence": 2.5, "air": -4.5}),
    ("Indie Folk", "indie", ["indie folk", "chamber folk"],
     {"ls": 2.0, "air": -3.0, "bells": [(250, 1.0, 1.0)]}),  # akustik gitar gövdesi

    ("Psikedelik", "psych", ["psych"], {}),
    # 70'lerin ince baslı kayıtları ısıtılır; bağlama/org ortası zaten güçlü
    ("Anadolu Rock", "psych", ["anatolian rock", "anadolu rock", "anatolian psych"],
     {"ls": 3.0, "mid": 2.0, "bells": [(90, 1.5, 0.9)], "comp": GLUE}),

    ("Rock", "rock", ["rock"], {}),
    ("Türkçe Rock", "rock", ["turkish rock", "türkçe rock"], {"mid": 2.5, "presence": 3.0}),  # vokal önde
    ("Hard Rock", "rock", ["hard rock"], {"mud": -4.0, "bells": [(85, 2.0, 1.0), (2500, 1.0, 1.0)]}),
    # 60-70'lerin dinamik, ince baslı kayıtları
    ("Klasik Rock", "rock", ["classic rock", "rock and roll", "rock & roll", "rock opera"],
     {"ls": 3.0, "mud": -3.0, "air": -3.0, "bells": [(85, 1.5, 1.0)], "comp": GLUE}),
    ("Alternatif Rock", "rock", ["alternative rock", "alt-rock", "britpop"],
     {"bells": [(85, 1.5, 1.0), (1500, 1.0, 1.0)]}),
    # ince bas, orta frekanslı gitar, sert ziller
    ("Punk", "rock", ["punk", "punk rock"],
     {"mud": -3.0, "air": -4.5, "bells": [(100, 1.5, 1.0), (1500, 1.0, 1.0)]}),
    # kalın, alçak akortlu gitarlar: alt-orta korunur
    ("Grunge", "rock", ["grunge"], {"mud": -2.5, "mid": 1.5, "presence": 3.0,
                                    "bells": [(80, 1.5, 1.0), (2000, 1.0, 1.0)]}),
    # melodik bas gitar 120 Hz, chorus'lu gitar
    ("Post-Punk", "rock", ["post-punk", "post punk", "dance-punk", "darkwave", "coldwave"],
     {"mud": -2.5, "presence": 3.0, "bells": [(120, 1.5, 1.0), (2500, 1.0, 1.2)]}),
    ("Progresif Rock", "rock", ["prog", "progressive rock", "prog rock"],
     {"mud": -3.0, "air": -3.0, "bells": [(85, 1.5, 1.0)]}),  # dinamik, geniş

    ("Metal", "metal", ["metal"], {}),
    # 80'lerin orta frekanslı gitarları, daha az alt
    ("Heavy Metal", "metal", ["heavy metal", "nwobhm"],
     {"ls": 3.0, "mid": 2.0, "presence": 3.5, "air": -4.5, "bells": [(90, 1.5, 1.0)]}),
    # oyulmuş orta, double kick tıkırtısı 2.5 kHz
    ("Thrash Metal", "metal", ["thrash"], {"mid": 0.5, "bells": [(70, 2.0, 1.0), (2500, 1.0, 1.2)]}),
    # alçak akort gitarların 300 Hz çamuru alınır
    ("Death Metal", "metal", ["death metal", "deathcore"],
     {"mud": -4.5, "mid": 0.5, "bells": [(60, 2.0, 1.0), (300, -1.0, 1.0)]}),
    ("Metalcore", "metal", ["metalcore", "post-hardcore"], {"bells": [(50, 2.5, 0.9)]}),  # breakdown sub'ları
    ("Nu Metal", "metal", ["nu metal", "nu-metal", "rap metal"],
     {"mud": -3.0, "mid": 1.5, "bells": [(60, 2.5, 0.9)]}),  # hip hop davulu, alçak akort groove

    ("R&B", "rnb", ["r&b", "rnb", "rhythm and blues"], {}),
    # karanlık, havadar; 808 sub
    ("Alternatif R&B", "rnb", ["alternative r&b", "indie r&b", "pbr&b", "trap soul"],
     {"air": -4.0, "bells": [(50, 2.5, 0.8)]}),
    # canlı bas ve Rhodes: sıcak alt-orta
    ("Neo Soul", "rnb", ["neo soul", "neo-soul"],
     {"ls": 3.0, "mud": -2.5, "air": -3.0, "bells": [(80, 1.5, 0.9)]}),
    # 60-70'lerin orta ağırlıklı kayıtları, nefesliler
    ("Soul", "rnb", ["soul", "motown"],
     {"ls": 3.0, "mud": -2.5, "mid": 2.5, "air": -3.0, "bells": [(90, 1.5, 1.0)]}),
    # slap bas 90 Hz, "chicken scratch" gitar 2 kHz
    ("Funk", "rnb", ["funk", "funk rock", "jazz-funk", "jazz funk"],
     {"mud": -2.5, "bells": [(90, 2.0, 1.0), (2000, 1.0, 1.2)]}),
    # koro ve Hammond orgu: geniş orta
    ("Gospel", "rnb", ["gospel", "worship"],
     {"mid": 2.5, "presence": 3.5, "air": -3.0, "bells": [(70, 1.5, 0.9)]}),

    ("Caz", "jazz", ["jazz", "bebop", "swing", "soul jazz"], {}),
    # cilalı prodüksiyon, saksafon gövdesi; radyo usulü hafif yapıştırma
    ("Smooth Jazz", "jazz", ["smooth jazz"], {"ls": 2.5, "mid": 2.5, "air": -3.0, "bells": [(70, 1.5, 0.9)],
                                             "comp": GLUE}),
    # naylon telli gitar ve fısıltı vokal
    ("Bossa Nova", "jazz", ["bossa nova", "mpb", "samba"], {"mud": -3.0, "mid": 2.5, "bells": []}),

    ("Klasik", "classical", ["classical", "orchestral"], {}),
    ("Opera", "classical", ["opera"], {"mid": 2.5, "presence": 2.5}),  # soprano 3-5 kHz'te sertleşmesin
    # yakın mikrofonlu piyano ve yaylılar
    ("Neoklasik", "classical", ["neoclassical", "neo-classical", "modern classical", "contemporary classical"],
     {"ls": 2.5, "mud": -2.5, "presence": 2.5, "air": -2.5}),
    # modern film müziğinin 30-50 Hz "braam"ları
    ("Film Müziği", "classical", ["soundtrack", "film score", "video game"],
     {"ls": 2.5, "bells": [(40, 2.0, 0.8)]}),

    ("Akustik", "acoustic", ["acoustic", "singer-songwriter", "singer/songwriter", "singer songwriter"], {}),

    ("Folk", "folk", ["folk", "folk rock"], {}),
    # bağlama ve zurna 2-5 kHz'te zaten keskin; TRT kayıtlarının ince altı ısıtılır
    ("Türk Halk", "folk", ["turkish folk", "türk halk", "türkü", "halk müziği", "uzun hava"],
     {"ls": 2.5, "presence": 3.0, "air": -3.5, "bells": [(90, 1.0, 1.0)]}),

    ("Country", "country", ["country", "bluegrass", "americana"], {}),

    ("Blues", "blues", ["blues", "country blues"], {}),

    ("Reggaeton", "latin", ["reggaeton", "reggaetón", "latin trap", "dembow", "urbano"], {}),
    ("Latin Pop", "latin", ["latin", "sertanejo"], {"ls": 2.5, "mid": 2.5, "bells": [(60, 1.5, 0.9)]}),
    # nefesliler ve konga/timbal; eski dinamik kayıtlar
    ("Salsa", "latin", ["salsa", "latin jazz", "timba", "son cubano"],
     {"mud": -2.5, "presence": 3.0, "air": -3.0, "bells": [(90, 1.5, 1.0)], "comp": GLUE}),
    # requinto gitar 2-5 kHz, güira tizleri sert
    ("Bachata", "latin", ["bachata"], {"presence": 3.0, "air": -4.5, "bells": [(80, 1.5, 1.0)]}),
    # akordeon ortası, güiro tizleri
    ("Cumbia", "latin", ["cumbia", "vallenato"], {"mid": 2.5, "air": -4.5, "bells": [(80, 1.5, 1.0)]}),
    # tuba/tololoche bası 70 Hz, bando nefeslileri
    ("Meksika Müziği", "latin", ["regional mexican", "corrido", "banda", "mariachi", "norteño", "ranchera"],
     {"mud": -3.0, "mid": 2.5, "bells": [(70, 2.0, 0.9)]}),
    # tamborzão 808'i, aşırı yüksek masterlar
    ("Funk Carioca", "latin", ["funk carioca", "baile funk", "brazilian funk", "funk brasileiro"],
     {"hp": 22.0, "presence": 3.0, "air": -4.5, "bells": [(50, 3.0, 0.9)]}),

    ("Reggae", "reggae", ["reggae", "dub", "ska", "rocksteady"], {}),
    # dijital riddim, 808'e yakın kick; yüksek masterlar
    ("Dancehall", "reggae", ["dancehall", "ragga"], {"air": -4.0, "bells": [(55, 2.5, 0.9)], "comp": OFF}),

    ("Afrobeats", "african", ["afrobeat", "afropop", "afro pop", "afro-pop", "naija", "highlife"], {}),
    ("Amapiano", "african", ["amapiano", "gqom", "kwaito"], {"ls": 2.0, "bells": [(50, 3.0, 0.8)]}),  # log drum

    ("Arap Müziği", "arabic", ["arab", "khaleeji", "raï", "chaabi"], {}),
    # kaset dönemi yaylıları sert, bas ince
    ("Arabesk", "arabic", ["arabesk", "arabesque", "damar"],
     {"ls": 3.0, "presence": 2.5, "air": -4.0, "bells": [(90, 1.5, 1.0)]}),
    # 90'ların synth/davul makinesi prodüksiyonu
    ("Fantezi", "arabic", ["fantezi"], {"ls": 2.5, "air": -4.0, "bells": [(70, 1.5, 0.9)]}),

    ("Türk Sanat", "turkish", ["turkish classical", "türk sanat", "sanat müziği", "fasıl"], {}),
]

TURKISH = {"Türkçe Rap", "Türkçe Pop", "Türkçe Rock", "Türkçe Indie", "Anadolu Rock", "Arabesk", "Fantezi",
           "Türk Halk", "Türk Sanat"}
# Sanatçı/şarkı Türkçeyse ailenin bu türü seçilir
TURKISH_VARIANT = {"rap": "Türkçe Rap", "pop": "Türkçe Pop", "rock": "Türkçe Rock",
                   "indie": "Türkçe Indie", "psych": "Anadolu Rock", "folk": "Türk Halk", "arabic": "Arabesk"}
DEFAULTS = ["Türkçe Rap", "Psikedelik", "Elektronik", "Türkçe Rock", "R&B"]
# Deezer tür numarası -> tür (api.deezer.com/genre ve /genre/<id>; albümler ana ve alt türleri birlikte verir)
DEEZER = {
    132: "Pop", 116: "Hip Hop", 152: "Rock", 113: "EDM", 165: "R&B", 85: "Indie", 106: "Elektronik",
    466: "Folk", 144: "Reggae", 129: "Caz", 98: "Klasik", 173: "Film Müziği", 464: "Metal", 169: "Soul",
    2: "Afrobeats", 12: "Arap Müziği", 16: "K-pop", 153: "Blues", 75: "Latin Pop", 81: "Bollywood",
    95: "Pop", 197: "Latin Pop", 84: "Country",
    3: "Afrobeats", 13: "Arap Müziği", 14: "Arap Müziği", 15: "Arap Müziği", 22: "J-pop", 23: "K-pop",
    49: "Türk Halk", 58: "Meksika Müziği", 65: "Meksika Müziği", 67: "Salsa", 71: "Cumbia",
    76: "Latin Pop", 78: "Bossa Nova", 79: "Latin Pop", 80: "Latin Pop", 86: "Indie Pop", 87: "Indie Rock",
    99: "Klasik", 100: "Klasik", 101: "Klasik", 102: "Neoklasik", 103: "Opera", 104: "Klasik", 105: "Klasik",
    107: "Downtempo", 108: "Dubstep", 110: "Electropop", 111: "House", 112: "Afro House", 114: "EDM",
    115: "Trance", 121: "Hip Hop", 122: "Reggaeton", 123: "Hip Hop", 124: "Hip Hop", 125: "Amapiano",
    128: "Hip Hop", 130: "Caz", 131: "Caz", 133: "Indie Pop", 134: "Pop", 137: "Türkçe Pop", 138: "Latin Pop",
    143: "Pop", 145: "Dancehall", 146: "Reggae", 147: "Reggae", 154: "Indie Rock", 155: "Hard Rock",
    156: "Klasik Rock", 159: "Türkçe Rock", 160: "Rock", 166: "R&B", 167: "Neo Soul", 168: "Disco",
    170: "Soul", 171: "Soul", 174: "Film Müziği", 175: "Film Müziği", 176: "Film Müziği",
    177: "Film Müziği", 178: "Bollywood", 179: "Film Müziği", 180: "Blues", 181: "Blues", 182: "Blues",
    183: "Blues", 184: "Blues", 185: "Blues", 186: "Gospel", 187: "Gospel", 188: "Gospel", 192: "Country",
    193: "Country", 194: "Country", 195: "Country", 196: "Country", 200: "Trap", 202: "Boom Bap", 204: "Hip Hop",
    206: "Boom Bap",
    208: "Boom Bap", 472: "Funk Carioca", 498: "Cumbia", 500: "Cumbia", 504: "Salsa", 510: "Meksika Müziği",
    512: "Meksika Müziği", 514: "Meksika Müziği", 516: "Latin Pop", 520: "Grime", 522: "Akustik",
    530: "Bachata", 532: "Folk", 534: "Latin Pop", 536: "Soul", 537: "Downtempo",
}


def genre_preset(family, diff):
    """Aile şablonu + türün farkları; "bells" ve "comp" verilirse ailedekinin yerine geçer."""
    kw, bells, comp = FAMILIES[family]
    kw = {**kw, **{k: v for k, v in diff.items() if k not in ("bells", "comp")}}
    return preset(nova(**kw) + [band("Bell", float(f), g, q) for f, g, q in diff.get("bells", bells)],
                  diff.get("comp", comp))


# Her türe uyan Harman eğrisi; tanınmayan türler buna düşer
PRESETS = {"Genel": preset(nova(), GLUE)}
PRESETS.update((name, genre_preset(family, diff)) for name, family, _, diff in GENRES)
CATALOG = {"genres": [{"name": n, "family": f, "keywords": k, "turkish": n in TURKISH} for n, f, k, _ in GENRES],
           "deezer": {str(k): v for k, v in DEEZER.items()},
           "turkish_variant": TURKISH_VARIANT, "defaults": DEFAULTS}


APO_TYPES = {"Hi-pass": "HPQ", "Bell": "PK", "Lo-shelf": "LSC", "Hi-shelf": "HSC"}
HEADSET_TYPES = {"Hi-pass": "highpass", "Bell": "peaking", "Lo-shelf": "lowshelf", "Hi-shelf": "highshelf"}


def single_slope(bands):
    """x2 eğimli filtreyi iki ardışık filtreye açar; APO'da ve kulaklıkta eğim ayarı yok."""
    return [b for b in bands for _ in range(2 if b["slope"] == "x2" else 1)]


def apo_config(bands, preamp):
    """Windows Equalizer APO config dosyası."""
    lines = [f"Preamp: {preamp:.1f} dB"]
    for i, b in enumerate(single_slope(bands), 1):
        gain = "" if b["type"] == "Hi-pass" else f" Gain {b['gain']:.1f} dB"
        lines.append(f"Filter {i}: ON {APO_TYPES[b['type']]} Fc {b['frequency']:g} Hz{gain} Q {b['q']:.2f}")
    return "\n".join(lines) + "\n"


def headset_bands(bands):
    """headsetcontrol --parametric-equalizer argümanı (kulaklığın kendi EQ'su: 10 bant, en az 20 Hz)."""
    return ";".join(f"{max(b['frequency'], 20):g},{b['gain']:g},{b['q']:g},{HEADSET_TYPES[b['type']]}"
                    for b in single_slope(bands)) + "\n"


def response_db(bands, f, fs=48000.0):
    """RBJ biquad yaklaşımıyla EQ'nun f frekansındaki toplam kazancı (dB)."""
    total = 0.0
    for b in bands:
        t, f0, g, q = b["type"], b["frequency"], b["gain"], b["q"]
        A = 10 ** (g / 40)
        w0 = 2 * math.pi * f0 / fs
        alpha = math.sin(w0) / (2 * q)
        cw = math.cos(w0)
        if t == "Bell":
            num = (1 + alpha * A, -2 * cw, 1 - alpha * A)
            den = (1 + alpha / A, -2 * cw, 1 - alpha / A)
        elif t in ("Lo-shelf", "Hi-shelf"):
            s = 1 if t == "Lo-shelf" else -1
            sq = 2 * math.sqrt(A) * alpha
            num = (A * ((A + 1) - s * (A - 1) * cw + sq),
                   s * 2 * A * ((A - 1) - s * (A + 1) * cw),
                   A * ((A + 1) - s * (A - 1) * cw - sq))
            den = ((A + 1) + s * (A - 1) * cw + sq,
                   -s * 2 * ((A - 1) + s * (A + 1) * cw),
                   (A + 1) + s * (A - 1) * cw - sq)
        else:
            continue  # Hi-pass tepe noktasını etkilemez
        w = 2 * math.pi * f / fs
        z1, z2 = complex(math.cos(-w), math.sin(-w)), complex(math.cos(-2 * w), math.sin(-2 * w))
        h = (num[0] + num[1] * z1 + num[2] * z2) / (den[0] + den[1] * z1 + den[2] * z2)
        total += 20 * math.log10(abs(h))
    return total


def peak(bands):
    """EQ eğrisinin 20 Hz-20 kHz arasındaki en yüksek noktası: (frekans, dB)."""
    curve = [(f, response_db(bands, f)) for f in (20 * 1.02 ** i for i in range(350)) if f <= 20000]
    return max(curve, key=lambda c: c[1])


for _data in PRESETS.values():  # girişte tepe + 1 dB kısılır (0.5 dB adım)
    _eq = _data["output"]["equalizer#0"]
    _eq["input-gain"] = -math.ceil(2 * (peak(list(_eq["left"].values()))[1] + 1.0)) / 2


SCHEMA = "/usr/share/glib-2.0/schemas/com.github.wwmm.easyeffects.%s.gschema.xml"


def schema_ranges(name):
    """EasyEffects gsettings şemasındaki min/max aralıkları (şema yoksa boş)."""
    import re
    try:
        xml = open(SCHEMA % name).read()
    except OSError:
        return {}
    out = {}
    for key, body in re.findall(r'<key name="([^"]+)"[^>]*>(.*?)</key>', xml, re.S):
        m = re.search(r'<range min="([^"]+)" max="([^"]+)"', body)
        if m:
            out[key] = (float(m.group(1)), float(m.group(2)))
    return out


def validate(name, data):
    """Aralık dışı değerleri EasyEffects sessizce reddeder; bunları yakala."""
    errors = []
    for plugin, schema in (("compressor#0", "compressor"), ("limiter#0", "limiter"),
                           ("equalizer#0", "equalizer")):
        ranges = schema_ranges(schema)
        for key, val in data["output"][plugin].items():
            if isinstance(val, (int, float)) and not isinstance(val, bool) and key in ranges:
                lo, hi = ranges[key]
                if not lo <= val <= hi:
                    errors.append(f"{name}: {plugin}.{key}={val} (izin verilen {lo}..{hi})")
    return errors


def check_catalog():
    """genres.json sözleşmesi (servis ve menü buna güvenir) ve her presetin sınırları."""
    names = [g[0] for g in GENRES]
    words = [w for g in GENRES for w in g[2]]
    family = {g[0]: g[1] for g in GENRES}
    errors = [] if len(GENRES) == 100 else [f"{len(GENRES)} tür var, tam 100 olmalı"]
    errors += [f"ad iki kez geçiyor: {n}" for n in sorted({n for n in names if names.count(n) > 1})]
    errors += [f"geçersiz ad: {n}" for n in names if "/" in n or n == "Genel"]
    errors += [f"anahtar kelime iki kez geçiyor: {w}" for w in sorted({w for w in words if words.count(w) > 1})]
    errors += [f"anahtar kelime küçük harf değil: {w}" for w in words if w != w.lower()]
    errors += [f"{where}: katalogda olmayan tür {v}" for where, values in
               (("defaults", DEFAULTS), ("deezer", DEEZER.values()), ("turkish_variant", TURKISH_VARIANT.values()),
                ("TURKISH", TURKISH)) for v in values if v not in family]
    errors += [f"turkish_variant: {k} -> {v} Türkçe tür değil ya da ailesi {k} değil"
               for k, v in TURKISH_VARIANT.items() if v not in TURKISH or family.get(v) != k]
    if len(DEFAULTS) != 5:
        errors.append(f"defaults {len(DEFAULTS)} tür, 5 olmalı")
    for name, data in PRESETS.items():
        eq = data["output"]["equalizer#0"]
        bands = list(eq["left"].values())
        if len(single_slope(bands)) > 10:
            errors.append(f"{name}: kulaklıkta {len(single_slope(bands))} bant, en fazla 10")
        if min(b["frequency"] for b in bands) < 20:
            errors.append(f"{name}: 20 Hz altında bant var")
        if any(b["gain"] > 0 and b["frequency"] > 12000 for b in bands):
            errors.append(f"{name}: 12 kHz üstünde yükseltme var")
        if peak(bands)[1] + eq["input-gain"] > -1.0:
            errors.append(f"{name}: net tepe -1 dB'in üstünde")
        errors += validate(name, data)
    return errors


if __name__ == "__main__":
    problems = check_catalog()
    if problems:
        sys.exit("Katalog/preset hataları:\n  " + "\n  ".join(problems))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    here = os.path.dirname(os.path.abspath(__file__))
    default_out = os.path.join(here, "output")
    out = args[0] if args else default_out
    for name, data in PRESETS.items():
        eq = data["output"]["equalizer#0"]
        bands = list(eq["left"].values())
        if "--check" in sys.argv:
            fmax, gmax = peak(bands)
            print(f"{name:17s} tepe {gmax:+.1f} dB @ {fmax:6.0f} Hz | input-gain {eq['input-gain']:+.1f}"
                  f" | net tepe {gmax + eq['input-gain']:+.1f} dB | "
                  + " ".join(f"{int(f)}:{response_db(bands, f):+.1f}" for f in (40, 60, 100, 200, 300, 1000, 3000, 6500, 12000)))
            continue
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, f"{name}.json"), "w") as fh:
            json.dump(data, fh, indent=4)
        print(f"yazıldı: {os.path.join(out, name)}.json")
        for folder, text in (("equalizer-apo", apo_config(bands, eq["input-gain"])),
                             ("headset", headset_bands(bands))):
            path = os.path.normpath(os.path.join(here, "..", folder, f"{name}.txt"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as fh:
                fh.write(text)
            print(f"yazıldı: {path}")
    if "--check" not in sys.argv:
        path = os.path.normpath(os.path.join(here, "..", "genres.json"))
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(CATALOG, fh, ensure_ascii=False, indent=1)
        print(f"yazıldı: {path}")
        stale = [(os.path.normpath(os.path.join(here, "..", d)), ".txt") for d in ("equalizer-apo", "headset")]
        if os.path.realpath(out) == os.path.realpath(default_out):
            stale.append((out, ".json"))
        for folder, ext in stale:  # katalogdan çıkmış türlerin eski dosyaları
            for f in sorted(os.listdir(folder)):
                if f.endswith(ext) and f[:-len(ext)] not in PRESETS:
                    os.remove(os.path.join(folder, f))
                    print(f"silindi: {os.path.join(folder, f)}")
