// Üst bar menüsü: panelde yüklü preset (yoksa çalan tür); menüde servisin hesapladığı satırlar (en çok dinlenen 5 tür, Genel,
// listede yoksa çalan tür) ve EasyEffects'te yüklü preset listede yoksa en altta o. Her satırdaki kilit o
// preseti sabitler: tür ne olursa olsun sonraki şarkılar o presette çalar.
// Sıralamayı ve istatistiği spotify-genre-preset servisi state.json'a yazar; kilit dosyası kilitli presetin adını
// tutar. "Kaynak", "Dönem", "Menüde sabitle" ve "Menüde gizle" config.json'a yazar; servis onu izleyip menüyü
// yeniden hesaplar.
import Clutter from 'gi://Clutter';
import GLib from 'gi://GLib';
import Gio from 'gi://Gio';
import GObject from 'gi://GObject';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';

const APP = 'spotify-genre-preset';
const STATE_DIR = GLib.build_filenamev([GLib.get_user_state_dir(), APP]);
const STATE = GLib.build_filenamev([STATE_DIR, 'state.json']);
const LOCK = GLib.build_filenamev([STATE_DIR, 'kilit']);
const CONFIG_DIR = GLib.build_filenamev([GLib.get_user_config_dir(), APP]);
const CONFIG = GLib.build_filenamev([CONFIG_DIR, 'config.json']);
const SPOTIFY = GLib.build_filenamev([CONFIG_DIR, 'spotify.json']);
const GENRES = GLib.build_filenamev([GLib.get_user_data_dir(), APP, 'genres.json']);
const EE_PRESET = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', 'ee-preset']);
const SERVICE = GLib.build_filenamev([GLib.get_home_dir(), '.local', 'bin', APP]);
const EE_SCHEMA = 'com.github.wwmm.easyeffects';
const GENEL = 'Genel';
const MODES = [
    ['cihaz', 'Bu cihazdaki dinlemelerim'],
    ['hesap', 'Spotify hesabım (tüm cihazlar)'],
];
const DONEMLER = [[1, 'Son 1 gün'], [7, 'Son 1 hafta'], [30, 'Son 1 ay'], [90, 'Son 3 ay'], [180, 'Son 6 ay'],
    [365, 'Son 1 yıl']];

function readText(path) {
    try {
        const [, bytes] = Gio.File.new_for_path(path).load_contents(null);
        return new TextDecoder().decode(bytes);
    } catch (e) {
        if (!e.matches?.(Gio.IOErrorEnum, Gio.IOErrorEnum.NOT_FOUND))
            logError(e, `arctis-preset-menu: ${path} okunamadı`);
        return null;
    }
}

function readJson(path) {
    const text = readText(path);
    try {
        return text === null ? null : JSON.parse(text);
    } catch (e) {
        logError(e, `arctis-preset-menu: ${path} bozuk`);
        return null;
    }
}

// config.json yoksa: Spotify bağlıysa hesap, değilse cihaz modu
function readConfig() {
    const mode = GLib.file_test(SPOTIFY, GLib.FileTest.EXISTS) ? 'hesap' : 'cihaz';
    return {mode, sabitle: [], gizli: [], donem: 30, ...readJson(CONFIG)};
}

function writeConfig(config) {
    GLib.mkdir_with_parents(CONFIG_DIR, 0o755);
    GLib.file_set_contents(CONFIG, `${JSON.stringify(config, null, 2)}\n`);
}

function openLogin() {
    // giriş bitince ya da hata verince terminal hemen kapanmasın, sonuç okunabilsin
    const argv = ['bash', '-c', '"$0" --login; read -rp "Kapatmak için Enter\'a basın"', SERVICE];
    if (GLib.find_program_in_path('gnome-terminal'))
        Gio.Subprocess.new(['gnome-terminal', '--', ...argv], Gio.SubprocessFlags.NONE);
    else if (GLib.find_program_in_path('x-terminal-emulator'))
        Gio.Subprocess.new(['x-terminal-emulator', '-e', ...argv], Gio.SubprocessFlags.NONE);
    else
        Main.notify('Spotify hesabını bağla', `Bir terminalde çalıştırın: ${SERVICE} --login`);
}

const Indicator = GObject.registerClass(
class Indicator extends PanelMenu.Button {
    _init(settings) {
        super._init(0.5, 'Arctis Preset'); // 0.5: menü simgenin ortasından açılır
        this._settings = settings;
        this._rows = [];
        this._rowsKey = null;

        const box = new St.BoxLayout({style_class: 'panel-status-menu-box'});
        this._icon = new St.Icon({style_class: 'system-status-icon'});
        this._label = new St.Label({y_align: Clutter.ActorAlign.CENTER});
        box.add_child(this._icon);
        box.add_child(this._label);
        this.add_child(box);

        this._section = new PopupMenu.PopupMenuSection();
        this.menu.addMenuItem(this._section);
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        this._source = new PopupMenu.PopupSubMenuMenuItem('Kaynak');
        this.menu.addMenuItem(this._source);
        this._donem = new PopupMenu.PopupSubMenuMenuItem('Dönem');
        this.menu.addMenuItem(this._donem);
        this._stats = new PopupMenu.PopupSubMenuMenuItem('İstatistik');
        this.menu.addMenuItem(this._stats);
        // tür listeleri: config[key]'deki türler işaretli; en fazla max tür, fazlasında en eski seçim düşer.
        // Sabitlenen tür menüde en az dinlenenin yerine geçer (servis hesaplar).
        this._lists = [['sabitle', 'Menüde sabitle', 5], ['gizli', 'Menüde gizle', Infinity]].map(([key, text, max]) => {
            const submenu = new PopupMenu.PopupSubMenuMenuItem(text);
            this.menu.addMenuItem(submenu);
            return {key, max, submenu, names: null, items: new Map()};
        });

        // GNOME boş menüyü açmıyor (open-state-changed de gelmiyor); satırları baştan doldur
        this._update();
        this.menu.connect('open-state-changed', (_menu, open) => {
            if (open) {
                this._update();
                this._fillSubmenus();
            }
        });
        this._settings?.connectObject('changed::last-used-output-preset', () => this._update(), this);
        this._monitors = [[STATE, () => this._update()], [LOCK, () => this._refresh()]].map(([path, onChange]) => {
            const monitor = Gio.File.new_for_path(path).monitor_file(Gio.FileMonitorFlags.NONE, null);
            monitor.connectObject('changed', (_monitor, file, _other, event) => {
                // atomik yazımda geçici dosyanın olayları da gelir; sadece bu dosyanın son hâline bak
                if (file.get_path() === path && (event === Gio.FileMonitorEvent.CHANGES_DONE_HINT ||
                    event === Gio.FileMonitorEvent.DELETED))
                    onChange();
            }, this);
            return monitor;
        });
    }

    _onDestroy() {
        for (const monitor of this._monitors)
            monitor.cancel();
        super._onDestroy();
    }

    _locked() {
        return readText(LOCK)?.trim() || null;
    }

    _apply(name) {
        Gio.Subprocess.new([EE_PRESET, name], Gio.SubprocessFlags.NONE);
    }

    _lock(name) {
        if (name) {
            GLib.mkdir_with_parents(STATE_DIR, 0o755);
            GLib.file_set_contents(LOCK, name);
            this._apply(name);
        } else if (this._locked()) {
            Gio.File.new_for_path(LOCK).delete(null);
        }
        this._refresh();
    }

    _refresh() {
        const locked = this._locked();
        this._icon.icon_name = locked ? 'changes-prevent-symbolic' : 'audio-headphones-symbolic';
        for (const {name, icon} of this._rows)
            icon.icon_name = name === locked ? 'changes-prevent-symbolic' : 'changes-allow-symbolic';
    }

    _update() {
        const state = readJson(STATE);
        const loaded = this._settings?.get_string('last-used-output-preset') ?? '';
        // elle seçilen preset de yazsın: menüdeki noktayla aynı
        this._label.text = loaded || (state?.current?.genre ?? '');
        this._label.visible = this._label.text !== '';

        const names = state?.menu ?? [...(readJson(GENRES)?.defaults ?? []), GENEL];
        if (loaded && !names.includes(loaded))
            names.push(loaded);

        // aynı satırları yeniden kurma: menü açıkken üzerindeki satır yok olmasın
        const key = JSON.stringify([names, loaded]);
        if (key !== this._rowsKey) {
            this._rowsKey = key;
            // silinecek satır fare altındaysa üst menü onu etkin sanmaya devam eder (Gjs-CRITICAL); önce bıraktır
            for (const {item} of this._rows)
                item.active = false;
            this._section.removeAll();
            this._rows = [];
            for (const name of names) {
                const item = new PopupMenu.PopupBaseMenuItem();
                item.setOrnament(name === loaded ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
                item.add_child(new St.Label({text: name, x_expand: true, y_align: Clutter.ActorAlign.CENTER}));
                const icon = new St.Icon({style_class: 'popup-menu-icon'});
                const lockButton = new St.Button({child: icon, can_focus: true, accessible_name: `${name} kilidi`});
                // Kilit düğmesi: bu preseti kilitle ya da kilidini aç (St.Button olayı durdurur, satır etkinleşmez)
                lockButton.connect('clicked', () => this._lock(this._locked() === name ? null : name));
                item.add_child(lockButton);
                // Satıra tıklama: preseti uygula; kilit varsa bu presete taşınır
                item.connect('activate', () => (this._locked() ? this._lock(name) : this._apply(name)));
                this._section.addMenuItem(item);
                this._rows.push({name, icon, item});
            }
        }
        this._refresh();
    }

    _fillSubmenus() {
        const genres = readJson(GENRES);
        const config = readConfig();
        const state = readJson(STATE);

        this._fillChoice(this._source, MODES, 'mode', config);
        if (config.mode === 'hesap' && !GLib.file_test(SPOTIFY, GLib.FileTest.EXISTS))
            this._source.menu.addAction('Spotify hesabını bağla…', openLogin).setOrnament(PopupMenu.Ornament.NONE);
        else if (state?.izin_eksik) // eski girişte son çalınanlar izni yok
            this._source.menu.addAction('Spotify hesabını yeniden bağla…', openLogin).setOrnament(PopupMenu.Ornament.NONE);
        this._fillChoice(this._donem, DONEMLER, 'donem', config);
        this._fillStats(state);

        const names = (genres?.genres ?? []).map(g => g.name).sort((a, b) => a.localeCompare(b, 'tr'));
        for (const list of this._lists)
            this._fillList(list, names, config);
    }

    // tek seçimli alt menü: config[key] değeri noktalı; tıklama config.json'a yazar
    _fillChoice(submenu, options, key, config) {
        submenu.menu.removeAll();
        for (const [value, text] of options) {
            const item = new PopupMenu.PopupMenuItem(text);
            item.setOrnament(config[key] === value ? PopupMenu.Ornament.DOT : PopupMenu.Ornament.NONE);
            // menü açıkken listeler değişmiş olabilir; yazmadan önce dosyayı yeniden oku
            item.connect('activate', () => writeConfig({...readConfig(), [key]: value}));
            submenu.menu.addMenuItem(item);
        }
    }

    // servisin hesapladığı dönem ve kaynakta ana türlerin yüzdesi
    _fillStats(state) {
        const stats = state?.istatistik;
        const donem = DONEMLER.find(([days]) => days === state?.donem)?.[1];
        this._stats.label.text = donem ? `İstatistik · ${donem}` : 'İstatistik';
        this._stats.menu.removeAll();
        const info = text => this._stats.menu.addMenuItem(new PopupMenu.PopupMenuItem(text, {reactive: false}));
        if (!stats)
            return info('Tür takibi servisi henüz yazmadı');
        info(stats.aciklama);
        if (!stats.turler.length)
            info('Bu dönemde dinleme yok');
        for (const [name, pct] of stats.turler) {
            const item = new PopupMenu.PopupMenuItem(name, {reactive: false});
            item.label.x_expand = true;
            item.add_child(new St.Label({text: `%${pct}`, y_align: Clutter.ActorAlign.CENTER}));
            this._stats.menu.addMenuItem(item);
        }
    }

    _fillList(list, names, config) {
        const key = names.join('\n');
        if (key !== list.names) {
            list.names = key;
            list.submenu.menu.removeAll();
            list.items.clear();
            if (!names.length)
                list.submenu.menu.addMenuItem(new PopupMenu.PopupMenuItem('Tür listesi bulunamadı', {reactive: false}));
            for (const name of names) {
                const item = new PopupMenu.PopupMenuItem(name);
                // activate sinyali yayılmadığı için menü kapanmaz, art arda tür seçilebilir (PopupSwitchMenuItem gibi)
                item.activate = () => this._toggle(list, name);
                list.submenu.menu.addMenuItem(item);
                list.items.set(name, item);
            }
        }
        this._mark(list, config[list.key]);
    }

    // seçili türü kaldırır, değilse ekler; liste doluysa eklenen türe yer açmak için en eski seçim düşer
    _toggle(list, name) {
        const config = readConfig();
        const old = config[list.key];
        const selected = old.includes(name) ? old.filter(n => n !== name) : [...old, name].slice(-list.max);
        writeConfig({...config, [list.key]: selected});
        this._mark(list, selected);
    }

    _mark(list, selected) {
        for (const [name, item] of list.items)
            item.setOrnament(selected.includes(name) ? PopupMenu.Ornament.CHECK : PopupMenu.Ornament.NONE);
    }
});

export default class ArctisPresetMenu extends Extension {
    enable() {
        const schema = Gio.SettingsSchemaSource.get_default().lookup(EE_SCHEMA, true);
        this._indicator = new Indicator(schema ? new Gio.Settings({schema_id: EE_SCHEMA}) : null);
        Main.panel.addToStatusArea(this.uuid, this._indicator);
    }

    disable() {
        this._indicator?.destroy();
        this._indicator = null;
    }
}
