#!/bin/bash
# Oturum açıldıktan sonra ilk 2 dakika Arctis Nova 3P'ye bağlanmayı dener.
# Kulaklık açılışta zaten açıksa ve kendisi bağlanmadıysa bağlantıyı bilgisayar kurar.
MAC=$(bluetoothctl devices | grep -i 'Arctis Nova 3P' | awk '{print $2}' | head -1)
[ -z "$MAC" ] && exit 0
for _ in $(seq 1 12); do
    bluetoothctl info "$MAC" | grep -q "Connected: yes" && exit 0
    bluetoothctl connect "$MAC" >/dev/null 2>&1
    sleep 10
done
