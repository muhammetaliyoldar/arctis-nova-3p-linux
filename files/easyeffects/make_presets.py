#!/usr/bin/env python3
"""EasyEffects 7.x presetlerini üretir: Rap, Tekno - Rave, Deep House, Genel.

Kullanım: python3 make_presets.py [çıktı_klasörü] [--check]
  --check: her presetin EQ eğrisinin tepe noktalarını yazdırır (dosya yazmaz)

Zincir: Equalizer -> Compressor -> Limiter
- Compressor attack >= 25 ms: kick/808'in ilk vuruşu ezilmeden geçer (punch).
- Limiter: EasyEffects 7.x'te release en fazla 20 ms; 50 Hz'lik bir dalga da 20 ms
  sürdüğü için limiter devreye girdiğinde basta bozulma yapar. Bu yüzden EQ
  input-gain en yüksek boost kadar negatif ve compressor makeup düşük: sinyal
  limiter'a nadiren ulaşır, limiter sadece güvenlik ağıdır.
"""
import json
import math
import os
import sys


def band(type_, freq, gain=0.0, q=0.7, slope="x1"):
    return {"type": type_, "mode": "RLC (BT)", "slope": slope, "solo": False,
            "mute": False, "gain": gain, "frequency": freq, "q": q, "width": 4.0}


def equalizer(bands, input_gain):
    ch = {f"band{i}": b for i, b in enumerate(bands)}
    return {"bypass": False, "num-bands": len(bands), "mode": "IIR",
            "input-gain": input_gain, "output-gain": 0.0, "split-channels": False,
            "balance": 0.0, "pitch-left": 0.0, "pitch-right": 0.0,
            "left": ch, "right": json.loads(json.dumps(ch))}


def compressor(threshold, ratio, attack, release, makeup):
    return {"bypass": False, "input-gain": 0.0, "output-gain": 0.0,
            "dry": -100.0, "wet": 0.0, "mode": "Downward",
            "attack": attack, "release": release, "release-threshold": -100.0,
            "threshold": threshold, "ratio": ratio, "knee": -6.0, "makeup": makeup,
            "boost-amount": 6.0, "boost-threshold": -72.0, "stereo-split": False,
            "sidechain": {"type": "Feed-forward", "mode": "RMS", "source": "Middle",
                          "stereo-split-source": "Left/Right", "preamp": 0.0,
                          "reactivity": 10.0, "lookahead": 0.0},
            "hpf-mode": "off", "hpf-frequency": 10.0,
            "lpf-mode": "off", "lpf-frequency": 20000.0}


def limiter(input_gain=0.0):
    return {"bypass": False, "input-gain": input_gain, "output-gain": 0.0,
            "mode": "Herm Thin", "oversampling": "None", "dithering": "None",
            "lookahead": 5.0, "attack": 5.0, "release": 20.0, "threshold": -1.0,
            "gain-boost": False, "sidechain-preamp": 0.0, "stereo-link": 100.0,
            "alr": False, "alr-attack": 5.0, "alr-release": 50.0, "alr-knee": 0.0,
            "external-sidechain": False}


def preset(bands, input_gain, comp, lim_gain=0.0):
    return {"output": {"blocklist": [],
                       "plugins_order": ["equalizer#0", "compressor#0", "limiter#0"],
                       "equalizer#0": equalizer(bands, input_gain),
                       "compressor#0": comp, "limiter#0": limiter(lim_gain)}}


PRESETS = {
    # 808 sub'ı göğüste, vokal en önde. Geniş lo-shelf yerine Bell: 120-200 Hz
    # "boom"unu şişirmeden sadece sub'ı kaldırır, bas sıkı ve temiz vurur.
    "Rap": preset([
        band("Hi-pass", 22.0, q=0.7, slope="x2"),   # duyulmayan infrasonik çöp
        band("Bell", 50.0, 5.0, q=0.9),             # 808 sub
        band("Bell", 110.0, 1.0, q=1.2),            # kick punch / 808 harmoniği
        band("Bell", 220.0, -3.0, q=1.1),           # çamur kesimi
        band("Bell", 450.0, -1.0, q=1.4),           # kutu sesi
        band("Bell", 3000.0, 2.5, q=1.0),           # vokal netliği / sözler
        band("Bell", 6500.0, -1.5, q=3.0),          # "sss" + SBC sertliği
        band("Hi-shelf", 10000.0, 1.5, q=0.7),      # hava
    ], -6.0, compressor(threshold=-16.0, ratio=2.0, attack=25.0, release=150.0, makeup=0.5)),

    # Sürükleyen kick + rumble, parlak synth/hat'ler, orta frekanslar hafif oyuk (V)
    "Tekno - Rave": preset([
        band("Hi-pass", 25.0, q=0.7, slope="x2"),
        band("Bell", 55.0, 4.5, q=1.0),             # kick / rumble
        band("Bell", 120.0, 1.0, q=1.2),            # kick gövdesi
        band("Bell", 300.0, -2.5, q=1.0),           # çamur
        band("Bell", 800.0, -1.5, q=1.0),           # orta oyuk -> geniş, enerjik ses
        band("Bell", 4500.0, 1.5, q=1.0),           # synth ısırığı / hat'ler
        band("Bell", 7500.0, -1.0, q=3.0),          # SBC sertliği
        band("Hi-shelf", 11000.0, 3.0, q=0.7),      # parlaklık
    ], -5.5, compressor(threshold=-18.0, ratio=2.5, attack=30.0, release=150.0, makeup=1.0)),

    # Derin, sıcak sub ve yumuşak tizler; uzun setlerde yormaz
    "Deep House": preset([
        band("Hi-pass", 20.0, q=0.7, slope="x2"),
        band("Lo-shelf", 60.0, 4.0, q=0.7),         # sıcak taban
        band("Bell", 42.0, 2.0, q=1.2),             # derin sub
        band("Bell", 250.0, -2.0, q=1.0),           # çamur
        band("Bell", 700.0, -1.0, q=1.2),           # kutu sesi
        band("Bell", 3200.0, 1.0, q=1.0),           # vokal / synth varlığı
        band("Hi-shelf", 10000.0, 2.0, q=0.7),      # hi-hat havası
    ], -6.5, compressor(threshold=-18.0, ratio=1.8, attack=30.0, release=200.0, makeup=0.5)),

    # Her türe uyan hafif V; günlük kullanım
    "Genel": preset([
        band("Hi-pass", 18.0, q=0.7, slope="x2"),
        band("Lo-shelf", 105.0, 3.5, q=0.7),        # dolgun bas
        band("Bell", 220.0, -1.0, q=0.8),
        band("Bell", 3000.0, 1.0, q=1.0),
        band("Bell", 6500.0, -1.0, q=3.0),
        band("Hi-shelf", 10000.0, 1.5, q=0.7),
    ], -4.0, compressor(threshold=-16.0, ratio=1.5, attack=30.0, release=150.0, makeup=0.0)),
}


def response_db(bands, f, fs=48000.0):
    """RBJ biquad yaklaşımıyla EQ'nun f frekansındaki toplam kazancı (dB)."""
    total = 0.0
    for b in bands:
        t, f0, g, q = b["type"], b["frequency"], b["gain"], b["q"]
        A = 10 ** (g / 40)
        w0 = 2 * math.pi * f0 / fs
        alpha = math.sin(w0) / (2 * q)
        cw = math.cos(w0)
        if t == "Bell":
            num = (1 + alpha * A, -2 * cw, 1 - alpha * A)
            den = (1 + alpha / A, -2 * cw, 1 - alpha / A)
        elif t in ("Lo-shelf", "Hi-shelf"):
            s = 1 if t == "Lo-shelf" else -1
            sq = 2 * math.sqrt(A) * alpha
            num = (A * ((A + 1) - s * (A - 1) * cw + sq),
                   s * 2 * A * ((A - 1) - s * (A + 1) * cw),
                   A * ((A + 1) - s * (A - 1) * cw - sq))
            den = ((A + 1) + s * (A - 1) * cw + sq,
                   -s * 2 * ((A - 1) + s * (A + 1) * cw),
                   (A + 1) + s * (A - 1) * cw - sq)
        else:
            continue  # Hi-pass tepe noktasını etkilemez
        w = 2 * math.pi * f / fs
        z1, z2 = complex(math.cos(-w), math.sin(-w)), complex(math.cos(-2 * w), math.sin(-2 * w))
        h = (num[0] + num[1] * z1 + num[2] * z2) / (den[0] + den[1] * z1 + den[2] * z2)
        total += 20 * math.log10(abs(h))
    return total


SCHEMA = "/usr/share/glib-2.0/schemas/com.github.wwmm.easyeffects.%s.gschema.xml"


def schema_ranges(name):
    """EasyEffects gsettings şemasındaki min/max aralıkları (şema yoksa boş)."""
    import re
    try:
        xml = open(SCHEMA % name).read()
    except OSError:
        return {}
    out = {}
    for key, body in re.findall(r'<key name="([^"]+)"[^>]*>(.*?)</key>', xml, re.S):
        m = re.search(r'<range min="([^"]+)" max="([^"]+)"', body)
        if m:
            out[key] = (float(m.group(1)), float(m.group(2)))
    return out


def validate(name, data):
    """Aralık dışı değerleri EasyEffects sessizce reddeder; bunları yakala."""
    errors = []
    for plugin, schema in (("compressor#0", "compressor"), ("limiter#0", "limiter"),
                           ("equalizer#0", "equalizer")):
        ranges = schema_ranges(schema)
        for key, val in data["output"][plugin].items():
            if isinstance(val, (int, float)) and not isinstance(val, bool) and key in ranges:
                lo, hi = ranges[key]
                if not lo <= val <= hi:
                    errors.append(f"{name}: {plugin}.{key}={val} (izin verilen {lo}..{hi})")
    return errors


if __name__ == "__main__":
    problems = [e for n, d in PRESETS.items() for e in validate(n, d)]
    if problems:
        sys.exit("Aralık dışı değerler:\n  " + "\n  ".join(problems))
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    out = args[0] if args else os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    for name, data in PRESETS.items():
        eq = data["output"]["equalizer#0"]
        bands = list(eq["left"].values())
        if "--check" in sys.argv:
            freqs = [20 * (1.02 ** i) for i in range(350)]
            curve = [(f, response_db(bands, f)) for f in freqs if f <= 20000]
            fmax, gmax = max(curve, key=lambda c: c[1])
            print(f"{name:14s} tepe {gmax:+.1f} dB @ {fmax:6.0f} Hz | input-gain {eq['input-gain']:+.1f}"
                  f" | net tepe {gmax + eq['input-gain']:+.1f} dB | "
                  + " ".join(f"{int(f)}:{response_db(bands, f):+.1f}" for f in (40, 60, 100, 200, 300, 1000, 3000, 6500, 12000)))
            continue
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, f"{name}.json"), "w") as fh:
            json.dump(data, fh, indent=4)
        print(f"yazıldı: {os.path.join(out, name)}.json")
