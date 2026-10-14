"""
L-Code Strudel export -- prevede aranz z arrangement_builder (vcetne pauz,
nadechu a FX hitu z plan_transitions) na Strudel kod, ktery se da v REPLu
(strudel.cc) dal upravovat. Jedna sekce = jedna konstanta (stack vrstev),
cela pisen = arrange([takty, sekce], ...). 1 cyklus Strudelu = 1 takt.

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


def note_name(midi: int) -> str:
    """MIDI cislo -> jmeno noty ve Strudelu (c4 = 60)."""
    return f"{NOTE_NAMES[midi % 12]}{midi // 12 - 1}"


def slug(name: str) -> str:
    # prefix kvuli rezervovanym slovum v JS ("break" by byla neplatna konstanta)
    return "sec_" + re.sub(r"\W+", "", name.lower())


def euclid(kwargs: dict) -> str:
    return f"({kwargs.get('pulses', 4)},{kwargs.get('steps', 16)})"


# role -> funkce(kwargs) -> vyraz vrstvy; zvuky jsou zamerne ze zakladni sady Strudelu
RHYTHMIC_LAYERS = {
    "kick_bass":  lambda k: f's("bd{euclid(k)}")',
    "snare":      lambda k: f's("sd{euclid(k)}").gain(.8)',
    "clap":       lambda k: f's("cp{euclid(k)}").gain(.8)',
    "hats":       lambda k: f's("hh{euclid(k)}").gain(.6)',
    "sub_bass":   lambda k: f'note("{note_name(k["root_note"])}{euclid(k)}").s("sine").gain(.9)',
    "mid_bass":   lambda k: f'note("{note_name(k["root_note"])}{euclid(k)}").s("sawtooth").lpf(500).gain(.5)',
    "synth_lead": lambda k: f'note("{note_name(k["root_note"])}{euclid(k)}").s("square").lpf(2200).decay(.12).sustain(0).gain(.4)',
}

MELODIC_SOUNDS = {
    "pads":         '.s("sawtooth").lpf(1200).gain(.35)',
    "piano_guitar": '.s("triangle").decay(.3).sustain(0).gain(.6)',
    "lead_vocal":   '.s("square").lpf(2500).decay(.4).sustain(0).gain(.4)',
    "backing_vox":  '.s("sawtooth").lpf(1800).gain(.3)',
}


def bar_grids(hits: list, bars: int) -> list:
    """Hity v dobach -> seznam taktu, kazdy jako retezec 16 sestnactin (mini-notace)."""
    cells = [[[] for _ in range(16)] for _ in range(bars)]
    for start, note, _dur, _vel in hits:
        bar, step = divmod(int(round(start * 4)), 16)
        if bar >= bars:
            continue
        name = note_name(note)
        if name not in cells[bar][step]:
            cells[bar][step].append(name)
    out = []
    for bar in cells:
        tokens = ["~" if not c else (c[0] if len(c) == 1 else "[" + ",".join(c) + "]") for c in bar]
        out.append("~" if all(t == "~" for t in tokens) else "[" + " ".join(tokens) + "]")
    return out


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


def melodic_layer(section: "ab.Section", role: str, hits: list):
    hits = list(hits)
    for a, b, roles in ab.section_cuts(section):
        if roles is None or role in roles:
            hits = ab.cut_hits(hits, a, b)
    if not hits:
        return None
    if role == "fx":  # pitched riser -> sum, delka podle (pripadne zkracene) noty
        sec = max(d for _s, _n, d, _v in hits) * 60 / BPM
        grid = alternation(_tokens_as_names(hits, "white", section.bars))
        return f's("{grid}").attack({sec * 0.95:.2f}).release(.05).hpf(600).gain(.35){clip_suffix(hits)}'
    sound = MELODIC_SOUNDS[role]
    return f'note("{alternation(bar_grids(hits, section.bars))}"){sound}{clip_suffix(hits)}'


# FX pad (MIDI nota z arrangement_builder) -> (popis, token, sablona vrstvy); {sec} = delka v sekundach
FX_LAYERS = {
    ab.FX_IMPACT:    ("impact",        "c1",    'note("{grid}").s("sine").decay(.8).sustain(0).gain(1)'),
    ab.FX_REV_CRASH: ("reverse crash", "white", 's("{grid}").attack({att}).release(.05).hpf(3000).gain(.4){clip}'),
    ab.FX_DOWNLIFT:  ("downlifter",    "pink",  's("{grid}").decay({sec}).sustain(0).lpf(2500).gain(.5){clip}'),
    ab.FX_SWEEP:     ("sweep",         "white", 's("{grid}").attack({att}).release(.05).hpf(1500).gain(.3){clip}'),
    ab.FX_SHOUT:     ("shout slot",    "c4",    'note("{grid}").s("square").decay(.15).sustain(0).gain(.5)'),
}


def fx_layers(section: "ab.Section") -> list:
    out = []
    for pad, (label, token, template) in FX_LAYERS.items():
        hits = [h for h in section.fx_hits if h[1] == pad]
        if not hits:
            continue
        grid = alternation(_tokens_as_names(hits, token, section.bars))
        sec = max(d for _s, _n, d, _v in hits) * 60 / BPM
        out.append((label, template.format(grid=grid, sec=f"{sec:.2f}", att=f"{sec * 0.95:.2f}",
                                           clip=clip_suffix(hits))))
    return out


def _tokens_as_names(hits: list, token: str, bars: int) -> list:
    """Jako bar_grids(), ale s vlastnim tokenem (zvuk/nota) misto jmena MIDI noty."""
    cells = [["~"] * 16 for _ in range(bars)]
    for start, _n, _d, _v in hits:
        bar, step = divmod(int(round(start * 4)), 16)
        if bar < bars:
            cells[bar][step] = token
    return ["~" if all(t == "~" for t in c) else "[" + " ".join(c) + "]" for c in cells]


def section_code(section: "ab.Section") -> str:
    lines = []
    for role, kwargs in section.rhythmic.items():
        expr = RHYTHMIC_LAYERS[role](kwargs)
        expr += mask_for(section, role) or ""
        lines.append((f'{role} ("{ab.TRACK_NAMES[role]}")', expr))
    for role, hits in section.melodic.items():
        expr = melodic_layer(section, role, hits)
        if expr:
            lines.append((f'{role} ("{ab.TRACK_NAMES[role]}")', expr))
    for label, expr in fx_layers(section):
        lines.append((f'fx: {label} ("{ab.TRACK_NAMES["fx"]}")', expr))
    body = ",\n".join(f"  // {c}\n  {e}" for c, e in lines)
    return f"const {slug(section.name)} = stack(\n{body}\n)"


BPM = 120.0


def export(bpm: float = 120.0) -> str:
    global BPM
    BPM = bpm
    sections = ab.plan_transitions(ab.SECTIONS)
    parts = [
        "// L-Code tech house draft -- generovano z arrangement_builder.py (strudel_export.py)",
        "// 1 cyklus = 1 takt. Pauzy: .mask() / zkracene noty. FX: sum a sine misto samplu.",
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
    """Odkaz na strudel.cc s predvyplnenym kodem (hash = base64 kodu)."""
    return "https://strudel.cc/#" + urllib.parse.quote(base64.b64encode(code.encode("utf-8")).decode(), safe="")


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUT
    bpm = float(sys.argv[2]) if len(sys.argv) > 2 else 120.0
    code = export(bpm)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(code, encoding="utf-8")
    print(f"zapsano {out} ({len(code)} znaku, {code.count(chr(10))} radku)")
    print(f"odkaz: {strudel_link(code)}")
