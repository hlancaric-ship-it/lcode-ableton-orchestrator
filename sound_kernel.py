"""
L-Code Kernel -- low-level sound-design primitives that archetypes/intent
resolution build on top of. Each primitive maps to one or more semantic
functions from semantic_profiles.py and goes through the same live-registry
check as everything else (LCodeOrchestrator.execute_command) -- no primitive
here can silently send a wrong/stale OSC index.

Honesty over completeness: a primitive whose underlying Ableton parameter
isn't mapped in Live yet, or whose device doesn't exist on the track at all
(e.g. no compressor/reverb device loaded), raises NotImplementedError with a
clear explanation -- it does NOT pretend to succeed. See each method's
docstring for what it currently needs to actually work.
"""

from lcode_orchestrator import LCodeOrchestrator, LCodeOrchestratorError
from semantic_profiles import PLUGIN_EXPOSED


class KernelNotReady(Exception):
    """Raised when a primitive's underlying parameter/device isn't available
    yet -- distinct from LCodeOrchestratorError so callers can tell 'this
    needs more Live-side setup' apart from 'this OSC call itself failed'."""
    pass


class SoundGenerator:
    def __init__(self, orchestrator: LCodeOrchestrator, track_name: str, device_name: str = "Serum 2"):
        self.orchestrator = orchestrator
        self.track_name = track_name
        self.device_name = device_name

    def _send(self, function_name: str, value: float, label: str):
        exposed = PLUGIN_EXPOSED.get(self.device_name, {})
        function_to_param = {fn: p for p, fn in exposed.items()}
        param = function_to_param.get(function_name)
        if param is None:
            raise KernelNotReady(
                f"{label} potřebuje funkci '{function_name}', která zatím není "
                f"namapovaná v Live (Configure -> Macro). Nic se neodeslalo.")
        try:
            self.orchestrator.execute_command(self.track_name, self.device_name, param, value)
        except LCodeOrchestratorError as e:
            raise KernelNotReady(f"{label}: {e}") from e

    # --- 1. Modulacni primitiva (Motion Layer) ---

    def set_osc_morph(self, target_osc: str, wavetable_index: float):
        """target_osc: 'A' or 'B'. wavetable_index: 0.0-1.0."""
        function = "wt_pos" if target_osc.upper() == "B" else "a_wt_pos"
        self._send(function, wavetable_index, f"set_osc_morph({target_osc})")

    def apply_envelope_shape(self, envelope_id: str, attack: float, decay: float,
                              sustain: float, release: float):
        """envelope_id: 'ENV_1' or 'ENV_2'. All values 0.0-1.0."""
        prefix = "env1" if "1" in envelope_id else "env2"
        for suffix, value in [("attack", attack), ("decay", decay),
                               ("sustain", sustain), ("release", release)]:
            self._send(f"{prefix}_{suffix}", value, f"apply_envelope_shape({envelope_id}.{suffix})")

    def link_lfo_to_param(self, lfo_id: str, target_param: str, amount: float):
        """NOT YET IMPLEMENTABLE: AbletonOSC/Serum's Configure-mapped Macros
        expose a knob's current VALUE, not its modulation ROUTING -- wiring
        an LFO to a new target has to be done inside Serum's own mod matrix
        by hand, there's no OSC call for it. Raises unconditionally so this
        isn't mistaken for something that quietly no-ops."""
        raise NotImplementedError(
            "link_lfo_to_param: LFO->parameter routing must be set inside Serum's "
            "own mod matrix (drag LFO onto the target knob) -- not controllable via "
            "AbletonOSC. Once routed by hand, the DESTINATION knob's resulting value "
            "can be automated normally through the usual Macro mapping.")

    # --- 2. Spektralni a fazova primitiva (Tone Layer) ---

    def set_fm_amount(self, osc_a: str, osc_b: str, intensity: float):
        """NOT YET IMPLEMENTABLE: Serum 2's FM amount lives in the OSC B
        'Warp' section set to an FM warp mode, not as its own dedicated
        parameter -- would need 'B Warp' mapped AND B's warp mode set to FM
        first. Use set_warp_mode('B', mode='FM') once that primitive exists,
        or map 'B Warp Mode' + 'B Warp' in Configure and use set_osc_morph-
        style direct calls in the meantime."""
        raise NotImplementedError(
            "set_fm_amount: needs 'B Warp Mode' set to an FM mode plus 'B Warp' "
            "amount -- both must be mapped in Live's Configure first. Not wired yet.")

    def set_unison_spread(self, osc_id: str, voices: float, detune: float):
        """osc_id: 'A' or 'B'. voices/detune: 0.0-1.0 (normalized, not raw voice count)."""
        prefix = osc_id.lower()
        self._send(f"{prefix}_unison_voices", voices, f"set_unison_spread({osc_id}).voices")
        self._send(f"{prefix}_unison_detune", detune, f"set_unison_spread({osc_id}).detune")

    def set_filter_topology(self, filter_type: float, cutoff: float,
                             resonance: float, drive: float):
        """filter_type: 0.0-1.0 (position in Serum's filter type list, not a name --
        Filter 1 Type is a continuous parameter, see semantic_profiles.py filter_type)."""
        self._send("filter_type", filter_type, "set_filter_topology.type")
        self._send("filter_cutoff", cutoff, "set_filter_topology.cutoff")
        self._send("filter_resonance", resonance, "set_filter_topology.resonance")
        self._send("filter_drive", drive, "set_filter_topology.drive")

    # --- 3. Dynamicka a efektova vrstva (Pressure Layer) ---

    def setup_compression_chain(self, source_track: str, target_track: str,
                                 ratio: float, release: float):
        """NOT YET IMPLEMENTABLE: no compressor device is loaded on any track
        in the current session (audit_project() only found Serum 2 on
        1-Serum 2) -- sidechain compression needs an actual Compressor
        device added to the target track first (drag from Live's browser),
        with its sidechain input routed from source_track. AbletonOSC can't
        insert devices from the browser, only control ones already there."""
        raise NotImplementedError(
            "setup_compression_chain: no Compressor device exists on any track yet. "
            "Drag one onto the target track in Live first, then this can control its "
            "ratio/release/sidechain params once it shows up in audit_project()."
        )

    def apply_saturation(self, target_track: str, saturation_type: str, drive_amount: float):
        """Maps to Serum's own Filter Drive for now (the only saturation-ish
        parameter currently mapped). A dedicated Distortion FX device isn't
        loaded, so `saturation_type` is currently ignored -- only drive_amount
        does anything real."""
        self._send("filter_drive", drive_amount, f"apply_saturation({target_track})")

    def setup_spatial_depth(self, target_track: str, room_size: float, dry_wet: float):
        """NOT YET IMPLEMENTABLE: no Reverb device is loaded/mapped on the
        target track (the A-Reverb/B-Delay return tracks exist in the set
        but aren't in PLUGIN_EXPOSED yet -- their sends would need mapping,
        or the return track devices need their own audit_project() entries)."""
        raise NotImplementedError(
            "setup_spatial_depth: A-Reverb/B-Delay return tracks exist in the set but "
            "aren't exposed as controllable parameters yet -- their own devices need "
            "Configure-mapping the same way Serum 2's macros were."
        )

    def craft_techno_stab(self):
        """Example composite primitive -- builds a stab from only the
        primitives that actually work right now. Raises KernelNotReady with
        a clear message the moment it hits one that isn't ready, rather than
        applying half a sound silently."""
        self.set_osc_morph("B", 0.85)
        self.set_unison_spread("A", 0.6, 0.15)
        self.set_filter_topology(filter_type=0.0, cutoff=0.45, resonance=0.6, drive=0.5)
        self.apply_saturation(self.track_name, "Hard_Clip", 0.4)
        self.apply_envelope_shape("ENV_1", attack=0.01, decay=0.3, sustain=0.0, release=0.2)


if __name__ == "__main__":
    orch = LCodeOrchestrator()
    orch.audit_project(verbose=False)
    gen = SoundGenerator(orch, track_name="1-Serum 2")
    try:
        gen.craft_techno_stab()
        print("techno stab aplikován kompletně")
    except KernelNotReady as e:
        print(f"[ZASTAVENO] {e}")
    orch.close()
