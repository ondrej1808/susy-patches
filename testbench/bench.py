"""Migration test bench: original SuSy 0.2.0.1-patch2 server -> install_patches.sh -> patched server.

Phases (run all with no args, or one: seed | patch | verify):
  seed   - start the server with ORIGINAL jars on a fresh flat world, place storage racks / chests / a GT
           crafting station with known contents via commands, save, stop, dump -> before.json
  patch  - run server/install_patches.sh (real GitHub release download) on the server dir
  verify - start the PATCHED server on the same world, let it tick, save, stop, dump -> after.json,
           compare contents, registry IDs and logs, print PASS/FAIL

Usage: python bench.py [seed|patch|verify|all]
"""
import gzip
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SERVER = os.path.join(HERE, 'server')
WORLD = os.path.join(SERVER, 'world')
JAVA = r'C:\Program Files\Java\jdk1.8.0_211\bin\java.exe'
BASH = r'C:\Program Files\Git\bin\bash.exe'
INSTALL_SH = os.path.join(HERE, '..', 'susy-patches', 'server', 'install_patches.sh')
sys.path.insert(0, HERE)
import nbtdump  # noqa: E402


def item(slot, iid, count, dmg=0):
    """Builds an NBT item compound string.

    :param slot: slot index
    :param iid: item registry name
    :param count: stack count (byte)
    :param dmg: damage/meta
    :return: SNBT string
    """
    return '{Slot:%d,id:"%s",Count:%db,Damage:%ds}' % (slot, iid, count, dmg)


def rack(x, y, z, iid, count, max_stack, internal_count=1):
    """setblock command for a storage-rack master with contents.

    :param x,y,z: master position
    :param iid: stored item (None = empty)
    :param count: stored amount
    :param max_stack: capacity
    :param internal_count: Count byte of the stored "type" stack (legacy saves had garbage here)
    :return: command string
    """
    items = '[%s]' % item(0, iid, internal_count) if iid else '[]'
    return ('setblock %d %d %d industrialrenewal:storage_rack 4 replace '
            '{inv:{Size:1,Items:%s,count:%d,maxStack:%d,sync:1b},master:1b,checked:1b}'
            % (x, y, z, items, count if iid else 0, max_stack))


def chest(x, y, z, size, items):
    """setblock command for a storage-chest master with contents.

    :param x,y,z: master position
    :param size: inventory size
    :param items: list of item() strings
    :return: command string
    """
    return ('setblock %d %d %d industrialrenewal:storage_chest 4 replace '
            '{inv:{Size:%d,Items:[%s]},master:1b,checked:1b}' % (x, y, z, size, ','.join(items)))


# compact layout inside the spawn chunk (x 1..14, z 0..9); stacks are placed TOP FIRST so the original code
# never sees a bottom rack alone (it would shrink it and drop the overflow before the upper racks exist)
SEED = [
    'setworldspawn 0 10 0',
    # S1 single rack
    rack(1, 11, 0, 'minecraft:cobblestone', 3000, 4096),
    # S2 stack of 2, contents in bottom
    rack(5, 14, 0, None, 0, 4096),
    rack(5, 11, 0, 'minecraft:iron_ingot', 6000, 8192),
    # S3 stack of 2 with ORPHANED items in the top rack (bug #2 state)
    rack(9, 14, 0, 'minecraft:gold_ingot', 200, 4096),
    rack(9, 11, 0, 'minecraft:gold_ingot', 500, 8192),
    # S4 stack of 3
    rack(13, 17, 0, None, 0, 4096),
    rack(13, 14, 0, None, 0, 4096),
    rack(13, 11, 0, 'minecraft:redstone', 10000, 12288),
    # S5 legacy: count 256 saved with Count byte 0
    rack(1, 11, 5, 'minecraft:diamond', 256, 4096, internal_count=0),
    # C1 single chest
    chest(5, 11, 5, 99, [item(0, 'minecraft:stone', 64), item(50, 'minecraft:apple', 32),
                         item(98, 'minecraft:diamond_sword', 1, 7)]),
    # C2 stack of 2 chests, contents in bottom
    chest(9, 14, 5, 99, []),
    chest(9, 11, 5, 198, [item(0, 'minecraft:coal', 64), item(120, 'minecraft:glass', 16),
                          item(197, 'minecraft:emerald', 5)]),
    # W1 GregTech crafting station
    ('setblock 13 11 5 gregtech:machine 0 replace {MetaId:"gregtech:workbench",FrontFacing:2,MetaTileEntity:{'
     'FrontFacing:2,InternalInventory:{Size:18,Items:[%s,%s]},ToolInventory:{Size:9,Items:[%s]},'
     'CraftingGridInventory:{Size:9,Items:[%s]},ItemsCrafted:42}}'
     % (item(0, 'minecraft:iron_ingot', 64), item(17, 'minecraft:stick', 60),
        item(0, 'minecraft:iron_pickaxe', 1, 5), item(0, 'minecraft:planks', 1))),
]

# expected item totals per scenario after migration: masters (bottom first) -> (item, total)
EXPECT_RACKS = {
    'S1': (['1,11,0'], 'minecraft:cobblestone', 3000),
    'S2': (['5,11,0', '5,14,0'], 'minecraft:iron_ingot', 6000),
    'S3': (['9,11,0', '9,14,0'], 'minecraft:gold_ingot', 700),
    'S4': (['13,11,0', '13,14,0', '13,17,0'], 'minecraft:redstone', 10000),
    # legacy save: the original code may already have lost the item type; expect 'same as before'
    'S5': (['1,11,5'], 'minecraft:diamond', None),
}


class Server:
    """Runs the Forge server as a child process with console access."""

    def __init__(self, log_name, extra_jvm=()):
        """Starts the server.

        :param log_name: file in HERE where the console output is copied
        """
        self.lines = queue.Queue()
        self.log = open(os.path.join(HERE, log_name), 'w', encoding='utf-8', errors='replace')
        self.proc = subprocess.Popen(
            [JAVA, '-Xms4G', '-Xmx6G'] + list(extra_jvm) + ['-jar', 'forge-1.12.2-14.23.5.2860.jar', 'nogui'],
            cwd=SERVER, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding='utf-8', errors='replace', bufsize=1)
        threading.Thread(target=self._pump, daemon=True).start()

    def _pump(self):
        """Copies console output to the log file and the line queue."""
        for line in self.proc.stdout:
            self.log.write(line); self.log.flush()
            self.lines.put(line)
        self.lines.put(None)

    def wait_for(self, text, timeout):
        """Waits for a console line containing text.

        :param text: substring to wait for
        :param timeout: seconds
        :return: the matching line
        :raises RuntimeError: on timeout or server exit
        """
        end = time.time() + timeout
        while time.time() < end:
            try:
                line = self.lines.get(timeout=1)
            except queue.Empty:
                continue
            if line is None: raise RuntimeError('server exited while waiting for %r' % text)
            if text in line: return line
        raise RuntimeError('timeout waiting for %r' % text)

    def cmd(self, command):
        """Sends a console command.

        :param command: command without leading slash
        """
        self.proc.stdin.write(command + '\n'); self.proc.stdin.flush()

    def save_and_stop(self):
        """save-all flush, stop, wait for exit."""
        self.cmd('save-all flush'); self.wait_for('Saved the world', 300)
        self.cmd('stop'); self.proc.wait(600); self.log.close()


def write_server_config():
    """Writes eula.txt (consent given by the user) and a test server.properties."""
    with open(os.path.join(SERVER, 'eula.txt'), 'w') as f: f.write('eula=true\n')
    props = {'level-type': 'FLAT', 'generate-structures': 'false', 'online-mode': 'false', 'server-port': '25599',
             'spawn-protection': '0', 'max-tick-time': '-1', 'view-distance': '4', 'level-seed': '1',
             'spawn-monsters': 'false',
             # SuSy's world-type prompt: Super Flat
             'defaultworldgenerator-port': '3bc7e023-60a1-11ee-b9f3-80e82ceaaf53', 'spawn-animals': 'false', 'spawn-npcs': 'false', 'motd': 'susy patch bench'}
    with open(os.path.join(SERVER, 'server.properties'), 'w') as f:
        f.writelines('%s=%s\n' % kv for kv in props.items())


def registry_ids():
    """Reads FML block/item ID maps for gregtech and industrialrenewal from level.dat.

    :return: dict name -> id
    """
    with gzip.open(os.path.join(WORLD, 'level.dat')) as f: root = nbtdump.read_root(f.read())
    ids = {}
    for reg, data in root.get('FML', {}).get('Registries', {}).items():
        if reg not in ('minecraft:blocks', 'minecraft:items'): continue
        for e in data.get('ids', []):
            if e['K'].startswith(('gregtech:', 'industrialrenewal:')): ids[reg + '/' + e['K']] = e['V']
    return ids


def spawn_xz():
    """Reads the overworld spawn from level.dat (spawn chunks are always loaded there).

    :return: (x, z) rounded to a chunk corner
    """
    with gzip.open(os.path.join(WORLD, 'level.dat')) as f: d = nbtdump.read_root(f.read())['Data']
    return (d['SpawnX'] // 16) * 16, (d['SpawnZ'] // 16) * 16


def shift_cmd(cmd, ox, oz):
    """Shifts the x/z coordinates of a 'setblock x y z ...' command.

    :param cmd: command
    :param ox,oz: offset
    :return: shifted command
    """
    p = cmd.split(' ', 4)
    return ' '.join([p[0], str(int(p[1]) + ox), p[2], str(int(p[3]) + oz), p[4]])


def shift_key(key, ox, oz):
    """Shifts an "x,y,z" key.

    :param key: key
    :param ox,oz: offset
    :return: shifted key
    """
    x, y, z = map(int, key.split(','))
    return '%d,%d,%d' % (x + ox, y, z + oz)


def phase_seed():
    """Fresh world with original jars, place test content, dump before.json."""
    if os.path.exists(WORLD): shutil.rmtree(WORLD)
    write_server_config()
    s = Server('log-1-original.log')
    s.wait_for('Done (', 1800)
    s.cmd('save-all flush'); s.wait_for('Saved the world', 300)  # writes level.dat with the spawn
    ox, oz = spawn_xz()
    json.dump([ox, oz], open(os.path.join(HERE, 'offset.json'), 'w'))
    for c in SEED[1:]:
        s.cmd(shift_cmd(c, ox, oz)); time.sleep(0.5)
    time.sleep(20)  # let the multiblocks tick (original linking logic)
    s.save_and_stop()
    json.dump(nbtdump.dump(WORLD), open(os.path.join(HERE, 'before.json'), 'w'), indent=1, sort_keys=True)
    json.dump(registry_ids(), open(os.path.join(HERE, 'ids-before.json'), 'w'), indent=1, sort_keys=True)


def phase_patch():
    """Runs the real server install script (downloads the GitHub release)."""
    for args in ([], ['--check']):
        r = subprocess.run([BASH, INSTALL_SH, SERVER.replace('\\', '/')] + args, capture_output=True, text=True)
        print(r.stdout, r.stderr)
        if r.returncode: raise SystemExit('install_patches.sh failed')


def total(entry):
    """Item total of one dumped rack.

    :param entry: dumped rack dict
    :return: (item id or None, count)
    """
    if not entry or not entry['items'] or not entry['count']: return None, 0
    return entry['items'][0][1], entry['count']


def phase_verify():
    """Patched server on the same world, dump after.json, compare, print PASS/FAIL."""
    s = Server('log-2-patched.log')
    s.wait_for('Done (', 1800)
    time.sleep(30)  # first ticks: relink + migration
    s.save_and_stop()
    before = json.load(open(os.path.join(HERE, 'before.json')))
    after = nbtdump.dump(WORLD)
    json.dump(after, open(os.path.join(HERE, 'after.json'), 'w'), indent=1, sort_keys=True)
    ok = True
    ox, oz = json.load(open(os.path.join(HERE, 'offset.json')))

    def report(name, passed, detail):
        nonlocal ok
        ok &= passed
        print('%-4s %-28s %s' % ('PASS' if passed else 'FAIL', name, detail))

    for name, (masters, iid, expected) in EXPECT_RACKS.items():
        masters = [shift_key(m, ox, oz) for m in masters]
        tot_b = sum(total(before['racks'].get(m))[1] for m in masters)
        got = [total(after['racks'].get(m)) for m in masters]
        tot_a = sum(c for i, c in got if i == iid)
        bottom_ok = got[0][1] == tot_a
        if expected is None: expected = tot_b
        report('rack ' + name, tot_a == expected and bottom_ok,
               'before %d -> after %d (expected %d, all in bottom: %s)' % (tot_b, tot_a, expected, bottom_ok))
    for key in (shift_key('5,11,5', ox, oz), shift_key('9,11,5', ox, oz)):
        b = sorted(map(tuple, before['chests'].get(key, {}).get('items', [])))
        a = sorted(map(tuple, after['chests'].get(key, {}).get('items', [])))
        report('chest ' + key, a == b and len(a) > 0, '%d stacks before, %d after' % (len(b), len(a)))
    wk = shift_key('13,11,5', ox, oz)
    wb, wa = before['machines'].get(wk), after['machines'].get(wk)
    report('crafting station', wb is not None and wb == wa, 'identical' if wb == wa else '%s -> %s' % (wb, wa))
    report('dropped items', not after['dropped_items'], str(after['dropped_items'][:5]))
    ids_b = json.load(open(os.path.join(HERE, 'ids-before.json')))
    ids_a = registry_ids()
    report('registry IDs unchanged', ids_a == ids_b, '%d ids' % len(ids_a))
    def interesting(path):
        """Error-ish lines mentioning the patched mods, without timestamps."""
        lines = open(os.path.join(HERE, path), encoding='utf-8', errors='replace').read().splitlines()
        return {re.sub(r'@[0-9a-f]{6,8}', '@X', l.split('] ', 1)[-1]) for l in lines if ('Exception' in l or 'Missing' in l or 'has no Master' in l
                or 'ERROR' in l) and ('gregtech' in l.lower() or 'industrialrenewal' in l.lower())}
    bad = sorted(interesting('log-2-patched.log') - interesting('log-1-original.log'))
    report('patched log clean', not bad, '; '.join(bad[:3]))
    print('\nRESULT:', 'ALL PASS' if ok else 'SOME FAILED')


def groups(entries):
    """Groups dumped multiblock masters into vertical stacks (same x,z, masters 3 blocks apart).

    :param entries: dict "x,y,z" -> data
    :return: dict "x,z@bottomY" -> list of keys bottom first
    """
    by_col = {}
    for k in entries:
        x, y, z = map(int, k.split(','))
        by_col.setdefault((x, z), []).append(y)
    out = {}
    for (x, z), ys in by_col.items():
        ys.sort(); cur = []
        for y in ys:
            if cur and y - cur[-1] != 3:
                out['%d,%d@%d' % (x, z, cur[0])] = ['%d,%d,%d' % (x, yy, z) for yy in cur]; cur = []
            cur.append(y)
        out['%d,%d@%d' % (x, z, cur[0])] = ['%d,%d,%d' % (x, yy, z) for yy in cur]
    return out


def item_totals(entries, keys, rack):
    """Sums items over a stack.

    :param entries: dumped racks or chests
    :param keys: master keys of one stack
    :param rack: True for racks (count field), False for chests (slot counts)
    :return: dict item id/meta -> count
    """
    t = {}
    for k in keys:
        e = entries.get(k)
        if not e: continue
        if rack:
            if e['items'] and e['count']:
                iid = '%s:%s' % (e['items'][0][1], e['items'][0][2]); t[iid] = t.get(iid, 0) + e['count']
        else:
            for _, iid, dmg, cnt in e['items']:
                key = '%s:%s' % (iid, dmg); t[key] = t.get(key, 0) + cnt
    return t


def phase_realworld(save_dir):
    """Runs a real singleplayer save (made with the ORIGINAL jars) through the patched server and compares.

    :param save_dir: path to the save folder (copied, never modified)
    """
    if os.path.exists(WORLD): shutil.rmtree(WORLD)
    shutil.copytree(save_dir, WORLD)
    write_server_config()
    before = nbtdump.dump(WORLD)
    json.dump(before, open(os.path.join(HERE, 'real-before.json'), 'w'), indent=1, sort_keys=True)
    ids_b = registry_ids()
    print('before: racks %d chests %d machines %d dropped %d' % (len(before['racks']), len(before['chests']),
                                                                 len(before['machines']), len(before['dropped_items'])))
    phase_patch()
    # singleplayer saves contain client-only sound IDs; confirm dropping them (copy only, no items/blocks)
    s = Server('log-3-realworld.log', ['-Dfml.queryResult=confirm'])
    s.wait_for('Done (', 1800)
    time.sleep(30)
    s.save_and_stop()
    after = nbtdump.dump(WORLD)
    json.dump(after, open(os.path.join(HERE, 'real-after.json'), 'w'), indent=1, sort_keys=True)
    ok = True
    for kind, rack in (('racks', True), ('chests', False)):
        for gname, keys in sorted(groups(before[kind]).items()):
            keys_a = groups(after[kind]).get(gname, keys)
            tb, ta = item_totals(before[kind], keys, rack), item_totals(after[kind], keys_a, rack)
            bottom_only = all(not item_totals(after[kind], [k], rack) for k in keys_a[1:]) if rack else True
            passed = tb == ta and bottom_only
            ok &= passed
            print('%-4s %-6s %-14s %d floors  before %s  after %s%s' % (
                'PASS' if passed else 'FAIL', kind[:-1], gname, len(keys), tb, ta,
                '' if bottom_only else '  (items not all in bottom!)'))
    for k, wb in sorted(before['machines'].items()):
        wa = after['machines'].get(k)
        passed = wb == wa
        ok &= passed
        print('%-4s machine %s %s' % ('PASS' if passed else 'FAIL', k, wb.get('id')))
    new_drops = len(after['dropped_items']) - len(before['dropped_items'])
    print('%-4s dropped items: %d before, %d after' % ('PASS' if new_drops <= 0 else 'FAIL',
                                                       len(before['dropped_items']), len(after['dropped_items'])))
    ok &= new_drops <= 0
    ids_a = registry_ids()
    print('%-4s registry IDs unchanged (%d)' % ('PASS' if ids_a == ids_b else 'FAIL', len(ids_a)))
    ok &= ids_a == ids_b
    print('\nRESULT:', 'ALL PASS' if ok else 'SOME FAILED')


if __name__ == '__main__':
    if len(sys.argv) > 2 and sys.argv[1] == 'realworld':
        phase_realworld(sys.argv[2]); sys.exit(0)
    phase = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if phase in ('seed', 'all'): phase_seed()
    if phase in ('patch', 'all'): phase_patch()
    if phase in ('verify', 'all'): phase_verify()
