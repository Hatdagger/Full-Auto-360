# Roadmap

Each phase ends with something you can test.

## Phase 0 — Setup ✅

- Game files extracted from the Games on Demand package (247 files, 3.49 GB, all sizes checked)
- `default.xex` decrypted and analyzed: 12,089 functions in `.pdata`, 227 system imports, XDK 2.0.2417 (Nov 2005)
- `setjmp`/`longjmp` located and added to the manifest
- ReXGlue 0.11.0 project created (`fullauto_manifest.toml`, CMake, `build.bat`)

## Phase 1 — First build

- [x] Codegen passes validation (0 errors on the first run, 100 C++ files, ~105 MB)
- [x] Generated C++ compiles (Linux test build; Windows not yet run)
- [x] Links (Linux `fullauto`; Windows `fullauto.exe` not yet run)
- Fixed: a fresh folder needs codegen, then a second CMake configure, then the build. `build.bat` does this.

## Phase 2 — Boot

Headless tests (no picture, see [TESTING.md](TESTING.md)) reach all of these. They still need a look on a real screen.

- [x] Pseudo Interactive / SEGA splash screens (`piLaunch/*.dds`) and the logo and intro videos
- [x] Title screen and "Press A" (left alone, it goes back to the attract video after ~30 s)
- [x] Main menu (XUI: `Media/ui.xzp`), driven by A presses
- [x] Save device prompt answered; the game creates its profile save package
- Known risk: the intro and attract videos are WMV through the XDK's XMV player; they may be black or skipped at first

## Phase 3 — Play offline

- [ ] Load a track (`rtdXenon/*.pix`, `textures.pit`) and finish a race. Headless: `fa_T121` loads
  and the race runs for 4+ minutes without a crash, after a jump table fix in the manifest
- [ ] Audio: XACT banks (`*.xwb/*.xsb`) and XMA music (`*.rxx`). FFmpeg reports decode errors on
  the race music; listen for glitches
- [ ] Controller, then keyboard
- [ ] Career saves
- [ ] Unwreck (the time rewind) works and stays in sync
- [ ] Split screen, 2 to 4 players

## Phase 4 — LAN races

- [ ] The game's Xbox Live menus open with a local "signed in" profile
- [ ] Host a lobby on one PC, see it from another PC on the same network
- [ ] Race start, positions and weapons stay in sync for 2, then 8 players
- See [NETWORK.md](NETWORK.md)

## Phase 5 — Online races

- [ ] Join over the internet by code or IP
- [ ] NAT traversal (UPnP and/or hole punching), relay only if needed
- [ ] Leaderboards and stats kept locally

## Phase 6 — Polish

- [ ] Higher resolution and widescreen options
- [ ] Higher frame rate, if the game logic allows it
- [ ] Controller-driven launcher in the style of the game's own menus
- [ ] Linux / Steam Deck build
- [ ] Mod loading
