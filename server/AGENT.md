# Server patch procedure (for the agent managing the server)

> [!WARNING]
> **UNOFFICIAL PATCH – USE AT YOUR OWN RISK.** Not made, endorsed or supported by the authors of Supersymmetry, GregTech CEu or Industrial Renewal. No warranty of any kind. Back up your world before using it.

Target: a Supersymmetry **0.2.0.1-patch2** server. Goal: replace two mod jars with the patched builds
without losing or changing any existing items or blocks.

## Why this is safe for existing worlds
- The patches do not change any block/item registry names, metadata, tile-entity IDs or NBT keys.
  Forge's ID map in `level.dat` stays the same, so no items are remapped or removed.
- Industrial Renewal storage racks: old save data is read with the same keys. On the first load the patched
  code re-links each rack stack and moves items that were orphaned in non-bottom racks back into the bottom one.
  It never deletes contents; anything that does not fit is dropped as items at the rack.
- GregTech Crafting Station: no save format change.

## Procedure
1. Announce maintenance and **stop the server** cleanly (`stop` in the console). Wait for the process to exit.
2. **Back up the world** (the whole `world/` directory, or whatever `level-name` in `server.properties` says).
   Keep the backup until the patched server has run fine for a while.
3. Check the current state:
   `bash install_patches.sh <server_dir> --check`
   Expected: `ORIGINAL` for both mods (or `PATCHED` if already done).
4. Install:
   `bash install_patches.sh <server_dir>`
   The script refuses to replace a jar whose SHA-1 is not the original pack jar. Do not force it; report instead.
5. Start the server and wait for `Done (` in the log.
6. Check `logs/latest.log` for:
   - `Missing` / `missing registry` / `remapping` lines mentioning `gregtech` or `industrialrenewal` → **stop and roll back**
   - `MultiBlock Machine: ... has no Master` → report (not fatal)
   - any `Exception` with `gregtech` or `industrialrenewal` in the stack trace → report
7. Tell players to update their client to the same two jars (or the patched modpack zip from Releases).
   A client without the patched jars can still connect, but the fixes only work with both sides patched.

## Rollback
Stop the server, then `bash install_patches.sh <server_dir> --rollback`, start again.
If items were affected, restore the world backup from step 2.

## Updating to a newer patch release
`patches.json` on the `main` branch always lists the current release. Re-run step 3–5; already patched jars with a
different hash are replaced (the old patched jar goes to the backup folder).
