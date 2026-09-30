# Úpravy AbletonOSC (L-Code)

`lcode-abletonosc.patch` = naše rozšíření AbletonOSC oproti původnímu repu
(`AbletonOSC_reference`, commit `0ca68214bd62c9b5cb641ca34006cfd70ba94430`):

- `track.py`: `/live/track/insert_device` – vloží nástroj/efekt z browseru podle jména
- `application.py`: `/live/browser/children` – procházení stromu browseru

Živá kopie, kterou Live načítá:
`~/Music/Ableton/User Library/Remote Scripts/AbletonOSC/`

Obnova na čisté AbletonOSC:
```bash
git -C AbletonOSC_reference apply ../abletonosc_patches/lcode-abletonosc.patch
cp AbletonOSC_reference/abletonosc/{track,application}.py \
   ~/Music/Ableton/"User Library/Remote Scripts/AbletonOSC/abletonosc/"
```
Po změně souborů v Remote Scripts je nutný restart Live (nejdřív Cmd+S).
Po každé úpravě živých souborů patch přegenerovat (`diff -u`), jinak se rozejde.
