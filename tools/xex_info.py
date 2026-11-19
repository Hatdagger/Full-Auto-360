#!/usr/bin/env python3
"""Small XEX2 inspector used to set up the Full Auto recomp project.

Prints the headers of an Xbox 360 XEX2 file, decrypts + decompresses the PE image
(writes <out_dir>/basefile.bin), lists PE sections and resolves the kernel/XAM imports to
names using the export tables in a ReXGlue SDK source checkout. Writes xex_report.json.

usage: python3 xex_info.py <default.xex> <out_dir> <rexglue-sdk source dir> [lzxdec binary]

Needs the `cryptography` package. lzxdec (build it from lzxdec.c + libmspack's lzxd.c) is
only needed for LZX-compressed XEX files; Full Auto uses basic compression.
"""
import json, os, re, struct, subprocess, sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

RETAIL_KEY = bytes.fromhex('20B185A59D28FDC340583FBB0896BF91')
DEVKIT_KEY = bytes(16)

HEADER_NAMES = {
    0x000002FF: 'resource_info', 0x000003FF: 'file_format_info', 0x000005FF: 'delta_patch_descriptor',
    0x00010001: 'original_base_address', 0x00010100: 'entry_point', 0x00010201: 'image_base_address',
    0x000103FF: 'import_libraries', 0x00018002: 'checksum_timestamp', 0x00018102: 'enabled_for_callcap',
    0x00018200: 'enabled_for_fastcap', 0x000183FF: 'original_pe_name', 0x000200FF: 'static_libraries',
    0x00020104: 'tls_info', 0x00020200: 'default_stack_size', 0x00020301: 'default_filesystem_cache_size',
    0x00020401: 'default_heap_size', 0x00028002: 'page_heap_size_and_flags', 0x00030000: 'system_flags',
    0x00040006: 'execution_info', 0x00040201: 'title_workspace_size', 0x00040310: 'game_ratings',
    0x00040404: 'lan_key', 0x000405FF: 'xbox360_logo', 0x000406FF: 'multidisc_media_ids',
    0x000407FF: 'alternate_title_ids', 0x00040801: 'additional_title_memory', 0x00E10402: 'exports_by_name',
}

def be32(b, o): return struct.unpack_from('>I', b, o)[0]
def be16(b, o): return struct.unpack_from('>H', b, o)[0]

def load_export_names(sdk):
    names = {}
    for lib, rel in (('xboxkrnl.exe', 'src/kernel/xboxkrnl/export_table.inc'),
                     ('xam.xex', 'src/kernel/xam/export_table.inc'),
                     ('xbdm.xex', 'src/kernel/xbdm/export_table.inc')):
        p = os.path.join(sdk, rel)
        if not os.path.exists(p): continue
        for m in re.finditer(r'REX_EXPORT\(\s*\w+\s*,\s*(0x[0-9A-Fa-f]+)\s*,\s*(\w+)\s*,\s*(\w+)', open(p).read()):
            names[(lib, int(m.group(1), 16))] = (m.group(2), m.group(3))
    return names

def main():
    xex_path, out_dir, sdk = sys.argv[1:4]
    lzxdec = sys.argv[4] if len(sys.argv) > 4 else 'lzxdec'
    os.makedirs(out_dir, exist_ok=True)
    x = open(xex_path, 'rb').read()
    assert x[:4] == b'XEX2', 'not an XEX2 file'
    module_flags, pe_off, _res, sec_off, hdr_count = struct.unpack_from('>IIIII', x, 4)
    report = {'module_flags': '%08X' % module_flags, 'pe_data_offset': pe_off,
              'security_info_offset': sec_off, 'headers': {}}
    hdrs = {}
    for i in range(hdr_count):
        key, val = struct.unpack_from('>II', x, 0x18 + i * 8)
        hdrs[key] = val
        report['headers'][HEADER_NAMES.get(key, '%08X' % key)] = '%08X' % val

    def blob(key):  # optional header that points to data whose first dword is its size
        off = hdrs[key]; return x[off: off + be32(x, off)]

    info = {}
    if 0x00010100 in hdrs: info['entry_point'] = '%08X' % hdrs[0x00010100]
    if 0x00010201 in hdrs: info['image_base'] = '%08X' % hdrs[0x00010201]
    if 0x00020200 in hdrs: info['default_stack_size'] = hdrs[0x00020200]
    if 0x00020401 in hdrs: info['default_heap_size'] = hdrs[0x00020401]
    if 0x00030000 in hdrs: info['system_flags'] = '%08X' % hdrs[0x00030000]
    if 0x000183FF in hdrs:
        b = blob(0x000183FF); info['original_pe_name'] = b[4:].split(b'\0')[0].decode('latin1')
    if 0x00040006 in hdrs:
        o = hdrs[0x00040006]
        media_id, version, base_version, title_id = struct.unpack_from('>IIII', x, o)
        platform, exe_type, disc_no, disc_count = x[o + 16: o + 20]
        savegame_id = be32(x, o + 20)
        def ver(v): return '%d.%d.%d.%d' % (v >> 28, (v >> 24) & 0xF, (v >> 8) & 0xFFFF, v & 0xFF)
        info['execution_info'] = {'media_id': '%08X' % media_id, 'version': ver(version),
                                  'base_version': ver(base_version), 'title_id': '%08X' % title_id,
                                  'disc': '%d/%d' % (disc_no, disc_count), 'savegame_id': '%08X' % savegame_id}
    if 0x00040404 in hdrs:
        o = hdrs[0x00040404]; info['lan_key'] = x[o:o + 16].hex().upper()
    if 0x00020104 in hdrs:
        o = hdrs[0x00020104]; info['tls'] = dict(zip(('slot_count', 'raw_data_address', 'data_size', 'raw_data_size'),
                                                     struct.unpack_from('>IIII', x, o)))
    if 0x000200FF in hdrs:
        b = blob(0x000200FF); libs = []
        for i in range((len(b) - 4) // 16):
            e = b[4 + i * 16: 4 + i * 16 + 16]
            name = e[:8].split(b'\0')[0].decode('latin1')
            maj, minr, bld, qfe = struct.unpack_from('>HHHH', e, 8)
            libs.append('%s %d.%d.%d.%d' % (name, maj, minr, bld, qfe & 0xFF))
        info['static_libraries'] = libs
    if 0x000407FF in hdrs:
        b = blob(0x000407FF); info['alternate_title_ids'] = ['%08X' % be32(b, 4 + i * 4) for i in range((len(b) - 4) // 4)]

    # --- security info
    s = sec_off
    image_size = be32(x, s + 4)
    image_flags = be32(x, s + 0x10C)
    load_address = be32(x, s + 0x110)
    import_table_count = be32(x, s + 0x128)
    enc_key = x[s + 0x150: s + 0x160]
    region = be32(x, s + 0x178)
    allowed_media = be32(x, s + 0x17C)
    page_count = be32(x, s + 0x180)
    pages = []
    for i in range(page_count):
        v = be32(x, s + 0x184 + i * 24)
        pages.append((v >> 4, v & 0xF))  # (page count, info: 1=code 2=data 3=readonly)
    info.update({'image_size': image_size, 'image_flags': '%08X' % image_flags,
                 'load_address': '%08X' % load_address, 'region': '%08X' % region,
                 'allowed_media': '%08X' % allowed_media, 'security_page_descriptors': page_count})

    # --- file format (encryption/compression)
    ff = hdrs[0x000003FF]
    ff_size = be32(x, ff); enc_type = be16(x, ff + 4); comp_type = be16(x, ff + 6)
    info['encryption'] = {0: 'none', 1: 'normal'}.get(enc_type, enc_type)
    info['compression'] = {0: 'none', 1: 'basic', 2: 'normal (LZX)', 3: 'delta'}.get(comp_type, comp_type)
    data = x[pe_off:]
    if enc_type == 1:
        # Retail key. (Devkit XEX files use an all-zero key instead.)
        d = Cipher(algorithms.AES(RETAIL_KEY), modes.ECB()).decryptor()
        session = d.update(enc_key) + d.finalize()
        dec = Cipher(algorithms.AES(session), modes.CBC(bytes(16))).decryptor()
        n = len(data) - len(data) % 16
        data = dec.update(data[:n]) + dec.finalize() + data[n:]

    if comp_type == 2:
        window = be32(x, ff + 8)
        first_block_size = be32(x, ff + 12)
        p = 0; out = bytearray(); bs = first_block_size
        while bs:
            nxt = p + bs
            next_size = be32(data, p); q = p + 24
            while True:
                cs = be16(data, q); q += 2
                if cs == 0: break
                out += data[q:q + cs]; q += cs
            p = nxt; bs = next_size
        lz_in = os.path.join(out_dir, 'image.lzx'); open(lz_in, 'wb').write(out)
        img_path = os.path.join(out_dir, 'basefile.bin')
        r = subprocess.run([lzxdec, lz_in, img_path, str(image_size), str(window)], capture_output=True, text=True)
        info['lzx'] = r.stderr.strip(); os.remove(lz_in)
        img = open(img_path, 'rb').read()
    elif comp_type == 1:
        nblk = (ff_size - 8) // 8; img = bytearray(); p = 0
        for i in range(nblk):
            ds, zs = struct.unpack_from('>II', x, ff + 8 + i * 8)
            img += data[p:p + ds]; img += bytes(zs); p += ds
        img = bytes(img); open(os.path.join(out_dir, 'basefile.bin'), 'wb').write(img)
    else:
        img = data[:image_size]; open(os.path.join(out_dir, 'basefile.bin'), 'wb').write(img)
    assert img[:2] == b'MZ', 'decrypted image does not start with MZ - wrong key?'

    # --- PE sections
    e_lfanew = struct.unpack_from('<I', img, 0x3C)[0]
    nsec = struct.unpack_from('<H', img, e_lfanew + 6)[0]
    opt_size = struct.unpack_from('<H', img, e_lfanew + 20)[0]
    sec_tab = e_lfanew + 24 + opt_size
    sections = []
    for i in range(nsec):
        o = sec_tab + i * 40
        name = img[o:o + 8].split(b'\0')[0].decode('latin1')
        vsize, vaddr, rsize, raddr = struct.unpack_from('<IIII', img, o + 8)
        flags = struct.unpack_from('<I', img, o + 36)[0]
        sections.append({'name': name, 'va': '%08X' % (load_address + vaddr), 'vsize': vsize,
                         'flags': '%08X' % flags, 'code': bool(flags & 0x20)})
    info['sections'] = sections

    # --- pdata function count
    for sct in sections:
        if sct['name'] == '.pdata':
            off = int(sct['va'], 16) - load_address
            n = sct['vsize'] // 8
            info['pdata_functions'] = sum(1 for i in range(n) if be32(img, off + i * 8) != 0)

    # --- imports
    names = load_export_names(sdk)
    b = blob(0x000103FF)
    str_size, lib_count = struct.unpack_from('>II', b, 4)
    strs = b[12:12 + str_size].split(b'\0'); strs = [t.decode('latin1') for t in strs if t]
    p = 12 + str_size
    imports = []
    for li in range(lib_count):
        size = be32(b, p)
        # layout: size(4) next_import_digest(20) id(4) version(4) version_min(4) name_index(2) count(2) records[count](4)
        lib_id, lver, lvermin = struct.unpack_from('>III', b, p + 24)
        nidx, rcount = struct.unpack_from('>HH', b, p + 36)
        recs = [be32(b, p + 40 + i * 4) for i in range(rcount)]
        lib = strs[nidx]
        def ver(v): return '%d.%d.%d.%d' % (v >> 28, (v >> 24) & 0xF, (v >> 8) & 0xFFFF, v & 0xFF)
        entries = []
        for addr in recs:
            # the import record in the image: high byte = type (0 variable, 1 thunk), low 16 bits = ordinal
            off = addr - load_address
            if 0 <= off < len(img):
                v = be32(img, off); typ = v >> 24; ordinal = v & 0xFFFF
                if typ == 0:   # variable slot; thunks follow as type 1 with same ordinal
                    nm = names.get((lib, ordinal), ('ordinal_%X' % ordinal, '?'))
                    entries.append({'ordinal': '%03X' % ordinal, 'name': nm[0], 'kind': nm[1], 'slot': '%08X' % addr})
        imports.append({'library': lib, 'version': ver(lver), 'min_version': ver(lvermin), 'records': rcount,
                        'imports': entries})
        p += size
    info['imports'] = imports
    report['info'] = info
    json.dump(report, open(os.path.join(out_dir, 'xex_report.json'), 'w'), indent=2)
    # human summary
    ei = info.get('execution_info', {})
    print('title', ei, '\nentry', info.get('entry_point'), 'base', info.get('image_base'), 'size', hex(image_size))
    print('format', info['encryption'], info['compression'], info.get('lzx'))
    print('pe name', info.get('original_pe_name'))
    print('static libs:', ', '.join(info.get('static_libraries', [])))
    print('sections:'); [print('  ', s_) for s_ in sections]
    print('pdata functions:', info.get('pdata_functions'))
    for lib in imports:
        print('%s v%s: %d imports' % (lib['library'], lib['version'], len(lib['imports'])))

if __name__ == '__main__':
    main()
