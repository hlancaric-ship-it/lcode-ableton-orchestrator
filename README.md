# L-Code Ableton Orchestrator

MCP server, který řídí Ableton Live přes OSC: audit projektu, gain staging,
device chainy, stavba aranže, nasazení zvukových archetypů (Serum 2) a měření mixu.
Jakýkoli MCP klient (Claude Desktop, Claude Code) pak ovládá Live přirozeným jazykem
místo ručního spouštění skriptů.

Pravidlo celého projektu: **dry-run first**. `audit_project` a `gain_staging.build_plan`
jen čtou. Nic se nezapíše, dokud se explicitně nezavolá odpovídající `*_apply` /
`execute_command` / `deploy` nástroj. Každý zápis gain stagingu ukládá snapshot pro rollback.

---

## Instalace na Windows

### 1. Python
Nainstaluj **Python 3.10 nebo novější** z https://www.python.org/downloads/windows/
(při instalaci zaškrtni „Add Python to PATH"). Ověř v PowerShellu:
```
python --version
```

### 2. Stáhni repo a nainstaluj závislosti
```
git clone https://github.com/hlancaric-ship-it/lcode-ableton-orchestrator.git
cd lcode-ableton-orchestrator
pip install -r requirements.txt
```

### 3. AbletonOSC + L-Code patch
Server mluví s Live přes AbletonOSC (nutné rozšíření, Remote Script).

1. Stáhni AbletonOSC: https://github.com/ideoforms/AbletonOSC
2. Rozbal složku `AbletonOSC` do:
   ```
   %USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\AbletonOSC\
   ```
   (na Macu je to `~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/` — na Windows
   je to pod Documents)
3. Aplikuj L-Code patch (přidává vkládání device chainů, co stock AbletonOSC neumí).
   V `abletonosc_patches/lcode-abletonosc.patch` je diff; v `abletonosc_patches/README.md`
   je postup. Soubory se patchují v nainstalované složce AbletonOSC z kroku 2.
4. V Ableton Live: **Preferences → Link/Tempo/MIDI → MIDI** (v novějších verzích
   **Link/MIDI**), nahoře **Control Surface** vyber **AbletonOSC**. Live ho načte.

AbletonOSC poslouchá na portech 11000 (příkazy) / 11001 (odpovědi) na 127.0.0.1 —
stejné na Windows i Macu, nic se nenastavuje.

### 4. ffmpeg (jen pro měření mixu)
Nástroje `measure_mix` / `measure_stems` potřebují ffmpeg. Když nebudeš měřit exporty,
přeskoč. Jinak: `winget install ffmpeg` (nebo https://www.gyan.dev/ffmpeg/builds/)
a přidej do PATH.

### 5. Napojení na Claude (MCP)
Spuštění serveru ručně pro test:
```
python mcp_server.py
```
Do konfigurace MCP klienta (Claude Desktop `claude_desktop_config.json`, nebo
Claude Code) přidej server, uprav cestu podle sebe:
```json
{
  "mcpServers": {
    "lcode-ableton": {
      "command": "python",
      "args": ["C:\\Users\\<ty>\\lcode-ableton-orchestrator\\mcp_server.py"]
    }
  }
}
```
Restartuj klienta. Nástroje `audit_project`, `gain_staging_plan`, `build_device_chains`,
`deploy_archetype`, `measure_mix` atd. naběhnou.

---

## Jak to dohromady funguje
1. V Live si naimportuješ MIDI/stopy a pojmenuješ kanály (podle jmen se páruje
   gain staging a chainy — `bass`, `clap`, `hat`, `pad`, `lead`, `pluck`, `fx` …).
2. `audit_project` → přečte projekt.
3. `gain_staging_plan` → dry-run, ukáže navržené faders. `gain_staging_apply` → srovná
   a uloží snapshot.
4. `build_device_chains` → nasadí Utility + EQ low-cut + kompresor na pojmenované kanály.
5. `deploy_archetype` → nahraje makro matici archetypu do Serum 2 na dané stopě
   (Serum 2 musí na stopě být).

Archetypy žijí v `lcode_studio.db` (žánr → archetyp → mapování knobů / noty).

## Co není v repu
`.wrangler/` (Cloudflare account) je v `.gitignore` a není tu — nic tajného repo neobsahuje.
