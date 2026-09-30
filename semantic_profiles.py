"""
L-Code Semantic Profile: Xfer Serum (Master Matrix)

Two layers, kept deliberately separate:

1. SERUM2_KNOWLEDGE -- the full acoustic/synthesis knowledge base (what each
   function DOES to the sound). This is reference knowledge, independent of
   whether Live can currently reach that parameter.

2. SERUM2_EXPOSED_PARAMS -- the actionable subset: which of those functions
   are CURRENTLY wired to an Ableton parameter name via Configure + Macro
   Control (see lcode_orchestrator.py's audit_project output for the live
   ground truth). A function only becomes controllable once it has an entry
   here; everything else is real knowledge but not yet actionable.

Resolving intent always reports BOTH what it would change semantically and
which of those changes it can actually send right now -- never silently
pretends full coverage it doesn't have.
"""

import unicodedata

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class SemanticFunction:
    function: str
    category: str
    description: str
    param_range: str = ""
    direction: Literal["up", "down"] = "up"  # which way "more of this quality" moves the value


SERUM2_KNOWLEDGE: dict[str, SemanticFunction] = {
    # --- Oscillators (OSC A / OSC B) ---
    "pitch_semitones": SemanticFunction(
        "pitch_semitones", "oscillator",
        "Základní tónová výška oscilátoru. Skok o 12 = oktáva. "
        "Sub-basy: -12 až -24. Harmonické vrstvy v leadech: kladné hodnoty.",
        "-127 až +127 půltónů",
    ),
    "pitch_cents": SemanticFunction(
        "pitch_cents", "oscillator",
        "Jemné rozladění. Sjednocuje nebo rozbřeďuje zvuk pro tlustší, "
        "analogovější, širší charakter.",
        "-100 až +100 centů",
    ),
    "wt_pos": SemanticFunction(
        "wt_pos", "oscillator",
        "Pozice ve wavetable. Nižší = kulatější/sub-basovější/jemnější (sine/triangle). "
        "Vyšší = ostré, kovové, harmonicky bohaté, agresivní.",
        "0.0-1.0", direction="up",
    ),
    "warp_mode": SemanticFunction(
        "warp_mode", "oscillator",
        "Deformace vlnové délky (FM/AM/Sync/Bend/Asym). Trhá spektrum, přidává "
        "extrémní vyšší harmonické. Bzučivé, industriální, techno leady/hoovers.",
        direction="up",
    ),
    "unison_voices": SemanticFunction(
        "unison_voices", "oscillator",
        "Počet skládaných kopií oscilátoru. 1 = čistý tenký tón. 7+ = masivní "
        "široká stěna (supersaw/tech-house stab).",
        "1-16 hlasů",
    ),
    "unison_detune": SemanticFunction(
        "unison_detune", "oscillator",
        "Rozptyl hlasů v centech. Nízké (5-15%) = tělo/tloušťka. "
        "Vysoké (50%+) = rozplizlé, psychedelické, supersaw prostor.",
    ),
    "noise_pitch_fine": SemanticFunction(
        "noise_pitch_fine", "oscillator",
        "Jemné rozladění NOISE oscilátoru. Ovlivňuje, jak se šumová vrstva "
        "barevně sjednotí/odliší od ostatních oscilátorů -- šum se dá tímhle "
        "trochu 'naladit' k tónu místo aby byl čistě bílý.",
        "-100 až +100 centů",
    ),
    "osc_level": SemanticFunction(
        "osc_level", "oscillator",
        "Hlasitost oscilátoru vůči zbytku -- určuje, jestli dominuje měkký "
        "OSC A nebo řezavý digitální/šumový OSC B.",
    ),

    # --- Filter ---
    "arp_enable": SemanticFunction(
        "arp_enable", "sequencer", "Zapíná/vypíná vestavěný arpeggiator.",
    ),
    "porta_time": SemanticFunction(
        "porta_time", "performance",
        "Portamento (glide) rychlost mezi noty. 0 = okamžitý skok mezi tóny. "
        "Vysoké = pomalé, sklouzávající legato (typické pro basy/leady).",
        direction="up",
    ),
    "device_bypass": SemanticFunction(
        "device_bypass", "global", "Zapnutí/vypnutí celého Serum 2 (0 = ticho).",
    ),
    "filter1_active": SemanticFunction(
        "filter1_active", "filter", "Zapnutí/vypnutí Filter 1 (lowpass sekce).",
    ),
    "filter2_active": SemanticFunction(
        "filter2_active", "filter", "Zapnutí/vypnutí Filter 2 (highpass sekce, 'High 18').",
    ),
    "filter2_type": SemanticFunction(
        "filter2_type", "filter",
        "Algoritmus Filter 2 (aktuálně 'High 18' -- highpass). Stejná logika "
        "jako filter_type, ale pro druhý filtr v sérii/paralelně.",
    ),
    "filter_level": SemanticFunction(
        "filter_level", "filter",
        "Výstupní hlasitost signálu PO filtru -- kompenzuje, když Cutoff/"
        "Resonance/Drive změní vnímanou hlasitost (rezonance a drive typicky "
        "zesilují). Použij pro srovnání hlasitosti, ne pro barvu zvuku.",
        direction="up",
    ),
    "filter1_bus1": SemanticFunction(
        "filter1_bus1", "filter",
        "Routing/blend Filter 1 do Bus 1 -- kolik Filter 1 přispívá do "
        "výstupní kombinace mezi Filter 1 a Filter 2 (sérii/paralelně). "
        "(Poznámka: první test byl nekonkluzivní, protože klip mezitím "
        "nehrál -- potvrdit znovu se skutečně hrajícím zvukem.)",
        direction="up",
    ),
    "filter1_bus2": SemanticFunction(
        "filter1_bus2", "filter",
        "Routing/blend Filter 1 do Bus 2 -- druhá výstupní větev pro "
        "kombinování Filter 1 s Filter 2.",
        direction="up",
    ),
    "filter2_bus1": SemanticFunction(
        "filter2_bus1", "filter",
        "Routing/blend Filter 2 do Bus 1 -- kolik Filter 2 (highpass) "
        "přispívá do stejné výstupní větve jako Filter 1.",
        direction="up",
    ),
    "filter2_bus2": SemanticFunction(
        "filter2_bus2", "filter",
        "Routing/blend Filter 2 do Bus 2 -- druhá výstupní větev pro "
        "kombinování Filter 2 s Filter 1.",
        direction="up",
    ),
    "filter_type": SemanticFunction(
        "filter_type", "filter",
        "Algoritmus filtru (LowPass 12/24dB, Notch, BandPass, MG LowPass...). "
        "MG (Moog) = teplá analogová saturace při rezonanci. Ostatní = chirurgický řez.",
    ),
    "filter_cutoff": SemanticFunction(
        "filter_cutoff", "filter",
        "Nejdůležitější pohybový knoflík. Zavřený = temný, tlumený, 'pod vodou'. "
        "Otevřený = pouští ven ostrost a agresivitu.",
        "10 Hz - 20 kHz", direction="up",
    ),
    "filter_resonance": SemanticFunction(
        "filter_resonance", "filter",
        "Zvýraznění frekvencí na bodu Cutoff. Nízká = hladká. Vysoká = pištivý, "
        "laserový, kybernetický charakter (pozor na přehlcení).",
        direction="up",
    ),
    "filter_drive": SemanticFunction(
        "filter_drive", "filter",
        "Silnější signál před filtrem -- lampová/digitální saturace, tiskne "
        "zvuk dopředu, dává dravost.",
        direction="up",
    ),
    "filter_wet": SemanticFunction(
        "filter_wet", "filter",
        "Dry/wet mix filtrovaného signálu -- 0 = filtr neslyšet vůbec (bypass), "
        "1 = čistě filtrovaný signál. Nižší hodnoty = paralelní filtrování, "
        "zachovává víc původní barvy zvuku.",
        direction="up",
    ),
    "filter_stereo": SemanticFunction(
        "filter_stereo", "filter",
        "Stereo šířka filtru -- vyšší hodnoty rozšiřují filtrovaný signál do "
        "stran, dělají zvuk širší a prostornější.",
        direction="up",
    ),

    # --- Envelopes & LFOs ---
    "env_attack": SemanticFunction(
        "env_attack", "envelope",
        "Rychlost náběhu na maximum. 0 = okamžitý úder. Pomalý = náběh/pad.",
        direction="down",  # "punchier" = lower attack
    ),
    "env_decay_sustain": SemanticFunction(
        "env_decay_sustain", "envelope",
        "Jak rychle se zvuk usadí po úderu na stabilní hladinu.",
    ),
    "env_release": SemanticFunction(
        "env_release", "envelope",
        "Doznívání po puštění klávesy. Krátké = staccato/pluck. "
        "Dlouhé = doznívající prostor.",
    ),
    "mod_envelope": SemanticFunction(
        "mod_envelope", "envelope",
        "Rychlé mechanické pohyby (Env 2/3) -- trhnutí Cutoffu při kopáku, "
        "rychlé zakmitnutí pitche pro 'punch' na začátku beatu.",
    ),
    "lfo_rate": SemanticFunction(
        "lfo_rate", "modulation",
        "Rychlost pulzování (synced 1/4, 1/8, 1/16). Rytmické otevírání filtru "
        "(wobble/pump) nebo jemné klouzání wavetablu.",
    ),

    # --- FX Rack ---
    "fx_distortion": SemanticFunction(
        "fx_distortion", "fx",
        "Zkreslení (Soft Tube/Hard Clip/Diode). Nízký drive = teplo. "
        "Vysoký drive = brutální industriální stěna, ničí dynamiku.",
        direction="up",
    ),
    "fx_hyper_dimension": SemanticFunction(
        "fx_hyper_dimension", "fx",
        "Hyper násobí a rozhazuje hlasy do stereo pole. Dimension přidává "
        "hloubkový chorus-like rozměr. Zvuk obrovský, široký, obklopující.",
        direction="up",
    ),
    "fx_space": SemanticFunction(
        "fx_space", "fx",
        "Reverb/Delay -- prostor a hloubka. Moc reverbu bez filtrace spodků "
        "zabíjí čistotu beatu; správně nastavený dává atmosféru klubu.",
        direction="up",
    ),
    "filter2_hp_cutoff": SemanticFunction(
        "filter2_hp_cutoff", "filter",
        "Filter 2 je HIGHPASS (\"High 18\"), ne lowpass jako Filter 1 -- opačná "
        "logika. Zvyšování cutoffu UBÍRÁ basy (ztenčuje, zesvětluje zvuk), "
        "snižování je NECHÁVÁ (plnější, tučnější). Použij pro čištění spodku "
        "mixu nebo pro efekt 'telefonního'/tenkého zvuku při vysokých hodnotách.",
        "10 Hz - 20 kHz", direction="down",  # "more low end" = LOWER this cutoff
    ),
}


def _add_per_oscillator_functions():
    """
    Serum has 3 independent oscillators (OSC A, OSC B, Sub) that each expose
    their own pitch/level/unison/warp knobs to Ableton. The generic
    'pitch_semitones'/'osc_level'/etc. functions above can only back ONE
    Ableton parameter each (see resolve_intent's function_to_param dict), so
    each oscillator needs its own function id -- generated here from the
    shared descriptions instead of copy-pasting three near-identical blocks.
    """
    oscillators = {
        "a": "OSC A (hlavní melodický/harmonický oscilátor, obvykle wavetable)",
        "b": "OSC B (druhý oscilátor, typicky pro vrstvení/detuning proti OSC A)",
        "sub": "Sub oscilátor (čistý sine/triangle o oktávu níž, basový fundament)",
    }
    templates = {
        "pitch_semitones": SERUM2_KNOWLEDGE["pitch_semitones"],
        "pitch_cents": SERUM2_KNOWLEDGE["pitch_cents"],
        "unison_voices": SERUM2_KNOWLEDGE["unison_voices"],
        "unison_detune": SERUM2_KNOWLEDGE["unison_detune"],
        "osc_level": SERUM2_KNOWLEDGE["osc_level"],
        "warp_mode": SERUM2_KNOWLEDGE["warp_mode"],
    }
    for osc_id, osc_label in oscillators.items():
        for base_fn, template in templates.items():
            fn_id = f"{osc_id}_{base_fn}"
            SERUM2_KNOWLEDGE[fn_id] = SemanticFunction(
                fn_id, template.category,
                f"[{osc_label}] {template.description}",
                template.param_range, template.direction,
            )


_add_per_oscillator_functions()

SERUM2_KNOWLEDGE.update({
    "env1_attack": SemanticFunction(
        "env1_attack", "envelope", "[Amp Envelope] " + SERUM2_KNOWLEDGE["env_attack"].description,
        direction="down",
    ),
    "env1_decay": SemanticFunction(
        "env1_decay", "envelope", "[Amp Envelope] " + SERUM2_KNOWLEDGE["env_decay_sustain"].description,
    ),
    "env1_sustain": SemanticFunction(
        "env1_sustain", "envelope", "[Amp Envelope] Hladina, na které tón zůstane držený, dokud se drží klávesa.",
    ),
    "env1_release": SemanticFunction(
        "env1_release", "envelope", "[Amp Envelope] " + SERUM2_KNOWLEDGE["env_release"].description,
    ),
    "env2_attack": SemanticFunction(
        "env2_attack", "envelope", "[Mod Envelope 2 -- typicky routovaná na Filter Cutoff pro punch] "
        + SERUM2_KNOWLEDGE["env_attack"].description, direction="down",
    ),
    "env2_decay": SemanticFunction(
        "env2_decay", "envelope", "[Mod Envelope 2] " + SERUM2_KNOWLEDGE["env_decay_sustain"].description,
    ),
    "env2_sustain": SemanticFunction(
        "env2_sustain", "envelope", "[Mod Envelope 2] Hladina modulace, která zůstává držená.",
    ),
    "env2_release": SemanticFunction(
        "env2_release", "envelope", "[Mod Envelope 2] " + SERUM2_KNOWLEDGE["env_release"].description,
    ),
    "lfo1_rate": SemanticFunction(
        "lfo1_rate", "modulation", SERUM2_KNOWLEDGE["lfo_rate"].description,
    ),
    "noise_level": SemanticFunction(
        "noise_level", "oscillator", "[Noise] " + SERUM2_KNOWLEDGE["osc_level"].description,
    ),
    "main_volume": SemanticFunction(
        "main_volume", "global", "Celková výstupní hlasitost Serum 2 -- master fader.",
        direction="up",
    ),
})

# --- Actionable subset: only functions with a live Ableton parameter wired
# up. This is a LIVE fact about the current session, not a fixed spec --
# rebuild it from audit_project() output whenever the Configure-mapped set
# changes (it's per-instance and gets overwritten by later Configure passes,
# not purely additive -- confirmed 2026-08-10: an initial 29-param pass on
# Pads Strings/Serum 2 became a DIFFERENT 97-param set after a second
# Configure-mode pass, with some earlier entries like "C WT Pos" gone).
#
# Re-verified live against Pads Strings/Serum 2 on 2026-08-10 (97 parameters,
# read directly via audit_project()). wt_pos has no live parameter in this
# pass (no *WT Pos entry present) -- omitted rather than guessed.
SERUM2_EXPOSED_PARAMS: dict[str, str] = {
    "Device On": "device_bypass",

    # OSC A
    "A Coarse Pitch": "a_pitch_semitones", "A Fine": "a_pitch_cents",
    "A Semi": "a_pitch_semi", "A Octave": "a_octave", "A Enable": "a_enable",
    "A Unison": "a_unison_voices", "A Uni Detune": "a_unison_detune",
    "A Uni Blend": "a_uni_blend", "A Level": "a_osc_level", "A Pan": "a_pan",
    "A Warp": "warp_mode", "A Warp 2": "a_warp2",

    # OSC B
    "B Coarse Pitch": "b_pitch_semitones", "B Fine": "b_pitch_cents",
    "B Semi": "b_pitch_semi", "B Octave": "b_octave", "B Enable": "b_enable",
    "B Uni Detune": "unison_detune", "B Uni Blend": "b_unison_detune",
    "B Level": "b_osc_level", "B Pan": "b_pan", "B Delay": "b_delay",
    "B Warp": "b_warp_mode", "B Warp 2": "b_warp2", "B Timbre": "b_timbre",
    "B Env Override": "b_env_override",

    # OSC C
    "C Coarse Pitch": "c_pitch_semitones", "C Fine": "c_pitch_cents",
    "C Unison": "unison_voices", "C Enable": "c_enable",
    "C Uni Detune": "c_uni_detune", "C Uni Blend": "c_uni_blend",
    "C Level": "c_osc_level", "C Pan": "c_pan",
    "C Warp": "c_warp_mode", "C Warp 2": "c_warp2",

    # Sub
    "Sub Enable": "sub_enable", "Sub Coarse Pitch": "sub_pitch_semitones",
    "Sub Octave": "sub_octave", "Sub Level": "sub_osc_level",
    "Sub Pan": "sub_pan", "Sub Phase": "sub_phase", "Sub Shape": "sub_shape",

    # Noise
    "Noise Enable": "noise_enable", "Noise Level": "noise_level",
    "Noise Pitch": "noise_pitch_fine", "Noise Pan": "noise_pan",

    # Filter 1 (the real thing, verified with an actual Hz range live)
    "Filter 1 On": "filter1_active", "Filter 1 Type": "filter_type",
    "Filter 1 Freq": "filter_cutoff", "Filter 1 Res": "filter_resonance",
    "Filter 1 Drive": "filter_drive", "Filter 1 Wet": "filter_wet",
    "Filter 1 Stereo": "filter_stereo", "Filter 1 Level": "filter_level",
    "Filter 1 Var": "filter1_var",

    # Filter 2
    "Filter 2 On": "filter2_active",

    # Envelopes
    "Env 1 Decay": "env1_decay", "Env 1 Sustain": "env1_sustain",
    "Env 2 Attack": "env2_attack", "Env 2 Decay": "env2_decay",
    "Env 2 Sustain": "env2_sustain", "Env 2 Hold": "env2_hold",
    "Env 2 Release": "env2_release",

    # Performance / global
    "Arp Enable": "arp_enable", "Transpose": "transpose",
    "Mod Wheel": "mod_wheel", "Pitch Bend": "pitch_bend",
    "Bend Down": "bend_down", "Bend Up": "bend_up",
    "Clip Player Enable": "clip_player_enable",
}

PLUGIN_KNOWLEDGE = {"Serum 2": SERUM2_KNOWLEDGE}
PLUGIN_EXPOSED = {"Serum 2": SERUM2_EXPOSED_PARAMS}

# Czech/English keyword -> (function, intensity 0..1) intent vocabulary.
    # STEM-based, not whole-word: Czech inflects heavily (masivní/masivnější/
    # masivnost/masivnějš...), so keys here are deliberately short word stems
    # matched as substrings via _fold() -- "masivn" alone covers all of those
    # without listing every form by hand. Keep stems long enough to avoid
    # false positives (e.g. "tep" would wrongly match "teplota"/"tep srdce"
    # if it existed elsewhere in a sentence -- use "teplej"/"teplo" instead).
INTENT_KEYWORDS: dict[str, tuple[str, float]] = {
    # --- Jas / ostrost (brightness / cutting edge) -> wavetable position ---
    "rezav": ("wt_pos", 0.8), "ostr": ("wt_pos", 0.8), "brit": ("wt_pos", 0.85),
    "kovov": ("wt_pos", 0.85), "digitaln": ("wt_pos", 0.8),
    "hladk": ("wt_pos", 0.2), "cist": ("wt_pos", 0.15), "jemn": ("wt_pos", 0.25),
    "kulat": ("wt_pos", 0.15), "mekc": ("wt_pos", 0.2),

    # --- Špína / zkreslení -> distortion ---
    "spinav": ("fx_distortion", 0.85), "zkreslen": ("fx_distortion", 0.8),
    "drsn": ("fx_distortion", 0.75), "brutal": ("fx_distortion", 0.9),
    "syrov": ("fx_distortion", 0.7), "spinavost": ("fx_distortion", 0.85),

    # --- Agresivita / warp -> oscillator warp ---
    "agresiv": ("warp_mode", 0.85), "bzuciv": ("warp_mode", 0.8),
    "industrialn": ("warp_mode", 0.85), "hoover": ("warp_mode", 0.9),

    # --- Cutoff (Filter 1, lowpass) -> otevři/zavři, tmavý/jasný ---
    "otevri spodek": ("filter_cutoff", 0.75), "otevrit spodek": ("filter_cutoff", 0.75),
    "otevrenej": ("filter_cutoff", 0.8), "otevrenejsi": ("filter_cutoff", 0.8),
    "temn": ("filter_cutoff", 0.25), "tmav": ("filter_cutoff", 0.25),
    "svetl": ("filter_cutoff", 0.75), "jasnejs": ("filter_cutoff", 0.75),
    "pod vodou": ("filter_cutoff", 0.15), "zavrenej": ("filter_cutoff", 0.2),

    # --- Resonance ---
    "pistiv": ("filter_resonance", 0.85), "rezonanc": ("filter_resonance", 0.75),
    "laserov": ("filter_resonance", 0.85), "kybernetick": ("filter_resonance", 0.8),
    "kvicav": ("filter_resonance", 0.85),

    # --- Filter drive / saturace ---
    "dravost": ("filter_drive", 0.8), "dravejs": ("filter_drive", 0.8),
    "nakrmit filtr": ("filter_drive", 0.75), "lampov": ("filter_drive", 0.6),

    # --- Šířka / masivnost -> unison ---
    "sirs": ("unison_detune", 0.7), "sirok": ("unison_detune", 0.7),
    "masivn": ("unison_voices", 0.9), "mohutn": ("unison_voices", 0.85),
    "supersaw": ("unison_voices", 0.95), "stena zvuku": ("unison_voices", 0.9),
    "psychedelick": ("unison_detune", 0.9), "rozplizl": ("unison_detune", 0.85),
    "tluste": ("unison_detune", 0.4), "tlusty": ("unison_detune", 0.4),
    "tencejs": ("unison_voices", 0.15), "tenci": ("unison_voices", 0.15),
    "tenky ton": ("unison_voices", 0.1),

    # --- Prostor / reverb ---
    "prostorov": ("fx_space", 0.7), "rozmazat v prostoru": ("fx_space", 0.75),
    "atmosferick": ("fx_space", 0.75), "klubov": ("fx_space", 0.7),
    "ozvena": ("fx_space", 0.7), "hloubka": ("fx_space", 0.65),

    # --- Basy / spodek mixu (Filter 2 highpass) ---
    "vic basu": ("filter2_hp_cutoff", 0.9), "tucnejs": ("filter2_hp_cutoff", 0.85),
    "plnejs": ("filter2_hp_cutoff", 0.8), "vycistit spodek": ("filter2_hp_cutoff", 0.2),
    "vyhubenej": ("filter2_hp_cutoff", 0.85), "telefonn": ("filter2_hp_cutoff", 0.9),

    # --- Punch / dynamika (Amp envelope, Env 1) ---
    "punch": ("env1_attack", 0.9), "uder": ("env1_attack", 0.9),
    "staccato": ("env1_attack", 0.9), "pluck": ("env1_attack", 0.9),
    "bomb": ("env1_attack", 0.9),  # slang "ať to praští/bomba" -> fast punchy attack
    "nabeh": ("env1_attack", 0.2), "pad": ("env1_attack", 0.1),
    "pozvolna": ("env1_attack", 0.15),

    # --- Doznívání ---
    "doznivat kratc": ("env1_release", 0.15), "krat": ("env1_release", 0.2),
    "dlouho doznivat": ("env1_release", 0.85), "dozvuk": ("env1_release", 0.8),

    # --- Pitch / oktávy (OSC A jako hlavní melodický) ---
    "vyssi ton": ("a_pitch_semitones", 0.7), "nizsi ton": ("a_pitch_semitones", 0.3),
    "o oktavu vejs": ("a_pitch_semitones", 0.75), "o oktavu niz": ("a_pitch_semitones", 0.25),
    "rozladit": ("a_pitch_cents", 0.7), "analogovejs": ("a_pitch_cents", 0.65),

    # --- Hlasitost ---
    "hlasitejs": ("main_volume", 0.85), "tisejs": ("main_volume", 0.3),
    "potisit": ("main_volume", 0.3),

    # --- Arp / portamento ---
    "arpeggi": ("arp_enable", 1.0), "sklouzavat": ("porta_time", 0.7),
    "glide": ("porta_time", 0.7), "legato skluz": ("porta_time", 0.6),
}

# Genre/role archetypes -- a producer says "techno peak lead" or "acidovej
# baslík", not a list of adjectives. Each archetype expands directly to a
# fixed set of (function, target_value) changes, bypassing the stem matcher.
# Matched as a whole phrase (word-order independent, same as multi-word
# INTENT_KEYWORDS) so it takes priority over any individual stems that also
# happen to appear in the sentence.
ARCHETYPES: dict[str, list[tuple[str, float]]] = {
    "techno peak lead": [
        ("wt_pos", 0.75), ("warp_mode", 0.75), ("filter_resonance", 0.7),
        ("filter_cutoff", 0.7), ("unison_voices", 0.8), ("env1_attack", 0.05),
    ],
    "warehouse lead": [
        ("wt_pos", 0.75), ("filter_resonance", 0.75), ("filter_drive", 0.7),
        ("unison_voices", 0.7),
    ],
    "acidovy baslik": [  # acid bassline -- resonant filter + fast movement
        ("filter_resonance", 0.9), ("filter_cutoff", 0.55), ("warp_mode", 0.5),
        ("unison_voices", 0.2),  # acid basslines are classically mono/thin, not stacked
    ],
    "hoover": [
        ("warp_mode", 0.9), ("unison_voices", 0.85), ("unison_detune", 0.7),
        ("filter_resonance", 0.6),
    ],
    "pad": [
        ("env1_attack", 0.85), ("env1_release", 0.8), ("unison_detune", 0.7),
        ("fx_space", 0.7), ("wt_pos", 0.25),
    ],
    "pluck": [
        ("env1_attack", 0.02), ("env1_release", 0.15), ("wt_pos", 0.6),
    ],
    "stab": [
        ("env1_attack", 0.02), ("env1_release", 0.1), ("filter_drive", 0.6),
        ("unison_voices", 0.6),
    ],
    "sub bas": [
        ("a_pitch_semitones", 0.15), ("wt_pos", 0.1), ("unison_voices", 0.1),
        ("filter_cutoff", 0.3),
    ],
}

# Per-archetype note pattern -- (semitone offset from root, beat position,
# duration in beats, velocity). Written relative to a root note the caller
# supplies, so the same pattern transposes to any key.
NOTE_PATTERNS: dict[str, list[tuple[int, float, float, int]]] = {
    "techno peak lead": [
        # Real 1-bar riff (root/minor-third/fifth/octave) with rests, played
        # twice per 2-bar phrase then varied -- NOT the same note hammered on
        # every 16th (that's a gate/stutter effect, not a lead line). Step
        # grid: 16 steps/bar x 0.25 beats. Pattern per bar (None = rest):
        #   R  .  m3 .  5  .  R  R  8ve .  5  .  m3 .  R  .
        *[(o, bar * 4 + i * 0.25, 0.2, 100 if o == 0 else 85)
          for bar in range(4)
          for i, o in enumerate([0, None, 3, None, 7, None, 0, 0, 12, None, 7, None, 3, None, 0, None])
          if o is not None],
    ],
    "warehouse lead": [
        *[(0, i * 0.5, 0.4, 95) for i in range(8)],
        *[(0, 4 + i * 0.5, 0.4, 95) for i in range(8)],
        *[(7, 8 + i * 0.5, 0.4, 100) for i in range(8)],  # fifth for lift
        *[(0, 12 + i * 0.5, 0.4, 95) for i in range(8)],
    ],
    "acidovy baslik": [
        # Classic 303-style syncopated 16ths with octave jumps and slides
        (0, 0.0, 0.2, 110), (0, 0.5, 0.15, 80), (12, 0.75, 0.15, 90),
        (0, 1.5, 0.2, 100), (3, 2.0, 0.15, 85), (0, 2.5, 0.2, 90),
        (0, 3.0, 0.15, 80), (12, 3.5, 0.2, 105),
    ] * 4,
    "hoover": [
        (0, 0.0, 3.5, 110), (0, 4.0, 3.5, 110), (0, 8.0, 3.5, 110), (0, 12.0, 3.5, 110),
    ],
    "pad": [
        (0, 0.0, 15.5, 90), (4, 0.0, 15.5, 80), (7, 0.0, 15.5, 80),
    ],
    "pluck": [(0, i * 1.0, 0.15, 100) for i in range(16)],
    "stab": [
        (0, 0.0, 0.15, 110), (0, 2.0, 0.15, 110), (0, 4.5, 0.15, 105),
        (0, 8.0, 0.15, 110), (0, 10.0, 0.15, 110), (0, 12.5, 0.15, 105),
    ],
    "sub bas": [(0, i * 1.0, 0.9, 110) for i in range(16)],
}


def build_notes_for_archetype(text: str, root_note: int = 36) -> Optional[list[tuple[int, float, float, int]]]:
    """
    If the text matches a known archetype phrase, return absolute
    (pitch, start_beat, duration, velocity) notes for it, transposed to
    root_note (default C1 = 36, a sensible bass/lead register). Returns
    None if no archetype phrase matched -- caller should leave existing
    notes alone rather than overwrite with nothing.
    """
    text_words = set(_fold(text).split())
    for phrase, pattern in NOTE_PATTERNS.items():
        phrase_words = _fold(phrase).split()
        if all(w in text_words for w in phrase_words):
            return [(root_note + offset, start, dur, vel) for offset, start, dur, vel in pattern]
    return None


@dataclass
class ResolvedChange:
    function: str
    description: str
    target_value: float
    ableton_param: Optional[str]  # None if not currently exposed/controllable


def _fold(s: str) -> str:
    """Strip diacritics and lowercase, so 'řezavý'/'rezavy'/'ŘEZAVÝ' all match --
    users type Czech without háčky/čárky constantly (see: this whole session)."""
    normalized = unicodedata.normalize("NFKD", s)
    return "".join(c for c in normalized if not unicodedata.combining(c)).lower()


def resolve_intent(text: str, plugin_name: str = "Serum 2") -> list[ResolvedChange]:
    """
    Parse free-text Czech/English intent into semantic changes, using the
    FULL knowledge base -- then annotate each with whether it's currently
    controllable (ableton_param set) or just known-but-not-yet-wired
    (ableton_param is None). Callers should surface both, not just execute
    silently on whatever happens to be controllable.

    Matching is diacritics-folded and word-order-independent for multi-word
    keywords (e.g. "otevři spodek" matches "otevři mi trochu ten spodek"),
    since natural phrasing rarely matches a fixed phrase exactly.
    """
    knowledge = PLUGIN_KNOWLEDGE.get(plugin_name, {})
    exposed = PLUGIN_EXPOSED.get(plugin_name, {})
    function_to_param = {fn: p for p, fn in exposed.items()}

    text_folded = _fold(text)
    text_words = set(text_folded.split())
    results = []
    seen_functions = set()

    # Archetypes first and take priority -- "techno peak lead" should win
    # over any individual stem that happens to also appear in the sentence.
    for phrase, changes in ARCHETYPES.items():
        phrase_words = _fold(phrase).split()
        if not all(w in text_words for w in phrase_words):
            continue
        for function, target in changes:
            if function in seen_functions:
                continue
            seen_functions.add(function)
            info = knowledge.get(function)
            if info is None:
                continue
            results.append(ResolvedChange(
                function=function, description=info.description,
                target_value=target, ableton_param=function_to_param.get(function),
            ))

    for keyword, (function, intensity) in INTENT_KEYWORDS.items():
        keyword_words = _fold(keyword).split()
        matched = all(w in text_words for w in keyword_words) if len(keyword_words) > 1 \
            else _fold(keyword) in text_folded
        if not matched or function in seen_functions:
            continue
        seen_functions.add(function)
        info = knowledge.get(function)
        if info is None:
            continue
        target = intensity if info.direction == "up" else (1.0 - intensity)
        results.append(ResolvedChange(
            function=function,
            description=info.description,
            target_value=target,
            ableton_param=function_to_param.get(function),
        ))
    return results
