"""
TechnoGenEngine -- Euclidean rhythm MIDI pattern generator, with accent/
velocity dynamics, swing/humanize micro-timing, and polyrhythmic layering
across multiple tracks.

Scope note: only pattern generation is implemented here.
build_rumble_chain() (auto-building a return-track FX chain with sidechain
routing) is NOT implemented -- AbletonOSC can control devices already on a
track but can't insert new ones from the browser (same limitation as the
Serum Macro mapping earlier in this project: device insertion is a manual,
one-time GUI step, not an OSC call).
"""

import random
import time
from lcode_orchestrator import LCodeOrchestrator


def euclidean_rhythm(steps: int, pulses: int) -> list[bool]:
    """
    Bjorklund's algorithm -- distributes `pulses` onsets as evenly as
    possible across `steps` slots. E.g. euclidean_rhythm(16, 4) gives the
    classic four-on-the-floor techno kick pattern; euclidean_rhythm(16, 5)
    gives a standard Afro-Cuban/techno hat pattern.
    """
    if pulses <= 0:
        return [False] * steps
    if pulses >= steps:
        return [True] * steps

    pattern = []
    counts, remainders = [], []
    divisor = steps - pulses
    remainders.append(pulses)
    level = 0
    while remainders[level] > 1:
        counts.append(divisor // remainders[level])
        remainders.append(divisor % remainders[level])
        divisor = remainders[level]
        level += 1
    counts.append(divisor)

    def build(level):
        if level == -1:
            pattern.append(False)
        elif level == -2:
            pattern.append(True)
        else:
            for _ in range(counts[level]):
                build(level - 1)
            if remainders[level] != 0:
                build(level - 2)

    build(level)
    pattern = pattern[::-1]
    # Rotate so the pattern starts on a hit, matching how these are normally written.
    first_hit = pattern.index(True)
    return pattern[first_hit:] + pattern[:first_hit]


def accent_velocity(step_index: int, steps: int, base_velocity: int = 100,
                     downbeat_velocity: int = 127, ghost_probability: float = 0.0,
                     ghost_velocity_range: tuple[int, int] = (40, 60),
                     rng: random.Random = None) -> int:
    """
    Velocity & Accent Matrix -- a euclidean pattern of pure 1/0 hits sounds
    like a sterile MIDI metronome without this. Downbeat (step 0, and every
    quarter-bar boundary for steps=16) gets full velocity; everything else
    gets a slightly softer accent. Optionally a hit can be randomly demoted
    to a ghost note (quiet, felt more than heard -- classic hat/perc texture).
    """
    rng = rng or random
    quarter = steps // 4 if steps >= 4 else 1
    is_downbeat = (step_index % quarter == 0)
    if ghost_probability > 0 and not is_downbeat and rng.random() < ghost_probability:
        return rng.randint(*ghost_velocity_range)
    return downbeat_velocity if is_downbeat else base_velocity


def apply_swing(start_beat: float, step_index: int, step_duration: float,
                 swing_amount: float = 0.0) -> float:
    """
    Swing shifts every OFF-beat (odd-numbered) step later by a fraction of a
    step -- swing_amount=0.0 is straight/mechanical, ~0.15-0.25 is the classic
    "shuffled" tech-house/swung-hat feel, 0.66 approaches a full triplet
    swing. Only odd steps move; downbeats stay locked to the grid, which is
    what makes swing read as "pushed" rather than just "misaligned."
    """
    if step_index % 2 == 1:
        return start_beat + step_duration * swing_amount
    return start_beat


def humanize(start_beat: float, amount_beats: float = 0.0, rng: random.Random = None) -> float:
    """
    Micro-timing jitter -- a small random offset (typically 0.005-0.02 beats,
    a handful of milliseconds at club tempos) so notes don't land on a
    computer-perfect grid. Symmetric (can push early or late), independent
    per note. Set amount_beats=0 to disable (default -- opt-in, not a
    surprise mutation of an otherwise-deterministic pattern).
    """
    if amount_beats <= 0:
        return start_beat
    rng = rng or random
    return start_beat + rng.uniform(-amount_beats, amount_beats)


class TechnoGenEngine:
    def __init__(self, orchestrator: LCodeOrchestrator):
        self.orchestrator = orchestrator

    def generate_techno_pattern(self, track_idx: int, slot_idx: int, root_note: int,
                                 steps: int = 16, pulses: int = 4, bars: int = 4,
                                 velocity: int = 100, note_duration_beats: float = 0.2,
                                 downbeat_velocity: int = 127, ghost_probability: float = 0.0,
                                 swing_amount: float = 0.0, humanize_amount: float = 0.0,
                                 seed: int = None):
        """
        Writes a euclidean(steps, pulses) rhythm into a Session clip slot,
        repeated over `bars` bars of 4/4, with velocity accents + optional
        swing/humanize micro-timing. `seed` makes ghost-note/humanize
        randomness reproducible (same seed = same pattern every time) --
        omit for a fresh random feel on each call.
        """
        rng = random.Random(seed)
        client = self.orchestrator.client
        beats_per_bar = 4.0
        clip_length = beats_per_bar * bars
        step_duration = beats_per_bar / steps

        pattern = euclidean_rhythm(steps, pulses)

        client.send_message("/live/clip_slot/delete_clip", [track_idx, slot_idx])
        time.sleep(0.5)
        client.send_message("/live/clip_slot/create_clip", [track_idx, slot_idx, clip_length])
        time.sleep(0.5)

        count = 0
        for bar in range(bars):
            for i, hit in enumerate(pattern):
                if not hit:
                    continue
                start = bar * beats_per_bar + i * step_duration
                start = apply_swing(start, i, step_duration, swing_amount)
                start = humanize(start, humanize_amount, rng)
                start = max(0.0, start)  # never push a note before the clip start
                vel = accent_velocity(i, steps, base_velocity=velocity,
                                       downbeat_velocity=downbeat_velocity,
                                       ghost_probability=ghost_probability, rng=rng)
                client.send_message("/live/clip/add/notes",
                                     [track_idx, slot_idx, root_note, start,
                                      note_duration_beats, vel, 0])
                count += 1
        print(f"euclidean({steps},{pulses}) zapsáno: {count} úderů přes {bars} taktů "
              f"(pattern: {''.join('X' if h else '.' for h in pattern)}, "
              f"swing={swing_amount}, humanize={humanize_amount})")
        return count

    def generate_polyrhythmic_layer(self, layers: list[dict], bars: int = 4):
        """
        Polyrhythm & Phase Shift Engine -- writes multiple independent
        euclidean patterns to different tracks/slots in one call, so their
        different step/pulse ratios phase against each other over time
        instead of looping in lockstep. Each layer dict takes the same
        keyword arguments as generate_techno_pattern() (track_idx, slot_idx,
        root_note, steps, pulses, ...).

        Example -- kick locked to 4-on-the-floor while a shaker drifts
        against it in a 12-step cycle (true polyrhythm, not just two
        16-step patterns with different hit counts):
            engine.generate_polyrhythmic_layer([
                dict(track_idx=0, slot_idx=0, root_note=36, steps=16, pulses=4),
                dict(track_idx=1, slot_idx=0, root_note=44, steps=12, pulses=7,
                     swing_amount=0.15),
            ], bars=4)
        """
        total = 0
        for layer in layers:
            total += self.generate_techno_pattern(bars=bars, **layer)
        print(f"[POLYRHYTHM] {len(layers)} vrstev, {total} úderů celkem přes {bars} taktů")
        return total


if __name__ == "__main__":
    import sys
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 16
    pulses = int(sys.argv[2]) if len(sys.argv) > 2 else 5

    orch = LCodeOrchestrator()
    orch.audit_project(verbose=False)
    engine = TechnoGenEngine(orch)
    engine.generate_techno_pattern(track_idx=0, slot_idx=0, root_note=36,
                                    steps=steps, pulses=pulses, bars=4,
                                    ghost_probability=0.3, swing_amount=0.18,
                                    humanize_amount=0.01, seed=42)
    orch.close()
