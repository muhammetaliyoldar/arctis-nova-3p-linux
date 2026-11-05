-- Mikrofonu açık kalması gereken bilgisayarlar için (install.sh'ta mikrofon sorusuna "h").
-- HFP/HSP açık kalır, sadece codec listesi SBC'ye indirilir. Neden: 51-arctis-a2dp-only.lua
bluez_monitor.properties["bluez5.codecs"] = "[ sbc ]"
