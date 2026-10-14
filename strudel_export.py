"""
L-Code Strudel export -- prevede aranz z arrangement_builder (vcetne pauz,
nadechu, double kicku a FX hitu z plan_transitions) na Strudel kod, ktery se
da v REPLu (strudel.cc) dal upravovat. Jedna sekce = jedna konstanta (stack
vrstev), cela pisen = arrange([takty, sekce], ...). 1 cyklus Strudelu = 1 takt.

Zvuk je postaveny cely ve Strudelu: TR-909 bicky, supersaw/FM syntezatory,
filtry, distortion, reverb, delay a sidechain (kick duckuje orbit 2). FX jsou
samply a stoupajici/klesajici arpeggia, zadny white noise.

Pouziti:
    python3 strudel_export.py [vystup.js] [bpm]

Kod je zamerne cisty ASCII (komentare bez diakritiky), aby ho sel bezpecne
poslat jako odkaz na strudel.cc.
"""
import base64
import re
import sys
import urllib.parse
from pathlib import Path

import arrangement_builder as ab

NOTE_NAMES = ["c", "db", "d", "eb", "e", "f", "gb", "g", "ab", "a", "bb", "b"]
DEFAULT_OUT = Path.home() / "lcode-strudel" / "patterns" / "techhouse_draft.js"
BPM = 120.0

# sidechain: kick (duckorbit) stahuje vse, co je na orbit 2 (basy, pady, leady)
SC = ".orbit(2)"
DUCK = ".duckorbit(2).duckattack(.18).duckdepth(.7)"
DRUMS = '.bank("RolandTR909")'


def note_name(midi: int) -> str:
    """MIDI cislo -> jmeno noty ve Strudelu (c4 = 60)."""
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def slug(name: str) -> str:
    # prefix kvuli rezervovanym slovum v JS ("break" by byla neplatna konstanta)
    return "sec_" + re.sub(r"\W+", "", name.lower())


def euclid(kwargs: dict) -> str:
    return f"({kwargs.get('pulses', 4)},{kwargs.get('steps', 16)})"


# role -> funkce(kwargs) -> vyraz vrstvy
RHYTHMIC_LAYERS = {
    "kick_bass":  lambda k: f's("bd{euclid(k)}"){DRUMS}.shape(.25).gain(1.1){DUCK}',
    "snare":      lambda k: f's("sd{euclid(k)}"){DRUMS}.room(.3).roomsize(2.5).gain(.8)',
    "clap":       lambda k: (f's("cp{euclid(k)}"){DRUMS}.room(.45).roomsize(3)'
                             '.delay(.18).delaytime(.1875).delayfeedback(.35).gain(.8)'),
    "hats":       lambda k: f's("hh{euclid(k)}"){DRUMS}.hpf(6500).room(.12).gain(.55)',
    "sub_bass":   lambda k: f'note("{note_name(k["root_note"])}{euclid(k)}").s("sine").lpf(140).gain(.9){SC}',
    "mid_bass":   lambda k: (f'note("{note_name(k["root_note"])}{euclid(k)}").s("sawtooth")'
                             '.lpf(sine.range(350,1100).slow(8)).lpq(8).distort(.35).gain(.5)' + SC),
    "synth_lead": lambda k: (f'note("{note_name(k["root_note"])}{euclid(k)}").s("supersaw").detune(.25)'
                             '.lpf(sine.range(1800,5200).slow(16)).lpq(6).decay(.14).sustain(0)'
                             '.delay(.4).delaytime(.1875).delayfeedback(.45).room(.3).roomsize(4).gain(.4)' + SC),
}

MELODIC_SOUNDS = {
    "pads":         ('.s("supersaw").detune(.4).lpf(sine.range(700,2200).slow(16)).attack(.4).release(1.2)'
                     '.room(.8).roomsize(7).gain(.28)' + SC),
    "piano_guitar": ('.s("sine").fm(2.5).fmh(2).decay(.35).sustain(0)'
                     '.delay(.3).delaytime(.1875).delayfeedback(.4).room(.35).gain(.55)'),
    "lead_vocal":   ('.s("sawtooth").lpf(2600).lpq(10).vib(5).decay(.35).sustain(0)'
                     '.delay(.45).delaytime(.1875).delayfeedback(.4).room(.5).roomsize(4).gain(.4)'),
    "backing_vox":  ('.s("supersaw").detune(.3).lpf(1800).attack(.3).release(1)'
                     '.room(.7).roomsize(6).gain(.25)' + SC),
}


# --- mrizky (kazdy takt = 16 sestnactin) -------------------------------------
def _cells_to_bars(cells: list, fill: str = "~") -> list:
    out = []
    for bar in cells:
        tokens = [fill if not c else (c[0] if len(c) == 1 else "[" + ",".join(c) + "]") for c in bar]
        out.append(fill if all(t == fill for t in tokens) else "[" + " ".join(tokens) + "]")
    return out


def bar_grids(hits: list, bars: int, token=None) -> list:
    """Hity v dobach -> seznam taktu v mini-notaci. token=None -> jmeno MIDI noty, jinak pevny zvuk/nota."""
    cells = [[[] for _ in range(16)] for _ in range(bars)]
    for start, note, _dur, _vel in hits:
        bar, step = divmod(int(round(start * 4)), 16)
        if bar >= bars:
            continue
        name = token or note_name(note)
        if name not in cells[bar][step]:
            cells[bar][step].append(name)
    return _cells_to_bars(cells)


def run_length(items: list) -> list:
    """['a','a','b'] -> ['a!2','b'] (replikace v mini-notaci)."""
    out = []
    i = 0
    while i < len(items):
        j = i
        while j < len(items) and items[j] == items[i]:
            j += 1
        out.append(items[i] + (f"!{j - i}" if j - i > 1 else ""))
        i = j
    return out


def alternation(bars_str: list) -> str:
    """Jeden prvek na takt; kdyz jsou vsechny stejne, staci jeden bez <>."""
    if len(set(bars_str)) == 1:
        return bars_str[0]
    return "<" + " ".join(run_length(bars_str)) + ">"


def mask_for(section: "ab.Section", role: str):
    """.mask(...) pro pauzy a nadechy rytmickych roli, nebo None kdyz se role nerezou."""
    cuts = [c for c in ab.section_cuts(section) if c[2] is None or role in c[2]]
    if not cuts:
        return None
    tokens = []
    for bar in range(section.bars):
        slots = []
        for beat in range(4):
            t = bar * 4 + beat
            slots.append("0" if any(a <= t < b for a, b, _ in cuts) else "1")
        tokens.append("1" if set(slots) == {"1"} else "[" + " ".join(slots) + "]")
    return f'.mask("{alternation(tokens)}")'


def clip_suffix(hits: list) -> str:
    longest = max((d for _s, _n, d, _v in hits), default=0)
    steps = round(longest * 4)
    return f".clip({steps})" if steps > 1 else ""


# --- arpeggio "ladder": riser / sweep / downlifter bez sumu ---------------------
def ladder(section: "ab.Section", start: float, dur: float, first_note: int, semis_per_beat: float,
           gain: tuple, cutoff: tuple, body: str) -> str:
    """Pulzujici (osminy) arpeggio, ktere stoupa/klesa po pulltonech; gain a cutoff rostou/klesaji
    po kazde note (hodnoty jsou v mrizce stejne jako noty, takze nezavisi na poloze sekce)."""
    n = max(int(dur / 0.5), 1)
    notes = [[[] for _ in range(16)] for _ in range(section.bars)]
    gains = [["0.3"] * 16 for _ in range(section.bars)]
    cuts = [["800"] * 16 for _ in range(section.bars)]
    for k in range(n):
        frac = k / (n - 1) if n > 1 else 0.0
        bar, step = divmod(int(round((start + k * 0.5) * 4)), 16)
        if bar >= section.bars:
            break
        notes[bar][step] = [note_name(first_note + int(semis_per_beat * k * 0.5))]
        gains[bar][step] = f"{gain[0] + (gain[1] - gain[0]) * frac:.2f}"
        cuts[bar][step] = str(int(cutoff[0] * (cutoff[1] / cutoff[0]) ** frac))
    note_bars = _cells_to_bars(notes)
    gain_bars = ["0.3" if nb == "~" else "[" + " ".join(g) + "]" for nb, g in zip(note_bars, gains)]
    cut_bars = ["800" if nb == "~" else "[" + " ".join(c) + "]" for nb, c in zip(note_bars, cuts)]
    return (f'note("{alternation(note_bars)}").s("supersaw").detune(.3)'
            f'.lpf("{alternation(cut_bars)}").lpq(5).gain("{alternation(gain_bars)}"){body}')


def melodic_layer(section: "ab.Section", role: str, hits: list):
    hits = ab.role_hits(list(hits), ab.section_cuts(section), role)
    if not hits:
        return None
    if role == "fx":  # pitched riser (cela sekce, ev. zkracena pauzou) -> stoupajici arpeggio
        start, _n, dur, _v = hits[0]
        return ladder(section, start, dur, first_note=hits[0][1] - 12, semis_per_beat=1,
                      gain=(0.15, 0.6), cutoff=(400, 7000), body=".attack(.01).release(.15).room(.4).roomsize(4)" + SC)
    sound = MELODIC_SOUNDS[role]
    return f'note("{alternation(bar_grids(hits, section.bars))}"){sound}{clip_suffix(hits)}'


# --- FX pady (MIDI nota z arrangement_builder) -------------------------------
def fx_expr(section: "ab.Section", pad: int, hits: list) -> str:
    def grid(token):
        return alternation(bar_grids(hits, section.bars, token))

    if pad == ab.FX_IMPACT:    # hluboky 808 boom + zpomaleny crash, obojí s dlouhym reverbem
        return (f'stack(s("{grid("808bd")}").speed(.55).shape(.3).room(.8).roomsize(7).gain(1.1), '
                f's("{grid("cr")}").speed(.7).room(.6).roomsize(5).gain(.5))')
    if pad == ab.FX_REV_CRASH:  # crash prehravany pozpatku
        return f's("{grid("cr")}").speed(-1).room(.5).roomsize(4).gain(.8)'
    if pad == ab.FX_SHOUT:     # placeholder za vocal shout
        return (f's("{grid("yeah")}").room(.5).roomsize(4)'
                '.delay(.3).delaytime(.1875).delayfeedback(.4).gain(.9)')
    start, _n, dur, _v = hits[0]
    if pad == ab.FX_DOWNLIFT:  # klesajici arpeggio, filtr se zavira
        return ladder(section, start, dur, first_note=72, semis_per_beat=-1,
                      gain=(0.5, 0.1), cutoff=(5000, 300), body=".attack(.01).release(.4).room(.6).roomsize(6)" + SC)
    if pad == ab.FX_SWEEP:     # kratke stoupajici arpeggio pred zmenou sekce
        return ladder(section, start, dur, first_note=60, semis_per_beat=2,
                      gain=(0.15, 0.55), cutoff=(600, 8000), body=".attack(.005).release(.1).room(.3)" + SC)
    raise ValueError(f"neznamy FX pad {pad}")


FX_LABELS = {ab.FX_IMPACT: "impact (808 boom + crash)", ab.FX_REV_CRASH: "reverse crash",
             ab.FX_DOWNLIFT: "downlifter", ab.FX_SWEEP: "sweep", ab.FX_SHOUT: "shout slot"}


def fx_layers(section: "ab.Section") -> list:
    out = []
    for pad, label in FX_LABELS.items():
        hits = [h for h in section.fx_hits if h[1] == pad]
        if hits:
            out.append((f'fx: {label} ("{ab.TRACK_NAMES["fx"]}")', fx_expr(section, pad, hits)))
    return out


def kick_layer(section: "ab.Section"):
    hits = ab.role_hits(list(section.kick_extra), ab.section_cuts(section), "kick_bass")
    if not hits:
        return None
    grid = alternation(bar_grids(hits, section.bars, "bd"))
    return f's("{grid}"){DRUMS}.shape(.25).gain(1){DUCK}'


def section_code(section: "ab.Section") -> str:
    lines = []
    for role, kwargs in section.rhythmic.items():
        expr = RHYTHMIC_LAYERS[role](kwargs)
        expr += mask_for(section, role) or ""
        lines.append((f'{role} ("{ab.TRACK_NAMES[role]}")', expr))
    kick = kick_layer(section)
    if kick:
        lines.append((f'double kick / kick roll ("{ab.TRACK_NAMES["kick_bass"]}")', kick))
    for role, hits in section.melodic.items():
        expr = melodic_layer(section, role, hits)
        if expr:
            lines.append((f'{role} ("{ab.TRACK_NAMES[role]}")', expr))
    lines += fx_layers(section)
    body = ",\n".join(f"  // {c}\n  {e}" for c, e in lines)
    return f"const {slug(section.name)} = stack(\n{body}\n)"


def export(bpm: float = 120.0) -> str:
    global BPM
    BPM = bpm
    sections = ab.plan_transitions(ab.SECTIONS)
    parts = [
        "// L-Code tech house draft -- generovano z arrangement_builder.py (strudel_export.py)",
        "// 1 cyklus = 1 takt. Pauzy: .mask() / zkracene noty. Double kick: vrstva 'double kick' v sekcich.",
        "// Zvuk: TR-909 bicky, supersaw/FM, filtry, distortion, reverb, delay. Sidechain: kick duckuje orbit 2.",
        "// FX pady v Abletonu (Drum Rack na 'FX Risers'): 36 impact, 37 reverse crash,",
        "// 38 downlifter, 39 sweep, 40 shout. Upravuj sekce nize, poradi je dole v arrange().",
        f"setcps({bpm:g}/60/4)",
        "",
    ]
    for s in sections:
        parts.append(f"// --- {s.name} ({s.bars} taktu)")
        parts.append(section_code(s))
        parts.append("")
    arr = ",\n".join(f"  [{s.bars}, {slug(s.name)}]" for s in sections)
    parts.append(f"arrange(\n{arr}\n)")
    return "\n".join(parts) + "\n"


def strudel_link(code: str) -> str:
    """Odkaz na strudel.cc s predvyplnenym kodem (hash = encodeURIComponent(base64(utf8)))."""
    return "https://strudel.cc/#" + urllib.parse.quote(base64.b64encode(code.encode("utf-8")).decode(), safe="")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    bpm = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    code = export(bpm)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(code, encoding="utf-8")
    out.with_suffix(".url").write_text(strudel_link(code), encoding="utf-8")
    print(f"zapsano {out} ({len(code)} znaku, {code.count(chr(10))} radku) + {out.with_suffix('.url').name}")
