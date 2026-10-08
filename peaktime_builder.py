"""
L-Code Peak-Time Techno Builder -- arrangement ve stylu "METODI, JD Davis -
You Gonna Want Me" (Set About, 2026): peak-time / driving techno (original 135 BPM, my jedeme 132),
G moll, rolling offbeat bass, 16tinove haty, clap na 2 a 4, kratky
syncopovany riff a vokalni hook, ktery nese breaky.

Pouziva stejnou infrastrukturu jako arrangement_builder.py (Section, build,
print_to_arrangement, stejne nazvy stop) - jen jina struktura a patterny.
Vsechno je psane jako explicitni MIDI hity (ne euklid), protoze techno stoji
na offbeatech a euklidovsky generator vzdy zacina na dobe.

Vokal: original hook je Tiga ("You Gonna Want Me", 2005) - bez licence ho
nepouzivej. Stopa "Lead Vocal" dostane jen MIDI placeholder pro vlastni
nahravku / vlastni hook (napr. z Mureky) nasekany do Simpleru.

Pouziti:
    python3 peaktime_builder.py            # jen song map + kontrola (nic nepise)
    python3 peaktime_builder.py --build    # zapise sceny do otevreneho Live setu
    python3 peaktime_builder.py --print    # zkopiruje sceny do Arrangementu (presne na takt)
"""

import argparse
import time

from lcode_orchestrator import LCodeOrchestratorError

from arrangement_builder import Section, BEATS_PER_BAR, TRACK_NAMES, build, print_song_map, copy_to_arrangement

BPM = 132
TITLE = "PEAK-TIME TECHNO (G minor)"

# --- G moll: MIDI noty --------------------------------------------------------
KICK, CLAP, SNARE, CH, OH = 36, 39, 38, 42, 46
SUB_G = 31      # G1 - rumble / sub
BASS_G = 43     # G2 - rolling mid bass
# Akordy i - VI - VII (Gm - Eb - F), stredni poloha
GM, EB, F = [55, 58, 62], [51, 55, 58], [53, 57, 60]


def _bars(bars: int, per_bar):
    """Zopakuje 1taktovy pattern `per_bar(bar_idx)` -> [(beat, note, dur, vel)] pres `bars` taktu."""
    hits = []
    for b in range(bars):
        for beat, note, dur, vel in per_bar(b):
            hits.append((b * BEATS_PER_BAR + beat, note, dur, vel))
    return hits


def kick(bars):
    return _bars(bars, lambda b: [(float(i), KICK, 0.25, 127) for i in range(4)])


def rumble(bars):
    # Sub na kazde dobe, kratky - ducking si udela sidechain z kicku.
    return _bars(bars, lambda b: [(float(i), SUB_G, 0.45, 100) for i in range(4)])


def rolling_bass(bars):
    # Klasicka "rolling" basa: 3 sestnactiny mezi kicky (e, and, a), akcent na offbeatu.
    # Kazdy 4. takt skok o kvartu (C) pro pohyb.
    def bar(b):
        note = BASS_G + (5 if b % 4 == 3 else 0)
        return [(i + off, note, 0.2, vel) for i in range(4)
                for off, vel in ((0.25, 88), (0.5, 110), (0.75, 92))]
    return _bars(bars, bar)


def closed_hats(bars):
    # 16tiny, akcent na offbeatu, jemne ghost noty.
    vel = [70, 55, 100, 60]
    return _bars(bars, lambda b: [(i + s * 0.25, CH, 0.1, vel[s]) for i in range(4) for s in range(4)])


def open_hats(bars):
    return _bars(bars, lambda b: [(i + 0.5, OH, 0.3, 105) for i in range(4)])


def clap(bars):
    return _bars(bars, lambda b: [(1.0, CLAP, 0.3, 115), (3.0, CLAP, 0.3, 115)])


def snare_roll(bars):
    # Build: ctvrtky -> osminy -> sestnactiny, velocity roste.
    hits, total = [], bars * BEATS_PER_BAR
    t = 0.0
    while t < total:
        progress = t / total
        step = 1.0 if progress < 0.5 else 0.5 if progress < 0.75 else 0.25
        hits.append((t, SNARE, 0.1, int(60 + 67 * progress)))
        t += step
    return hits


# 2taktovy syncopovany riff (G moll pentatonika), 16tinove pozice.
_RIFF = [
    [(0, 67), (3, 67), (6, 70), (8, 67), (11, 74), (14, 72)],
    [(0, 67), (3, 65), (6, 67), (10, 70), (12, 62)],
]


def riff(bars):
    return _bars(bars, lambda b: [(pos * 0.25, n, 0.2, 100 if pos == 0 else 90) for pos, n in _RIFF[b % 2]])


def pads(bars):
    # Gm (2 takty) - Eb - F, dlouhe plochy.
    prog = [GM, GM, EB, F]
    return _bars(bars, lambda b: [(0.0, n, 3.9, 80) for n in prog[b % 4]])


def vocal_hook(bars):
    # Placeholder: 1 fraze kazde 2 takty (chop na C4 v Simpleru), odpoved v polovine.
    return _bars(bars, lambda b: [(0.0, 60, 1.5, 110), (2.0, 62, 1.0, 95)] if b % 2 == 0 else [])


def riser(bars, note=60):
    return [(0.0, note, bars * BEATS_PER_BAR - 0.1, 100)]


def _full_groove(bars, lead=True, vox=False):
    m = {"kick_bass": kick(bars), "sub_bass": rumble(bars), "mid_bass": rolling_bass(bars),
         "hats": closed_hats(bars) + open_hats(bars), "clap": clap(bars)}
    if lead:
        m["synth_lead"] = riff(bars)
    if vox:
        m["lead_vocal"] = vocal_hook(bars)
    return m


# --- Struktura: DJ-friendly Original Mix (~6,8 min @ 132) ---------------------
SECTIONS = [
    Section("Intro", 32, melodic={"kick_bass": kick(32), "hats": closed_hats(32)}),
    Section("Groove A", 32, melodic=_full_groove(32, lead=False)),
    Section("Tension", 16, melodic=_full_groove(16, lead=True)),
    Section("Break", 16, melodic={"pads": pads(16), "lead_vocal": vocal_hook(16),
                                   "hats": open_hats(16), "fx": riser(16, 60)}),
    Section("Build", 8, melodic={"snare": snare_roll(8), "lead_vocal": vocal_hook(8),
                                  "fx": riser(8, 67)}),
    Section("Drop A", 32, melodic=_full_groove(32, lead=True, vox=True)),
    Section("Groove B", 16, melodic=_full_groove(16, lead=False, vox=True)),
    Section("Break 2", 8, melodic={"pads": pads(8), "lead_vocal": vocal_hook(8), "fx": riser(8, 64)}),
    Section("Drop B", 32, melodic={**_full_groove(32, lead=True, vox=True), "pads": pads(32)}),
    Section("Outro", 32, melodic={"kick_bass": kick(32), "hats": closed_hats(32),
                                   "mid_bass": rolling_bass(16)}),
]


def validate(sections=SECTIONS) -> int:
    """Kontrola pred zapisem do Live: zadny hit mimo delku klipu, MIDI rozsahy OK."""
    errors, notes = [], 0
    for s in sections:
        length = s.bars * BEATS_PER_BAR
        for role, hits in s.melodic.items():
            for start, note, dur, vel in hits:
                notes += 1
                if not (0 <= start < length) or start + dur > length + 1e-9:
                    errors.append(f"{s.name}/{role}: hit {start}+{dur} mimo klip {length}")
                if not (0 <= note <= 127 and 1 <= vel <= 127):
                    errors.append(f"{s.name}/{role}: note {note} vel {vel} mimo rozsah")
    if errors:
        raise ValueError("\n".join(errors[:20]))
    return notes


# Nastroje z knihovny Live 12 Suite (presety se zvukem - Serum presety programove
# vybrat nejdou, viz PROGRESS_LOG). Core Kity maji kick C1, snare D1, clap D#1,
# closed hat F#1, open hat A#1 = sedi na KICK/SNARE/CLAP/CH/OH vyse.
INSTRUMENTS = {
    "kick_bass":  "909 Core Kit.adg",
    "snare":      "909 Core Kit.adg",
    "clap":       "909 Core Kit.adg",
    "hats":       "909 Core Kit.adg",
    "sub_bass":   "Sub Sine Bass.adv",          # Operator - cisty sinus G1
    "mid_bass":   "Short Decay Saw Bass.adv",   # Operator - kratka rolling basa
    "synth_lead": "Tech Lead.adg",              # Wavetable
    "pads":       "Dark Swell Pad.adg",         # Wavetable
    "fx":         "Riser Basic.adg",            # Wavetable - dlouha nota = riser
    "lead_vocal": "Synth Vox Ai.adg",           # Wavetable - docasny hlas, nahradit vlastnim vokalem
}


def load_instruments(orch) -> dict:
    """Nahraje preset na kazdou stopu, ktera jeste nema zadne zarizeni
    (idempotentni - opakovane spusteni nic nezdvoji). Vraci {stopa: zarizeni}."""
    q = orch._query
    names = list(q("/live/song/get/track_names", []))
    result = {}
    for role, preset in INSTRUMENTS.items():
        t = names.index(TRACK_NAMES[role])
        devices = q("/live/track/get/devices/name", [t])[1:]
        if not devices:
            orch.client.send_message("/live/track/insert_device", [t, preset])
            # Hledani v browseru blokuje hlavni vlakno Live - dotazy mezitim
            # timeoutuji, to neni chyba, cekame dal.
            deadline = time.time() + 90
            while time.time() < deadline and not devices:
                time.sleep(0.5)
                try:
                    devices = q("/live/track/get/devices/name", [t], timeout=5)[1:]
                except LCodeOrchestratorError:
                    pass
        result[TRACK_NAMES[role]] = list(devices) or f"NENAHRANO ({preset})"
    return result


# Barvy stop (Live color_index) - rytmika cervena/oranzova, basy fialova, harmonie modra.
_COLORS = {"kick_bass": 14, "sub_bass": 24, "mid_bass": 25, "snare": 1, "clap": 2, "hats": 3,
           "lead_vocal": 11, "backing_vox": 12, "piano_guitar": 16, "pads": 20, "synth_lead": 18, "fx": 5}


def _set_is_empty(orch) -> bool:
    n_tracks = orch._query("/live/song/get/num_tracks", [])[0]
    n_scenes = orch._query("/live/song/get/num_scenes", [])[0]
    for t in range(n_tracks):
        for sc in range(n_scenes):
            if orch._query("/live/clip_slot/get/has_clip", [t, sc])[-1]:
                return False
    return True


def setup_tracks(orch):
    """Pripravi prazdny set: 12 MIDI stop s nazvy z TRACK_NAMES. Bezi jen nad
    setem bez klipu, aby nikdy neprepsal rozdelany projekt."""
    if not _set_is_empty(orch):
        raise RuntimeError("Otevreny set obsahuje klipy - otevri novy prazdny Live Set (Cmd+N)")
    existing = orch._query("/live/song/get/num_tracks", [])[0]
    for i, (role, name) in enumerate(TRACK_NAMES.items()):
        orch.client.send_message("/live/song/create_midi_track", [-1])
        time.sleep(0.3)
        idx = existing + i
        orch.client.send_message("/live/track/set/name", [idx, name])
        orch.client.send_message("/live/track/set/color_index", [idx, _COLORS.get(role, 0)])
    time.sleep(0.5)
    for _ in range(existing):  # puvodni prazdne vychozi stopy
        orch.client.send_message("/live/song/delete_track", [0])
        time.sleep(0.3)
    names = orch._query("/live/song/get/track_names", [])
    if list(names) != list(TRACK_NAMES.values()):
        raise RuntimeError(f"Stopy nesedi: {names}")
    print(f"stopy pripraveny: {len(names)}")


def cleanup_scenes(orch, keep: int):
    """build() vklada sceny na zacatek - puvodni prazdne sceny zustanou za nimi, smazat."""
    n = orch._query("/live/song/get/num_scenes", [])[0]
    for sc in range(n - 1, keep - 1, -1):
        orch.client.send_message("/live/song/delete_scene", [sc])
        time.sleep(0.2)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true", help="zapsat do otevreneho Live setu")
    ap.add_argument("--print", dest="print_arr", action="store_true",
                    help="zkopirovat sceny do Arrangementu (okamzite, presne na takt)")
    ap.add_argument("--instruments", action="store_true", help="nahodit presety nastroju")
    ap.add_argument("--setup", action="store_true", help="nejdriv pripravit 12 stop v prazdnem setu")
    args = ap.parse_args()

    print_song_map(SECTIONS, BPM, TITLE)
    print(f"validace OK: {validate()} MIDI not")
    if args.build or args.print_arr or args.instruments:
        from lcode_orchestrator import LCodeOrchestrator
        orch = LCodeOrchestrator()
        try:
            if args.build:
                if args.setup:
                    setup_tracks(orch)
                orch.audit_project(verbose=False)
                build(orch, SECTIONS, tempo=BPM)
                cleanup_scenes(orch, keep=len(SECTIONS))
            if args.instruments:
                for track, dev in load_instruments(orch).items():
                    print(f"  {track:18s} {dev}")
            if args.print_arr:
                print("arrangement:", copy_to_arrangement(orch, SECTIONS))
        finally:
            orch.close()
