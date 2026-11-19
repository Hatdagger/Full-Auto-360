# Game notes

Facts about the retail executable, gathered with `tools/xex_info.py` and `tools/god_extract.py`.

## Package

| | |
|---|---|
| Title | Full Auto |
| Title ID | `534507D5` |
| Media ID | `1D5F3880` |
| Source | Games on Demand package (`LIVE`, content type `00007000`), 21 data files |
| Contents | 247 files, 3,488,909,034 bytes |

## default.xex

| | |
|---|---|
| Size | 7,675,904 bytes |
| SHA1 | `855aefb7d2e227c8e71f33b6e68743cec5fc6f9a` |
| Version | 4 (base version 4) |
| Format | XEX2, retail-encrypted, basic compression |
| Original name | `FullAuto.pe` |
| Image | base `0x82000000`, size `0x7D0000` |
| Entry point | `0x82338758` |
| Stack | 512 KB default, 64 TLS slots |
| XDK | 2.0.2417.0 (November 2005; build paths say `xenon\nov05`) |
| XDK libraries | XAPILIB, XMP, XAUD, D3DX9, XBOXKRNL, XONLINE, XUIRUN, XUIRNDR, XMEDIA, XHV, LIBCMT, XGRAPHC, D3D9LTCG, X3DAUDL, XACTLTCG |

### Sections

| Name | Address | Size | Notes |
|---|---|---|---|
| `.rdata` | `82000600` | 720,580 | |
| `.pdata` | `820B0600` | 96,712 | 12,089 function entries |
| `.text` | `820D0000` | 6,026,292 | code, 93.6% covered by `.pdata` |
| `.no_bbt` | `8268F600` | 1,100 | code |
| `.embsec_` x7 | `8268FC00`–`826A4FE8` | 85,488 total | code (real PowerPC, 57 `.pdata` entries) |
| `.data` | `826B0000` | 659,096 | |
| `.XEXID`, `.idata`, `.XBLD`, `.reloc` | `82751000`+ | | |

### Addresses used in the manifest

| What | Address | How it was found |
|---|---|---|
| `setjmp` | `0x82580690` | stores f14–f31, r13–r31, LR, CR and r1 into the buffer in r3, returns 0; 10 callers |
| `longjmp` | `0x82580330` | the matching restore of the same 0x13C-byte buffer layout |

### Imports

`xam.xex` (75) and `xboxkrnl.exe` (152), both version 2.0.2417.0. Groups worth knowing:

- **Graphics:** `Vd*` (EDRAM, ring buffer, swap, display mode) — handled by ReXGlue's Xenos GPU layer
- **Audio:** `XAudio*`, `XMACreateContext`/`XMAReleaseContext` — XMA decode in ReXGlue's APU
- **Files:** `NtCreateFile`, `NtReadFile`, `NtQueryDirectoryFile`, `StfsCreateDevice`, `XamContent*` — saves and the `game:` / `D:` paths
- **Network / Live:** see [NETWORK.md](NETWORK.md)
- **Crypto:** `XeCryptSha`, `XeCryptRotSumSha`, `XeCryptBnQwBeSigVerify`, `XeKeysGetKey`, `XeKeysConsolePrivateKeySign`, `XeKeysConsoleSignatureVerification` — likely save signing

## Game files

| Folder | What is in it |
|---|---|
| `Media/` | music (`*.rxx`, two files per track name), XACT sound and wave banks (`*.xsb`/`*.xwb`, `XactCueList.txt`), WMV videos (`Pseudo720`, `AttractLoop720`, `AttractLoopAlt_FINAL`, `Credits`, `chromehounds`), XUI menus (`ui.xzp`, `uigame.xzp`), fonts |
| `piLaunch/` | boot and loading screens (`*.dds`, 720p and 480p versions), hint cards, `interface.xma`, `vshaders.dat` |
| `rtdXenon/` | track and level data (`fa_T*.pix`, `fa_frontend.pix`) and one 1.26 GB texture archive `textures.pit` |
| root | `default.xex`, `smallF.dat`, `pitaLocal.psc`, `$SystemUpdate/` (console system update, not used) |

The executable also looks for `D:\settings.psc`, `D:\TweakData_%s.psc` and `D:\pitaStats.txt`, and has debug strings for split screen tests and PIX captures.

## Manual jump tables

Kept in `[[switch_tables]]` in the manifest.

| bctr | Index | Entries | Where |
|---|---|---|---|
| `0x8230E43C` | r4 | 8 (table at `0x8230E440`) | `sub_8230E1A8`, run by the loader threads when a race loads. The switch reads a byte with no range check, so analysis kept only the first entry |

## Seen in headless tests

- Boot: `smallF.dat`, `pitaLocal.psc`, `piLaunch/vshaders.dat`, `rtdXenon/textures.pit`, the sound
  banks, `SEGA720.dds`, `Pseudo720.wmv`, `AttractLoop720.wmv`, then `title_screen1280x720.dds`,
  `ui.xzp`, three fonts, `dw_piLX2.pix` and `fa_frontend.pix`.
- Files the retail game looks for and does not have (normal, it carries on): `D:\pitaNot*.txt`,
  `D:\pitaStats.txt`, `D:\DebugLevel.psc`, `D:\TweakData_*.psc`, `D:\pilaunch\special_32.abc`,
  `D:\pilaunch\buttona.dds`, `buttonb.dds`, `hudgirder.dds`, `hudgirderholder.dds`,
  `hudwinarrow.dds`, `hudframe.dds`.
- Pressing A at the title: `XGIUserSetContextEx`, `XamContentCreateEnumerator` (no saves),
  `XamShowDeviceSelectorUI`, then a content package `pprofilescript1.txt` is created and mounted
  as `z:`. The file inside it is not found on the first run; check that saves stick.
- Kernel calls ReXGlue does not implement yet: `XeKeysConsolePrivateKeySign` (likely save
  signing) and `IoDismountVolumeByFileHandle`.
- Race music (`*.rxx`, XMA): FFmpeg logs hundreds of decode errors per race ("would have to skip
  N bits", "overflow in spectral RLE").

## If codegen reports an unresolved call

```
UnresolvedCall (1):
  0x82001234 from 0x82000F00: bl 0x82001234 from 0x82000F00 has a target in no function
```

The first address is the missing function. Add it to `fullauto_manifest.toml`:

```toml
[entrypoint.functions]
0x82001234 = {}
```

For a `b` (not `bl`) target, the function start may be earlier than the address; check a disassembly first.
