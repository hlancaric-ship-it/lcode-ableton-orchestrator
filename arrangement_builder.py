"""
L-Code Arrangement Builder -- writes a full tech-house song structure into
Session clip slots (one Scene per section), using TechnoGenEngine's
euclidean generator for percussive tracks and a simple chord/stab writer
for the melodic/harmonic tracks. Session, not Arrangement, is where
AbletonOSC can actually write content (see README: /live/track/get/
arrangement_clips/* is read-only, there's no write equivalent) -- the
Session grid built here is a 1:1 map of the arrangement and is meant to be
"printed" into Arrangement afterwards with print_to_arrangement().

Honesty over completeness: these tracks have no instrument loaded yet
(AbletonOSC can't insert devices from the browser -- same limitation noted
in techno_gen.py), so nothing will be audible until you drop an instrument
on each track. This builds correct MIDI content and structure, not sound.
"""

import time
from dataclasses import dataclass, field

from lcode_orchestrator import LCodeOrchestrator
from techno_gen import TechnoGenEngine

# --- Track roles -> track NAME (resolved to a live index via resolve_tracks(),
# never hardcoded -- inserting/removing a track shifts every index after it,
# which is exactly what broke this the first time). -------------------------

TRACK_NAMES = {
    "kick_bass":    "Kick 808 Bass",
    "sub_bass":     "Sub Bass",
    "mid_bass":     "Mid Bass",
    "snare":        "Snare",
    "clap":         "Clap",
    "hats":         "HiHats Cymbals",
    "lead_vocal":   "Lead Vocal",
    "backing_vox":  "Backing Vocals",
    "piano_guitar": "Piano Guitar",
    "pads":         "Pads Strings",
    "synth_lead":   "Synth Lead Plucks",
    "fx":           "FX Risers",
}


def resolve_tracks(orch: LCodeOrchestrator) -> dict:
    """Looks up the current track index for every role by name. Raises a
    clear error if a track is missing/renamed rather than silently using a
    stale index."""
    resolved = {}
    missing = []
    for role, name in TRACK_NAMES.items():
        track = orch.registry.get(name)
        if track is None:
            missing.append(name)
        else:
            resolved[role] = track.index
    if missing:
        raise ValueError(f"Tracks not found in live set: {missing}")
    return resolved

BEATS_PER_BAR = 4.0


@dataclass
class Section:
    name: str
    bars: int
    # role -> kwargs for TechnoGenEngine.generate_techno_pattern (euclidean tracks)
    rhythmic: dict = field(default_factory=dict)
    # role -> list of (start_beat, note, duration_beats, velocity) (melodic/chord tracks)
    melodic: dict = field(default_factory=dict)


def chord_hits(root_notes: list[int], bars: int, beats_per_hit: float = 4.0,
               duration_beats: float = 3.8, velocity: int = 90) -> list[tuple]:
    """Sustained chord stabs, one per `beats_per_hit`, across `bars` bars."""
    hits = []
    total_beats = bars * BEATS_PER_BAR
    t = 0.0
    while t < total_beats:
        for n in root_notes:
            hits.append((t, n, duration_beats, velocity))
        t += beats_per_hit
    return hits


def riser_hit(bars: int, note: int = 60, velocity: int = 100) -> list[tuple]:
    """One long swelling note spanning the whole section -- placeholder for an FX riser."""
    return [(0.0, note, bars * BEATS_PER_BAR - 0.1, velocity)]


# --- Song structure (16-bar sections unless noted) --------------------------
# Root notes are placeholders (C2=36 for low end, C3=60 mid, C4=72 vocal-chop
# register) -- once real instruments are loaded, remap to taste.

SECTIONS = [
    Section("Intro", 16,
        rhythmic={
            "kick_bass": dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "hats":      dict(root_note=42, steps=16, pulses=5, ghost_probability=0.3, swing_amount=0.12),
        }),
    Section("Build 1", 8,
        rhythmic={
            "kick_bass": dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "hats":      dict(root_note=42, steps=16, pulses=5, ghost_probability=0.3, swing_amount=0.12),
            "clap":      dict(root_note=39, steps=16, pulses=2),
        },
        melodic={"fx": riser_hit(8, note=60)}),
    Section("Groove A", 16,
        rhythmic={
            "kick_bass":  dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "hats":       dict(root_note=42, steps=16, pulses=5, ghost_probability=0.3, swing_amount=0.12),
            "clap":       dict(root_note=39, steps=16, pulses=2),
            "snare":      dict(root_note=38, steps=16, pulses=2),
            "synth_lead": dict(root_note=72, steps=16, pulses=6, note_duration_beats=0.15, swing_amount=0.15),
        }),
    Section("Break", 8,
        rhythmic={
            "hats": dict(root_note=42, steps=16, pulses=2),
        },
        melodic={
            "pads":         chord_hits([60, 63, 67], bars=8),
            "piano_guitar": [(t, 60, 0.3, 95) for t in [0.0, 1.5, 4.0, 5.5, 8.0, 9.5, 12.0, 13.5]],
            "fx":           riser_hit(8, note=64),
        }),
    Section("Build 2", 8,
        rhythmic={
            "hats":  dict(root_note=42, steps=16, pulses=10, swing_amount=0.08),
            "snare": dict(root_note=38, steps=16, pulses=10),
        },
        melodic={"fx": riser_hit(8, note=67)}),
    Section("Drop A", 16,
        rhythmic={
            "kick_bass":  dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "snare":      dict(root_note=38, steps=16, pulses=2),
            "clap":       dict(root_note=39, steps=16, pulses=3),
            "hats":       dict(root_note=42, steps=16, pulses=5, ghost_probability=0.25, swing_amount=0.12),
            "synth_lead": dict(root_note=72, steps=16, pulses=6, note_duration_beats=0.15, swing_amount=0.15),
        },
        melodic={
            "lead_vocal":   [(t, 76, 0.4, 100) for t in [0.0, 4.0, 8.0, 12.0, 32.0, 36.0, 40.0, 44.0]],
            "piano_guitar": [(t, 60, 0.3, 95) for t in [2.0, 6.0, 10.0, 14.0, 34.0, 38.0, 42.0, 46.0]],
        }),
    Section("Groove B", 16,
        rhythmic={
            "kick_bass":  dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "hats":       dict(root_note=42, steps=16, pulses=5, ghost_probability=0.3, swing_amount=0.12),
            "clap":       dict(root_note=39, steps=16, pulses=2),
            "snare":      dict(root_note=38, steps=16, pulses=2),
            "synth_lead": dict(root_note=72, steps=16, pulses=6, note_duration_beats=0.15, swing_amount=0.15),
        },
        melodic={"backing_vox": chord_hits([64, 67], bars=16, beats_per_hit=8.0, duration_beats=7.5, velocity=75)}),
    Section("Break 2", 8,
        rhythmic={"hats": dict(root_note=42, steps=16, pulses=2)},
        melodic={
            "pads":         chord_hits([60, 63, 67], bars=8),
            "backing_vox":  chord_hits([64, 67], bars=8, beats_per_hit=8.0, duration_beats=7.5, velocity=70),
            "fx":           riser_hit(8, note=64),
        }),
    Section("Build 3", 8,
        rhythmic={
            "hats":  dict(root_note=42, steps=16, pulses=10, swing_amount=0.08),
            "snare": dict(root_note=38, steps=16, pulses=10),
        },
        melodic={"fx": riser_hit(8, note=67)}),
    Section("Drop B", 16,
        rhythmic={
            "kick_bass":  dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "snare":      dict(root_note=38, steps=16, pulses=2),
            "clap":       dict(root_note=39, steps=16, pulses=3),
            "hats":       dict(root_note=42, steps=16, pulses=5, ghost_probability=0.25, swing_amount=0.12),
            "synth_lead": dict(root_note=72, steps=16, pulses=6, note_duration_beats=0.15, swing_amount=0.15),
        },
        melodic={
            "lead_vocal":   [(t, 76, 0.4, 100) for t in [0.0, 4.0, 8.0, 12.0, 32.0, 36.0, 40.0, 44.0]],
            "backing_vox":  chord_hits([64, 67], bars=16, beats_per_hit=8.0, duration_beats=7.5, velocity=80),
            "piano_guitar": [(t, 60, 0.3, 95) for t in [2.0, 6.0, 10.0, 14.0, 34.0, 38.0, 42.0, 46.0]],
        }),
    Section("Outro", 16,
        rhythmic={
            "kick_bass": dict(root_note=36, steps=16, pulses=4),
            "sub_bass":   dict(root_note=24, steps=16, pulses=4, note_duration_beats=0.3),
            "mid_bass":   dict(root_note=36, steps=16, pulses=7, swing_amount=0.1, note_duration_beats=0.15),
            "hats":      dict(root_note=42, steps=16, pulses=5, ghost_probability=0.3, swing_amount=0.12),
        }),
]


def print_song_map():
    total_bars = sum(s.bars for s in SECTIONS)
    print(f"\n=== TECH HOUSE ARRANGEMENT ({len(SECTIONS)} scenes, {total_bars} bars @ 120 BPM ~= "
          f"{total_bars * BEATS_PER_BAR * 60 / 120 / 60:.1f} min) ===")
    for i, s in enumerate(SECTIONS):
        roles = sorted(set(s.rhythmic) | set(s.melodic))
        print(f"  [{i}] {s.name:10s} {s.bars:3d} bars  -- {', '.join(roles)}")
    print("=== end song map ===\n")


def write_melodic_clip(client, track_idx: int, slot_idx: int, bars: int, hits: list[tuple]):
    clip_length = bars * BEATS_PER_BAR
    client.send_message("/live/clip_slot/delete_clip", [track_idx, slot_idx])
    time.sleep(0.3)
    client.send_message("/live/clip_slot/create_clip", [track_idx, slot_idx, clip_length])
    time.sleep(0.3)
    for start, note, dur, vel in hits:
        client.send_message("/live/clip/add/notes", [track_idx, slot_idx, note, start, dur, vel, 0])


def build(orch: LCodeOrchestrator):
    """Creates one Scene per section and writes all clip content. Idempotent
    per role -- clip_slot/delete_clip runs first so re-running replaces
    content rather than layering duplicates."""
    engine = TechnoGenEngine(orch)
    tracks = resolve_tracks(orch)

    for scene_idx, section in enumerate(SECTIONS):
        orch.client.send_message("/live/song/create_scene", [scene_idx])
        time.sleep(0.2)
        orch.client.send_message("/live/scene/set/name", [scene_idx, section.name])

        for role, kwargs in section.rhythmic.items():
            track_idx = tracks[role]
            engine.generate_techno_pattern(track_idx=track_idx, slot_idx=scene_idx,
                                            bars=section.bars, **kwargs)

        for role, hits in section.melodic.items():
            track_idx = tracks[role]
            write_melodic_clip(orch.client, track_idx, scene_idx, section.bars, hits)

        print(f"-- scene [{scene_idx}] {section.name} done --\n")


def print_to_arrangement(orch: LCodeOrchestrator):
    """
    Bakes the Session scenes into the Arrangement timeline in order, by
    enabling arrangement record and launching each scene for exactly its
    bar length -- this is the only way AbletonOSC content ends up in
    Arrangement (there's no direct 'write clip to arrangement' call).
    Real-time: takes as long as the song itself to run.
    """
    tempo = orch._query("/live/song/get/tempo", [])[0]
    seconds_per_beat = 60.0 / tempo

    orch.client.send_message("/live/song/set/record_mode", [1])
    orch.client.send_message("/live/song/set/current_song_time", [0])
    orch.client.send_message("/live/song/start_playing", [])
    time.sleep(0.3)

    for scene_idx, section in enumerate(SECTIONS):
        orch.client.send_message("/live/scene/fire", [scene_idx])
        wait_seconds = section.bars * BEATS_PER_BAR * seconds_per_beat
        print(f"printing [{scene_idx}] {section.name} ({section.bars} bars, {wait_seconds:.1f}s)...")
        time.sleep(wait_seconds)

    orch.client.send_message("/live/song/stop_playing", [])
    orch.client.send_message("/live/song/set/record_mode", [0])
    print("Printed to Arrangement.")


if __name__ == "__main__":
    orch = LCodeOrchestrator()
    try:
        print_song_map()
        orch.audit_project(verbose=False)
        build(orch)
    finally:
        orch.close()
