"""Windows ön yüzü: Spotify'da çalan şarkının türüne göre Equalizer APO presetini değiştirir; tepside menü.

Çalan şarkı Windows'un medya oturumlarından (SMTC, winrt-Windows.Media.Control) 2 saniyede bir okunur. Preset
Equalizer APO'nun config.txt'sine yazılır, APO dosya değişince kendisi yeniden yükler; ilk satırdaki yorum yüklü
presetin adıdır (kurulum eski config.txt'yi config.txt.arctis-yedek'e alır). Presetler kurulum klasöründeki
presets\\ (repodan çalışırken files/equalizer-apo/). Tür bulma, Spotify hesabı, geçmiş, dönem, istatistik ve menü
ortak çekirdekte (files/core). Kurulum: install.ps1 (%LOCALAPPDATA%\\spotify-genre-preset). pythonw'da konsol
olmadığı için çıktı aynı klasördeki gunluk.txt'ye yazılır.

Kullanım: pythonw spotify-genre-preset.pyw          (tepsi uygulaması; install.ps1 Başlangıç'a ekler)
          python spotify-genre-preset.pyw --login  (Spotify hesabını bağlar)
          python spotify-genre-preset.pyw --dene   (çalan şarkıyı, türünü ve uygulanan preseti bir kez yazar)
"""
import asyncio
import functools
import os
import subprocess
import sys
import threading
import time
import winreg

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, "..", "core")]  # kurulu, repo
import genre_core as core  # noqa: E402
import tray_menu as tray  # noqa: E402

PRESETS = os.path.join(HERE, "presets")  # kurulu
if not os.path.isdir(PRESETS):
    PRESETS = os.path.join(HERE, "..", "equalizer-apo")  # repo
HEADER = "# spotify-genre-preset: "


class EqualizerAPO:
    def __init__(self):
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\EqualizerAPO") as key:
            self.config = os.path.join(winreg.QueryValueEx(key, "ConfigPath")[0], "config.txt")

    def current(self):
        try:
            with open(self.config, encoding="utf-8") as fh:
                line = fh.readline()
        except (FileNotFoundError, UnicodeDecodeError):  # kurulumdan önceki config.txt UTF-8 olmayabilir
            return ""
        return line[len(HEADER):].strip() if line.startswith(HEADER) else ""

    def has(self, name):
        return os.path.exists(os.path.join(PRESETS, name + ".txt"))

    def apply(self, name):
        with open(os.path.join(PRESETS, name + ".txt"), encoding="utf-8") as fh:
            text = HEADER + name + "\n" + fh.read()
        for attempt in range(5):  # APO dosyayı o an okuyorsa yazma kısa süre reddedilebilir
            try:
                with open(self.config, "w", encoding="utf-8") as fh:  # yerinde yazım: APO değişikliği görür
                    fh.write(text)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.2)


def smtc_reader():
    """Spotify'ın medya oturumundan (kimlik, sanatçı, şarkı, albüm) okuyan fonksiyon; oturum yoksa None döner.
    Çağıran iş parçacığında çalışır (COM MTA)."""
    from winrt.runtime import init_apartment, MTA
    import winrt.windows.foundation  # noqa: F401  dönen IAsyncOperation ve liste türleri için
    import winrt.windows.foundation.collections  # noqa: F401
    from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as Manager

    init_apartment(MTA)
    loop = asyncio.new_event_loop()
    manager = loop.run_until_complete(Manager.request_async())

    async def read():
        session = next((s for s in manager.get_sessions() if "spotify" in s.source_app_user_model_id.lower()), None)
        if not session:
            return None
        props = await session.try_get_media_properties_async()
        if not props or not props.artist:  # boş oturum ya da reklam
            return None
        artist = tray.first_artist(props.artist)
        return f"{artist}\t{props.title}\t{props.album_title}", artist, props.title, props.album_title

    return lambda: loop.run_until_complete(read())


def to_pystray(items):
    import pystray
    out = []
    for it in items:
        if it is None:
            out.append(pystray.Menu.SEPARATOR)
            continue
        action = (pystray.Menu(*to_pystray(it.items)) if it.items is not None else
                  functools.partial(tray.run_action, it.action) if it.action else None)  # partial: pystray (icon, item) verir
        out.append(pystray.MenuItem(it.text, action, checked=None if it.checked is None else (lambda _, c=it.checked: c),
                                    radio=it.radio, enabled=it.enabled))
    return out


def icon_image(locked):
    from PIL import Image, ImageDraw
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    color = (230, 140, 30, 255) if locked else (40, 170, 160, 255)  # kilitliyken turuncu
    draw.arc((10, 6, 54, 50), 180, 360, fill=color, width=7)  # kafa bandı
    draw.rounded_rectangle((4, 28, 20, 58), 5, fill=color)  # kulaklıklar
    draw.rounded_rectangle((44, 28, 60, 58), 5, fill=color)
    return img


def main():
    import pystray

    f = core.Follower(EqualizerAPO())
    f.write_state()
    restart = []

    def login():
        """Spotify girişi yeni bir konsolda (Client ID sorulabilir); konsol kapanınca uygulama yeniden başlar ki
        hesap okunsun (Linux'ta servis yeniden başlatılıyor)."""
        python = os.path.join(os.path.dirname(sys.executable), "python.exe")

        def run():
            # cmd /c tüm komutu bir çift tırnakla daha sarınca içteki tırnaklı yollar bozulmuyor
            subprocess.run(f'cmd /c ""{python}" "{os.path.abspath(__file__)}" --login & pause"',
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            restart.append(True)
            icon.stop()

        threading.Thread(target=run, daemon=True).start()

    def refresh():
        locked = core.locked_preset()
        icon.icon = icon_image(bool(locked))
        icon.title = f"Arctis: {f.engine.current() or '-'}" + (" (kilitli)" if locked else "")  # en fazla 127 harf
        icon.update_menu()

    menu = pystray.Menu(lambda: to_pystray(tray.items(f, login) + [None, tray.Item("Çıkış", icon.stop)]))
    icon = pystray.Icon(core.APP, icon_image(False), "Arctis", menu)

    def setup(icon):
        icon.visible = True
        threading.Thread(target=lambda: tray.follow(f, smtc_reader(), refresh), daemon=True).start()
        if f.spotify:
            threading.Thread(target=f.run_spotify, daemon=True).start()

    icon.run(setup)
    if restart:
        subprocess.Popen([sys.executable, os.path.abspath(__file__)])


if __name__ == "__main__":
    if sys.stdout is None:  # pythonw: konsol yok, çıktı günlüğe
        os.makedirs(core.STATE_DIR, exist_ok=True)
        sys.stdout = sys.stderr = open(os.path.join(core.STATE_DIR, "gunluk.txt"), "w", encoding="utf-8", buffering=1)
    if sys.argv[1:2] == ["--login"]:
        core.login(sys.argv[2] if len(sys.argv) > 2 else
                   (core.load(core.SPOTIFY, None) or {}).get("client_id") or core.ask_client_id())
    elif sys.argv[1:2] == ["--dene"]:
        tray.dene(core.Follower(EqualizerAPO()), smtc_reader())
    else:
        main()
