"""Minimal Anvil/NBT reader: dumps the storage-rack, storage-chest and GT machine tile entities of a 1.12 world.

Usage: python nbtdump.py <world dir> <out.json>
"""
import gzip
import json
import os
import struct
import sys
import zlib


def read_tag(buf, pos, tag_type):
    """Reads one NBT payload.

    :param buf: bytes
    :param pos: offset of the payload
    :param tag_type: NBT tag id (1..12)
    :return: (value, new offset)
    """
    if tag_type == 1: return struct.unpack_from('>b', buf, pos)[0], pos + 1
    if tag_type == 2: return struct.unpack_from('>h', buf, pos)[0], pos + 2
    if tag_type == 3: return struct.unpack_from('>i', buf, pos)[0], pos + 4
    if tag_type == 4: return struct.unpack_from('>q', buf, pos)[0], pos + 8
    if tag_type == 5: return struct.unpack_from('>f', buf, pos)[0], pos + 4
    if tag_type == 6: return struct.unpack_from('>d', buf, pos)[0], pos + 8
    if tag_type == 7:
        n = struct.unpack_from('>i', buf, pos)[0]; return list(buf[pos + 4:pos + 4 + n]), pos + 4 + n
    if tag_type == 8:
        n = struct.unpack_from('>H', buf, pos)[0]; return buf[pos + 2:pos + 2 + n].decode('utf-8', 'replace'), pos + 2 + n
    if tag_type == 9:
        sub, n = struct.unpack_from('>bi', buf, pos); pos += 5; out = []
        for _ in range(n):
            v, pos = read_tag(buf, pos, sub); out.append(v)
        return out, pos
    if tag_type == 10:
        out = {}
        while True:
            t = buf[pos]; pos += 1
            if t == 0: return out, pos
            n = struct.unpack_from('>H', buf, pos)[0]; name = buf[pos + 2:pos + 2 + n].decode('utf-8', 'replace')
            pos += 2 + n
            out[name], pos = read_tag(buf, pos, t)
    if tag_type == 11:
        n = struct.unpack_from('>i', buf, pos)[0]; return list(struct.unpack_from('>%di' % n, buf, pos + 4)), pos + 4 + 4 * n
    if tag_type == 12:
        n = struct.unpack_from('>i', buf, pos)[0]; return list(struct.unpack_from('>%dq' % n, buf, pos + 4)), pos + 4 + 8 * n
    raise ValueError('bad tag %d' % tag_type)


def read_root(data):
    """Parses a root compound.

    :param data: uncompressed NBT bytes
    :return: dict
    """
    n = struct.unpack_from('>H', data, 1)[0]
    return read_tag(data, 3 + n, 10)[0]


def iter_chunks(region_dir):
    """Yields every chunk's root compound in a region directory.

    :param region_dir: path to <world>/region
    :return: generator of dicts
    """
    for name in os.listdir(region_dir):
        if not name.endswith('.mca'): continue
        with open(os.path.join(region_dir, name), 'rb') as f: data = f.read()
        for i in range(1024):
            off = int.from_bytes(data[i * 4:i * 4 + 3], 'big')
            if off == 0: continue
            start = off * 4096
            length, comp = struct.unpack_from('>iB', data, start)
            raw = data[start + 5:start + 4 + length]
            yield read_root(zlib.decompress(raw) if comp == 2 else gzip.decompress(raw))


def items_of(handler):
    """Summarises an ItemStackHandler compound.

    :param handler: dict with Items list
    :return: list of [slot, id, damage, count]
    """
    return [[it.get('Slot'), it.get('id'), it.get('Damage', 0), it.get('Count')] for it in handler.get('Items', [])]


def dump(world):
    """Collects relevant tile entities and dropped items.

    :param world: world directory
    :return: dict for JSON
    """
    out = {'racks': {}, 'chests': {}, 'machines': {}, 'dropped_items': []}
    for chunk in iter_chunks(os.path.join(world, 'region')):
        level = chunk.get('Level', {})
        for te in level.get('TileEntities', []):
            key = '%d,%d,%d' % (te['x'], te['y'], te['z'])
            tid = te.get('id', '')
            if tid == 'industrialrenewal:storage_rack' and te.get('master'):
                inv = te.get('inv', {})
                out['racks'][key] = {'items': items_of(inv), 'count': inv.get('count'), 'maxStack': inv.get('maxStack'),
                                     'bottom': te.get('bottom'), 'isTop': te.get('isTop')}
            elif tid == 'industrialrenewal:storage_chest' and te.get('master'):
                inv = te.get('inv', {})
                out['chests'][key] = {'size': inv.get('Size'), 'items': items_of(inv),
                                      'bottom': te.get('bottom'), 'isTop': te.get('isTop')}
            elif tid == 'gregtech:machine':
                mte = te.get('MetaTileEntity', {})
                out['machines'][key] = {'id': te.get('MetaId'),
                                        'internal': items_of(mte.get('InternalInventory', {})),
                                        'tools': items_of(mte.get('ToolInventory', {})),
                                        'grid': items_of(mte.get('CraftingGridInventory', {})),
                                        'crafted': mte.get('ItemsCrafted')}
        for ent in level.get('Entities', []):
            if ent.get('id') == 'minecraft:item':
                it = ent.get('Item', {})
                out['dropped_items'].append([it.get('id'), it.get('Count'), [round(p) for p in ent.get('Pos', [])]])
    return out


if __name__ == '__main__':
    result = dump(sys.argv[1])
    with open(sys.argv[2], 'w') as f: json.dump(result, f, indent=1, sort_keys=True)
    print('racks %d chests %d machines %d dropped %d' % (len(result['racks']), len(result['chests']),
                                                         len(result['machines']), len(result['dropped_items'])))
