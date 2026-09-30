"""
L-Code Device Chain Builder -- gain staging + a standard device chain
(Utility / EQ Eight / Compressor) applied to every track in the live set,
based on the track's name.

Depends on an AbletonOSC extension made specifically for this: stock
AbletonOSC can only control devices already sitting on a track (get/
num_devices, get/devices/*) -- there is no browser exposed over OSC, so it
cannot insert a device that isn't there yet. /live/track/insert_device was
added to the installed control surface
(~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/abletonosc/track.py)
using Live.Application.get_application().browser + browser.load_item(),
the same mechanism Live's own UI uses for double-click-load from the
device browser. If that extension isn't installed, insert_device() below
raises instead of silently doing nothing.

Honesty over completeness -- what IS and ISN'T precisely calibrated here:
  - Track fader gain staging (gain_staging.py): dB<->float conversion uses
    Live's two published anchor points (0.85=0dB, 1.0=+6dB) -- reasonably
    trustworthy.
  - EQ Eight Frequency: AbletonOSC exposes it as a raw 0.0-1.0 parameter,
    not Hz. Uses the commonly-cited 3-decade log curve (20Hz..20kHz over
    0..1) -- a community approximation, not an Ableton-published spec.
    Verify the cutoff by eye in Live after running this.
  - EQ Eight Filter Type / Filter On, Utility Gain, Compressor Device On:
    exact, documented, safe to trust.
  - Compressor Threshold/Ratio/Attack/Release: AbletonOSC exposes these as
    raw 0.0-1.0 too, and unlike Volume there is NO published anchor point
    for their dB/ms curves. Rather than fabricate a curve and silently set
    a wrong number, this script leaves them at Live's own factory-default
    Compressor values (which are already sane starting points for gentle
    vocal/bass leveling) and only sets what's unambiguous (Device On,
    Dry/Wet=100%). Tune Threshold/Ratio/Attack/Release by ear in Live.
  - Utility Gain is left at 0 dB (unity) on purpose: the track fader
    (gain_staging.py) is the single source of truth for headroom targets.
    Setting Utility's Gain to the same matrix value on top of the fader
    would double-attenuate every track -- a real mixing bug, not a safe
    default -- so it's deliberately not done here.
"""

import time

from lcode_orchestrator import LCodeOrchestrator, LCodeOrchestratorError
from gain_staging import MIX_REFERENCE, classify_track_name, build_plan, apply as apply_gain_staging

# --- EQ Eight helpers --------------------------------------------------------

EQ_FILTER_TYPE_LOW_CUT_12 = 1.0  # "Low Cut 12 dB/oct" -- Live's built-in filter-type enum for band 1

def hz_to_eq8_freq_param(hz: float) -> float:
    """
    EQ Eight's '<band> Frequency <A|B>' parameter is raw 0.0-1.0, not Hz.
    Community-documented curve: 20 Hz at 0.0, 20 kHz at 1.0, log across
    3 decades -- freq = 20 * 1000**value  =>  value = log10(freq/20) / 3.
    """
    import math
    value = math.log10(hz / 20.0) / 3.0
    return max(0.0, min(1.0, value))


# --- Chain rules by category --------------------------------------------------
# Every classified track gets Utility (Gain left at 0 dB -- see module docstring).
# Every classified track also gets EQ Eight with a low-cut on band 1:
#   - kick/bass roles: 30 Hz, rumble/DC removal only, doesn't touch the
#     musical sub content.
#   - everything else: 90 Hz, standard vocal/instrument cleanup HPF.
# Compressor (factory defaults, Device On + Dry/Wet=100% only) goes on
# Lead Vocal and the bass tracks, per the brief ("Lead Vocal a Bass").

LOW_CUT_ROLES_HZ = {
    "KICK_808_BASS": 30.0,
}
DEFAULT_HPF_HZ = 90.0

COMPRESSOR_CATEGORIES = {"LEAD_VOCAL"}
COMPRESSOR_NAME_HINT = ("bass",)  # also compress anything with "bass" in the track name (Sub Bass, Mid Bass, Kick 808 Bass)


def insert_device_if_missing(orch: LCodeOrchestrator, track_idx: int, track_name: str,
                               device_name: str, existing_devices: set) -> bool:
    if device_name in existing_devices:
        print(f"  [{track_idx}] {track_name}: {device_name} already present, skipping insert")
        return False
    try:
        orch.client.send_message("/live/track/insert_device", [track_idx, device_name])
    except LCodeOrchestratorError as e:
        raise LCodeOrchestratorError(
            f"insert_device failed for {track_name!r}/{device_name!r} -- is the extended "
            f"AbletonOSC control surface (with /live/track/insert_device) loaded? {e}")
    time.sleep(0.8)
    print(f"  [{track_idx}] {track_name}: inserted {device_name}")
    return True


def configure_eq_low_cut(orch: LCodeOrchestrator, track_idx: int, freq_hz: float):
    param_value = hz_to_eq8_freq_param(freq_hz)
    for param_name, value in [
        ("1 Filter On A", 1.0),
        ("1 Filter Type A", EQ_FILTER_TYPE_LOW_CUT_12),
        ("1 Frequency A", param_value),
    ]:
        orch.client.send_message("/live/device/set/parameter/value", [track_idx, _eq_device_index(orch, track_idx), _param_index(orch, track_idx, "EQ Eight", param_name), value])


def _eq_device_index(orch, track_idx):
    track = [t for t in orch.registry.values() if t.index == track_idx][0]
    return track.devices["EQ Eight"].index


def _param_index(orch, track_idx, device_name, param_name):
    track = [t for t in orch.registry.values() if t.index == track_idx][0]
    return track.devices[device_name].params[param_name].index


import re


def _parse_number(s: str) -> float:
    """Parses a Live parameter display string to a float. Normalizes bare-
    seconds units to milliseconds (Attack/Release switch from "ms" to "s"
    display above ~1000ms -- e.g. "1.00 s" -> 1000.0) so a single numeric
    target in ms works across the whole raw 0-1 range."""
    lowered = s.lower()
    if "-inf" in lowered:
        return float("-inf")
    if "inf" in lowered:
        return float("inf")
    m = re.search(r"-?\d+\.?\d*", s)
    if m is None:
        raise ValueError(f"No number found in device value string {s!r}")
    value = float(m.group(0))
    if "ms" not in lowered and re.search(r"\bs\b", lowered):
        value *= 1000.0
    return value


def _read_display_value(orch, track_idx, device_idx, param_idx) -> float:
    result = orch._query("/live/device/get/parameter/value_string", [track_idx, device_idx, param_idx])
    return _parse_number(result[-1])


def set_param_to_display_target(orch: LCodeOrchestrator, track_idx: int, device_idx: int, param_idx: int,
                                  target: float, raw_min: float = 0.0, raw_max: float = 1.0,
                                  tolerance: float = 0.05, max_iters: int = 25) -> float:
    """
    Binary-searches the device's raw 0.0-1.0 parameter for the raw value
    whose Live-displayed number (via str_for_value, same text the UI shows)
    matches `target` -- e.g. target=-18.0 for a Threshold of "-18.00 dB".
    This is empirically verified against Live itself, not a guessed curve.
    Assumes the raw<->display relationship is monotonic (true for
    Threshold/Ratio/Attack/Release).
    """
    def read_at(raw):
        orch.client.send_message("/live/device/set/parameter/value", [track_idx, device_idx, param_idx, raw])
        time.sleep(0.05)
        return _read_display_value(orch, track_idx, device_idx, param_idx)

    low, high = raw_min, raw_max
    value_at_low = read_at(low)
    value_at_high = read_at(high)
    increasing = value_at_high > value_at_low

    if not (min(value_at_low, value_at_high) <= target <= max(value_at_low, value_at_high)):
        raise ValueError(f"target {target} outside this parameter's display range [{value_at_low}, {value_at_high}]")

    for _ in range(max_iters):
        mid = (low + high) / 2.0
        current = read_at(mid)
        if abs(current - target) <= tolerance:
            return mid
        higher_than_target = current > target
        if higher_than_target == increasing:
            high = mid
        else:
            low = mid

    return (low + high) / 2.0


# Safe, moderate default targets for gentle vocal/bass dynamics leveling
# (standard engineering starting points, not squashed/limiter-style settings).
COMPRESSOR_TARGETS = {
    "Threshold": -18.0,  # dB
    "Ratio": 3.0,        # :1
    "Attack": 10.0,      # ms
    "Release": 100.0,    # ms
}


def configure_compressor_safe_defaults(orch: LCodeOrchestrator, track_idx: int):
    comp_idx = _eq_device_index_generic(orch, track_idx, "Compressor")
    dev_on_idx = _param_index(orch, track_idx, "Compressor", "Device On")
    dry_wet_idx = _param_index(orch, track_idx, "Compressor", "Dry/Wet")
    orch.client.send_message("/live/device/set/parameter/value", [track_idx, comp_idx, dev_on_idx, 1.0])
    orch.client.send_message("/live/device/set/parameter/value", [track_idx, comp_idx, dry_wet_idx, 1.0])

    for param_name, target in COMPRESSOR_TARGETS.items():
        param_idx = _param_index(orch, track_idx, "Compressor", param_name)
        achieved_raw = set_param_to_display_target(orch, track_idx, comp_idx, param_idx, target)
        display = _read_display_value(orch, track_idx, comp_idx, param_idx)
        print(f"    Compressor {param_name}: target {target} -> raw {achieved_raw:.3f} (display ~{display})")


def _eq_device_index_generic(orch, track_idx, device_name):
    track = [t for t in orch.registry.values() if t.index == track_idx][0]
    return track.devices[device_name].index


def build_device_chains(orch: LCodeOrchestrator):
    orch.audit_project(verbose=False)

    for track_name, track in list(orch.registry.items()):
        is_foldable = orch._query("/live/track/get/is_foldable", [track.index])[1]
        if is_foldable:
            continue  # group/folder tracks (DRUMS, VOCALS, MELODICS) get no device chain

        category = classify_track_name(track_name)
        if category is None:
            print(f"  [{track.index}] {track_name}: no category match, skipping device chain")
            continue

        existing = set(track.devices.keys())
        print(f"-- {track_name} ({category}) --")

        insert_device_if_missing(orch, track.index, track_name, "Utility", existing)
        # Utility Gain intentionally left at 0 dB -- see module docstring.

        eq_inserted = insert_device_if_missing(orch, track.index, track_name, "EQ Eight", existing)
        if eq_inserted or "EQ Eight" in existing:
            orch.audit_project(verbose=False)
            freq_hz = LOW_CUT_ROLES_HZ.get(category, DEFAULT_HPF_HZ)
            configure_eq_low_cut(orch, track.index, freq_hz)
            print(f"  [{track.index}] {track_name}: EQ Eight low-cut @ {freq_hz:.0f} Hz")

        wants_compressor = category in COMPRESSOR_CATEGORIES or any(h in track_name.lower() for h in COMPRESSOR_NAME_HINT)
        if wants_compressor:
            comp_inserted = insert_device_if_missing(orch, track.index, track_name, "Compressor", existing)
            if comp_inserted or "Compressor" in existing:
                orch.audit_project(verbose=False)
                configure_compressor_safe_defaults(orch, track.index)
                print(f"  [{track.index}] {track_name}: Compressor on (factory defaults, Dry/Wet=100%)")

        print()


if __name__ == "__main__":
    orch = LCodeOrchestrator()
    try:
        orch.audit_project(verbose=False)

        print("=== Step 1: gain staging (track faders) ===")
        planned, unresolved = build_plan(orch)
        if unresolved:
            print("UNRESOLVED (skipped, not guessed):", unresolved)
        if planned:
            apply_gain_staging(orch, planned, __import__("pathlib").Path(__file__).parent)

        print("\n=== Step 2: device chains (Utility / EQ Eight / Compressor) ===")
        build_device_chains(orch)
    finally:
        orch.close()
