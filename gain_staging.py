"""
L-Code Gain Staging -- sets track fader levels in a live Ableton Live 12 set
via AbletonOSC to match a fixed mixing-reference peak-dB matrix.

Dry-run first: build_plan() only READS from Live (audit + get/volume) and
prints what WOULD be written. Nothing is sent to Live until apply(plan)
is called explicitly, and apply() always snapshots the pre-change volumes
to a JSON file first so the run can be rolled back.

Honesty over completeness: a track whose name doesn't match any known
keyword is reported as UNRESOLVED and skipped, never guessed.
"""

import json
import math
import time
from dataclasses import dataclass
from pathlib import Path

from lcode_orchestrator import LCodeOrchestrator, LCodeOrchestratorError

# --- 1. Mixing reference matrix (peak dB, low..high) -----------------------

MIX_REFERENCE = {
    "KICK_808_BASS":     (-8.0, -6.0),
    "SNARE":             (-10.0, -8.0),
    "CLAP":              (-12.0, -10.0),
    "HIHATS_CYMBALS":    (-18.0, -14.0),
    "LEAD_VOCAL":        (-8.0, -6.0),
    "BACKING_VOCALS":    (-16.0, -12.0),
    "PIANO_GUITAR":      (-15.0, -12.0),
    "PADS_STRINGS":      (-18.0, -14.0),
    "SYNTH_LEAD_PLUCKS": (-15.0, -10.0),
    "FX_RISERS":         (-20.0, -18.0),
}

# --- 2. Track-name keyword -> category (case-insensitive substring match) --
# First match wins; order matters (more specific keywords first).

NAME_KEYWORDS = [
    ("808", "KICK_808_BASS"),
    ("kick", "KICK_808_BASS"),
    ("bd", "KICK_808_BASS"),
    ("bass", "KICK_808_BASS"),
    ("snare", "SNARE"),
    ("sd", "SNARE"),
    ("clap", "CLAP"),
    ("hat", "HIHATS_CYMBALS"),
    ("hh", "HIHATS_CYMBALS"),
    ("cymbal", "HIHATS_CYMBALS"),
    ("crash", "HIHATS_CYMBALS"),
    ("ride", "HIHATS_CYMBALS"),
    ("lead vocal", "LEAD_VOCAL"),
    ("lead vox", "LEAD_VOCAL"),
    ("main vocal", "LEAD_VOCAL"),
    ("backing vocal", "BACKING_VOCALS"),
    ("bv", "BACKING_VOCALS"),
    ("vocal", "LEAD_VOCAL"),
    ("vox", "LEAD_VOCAL"),
    ("piano", "PIANO_GUITAR"),
    ("guitar", "PIANO_GUITAR"),
    ("gtr", "PIANO_GUITAR"),
    ("pad", "PADS_STRINGS"),
    ("string", "PADS_STRINGS"),
    ("pluck", "SYNTH_LEAD_PLUCKS"),
    ("synth lead", "SYNTH_LEAD_PLUCKS"),
    ("lead", "SYNTH_LEAD_PLUCKS"),
    ("fx", "FX_RISERS"),
    ("riser", "FX_RISERS"),
    ("sweep", "FX_RISERS"),
]


def classify_track_name(name: str) -> str | None:
    lowered = name.lower()
    for keyword, category in NAME_KEYWORDS:
        if keyword in lowered:
            return category
    return None


# --- 3. dB <-> Live's internal 0.0-1.0 fader-parameter float ---------------
#
# Live's Track.Mixer.Volume parameter is NOT itself calibrated in dB -- it's
# a raw 0.0-1.0 float. AbletonOSC's /live/track/set/volume passes that raw
# float straight through with no conversion. The two fixed points Ableton's
# own UI is known to use are value=0.85 -> 0dB and value=1.0 -> +6dB; below
# 0.85 there's no officially published curve, so this uses the standard
# reverse-engineered approximation (log-scaled toward 0.85, same one used by
# most third-party Live-API tooling). Treat it as "close enough for gain
# staging", not a certified-accurate dB meter -- verify by ear/meter in Live.

UNITY_VALUE = 0.85  # value at 0 dB
UNITY_DB_AT_MAX = 6.0  # dB at value = 1.0


def db_to_live_float(db: float) -> float:
    if db >= 0:
        return min(1.0, UNITY_VALUE + (db / UNITY_DB_AT_MAX) * (1.0 - UNITY_VALUE))
    if db <= -70:
        return 0.0
    return max(0.0, UNITY_VALUE * (10 ** (db / 20.0)))


def live_float_to_db(value: float) -> float:
    if value <= 0:
        return float("-inf")
    if value >= UNITY_VALUE:
        return (value - UNITY_VALUE) / (1.0 - UNITY_VALUE) * UNITY_DB_AT_MAX
    return 20.0 * math.log10(value / UNITY_VALUE)


# --- 4. Plan construction (dry-run) -----------------------------------------

@dataclass
class PlannedChange:
    track_index: int
    track_name: str
    category: str
    current_value: float
    current_db: float
    target_db: float
    target_value: float


def build_plan(orch: LCodeOrchestrator, overrides: dict[str, str] | None = None) -> tuple[list[PlannedChange], list[str]]:
    """
    Read-only: audits the live set, classifies every track by name (or by
    `overrides` = {track_name: category}), and returns
    (planned_changes, unresolved_track_names). Writes nothing.
    """
    overrides = overrides or {}
    orch.audit_project(verbose=False)

    planned: list[PlannedChange] = []
    unresolved: list[str] = []

    for track_name, track in orch.registry.items():
        is_foldable = orch._query("/live/track/get/is_foldable", [track.index])[1]
        if is_foldable:
            # Group/folder track (e.g. DRUMS, VOCALS) -- its fader sits on top
            # of the already gain-staged child tracks, so it must never get a
            # per-instrument target applied on top of them.
            continue

        category = overrides.get(track_name) or classify_track_name(track_name)
        if category is None:
            unresolved.append(track_name)
            continue
        if category not in MIX_REFERENCE:
            raise ValueError(f"Unknown category {category!r} for track {track_name!r}")

        low_db, high_db = MIX_REFERENCE[category]
        target_db = (low_db + high_db) / 2.0

        current_value = orch._query("/live/track/get/volume", [track.index])[1]
        current_db = live_float_to_db(current_value)
        target_value = db_to_live_float(target_db)

        planned.append(PlannedChange(
            track_index=track.index,
            track_name=track_name,
            category=category,
            current_value=current_value,
            current_db=current_db,
            target_db=target_db,
            target_value=target_value,
        ))

    return planned, unresolved


def print_plan(planned: list[PlannedChange], unresolved: list[str]) -> None:
    print("\n=== DRY RUN: gain staging plan (nothing written yet) ===")
    for p in planned:
        cur = "-inf" if p.current_db == float("-inf") else f"{p.current_db:+.1f} dB"
        print(f"  [{p.track_index}] {p.track_name:20s} {p.category:20s} "
              f"{cur:>9s} -> {p.target_db:+.1f} dB  (fader {p.current_value:.3f} -> {p.target_value:.3f})")
    if unresolved:
        print("\n  UNRESOLVED (no keyword match -- skipped, not guessed):")
        for name in unresolved:
            print(f"    - {name}")
    print("=== end dry run ===\n")


# --- 5. Snapshot (rollback) + apply -----------------------------------------

def snapshot_path(project_dir: Path) -> Path:
    ts = time.strftime("%Y%m%d-%H%M%S")
    return project_dir / f"gain_staging_snapshot_{ts}.json"


def apply(orch: LCodeOrchestrator, planned: list[PlannedChange], project_dir: Path) -> Path:
    """
    Writes a rollback snapshot FIRST, then sends every planned volume change.
    Returns the snapshot path so it can be restored with restore().
    """
    snap = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tracks": [
            {"track_index": p.track_index, "track_name": p.track_name, "volume": p.current_value}
            for p in planned
        ],
    }
    path = snapshot_path(project_dir)
    path.write_text(json.dumps(snap, indent=2))
    print(f"Rollback snapshot written to {path}")

    for p in planned:
        orch.client.send_message("/live/track/set/volume", [p.track_index, p.target_value])
        print(f"  set [{p.track_index}] {p.track_name} -> {p.target_value:.3f} ({p.target_db:+.1f} dB)")

    return path


def restore(orch: LCodeOrchestrator, snapshot_file: Path) -> None:
    """Rolls back a previous apply() using its snapshot JSON."""
    snap = json.loads(snapshot_file.read_text())
    for entry in snap["tracks"]:
        orch.client.send_message("/live/track/set/volume", [entry["track_index"], entry["volume"]])
        print(f"  restored [{entry['track_index']}] {entry['track_name']} -> {entry['volume']:.3f}")


# --- 6. CLI entry point ------------------------------------------------------

def main():
    project_dir = Path(__file__).parent
    orch = LCodeOrchestrator()
    try:
        planned, unresolved = build_plan(orch)
        print_plan(planned, unresolved)

        if not planned:
            print("Nothing to apply -- no track matched a known category.")
            return

        answer = input("Apply these changes to the live set? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted -- nothing written.")
            return

        apply(orch, planned, project_dir)
        print("Done.")
    except LCodeOrchestratorError as e:
        print(f"Orchestrator error: {e}")
    finally:
        orch.close()


if __name__ == "__main__":
    main()
