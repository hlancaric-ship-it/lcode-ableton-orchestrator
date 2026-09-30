import sys
import time
from lcode_orchestrator import LCodeOrchestrator
from semantic_profiles import resolve_intent, build_notes_for_archetype

TRACK_NAME = "1-Serum 2"
DEVICE = "Serum 2"
TRACK_IDX, SLOT_IDX = 0, 0
CLIP_LENGTH_BEATS = 16.0
ROOT_NOTE = 36  # C1


def apply_intent(orch: LCodeOrchestrator, text: str):
    changes = resolve_intent(text, plugin_name=DEVICE)
    if changes:
        print("Sémantický rozbor:")
        for c in changes:
            status = "OVLADATELNÉ" if c.ableton_param else "zatím NEmapováno v Live"
            print(f"  - {c.function} -> {c.target_value:.2f}  [{status}]")
        print("\nOdesílám, co je reálně mapované:")
        for c in changes:
            if c.ableton_param:
                orch.execute_command(TRACK_NAME, DEVICE, c.ableton_param, c.target_value)
                print(f"  {c.ableton_param} -> {c.target_value:.2f}  [OK]")
    else:
        print("Žádná zvuková charakteristika nerozpoznána.")

    notes = build_notes_for_archetype(text, root_note=ROOT_NOTE)
    if notes:
        print(f"\nRozpoznán archetyp -- přepisuji noty ({len(notes)} not)...")
        orch.client.send_message("/live/clip_slot/delete_clip", [TRACK_IDX, SLOT_IDX])
        time.sleep(0.5)
        orch.client.send_message("/live/clip_slot/create_clip", [TRACK_IDX, SLOT_IDX, CLIP_LENGTH_BEATS])
        time.sleep(0.5)
        for pitch, start, dur, vel in notes:
            orch.client.send_message("/live/clip/add/notes",
                                      [TRACK_IDX, SLOT_IDX, pitch, start, dur, vel, 0])
        print("noty zapsany do Session klipu")
        print_to_arrangement(orch)
    else:
        print("\n(žádný rozpoznaný archetyp -> noty beze změny)")


def print_to_arrangement(orch: LCodeOrchestrator):
    """Always write the result into Arrangement -- see feedback_ableton_arrangement_default
    memory: Jan wants this every time, not left sitting in the Session clip.
    Reuses orch's own OSC client/server (AbletonOSC always replies to the one
    fixed receive port the orchestrator already bound -- a second server on
    a different port would never receive anything)."""
    client = orch.client
    print("Tisknu do Arrangement...")
    client.send_message("/live/song/stop_all_clips", [])
    time.sleep(0.5)
    client.send_message("/live/song/stop_playing", [])
    time.sleep(0.5)
    client.send_message("/live/song/set/current_song_time", [0.0])
    time.sleep(0.3)
    client.send_message("/live/song/set/back_to_arranger", [0])
    time.sleep(0.3)
    client.send_message("/live/track/set/arm", [TRACK_IDX, 1])
    time.sleep(0.3)
    client.send_message("/live/clip_slot/fire", [TRACK_IDX, SLOT_IDX])
    time.sleep(1.0)
    client.send_message("/live/song/set/current_song_time", [0.0])
    client.send_message("/live/song/set/record_mode", [1])

    target = CLIP_LENGTH_BEATS - 0.3
    deadline = time.time() + 15
    current_time = 0.0
    while current_time < target and time.time() < deadline:
        try:
            current_time = orch._query("/live/song/get/current_song_time", [], timeout=0.5)[0]
        except Exception:
            pass

    client.send_message("/live/song/stop_playing", [])
    time.sleep(0.3)
    client.send_message("/live/song/set/record_mode", [0])
    client.send_message("/live/track/set/arm", [TRACK_IDX, 0])
    client.send_message("/live/song/stop_all_clips", [])
    print(f"hotovo -- vytisknuto do Arrangement (beat {current_time:.2f})")


if __name__ == "__main__":
    text = " ".join(sys.argv[1:]) or "chci poradnej techno peak lead"
    orch = LCodeOrchestrator()
    orch.audit_project(verbose=False)
    print(f"Intent: {text!r}\n")
    apply_intent(orch, text)
    orch.close()
