#!/bin/bash
# macOS: Spotify'da çalan şarkının türüne göre CamillaDSP EQ preseti + menü çubuğu menüsü (Linux'taki tür takibinin
# aynısı). Ses zinciri: sistem çıkışı BlackHole 2ch -> CamillaDSP (EQ) -> kulaklık (Bluetooth ya da USB-C alıcı).
# Normal kullanıcı olarak çalıştır (sudo ile DEĞİL); BlackHole kurulurken yönetici şifresi sorulur:
#   bash install-mac.sh
# Önce: Homebrew kurulu olmalı (https://brew.sh).
set -euo pipefail
FILES="$(cd "$(dirname "$0")" && pwd)/files"
DIR="$HOME/Library/Application Support/spotify-genre-preset"  # genre_core.app_paths() ile aynı klasör
LABEL=com.github.muhammetaliyoldar.spotify-genre-preset       # spotify-genre-preset.py'deki LABEL
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
CAMILLADSP=v4.1.3
PY="$DIR/venv/bin/python3"

say() { printf '\033[32m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[33m!! %s\033[0m\n' "$*"; }

[ "$(uname)" = Darwin ] || { warn "Bu script macOS için (Ubuntu: install.sh, Windows: install.ps1)."; exit 1; }
[ "$(id -u)" -ne 0 ] || { warn "sudo ile değil, normal kullanıcı olarak çalıştır."; exit 1; }
command -v brew >/dev/null || { warn "Homebrew yok: https://brew.sh adresindeki komutla kur, sonra bu scripti tekrar çalıştır."; exit 1; }

# 1) BlackHole (sanal ses kartı), SwitchAudioSource (çıkış cihazını değiştirir), Python 3.12 (çekirdek 3.11+ ister)
say 'Homebrew paketleri kuruluyor: blackhole-2ch, switchaudio-osx, python@3.12'
brew install switchaudio-osx python@3.12
brew install --cask blackhole-2ch
BREW="$(brew --prefix)"
if ! "$BREW/bin/SwitchAudioSource" -a -t output | grep -x 'BlackHole 2ch' >/dev/null; then  # -q değil: pipefail
    warn "BlackHole 2ch ses cihazlarında görünmüyor: Mac'i yeniden başlat, sonra bu scripti tekrar çalıştır."
    exit 1
fi

# 2) Program dosyaları, presetler, CamillaDSP (Homebrew'da yok: GitHub sürümü) ve rumps (menü çubuğu)
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true  # çalışan eski sürüm: CamillaDSP durur, çıkış geri alınır
say "Kuruluyor: $DIR"
mkdir -p "$DIR/presets"
rm -f "$DIR/presets/"*.yml  # katalogdan çıkan türler kalmasın
cp "$FILES/camilladsp/"*.yml "$DIR/presets/"
cp "$FILES/core/genre_core.py" "$FILES/core/tray_menu.py" "$FILES/genres.json" "$FILES/mac/spotify-genre-preset.py" "$DIR/"
rm -f "$HOME/Library/Caches/spotify-genre-preset.json"  # tür eşlemesi değişmiş olabilir, baştan sorulsun
ARCH=$([ "$(uname -m)" = arm64 ] && echo aarch64 || echo amd64)
say "CamillaDSP $CAMILLADSP indiriliyor ($ARCH)"
curl -fsSL "https://github.com/HEnquist/camilladsp/releases/download/$CAMILLADSP/camilladsp-macos-$ARCH.tar.gz" |
    tar xz -C "$DIR" camilladsp
[ -x "$PY" ] || "$(brew --prefix python@3.12)/bin/python3.12" -m venv "$DIR/venv"
say 'Python paketi kuruluyor: rumps 0.4.0'
"$PY" -m pip install --disable-pip-version-check -q rumps==0.4.0  # sürüm sabit: menü kodu iç yapısına dokunuyor

# 3) Spotify hesabı (menüdeki "en çok dinlenen 5" tüm cihazlardan gelsin); sonradan menüden de bağlanabilir
if [ ! -f "$DIR/spotify.json" ]; then
    read -r -p '?? Spotify hesabını bağlayalım mı? Menüdeki en çok dinlenen 5 tür tüm cihazlarından gelir (Premium). [E/h] ' c ||
        c=h  # terminal yoksa sorma
    case "$c" in
        [HhNn]*) ;;
        *) "$PY" "$DIR/spotify-genre-preset.py" --login || warn 'Giriş yapılmadı; sonra menüden: Kaynak > Spotify hesabını bağla' ;;
    esac
fi

# 4) Oturum açılışında başlat (LaunchAgent; menüden Çıkış'ta yeniden başlatılmaz, çökerse başlatılır) ve şimdi başlat
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>$LABEL</string>
    <key>ProgramArguments</key>
    <array><string>$PY</string><string>$DIR/spotify-genre-preset.py</string></array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key><string>$BREW/bin:/usr/bin:/bin:/usr/sbin:/sbin</string>
        <key>PYTHONUTF8</key><string>1</string>
    </dict>
    <key>RunAtLoad</key><true/>
    <key>KeepAlive</key><dict><key>SuccessfulExit</key><false/></dict>
    <key>ProcessType</key><string>Interactive</string>
    <key>StandardOutPath</key><string>$DIR/gunluk.txt</string>
    <key>StandardErrorPath</key><string>$DIR/gunluk.txt</string>
</dict>
</plist>
EOF
chmod 644 "$PLIST"
launchctl bootstrap "gui/$(id -u)" "$PLIST"
say 'Kuruldu: menü çubuğunda 🎧 ve yüklü preset (kilitliyken 🔒); tıklayınca menü.'
cat <<EOF
    - İlk açılışta macOS iki izin sorabilir, ikisine de izin ver: Python'un Spotify'ı denetlemesi (çalan şarkıyı
      okumak için) ve mikrofon erişimi (CamillaDSP sesi BlackHole'dan alıyor). Mikrofon izni yoksa kulaklıkta ses
      KESİLİR ve hata çıkmaz: Sistem Ayarları > Gizlilik ve Güvenlik > Mikrofon'da Python'u aç; listede yoksa
      tccutil reset Microphone, sonra launchctl kickstart -k gui/$(id -u)/$LABEL
    - Kulaklık (Bluetooth ya da USB-C alıcı) ses çıkışı olunca çıkış BlackHole'a alınır, EQ'lu ses kulaklığa gider;
      kulaklık gidince önceki çıkışa döner. Başka bir çıkış seçersen EQ devreden çıkar.
    - Ses tuşları EQ öncesi seviyeyi (BlackHole) değiştirir; kulaklığın kendi tekerleği her zaman çalışır.
    - SteelSeries GG ya da kulaklığın kendi EQ'su düz olmalı; yoksa EQ'lar toplanır.
    - Günlük: $DIR/gunluk.txt
    - Deneme (Spotify çalarken): "$PY" "$DIR/spotify-genre-preset.py" --dene
EOF
