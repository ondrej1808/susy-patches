"""UNOFFICIAL PATCH - USE AT YOUR OWN RISK.

Builds a Prism/CurseForge-importable modpack zip: original Supersymmetry pack + patched jars.

The zip contains the original CurseForge manifest (mods are downloaded by the launcher from CurseForge)
with the patched mods removed from the manifest, the original pack overrides (config, groovy, resources, ...)
and the patched jars as overrides/mods/*.jar.

Usage:
    python build_modpack.py <prism instance dir> <out.zip> <patched jar> [<patched jar> ...]
"""
import json
import os
import sys
import zipfile

# CurseForge project IDs replaced by the patched jars
PATCHED_PROJECTS = {
    557242: 'GregTech CEu',
    299849: 'Industrial Renewal',
}
PACK_SUFFIX = '+ondrej1808-patches'


def load_manifest(instance_dir):
    """Reads the CurseForge manifest Prism stored for the instance.

    :param instance_dir: Prism instance folder (contains flame/manifest.json)
    :return: manifest dict
    :raises FileNotFoundError: if the instance was not installed from a CurseForge pack
    """
    with open(os.path.join(instance_dir, 'flame', 'manifest.json'), encoding='utf-8') as f:
        return json.load(f)


def load_overrides(instance_dir):
    """Reads the list of override files the original pack shipped (relative to .minecraft).

    :param instance_dir: Prism instance folder (contains flame/overrides.txt)
    :return: list of relative paths with forward slashes
    """
    with open(os.path.join(instance_dir, 'flame', 'overrides.txt'), encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]


def build(instance_dir, out_zip, jars):
    """Writes the modpack zip.

    :param instance_dir: Prism instance folder of the ORIGINAL (unpatched) pack
    :param out_zip: output zip path
    :param jars: patched mod jar paths, put into overrides/mods/
    :return: None; prints a summary. Missing override files are reported and skipped.
    """
    manifest = load_manifest(instance_dir)
    before = len(manifest['files'])
    manifest['files'] = [f for f in manifest['files'] if f['projectID'] not in PATCHED_PROJECTS]
    removed = before - len(manifest['files'])
    if removed != len(PATCHED_PROJECTS):
        raise SystemExit(f'expected to remove {len(PATCHED_PROJECTS)} mods, removed {removed}')
    manifest['name'] = manifest.get('name', 'Supersymmetry') + ' (UNOFFICIAL patched - use at your own risk)'
    manifest['version'] = manifest.get('version', '') + PACK_SUFFIX
    manifest['author'] = manifest.get('author', '') + ', patches: ondrej1808'
    manifest['overrides'] = 'overrides'

    mc_dir = os.path.join(instance_dir, 'minecraft')
    missing = 0
    with zipfile.ZipFile(out_zip, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json', json.dumps(manifest, indent=2))
        for rel in load_overrides(instance_dir):
            src = os.path.join(mc_dir, *rel.split('/'))
            if os.path.isfile(src):
                z.write(src, 'overrides/' + rel)
            else:
                missing += 1
                print('missing override:', rel)
        for jar in jars:
            z.write(jar, 'overrides/mods/' + os.path.basename(jar))
    print(f'{out_zip}: {len(manifest["files"])} CurseForge mods, {len(jars)} patched jars, '
          f'{missing} missing overrides, {os.path.getsize(out_zip) / 1e6:.1f} MB')


if __name__ == '__main__':
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    build(sys.argv[1], sys.argv[2], sys.argv[3:])
