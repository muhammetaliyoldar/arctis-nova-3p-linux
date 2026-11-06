"""macOS ön yüzü: Spotify'da çalan şarkının türüne göre CamillaDSP EQ presetini değiştirir; menü çubuğunda menü.

Ses zinciri: sistem çıkışı BlackHole 2ch, CamillaDSP oradan alıp EQ'lu sesi kulaklığa (adında "Arctis" geçen çıkış
cihazı: Bluetooth ya da USB-C alıcı) çalar. Kulaklık sistem çıkışı olunca (bağlanınca macOS kendisi seçer) CamillaDSP
başlar ve çıkış BlackHole'a alınır; kulaklık gidince çıkış önceki cihaza döner; kullanıcı başka bir çıkış seçerse
karışılmaz. Çıkışlar SwitchAudioSource ile okunur ve değiştirilir, 2 saniyede bir. CamillaDSP bu uygulamanın alt
süreci; config'i veri klasöründeki camilladsp.yml: ilk satır yüklü preset, devices o anki kulaklık, filters ve pipeline
presets/<ad>.yml (repodan çalışırken files/camilladsp/; make_presets.py üretir). Preset değişince dosya yazılır ve
SIGHUP gönderilir (yalnız filtre değiştiği için kesintisiz). Çalan şarkı Spotify'ın AppleScript'inden 2 saniyede bir
okunur. Tür bulma, Spotify hesabı, geçmiş, dönem, istatistik ve menü ortak çekirdekte (files/core). Kurulum:
install-mac.sh (~/Library/Application Support/spotify-genre-preset, LaunchAgent; çıktı gunluk.txt'ye).

Kullanım: python3 spotify-genre-preset.py          (menü çubuğu uygulaması; install-mac.sh oturum açılışına ekler)
          python3 spotify-genre-preset.py --login  (Spotify hesabını bağlar)
          python3 spotify-genre-preset.py --dene   (çalan şarkıyı, türünü ve uygulanan preseti bir kez yazar)
"""
import json
import os
import shlex
import signal
import subprocess
import sys
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "core")]  # kurulu, repo
import genre_core as core  # noqa: E402
import tray_menu as tray  # noqa: E402

PRESETS = os.path.join(HERE, "presets")  # kurulu
if not os.path.isdir(PRESETS):
    PRESETS = os.path.join(HERE, "..", "camilladsp")  # repo
CAMILLADSP = os.path.join(HERE, "camilladsp")  # install-mac.sh indirir
CONFIG = os.path.join(core.DATA_DIR, "camilladsp.yml")
HEADER = "# spotify-genre-preset: "
BLACKHOLE = "BlackHole 2ch"
LABEL = "com.github.muhammetaliyoldar.spotify-genre-preset"  # install-mac.sh'deki LaunchAgent
SPOTIFY_SCRIPT = """
if application "Spotify" is running then
    tell application "Spotify"
        if player state is not stopped then
            set t to current track
            return (id of t) & tab & (artist of t) & tab & (name of t) & tab & (album of t)
        end if
    end tell
end if
return ""
"""


def run(*cmd, stdin=None):
    """Komutun çıktısı; hata olursa mesajı (SwitchAudioSource hatayı stdout'a yazar) istisnada."""
    r = subprocess.run(cmd, input=stdin, capture_output=True, encoding="utf-8")
    if r.returncode:
        raise RuntimeError(f"{cmd[0]}: {(r.stderr or r.stdout).strip()}")
    return r.stdout


def outputs():
    return run("SwitchAudioSource", "-a", "-t", "output").splitlines()


def current_output():
    return run("SwitchAudioSource", "-c", "-t", "output").strip()


def set_output(name):
    run("SwitchAudioSource", "-s", name, "-t", "output")
    print(f"Ses çıkışı: {name}", flush=True)


class CamillaDSP:
    def __init__(self):
        os.makedirs(core.DATA_DIR, exist_ok=True)
        self.proc = None
        self.loaded = None  # bu süreçte yazılan preset (--dene ayrı süreçte dosyayı değiştirse de doğru kalsın)
        self.device = None  # CamillaDSP'nin çaldığı kulaklık
        self.rate = 48000
        self.normal = None  # kulaklık gidince dönülecek çıkış: en son seçili olan, kulaklık ve BlackHole dışı
        self.failed = None  # CamillaDSP'nin açılamadığı kulaklık: çıkış değişene kadar yeniden denenmez
        self.lock = threading.RLock()  # menü (ana iş parçacığı) ve takip döngüsü aynı anda çağırır

    def current(self):
        if self.loaded:
            return self.loaded
        try:
            with open(CONFIG, encoding="utf-8") as fh:
                line = fh.readline()
        except FileNotFoundError:
            return ""
        return line[len(HEADER):].strip() if line.startswith(HEADER) else ""

    def has(self, name):
        return os.path.exists(os.path.join(PRESETS, name + ".yml"))

    def write(self, name):
        with open(os.path.join(PRESETS, name + ".yml"), encoding="utf-8") as fh:
            filters = fh.read()
        with open(CONFIG, "w", encoding="utf-8") as fh:  # json.dumps: YAML'da da geçerli tırnaklı metin
            fh.write(f"{HEADER}{name}\ndevices:\n  samplerate: {self.rate}\n  chunksize: 1024\n"
                     f"  enable_rate_adjust: true\n"
                     f"  capture: {{type: CoreAudio, channels: 2, device: {json.dumps(BLACKHOLE)}}}\n"
                     f"  playback: {{type: CoreAudio, channels: 2, device: {json.dumps(self.device)}}}\n{filters}")
        self.loaded = name

    def apply(self, name):
        with self.lock:
            self.write(name)
            if self.proc:
                self.proc.send_signal(signal.SIGHUP)  # config'i yeniden okur; yalnız filtre değiştiyse kesintisiz

    def start(self, device):
        """CamillaDSP'yi BlackHole -> device için başlatır; 48 kHz açılmazsa 44.1 kHz dener (Bluetooth cihazının hızı
        değişmeyebilir). İlk 2 saniyede kapanırsa açılamamış sayılır."""
        self.stop()
        self.device = device
        name = self.current() if self.has(self.current()) else core.GENEL
        for rate in (48000, 44100):
            self.rate = rate
            self.write(name)
            self.proc = subprocess.Popen([CAMILLADSP, "-l", "warn", CONFIG])
            try:
                code = self.proc.wait(2)
            except subprocess.TimeoutExpired:
                print(f"CamillaDSP: {BLACKHOLE} -> {device}, {rate} Hz, {name}", flush=True)
                return True
            print(f"CamillaDSP {device} için {rate} Hz ile açılamadı (çıkış kodu {code})", flush=True)
        self.proc = None
        return False

    def stop(self):
        if self.proc:
            self.proc.terminate()
            self.proc.wait(5)
            self.proc = None

    def leave_blackhole(self, outs):
        """Çıkışı kulaklığa, o yoksa önceki cihaza, o da yoksa BlackHole dışındaki ilk cihaza alır."""
        back = next((d for d in (self.device, self.normal, *outs) if d in outs and d != BLACKHOLE), None)
        if back:
            set_output(back)

    def sync(self):
        """Sistem çıkışı kuralı (2 saniyede bir): kulaklık seçilince CamillaDSP ona çalar ve çıkış BlackHole'a alınır;
        kulaklık gidince önceki çıkışa dönülür; kullanıcı başka çıkış seçtiyse CamillaDSP durur, karışılmaz."""
        outs, current = outputs(), current_output()
        arctis = [d for d in outs if "arctis" in d.lower()]
        with self.lock:
            if self.proc and self.proc.poll() is not None:  # kulaklık kopunca CamillaDSP 0 ile kendisi kapanır
                print(f"CamillaDSP kapandı (çıkış kodu {self.proc.returncode})", flush=True)
                self.proc = None
            if current != BLACKHOLE and current not in arctis:
                self.normal, self.failed = current, None
                self.stop()
                return
            target = current if current in arctis else self.device if self.device in arctis else next(iter(arctis), None)
            if target is None:  # BlackHole seçili ama kulaklık yok
                self.stop()
                self.failed = None
                self.leave_blackhole(outs)
                return
            if target == self.failed:
                return
            if not self.proc or target != self.device:
                if not self.start(target):
                    self.failed = target
                    if current == BLACKHOLE:
                        set_output(target)  # EQ'suz da olsa ses kulaklıktan gelsin
                    return
            if current != BLACKHOLE:
                set_output(BLACKHOLE)

    def close(self):
        """Uygulama kapanırken: CamillaDSP durur; çıkış BlackHole'daysa geri alınır ki ses kesilmesin."""
        with self.lock:
            self.stop()
            if current_output() == BLACKHOLE:
                self.leave_blackhole(outputs())


def spotify_track():
    """Spotify'da çalan (kimlik, sanatçı, şarkı, albüm); Spotify kapalıysa ya da durmuşsa None."""
    out = run("osascript", stdin=SPOTIFY_SCRIPT).rstrip("\n")
    if not out:
        return None
    track, artist, title, album = out.split("\t")
    return track, tray.first_artist(artist), title, album


def to_rumps(items, click):
    """tray_menu öğe ağacını rumps menü öğelerine çevirir; tıklamada click(eylem). Eylemsiz öğe gri görünür (alt
    menüsü olan hariç)."""
    import rumps
    out = []
    for it in items:
        if it is None:
            out.append(None)  # rumps ayırıcıya çevirir
            continue
        mi = rumps.MenuItem(it.text, callback=(lambda _sender, a=it.action: click(a)) if it.action else None)
        mi.state = int(bool(it.checked))
        for sub in to_rumps(it.items or [], click):
            mi.add(sub)
        out.append(mi)
    return out


def forget(menu):
    """rumps her menü öğesini sınıf düzeyindeki bir sözlükte tutar; menü her yeniden kurulduğunda eskileri silinmezse
    bellek büyür (rumps 0.4.0 iç yapısı; install-mac.sh bu sürümü kurar)."""
    import rumps
    for item in menu.values():
        if isinstance(item, rumps.MenuItem):
            rumps.rumps.NSApp._ns_to_py_and_callback.pop(item._menuitem, None)
            forget(item)


def login():
    """Spotify girişi Terminal'de (Client ID sorulabilir); --login bitince uygulamayı yeniden başlatır."""
    script = os.path.join(core.STATE_DIR, "spotify-giris.command")
    with open(script, "w", encoding="utf-8") as fh:
        fh.write(f"#!/bin/bash\n{shlex.quote(sys.executable)} {shlex.quote(os.path.abspath(__file__))} --login\n")
    os.chmod(script, 0o755)
    run("open", script)  # .command dosyası Terminal'de açılır


def main():
    import rumps
    from AppKit import NSApplication, NSApplicationActivationPolicyAccessory

    subprocess.run(["pkill", "-f", CONFIG])  # önceki örnek çökmüşse kalan CamillaDSP ikinci kez çalmasın
    engine = CamillaDSP()
    f = core.Follower(engine)
    f.write_state()
    changed = threading.Event()
    changed.set()

    def click(action):
        tray.run_action(action)
        changed.set()  # menü takip döngüsünü beklemeden yenilensin

    def refresh(_timer):
        """Ana iş parçacığında, saniyede bir: bir şey değiştiyse başlık ve menü yeniden kurulur."""
        if not changed.is_set():
            return
        changed.clear()
        app.title = ("🔒 " if core.locked_preset() else "🎧 ") + (engine.current() or "-")
        forget(app.menu)
        app.menu.clear()
        app.menu.update(to_rumps(tray.items(f, login) + [None, tray.Item("Çıkış", rumps.quit_application)], click))

    def read_track():
        engine.sync()  # kulaklık bağlandı mı, gitti mi: şarkıyla aynı döngüde
        return spotify_track()

    app = rumps.App(core.APP, title="🎧", quit_button=None)
    rumps.events.before_quit.register(engine.close)
    signal.signal(signal.SIGTERM, lambda *_: rumps.quit_application())  # launchctl bootout: çıkış geri alınsın
    rumps.Timer(refresh, 1).start()
    threading.Thread(target=tray.follow, args=(f, read_track, changed.set), daemon=True).start()
    if f.spotify:
        threading.Thread(target=f.run_spotify, daemon=True).start()
    NSApplication.sharedApplication().setActivationPolicy_(NSApplicationActivationPolicyAccessory)  # Dock'ta simge yok
    app.run()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--login"]:
        core.login(sys.argv[2] if len(sys.argv) > 2 else
                   (core.load(core.SPOTIFY, None) or {}).get("client_id") or core.ask_client_id())
        subprocess.run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{LABEL}"], capture_output=True)
        print("Menü çubuğu uygulaması çalışıyorsa yeniden başlatıldı.")
    elif sys.argv[1:2] == ["--dene"]:
        tray.dene(core.Follower(CamillaDSP()), spotify_track)
    else:
        main()
