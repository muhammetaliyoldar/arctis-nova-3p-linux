# Windows: Spotify'da çalan şarkının türüne göre Equalizer APO preseti + tepsi menüsü (Linux'taki tür takibinin aynısı).
# Normal kullanıcı olarak çalıştır (yönetici olarak DEĞİL); APO klasörüne yazma izni için yönetici onayını kendisi ister:
#   powershell -ExecutionPolicy Bypass -File install.ps1
# Önce: Equalizer APO kurulu, Device Selector'da kulaklığın Bluetooth cihazı ve alıcının takıldığı her USB yolu
# (Windows her port için ayrı cihaz açar) işaretli ve bilgisayar yeniden başlatılmış olmalı.
# Dosya UTF-8 BOM'lu: Windows PowerShell 5.1 BOM'suz dosyadaki Türkçe harfleri bozuyor.
$ErrorActionPreference = 'Stop'
$Files = Join-Path $PSScriptRoot 'files'
$Dir = Join-Path $env:LOCALAPPDATA 'spotify-genre-preset'  # genre_core.app_paths() ile aynı klasör
$App = Join-Path $Dir 'spotify-genre-preset.pyw'
$Pythonw = Join-Path $Dir 'venv\Scripts\pythonw.exe'
$Shortcut = Join-Path ([Environment]::GetFolderPath('Startup')) 'Arctis Preset.lnk'

function Say($m) { Write-Host "==> $m" -ForegroundColor Green }
function Warn($m) { Write-Host "!! $m" -ForegroundColor Yellow }

# 1) Equalizer APO ve config klasörüne yazma izni
$Cfg = (Get-ItemProperty 'HKLM:\SOFTWARE\EqualizerAPO' -ErrorAction SilentlyContinue).ConfigPath
if (-not $Cfg) {
    Warn 'Equalizer APO bulunamadı. https://sourceforge.net/projects/equalizerapo/ adresinden kur, Device Selector''da kulaklığın Bluetooth ve USB alıcı cihazlarını işaretle, bilgisayarı yeniden başlat, sonra bu scripti tekrar çalıştır.'
    exit 1
}
try {
    [IO.File]::WriteAllText((Join-Path $Cfg 'yazma-denemesi.tmp'), '')
    Remove-Item (Join-Path $Cfg 'yazma-denemesi.tmp')
} catch {
    Say "Equalizer APO config klasörüne yazma izni veriliyor (yönetici onayı istenecek): $Cfg"
    $User = [Security.Principal.WindowsIdentity]::GetCurrent().Name
    try {
        $p = Start-Process icacls -ArgumentList "`"$Cfg`"", '/grant', "`"${User}:(OI)(CI)M`"" -Verb RunAs -Wait -PassThru -WindowStyle Hidden
    } catch {
        Warn 'Yönetici onayı verilmedi; preset değiştirilemez. Scripti tekrar çalıştır.'
        exit 1
    }
    if ($p.ExitCode -ne 0) { Warn "İzin verilemedi (icacls çıkış kodu $($p.ExitCode))"; exit 1 }
}
$Conf = Join-Path $Cfg 'config.txt'
if ((Test-Path $Conf) -and -not (Test-Path "$Conf.arctis-yedek")) {
    Copy-Item $Conf "$Conf.arctis-yedek"  # uninstall.ps1 geri koyar
    Say "Eski config.txt yedeklendi: $Conf.arctis-yedek (bundan sonra config.txt'yi tür takibi yazıyor)"
}

# 2) Python 3.11+ (winrt paketleri 3.11 istiyor)
function Find-Python {
    $ErrorActionPreference = 'Continue'  # Microsoft Store'un sahte python'u stderr'e yazar; durdurmasın
    # çift tırnak yok: PowerShell 5.1 yerel programa giden argümandaki çift tırnakları siliyor
    $code = 'import sys; print(sys.executable if sys.version_info >= (3, 11) else '''')'
    $tries = @(
        { py -3 -c $code },
        { python -c $code },
        { & "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -c $code },  # winget'in kişisel kurulumu
        { & "$env:ProgramFiles\Python312\python.exe" -c $code })
    foreach ($t in $tries) {
        $out = try { & $t 2>$null } catch { $null }  # komut yoksa sıradakine
        if ($out) { return "$out".Trim() }
    }
}
$Py = Find-Python
if (-not $Py) {
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Warn 'Python 3.11 ya da üstü yok ve winget bulunamadı: python.org''dan Python 3.12 kur, sonra scripti tekrar çalıştır.'
        exit 1
    }
    Say 'Python 3.12 kuruluyor (winget)'
    winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'User') + ';' + [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $Py = Find-Python
    if (-not $Py) { Warn 'Python kuruldu ama bulunamadı: yeni bir PowerShell penceresinde scripti tekrar çalıştır.'; exit 1 }
}
Say "Python: $Py"

# 3) Program dosyaları, presetler ve paketler
Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*spotify-genre-preset.pyw*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }  # çalışan eski sürüm
Say "Kuruluyor: $Dir"
New-Item -ItemType Directory -Force (Join-Path $Dir 'presets') | Out-Null
Remove-Item (Join-Path $Dir 'presets\*.txt') -ErrorAction SilentlyContinue  # katalogdan çıkan türler kalmasın
Copy-Item (Join-Path $Files 'equalizer-apo\*.txt') (Join-Path $Dir 'presets')
Copy-Item (Join-Path $Files 'core\genre_core.py'), (Join-Path $Files 'core\tray_menu.py'), (Join-Path $Files 'genres.json'), `
    (Join-Path $Files 'windows\spotify-genre-preset.pyw') $Dir
Remove-Item (Join-Path $Dir 'cache.json') -ErrorAction SilentlyContinue  # tür eşlemesi değişmiş olabilir, baştan sorulsun
if (-not (Test-Path $Pythonw)) { & $Py -m venv (Join-Path $Dir 'venv') }
Say 'Paketler kuruluyor: pystray, Pillow, winrt (Windows medya oturumu)'
& (Join-Path $Dir 'venv\Scripts\python.exe') -m pip install --disable-pip-version-check -q --upgrade `
    pystray pillow winrt-runtime winrt-Windows.Foundation winrt-Windows.Foundation.Collections winrt-Windows.Media.Control
if ($LASTEXITCODE -ne 0) { Warn 'Paket kurulumu başarısız (yukarıdaki pip hatasına bak).'; exit 1 }

# 4) Spotify hesabı (menüdeki "en çok dinlenen 5" tüm cihazlardan gelsin); sonradan tepsi menüsünden de bağlanabilir
if (-not (Test-Path (Join-Path $Dir 'spotify.json'))) {
    $c = Read-Host '?? Spotify hesabını bağlayalım mı? Menüdeki en çok dinlenen 5 tür tüm cihazlarından gelir (Premium). [E/h]'
    if ($c -notmatch '^[HhNn]') {
        & (Join-Path $Dir 'venv\Scripts\python.exe') $App --login
        if ($LASTEXITCODE -ne 0) { Warn "Giriş yapılmadı; sonra tepsi menüsünden: Kaynak > Spotify hesabını bağla" }
    }
}

# 5) Oturum açılışında başlat ve şimdi başlat
$Lnk = (New-Object -ComObject WScript.Shell).CreateShortcut($Shortcut)
$Lnk.TargetPath = $Pythonw
$Lnk.Arguments = "`"$App`""
$Lnk.WorkingDirectory = $Dir
$Lnk.Save()
Start-Process $Pythonw -ArgumentList "`"$App`"" -WorkingDirectory $Dir
Say 'Kuruldu: tepside kulaklık simgesi (kilitliyken turuncu); üzerine gelince yüklü preset yazar, sağ tıkla menü.'
Write-Host @"
    - Kısayollar: Ctrl+Alt+Shift+1..7 menüdeki satırlar, Ctrl+Alt+Shift+0 sıradaki preset.
    - SteelSeries GG'de Sonar kapalı, Engine'deki EQ (Bluetooth ve 2.4GHz profili) düz olmalı; yoksa EQ'lar toplanır.
    - Equalizer APO Device Selector'da kulaklığın Bluetooth cihazı ve alıcının takıldığı her USB portu işaretli olmalı
      (Windows her port için ayrı cihaz açar; alıcı takılı değilken listede çıkmaz).
    - Günlük: $Dir\gunluk.txt
    - Deneme (Spotify çalarken): & '$Dir\venv\Scripts\python.exe' '$App' --dene
"@
