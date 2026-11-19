# Roadmap

Each phase ends with something you can test.

## Phase 0 — Setup ✅

- Game files extracted from the Games on Demand package (247 files, 3.49 GB, all sizes checked)
- `default.xex` decrypted and analyzed: 12,089 functions in `.pdata`, 227 system imports, XDK 2.0.2417 (Nov 2005)
- `setjmp`/`longjmp` located and added to the manifest
- ReXGlue 0.11.0 project created (`fullauto_manifest.toml`, CMake, `build.bat`)

## Phase 1 — First build

- [ ] Codegen passes validation (any "function in no function" errors get added to the manifest)
- [ ] Generated C++ compiles (Release)
- [ ] Links into `fullauto.exe`

## Phase 2 — Boot

- [ ] Pseudo Interactive / SEGA splash screens (`piLaunch/*.dds`)
- [ ] Title screen and "Press A"
- [ ] Main menu (XUI: `Media/ui.xzp`)
- [ ] Profile sign-in and save device prompts get sensible answers
- Known risk: the intro and attract videos are WMV through the XDK's XMV player; they may be black or skipped at first

## Phase 3 — Play offline

- [ ] Load a track (`rtdXenon/*.pix`, `textures.pit`) and finish a race
- [ ] Audio: XACT banks (`*.xwb/*.xsb`) and XMA music (`*.rxx`)
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
