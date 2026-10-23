#!/bin/bash
# install.sh ile kurulan her şeyi kaldırır (EasyEffects presetleri hariç).

systemctl --user disable --now arctis-autoconnect.service 2>/dev/null
rm -f ~/.config/systemd/user/arctis-autoconnect.service ~/.local/bin/arctis-autoconnect.sh
systemctl --user daemon-reload

rm -f ~/.config/wireplumber/bluetooth.lua.d/51-arctis-a2dp-only.lua \
      ~/.config/wireplumber/wireplumber.conf.d/51-arctis-a2dp-only.conf
rm -f ~/.config/easyeffects/autoload/output/bluez_output.*:headphone-output.json \
      ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/autoload/output/bluez_output.*:headphone-output.json

if [ -f /etc/modprobe.d/rtw88.conf ] || [ -f /etc/NetworkManager/conf.d/wifi-powersave-off.conf ]; then
    sudo rm -f /etc/modprobe.d/rtw88.conf /etc/NetworkManager/conf.d/wifi-powersave-off.conf \
        && echo "rtw88 ve WiFi güç tasarrufu ayarları kaldırıldı (yeniden başlatınca geçerli)"
fi
# /etc/modprobe.d/btusb.conf bilerek bırakılıyor: Bluetooth adaptörünün uykuya
# geçmemesi her durumda zararsız ve çoğu sistemde zaten istenen ayar.

# Preset kısayolları
rm -f ~/.local/bin/ee-preset
KB=org.gnome.settings-daemon.plugins.media-keys
KB_PATH=/org/gnome/settings-daemon/plugins/media-keys/custom-keybindings
for id in ee-preset-1 ee-preset-2 ee-preset-3 ee-preset-4 ee-preset-next; do
    gsettings reset-recursively "$KB.custom-keybinding:$KB_PATH/$id/" 2>/dev/null
done
gsettings set $KB custom-keybindings "$(gsettings get $KB custom-keybindings | python3 -c "
import ast,sys; l=ast.literal_eval(sys.stdin.read().replace('@as ','')); print([p for p in l if '/ee-preset-' not in p])")"

systemctl --user restart wireplumber
if pgrep -x easyeffects >/dev/null; then
    sleep 3; easyeffects -q; sleep 2
    setsid -f easyeffects --gapplication-service >/dev/null 2>&1
fi
echo "Kaldırıldı. Presetler EasyEffects'te ve GNOME uzantıları (Music Pill, Preset Selector) yerinde duruyor; istersen Uzantılar uygulamasından kaldırabilirsin."
