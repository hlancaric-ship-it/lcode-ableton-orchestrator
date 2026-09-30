"""
L-Code Global Matrix -- loads genre archetypes from lcode_studio.db and
deploys them to a live Ableton session via LCodeOrchestrator.

Note on the two pseudocode drafts this was built from: both called
orchestrator.execute_command(track_idx, device_idx, ...), but our real
LCodeOrchestrator.execute_command() takes track_name/device_name strings and
resolves them through the live registry built by audit_project() -- that's
what makes it safe (clear error on a stale/renamed parameter instead of a
silently wrong OSC index). Adjusted here to match, not changed silently.
"""

import sqlite3
from lcode_orchestrator import LCodeOrchestrator, LCodeOrchestratorError
from semantic_profiles import PLUGIN_EXPOSED


class LCodeGlobalMatrix:
    def __init__(self, db_path: str = "lcode_studio.db"):
        self.db_path = db_path

    def fetch_archetype_matrix(self, archetype_name: str) -> dict:
        """
        Vytáhne kompletní mapu parametrů pro zvolený archetyp.
        Returns {parameter_name: {"value": float, "role": str}}.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT m.parameter_name, m.target_value, m.acoustic_role
            FROM archetype_knob_mappings m
            JOIN genre_archetypes a ON m.archetype_id = a.id
            WHERE a.name = ?
        """, (archetype_name,))
        rows = cursor.fetchall()
        conn.close()
        return {row[0]: {"value": row[1], "role": row[2]} for row in rows}

    def list_archetypes(self) -> list[tuple[str, str]]:
        """Returns [(genre_name, archetype_name), ...] for discovery."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.name, a.name FROM genre_archetypes a
            LEFT JOIN genres g ON a.genre_id = g.id
            ORDER BY g.id, a.id
        """)
        rows = cursor.fetchall()
        conn.close()
        return rows

    def deploy_to_live_rack(self, orchestrator: LCodeOrchestrator, track_name: str,
                             device_name: str, archetype_name: str):
        """
        Aplikuje kompletní žánrový archetyp z databáze do živého Ableton
        projektu přes OSC. `parameter_name` v databázi je SÉMANTICKÁ funkce
        (např. "filter_cutoff"), ne přímo Ableton parametr -- ten se překládá
        přes semantic_profiles.PLUGIN_EXPOSED, protože to, co je zrovna
        namapované v Live, se mění za běhu (stejný princip jako
        resolve_intent). Nikdy nepředstírá plné pokrytí -- u každého
        parametru, který zrovna není v Live namapovaný, to jasně nahlásí a
        pokračuje dál, místo aby spadlo nebo mlčelo.
        """
        matrix = self.fetch_archetype_matrix(archetype_name)
        if not matrix:
            print(f"[L-CODE ERROR] Archetyp '{archetype_name}' nenalezen v databázi!")
            return

        exposed = PLUGIN_EXPOSED.get(device_name, {})
        function_to_param = {fn: p for p, fn in exposed.items()}

        print(f"[L-CODE] Nasazuji žánrový archetyp: {archetype_name}")
        applied, skipped = 0, 0
        for function_name, data in matrix.items():
            ableton_param = function_to_param.get(function_name)
            if ableton_param is None:
                print(f"  [PRESKOCENO] {function_name} -> {data['value']:.2f}  "
                      f"({data['role']}) -- zatím nenamapováno v Live")
                skipped += 1
                continue
            try:
                orchestrator.execute_command(track_name, device_name, ableton_param, data["value"])
                print(f"  [OK] {ableton_param} ({function_name}) -> {data['value']:.2f}  ({data['role']})")
                applied += 1
            except LCodeOrchestratorError as e:
                print(f"  [PRESKOCENO] {function_name} -> {data['value']:.2f}  ({data['role']}) -- {e}")
                skipped += 1
        print(f"[L-CODE] Hotovo: {applied} aplikováno, {skipped} zatím nemapováno v Live.")


if __name__ == "__main__":
    import sys
    archetype = " ".join(sys.argv[1:]) or "Peak-Time Lead Synth (Saw/Warp)"

    matrix_db = LCodeGlobalMatrix()
    print("Dostupné archetypy v databázi:")
    for genre, name in matrix_db.list_archetypes():
        marker = " <-- vybráno" if name == archetype else ""
        print(f"  [{genre}] {name}{marker}")
    print()

    orch = LCodeOrchestrator()
    orch.audit_project(verbose=False)
    matrix_db.deploy_to_live_rack(orch, "1-Serum 2", "Serum 2", archetype)
    orch.close()
