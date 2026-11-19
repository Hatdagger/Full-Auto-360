// fullauto - test input for headless boot tests (built only with -DFULLAUTO_TEST_INPUT=ON)
//
// With the environment variable FULLAUTO_TEST_AUTOPRESS set, controller 1 reports as connected
// and taps A for 150 ms every few seconds (the value of the variable in milliseconds, 3000 when
// it is not a number). A test run with no controller can then get past "Press A" and through the
// menus. With the variable unset these hooks only pass the calls through.

#include <atomic>
#include <chrono>
#include <cstdlib>

#include "generated/default/fullauto_funcs.h"

namespace {

constexpr rex::u16 kButtonA = 0x1000;  // XINPUT_GAMEPAD_A

bool AutopressEnabled() {
  static const bool enabled = std::getenv("FULLAUTO_TEST_AUTOPRESS") != nullptr;
  return enabled;
}

long long AutopressPeriodMs() {
  static const long long period = [] {
    const char* value = std::getenv("FULLAUTO_TEST_AUTOPRESS");
    char* end = nullptr;
    long long ms = value ? std::strtoll(value, &end, 10) : 0;
    return (value && end != value && ms >= 500) ? ms : 3000LL;
  }();
  return period;
}

bool APressedNow() {
  using namespace std::chrono;
  static const auto start = steady_clock::now();
  const long long ms = duration_cast<milliseconds>(steady_clock::now() - start).count();
  return (ms % AutopressPeriodMs()) < 150;
}

std::atomic<rex::u32> g_packet{1};
std::atomic<bool> g_last_a{false};

}  // namespace

// XInputGetCapabilities(user, flags, caps): the game's jump to XamInputGetCapabilities.
REX_HOOK_RAW(sub_82337960) {
  const rex::u32 user = ctx.r3.u32;
  const rex::u32 caps = ctx.r5.u32;
  __imp__XamInputGetCapabilities(ctx, base);
  if (!AutopressEnabled() || user != 0 || ctx.r3.u32 == 0) {
    return;
  }
  // XINPUT_CAPABILITIES: Type, SubType, Flags, Gamepad (12 bytes), Vibration (4 bytes)
  REX_STORE_U8(caps + 0, 1);         // XINPUT_DEVTYPE_GAMEPAD
  REX_STORE_U8(caps + 1, 1);         // XINPUT_DEVSUBTYPE_GAMEPAD
  REX_STORE_U16(caps + 2, 0);        // Flags
  REX_STORE_U16(caps + 4, 0xF3FF);   // every button
  REX_STORE_U8(caps + 6, 0xFF);      // left trigger
  REX_STORE_U8(caps + 7, 0xFF);      // right trigger
  for (rex::u32 i = 0; i < 4; ++i) {
    REX_STORE_U16(caps + 8 + i * 2, 0xFFC0);  // sticks
  }
  REX_STORE_U16(caps + 16, 0xFFFF);  // vibration motors
  REX_STORE_U16(caps + 18, 0xFFFF);
  ctx.r3.u64 = 0;  // ERROR_SUCCESS
}

// XInputGetState(user, state): the game's jump to XamInputGetState(user, 0, state).
REX_HOOK_RAW(sub_82337968) {
  const rex::u32 user = ctx.r3.u32;
  const rex::u32 state = ctx.r4.u32;
  ctx.r5.u64 = ctx.r4.u64;
  ctx.r4.u64 = 0;
  __imp__XamInputGetState(ctx, base);
  if (!AutopressEnabled() || user != 0) {
    return;
  }
  const bool a = APressedNow();
  rex::u32 packet = g_packet.load();
  if (g_last_a.exchange(a) != a) {
    packet = ++g_packet;
  }
  // XINPUT_STATE: dwPacketNumber, then XINPUT_GAMEPAD (buttons, 2 triggers, 4 stick axes)
  REX_STORE_U32(state + 0, packet);
  REX_STORE_U16(state + 4, a ? kButtonA : 0);
  REX_STORE_U8(state + 6, 0);
  REX_STORE_U8(state + 7, 0);
  for (rex::u32 i = 0; i < 4; ++i) {
    REX_STORE_U16(state + 8 + i * 2, 0);
  }
  ctx.r3.u64 = 0;  // ERROR_SUCCESS
}

namespace {

// Hands out one A key down, then one A key up, each time a new tap period starts.
bool NextAKeystroke(rex::u16* flags) {
  using namespace std::chrono;
  static const auto start = steady_clock::now();
  static std::atomic<long long> handled_period{-1};
  static std::atomic<int> step{0};  // 0 idle, 1 key down sent
  const long long period =
      duration_cast<milliseconds>(steady_clock::now() - start).count() / AutopressPeriodMs();
  if (step.load() == 1) {
    step = 0;
    *flags = 0x0002;  // XINPUT_KEYSTROKE_KEYUP
    return true;
  }
  if (period > handled_period.load()) {
    handled_period = period;
    step = 1;
    *flags = 0x0001;  // XINPUT_KEYSTROKE_KEYDOWN
    return true;
  }
  return false;
}

}  // namespace

// XInputGetKeystroke(user, flags, keystroke): the game's call to XamInputGetKeystrokeEx, which the
// menus (XUI) read buttons through.
REX_HOOK_RAW(sub_82337990) {
  const rex::u32 user = ctx.r3.u32;
  const rex::u32 keystroke = ctx.r5.u32;
  if (AutopressEnabled() && (user == 0 || user == 0xFF)) {
    rex::u16 flags = 0;
    if (NextAKeystroke(&flags)) {
      // XINPUT_KEYSTROKE: VirtualKey, Unicode, Flags, UserIndex, HidCode
      REX_STORE_U16(keystroke + 0, 0x5800);  // VK_PAD_A
      REX_STORE_U16(keystroke + 2, 0);
      REX_STORE_U16(keystroke + 4, flags);
      REX_STORE_U8(keystroke + 6, 0);
      REX_STORE_U8(keystroke + 7, 0);
      ctx.r3.u64 = 0;  // ERROR_SUCCESS
    } else {
      ctx.r3.u64 = 0x10D2;  // ERROR_EMPTY: connected, nothing pressed
    }
    return;
  }
  __imp__sub_82337990(ctx, base);
}
