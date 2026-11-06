"""Windows ve macOS ön yüzlerinin ortak parçası: menü ve şarkı takip döngüsü (Linux'ta GNOME uzantısı ve servis var).

Menü GNOME uzantısındakiyle aynı (files/gnome/arctis-preset-menu@muhammetaliyoldar/extension.js): servisin
hesapladığı satırlar (en çok dinlenen 5 tür, Genel, çalan alt tür) ve yüklü preset; satıra tıklama preseti uygular,
kilit varsa kilidi o presete taşır. GNOME'daki satır başı kilit düğmesinin yerine "Kilitle" alt menüsü var. Kaynak,
Dönem, İstatistik, Menüde sabitle ve Menüde gizle aynı. items() araç takımından bağımsız bir öğe ağacı döner; ön yüz
onu kendi menüsüne çevirir (Windows pystray, macOS rumps). Ayarlar config.json'a yazılır ve aynı süreçteki
Follower'a hemen bildirilir (Linux'ta uzantı yazar, servis dosyayı izler).
"""
import os
import time
import traceback
from collections import namedtuple

import genre_core as core

# None ayırıcıdır. checked None: işaretlenemez öğe; items: alt menü
Item = namedtuple("Item", "text action checked radio items enabled", defaults=(None, None, False, None, True))
MODES = (("cihaz", "Bu cihazdaki dinlemelerim"), ("hesap", "Spotify hesabım (tüm cihazlar)"))
DONEMLER = ((1, "Son 1 gün"), (7, "Son 1 hafta"), (30, "Son 1 ay"), (90, "Son 3 ay"), (180, "Son 6 ay"),
            (365, "Son 1 yıl"))
LISTS = (("sabitle", "Menüde sabitle", 5), ("gizli", "Menüde gizle", None))  # en fazla kaç tür; None: sınırsız


def first_artist(artists):
    """Spotify birden çok sanatçıyı "A, B" diye tek metinde veriyor; tür ilk sanatçıdan bulunur (Linux'ta MPRIS
    listesinin ilki gibi)."""
    return artists.split(", ")[0]


def read_config():
    """config.json; yoksa ya da eksikse menünün varsayılanları (Spotify bağlıysa hesap, değilse cihaz modu)."""
    cfg = {"mode": "hesap" if os.path.exists(core.SPOTIFY) else "cihaz", "sabitle": [], "gizli": [], "donem": 30}
    try:
        cfg.update(core.load(core.CONFIG, {}))
    except ValueError as e:
        print(f"config.json okunamadı ({e}), varsayılanlar kullanılıyor", flush=True)
    return cfg


def set_config(f, key, value):
    core.save(core.CONFIG, {**read_config(), key: value})  # menü açıkken dosya değişmiş olabilir: yeniden okunur
    f.reload_config()


def toggle(f, key, name, limit):
    """Listedeki türü çıkarır, yoksa ekler; liste doluysa en eski seçim düşer."""
    old = read_config()[key]
    set_config(f, key, [n for n in old if n != name] if name in old else (old + [name])[-(limit or len(old) + 1):])


def lock(f, name):
    """name presetini kilitler ve uygular; None kilidi açar."""
    if name:
        os.makedirs(core.STATE_DIR, exist_ok=True)
        with open(core.LOCK, "w", encoding="utf-8") as fh:
            fh.write(name)
        f.engine.apply(name)
    elif os.path.exists(core.LOCK):
        os.remove(core.LOCK)


def choose(f, name):
    lock(f, name) if core.locked_preset() else f.engine.apply(name)


def items(f, login):
    """Menü ağacı. login: "Spotify hesabını bağla…" tıklanınca çağrılır."""
    st = core.load(core.STATE, {})
    cfg = read_config()
    loaded, locked = f.engine.current(), core.locked_preset()
    names = list(st.get("menu") or [*core.CAT["defaults"], core.GENEL])  # servis henüz yazmadıysa varsayılan 5
    if loaded and loaded not in names:
        names.append(loaded)

    source = [Item(text, lambda v=v: set_config(f, "mode", v), cfg["mode"] == v, True) for v, text in MODES]
    if cfg["mode"] == "hesap" and not os.path.exists(core.SPOTIFY):
        source.append(Item("Spotify hesabını bağla…", login))
    elif st.get("izin_eksik"):  # eski girişte son çalınanlar izni yok
        source.append(Item("Spotify hesabını yeniden bağla…", login))

    stats = st.get("istatistik")
    if not stats:
        stat_rows = [Item("Tür takibi henüz yazmadı", enabled=False)]
    else:
        stat_rows = [Item(stats["aciklama"], enabled=False)] + (
            [Item(f"{g}   %{pct}", enabled=False) for g, pct in stats["turler"]]
            or [Item("Bu dönemde dinleme yok", enabled=False)])
    donem = dict(DONEMLER).get(st.get("donem"))

    genres = sorted((g["name"] for g in core.CAT["genres"]), key=core.norm)
    lists = [Item(text, items=[Item(g, lambda k=key, g=g, m=limit: toggle(f, k, g, m), g in cfg[key]) for g in genres])
             for key, text, limit in LISTS]
    return [
        *(Item(n, lambda n=n: choose(f, n), n == loaded, True) for n in names),
        None,
        Item("Kilitle", items=[Item(n, lambda n=n: lock(f, None if core.locked_preset() == n else n), n == locked)
                               for n in names]),
        Item("Kaynak", items=source),
        Item("Dönem", items=[Item(text, lambda d=d: set_config(f, "donem", d), cfg["donem"] == d, True)
                             for d, text in DONEMLER]),
        Item(f"İstatistik · {donem}" if donem else "İstatistik", items=stat_rows),
        *lists,
    ]


def run_action(action, *_):
    """Menü eylemi; hata menü döngüsünü düşürmesin, günlüğe yazılsın."""
    try:
        action()
    except Exception:
        traceback.print_exc()


def mtime(path):
    try:
        return os.stat(path).st_mtime_ns
    except FileNotFoundError:
        return None


def follow(f, read_track, on_change, interval=2.0):
    """Arka plan iş parçacığında: çalan şarkıyı aralıkla okur (read_track: (kimlik, sanatçı, şarkı, albüm) ya da
    Spotify kapalıysa None) ve Follower'a verir; menüyü etkileyen bir şey değişince on_change() (menü ve başlık)."""
    shown, last_error = None, None
    while True:
        try:
            track = read_track()
            if track:
                f.on_track(*track)
            now = (mtime(core.STATE), mtime(core.LOCK), mtime(core.CONFIG), f.engine.current())
            if now != shown:
                shown = now
                on_change()
            last_error = None
        except Exception as e:  # aynı hata her turda günlüğü doldurmasın
            if repr(e) != last_error:
                last_error = repr(e)
                traceback.print_exc()
        time.sleep(interval)


def dene(f, read_track):
    """--dene: çalan şarkıyı, bulunan türü ve uygulanan preseti bir kez yazar."""
    track = read_track()
    if not track:
        print("Spotify'da çalan şarkı yok (Spotify kapalı ya da hiç şarkı açılmadı)")
        return
    f.on_track(*track)  # "sanatçı - şarkı: tür" satırını yazar
    print(f"Yüklü preset: {f.engine.current() or '(yok)'}")
