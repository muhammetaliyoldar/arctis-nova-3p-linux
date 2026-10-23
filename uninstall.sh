#!/bin/bash
# install.sh ile kurulan her şeyi kaldırır (EasyEffects presetleri hariç).

systemctl --user disable --now arctis-autoconnect.service 2>/dev/null
rm -f ~/.config/systemd/user/arctis-autoconnect.service ~/.local/bin/arctis-autoconnect.sh
systemctl --user daemon-reload

rm -f ~/.config/wireplumber/bluetooth.lua.d/51-arctis-a2dp-only.lua \
      ~/.config/wireplumber/wireplumber.conf.d/51-arctis-a2dp-only.conf
rm -f ~/.config/easyeffects/autoload/output/bluez_output.*:headphone-output.json \
      ~/.var/app/com.github.wwmm.easyeffects/config/easyeffects/autoload/output/bluez_output.*:headphone-output.json

if [ -f /etc/modprobe.d/rtw88.conf ]; then
    sudo rm -f /etc/modprobe.d/rtw88.conf && echo "rtw88 ayarı kaldırıldı (yeniden başlatınca geçerli)"
fi

systemctl --user restart wireplumber
if pgrep -x easyeffects >/dev/null; then
    sleep 3; easyeffects -q; sleep 2
    setsid -f easyeffects --gapplication-service >/dev/null 2>&1
fi
echo "Kaldırıldı. Presetler EasyEffects'te durmaya devam ediyor, istersen elle silebilirsin."
