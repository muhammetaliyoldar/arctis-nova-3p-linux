#!/usr/bin/env python3
"""EasyEffects 7.x presetlerini ve tür kataloğunu (../genres.json) üretir: Genel + 24 ana tür + alt türler.

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
Ana türün eğrisi, gruptaki en çok dinlenen alt türün eski eğrisidir. Eski 100 türlük katalogdan
kalkan adların hangi ana türe katıldığı MERGED'dedir (merged): install.sh eski preset dosyalarını
kenara alır, sabit listeyi ve kilidi yeni adlara çevirir.

Alt türler (SUBGENRES, genres.json "subgenres"): en çok dinlenen ana türlerin içinde, kullanıcının
dinlediği sanatçılarla tanınan alt türler (Türkçe trap/boom bap'i hiçbir tür kaynağı ayırmıyor).
Servis sanatçı listede ise alt türün presetini, değilse ana türünkini çalar; ara katman yok.
Eğriler kullanıcının parçalarının ölçümünden (2026-11-06, EQ öncesi kayıt): hafızada
"Arctis- Türkçe Rap alt türleri ses ölçümü ve eğri önerisi".

Zincir: Equalizer -> [Bass Enhancer, Stereo Tools: yalnız bazı alt türlerde, Calf] -> Compressor -> Limiter
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
import unicodedata


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


def bass_enhancer(amount, scope=100.0, output_gain=-2.0):
    """Calf Bass Enhancer: scope altındaki basın harmoniklerini ekler (sub küçük kulaklıkta da duyulur).
    Harmonikler tepeyi yükseltir; çıkış kısılır ki limiter basta devreye girip bozmasın."""
    return {"bypass": False, "input-gain": 0.0, "output-gain": output_gain, "amount": amount,
            "harmonics": 8.5, "scope": scope, "floor": 20.0, "floor-active": True, "blend": 0.0, "listen": False}


def stereo_tools(base):
    """Calf Stereo Tools: yalnız stereo genişlik (stereo-base > 0 açar); diğer alanlar EasyEffects varsayılanı."""
    return {"bypass": False, "input-gain": 0.0, "output-gain": 0.0, "stereo-base": base}


def preset(bands, comp, fx=None):
    """input-gain aşağıda, PRESETS tanımlandıktan sonra eğrinin tepesinden hesaplanır.
    fx: EQ ile compressor arasına girecek eklentiler, {"bass_enhancer#0": {...}, ...}."""
    fx = fx or {}
    return {"output": {"blocklist": [],
                       "plugins_order": ["equalizer#0", *fx, "compressor#0", "limiter#0"],
                       "equalizer#0": equalizer(bands, 0.0), **fx,
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
    # v1 Indie: sıcak bas, vokal ve synth dokusu; kaynak çoğu zaman zaten ezilmiş
    "indie": (dict(mud=-3.0, presence=3.0, air=-4.0), [(80, 1.5, 0.9)], OFF),
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
    # akustik gitar gövdesi 250 Hz; keman/banjo parlaklığı yumuşak
    "folk": (dict(ls=2.0, mud=-3.0, presence=3.5, air=-3.0), [(250, 1.0, 1.0)], OFF),
    # dembow kick + 808, 55 Hz; masterlar pop kadar yüksek
    "latin": (dict(air=-4.0), [(55, 2.5, 0.9)], OFF),
    # mix'in merkezi bas gitar (60-100 Hz), skank gitar ve vokal; kayıtlar dinamik
    "reggae": (dict(mud=-3.0, presence=3.0, air=-3.5), [(70, 2.5, 0.9)], GLUE),
    # senkoplu kick/bas 60 Hz, parlak shaker'lar yumuşatılır
    "african": (dict(mud=-3.5, air=-4.0), [(60, 2.0, 0.9)], OFF),
    # darbuka düm'ü 90 Hz, ud/vokal gövdesi 500 Hz, kanun/yaylı parlaklığı yumuşak
    "arabic": (dict(mud=-3.0, mid=2.5, presence=3.0, air=-3.5), [(90, 1.5, 1.0)], GLUE),
}

# (ad, aile, MusicBrainz anahtar kelimeleri, aileden farklar: nova() ayarları, "bells", "comp")
# Ana tür + içine katılan alt türlerin kelimeleri; eğri, gruptaki en çok dinlenen alt türünkidir.
GENRES = [
    # Türkçe ş/ç/s yoğun, miksler 5 kHz'i zaten itiyor (DaBaby mühendisi vokal bus +2.5 dB @5k): presence az
    ("Türkçe Rap", "rap", ["turkish hip hop", "turkish rap", "turkish trap", "türkçe rap"], {"presence": 3.5}),
    # Travis Scott / Gorillaz miksleri 25-40 Hz'e iniyor (hp 20), bas harmonikleri 100-200 Hz'e bilerek
    # ekleniyor (çamur az kesilir), 8-9 kHz sertliğini mühendis zaten alıyor (air az kesilir)
    ("Hip Hop", "rap", ["hip hop", "hip-hop", "hiphop", "rap", "g-funk", "trap", "drill", "boom bap", "boom-bap",
                        "east coast hip hop", "golden age hip hop", "jazz rap", "phonk", "memphis rap", "grime",
                        "pop rap", "melodic rap"],
     {"mud": -4.0, "air": -4.0, "hp": 20.0, "bells": [(50, 2.5, 0.9)]}),

    ("Pop", "pop", ["pop", "dance", "synthpop", "synth-pop", "synth pop", "techno-pop", "new wave", "electropop",
                    "electro-pop", "electro pop", "hyperpop", "digicore", "k-pop", "kpop", "korean pop", "j-pop",
                    "jpop", "japanese pop", "anime", "city pop", "bollywood", "filmi", "bhangra"],
     {"mud": -3.0, "mid": 2.5, "bells": [(80, 1.5, 0.9)]}),  # Synthpop'tan: synth bas 80 Hz
    # vokal gövdesi önde, parlak Türkçe sibilans yumuşak
    ("Türkçe Pop", "pop", ["turkish pop", "türkçe pop"], {"mid": 2.5, "presence": 3.5, "air": -4.5}),

    ("Rock", "rock", ["rock", "hard rock", "classic rock", "rock and roll", "rock & roll", "rock opera",
                      "alternative rock", "alt-rock", "britpop", "punk", "punk rock", "grunge", "post-punk",
                      "post punk", "dance-punk", "darkwave", "coldwave", "prog", "progressive rock", "prog rock",
                      "blues", "country blues"], {}),
    ("Türkçe Rock", "rock", ["turkish rock", "türkçe rock", "anatolian rock", "anadolu rock", "anatolian psych"],
     {"mid": 2.5, "presence": 3.0}),  # vokal önde

    ("Metal", "metal", ["metal", "heavy metal", "nwobhm", "thrash", "death metal", "deathcore", "metalcore",
                        "post-hardcore", "nu metal", "nu-metal", "rap metal"], {}),

    ("Indie", "indie", ["indie", "lo-fi", "turkish indie", "turkish alternative", "indie rock", "indie pop",
                        "bedroom pop", "jangle pop", "dream pop", "chillwave", "baroque pop", "shoegaze", "nu gaze",
                        "psych"],
     {"mid": 2.5, "air": -3.5}),  # gitar/vokal/synth gövdesi ortada; bant kaydı yumuşak tiz ile 8 kHz'li vokal arası

    ("R&B", "rnb", ["r&b", "rnb", "rhythm and blues", "alternative r&b", "indie r&b", "pbr&b", "trap soul",
                    "neo soul", "neo-soul", "soul", "motown", "funk", "funk rock", "jazz-funk", "jazz funk", "gospel",
                    "worship"], {}),

    ("House", "house", ["house", "lo-fi house", "latin house", "tech house", "progressive house", "french house",
                        "french touch", "filter house", "nu-disco", "nu disco", "indie dance", "disco house", "disco"],
     {"mid": 2.5, "bells": [(90, 2.0, 1.0), (1000, 1.0, 1.0)]}),  # French House'tan: filtreli disco örnekleri ortada
    # v1 Deep House: derin, sıcak sub ve yumuşak tizler; hafif yapıştırma, uzun setlerde yormaz
    ("Deep House", "house", ["deep house", "organic house", "afro house", "melodic house"],
     {"air": -2.5, "bells": [(60, 2.0, 0.8)], "comp": SLOW}),

    ("Techno", "techno", ["techno", "rave", "hard techno", "industrial techno", "schranz", "melodic techno",
                          "trance", "psytrance", "psy-trance", "psychedelic trance", "goa trance"], {}),
    ("Bass Müziği", "bass", ["drum and bass", "drum & bass", "drum n bass", "dnb", "liquid funk", "neurofunk",
                             "jungle", "dubstep", "brostep", "uk garage", "2-step", "speed garage", "bassline"],
     # UK Garage'dan: 2-step davullar ve vokal kesitleri; harmoniksiz sinüs sub kulaklıkta ancak temeliyle duyulur
     {"ls": 2.0, "presence": 3.5, "bells": [(55, 2.5, 1.0)]}),
    # big room kick 55 Hz, -5 LUFS masterlar
    ("EDM", "electronic", ["edm", "big room", "electro house", "electronic dance", "hardstyle", "hard dance",
                           "rawstyle", "gabber", "future bass"],
     {"ls": 2.0, "presence": 3.0, "air": -4.5, "bells": [(55, 2.5, 1.0)]}),
    ("Elektronik", "electronic", ["electronic", "electronica", "electro", "idm", "synthwave", "retrowave", "outrun",
                                  "vaporwave", "darksynth", "downtempo", "trip hop", "trip-hop"],
     {"air": -4.0}),  # en düz eğimli (en parlak) tür: tizler kaynakta zaten yükseltilmiş
    ("Ambient - Lo-fi", "ambient", ["ambient", "new age", "meditation", "lo-fi hip hop", "lofi", "chillhop", "chill",
                                    "lounge"], {}),

    ("Latin", "latin", ["reggaeton", "reggaetón", "latin trap", "dembow", "urbano", "latin", "sertanejo", "salsa",
                        "latin jazz", "timba", "son cubano", "bachata", "cumbia", "vallenato", "regional mexican",
                        "corrido", "banda", "mariachi", "norteño", "ranchera", "funk carioca", "baile funk",
                        "brazilian funk", "funk brasileiro"],
     {"ls": 2.5, "mid": 2.5, "bells": [(60, 1.5, 0.9)]}),  # Latin Pop'tan
    ("Afrobeats", "african", ["afrobeat", "afropop", "afro pop", "afro-pop", "naija", "highlife", "amapiano", "gqom",
                              "kwaito"], {}),
    ("Reggae", "reggae", ["reggae", "dub", "ska", "rocksteady", "dancehall", "ragga"], {}),

    # kaset dönemi yaylıları sert, bas ince
    ("Arabesk", "arabic", ["arab", "khaleeji", "raï", "chaabi", "arabesk", "arabesque", "damar", "fantezi"],
     {"ls": 3.0, "presence": 2.5, "air": -4.0, "bells": [(90, 1.5, 1.0)]}),
    # Türk Halk'tan: bağlama ve zurna 2-5 kHz'te zaten keskin; TRT kayıtlarının ince altı ısıtılır
    ("Türk Halk - Sanat", "folk", ["turkish folk", "türk halk", "türkü", "halk müziği", "uzun hava",
                                   "turkish classical", "türk sanat", "sanat müziği", "fasıl"],
     {"ls": 2.5, "presence": 3.0, "air": -3.5, "bells": [(90, 1.0, 1.0)]}),
    ("Folk - Akustik", "folk", ["folk", "folk rock", "acoustic", "singer-songwriter", "singer/songwriter",
                                "singer songwriter", "country", "bluegrass", "americana", "indie folk", "chamber folk"],
     {"air": -2.5, "bells": [(250, 0.5, 1.0)]}),  # kaynak zaten koyu; mühendisler 200-300 Hz'i kısıp tizi koruyor
    ("Caz", "jazz", ["jazz", "bebop", "swing", "soul jazz", "smooth jazz", "bossa nova", "mpb", "samba"], {}),
    ("Klasik", "classical", ["classical", "orchestral", "opera", "neoclassical", "neo-classical", "modern classical",
                             "contemporary classical", "soundtrack", "film score", "video game"], {}),
]

TURKISH = {"Türkçe Rap", "Türkçe Pop", "Türkçe Rock", "Arabesk", "Türk Halk - Sanat"}
# Sanatçı/şarkı Türkçeyse ailenin bu türü seçilir
TURKISH_VARIANT = {"rap": "Türkçe Rap", "pop": "Türkçe Pop", "rock": "Türkçe Rock", "folk": "Türk Halk - Sanat"}
DEFAULTS = ["Türkçe Rap", "Indie", "Elektronik", "Türkçe Rock", "R&B"]
# Deezer'ın üst düzey türlerine karşılık gelen geniş türler: etiketlerde bunlardan daha özel bir tür
# (House, Bass Müziği...) varsa o seçilir ("electronic, uk garage" -> Bass Müziği)
GENERIC = ["Pop", "Hip Hop", "Rock", "EDM", "R&B", "Indie", "Elektronik", "Folk - Akustik", "Reggae", "Caz", "Klasik",
           "Metal", "Afrobeats", "Arabesk", "Latin"]
# Deezer tür numarası -> tür (api.deezer.com/genre ve /genre/<id>; albümler ana ve alt türleri birlikte verir)
DEEZER = {
    132: "Pop", 116: "Hip Hop", 152: "Rock", 113: "EDM", 165: "R&B", 85: "Indie", 106: "Elektronik",
    466: "Folk - Akustik", 144: "Reggae", 129: "Caz", 98: "Klasik", 173: "Klasik", 464: "Metal", 169: "R&B",
    2: "Afrobeats", 12: "Arabesk", 16: "Pop", 153: "Rock", 75: "Latin", 81: "Pop", 95: "Pop", 197: "Latin",
    84: "Folk - Akustik", 3: "Afrobeats", 13: "Arabesk", 14: "Arabesk", 15: "Arabesk", 22: "Pop", 23: "Pop",
    49: "Türk Halk - Sanat", 58: "Latin", 65: "Latin", 67: "Latin", 71: "Latin", 76: "Latin", 78: "Caz", 79: "Latin",
    80: "Latin", 86: "Indie", 87: "Indie", 99: "Klasik", 100: "Klasik", 101: "Klasik", 102: "Klasik", 103: "Klasik",
    104: "Klasik", 105: "Klasik", 107: "Elektronik", 108: "Bass Müziği", 110: "Pop", 111: "House", 112: "Deep House",
    114: "EDM", 115: "Techno", 121: "Hip Hop", 122: "Latin", 123: "Hip Hop", 124: "Hip Hop", 125: "Afrobeats",
    128: "Hip Hop", 130: "Caz", 131: "Caz", 133: "Indie", 134: "Pop", 137: "Türkçe Pop", 138: "Latin", 143: "Pop",
    145: "Reggae", 146: "Reggae", 147: "Reggae", 154: "Indie", 155: "Rock", 156: "Rock", 159: "Türkçe Rock",
    160: "Rock", 166: "R&B", 167: "R&B", 168: "House", 170: "R&B", 171: "R&B", 174: "Klasik", 175: "Klasik",
    176: "Klasik", 177: "Klasik", 178: "Pop", 179: "Klasik", 180: "Rock", 181: "Rock", 182: "Rock", 183: "Rock",
    184: "Rock", 185: "Rock", 186: "R&B", 187: "R&B", 188: "R&B", 192: "Folk - Akustik", 193: "Folk - Akustik",
    194: "Folk - Akustik", 195: "Folk - Akustik", 196: "Folk - Akustik", 200: "Hip Hop", 202: "Hip Hop",
    204: "Hip Hop", 206: "Hip Hop", 208: "Hip Hop", 472: "Latin", 498: "Latin", 500: "Latin", 504: "Latin",
    510: "Latin", 512: "Latin", 514: "Latin", 516: "Latin", 520: "Hip Hop", 522: "Folk - Akustik", 530: "Latin",
    532: "Folk - Akustik", 534: "Latin", 536: "R&B", 537: "Elektronik",
}
# Eski 100 türlük katalogdan kalkan ad -> katıldığı ana tür
MERGED = {
    "Trap": "Hip Hop", "Drill": "Hip Hop", "Boom Bap": "Hip Hop", "Phonk": "Hip Hop", "Grime": "Hip Hop",
    "Pop Rap": "Hip Hop", "Lo-fi Hip Hop": "Ambient - Lo-fi", "Hard Techno": "Techno", "Melodic Techno": "Techno",
    "Trance": "Techno", "Psytrance": "Techno", "Hardstyle": "EDM", "Future Bass": "EDM", "Tech House": "House",
    "Progressive House": "House", "French House": "House", "Nu-Disco": "House", "Disco": "House",
    "Afro House": "Deep House", "Drum & Bass": "Bass Müziği", "Jungle": "Bass Müziği", "Dubstep": "Bass Müziği",
    "UK Garage": "Bass Müziği", "Synthwave": "Elektronik", "Downtempo": "Elektronik", "Trip Hop": "Elektronik",
    "Ambient": "Ambient - Lo-fi", "Dance Pop": "Pop", "Synthpop": "Pop", "Electropop": "Pop", "Hyperpop": "Pop",
    "K-pop": "Pop", "J-pop": "Pop", "Bollywood": "Pop", "Türkçe Indie": "Indie", "Indie Rock": "Indie",
    "Indie Pop": "Indie", "Dream Pop": "Indie", "Shoegaze": "Indie", "Psikedelik": "Indie",
    "Indie Folk": "Folk - Akustik", "Anadolu Rock": "Türkçe Rock", "Hard Rock": "Rock", "Klasik Rock": "Rock",
    "Alternatif Rock": "Rock", "Punk": "Rock", "Grunge": "Rock", "Post-Punk": "Rock", "Progresif Rock": "Rock",
    "Blues": "Rock", "Heavy Metal": "Metal", "Thrash Metal": "Metal", "Death Metal": "Metal", "Metalcore": "Metal",
    "Nu Metal": "Metal", "Alternatif R&B": "R&B", "Neo Soul": "R&B", "Soul": "R&B", "Funk": "R&B", "Gospel": "R&B",
    "Smooth Jazz": "Caz", "Bossa Nova": "Caz", "Opera": "Klasik", "Neoklasik": "Klasik", "Film Müziği": "Klasik",
    "Akustik": "Folk - Akustik", "Folk": "Folk - Akustik", "Country": "Folk - Akustik",
    "Türk Halk": "Türk Halk - Sanat", "Türk Sanat": "Türk Halk - Sanat", "Reggaeton": "Latin", "Latin Pop": "Latin",
    "Salsa": "Latin", "Bachata": "Latin", "Cumbia": "Latin", "Meksika Müziği": "Latin", "Funk Carioca": "Latin",
    "Dancehall": "Reggae", "Amapiano": "Afrobeats", "Arap Müziği": "Arabesk", "Fantezi": "Arabesk",
}

# (ad, ana tür, aileden farklar, sanatçılar). Ölçüm: Türkçe Rap ortalamasında bas tepesi 50-63 Hz;
# alt türlerin ortalamadan farkı yorumda. Sanatçı adları Spotify'daki gibi (servis harf/rakam dışını atıp karşılaştırır).
SUBGENRES = [
    # 808 32-60 Hz, 25-40 Hz ortalamadan +6..+8 dB, vokal bölgesi (0.8-3 kHz) -2; en sıkıştırılmış master (crest 9):
    # 808 göğüste, 808 harmonikleri (100-200 Hz) kalsın, vokal 808'in üstüne, hi-hat'e yer; compressor yok
    ("Türkçe Trap", "Türkçe Rap",
     {"ls": 3.0, "mud": -3.5, "mid": 1.5, "presence": 3.5, "air": -3.5, "hp": 20.0,
      "bells": [(40, 4.0, 0.9), (1500, 1.5, 1.0)], "comp": OFF, "fx": {"bass_enhancer#0": bass_enhancer(-6.0, 100.0)}},
     ["Şam", "Lil Zey", "UZI", "Ati242", "AGAB", "Kozmos", "Anıl Piyancı", "Wegh", "Volta Show", "K''st", "Grogi",
      "Stap", "Yung Ouzo", "PAN", "Istanbul Trip", "Jefe", "Motive", "Bixi Blake", "Gxblin", "GRi"]),
    # kick 50-60 Hz, snare gövdesi 125-200 Hz +1.5, sample tizi koyu (10-16 kHz -1.5..-3), dinamik geniş (crest 12)
    ("Türkçe Boom Bap", "Türkçe Rap",
     {"ls": 2.5, "mud": -3.0, "mid": 2.0, "presence": 4.0, "air": -3.0,
      "bells": [(60, 3.5, 1.0), (2200, 1.0, 1.0)]},
     ["Kamufle", "Allame", "Farazi", "Hayki", "Şehinşah", "Sagopa Kajmer", "Killa Hakan", "Mode XL", "Çağrı Sinci",
      "Kayra", "Sürveyan", "İndigo", "Redo", "Fredd", "İmpala", "Harim", "memzst", "Savai", "Kelanei", "Siirbaz",
      "90 BPM", "Spade427"]),
    # bas hafif (80-160 Hz -2), vokal/melodi önde (630 Hz-2 kHz +1..+2): sıcak, yumuşak tepe
    ("Türkçe Melodik Rap", "Türkçe Rap",
     {"ls": 2.0, "mud": -3.0, "presence": 3.0, "air": -4.0,
      "bells": [(60, 2.5, 0.9), (300, 1.0, 1.0)], "comp": GLUE},
     ["No.1", "Ahiyan", "Ezhel", "M Lisa", "Diyar Pala", "Şiir!", "Deniz Gürzumar", "Laçin", "Murda", "Sin4Hood", "Artz",
      "Stabil"]),
    # sub yok (31-50 Hz -4), kick 53-67 Hz, 2-12 kHz +1.5..+2 (parlak, kirli), en yoğun dinamik: kick yumruğu, tiz yormasın
    ("Türkçe Sert Rap", "Türkçe Rap",
     {"ls": 2.5, "mud": -4.0, "mid": 2.0, "presence": 3.0, "air": -5.0, "hp": 25.0,
      "bells": [(65, 3.5, 1.0), (1000, 1.0, 1.0)], "comp": OFF},
     ["Sansar Salvo", "Tahribad-ı İsyan", "Da Poet", "Hidra", "Maestro", "Contra", "Cash Flow"]),
    # 40 Hz altı -9..-11 dB (sub hiç yok: şişirilmez, hp yukarıda), 8-16 kHz +1..+6 (hışırtı), en az sıkıştırılmış
    ("Türkçe Old School", "Türkçe Rap",
     {"ls": 3.0, "mud": -3.0, "mid": 2.0, "presence": 3.0, "air": -5.5, "hp": 30.0,
      "bells": [(70, 3.0, 1.0), (13000, -2.0, 0.9)]},
     ["Ceza", "Ceg", "İstanbul Attack", "Beta Berk Bayındır", "DJ Sivo"]),
    # 31-40 Hz +6, tiz koyu (5-16 kHz -2..-3), tizde en geniş stereo: derin sub, açık tiz, biraz daha geniş
    ("Türkçe Deneysel Rap", "Türkçe Rap",
     {"ls": 2.5, "mud": -4.0, "presence": 3.5, "air": -3.0, "hp": 20.0,
      "bells": [(40, 3.0, 0.9)], "comp": OFF, "fx": {"stereo_tools#0": stereo_tools(0.15)}},
     ["Ağaçkakan", "Çiğ"]),
    # Hip Hop ve Indie: farklar kendi ana türlerinin ölçülen ortalamasına göre (Hip Hop 14, Indie 10 parça)
    # 808 tam 50 Hz (+3), 315-400 Hz +2 (vokal gövdesi), 1-2.5 kHz -1, tiz temiz, dinamik geniş (9.7):
    # 808 odakta, vokal öne (2 kHz), tiz açık, hafif yapıştırma
    ("Yabancı Melodik Rap", "Hip Hop",
     {"ls": 2.0, "mud": -3.0, "presence": 3.5, "air": -3.0, "hp": 20.0,
      "bells": [(50, 3.0, 1.0), (2000, 1.5, 1.0)], "comp": GLUE},
     ["Yenlik", "Ruhsora Emm", "Connor Price", "ния", "R-Kap"]),
    # sub az (25-50 Hz -3), kick/bas gövdesi 60-80 Hz, 1-2 kHz +1..+1.7 (canlı enstrüman, vokal), az sıkıştırılmış
    # (crest 11.6): olmayan sub şişirilmez, gövde ve orta öne
    ("Alternatif Hip Hop", "Hip Hop",
     {"ls": 2.0, "mud": -3.5, "mid": 2.5, "presence": 3.5, "air": -4.0, "hp": 25.0,
      "bells": [(70, 2.5, 1.0), (1500, 1.5, 1.0)]},
     ["Gorillaz", "Bloody Immigrants", "Chefket", "Mac Miller", "Kendrick Lamar"]),
    # 25-40 Hz +3..+6 (en derin sub), 10-16 kHz -2.4..-6 (buğulu), en sıkıştırılmış (crest 8.7), ortada en geniş
    # stereo (reverb): Türkçe Trap gibi derin 808 + Bass Enhancer, koyu tiz biraz açılır, compressor yok
    ("Cloud Rap", "Hip Hop",
     {"ls": 3.0, "mud": -4.0, "mid": 1.5, "presence": 3.0, "air": -3.0, "hp": 20.0,
      "bells": [(40, 4.0, 0.9)], "comp": OFF, "fx": {"bass_enhancer#0": bass_enhancer(-6.0, 100.0)}},
     ["Derek Pope", "IVOXYGEN", "BONES", "Biv"]),
    # bas gitar/synth bas 57-85 Hz, 31-50 Hz -2..-3 (sub az), yüksek ve sıkıştırılmış master (RMS -9.5, crest 9.3),
    # bas bile stereo: groove 80 Hz'de, alt-orta sıcak kalsın (çamur az kesilir), tiz yumuşak
    ("Neo-Psikedelik", "Indie",
     {"ls": 2.0, "mud": -2.5, "mid": 2.5, "air": -4.0, "hp": 25.0, "bells": [(80, 2.5, 0.9)]},
     ["Tame Impala", "Dolphin Love"]),
    # 25-50 Hz +5..+9.5 (synth/808 sub), 80 Hz -3, 2.5-16 kHz -3..-5.6 (koyu), tizde çok geniş stereo:
    # derin sub, koyu tiz biraz açılır
    ("Indie Elektronik", "Indie",
     {"ls": 3.0, "mud": -3.5, "mid": 2.0, "presence": 3.5, "air": -2.5, "hp": 20.0, "bells": [(40, 3.5, 0.9)]},
     ["Kid Francescoli", "Nova Norda", "Lin Pesto"]),
    # tek ölçüm (Lana Del Rey West Coast): bas az (25-125 Hz -1.3..-7.6), 400 Hz-1.25 kHz +1.5..+5.5 (vokal,
    # reverb'lü gitar), 10-12.5 kHz +4 (parıltı): orta zaten dolu (mid az), 250 Hz sıcaklık, parıltı açık
    ("Rüya Pop", "Indie",
     {"ls": 1.5, "mud": -2.5, "mid": 1.5, "presence": 3.5, "air": -2.5, "hp": 25.0,
      "bells": [(250, 1.5, 0.9)], "comp": GLUE},
     ["Lana Del Rey", "Still Corners"]),
]


def genre_preset(family, diff):
    """Aile şablonu + türün farkları; "bells" ve "comp" verilirse ailedekinin yerine geçer, "fx" eklenir."""
    kw, bells, comp = FAMILIES[family]
    kw = {**kw, **{k: v for k, v in diff.items() if k not in ("bells", "comp", "fx")}}
    return preset(nova(**kw) + [band("Bell", float(f), g, q) for f, g, q in diff.get("bells", bells)],
                  diff.get("comp", comp), diff.get("fx"))


FAMILY_OF = {name: family for name, family, _, _ in GENRES}
# Her türe uyan Harman eğrisi; tanınmayan türler buna düşer
PRESETS = {"Genel": preset(nova(), GLUE)}
PRESETS.update((name, genre_preset(family, diff)) for name, family, _, diff in GENRES)
PRESETS.update((name, genre_preset(FAMILY_OF[parent], diff)) for name, parent, diff, _ in SUBGENRES
               if parent in FAMILY_OF)  # ana türü olmayan alt tür check_catalog'da hata
CATALOG = {"genres": [{"name": n, "family": f, "keywords": k, "turkish": n in TURKISH} for n, f, k, _ in GENRES],
           "subgenres": [{"name": n, "parent": p, "artists": a} for n, p, _, a in SUBGENRES],
           "deezer": {str(k): v for k, v in DEEZER.items()},
           "turkish_variant": TURKISH_VARIANT, "defaults": DEFAULTS, "generic": GENERIC, "merged": MERGED}


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


PLUGIN_SCHEMA = {"equalizer": "equalizer", "compressor": "compressor", "limiter": "limiter",
                 "bass_enhancer": "bassenhancer", "stereo_tools": "stereotools"}


def validate(name, data):
    """Aralık dışı değerleri EasyEffects sessizce reddeder; bunları yakala."""
    errors = []
    for plugin in data["output"]["plugins_order"]:
        ranges = schema_ranges(PLUGIN_SCHEMA[plugin.split("#")[0]])
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
    errors = [] if len(GENRES) == 24 else [f"{len(GENRES)} tür var, tam 24 olmalı"]
    errors += [f"ad iki kez geçiyor: {n}" for n in sorted({n for n in names if names.count(n) > 1})]
    errors += [f"geçersiz ad: {n}" for n in names if "/" in n or n == "Genel"]
    errors += [f"anahtar kelime iki kez geçiyor: {w}" for w in sorted({w for w in words if words.count(w) > 1})]
    errors += [f"anahtar kelime küçük harf değil: {w}" for w in words if w != w.lower()]
    errors += [f"{where}: katalogda olmayan tür {v}" for where, values in
               (("defaults", DEFAULTS), ("deezer", DEEZER.values()), ("turkish_variant", TURKISH_VARIANT.values()),
                ("TURKISH", TURKISH), ("merged", MERGED.values()), ("generic", GENERIC))
               for v in values if v not in family]
    errors += [f"merged: {k} hâlâ katalogda" for k in MERGED if k in family or k == "Genel"]
    errors += [f"turkish_variant: {k} -> {v} Türkçe tür değil ya da ailesi {k} değil"
               for k, v in TURKISH_VARIANT.items() if v not in TURKISH or family.get(v) != k]
    if len(DEFAULTS) != 5:
        errors.append(f"defaults {len(DEFAULTS)} tür, 5 olmalı")
    subs = [s[0] for s in SUBGENRES]
    errors += [f"alt tür adı iki kez ya da ana türle aynı: {n}" for n in sorted({n for n in subs
                                                                               if (subs + names).count(n) > 1})]
    errors += [f"geçersiz alt tür adı: {n}" for n in subs if "/" in n or n == "Genel" or n in MERGED]
    errors += [f"{n}: ana tür {p} katalogda yok" for n, p, _, _ in SUBGENRES if p not in family]
    norm = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if c.isalnum())  # servisle aynı
    artists = [norm(a) for s in SUBGENRES for a in s[3]]
    errors += [f"sanatçı iki kez geçiyor: {a}" for a in sorted({a for a in artists if artists.count(a) > 1})]
    errors += [f"{n}: sanatçı listesi boş ya da boş ad var" for n, _, _, a in SUBGENRES if not a or not all(map(norm, a))]
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
            print(f"{name:19s} tepe {gmax:+.1f} dB @ {fmax:6.0f} Hz | input-gain {eq['input-gain']:+.1f}"
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
