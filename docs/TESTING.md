# Headless testing (Linux)

A way to test the recompiled game without a GPU, a screen or a controller, for example in a
cloud workspace. Graphics are not drawn (null GPU), so this checks the game's logic, file loading
and system calls, not the picture.

## Build

The Linux preset expects Clang 20. With Clang 18 (Ubuntu 24.04) these extra flags work:

```sh
cmake --preset linux-amd64 \
  -DCMAKE_C_COMPILER=clang-18 -DCMAKE_CXX_COMPILER=clang++-18 \
  "-DCMAKE_C_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13" \
  "-DCMAKE_CXX_FLAGS=--gcc-install-dir=/usr/lib/gcc/x86_64-linux-gnu/13 -D__cpp_concepts=202002L -Wno-builtin-macro-redefined -Wno-macro-redefined" \
  -DREXGLUE_RECOMP_OPTIMIZATION_RELWITHDEBINFO=O1 \
  -DFULLAUTO_TEST_INPUT=ON
cmake --build --preset linux-amd64-relwithdebinfo --target fullauto_codegen
cmake out/build/linux-amd64      # configure again: CMake reads the generated file list only here
cmake --build --preset linux-amd64-relwithdebinfo
```

The SDK goes in `sdk/linux-amd64` (the `rexglue-sdk-0.11.0-linux-amd64.zip` release). On 2 cores
the first build takes about 4 minutes with `O1`.

## Run

```sh
FULLAUTO_TEST_AUTOPRESS=2500 SDL_VIDEODRIVER=offscreen SDL_AUDIODRIVER=dummy \
  out/build/linux-amd64/RelWithDebInfo/fullauto \
  --gpu.driver=null --kernel.headless=true --ui.fullscreen=false \
  --title.game_root=/path/to/game --app.user_root=/tmp/fa/user --app.log_root=/tmp/fa/logs \
  --log.level=debug --log.categories.filesystem=trace
```

- `FULLAUTO_TEST_AUTOPRESS=<ms>` (only in builds with `FULLAUTO_TEST_INPUT=ON`) makes controller 1
  report as connected and tap A every `<ms>` milliseconds, through both the controller state and
  the keystroke calls the menus use. Without it the game waits at the title screen.
- `--ui.driver=none` and `--apu.driver=none` are refused: the game needs a window and audio. SDL's
  `dummy` video driver has no display, `offscreen` works.
- `--kernel.headless=true` answers system dialogs (save device, sign-in) at once.
- The `filesystem` category at `trace` logs every file the game opens: the easiest way to see how
  far it got.

With A tapped every 2.5 s the game reaches a race in about 20 seconds: SEGA screen, logo and intro
videos (skipped), title screen, save device, menus, then `uigame.xzp` and a track (`fa_T121.pix`).

## When it stops

- `SIGILL` at `__builtin_trap(); // Switch case out of range` means a jump table has more entries
  than analysis found. Run under `gdb`, read the table from guest memory (host address
  `0x100000000 + guest address`, big-endian words) and add a `[[switch_tables]]` entry to
  `fullauto_manifest.toml` with the `bctr` address, the index register and every target.
- `llvm-symbolizer --obj=fullauto <offset>` turns the offsets in a crash report into generated
  function names (`sub_XXXXXXXX` is the guest address).
