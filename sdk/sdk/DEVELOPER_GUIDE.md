# GP-50 SDK developer guide

This describes Peppercorn v0.1.0. Everything below has been used to build firmware that runs on a GP-50 (v0.1.0, A1.1.0i).
"Supported" means what this guide describes (summary: `sdk/SUPPORTED_SURFACE.md`).

## 1. What you are building on

The Valeton GP-50 is a guitar multi-effects pedal with two main processors:

- **NDS32 main processor**: runs the user interface (screen, knobs, footswitches), presets, USB/MIDI host messages
  and the effect catalog.
- **ARM Cortex-M4F audio processor**: runs the effect chain at 44.1 kHz in 64-frame blocks. Each effect group
  (NR, PRE, MOD, DLY, ...) has an execution slot into which one effect's code is loaded.

The SDK never ships Valeton's firmware. You supply the official **GP-50 V1.1.0** update file; the builder checks its
exact hash, applies the platform's changes and your code, and writes a new update file. The stock functions run
unmodified from that file; the platform adds small hooks plus its own C. You install the result with Valeton Suite like
an official update and can always go back by installing the official file.

There are two things you can add:

| You want to | Write | Runs on | Starter |
| --- | --- | --- | --- |
| Process audio (a new effect in a group's list) | an **ARM effect**: C plus `effect.json` | ARM | `sdk/effects/chop_trem/` (tremolo) |
| Add logic the host can talk to (read/write values, react on a tick) | an **NDS32 feature component**: C plus `component.json` | NDS32 | `sdk/nds/components/user_examples/answer/` |

You never choose addresses, edit linker scripts or write assembly. The builder places code and data automatically and
refuses builds that do not fit or break a rule.

## 2. What you need

- The official GP-50 **V1.1.0** update file (`Valeton GP-50 V1.1.0.bin`), unmodified.
- macOS (the only host checked so far) with **Python 3.11+**.
- **liblzo2** (e.g. `brew install lzo`): the firmware container is LZO-compressed.
- For NDS32 components: the qualified **nds32le-elf GCC** toolchain (`sdk/NDS_TOOLCHAIN.md`).
- **Apple Clang** and **ARM GNU 14.2.rel1 binutils** (every build).
- Node.js only if you want to run the JavaScript host tests.

The builder never talks to a pedal. Loading an image is done by you, with Valeton Suite.

## 3. Writing an ARM audio effect

### Files

Copy the starter and rename it:

```sh
mkdir -p user_effects
cp -R sdk/effects/chop_trem user_effects/my_effect
```

`effect.json` describes the effect:

| Field | Meaning |
| --- | --- |
| `name` | Display name on the pedal (keep it short; labels clip around 13 characters) |
| `type_name` | Type shown with it |
| `group` | Effect group (6 = MOD in the starter) |
| `public_id` | 32-bit ID, **unique within the group**; presets store this ID |
| `source`, `init`, `process` | Your C file and the two entry-point names |
| `parameters` | Up to 8 entries: `name`, `storage_index` (0..7), `min`, `max`, `step`, `default`, `knob` (255 = none), `flags`, `display_code` |

### The C interface (`sdk/include/gp50_effect.h`)

```c
#include "gp50_effect.h"
GP50_INIT    void my_init(const float *params);
GP50_PROCESS void my_process(float *samples, uint32_t frames, const float *params,
                             uint32_t reserved_r3, const uint8_t *enable,
                             const uint32_t *beat_period_ms, void *reserved_b18);
```

- `init` runs once when the effect is loaded into its slot.
- `process` runs for every block from the audio interrupt, **even when bypassed**: if `*enable == 0`, return without
  touching the buffer.
- `samples` is interleaved stereo float32, processed in place. The chain is mono in practice: read word 0 of each frame
  and write both words. Honour `frames` (64 today).
- `params[i]` is the value of the parameter with `storage_index` i, already clamped and stepped.
- `beat_period_ms` is 60000 / tempo, for tempo-synced effects.

Rules: single-precision float only (no doubles: the FPU has no double hardware); no libc/libm, no heap, no calls or data
outside your slot; zero-initialised static state lives in the slot after your code; small stack; never block. Your code
plus state must fit the group's slot (the builder reports a fit failure).

### Test on your computer first

```sh
clang -std=c11 -Wall -Wextra -Werror -fsanitize=undefined -I sdk/include -I user_effects/my_effect \
  sdk/tests/test_chop_trem.c -o /tmp/my_check && /tmp/my_check
```

Adapt the test to your algorithm (unity gain, bypass, bounds). A native pass says nothing about CPU cost.

### CPU cost

The pedal refuses a change that would overload the audio processor ("CPU FULL"). An effect without a measured cost is
charged a conservative allowance and the total shows `?`, so heavy chains may be refused early. Real cost and sound
quality are checked on hardware.

## 4. Writing a main-processor feature (ABI 3)

### What a feature is

A feature is a folder with a `component.json` and some C files. It runs on the pedal's main processor (NDS32), inside
the application loop that runs the screen, knobs, footswitches and USB/MIDI. You don't write a loop or a thread.
You write **callbacks** that the pedal calls at defined moments, and inside them you call **services** that read and
change the pedal. Everything is in one header, [`sdk/nds/components/gp50.h`](nds/components/gp50.h): no addresses,
no firmware structures, no screen objects.

Typical features: "the right footswitch toggles the reverb instead", "knob 3 sets the delay mix on the home screen",
"show something in the effect editor", "let my web page read and set a value", "remember a setting per preset".

### Callbacks: when the pedal calls you

All callbacks are optional; declare the ones you use in `component.json`. Each gets `const gp50_ctx *ctx`, whose
`ctx->state` is your private memory (`resources.state_bytes`, zeroed at boot). Two callbacks of the same feature never
run at the same time.

| Callback | When | What you return |
| --- | --- | --- |
| `init` | once at boot, before the screen and USB exist | nothing |
| `tick` | repeatedly from the application loop (not a clock; use `gp50_millis()`) | nothing |
| `event` | a control was used, a preset loaded or the screen changed (see below) | `GP50_CONSUMED` (the pedal skips its normal action) or `GP50_PASS` |
| `get` | a computer sent `12 <selector>` | reply length; reply = schema byte + payload; 0 refuses |
| `set` | a computer sent `11 <selector> <host.set_bytes bytes>` | `GP50_OK` or `GP50_REFUSED` |
| `status` | the effect editor refreshes its status line | text length (max `GP50_STATUS_TEXT_MAX`), 0 for none; must not change anything |
| `preset_save` / `preset_load` | the preset is saved / loaded: your own bytes stored with each preset | bytes written / nothing |
| `about` | the Global settings > About page is drawn | one line of text (max `GP50_ABOUT_TEXT_MAX`), 0 for none; all features share `GP50_ABOUT_LINES_MAX` lines under the copyright text |
| `strip` | the effect editor shows a block, about 10 times a second | fill a `gp50_strip` (label, value, bar level) and return 1 to show a meter strip above the parameters, 0 for none |
| `menu_value` / `menu_change` | your Global settings tile shows an item's value (when selected, then about twice a second) / knob 1..3 turned while the tile is selected (item 1..3) | text length (max `GP50_MENU_TEXT_MAX`) / `GP50_OK` |

Events, as `gp50_event { kind, index, screen, value }`:

| kind | index | value | delivered |
| --- | --- | --- | --- |
| `GP50_EVENT_FOOTSWITCH` | `GP50_FOOTSWITCH_LEFT` / `_RIGHT` | 1 | every press the pedal would turn into a block toggle, unless the switch is set up as an A/B parameter switch |
| `GP50_EVENT_KNOB` | `GP50_KNOB_1..3` | steps turned (+ = clockwise) | home screen, unless knob assignment drives that knob; also the editor in builds with the assignment feature |
| `GP50_EVENT_PRESET` | preset number | 0 | after every preset load (cannot be consumed) |
| `GP50_EVENT_ENCODER` | 0 | steps turned (+ = clockwise) | home and editor screens, in builds with the assignment feature |
| `GP50_EVENT_BACK`, `_DRUM`, `_DRUM_HOLD`, `_PARA` | 0 | 0 | EXIT, DRUM pressed, DRUM held, PARA pressed: home and editor screens, in builds with the assignment feature |
| `GP50_EVENT_SCREEN` | the new `GP50_SCREEN_*` | 0 | the screen changed (cannot be consumed) |

"The assignment feature" is Peppercorn's knob and footswitch assignment (`assignment`), which is part of the release
set. `screen` is `GP50_SCREEN_HOME`, `GP50_SCREEN_EDITOR`, `GP50_SCREEN_DRUM` or `GP50_SCREEN_OTHER`. Features see
events in id order; the first that consumes wins.

### Services: what you can call

| Area | Calls |
| --- | --- |
| Blocks (`GP50_NR` .. `GP50_NS`) | `gp50_block_model` (public ID), `gp50_block_enabled`, `gp50_block_set_enabled` (CPU protection applies), `gp50_block_select` (by public ID), `gp50_block_model_count` / `gp50_block_model_at` (browse), `gp50_block_name` |
| Parameters of a block's current model | `gp50_param_count`, `gp50_param_get`, `gp50_param_range` (min, max, step), `gp50_param_set` (like setting its knob: rounds, clamps, updates sound, screen and editors, marks the preset modified), `gp50_param_nudge` (like turning its knob), `gp50_param_name`, `gp50_param_text` (the value as shown) |
| Presets | `gp50_preset_number`, `gp50_preset_mark_modified` |
| Knob and footswitch assignments | `gp50_assignments_get`, `gp50_assignments_set`, `gp50_assignments_recover` |
| Screens | `gp50_screen`, `gp50_screen_open` (home, drum), `gp50_pedal_mode` (Patch or Stomp) |
| Home screen | `gp50_home_title` / `gp50_home_title_restore`, `gp50_home_knob_tile` / `gp50_home_knob_tile_reset` |
| Effect editor | `gp50_editor_block`, `gp50_editor_knob_param`, `gp50_editor_expression_page`, `gp50_editor_text` / `gp50_editor_text_clear` (a title-strip prompt or a full page of text) |
| Drum machine | `gp50_drum_playing`, `gp50_drum_set_playing` |
| Expression pedal | `gp50_expression_get` (on or off, its assignment, calibrated position) |
| Meters | `gp50_stock_meters_get` (gain reduction of the stock Gate, COMP and COMP4), `gp50_meter_get` (an SDK effect that reports gain reduction) |
| Load | `gp50_dsp_load` (the estimate CPU protection uses, in percent), `gp50_load_get` (measured) |
| Time | `gp50_millis`, `gp50_elapsed_ms` |
| Host | `gp50_host_notify` (send `12 <your selector> <payload>` to a connected editor unprompted) |

Services that can fail return `GP50_OK` or `GP50_REFUSED`; refused means nothing changed. Parameter values are
`float`s in the unit the screen shows. Limits are named in `gp50.h` (`GP50_HOST_BYTES_MAX`, `GP50_MENU_ITEMS_MAX`,
`GP50_PRESET_BYTES_MAX`, ...); the build checks your manifest against the same names, so don't hard-code the numbers.

### Pedal example: a Global settings tile showing the CPU load

[`sdk/nds/components/features/cpu_load/`](nds/components/features/cpu_load/) adds a 12th tile, "CPU", to Global
settings, after About. Selecting it shows "CPU load: 47%" (the estimate CPU protection uses), refreshed about twice a
second, and a computer reads the same value with `12 7a` (`Pedal.cpuLoad`). The manifest declares the tile:

```json
"callbacks": {"menu_value": "cpu_load_value", "get": "cpu_load_get"},
"menu": {"title": "CPU", "items": ["CPU load", "ARM", "DSP"]},
```

```c
uint32_t cpu_load_value(const gp50_ctx *ctx, uint32_t item, char *out, uint32_t capacity) {   /* "menu_value" */
    /* item GP50_MENU_ITEM_1: writes the number + "%" (or "--" when unknown) and returns its length */
}
uint32_t cpu_load_get(const gp50_ctx *ctx, uint8_t *out, uint32_t capacity) {  /* "get", selector 0x7a */
    /* writes 01, percent low byte, percent high byte (ffff = unknown) and returns 3 */
}
```

`cpu_load` has three items: "CPU load" (the estimate, `gp50_dsp_load`), "ARM" and "DSP" (measured, from
`gp50_load_get`: the latest busy ratio the audio processor and its coprocessor report, the same numbers as the host's
`12 50`; "--" until a fresh reading arrives).

The platform draws one centred line per item, "<item label>: <value>", in the About page's style. A feature with
settings to change adds `menu_change`: knob 1 changes item 1, knob 2 item 2, knob 3 item 3 (`delta` = signed knob
steps). The stock menu has one free slot, so one feature per image may have a menu (`GP50_MENU_TILES_MAX`); the
build refuses a second.

### Worked example: the right footswitch toggles a chosen block (computer-only)

This example runs on the computer only (see its README). On the pedal it would switch a block behind the stock
footswitch assignment, so the home screen would show the wrong label: a good illustration of the callbacks, a bad
pedal feature. Features you put on a pedal should use the pedal's own mechanisms where one exists and never change
existing behaviour silently.

[`sdk/nds/components/feature_examples/fs_block/`](nds/components/feature_examples/fs_block/). The right footswitch, on
the home screen, toggles one block chosen from a computer; until one is chosen the footswitch keeps its normal job. The
choice is kept per preset; the effect editor shows e.g. "FS2: DLY".

`component.json`:

```json
{
  "abi": 3,
  "id": "fs_block",
  "sources": ["fs_block_main.c"],
  "callbacks": {"init": "fs_block_init", "event": "fs_block_event", "get": "fs_block_get", "set": "fs_block_set",
                "status": "fs_block_status", "preset_save": "fs_block_save", "preset_load": "fs_block_load"},
  "host": {"selector": 121, "set_bytes": 1, "max_reply_bytes": 3},
  "preset_bytes": 1,
  "resources": {"state_bytes": 4, "stack_bytes": 128, "tick_us": 0}
}
```

The heart of `fs_block_main.c`:

```c
#include "gp50.h"
#define OFF 0xffu                       /* no block chosen: the footswitch keeps its normal job */
typedef struct { uint8_t block; } State;

uint32_t fs_block_event(const gp50_ctx *ctx, const gp50_event *e) {
    State *s = ctx->state;
    if (e->kind != GP50_EVENT_FOOTSWITCH || e->index != GP50_FOOTSWITCH_RIGHT || e->screen != GP50_SCREEN_HOME
        || s->block == OFF)
        return GP50_PASS;                                       /* not ours: the pedal does its usual thing */
    (void)gp50_block_set_enabled(s->block, !gp50_block_enabled(s->block));   /* refused = CPU full */
    return GP50_CONSUMED;
}

/* Host: 12 79 -> 12 79 01 <block> <on>;   11 79 <block>  (0xff = off) */
uint32_t fs_block_set(const gp50_ctx *ctx, const uint8_t *in, uint32_t n) {
    State *s = ctx->state;
    if (n != 1 || (in[0] >= GP50_BLOCKS && in[0] != OFF)) return GP50_REFUSED;
    if (s->block != in[0]) { s->block = in[0]; gp50_preset_mark_modified(); }
    return GP50_OK;
}
```

From a web page: `await pedal.writeComponent(identity, 0x79, Uint8Array.of(8))` makes it toggle the reverb;
`await pedal.readComponent(identity, 0x79, {schema: 1, length: 3})` reads `[1, block, on]`.

### Test on your computer first

```bash
python3 sdk/nds/components/native/run_native.py sdk/nds/components/feature_examples/fs_block
```

`run_native.py` compiles your sources with every `test_*.c` in your folder against a simulated pedal
(`sdk/nds/components/native/gp50_native.h`): tests press footswitches, turn knobs, load and save presets, send host
messages and check the result with `GP50_CHECK`. The simulation follows the contract in `gp50.h`; it is not an
emulator of the firmware, so the pedal remains the final test.

### Manifest reference (ABI 3)

| Field | Meaning |
| --- | --- |
| `abi` | 3 |
| `id` | your name: lowercase letters, digits, `_`; callbacks and source files start with `<id>_`, tests are `test_*.c` |
| `sources` | your C files, inside the folder |
| `callbacks` | role → function name, any of the roles above |
| `host` (optional) | `selector` (`GP50_HOST_SELECTOR_FIRST..LAST`, one per feature), `set_bytes` (exact SET length, 0 = no SET), `max_reply_bytes` |
| `preset_bytes` (optional) | your per-preset bytes, up to `GP50_PRESET_BYTES_MAX`; needs `preset_save` and `preset_load` |
| `menu` (optional) | `{"title": "...", "items": ["...", ...]}`: the Global settings tile; title up to `GP50_MENU_TITLE_MAX` characters, up to `GP50_MENU_ITEMS_MAX` items (one per knob) of `GP50_MENU_TEXT_MAX` characters; needs `menu_value`; one feature per image |
| `resources` | `state_bytes`, `stack_bytes` (the build measures every callback path, including the services you call, and refuses the image if one needs more: fs_block's footswitch path measures 104), `tick_us` (your estimate, needed with a tick) |

### Rules

- Return quickly: no waiting, no loops on hardware, no recursion, no allocation, no flash writes, no audio work.
- Keep all state in `ctx->state`; never keep pointers to buffers you were given.
- Give your `static` helpers names unique to your feature (e.g. a short prefix): the build's stack check cannot
  tell apart same-named helpers in different files and refuses the image.
- `status` and `menu_value` only format text.
- There is no sandbox: wrong C can still crash the pedal. Test natively, then on a preset you can afford to change, and keep the official
  firmware for going back.

### Status of this interface

- Tested on the pedal (v0.1.0 firmware): events, blocks, parameters, presets, time, host GET/SET/notify, status line,
  editor strip, home tiles/title, per-preset storage, Global settings tile, load readings.
- Per-preset storage: your `preset_save` bytes are written with a normal Save into a reserved area of the preset slot,
  tied by checksum to that preset's record, and handed to `preset_load` after the preset loads (copies, renames and
  imports start with none). All features share 432 bytes per preset (2 + id length + preset_bytes each; checked).
- About-page lines (`about`): work, but a line squeezes the About text; prefer a Global settings tile.
- Global settings tile: knob-changed items (`menu_change`) are tested natively and in emulation only (no shipped feature
  changes a value).
- Reading the expression pedal and the assignments, the drum calls and the meter strip: used by Peppercorn's own features on the pedal.
- Not yet: expression pedal events, drawing your own graphics.
- ABI 1 (host-only components, `component.h`, example `user_examples/answer`) still works.

## 5. Building an image

**On top of Peppercorn** (the usual way), from the repository root:

```sh
firmware/build_custom.sh "/path/to/Valeton GP-50 V1.1.0.bin" /path/to/nds32-toolchain/prefix \
  /opt/homebrew/opt/lzo/lib/liblzo2.dylib /path/to/arm-none-eabi/bin Z1.1.0a my_feature my_effect
```

It copies the SDK and the release's features and effects to a temporary folder, adds your folders (`component.json` =
feature, `effect.json` = effect; a folder named like one of ours replaces it) and builds with the release's options.

**The platform and your code only**, from the `sdk/` folder, with your components in `user_features/` and effects in
`user_effects/`:

```sh
python3 sdk/build_feature_image.py \
  --stock "/path/to/Valeton GP-50 V1.1.0.bin" \
  --toolchain-prefix /path/to/nds32-toolchain/prefix \
  --lzo-library /opt/homebrew/opt/lzo/lib/liblzo2.dylib \
  --clang /usr/bin/clang --arm-bin /path/to/arm-none-eabi/bin \
  --capture-player latest \
  --id my_build --mod 200 --version Z1.1.0a \
  --component-root user_features \
  --effect user_effects/my_effect
```

- `--clang`, `--arm-bin` and `--capture-player latest` are needed by every build.
- `--id`, `--mod`, `--version`: a fresh identity for this image. The version is what the pedal's version screen
  shows (`X1.1.0Y`: only the first and last characters are free). Reusing an identity with a different
  configuration is refused.
- `--effect` may be repeated; omit it for components only. `--component-root` may be repeated.
- `--boot-gif user_assets/boot.gif` (optional): your own boot animation (GIF89a, 144x28, at most 27,136 bytes and
  3.92 s), kept inside the package folder.

The builder compiles, checks imports and stack use, places code and data, adds your effects as the last entries of
their groups, composes the image from your stock file and writes `work/<id>/latest.json` and `sdk_build_result.json`
with the exact image hash and every input it used. The image is in the folder named there.

## 6. Checking and installing

- **Offline**: the build's own gates (fit, imports, stack, selector ownership, container checksums), plus your
  native tests.
- **On the pedal**: close everything that talks to the pedal, install the image with Valeton Suite's firmware
  update, wait until it finishes, then check the version screen and your feature. Test in a spare preset.
- **Going back**: install the official V1.1.0 file the same way. The bootloader is never modified.

## 7. Limits to know

- Only stock **V1.1.0** is supported as input.
- One Global settings tile per image (one free slot); per-preset storage up to 432 bytes shared.
- No libc, heap or blocking anywhere; arbitrary C can still crash the pedal, there is no sandbox.
- macOS is the only checked host.
- Valeton Suite's editor does not learn new effects; select them on the pedal or with the project's web editor.

## 8. Checklist

1. Copy a starter; give it a new name and a unique `public_id` (effect) or selector 0x76..0x7e (component).
2. Write the callbacks; keep to the rules above.
3. For an effect, run the native test.
4. Build with `sdk/build_feature_image.py` and a fresh identity.
5. Install with Valeton Suite; check on the pedal; keep the official V1.1.0 file for going back.
