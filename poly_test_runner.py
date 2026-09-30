"""
L-Code Poly Test Runner -- creates a second MIDI track and deploys a
polyrhythmic pattern onto it via TechnoGenEngine, so two different
euclidean(steps, pulses) cycles can phase against each other in Live.

Corrected against AbletonOSC's actual source (see conversation) -- the
original pseudocode used /live/track/create_midi, set_name, and
/live/clip/add_note, none of which exist. Real endpoints:
  /live/song/create_midi_track [index]
  /live/track/set/name [track_index, name]
  /live/clip/add/notes [track_index, clip_index, pitch, start, dur, vel, mute]
"""

import time
from lcode_orchestrator import LCodeOrchestrator
from techno_gen import TechnoGenEngine


class LCodePolyTestRunner:
    def __init__(self, orchestrator: LCodeOrchestrator):
        self.orchestrator = orchestrator
        self.engine = TechnoGenEngine(orchestrator)

    def ensure_midi_track(self, track_name: str, insert_index: int = -1) -> int:
        """
        Creates a new MIDI track (unless one with this name already exists,
        checked via a fresh audit so repeated runs don't pile up duplicate
        tracks) and returns its track_index. insert_index=-1 appends at the
        end of the track list (Live's own convention for "create_*_track").
        """
        self.orchestrator.audit_project(verbose=False)
        if track_name in self.orchestrator.registry:
            idx = self.orchestrator.registry[track_name].index
            print(f"[L-CODE] Stopa '{track_name}' už existuje (index {idx}), nevytvářím duplicitu.")
            return idx

        print(f"[L-CODE] Vytvářím novou MIDI stopu '{track_name}'...")
        self.orchestrator.client.send_message("/live/song/create_midi_track", [insert_index])
        time.sleep(0.5)

        self.orchestrator.audit_project(verbose=False)
        num_tracks = len(self.orchestrator.registry)
        new_idx = num_tracks - 1  # create_midi_track(-1) appends at the end
        self.orchestrator.client.send_message("/live/track/set/name", [new_idx, track_name])
        time.sleep(0.3)
        print(f"[L-CODE] Stopa '{track_name}' vytvořena na indexu {new_idx}")
        return new_idx

    def deploy_polyrhythmic_track(self, track_name: str, root_note: int,
                                   steps: int, pulses: int, bars: int = 4,
                                   swing_amount: float = 0.0, humanize_amount: float = 0.0,
                                   ghost_probability: float = 0.0, seed: int = None):
        """
        Ensures the target MIDI track exists, then writes a
        euclidean(steps, pulses) pattern onto it via TechnoGenEngine (which
        already handles accent velocity, swing and humanize correctly --
        no need to reimplement note injection by hand here).
        """
        track_idx = self.ensure_midi_track(track_name)
        count = self.engine.generate_techno_pattern(
            track_idx=track_idx, slot_idx=0, root_note=root_note,
            steps=steps, pulses=pulses, bars=bars,
            swing_amount=swing_amount, humanize_amount=humanize_amount,
            ghost_probability=ghost_probability, seed=seed,
        )
        print(f"[L-CODE] Polyrytmus zapsán na '{track_name}' (index {track_idx}): {count} úderů")
        return track_idx


if __name__ == "__main__":
    orch = LCodeOrchestrator()
    orch.audit_project(verbose=False)
    runner = LCodePolyTestRunner(orch)

    # Kick zustava na existujici stope 1-Serum 2 (16/4, ctverka), nova stopa
    # dostane 12/7 perkusni cyklus, ktery proti ni bude "driftovat" -- 16 a 12
    # kroku nemaji spolecny nasobek v ramci jednoho taktu, takze se jejich
    # vzajemna faze pri kazdem opakovani mirne posune (skutecny polyrytmus,
    # ne jen dva ruzne rytmy se stejnou delkou smycky).
    runner.deploy_polyrhythmic_track(
        track_name="02_POLY_PERC_12_7", root_note=44,
        steps=12, pulses=7, bars=4, swing_amount=0.15, humanize_amount=0.008, seed=7,
    )
    orch.close()
