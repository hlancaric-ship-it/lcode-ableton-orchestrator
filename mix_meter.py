"""
Mereni mixu / masteru pres ffmpeg (lokalne, bez API a bez dalsich knihoven).

PROC
Orchestrator nastavuje fadery a zarizeni naslepo - nevidi, jak vysledek zni.
Tohle je zpetna vazba: vyexportovany mix -> integrated LUFS, true peak,
loudness range, crest factor a energie v pasmech -> porovnani s cilem.

Pouziti:
    python3 mix_meter.py <soubor.wav> [--target spotify|apple|youtube|club]
    python3 mix_meter.py <stem1.wav> <stem2.wav> ...   (stemy se sectou do mixu)
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path

# Cilove hodnoty streamovacich sluzeb (normalizace hlasitosti) a klubu.
# lufs = integrated loudness, tp_max = max true peak v dBTP.
TARGETS = {
    "spotify": {"lufs": -14.0, "tp_max": -1.0},
    "youtube": {"lufs": -14.0, "tp_max": -1.0},
    "apple":   {"lufs": -16.0, "tp_max": -1.0},
    # Klubovy master (tech house/techno) byva hlasitejsi; streaming ho ztlumi.
    "club":    {"lufs": -8.0,  "tp_max": -0.5},
}

# Pasma pro hrubou spektralni bilanci (Hz).
BANDS = [
    ("sub", None, 60),
    ("low", 60, 250),
    ("mid", 250, 4000),
    ("high", 4000, None),
]


@dataclass
class MixReport:
    file: str
    duration_s: float
    integrated_lufs: float | None
    loudness_range_lu: float | None
    true_peak_dbtp: float | None
    rms_db: float | None
    peak_db: float | None
    crest_db: float | None
    bands_db: dict
    target: str
    findings: list


def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise RuntimeError("ffmpeg nenalezen v PATH")
    return exe


def _run_filter(path: Path, af: str) -> str:
    # ffmpeg vypisuje statistiky filtru na stderr; -nostats zkrati vystup.
    proc = subprocess.run(
        [_ffmpeg(), "-hide_banner", "-nostats", "-i", str(path), "-af", af, "-f", "null", "-"],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stderr.strip().splitlines()[-5:])
        raise RuntimeError(f"ffmpeg selhal ({proc.returncode}): {tail}")
    return proc.stderr


def _num(pattern: str, text: str) -> float | None:
    m = re.search(pattern, text)
    if not m:
        return None
    try:
        v = float(m.group(1))
    except ValueError:
        return None
    return None if math.isinf(v) or math.isnan(v) else v


def _duration(path: Path) -> float:
    exe = shutil.which("ffprobe")
    if not exe:
        return 0.0
    proc = subprocess.run(
        [exe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(path)],
        capture_output=True, text=True, timeout=60,
    )
    try:
        return round(float(proc.stdout.strip()), 2)
    except ValueError:
        return 0.0


def _overall_rms(stderr: str) -> float | None:
    # astats vypisuje bloky per kanal a na konci "Overall" - bereme Overall.
    overall = stderr.split("Overall", 1)[-1] if "Overall" in stderr else stderr
    return _num(r"RMS level dB:\s*(-?[\d.]+|-inf)", overall)


def _band_filter(lo: int | None, hi: int | None) -> str:
    parts = []
    if lo:
        parts.append(f"highpass=f={lo}:poles=2")
    if hi:
        parts.append(f"lowpass=f={hi}:poles=2")
    return ",".join(parts + ["astats=metadata=0:reset=0"])


def sum_stems(paths: list[str | Path], out_dir: str | Path | None = None) -> Path:
    """Secte stemy (napr. Vocals/Drums/Bass/Others ze stem separation v Live)
    zpet do jednoho mixu - bez normalizace, aby sedela hlasitost originalu."""
    files = [Path(x).expanduser() for x in paths]
    missing = [str(f) for f in files if not f.is_file()]
    if missing:
        raise FileNotFoundError(f"Stemy neexistuji: {missing}")
    if len(files) < 2:
        raise ValueError("Na secteni jsou potreba aspon 2 stemy")
    fd, out = tempfile.mkstemp(suffix=".wav", prefix="mixsum_", dir=out_dir)
    Path(out).unlink()  # ffmpeg si soubor vytvori sam
    del fd
    cmd = [_ffmpeg(), "-hide_banner", "-nostats", "-y"]
    for f in files:
        cmd += ["-i", str(f)]
    cmd += ["-filter_complex", f"amix=inputs={len(files)}:normalize=0:duration=longest",
            "-c:a", "pcm_f32le", out]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if proc.returncode != 0:
        raise RuntimeError(f"Scitani stemu selhalo: {proc.stderr.strip().splitlines()[-1:]}")
    return Path(out)


def measure_stems(paths: list[str | Path], target: str = "spotify") -> MixReport:
    """Secte stemy a zmeri vysledny mix. Docasny soubor po mereni smaze."""
    mixed = sum_stems(paths)
    try:
        rep = measure(mixed, target)
    finally:
        mixed.unlink(missing_ok=True)
    rep.file = " + ".join(Path(x).name for x in paths)
    return rep


def measure(path: str | Path, target: str = "spotify") -> MixReport:
    p = Path(path).expanduser()
    if not p.is_file():
        raise FileNotFoundError(f"Soubor neexistuje: {p}")
    if target not in TARGETS:
        raise ValueError(f"Neznamy cil '{target}', moznosti: {', '.join(TARGETS)}")

    loud = _run_filter(p, "ebur128=peak=true")
    summary = loud.split("Summary:", 1)[-1]
    lufs = _num(r"I:\s*(-?[\d.]+)\s*LUFS", summary)
    lra = _num(r"LRA:\s*(-?[\d.]+)\s*LU", summary)
    tp = _num(r"Peak:\s*(-?[\d.]+)\s*dBFS", summary)

    stats = _run_filter(p, "astats=metadata=0:reset=0")
    overall = stats.split("Overall", 1)[-1] if "Overall" in stats else stats
    rms = _num(r"RMS level dB:\s*(-?[\d.]+)", overall)
    peak = _num(r"Peak level dB:\s*(-?[\d.]+)", overall)
    crest = round(peak - rms, 2) if rms is not None and peak is not None else None

    bands = {}
    for name, lo, hi in BANDS:
        band_rms = _overall_rms(_run_filter(p, _band_filter(lo, hi)))
        # Relativne k celkovemu RMS - cislo rika podil pasma, ne absolutni hlasitost.
        bands[name] = round(band_rms - rms, 1) if band_rms is not None and rms is not None else None

    t = TARGETS[target]
    findings = []
    if lufs is not None:
        diff = round(lufs - t["lufs"], 1)
        if abs(diff) > 1.0:
            findings.append(
                f"Hlasitost {lufs:.1f} LUFS, cil {t['lufs']:.0f} ({target}): "
                + (f"o {diff:.1f} LU hlasitejsi - sluzba to ztlumi, zbytecne ztracis dynamiku"
                   if diff > 0 else f"o {abs(diff):.1f} LU tissi - bude znit slabeji nez ostatni skladby")
            )
    if tp is not None and tp > t["tp_max"]:
        findings.append(f"True peak {tp:.1f} dBTP nad limitem {t['tp_max']:.1f} - riziko zkresleni po prevodu do MP3/AAC, snizit ceiling limiteru")
    if crest is not None and crest < 6:
        findings.append(f"Crest factor {crest:.1f} dB - mix je hodne zkomprimovany/zlimitovany, ztraci punch")
    if lra is not None and lra < 3 and target != "club":
        findings.append(f"Loudness range {lra:.1f} LU - velmi malo dynamiky mezi castmi skladby")
    if bands.get("sub") is not None and bands.get("mid") is not None and bands["sub"] > bands["mid"] + 3:
        findings.append("Sub (pod 60 Hz) prevysuje stredy o vic nez 3 dB - na malych reproduktorech bude mix prazdny, na velkych muze dunet")

    return MixReport(
        file=str(p), duration_s=_duration(p), integrated_lufs=lufs, loudness_range_lu=lra,
        true_peak_dbtp=tp, rms_db=rms, peak_db=peak, crest_db=crest, bands_db=bands,
        target=target, findings=findings,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Mereni mixu (LUFS, true peak, dynamika, pasma)")
    ap.add_argument("files", nargs="+", help="jeden mix, nebo vic stemu (sectou se)")
    ap.add_argument("--target", default="spotify", choices=sorted(TARGETS))
    args = ap.parse_args()
    rep = measure(args.files[0], args.target) if len(args.files) == 1 else measure_stems(args.files, args.target)
    print(json.dumps(asdict(rep), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
