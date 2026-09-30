"""
MCP server for L-Code Ableton Orchestrator.

Exposes the existing OSC-based orchestrator functions (audit, gain staging,
device chains, arrangement building, archetype deployment) as MCP tools so
any MCP-compatible AI client (Claude Desktop, Claude Code, etc.) can drive
the Live session through natural language instead of running scripts by hand.

Dry-run first, same rule as the rest of this project: audit_project() and
gain_staging.build_plan() only READ from Live. Nothing writes until the
corresponding *_apply / execute_command / deploy tool is called explicitly.

Run:
    pip install mcp
    python mcp_server.py
"""

from pathlib import Path
from mcp.server.fastmcp import FastMCP

from lcode_orchestrator import LCodeOrchestrator
from archetype_manager import LCodeGlobalMatrix
import gain_staging
import device_chain_builder
import arrangement_builder
import mix_meter
from dataclasses import asdict

mcp = FastMCP("lcode-ableton-orchestrator")

_orch: LCodeOrchestrator | None = None


def get_orch() -> LCodeOrchestrator:
    global _orch
    if _orch is None:
        _orch = LCodeOrchestrator()
    return _orch


@mcp.tool()
def audit_project() -> dict:
    """Read-only snapshot of the current Ableton Live session: tracks,
    devices, and parameter values. Always run this first before any write
    operation to see the real current state."""
    return get_orch().audit_project(verbose=False)


@mcp.tool()
def set_device_param(track_name: str, device_name: str, param_name: str, value: float) -> str:
    """Set a single device parameter on a track to an explicit value.
    Always audit_project() first to confirm the track/device/param names exist."""
    get_orch().execute_command(track_name, device_name, param_name, value)
    return f"Set {track_name} / {device_name} / {param_name} = {value}"


@mcp.tool()
def gain_staging_plan() -> str:
    """Dry-run: compute the gain staging plan (fader levels per track) without
    writing anything to Live. Review this before calling gain_staging_apply."""
    orch = get_orch()
    planned, unresolved = gain_staging.build_plan(orch)
    lines = [f"{p.track_name}: {p.target_db:+.1f} dB" for p in planned]
    if unresolved:
        lines.append(f"Unresolved tracks (no matching profile): {', '.join(unresolved)}")
    return "\n".join(lines)


@mcp.tool()
def gain_staging_apply(project_dir: str = ".") -> str:
    """Apply the gain staging plan to Live. Writes a rollback snapshot JSON
    to project_dir before making any changes."""
    orch = get_orch()
    planned, _ = gain_staging.build_plan(orch)
    snapshot = gain_staging.apply(orch, planned, Path(project_dir))
    return f"Applied gain staging. Rollback snapshot: {snapshot}"


@mcp.tool()
def gain_staging_restore(snapshot_file: str) -> str:
    """Roll back a previous gain_staging_apply using its snapshot JSON file."""
    gain_staging.restore(get_orch(), Path(snapshot_file))
    return f"Restored from {snapshot_file}"


@mcp.tool()
def list_archetypes() -> list[dict]:
    """List available genre/sound archetypes stored in lcode_studio.db
    (e.g. 'Groove Tech-House Stab') that can be deployed onto a track's
    instrument rack."""
    mgr = LCodeGlobalMatrix()
    return [{"name": n, "description": d} for n, d in mgr.list_archetypes()]


@mcp.tool()
def deploy_archetype(archetype_name: str, track_name: str) -> str:
    """Deploy a named sound archetype's parameter matrix onto a track's
    instrument (e.g. Serum 2 macro mapping for a genre-specific patch)."""
    mgr = LCodeGlobalMatrix()
    mgr.deploy_to_live_rack(get_orch(), track_name, archetype_name)
    return f"Deployed archetype '{archetype_name}' to track '{track_name}'"

@mcp.tool()
def build_device_chains() -> str:
    """Insert and configure the standard device chain (Utility, EQ Eight
    low-cut, Compressor with calibrated settings) across the project's tracks."""
    device_chain_builder.build_device_chains(get_orch())
    return "Device chains built."


@mcp.tool()
def build_arrangement() -> str:
    """Build the song's Session-view scenes (Intro, Build, Groove, Break,
    Drop, Outro, etc.) with placeholder melodic clips."""
    arrangement_builder.build(get_orch())
    return "Arrangement scenes built in Session view."


@mcp.tool()
def print_arrangement_to_timeline() -> str:
    """Print the built Session-view scenes into the Arrangement view timeline."""
    arrangement_builder.print_to_arrangement(get_orch())
    return "Printed to Arrangement view."


@mcp.tool()
def measure_mix(file_path: str, target: str = "spotify") -> dict:
    """Measure an exported mix/stem (WAV/AIFF/MP3) locally via ffmpeg: integrated
    LUFS, true peak, loudness range, crest factor and band balance, compared to
    target (spotify|youtube|apple|club). Read-only, no Live connection needed."""
    return asdict(mix_meter.measure(file_path, target))


@mcp.tool()
def measure_stems(stem_paths: list[str], target: str = "spotify") -> dict:
    """Sum stems (e.g. Live stem-separation Vocals/Drums/Bass/Others) back into
    one mix and measure it like measure_mix. Temp file is deleted afterwards."""
    return asdict(mix_meter.measure_stems(stem_paths, target))


if __name__ == "__main__":
    mcp.run()
