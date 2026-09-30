# Progress Log

## 2026-08-10 -- Tech house arrangement + gain staging + Serum macro mapping

### Hotovo (živé, ověřené v Live, ne jen v kódu)

- **Arrangement**: 11 scén (Intro, Build 1, Groove A, Break, Build 2, Drop A,
  Groove B, Break 2, Build 3, Drop B, Outro), 136 taktů, vytištěno do
  Arrangement view (ne jen Session). Skript: `arrangement_builder.py`.
- **Tracky**: Kick 808 Bass, Sub Bass, Mid Bass, Snare, Clap, HiHats Cymbals
  (skupina DRUMS), Lead Vocal, Backing Vocals (skupina VOCALS), Piano Guitar,
  Pads Strings, Synth Lead Plucks (skupina MELODICS), FX Risers. Grupováno
  ručně v Live.
- **Gain staging**: fadery nastavené podle mixážní matice na všech 12
  tracích. Skript: `gain_staging.py`. Rollback snapshoty:
  `gain_staging_snapshot_*.json` (nejnovější `20260810-032920`).
- **Device chains**: Utility + EQ Eight (low-cut 30Hz na kick/bass, 90Hz
  jinde) na všech 12 tracích, Compressor (kalibrovaný přes `str_for_value`
  binary search, ne odhad: Threshold -18dB, Ratio 3:1, Attack 10ms, Release
  100ms) na Kick 808 Bass, Sub Bass, Mid Bass, Lead Vocal. Skript:
  `device_chain_builder.py`.
- **Nástroje**: Drum Rack na Kick/Snare/Clap/HiHats (PRÁZDNÉ -- žádné
  samply), Serum 2 na Sub Bass/Mid Bass/Pads Strings/Synth Lead Plucks
  (Init patch, kromě Pads Strings viz níže).
- **AbletonOSC rozšíření** (v `~/Music/Ableton/User Library/Remote
  Scripts/AbletonOSC/abletonosc/`):
  - `track.py`: nový `/live/track/insert_device` -- umí vložit nástroj/efekt
    z browseru (audio_effects, instruments, drums, max_for_live, plugins)
    podle jména, přes `Live.Application.browser.load_item()`. Stock
    AbletonOSC tohle neumělo (jen ovládá zařízení, co už na tracku jsou).
  - `application.py`: nový `/live/browser/children` -- prochází strom
    browseru podle jména, pro debug/objevování.
- **Pads Strings / Serum 2 macro mapping**: v průběhu session rostlo (29 ->
  97 -> 104 -> 129 parametrů, finální kontrola 2026-08-10 ~05:xx). Pořád se
  měnilo, jak se klikalo v Configure módu. Než cokoliv příště spouštíš, VŽDY
  nejdřív `audit_project()` znovu, čísla v tomhle logu jsou jen momentka.
  `wt_pos` (wavetable pozice) se do Live NEPROPSALA ani po opakovaném
  pokusu -- vědomé rozhodnutí nechat to tak, archetyp běží na 3/4. Živě
  vystavených bylo
  Live přes **Configure mode** (modré tlačítko v Live, ne Serum's vlastní
  right-click "Macro Control" -- to je jiná věc a stahuje jen na 8 slotů).
  Zahrnuje `Filter 1 Freq/Res/Drive/Wet/Stereo/Level`, oscilátory A/B/C/Sub,
  envelopy, atd. **`wt_pos` (wavetable pozice) v této sadě chybí** -- nebyl
  přes Configure naklikaný, potřebuje ještě jeden manuální krok v Serum UI
  (klik na wavetable pozici některého osc, dokud je Configure mode
  zapnutý).
- **`semantic_profiles.py`**: `SERUM2_EXPOSED_PARAMS` přemapován na sadu ze
  stavu s 97 parametry (starý mapping byl pro jinou, už neexistující
  instanci "1-Serum 2" z původního testovacího projektu). Sada mezitím
  narostla na 104 -- `SERUM2_EXPOSED_PARAMS` může být opět neúplný, ověřit
  přes `audit_project()` a doplnit chybějící jména než se příště archetyp
  nasazuje.
- **`archetype_manager.py` + `lcode_studio.db`**: 5 hotových žánrových
  archetypů. `Groove Tech-House Stab` byl nasazen na Pads Strings a 3 ze 4
  parametrů prošlo (`Filter 1 Freq/Res`, `C Unison`; `wt_pos` přeskočeno).
  POZOR: po nasazení jsi dál ručně točil knoflíky v Serum, takže aktuální
  hodnoty na Pads Strings už neodpovídají tomu, co archetyp nastavil --
  pokud chceš čistý archetyp, spusť `deploy_to_live_rack` znovu.

### Co zbývá (vyžaduje ruční krok v Live/Serum UI -- nejde přes OSC)

1. **Nasypat samply do Drum Racků** (Kick/Snare/Clap/HiHats) -- OSC neumí
   vkládat sample soubory, jen zařízení.
2. **Vybrat Serum presety** -- potvrzeno vyčerpávajícím auditem (browser
   strom prázdný, accessibility strom prázdný, VST3 parameter count,
   kompletní přečtení celého AbletonOSC balíku i README), že tovární
   presety (BA - Sub Amplitude apod.) NEJDOU vybrat programově -- Serum si
   je spravuje čistě interně, mimo Live Object Model.
3. **Domapovat `wt_pos`** na Pads Strings (Configure mode + klik na
   wavetable pozici) -- pak doběhne `Groove Tech-House Stab` na 4/4.
4. **Zopakovat Configure-mode mapping** na Sub Bass, Mid Bass, Synth Lead
   Plucks (mají zatím jen 1 parametr -- Device On) -- bez toho na ně
   `archetype_manager.py` nic neaplikuje.

### Důležité poznatky pro příště

- Macro/Configure mapping je **per-instance**, ne globální nastavení Serum
  2 -- nová instance pluginu vždy začíná od nuly, i na stejném typu tracku.
- Configure-mode mapping **přepisuje** předchozí sadu, není čistě aditivní
  (29 parametrů -> jiných 97, některé staré zmizely). Vždy si to znovu
  ověřit přes `audit_project()`, nespoléhat na to, co říká kód/dokumentace.
- Restart Ableton (přes `osascript ... quit` + `open apka.als`) je nutný po
  každé úpravě `abletonosc/*.py` souborů v Remote Scripts -- vždy nejdřív
  uložit projekt (Cmd+S), AbletonOSC restart neztratí projekt v paměti, ale
  jistota je jistota.
