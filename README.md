# Full Auto 360 — PC recomp

**Full Auto** (Xbox 360, 2006, Pseudo Interactive / SEGA) turned into a native PC program. No emulator.

The game's PowerPC code is translated to C++ ahead of time with the [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk), then compiled for your PC. Graphics, audio, input and the Xbox system calls run through ReXGlue's runtime.

**The goal:** the whole game on PC, with **online and LAN races (up to 8 players)** that work without Xbox Live.

> This repo contains **no game files and no game code**. You need your own copy of Full Auto.

---

## Status

| Step | |
|---|---|
| Game files pulled out of the Games on Demand package | ✅ |
| Game executable analyzed (functions, imports, network calls) | ✅ |
| ReXGlue project set up | ✅ |
| Recompile to C++ (codegen) | ✅ |
| Compiles and links | ✅ Linux test build · ⏳ Windows (first run on a PC) |
| Boots to the title screen | ✅ in a headless test (no graphics yet) |
| Races, audio, controller, saves | ⏳ a race loads and runs in a headless test; picture, sound and saves not checked yet |
| Split screen (2–4 players) | ⬜ |
| LAN races | ⬜ |
| Online races | ⬜ |

Details: [docs/ROADMAP.md](docs/ROADMAP.md)

---

## Build it (Windows 10/11)

1. **Double-click `build.bat`.**
2. First time only: it offers to install Microsoft's free **C++ Build Tools 2026 with Clang**. Say **Y** and approve the Windows prompt. (A few GB, one time.)
3. It downloads the ReXGlue SDK, checks your game files, recompiles and builds. The first build takes a while.
4. When it says **DONE**, double-click **`Play Full Auto.bat`**.

If it stops, the reason is at the bottom of the window and the full log is in `logs\last-build.log`.

## Your game files

They go in the `game` folder next to `build.bat`: `default.xex` plus the `Media`, `piLaunch` and `rtdXenon` folders (about 3.5 GB).

If `game` is empty, `build.bat` asks where your copy is. Drag in one of these:

- your **Games on Demand** folder (the one holding `534507D5`)
- an **.iso** of the disc
- a folder that already has the files unpacked

Saves go in `user\`, logs in `logs\`.

---

## Online and LAN

Full Auto only ever had **Xbox Live** online (8 players, ranked and player matches). It has no System Link mode, and Xbox Live for the 360 is gone.

So the recomp will answer the game's Xbox Live calls itself:

- **LAN:** PCs on the same network find each other's lobbies automatically. No server.
- **Online:** join a friend with a short code or IP address.

The game itself thinks it is on Xbox Live. Plan and progress: [docs/NETWORK.md](docs/NETWORK.md)

---

## For tinkerers

- `fullauto_manifest.toml` — codegen settings (addresses found during analysis)
- `src/` — game-specific host code and hooks
- `tools/god_extract.py` — unpack a Games on Demand package or ISO (any OS)
- `tools/xex_info.py` — dump the XEX headers, sections and imports
- [docs/TESTING.md](docs/TESTING.md) — headless test runs on Linux (no GPU or controller needed)
- [docs/GAME_NOTES.md](docs/GAME_NOTES.md) — what we know about the executable

## Credits

- [ReXGlue SDK](https://github.com/rexglue/rexglue-sdk) — the recompiler and runtime this is built on
- [Xenia](https://github.com/xenia-project/xenia) — the Xbox 360 research ReXGlue builds on
- [XenonRecomp](https://github.com/hedge-dev/XenonRecomp) — pioneered Xbox 360 static recompilation
- [Xenia Canary Netplay](https://github.com/AdrianCassar/xenia-canary) — reference for bringing Xbox Live games back online

Not affiliated with or endorsed by SEGA, Pseudo Interactive or Microsoft. Full Auto and its assets belong to their owners.
