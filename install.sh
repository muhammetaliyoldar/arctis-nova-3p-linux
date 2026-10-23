#!/bin/bash
# SteelSeries Arctis Nova 3P Wireless - Ubuntu/PipeWire Bluetooth düzeltmeleri
# Normal kullanıcı olarak çalıştır (sudo ile DEĞİL); gerektiğinde sudo kendisi sorulur.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)/files"
PRESET="Ana - HipHop House"

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }

if [ "$(id -u)" -eq 0 ]; then
    echo "Bu scripti sudo ile değil, normal kullanıcı olarak çalıştır." >&2
    exit 1
fi

# 1) Realtek rtw88 WiFi/BT kombo kartı: firmware LPS deep modundan çıkamıyor,
#    WiFi/BT coexistence bozulup ses cızırtılı/kesik geliyor. Sadece bu kartlarda gerekli.
if [ -d /sys/module/rtw88_core ]; then
    say "Realtek rtw88 WiFi kartı bulundu, güç tasarrufu düzeltmesi kuruluyor (sudo gerekli)"
    sudo install -m 644 "$DIR/modprobe/rtw88.conf" /etc/modprobe.d/rtw88.conf
    NEED_REBOOT=1
else
    say "rtw88 WiFi kartı yok, sürücü düzeltmesi atlandı (bu bilgisayarda gerekmiyor)"
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
    say "EasyEffects presetleri kuruluyor: $EE_DIR/output"
    mkdir -p "$EE_DIR/output" "$EE_DIR/autoload/output"
    cp "$DIR"/easyeffects/output/*.json "$EE_DIR/output/"

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
else
    warn "EasyEffects kurulu değil, presetler atlandı (kurmak için: sudo apt install easyeffects lsp-plugins)"
fi

# 5) Ayarları uygula. EasyEffects açıkken WirePlumber yeniden başlarsa
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
[ -n "$NEED_REBOOT" ] && warn "WiFi sürücü ayarının devreye girmesi için bilgisayarı yeniden başlat."
exit 0
