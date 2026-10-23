#!/bin/bash
# SteelSeries Arctis Nova 3P Wireless - Ubuntu/PipeWire Bluetooth düzeltmeleri,
# EasyEffects presetleri, hızlı preset geçişi ve Dynamic Music Pill.
# Normal kullanıcı olarak çalıştır (sudo ile DEĞİL); gerektiğinde sudo kendisi sorulur.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)/files"
PRESET="Rap"                                   # kulaklık bağlanınca otomatik yüklenen
PRESETS=("Rap" "Tekno - Rave" "Deep House" "Genel")
LEGACY_PRESETS=("Ana - HipHop House" "Rap - HipHop" "Genel Muzik")

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
    echo "Bu scripti sudo ile değil, normal kullanıcı olarak çalıştır." >&2
    exit 1
fi

# 0) Gerekli paketler: curl (uzantı indirme), EasyEffects + LSP eklentileri
command -v curl >/dev/null || { say "curl kuruluyor (sudo gerekli)"; sudo apt-get install -y curl; }
if ! command -v easyeffects >/dev/null && ! flatpak info com.github.wwmm.easyeffects >/dev/null 2>&1; then
    if command -v apt-get >/dev/null; then
        say "EasyEffects ve LSP eklentileri kuruluyor (sudo gerekli)"
        sudo apt-get install -y easyeffects lsp-plugins-lv2
    else
        warn "apt yok: EasyEffects'i ve lsp-plugins'i dağıtımının paket yöneticisiyle kur, sonra scripti tekrar çalıştır"
    fi
fi

# 1) Güç tasarrufu
#    - btusb autosuspend: Bluetooth USB adaptörü uykuya geçip bağlantıyı düşürmesin (her bilgisayarda)
#    - rtw88 + NetworkManager: Realtek WiFi/BT kombo kartında firmware LPS deep modundan
#      çıkamıyor, WiFi/BT anten paylaşımı bozulup ses cızırtılı/kesik geliyor (sadece bu kartlarda)
say "Bluetooth USB güç tasarrufu kapatılıyor (sudo gerekli)"
sudo install -m 644 "$DIR/modprobe/btusb.conf" /etc/modprobe.d/btusb.conf
if [ -d /sys/module/rtw88_core ]; then
    say "Realtek rtw88 WiFi kartı bulundu: sürücü ve WiFi güç tasarrufu kapatılıyor"
    sudo install -m 644 "$DIR/modprobe/rtw88.conf" /etc/modprobe.d/rtw88.conf
    sudo install -m 644 "$DIR/networkmanager/wifi-powersave-off.conf" \
        /etc/NetworkManager/conf.d/wifi-powersave-off.conf
    NEED_REBOOT=1
else
    say "rtw88 WiFi kartı yok, WiFi düzeltmeleri atlandı (bu bilgisayarda gerekmiyor)"
fi

# 2) WirePlumber: sadece SBC + sadece A2DP. Format sürüme göre değişiyor.
WP_VER=$(wireplumber --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
case "$WP_VER" in
    0.4)
        say "WirePlumber 0.4 -> Lua ayarı kuruluyor"
        install -Dm 644 "$DIR/wireplumber/51-arctis-a2dp-only.lua" \
            ~/.config/wireplumber/bluetooth.lua.d/51-arctis-a2dp-only.lua
        ;;
    "")
        warn "WirePlumber bulunamadı, Bluetooth codec ayarı atlandı"
        ;;
    *)
        say "WirePlumber $WP_VER -> .conf ayarı kuruluyor"
        install -Dm 644 "$DIR/wireplumber/51-arctis-a2dp-only.conf" \
            ~/.config/wireplumber/wireplumber.conf.d/51-arctis-a2dp-only.conf
        ;;
esac

# 3) Oturum açılışında otomatik bağlanma servisi
say "Otomatik bağlanma servisi kuruluyor"
install -Dm 755 "$DIR/systemd/arctis-autoconnect.sh" ~/.local/bin/arctis-autoconnect.sh
install -Dm 644 "$DIR/systemd/arctis-autoconnect.service" ~/.config/systemd/user/arctis-autoconnect.service
systemctl --user daemon-reload
systemctl --user enable arctis-autoconnect.service

# 4) EasyEffects presetleri + kulaklık bağlanınca otomatik yükleme
if flatpak info com.github.wwmm.easyeffects >/dev/null 2>&1; then
    EE_DIR=~/.var/app/com.github.wwmm.easyeffects/config/easyeffects
elif command -v easyeffects >/dev/null; then
    EE_DIR=~/.config/easyeffects
fi

if [ -n "$EE_DIR" ]; then
    say "EasyEffects presetleri kuruluyor: ${PRESETS[*]}"
    mkdir -p "$EE_DIR/output" "$EE_DIR/autoload/output"
    cp "$DIR"/easyeffects/output/*.json "$EE_DIR/output/"

    # Bu reponun eski sürümündeki presetler silinmez, kenara alınır
    for p in "${LEGACY_PRESETS[@]}"; do
        if [ -f "$EE_DIR/output/$p.json" ]; then
            mkdir -p "$EE_DIR/eski-presetler"
            mv "$EE_DIR/output/$p.json" "$EE_DIR/eski-presetler/"
            say "Eski preset kenara alındı: $EE_DIR/eski-presetler/$p.json"
        fi
    done

    MAC=$(bluetoothctl devices 2>/dev/null | grep -i 'Arctis Nova 3P' | awk '{print $2}' | head -1)
    if [ -n "$MAC" ]; then
        NODE="bluez_output.${MAC//:/_}.1"
        cat > "$EE_DIR/autoload/output/$NODE:headphone-output.json" <<EOF
{
    "device": "$NODE",
    "device-description": "Arctis Nova 3P Wireless",
    "device-profile": "headphone-output",
    "preset-name": "$PRESET"
}
EOF
        say "Kulaklık bağlanınca '$PRESET' otomatik yüklenecek"
    else
        warn "Kulaklık henüz eşleştirilmemiş: eşleştirdikten sonra scripti tekrar çalıştır (otomatik preset için)"
    fi

    # Oturum açılınca arka planda başlasın; pencere kapatılınca efektler kapanmasın
    if [ "$EE_DIR" = ~/.config/easyeffects ]; then
        install -Dm 644 "$DIR/easyeffects/autostart/easyeffects-service.desktop" \
            ~/.config/autostart/easyeffects-service.desktop
        gsettings set com.github.wwmm.easyeffects shutdown-on-window-close false 2>/dev/null || true
        gsettings set com.github.wwmm.easyeffects last-used-output-preset "$PRESET" 2>/dev/null || true
    fi

    # 5) Hızlı preset geçişi: Ctrl+Alt+1..4 ve Ctrl+Alt+0 (sıradaki)
    install -Dm 755 "$DIR/bin/ee-preset" ~/.local/bin/ee-preset
    say "Klavye kısayolları ekleniyor"
    KB=org.gnome.settings-daemon.plugins.media-keys
    KB_PATH=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings
    add_shortcut() {  # id, isim, komut, tuş
        local path="$KB_PATH/$1/"
        gsettings set "$KB.custom-keybinding:$path" name "$2"
        gsettings set "$KB.custom-keybinding:$path" command "$3"
        gsettings set "$KB.custom-keybinding:$path" binding "$4"
        gsettings set $KB custom-keybindings "$(gsettings get $KB custom-keybindings | python3 -c "
import ast,sys; l=ast.literal_eval(sys.stdin.read().replace('@as ','')); '$path' in l or l.append('$path'); print(l)")"
    }
    for i in "${!PRESETS[@]}"; do
        add_shortcut "ee-preset-$((i + 1))" "EasyEffects: ${PRESETS[$i]}" \
            "$HOME/.local/bin/ee-preset \"${PRESETS[$i]}\"" "<Control><Alt>$((i + 1))"
    done
    add_shortcut "ee-preset-next" "EasyEffects: sıradaki preset" \
        "$HOME/.local/bin/ee-preset next" "<Control><Alt>0"
else
    warn "EasyEffects kurulu değil, presetler atlandı"
fi

# 6) GNOME uzantıları: Dynamic Music Pill (üst barda şarkı kontrolü) ve
#    EasyEffects Preset Selector (üst barda preset menüsü)
install_extension() {  # uuid
    local uuid="$1" url tmp ver
    [ -d ~/.local/share/gnome-shell/extensions/"$uuid" ] && return 0
    ver=$(gnome-shell --version | grep -oE '[0-9]+' | head -1)
    url=$(curl -fsSL "https://extensions.gnome.org/extension-info/?uuid=$uuid&shell_version=$ver" \
          | python3 -c 'import json,sys; print(json.load(sys.stdin)["download_url"])' 2>/dev/null) || url=""
    if [ -z "$url" ]; then
        warn "$uuid bu GNOME sürümü ($ver) için bulunamadı, atlandı"
        return 1
    fi
    tmp=$(mktemp -d)
    curl -fsSL -o "$tmp/ext.zip" "https://extensions.gnome.org$url"
    gnome-extensions install --force "$tmp/ext.zip"
    rm -rf "$tmp"
}
enable_extension() {  # uuid -- yeni kurulan uzantı GNOME yeniden yüklenmeden görünmez,
                      # listeye ekleyip bir sonraki oturumda açılmasını garantile
    gnome-extensions enable "$1" 2>/dev/null || \
        gsettings set org.gnome.shell enabled-extensions \
            "$(gsettings get org.gnome.shell enabled-extensions | python3 -c "
import ast,sys; l=ast.literal_eval(sys.stdin.read().replace('@as ','')); '$1' in l or l.append('$1'); print(l)")"
}

if command -v gnome-shell >/dev/null; then
    PILL="dynamic-music-pill@andbal"
    say "Dynamic Music Pill kuruluyor"
    if install_extension "$PILL"; then
        dconf load /org/gnome/shell/extensions/dynamic-music-pill/ < "$DIR/gnome/dynamic-music-pill.ini"
        enable_extension "$PILL"
    fi
    if [ -n "$EE_DIR" ]; then
        SELECTOR="eepresetselector@ulville.github.io"
        say "EasyEffects Preset Selector kuruluyor"
        install_extension "$SELECTOR" && enable_extension "$SELECTOR"
    fi
fi

# 7) Ayarları uygula. EasyEffects açıkken WirePlumber yeniden başlarsa
#    ses bağlantıları kopuyor, o yüzden EasyEffects de yeniden başlatılır.
say "WirePlumber yeniden başlatılıyor (kulaklık birkaç saniye kopabilir)"
systemctl --user restart wireplumber
if pgrep -x easyeffects >/dev/null; then
    sleep 3
    easyeffects -q || true
    sleep 2
    setsid -f easyeffects --gapplication-service >/dev/null 2>&1
fi
systemctl --user start arctis-autoconnect.service --no-block

echo
say "Kurulum tamam."
echo "    Preset geçişi: Ctrl+Alt+1 Rap | Ctrl+Alt+2 Tekno - Rave | Ctrl+Alt+3 Deep House | Ctrl+Alt+4 Genel | Ctrl+Alt+0 sıradaki"
echo "    Üst bardaki uzantılar görünmezse oturumu kapatıp aç."
[ -n "$NEED_REBOOT" ] && warn "WiFi sürücü ayarlarının devreye girmesi için bilgisayarı yeniden başlat."
exit 0
