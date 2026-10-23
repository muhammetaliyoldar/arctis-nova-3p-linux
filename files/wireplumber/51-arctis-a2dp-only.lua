-- Arctis Nova 3P: açılışta A2DP ve HFP aynı anda kurulmaya çalışınca bağlantılar
-- çakışıyor (avdtp "Operation already in progress" / Discover timeout) ve kulaklık
-- kapanıyor. Mikrofon Bluetooth'ta kullanılmadığı için sadece A2DP bırakıldı.
bluez_monitor.properties["bluez5.roles"] = "[ a2dp_sink a2dp_source ]"
bluez_monitor.properties["bluez5.hfphsp-backend"] = "none"

-- Asıl sorun: PipeWire kulaklığa 19 endpoint (LDAC, aptX HD, aptX, FastStream, Opus...)
-- sunuyor; Arctis bunların yeteneklerini sorgularken donup kendini kapatıyor
-- (btmon: "Remote Device Terminated due to Power Off"). Arctis zaten sadece SBC kullanıyor.
bluez_monitor.properties["bluez5.codecs"] = "[ sbc ]"
-- sbc_xq de çıkarıldı: kulaklık bağlantıyı kendisi kurduğunda bu kanalı seçip
-- hata verebiliyor (wireplumber "error 24"); düz SBC zaten kullanılan codec.
