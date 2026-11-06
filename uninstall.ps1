# install.ps1'in kurduklarını kaldırır: tepsi uygulaması, Başlangıç kısayolu, program dosyaları ve presetler; Equalizer
# APO'nun eski config.txt'si geri konur. Ayarlar, Spotify girişi ve dinleme geçmişi (config.json, spotify.json,
# state.json, gecmis.json) Linux'taki gibi bilerek bırakılıyor. Equalizer APO ve Python kaldırılmaz.
#   powershell -ExecutionPolicy Bypass -File uninstall.ps1
$ErrorActionPreference = 'Stop'
$Dir = Join-Path $env:LOCALAPPDATA 'spotify-genre-preset'

Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
    Where-Object { $_.CommandLine -like '*spotify-genre-preset.pyw*' } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
Remove-Item (Join-Path ([Environment]::GetFolderPath('Startup')) 'Arctis Preset.lnk') -ErrorAction SilentlyContinue
foreach ($p in 'venv', 'presets', '__pycache__', 'genre_core.py', 'tray_menu.py', 'genres.json', 'spotify-genre-preset.pyw',
               'cache.json', 'kilit', 'gunluk.txt') {
    Remove-Item (Join-Path $Dir $p) -Recurse -Force -ErrorAction SilentlyContinue
}
$Cfg = (Get-ItemProperty 'HKLM:\SOFTWARE\EqualizerAPO' -ErrorAction SilentlyContinue).ConfigPath
if ($Cfg -and (Test-Path (Join-Path $Cfg 'config.txt.arctis-yedek'))) {
    Move-Item (Join-Path $Cfg 'config.txt.arctis-yedek') (Join-Path $Cfg 'config.txt') -Force
    Write-Host 'Equalizer APO: kurulumdan önceki config.txt geri kondu'
}
Write-Host "Kaldırıldı. Ayarlar ve dinleme geçmişi $Dir içinde duruyor; istersen klasörü silebilirsin."
