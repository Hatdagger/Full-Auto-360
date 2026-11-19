#!/usr/bin/env python3
"""Extract an Xbox 360 game from a Games on Demand (GOD/SVOD) package or an XGD .iso.

    python3 god_extract.py <GOD header file | .iso> <out_dir> [--all | file ...]

With no file names it only writes god_info.json and filelist.txt into <out_dir>.
Files go to <out_dir>/game/. Extraction can be stopped and resumed: a half-written file
is kept as <name>.part and continued on the next run. Set GOD_TIME_BUDGET=<seconds> to
stop cleanly after that long (used when running in short shell sessions).

On Windows, build.bat uses `rexglue vfs dump` instead; this script is the cross-platform
fallback and the tool that was used to set the project up.
"""
import json, os, struct, sys, time

DEADLINE = time.time() + float(os.environ.get('GOD_TIME_BUDGET', '1e9'))
BLK = 0x1000
DATA_PER_FILE = 0xA1C4 * BLK      # data blocks per DataNNNN file (after hash blocks are removed)
GROUP_DATA = 0xCC * BLK           # 204 data blocks per level-0 hash block
MAGIC = b'MICROSOFT*XBOX*MEDIA'


def u32be(b, o):
    return struct.unpack_from('>I', b, o)[0]


def parse_god_header(path):
    h = open(path, 'rb').read()
    def u16s(off, n):
        return h[off:off + n].decode('utf-16-be', 'ignore').split('\x00')[0]
    return {
        'container': h[0:4].decode('latin1'), 'content_type': '%08X' % u32be(h, 0x344),
        'media_id': '%08X' % u32be(h, 0x354), 'version': u32be(h, 0x358),
        'title_id': '%08X' % u32be(h, 0x360), 'disc': '%d/%d' % (h[0x366], h[0x367]),
        'data_file_count': u32be(h, 0x39D), 'display_name': u16s(0x411, 0x80),
    }


class GodStream:
    """The GDF image inside a GOD package, with the hash blocks skipped."""
    def __init__(self, data_dir):
        self.files = sorted(os.path.join(data_dir, f) for f in os.listdir(data_dir) if f.startswith('Data'))
        self.handles = {}

    def read(self, off, size):
        out = bytearray()
        while size > 0:
            fi, foff = divmod(off, DATA_PER_FILE)
            group, ingroup = divmod(foff, GROUP_DATA)
            phys = 0x2000 + group * 0x1000 + foff   # 1 master + 1 per-group hash block
            n = min(size, GROUP_DATA - ingroup)
            fh = self.handles.get(fi) or self.handles.setdefault(fi, open(self.files[fi], 'rb'))
            fh.seek(phys)
            chunk = fh.read(n)
            if len(chunk) != n:
                raise IOError('short read in %s at 0x%x' % (self.files[fi], phys))
            out += chunk; off += n; size -= n
        return bytes(out)


class IsoStream:
    """The game partition of an XGD1/2/3 disc image (or a plain XISO)."""
    def __init__(self, path):
        self.fh = open(path, 'rb')
        for part in (0, 0xFD90000, 0x2080000, 0x18300000):
            self.fh.seek(part + 0x10000)
            if self.fh.read(20) == MAGIC:
                self.base = part; return
        raise SystemExit('no Xbox game partition found in ' + path)

    def read(self, off, size):
        self.fh.seek(self.base + off)
        return self.fh.read(size)


def find_magic(st):
    for blk in range(64):
        for sub in (0, 0x800):
            o = blk * BLK + sub
            if st.read(o, 20) == MAGIC:
                return o
    raise SystemExit('GDF volume descriptor not found')


def walk(st, base, sector, size, prefix, out):
    raw = st.read((sector - base) * 0x800, size)
    seen = set()
    def visit(off):
        if off in seen or off + 14 > len(raw):
            return
        seen.add(off)
        left, right, sec, sz, attr, nl = struct.unpack_from('<HHIIBB', raw, off)
        if left == 0xFFFF and right == 0xFFFF and sec == 0xFFFFFFFF:
            return
        name = raw[off + 14: off + 14 + nl].decode('latin1')
        if left not in (0, 0xFFFF):
            visit(left * 4)
        path = prefix + name
        if attr & 0x10:
            out.append({'path': path + '/', 'dir': True, 'sector': sec, 'size': sz})
            if sz:
                walk(st, base, sec, sz, path + '/', out)
        else:
            out.append({'path': path, 'dir': False, 'sector': sec, 'size': sz})
        if right not in (0, 0xFFFF):
            visit(right * 4)
    visit(0)


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(2)
    src, out_dir, want = sys.argv[1], sys.argv[2], sys.argv[3:]
    os.makedirs(out_dir, exist_ok=True)
    if src.lower().endswith('.iso'):
        info = {'container': 'ISO'}; st = IsoStream(src)
    else:
        info = parse_god_header(src); st = GodStream(src + '.data')
    m = find_magic(st)
    base = 32 - m // 0x800                       # the volume descriptor is sector 32
    root_sec, root_size = struct.unpack_from('<II', st.read(m, 0x800), 20)
    entries = []
    walk(st, base, root_sec, root_size, '', entries)
    files = [e for e in entries if not e['dir']]
    info.update({'file_count': len(files), 'total_bytes': sum(e['size'] for e in files)})
    json.dump(info, open(os.path.join(out_dir, 'god_info.json'), 'w'), indent=2)
    with open(os.path.join(out_dir, 'filelist.txt'), 'w') as f:
        for e in sorted(entries, key=lambda e: e['path'].lower()):
            f.write('%s\t%d\t%d\n' % (e['path'], e['size'], e['sector']))
    if want == ['--all']:
        todo = files
    else:
        lw = [w.lower() for w in want]
        todo = [e for e in files if e['path'].lower() in lw]
    for e in todo:
        dst = os.path.join(out_dir, 'game', *e['path'].split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and os.path.getsize(dst) == e['size']:
            continue
        part = dst + '.part'
        done = os.path.getsize(part) if os.path.exists(part) else 0
        off = (e['sector'] - base) * 0x800 + done
        left = e['size'] - done
        with open(part, 'ab') as f:
            while left > 0:
                if time.time() > DEADLINE:
                    print('TIME_BUDGET_REACHED', e['path'], flush=True); return
                n = min(left, 8 << 20)
                f.write(st.read(off, n)); off += n; left -= n
        os.replace(part, dst)
        print('extracted', e['path'], e['size'], flush=True)
    print(json.dumps(info, indent=2))
    print('ALL_DONE', len(todo))


if __name__ == '__main__':
    main()
