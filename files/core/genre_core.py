"""Tür takibinin platformdan bağımsız çekirdeği (Linux, Windows, macOS ön yüzleri kullanır).

Ön yüz çalan şarkıyı Follower.on_track'e verir; preseti kendi ses motoruyla uygular (engine: current() yüklü
preset, has(ad) preset var mı, apply(ad) uygula). Linux ön yüzü: files/bin/spotify-genre-preset.
Türler genres.json'da (24 ana tür; her türün aynı adlı bir preseti var, uymayan her şey Genel):
veri klasöründeki genres.json, yoksa bu dosyanın yanındaki ../genres.json.
Alt tür: sanatçı genres.json "subgenres" listesindeyse ağ sorgusu yapılmadan alt türün preseti çalar
(preset dosyası yoksa ana türünki); listede yoksa aşağıdaki gibi ana tür bulunur, sonra MusicBrainz etiketleri
oy sırasıyla taranır: o ana türün bir alt türünün anahtar kelimesini içeren ilk etiket (en uzun kelime) alt türü
seçer (yeni keşfedilen sanatçılar için); hiçbiri yoksa ana tür. Sıralama ve sayım ana tür düzeyinde.
Tür (anahtar gerekmez): Deezer albüm türü ve MusicBrainz sanatçı etiketleri. Etiketler oy sırasıyla
taranır, ilk eşleşen etikette en uzun anahtar kelime kazanır ("deep house" > "house"). Etiket türü,
Deezer türü yoksa, aynı ailedense ya da Deezer türü genişse (pop, dance, elektro, alternatif,
techno/house) seçilir; değilse Deezer türü (MusicBrainz'deki ad karışıklığı başka aileden tür
getirmesin). Sanatçı ya da şarkı Türkçeyse (ğ ı ş harfleri ya da "turkish" etiketi) ve tür, Türkçe
karşılığı olan bir türse o seçilir (Hip Hop -> Türkçe Rap, Rock -> Türkçe Rock).
Sonuç albüm başına ~/.cache/spotify-genre-preset.json'a yazılır, tekrar sorulmaz.
Her şarkı değişiminde türün presetine geçilir (preset dosyası yoksa Genel); elle seçilen preset o
şarkı boyunca kalır. ~/.local/state/spotify-genre-preset/kilit dosyasında bir preset adı varsa (üst bar
menüsündeki kilit) türden bağımsız hep o preset çalar. Ağ hatasında preset değişmez.
Üst bar menüsü ~/.local/state/spotify-genre-preset/state.json'u okur (menü sırası, çalan tür,
sıralamalar, istatistik). Menünün 5 türü ~/.config/spotify-genre-preset/config.json'daki moda ve
"donem"e (gün: 1, 7, 30, 90, 180, 365; varsayılan 30) göre: "cihaz" (bu bilgisayarda
dönem içinde çalan şarkıların türü; saatlik geçmiş gecmis.json'da, dönemde dinleme yoksa tüm zamanlar),
"hesap" (Spotify, telefon dahil tüm cihazlar: 1 ay/6 ay/1 yıl için Spotify'ın ~4 hafta/~6 ay/~1 yıl
listesindeki en çok dinlenen 50 parça, 6 saatte bir; 1 gün/1 hafta/3 ay için yarım saatte bir çekilen son
çalınanlardan biriken geçmiş, geçmiş dönemi henüz kapsamıyorsa dönemi kapsayan en kısa Spotify listesi).
config.json "sabitle" listesindeki türler (en fazla 5) sıralamadaki en az dinlenenlerin yerine geçer, "gizli"
listesindekiler menüye girmez. config.json değişince menü hemen yeniden hesaplanır.
Klasörler (app_paths): Linux'ta XDG (~/.config, ~/.local/state, ~/.local/share/spotify-genre-preset,
~/.cache/spotify-genre-preset.json), Windows'ta %LOCALAPPDATA%\\spotify-genre-preset, macOS'ta
~/Library/Application Support/spotify-genre-preset. Durum, geçmiş ve sayım kilitle korunur: ön yüzün olay
iş parçacığı ile Spotify iş parçacığı (run_spotify) aynı anda yazabilir.
"""
import base64
import hashlib
import json
import os
import re
import secrets
import ssl
import sys
import threading
import time
import traceback
import unicodedata
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import urllib.error
import urllib.parse
import urllib.request

GENEL = "Genel"
BROAD_DEEZER = {"132", "113", "106", "85", "111", "152"}  # Pop, Dance, Electro, Alternative, Techno/House, Rock: etiket daha özel
TURKISH_LETTERS = set("ğışİĞŞ")

UA = "arctis-nova-3p-linux (https://github.com/muhammetaliyoldar/arctis-nova-3p-linux)"
APP = "spotify-genre-preset"


def app_paths():
    """(ayar, durum, veri klasörü, önbellek dosyası)."""
    home = os.path.expanduser("~")
    if sys.platform == "win32":
        d = os.path.join(os.environ["LOCALAPPDATA"], APP)
        return d, d, d, os.path.join(d, "cache.json")
    if sys.platform == "darwin":
        d = os.path.join(home, "Library", "Application Support", APP)
        return d, d, d, os.path.join(home, "Library", "Caches", APP + ".json")
    xdg = lambda var, default: os.environ.get(var) or os.path.join(home, default)  # noqa: E731
    return (os.path.join(xdg("XDG_CONFIG_HOME", ".config"), APP), os.path.join(xdg("XDG_STATE_HOME", ".local/state"), APP),
            os.path.join(xdg("XDG_DATA_HOME", ".local/share"), APP), os.path.join(xdg("XDG_CACHE_HOME", ".cache"), APP + ".json"))


CONFIG_DIR, STATE_DIR, DATA_DIR, CACHE = app_paths()
STATE, LOCK = os.path.join(STATE_DIR, "state.json"), os.path.join(STATE_DIR, "kilit")
HISTORY = os.path.join(STATE_DIR, "gecmis.json")
CONFIG, SPOTIFY = os.path.join(CONFIG_DIR, "config.json"), os.path.join(CONFIG_DIR, "spotify.json")
REDIRECT = "http://127.0.0.1:8888/callback"
DONEMLER = (1, 7, 30, 90, 180, 365)  # menüdeki dönemler (gün)
WINDOWS = {30: "short_term", 180: "medium_term", 365: "long_term"}  # Spotify'ın kendi dönemleri, kısadan uzuna
WINDOW_TEXT = {"short_term": "~4 haftalık", "medium_term": "~6 aylık", "long_term": "~1 yıllık"}


def norm(s):
    """Ad karşılaştırması için: harf ve rakam dışı her şey atılır, "İ" = "i" (make_presets.py'deki ile aynı)."""
    return "".join(c for c in unicodedata.normalize("NFKD", s.casefold()) if c.isalnum())


def load_genres():
    """genres.json + aramalar için türetilen tablolar: family (tür -> aile), keywords (kelime -> tür)."""
    for path in (os.path.join(DATA_DIR, "genres.json"),
                 os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "genres.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                cat = json.load(fh)
        except FileNotFoundError:
            continue
        cat["family"] = {g["name"]: g["family"] for g in cat["genres"]}
        cat["keywords"] = {k: g["name"] for g in cat["genres"] for k in g["keywords"]}
        cat["parent"] = {s["name"]: s["parent"] for s in cat.get("subgenres", [])}
        cat["artist_sub"] = {norm(a): s["name"] for s in cat.get("subgenres", []) for a in s["artists"]}
        cat["sub_keywords"] = {}  # ana tür -> {kelime: alt tür}
        for s in cat.get("subgenres", []):
            cat["sub_keywords"].setdefault(s["parent"], {}).update((k, s["name"]) for k in s.get("keywords", []))
        return cat
    sys.exit("genres.json bulunamadı: ~/.local/share/spotify-genre-preset/genres.json yok "
             "(install.sh kurar; repodan çalıştırırken files/genres.json olmalı)")


CAT = load_genres()

# Python 3.13+ sıkı X.509 denetimi, AKI'siz sertifika basan TLS ara kutularını (ör. kurum/kampüs proxy'si) reddediyor
SSL_CTX = ssl.create_default_context()
SSL_CTX.verify_flags &= ~ssl.VERIFY_X509_STRICT


def get_json(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=8, context=SSL_CTX) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:  # MusicBrainz yoğunken 503 dönüyor
            if e.code != 503 or i == tries - 1:
                raise
            time.sleep(2)


def same_name(a, b):
    """"Siyasiyabend" = "Siya siyabend", "AGAB" = "Aga B", "İ" = "i"."""
    return norm(a) == norm(b)


def deezer_genres(artist, title):
    """Şarkının albüm tür numaraları; şarkı bulunamazsa boş liste."""
    title = re.split(r" - |\(|\[", title)[0].strip()  # "... - Live Session", "(feat. X)" aramayı bozuyor
    q = urllib.parse.quote(f"{artist} {title}")
    for t in get_json(f"https://api.deezer.com/search?q={q}&limit=5").get("data", []):
        if same_name(t["artist"]["name"], artist):
            album = get_json(f"https://api.deezer.com/album/{t['album']['id']}")
            return [g["id"] for g in album.get("genres", {}).get("data", [])]
    return []


mb_next = 0.0


def musicbrainz_tags(artist):
    """Adı birebir eşleşen sanatçının (önce etiketlisi) etiketleri, en çok oy alan önce. Ülkesi TR ise sona
    "turkish" eklenir: Türkçe adı ğ/ı/ş içermeyen rapçiler (Kamufle, Laçin...) de Türkçe türe gitsin."""
    global mb_next
    time.sleep(max(0.0, mb_next - time.monotonic()))  # MusicBrainz kuralı: saniyede en fazla 1 istek
    mb_next = time.monotonic() + 1.1
    q = urllib.parse.quote(f'artist:"{artist}"')
    exact = [a for a in get_json(f"https://musicbrainz.org/ws/2/artist/?query={q}&limit=5&fmt=json")["artists"]
             if a.get("score") == 100]
    a = next((a for a in exact if a.get("tags")), exact[0] if exact else None)
    if not a:
        return []
    tags = [t["name"] for t in sorted(a.get("tags", []), key=lambda t: -t["count"])]
    return tags + ["turkish"] if a.get("country") == "TR" else tags


def genre_from_tags(tags):
    """Oyu en yüksek 5 etiketten oy sırasıyla ilk ÖZEL tür (House, Bass Müziği, Techno...); yoksa
    oradaki ilk eşleşen genel tür (Elektronik, Pop: genres.json "generic"); o da yoksa sonraki
    etiketlerden ilk eşleşen. Etiket birden çok kelime içeriyorsa en uzunu. Eşleşme yoksa (None, None)."""
    generic = set(CAT["generic"])
    matches = []  # (etiket sırası, tür, kelime)
    for i, t in enumerate(tags):
        words = [w for w in CAT["keywords"] if w in t]
        if words:
            word = max(words, key=len)
            matches.append((i, CAT["keywords"][word], word))
    top = [m for m in matches if m[0] < 5]
    pick = next((m for m in top if m[1] not in generic), None) or (top or matches or [None])[0]
    return (pick[1], pick[2]) if pick else (None, None)


def sub_from_tags(genre, tags):
    """Etiketlerde oy sırasıyla, türün bir alt türünün kelimesini içeren ilk etiketin alt türü (en uzun kelime)."""
    words = CAT["sub_keywords"].get(genre, {})
    for t in tags:
        hits = [w for w in words if w in t]
        if hits:
            return words[max(hits, key=len)]
    return None


def decide(deezer_ids, tags, artist, title):
    """Deezer albüm tür numaraları ve MusicBrainz etiketlerinden tür ya da alt tür adı (ya da Genel)."""
    family = CAT["family"]
    tagged, word = genre_from_tags(tags)
    dz_id = next((str(i) for i in deezer_ids if str(i) in CAT["deezer"]), None)
    dz = CAT["deezer"].get(dz_id)
    if tagged and (not dz or family[tagged] == family.get(dz) or dz_id in BROAD_DEEZER):
        genre = tagged
        general = word == family[tagged] or tagged in CAT["deezer"].values()  # "rap", "pop" gibi genel kelime
    elif dz:
        genre, general = dz, True
    else:
        return GENEL
    turkish = any(c in TURKISH_LETTERS for c in artist + title) or any("turkish" in t or "türk" in t for t in tags)
    genre = CAT["turkish_variant"].get(family.get(genre), genre) if turkish and general else genre
    return sub_from_tags(genre, tags) or genre


def classify(artist, title):
    return decide(deezer_genres(artist, title), musicbrainz_tags(artist), artist, title)


def main_genre(genre):
    """Alt türün ana türü (sayım, sıralama); ana tür ve Genel aynen döner."""
    return CAT["parent"].get(genre, genre)


def hour_now():
    return int(time.time() // 3600)


def add_play(buckets, ts, genre):
    """Saatlik kovaya ({saat: {tür: dinleme}}) bir dinleme ekler; 366 günden eski kovalar silinir."""
    bucket = buckets.setdefault(str(int(ts // 3600)), {})
    bucket[genre] = bucket.get(genre, 0) + 1
    for h in [h for h in buckets if int(h) < hour_now() - 366 * 24]:
        del buckets[h]


def since(buckets, days):
    """Son days günün kovalarındaki dinlemelerin tür toplamı (katalogdan çıkan türler atlanır)."""
    start, total = hour_now() - days * 24, {}
    for h, genres in buckets.items():
        if int(h) >= start:
            for g, n in genres.items():
                if g in CAT["family"]:
                    total[g] = total.get(g, 0) + n
    return total


def ranked(scores):
    return sorted(scores, key=lambda g: -scores[g])


def menu_for(cfg, st):
    """state.json "menu": sabitlenen türler ve modun sıralamasından kalan yerler (eksikse defaults'tan) toplam 5
    tür; sabitlenen tür en az dinlenenin yerine geçer. Dinlenme sırasında (dinlenmeyen sabitler sonda), sonra Genel,
    5'te değilse çalan preset (alt tür de olabilir)."""
    source = {"cihaz": st.get("top_cihaz"), "hesap": st.get("top_hesap") or st.get("top_cihaz")}.get(cfg["mode"]) or []
    order, hidden = [], set(cfg.get("gizli") or [])
    for g in source + CAT["defaults"]:
        if g in CAT["family"] and g not in order and g not in hidden:  # Genel, katalog dışı ve gizlenen atlanır
            order.append(g)
    pins = [g for g in dict.fromkeys(cfg.get("sabitle") or []) if g in CAT["family"]][:5]
    top = pins + [g for g in order if g not in pins][:5 - len(pins)]
    menu = sorted(top, key=lambda g: order.index(g) if g in order else len(order)) + [GENEL]
    playing = (st.get("current") or {}).get("preset")
    if (playing in CAT["family"] or playing in CAT["parent"]) and playing not in menu:
        menu.append(playing)
    return menu



def locked_preset():
    try:
        with open(LOCK, encoding="utf-8") as fh:
            return fh.read().strip() or None
    except FileNotFoundError:
        return None



def load(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def save(path, data, mode=0o644):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with os.fdopen(os.open(path + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode), "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    os.replace(path + ".tmp", path)


def token_request(fields):
    data = urllib.parse.urlencode(fields).encode()
    with urllib.request.urlopen("https://accounts.spotify.com/api/token", data, timeout=10, context=SSL_CTX) as r:
        return json.load(r)


def ask_client_id():
    print("Spotify hesabını bağlamak için bir kez ücretsiz bir Spotify geliştirici uygulaması gerekiyor:\n"
          "  1. https://developer.spotify.com/dashboard adresinde \"Create app\" de.\n"
          f"  2. Redirect URI olarak tam olarak şunu ekle: {REDIRECT}\n"
          "  3. Uygulamanın Client ID'sini aşağıya yapıştır.")
    client_id = input("Client ID: ").strip()
    if not client_id:
        sys.exit("Client ID girilmedi, hesap bağlanmadı.")
    return client_id


def login(client_id):
    """PKCE ile tek seferlik giriş; sadece refresh token saklanır (dosya izni 600)."""
    verifier = secrets.token_urlsafe(64)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state, answer = secrets.token_urlsafe(16), {}

    class Callback(BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state") == [state]:  # favicon gibi diğer istekler yok sayılır
                answer.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Tamam, bu sekmeyi kapatıp terminale dönebilirsin.".encode())

        def log_message(self, *_):
            pass

    server = HTTPServer(("127.0.0.1", 8888), Callback)
    url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode({
        "client_id": client_id, "response_type": "code", "redirect_uri": REDIRECT,
        "scope": "user-top-read user-read-recently-played",
        "code_challenge_method": "S256", "code_challenge": challenge, "state": state})
    print("Tarayıcıda Spotify girişi açılıyor. Açılmazsa bu adresi aç:\n" + url, flush=True)
    webbrowser.open(url)
    while not answer:
        server.handle_request()
    if "code" not in answer:
        sys.exit("Giriş başarısız: " + answer.get("error", ["bilinmeyen hata"])[0])
    tok = token_request({"grant_type": "authorization_code", "code": answer["code"][0], "redirect_uri": REDIRECT,
                         "client_id": client_id, "code_verifier": verifier})
    save(SPOTIFY, {"client_id": client_id, "refresh_token": tok["refresh_token"]}, 0o600)
    if not os.path.exists(CONFIG):
        save(CONFIG, {"mode": "hesap"})
    print("Spotify hesabı bağlandı.")


def access_token(cfg):
    tok = token_request({"grant_type": "refresh_token", "refresh_token": cfg["refresh_token"],
                         "client_id": cfg["client_id"]})
    if "refresh_token" in tok:  # Spotify bazen yenisini veriyor; eskisi geçersizleşir
        cfg["refresh_token"] = tok["refresh_token"]
        save(SPOTIFY, cfg, 0o600)
    return tok["access_token"]


def spotify_get(token, path):
    req = urllib.request.Request("https://api.spotify.com/v1/" + path, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as r:
        return json.load(r)


def recently_played(token):
    """Hesabın son çalınan 50 parçası (tüm cihazlar); eski girişte bu izin yoksa None."""
    try:
        return spotify_get(token, "me/player/recently-played?limit=50")["items"]
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return None
        raise



class Follower:
    def __init__(self, engine):
        self.engine = engine  # current() -> yüklü preset, has(ad) -> preset var mı, apply(ad) -> uygula
        self.track = None
        self.cache = load(CACHE, {})
        st = load(STATE, {})
        self.counts = {g: n for g, n in st.get("counts", {}).items() if g in CAT["family"]}  # eski aile adları atılır
        self.current = st.get("current")
        # {"cihaz"|"hesap": {saat: {ana tür: dinleme}}, "hesap_son": geçmişe eklenen son parçanın played_at'i}
        self.history = {"cihaz": {}, "hesap": {}, **load(HISTORY, {})}
        self.spotify = load(SPOTIFY, None)
        self.top_windows = st.get("hesap_donemler", {}) if self.spotify else None  # {dönem: {ana tür: puan}}
        self.need_login = False  # Spotify girişinde son çalınanlar izni yok
        self.read_config()
        self.lock = threading.RLock()  # önbellek ve durum (sayım, geçmiş, state.json) iş parçacıkları arasında ortak

    def read_config(self):
        try:
            cfg = load(CONFIG, {})
        except ValueError as e:
            print(f"config.json okunamadı ({e}), varsayılan mod kullanılıyor", flush=True)
            cfg = {}
        mode = cfg.get("mode") if cfg.get("mode") in ("cihaz", "hesap") else None  # eski "sabit" modu kaldırıldı
        self.config = {"mode": mode or ("hesap" if self.spotify else "cihaz"),
                       "sabitle": cfg.get("sabitle") or [], "gizli": cfg.get("gizli") or [],
                       "donem": cfg.get("donem") if cfg.get("donem") in DONEMLER else 30}

    def device_scores(self, days):
        """Bu cihazda dönem içinde dinlenen ana türler ({tür: dinleme}) ve açıklaması."""
        scores = since(self.history["cihaz"], days)
        return (scores, "bu cihaz") if scores else (self.counts, "bu cihaz, tüm zamanlar (dönemde dinleme yok)")

    def account_scores(self, days):
        """Spotify'ın kendi dönemiyse onun ilk 50 parçasının puanı; değilse biriken son çalınanlar geçmişi,
        geçmiş dönemi kapsamıyor ya da boşsa dönemi kapsayan en kısa Spotify dönemi."""
        note = ""
        if days not in WINDOWS:
            buckets = self.history["hesap"]
            if buckets and int(min(buckets, key=int)) <= hour_now() - days * 24:
                scores = since(buckets, days)
                if scores:
                    return scores, "Spotify geçmişi, tüm cihazlar"
                note = " (dönemde dinleme yok)"
            else:
                note = " (hesabı yeniden bağla)" if self.need_login else " (geçmiş birikiyor)"
        window = next(w for d, w in WINDOWS.items() if days <= d)
        return self.top_windows.get(window, {}), f"Spotify'ın {WINDOW_TEXT[window]} ilk 50 parçası{note}"

    def write_state(self):
        days = self.config["donem"]
        scores, text = self.device_scores(days)
        st = {"mode": self.config["mode"], "donem": days, "current": self.current,
              "top_cihaz": ranked(scores), "counts": self.counts}
        if self.top_windows is not None:  # hesap bağlı değilse anahtarlar yok
            hesap, hesap_text = self.account_scores(days)
            st.update(top_hesap=ranked(hesap), hesap_donemler=self.top_windows, izin_eksik=self.need_login)
            if self.config["mode"] == "hesap":  # istatistik seçili kaynaktan
                scores, text = hesap, hesap_text
        total = sum(scores.values())
        rows = [[g, round(100 * scores[g] / total)] for g in ranked(scores)]
        st["istatistik"] = {"aciklama": text, "turler": [r for r in rows if r[1]]}  # %1'in altı gösterilmez
        st["menu"] = menu_for(self.config, st)
        save(STATE, st)

    def genre_for(self, artist, album, title):
        sub = CAT["artist_sub"].get(norm(artist))
        if sub:  # listedeki sanatçı: önbellek ve ağ yok, liste değişince hemen geçerli
            return sub
        key = f"{artist}\t{album}"
        with self.lock:
            genre = self.cache.get(key)
        if genre == GENEL or genre in CAT["family"] or genre in CAT["parent"]:
            return genre
        # Kayıt yok ya da eski sürümün aile adı. Ağ sorgusu kilit dışında: arka plandaki sıralama
        # 50 parçayı sorgularken çalan şarkının türü beklemesin.
        genre = classify(artist, title)
        with self.lock:
            self.cache[key] = genre
            save(CACHE, self.cache)
        return genre

    def track_genre(self, t):
        """Spotify parçasının ana türü; Genel ya da tür alınamadıysa None."""
        try:
            genre = self.genre_for(t["artists"][0]["name"], t["album"]["name"], t["name"])
        except (OSError, ValueError, KeyError) as e:  # en çok dinlenenlerde sonraki güncellemede tekrar denenir
            print(f"{t['artists'][0]['name']} - {t['name']}: tür alınamadı ({e})", flush=True)
            return None
        return None if genre == GENEL else main_genre(genre)

    def refresh_spotify(self, top):
        """Arka planda: son çalınanların yenilerini hesap geçmişine ekler; top ise Spotify'ın 3 dönemindeki en çok
        dinlenen 50 parçayı da puanlar (1. parça 50 puan, 50. parça 1 puan). Ağ hatasında False."""
        try:
            token = access_token(self.spotify)
            recent = recently_played(token)
            tops = {w: spotify_get(token, f"me/top/tracks?time_range={w}&limit=50")["items"]
                    for w in WINDOWS.values()} if top else {}
        except (OSError, ValueError, KeyError) as e:
            print(f"Spotify'dan alınamadı ({e}); 400 ya da 401 ise tekrar --login yap", flush=True)
            return False
        last = self.history.get("hesap_son", 0)
        plays = [(ts, self.track_genre(i["track"])) for i in recent or []
                 if (ts := datetime.fromisoformat(i["played_at"]).timestamp()) > last]
        windows = {}
        for w, items in tops.items():
            score = windows[w] = {}
            for rank, t in enumerate(items):
                genre = self.track_genre(t)
                if genre:
                    score[genre] = score.get(genre, 0) + len(items) - rank

        with self.lock:  # ağ ve tür bulma kilit dışında
            self.need_login = recent is None
            self.top_windows.update(windows)
            if plays:
                for ts, genre in plays:
                    if genre:
                        add_play(self.history["hesap"], ts, genre)
                self.history["hesap_son"] = max(ts for ts, _ in plays)
                save(HISTORY, self.history)
            self.write_state()
        msg = f"Spotify: {len(plays)} yeni dinleme"
        if top:
            msg += ", ~4 haftada en çok dinlenen: " + ", ".join(ranked(windows["short_term"])[:5])
        if recent is None:
            msg += " (son çalınanlar izni yok, --login gerekli)"
        print(msg, flush=True)
        return True


    def on_track(self, track, artist, title, album):
        """Çalan şarkı değişti (track: parça kimliği; reklamda "/ad/" ya da ":ad:" içerir)."""
        if not artist or track == self.track or "/ad/" in track or ":ad:" in track:
            return
        self.track = track
        current = self.engine.current()
        try:
            genre = self.genre_for(artist, album, title)  # ağ sorgusu kilit dışında
        except (OSError, ValueError, KeyError) as e:
            print(f"{artist} - {title}: tür alınamadı ({e}), preset değişmedi", flush=True)
            genre = None
        with self.lock:
            if genre and genre != GENEL:
                self.counts[main_genre(genre)] = self.counts.get(main_genre(genre), 0) + 1
                add_play(self.history["cihaz"], time.time(), main_genre(genre))
            genre = genre or current
            locked = locked_preset()
            target = locked or genre
            print(f"{artist} - {title}: {genre}" + (f" (kilit: {locked})" if locked else ""), flush=True)
            if not self.engine.has(target):  # alt türün dosyası yoksa ana türünkine, o da yoksa Genel'e
                fallback = main_genre(target) if self.engine.has(main_genre(target)) else GENEL
                print(f"{target} preseti yok, {fallback} kullanılıyor", flush=True)
                target = fallback
            if target != current:
                self.engine.apply(target)
            self.current = {"genre": genre, "preset": target, "track": f"{artist} - {title}", "locked": bool(locked)}
            save(HISTORY, self.history)
            self.write_state()

    def reload_config(self):
        """config.json değişti (menü yazdı): ayarlar yeniden okunur, menü yeniden hesaplanır."""
        with self.lock:
            self.read_config()
            self.write_state()
        print(f"config.json değişti, mod: {self.config['mode']}", flush=True)

    def run_spotify(self):
        """Hesap bağlıysa arka plan iş parçacığında: son çalınanlar yarım saatte bir, en çok dinlenenler 6 saatte
        bir; hata olursa sonraki turda tekrar."""
        top_at = float("-inf")
        while True:
            top = time.monotonic() - top_at >= 6 * 3600
            try:
                if self.refresh_spotify(top) and top:
                    top_at = time.monotonic()
            except Exception:  # beklenmeyen hata döngüyü durdurmasın; günlüğe yazılır, sonraki turda tekrar
                traceback.print_exc()
            time.sleep(1800)
