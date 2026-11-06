#!/bin/bash
# install-mac.sh'nin kurduklarını kaldırır: menü çubuğu uygulaması (LaunchAgent), CamillaDSP, program dosyaları ve
# presetler. Uygulama kapanırken ses çıkışını BlackHole'dan kulaklığa ya da önceki cihaza alır. Ayarlar, Spotify
# girişi ve dinleme geçmişi (config.json, spotify.json, state.json, gecmis.json) Linux'taki gibi bilerek bırakılıyor.
# Homebrew paketleri (BlackHole, SwitchAudioSource, Python) kaldırılmaz.
#   bash uninstall-mac.sh
DIR="$HOME/Library/Application Support/spotify-genre-preset"
LABEL=com.github.muhammetaliyoldar.spotify-genre-preset

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null
rm -f "$HOME/Library/LaunchAgents/$LABEL.plist" "$HOME/Library/Caches/spotify-genre-preset.json"
for p in venv presets __pycache__ camilladsp camilladsp.yml genre_core.py tray_menu.py genres.json \
         spotify-genre-preset.py spotify-giris.command kilit gunluk.txt; do
    rm -rf "${DIR:?}/$p"
done
if [ "$(SwitchAudioSource -c -t output 2>/dev/null)" = 'BlackHole 2ch' ]; then
    echo "!! Ses çıkışı hâlâ BlackHole 2ch (ses gelmez): menü çubuğundaki ses menüsünden kulaklığı ya da hoparlörü seç."
fi
echo "Kaldırıldı. Ayarlar ve dinleme geçmişi $DIR içinde duruyor; istersen klasörü silebilirsin."
