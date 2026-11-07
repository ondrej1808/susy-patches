# Supersymmetry 0.2.0.1-patch2 – personal patches

> [!WARNING]
> **UNOFFICIAL PATCH – USE AT YOUR OWN RISK.** Not made, endorsed or supported by the authors of Supersymmetry, GregTech CEu or Industrial Renewal. No warranty of any kind. Back up your world before using it.

Unofficial fixes I made **for myself** for the
[Supersymmetry](https://github.com/SymmetricDevs/Supersymmetry) modpack, version **0.2.0.1-patch2**.
They are not made or supported by the mod or modpack authors. Use at your own risk and back up your world first.

The patches touch two different mods, so they live in two forks. This repository is the hub: README,
`.patch` files, a ready-to-import modpack zip, server install scripts and the built jars (in Releases).

## Versions

| Mod | Original jar in the pack | Upstream source | Patched branch | Changes vs. original |
|-----|--------------------------|-----------------|----------------|----------------------|
| GregTech CEu | `gregtech-1.12.2-2.8.10-beta.jar` | [GregTechCEu/GregTech @ `v2.8.10`](https://github.com/GregTechCEu/GregTech/tree/v2.8.10) | [ondrej1808/GregTech @ `susy-0.2.0.1-patch2`](https://github.com/ondrej1808/GregTech/tree/susy-0.2.0.1-patch2) | [compare v2.8.10…patch](https://github.com/ondrej1808/GregTech/compare/v2.8.10...susy-0.2.0.1-patch2) |
| Industrial Renewal | `IndustrialRenewal_1.12.2-0.21.8.jar` | [Cassiobsk8/Industrial_Renewal @ `f9389105`](https://github.com/Cassiobsk8/Industrial_Renewal/tree/f9389105) (branch `1.12.2`, version 0.21.8) | [ondrej1808/Industrial_Renewal @ `susy-0.2.0.1-patch2`](https://github.com/ondrej1808/Industrial_Renewal/tree/susy-0.2.0.1-patch2) | [compare f9389105…patch](https://github.com/ondrej1808/Industrial_Renewal/compare/f9389105...susy-0.2.0.1-patch2) |

Susy-Core (`Susy-Core-0.2.5.jar`) and everything else in the pack is unchanged.
No block/item IDs, registry names or save-data keys were changed, so existing worlds keep their items.

## What is fixed

### GregTech CEu 2.8.10 – Crafting Station
- **Search bar** on the connected-inventories tab: matches item names, `@modid` filters by mod.
- **Mouse wheel** scrolls the list one row at a time and no longer takes items from the tool slots or the two
  storage rows. The slots of the hidden tab used to stay active, so Mouse Tweaks acted on them.
- The recipe result reliably shows up after a **JEI/HEI recipe import** and after any grid change
  (upstream [#2285](https://github.com/GregTechCEu/GregTech/issues/2285)).
- Empty rows in the inventory list are removed correctly.
- Build: RetroFuturaGradle 1.4.9 and launchwrapper 1.17.4, because the original artifacts can no longer be downloaded.

### Industrial Renewal 0.21.8 – Storage Rack / Storage Chest
- **Items disappearing** when racks are stacked or broken: the whole stack is now re-linked at once, and on
  break the contents move to the remaining parts instead of being dumped or voided.
- Rack contents survive saving/reloading, and old saves are repaired on load.
- Racks and chests can be **opened from the top**. Only the same rack is placed on top (to build stacks).
- Chest GUI: **mouse wheel** scrolls over the slots (before Mouse Tweaks gets it), and **search** jumps to the
  line with a match (Enter jumps to the next one).
- Shift-click with a full inventory drops items instead of voiding them, the GUI closes when the stack changes,
  and breaking a rack no longer breaks its neighbour.

Full bug analysis and test scenarios:
[PATCH_STORAGE_RACK.md](https://github.com/ondrej1808/Industrial_Renewal/blob/susy-0.2.0.1-patch2/PATCH_STORAGE_RACK.md).

## Install – client (Prism Launcher)

**Easiest:** download `Supersymmetry-0.2.0.1-patch2-patched.zip` from
[Releases](https://github.com/ondrej1808/susy-patches/releases) and drag it onto Prism Launcher
(or *Add Instance → Import*). Prism downloads all mods from CurseForge and the two patched jars are already
inside the zip. If Prism reports mods that cannot be downloaded automatically, download them from the links it shows.

**Into an existing instance:** in `minecraft/mods` remove `gregtech-1.12.2-2.8.10-beta.jar` and
`IndustrialRenewal_1.12.2-0.21.8.jar` (keep them as a backup outside `mods`), then put in
`gregtech-1.12.2-2.8.10-beta-susypatch.jar` and `IndustrialRenewal_1.12.2-0.21.8-susypatch.jar` from Releases.

## Install – server

The server needs exactly the same two jars as the clients. With the server **stopped**:

```bash
curl -fsSLO https://raw.githubusercontent.com/ondrej1808/susy-patches/main/server/install_patches.sh
bash install_patches.sh /path/to/server            # install
bash install_patches.sh /path/to/server --check    # show what is installed
bash install_patches.sh /path/to/server --rollback # restore the original jars
```

The script downloads the jars listed in [`server/patches.json`](server/patches.json), verifies their SHA-256,
only replaces the **original** pack jars (verified by SHA-1), and moves the originals to
`mods-backup-<timestamp>/`. It is safe to re-run. Instructions for an automated agent managing the server are in
[`server/AGENT.md`](server/AGENT.md).

## Build from source
```bash
# GregTech (JDK 17+ for Gradle; it downloads a Java 8 toolchain)
git clone -b susy-0.2.0.1-patch2 https://github.com/ondrej1808/GregTech.git
cd GregTech && ./gradlew assemble -x spotlessCheck   # -> build/libs/gregtech-1.12.2-2.8.10-beta.jar

# Industrial Renewal (JDK 8, ForgeGradle 2.3)
git clone -b susy-0.2.0.1-patch2 https://github.com/ondrej1808/Industrial_Renewal.git
cd Industrial_Renewal && ./gradlew build              # -> build/libs/IndustrialRenewal_1.12.2-0.21.8.jar
```
Alternatively apply the files from [`patches/`](patches) with `git am` on top of the upstream tag/commit above.
The modpack zip is built with [`build_modpack.py`](build_modpack.py) from a Prism instance of the original pack.

## Licenses and credits
- **GregTech CEu** © GregTechCEu and contributors, **LGPL-3.0**. The modified version is under the same license.
- **Industrial Renewal** © Cassiobsk8, **CC BY-NC-SA 4.0**. The modified version is under the same license,
  non-commercial use only.
- **Supersymmetry** © SymmetricDevs, **LGPL-3.0** (the pack overrides in the modpack zip).
- All other mods are downloaded from CurseForge by the launcher and are not redistributed here.

All rights to the original mods belong to their authors. This repository only contains my modifications.
