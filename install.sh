#!/bin/bash
# SteelSeries Arctis Nova 3P Wireless - Ubuntu/PipeWire Bluetooth düzeltmeleri,
# EasyEffects presetleri, hızlı preset geçişi ve Dynamic Music Pill. Hangilerinin
# kurulacağını başta sorar. Normal kullanıcı olarak çalıştır (sudo ile DEĞİL);
# gerektiğinde sudo kendisi sorulur.
set -e

DIR="$(cd "$(dirname "$0")" && pwd)/files"
PRESET="Genel"                                 # açılışta ve kulaklık bağlanınca yüklenen
LEGACY_PRESETS=("Ana - HipHop House" "Rap - HipHop" "Genel Muzik" "Rap" "Tekno - Rave" "House - Disco")  # eski sürümlerin adları

say()  { printf '\033[1;32m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!!\033[0m %s\n' "$*"; }
ask()  { local c; read -rp $'\033[1;36m??\033[0m '"$1 [E/h] " c; [[ ! "$c" =~ ^[HhNn] ]]; }  # Enter = evet

if [ "$(id -u)" -eq 0 ]; then
    echo "Bu scripti sudo ile değil, normal kullanıcı olarak çalıştır." >&2
    exit 1
fi

echo "Hangi parçalar kurulsun? (Enter = evet, h = hayır)"
ask "Bağlantı düzeltmeleri: sadece SBC codec, güç tasarrufu kapalı, otomatik bağlanma" && DO_BT=1
[ -n "$DO_BT" ] && ask "  Bluetooth mikrofonu kapatılsın mı? (test edilen ayar; açık kalırsa kopmalar geri gelebilir)" && MIC_OFF=1
ask "Ses presetleri: EasyEffects, tür presetleri ve Ctrl+Alt kısayolları" && DO_EE=1
[ -n "$DO_EE" ] && ask "  Spotify'da çalan şarkının türüne göre preset kendiliğinden değişsin mi? (sanatçı ve şarkı adı Deezer ve MusicBrainz'e sorulur)" && DO_GENRE=1
if [ -n "$DO_GENRE" ]; then
    # Menüdeki "en çok dinlenen 5" nereden gelsin; sonradan menüdeki "Kaynak"tan değiştirilebilir
    [ -f ~/.config/spotify-genre-preset/spotify.json ] && MODE_DEFAULT=3 || MODE_DEFAULT=2
    echo "    Menüdeki 'en çok dinlenen 5' nereden gelsin?"
    echo "      1) Sabit 5 tür (menüden seçersin)  2) Bu bilgisayardaki dinlemelerim  3) Spotify hesabım (tüm cihazlar, Premium)"
    read -rp $'\033[1;36m??\033[0m '"  Seçim [$MODE_DEFAULT]: " c || c=""
    case "${c:-$MODE_DEFAULT}" in 1) MODE=sabit ;; 3) MODE=hesap ;; *) MODE=cihaz ;; esac
fi
command -v gnome-shell >/dev/null && ask "Dynamic Music Pill: üst barda şarkı kontrolü ve görselleştirici" && DO_PILL=1

# 0) Gerekli paketler: curl (uzantı indirme), EasyEffects + LSP eklentileri
[ -n "$DO_EE$DO_PILL" ] && ! command -v curl >/dev/null && { say "curl kuruluyor (sudo gerekli)"; sudo apt-get install -y curl; }
if [ -n "$DO_EE" ] && ! command -v easyeffects >/dev/null && ! flatpak info com.github.wwmm.easyeffects >/dev/null 2>&1; then
    if command -v apt-get >/dev/null; then
        say "EasyEffects ve LSP eklentileri kuruluyor (sudo gerekli)"
        sudo apt-get install -y easyeffects lsp-plugins-lv2
    else
        warn "apt yok: EasyEffects'i ve lsp-plugins'i dağıtımının paket yöneticisiyle kur, sonra scripti tekrar çalıştır"
    fi
fi

if [ -n "$DO_BT" ]; then
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

    # 2) WirePlumber: sadece SBC; mikrofon kapatılırsa ayrıca sadece A2DP. Format sürüme göre
    #    değişiyor. İki dosyadan biri kurulur, diğeri silinir (ikisi birden yüklenirse mikrofon kapalı kalır).
    if [ -n "$MIC_OFF" ]; then
        WP_FILE=51-arctis-a2dp-only; WP_OLD=51-arctis-sbc-only
    else
        WP_FILE=51-arctis-sbc-only; WP_OLD=51-arctis-a2dp-only
    fi
    WP_VER=$(wireplumber --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+' | head -1)
    case "$WP_VER" in
        0.4)
            say "WirePlumber 0.4 -> Lua ayarı kuruluyor ($WP_FILE)"
            rm -f ~/.config/wireplumber/bluetooth.lua.d/$WP_OLD.lua
            install -Dm 644 "$DIR/wireplumber/$WP_FILE.lua" \
                ~/.config/wireplumber/bluetooth.lua.d/$WP_FILE.lua
            ;;
        "")
            warn "WirePlumber bulunamadı, Bluetooth codec ayarı atlandı"
            ;;
        *)
            say "WirePlumber $WP_VER -> .conf ayarı kuruluyor ($WP_FILE)"
            rm -f ~/.config/wireplumber/wireplumber.conf.d/$WP_OLD.conf
            install -Dm 644 "$DIR/wireplumber/$WP_FILE.conf" \
                ~/.config/wireplumber/wireplumber.conf.d/$WP_FILE.conf
            ;;
    esac

    # 3) Oturum açılışında otomatik bağlanma servisi
    say "Otomatik bağlanma servisi kuruluyor"
    install -Dm 755 "$DIR/systemd/arctis-autoconnect.sh" ~/.local/bin/arctis-autoconnect.sh
    install -Dm 644 "$DIR/systemd/arctis-autoconnect.service" ~/.config/systemd/user/arctis-autoconnect.service
    systemctl --user daemon-reload
    systemctl --user enable arctis-autoconnect.service
fi

# 4) EasyEffects presetleri + kulaklık bağlanınca otomatik yükleme
if [ -n "$DO_EE" ] && flatpak info com.github.wwmm.easyeffects >/dev/null 2>&1; then
    EE_DIR=~/.var/app/com.github.wwmm.easyeffects/config/easyeffects
elif [ -n "$DO_EE" ] && command -v easyeffects >/dev/null; then
    EE_DIR=~/.config/easyeffects
fi

if [ -n "$EE_DIR" ]; then
    say "EasyEffects presetleri kuruluyor: Genel + $(ls "$DIR"/easyeffects/output/*.json | grep -vc '/Genel.json$') tür"
    mkdir -p "$EE_DIR/output" "$EE_DIR/autoload/output"
    cp "$DIR"/easyeffects/output/*.json "$EE_DIR/output/"
    install -Dm 644 "$DIR/genres.json" ~/.local/share/spotify-genre-preset/genres.json  # menü, kısayollar ve servis okur

    # Bu reponun eski sürümündeki presetler silinmez, kenara alınır; 100 türlük sürümden ana türlere
    # katılanların adları genres.json "merged"da
    mapfile -t MERGED < <(python3 -c 'import json, sys; print("\n".join(json.load(open(sys.argv[1]))["merged"]))' \
                          "$DIR/genres.json")
    MOVED=0
    for p in "${LEGACY_PRESETS[@]}" "${MERGED[@]}"; do
        if [ -f "$EE_DIR/output/$p.json" ]; then
            mkdir -p "$EE_DIR/eski-presetler"
            mv "$EE_DIR/output/$p.json" "$EE_DIR/eski-presetler/"
            MOVED=$((MOVED + 1))
        fi
    done
    [ "$MOVED" -gt 0 ] && say "$MOVED eski preset kenara alındı: $EE_DIR/eski-presetler/"

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

    # 5) Hızlı preset geçişi: Ctrl+Alt+1..7 = üst bar menüsünün satırları, Ctrl+Alt+0 = sıradaki
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
    for i in 1 2 3 4 5 6 7; do
        add_shortcut "ee-preset-$i" "EasyEffects: menüdeki $i. satır" "$HOME/.local/bin/ee-preset $i" "<Control><Alt>$i"
    done
    add_shortcut "ee-preset-next" "EasyEffects: sıradaki preset" \
        "$HOME/.local/bin/ee-preset next" "<Control><Alt>0"

    # 5b) Spotify'da çalan şarkının türüne göre otomatik preset
    if [ -n "$DO_GENRE" ]; then
        say "Spotify tür takibi kuruluyor"
        install -Dm 755 "$DIR/bin/spotify-genre-preset" ~/.local/bin/spotify-genre-preset
        install -Dm 644 "$DIR/systemd/spotify-genre-preset.service" ~/.config/systemd/user/spotify-genre-preset.service
        rm -f ~/.cache/spotify-genre-preset.json   # tür eşlemesi değişmiş olabilir, baştan sorulsun
        python3 - "$MODE" ~/.config/spotify-genre-preset/config.json ~/.local/share/spotify-genre-preset/genres.json \
            ~/.local/state/spotify-genre-preset/kilit <<'PY'
import json, os, sys
mode, path, genres, lock = sys.argv[1:5]
cat = json.load(open(genres))
old = json.load(open(path)) if os.path.exists(path) else {}
sabit = []
for name in old.get("sabit") or cat["defaults"]:  # 100 türlük sürümün adları ana türe çevrilir
    name = cat["merged"].get(name, name)
    if name not in sabit:
        sabit.append(name)
os.makedirs(os.path.dirname(path), exist_ok=True)
json.dump({"mode": mode, "sabit": sabit}, open(path, "w"), ensure_ascii=False, indent=1)
if os.path.exists(lock):  # kilitli preset de
    name = open(lock).read().strip()
    if name in cat["merged"]:
        open(lock, "w").write(cat["merged"][name])
PY
        if [ "$MODE" = hesap ] && [ ! -f ~/.config/spotify-genre-preset/spotify.json ] && [ -t 0 ]; then
            say "Spotify hesabını bağlama (README: Spotify hesabını bağlama)"
            ~/.local/bin/spotify-genre-preset --login || warn "Giriş yapılmadı; sonra: spotify-genre-preset --login"
        fi
        systemctl --user daemon-reload
        systemctl --user enable spotify-genre-preset.service
        systemctl --user restart spotify-genre-preset.service
    elif [ -f ~/.config/systemd/user/spotify-genre-preset.service ]; then
        say "Spotify tür takibi kaldırılıyor"
        systemctl --user disable --now spotify-genre-preset.service
        rm -f ~/.config/systemd/user/spotify-genre-preset.service ~/.local/bin/spotify-genre-preset
    fi
elif [ -n "$DO_EE" ]; then
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
disable_extension() {  # uuid
    gsettings set org.gnome.shell enabled-extensions \
        "$(gsettings get org.gnome.shell enabled-extensions | python3 -c "
import ast,sys; l=ast.literal_eval(sys.stdin.read().replace('@as ','')); print([e for e in l if e != '$1'])")"
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
    if [ -n "$DO_PILL" ]; then
        say "Dynamic Music Pill kuruluyor"
        if install_extension "$PILL"; then
            dconf load /org/gnome/shell/extensions/dynamic-music-pill/ < "$DIR/gnome/dynamic-music-pill.ini"
            enable_extension "$PILL"
        fi
    fi
    if [ -n "$EE_DIR" ]; then
        SELECTOR="eepresetselector@ulville.github.io"
        MENU="arctis-preset-menu@muhammetaliyoldar"
        EXT_DIR=~/.local/share/gnome-shell/extensions
        if [ -n "$DO_GENRE" ]; then
            # Kendi menümüz (kilit + en çok dinlenen 5 + Genel) tüm presetleri listeleyen Selector'ın yerine geçer
            say "Preset menüsü kuruluyor (kilit + en çok dinlenen 5 preset + Genel)"
            mkdir -p "$EXT_DIR" && rm -rf "$EXT_DIR/$MENU" && cp -r "$DIR/gnome/$MENU" "$EXT_DIR/"
            enable_extension "$MENU"
            disable_extension "$SELECTOR"
        else
            [ -d "$EXT_DIR/$MENU" ] && { disable_extension "$MENU"; rm -rf "${EXT_DIR:?}/$MENU"; }
            say "EasyEffects Preset Selector kuruluyor"
            install_extension "$SELECTOR" && enable_extension "$SELECTOR"
        fi
    fi
fi

# 7) Ayarları uygula. EasyEffects açıkken WirePlumber yeniden başlarsa
#    ses bağlantıları kopuyor, o yüzden EasyEffects de yeniden başlatılır.
if [ -n "$DO_BT" ]; then
    say "WirePlumber yeniden başlatılıyor (kulaklık birkaç saniye kopabilir)"
    systemctl --user restart wireplumber
    if pgrep -x easyeffects >/dev/null; then
        sleep 3
        easyeffects -q || true
        sleep 2
        setsid -f easyeffects --gapplication-service >/dev/null 2>&1
    fi
    systemctl --user start arctis-autoconnect.service --no-block
fi

echo
say "Kurulum tamam."
[ -n "$EE_DIR" ] && echo "    Preset geçişi: Ctrl+Alt+1..7 üst bar menüsündeki satırlar | Ctrl+Alt+0 sıradaki"
[ -n "$EE_DIR" ] && [ -n "$DO_GENRE" ] && echo "    Spotify tür takibini izlemek için: journalctl --user -u spotify-genre-preset -f"
[ -n "$EE_DIR" ] && [ "$MODE" = hesap ] && [ ! -f ~/.config/spotify-genre-preset/spotify.json ] && \
    echo "    Spotify hesabı bağlı değil: spotify-genre-preset --login (README: Spotify hesabını bağlama)"
[ -n "$DO_PILL$EE_DIR" ] && echo "    Üst bardaki uzantılar görünmezse oturumu kapatıp aç."
[ -n "$NEED_REBOOT" ] && warn "WiFi sürücü ayarlarının devreye girmesi için bilgisayarı yeniden başlat."
exit 0
