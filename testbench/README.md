# Migration test bench

> [!WARNING]
> **UNOFFICIAL PATCH – USE AT YOUR OWN RISK.** Test tooling only.

Checks that a world made with the ORIGINAL Supersymmetry 0.2.0.1-patch2 jars keeps all items after switching
to the patched jars via `server/install_patches.sh`.

Setup: unpack the official `server-0.2.0.1-patch2.zip` into `testbench/server/`, add the mods listed in its
`missing_mods.txt`, adjust `JAVA`/`BASH` paths at the top of `bench.py`. Running a server requires accepting
the Minecraft EULA (the bench writes `eula=true`).

- `python bench.py all` – synthetic test: fresh flat world on the original server, places storage racks
  (single, stacks of 2/3, orphaned-items stack, legacy save), storage chests and a GT Crafting Station with known
  contents, then runs the install script and the patched server and compares item totals, dropped items,
  block/item registry IDs and new log errors.
- `python bench.py realworld <save dir>` – copies a singleplayer save made with the original jars and compares
  every rack/chest/crafting station before and after (client-only sound IDs are dropped on the copy).
- `nbtdump.py` – minimal region/NBT reader used for the comparison.

Results on 2026-11-07: synthetic test ALL PASS (13 checks), real singleplayer world ALL PASS.
