# Building the current capture player

The isolated feature SDK can build the paired capture resident, ARM overlay and
exclusive DSP programs directly from the packaged SDK sources. This supports SnapTone
and LTTC captures, and 512-tap cabinet IRs alongside an LTTC capture. No earlier capture ELF, record or generated header is required.

Add these options to the normal `sdk/build_feature_image.py` command:

```text
--capture-player latest --arm-bin /path/to/arm-none-eabi/bin
```

The existing `--clang` selects the ARM C compiler. The NDS toolchain, stock image,
LZO library, component root, image ID and other normal SDK options still apply.
This is a platform extension, not an independently installable effect: the resident
and overlay are always linked and bound together by `sdk/build_capture.py`.

`--exclude-effect 0x0b0000f4` removes Long Echo from the SDK extension catalog and
its matching overlay record in each platform input. The option is repeatable and
accepts only IDs declared by the SDK extension catalog. Stock catalog effects
cannot be removed through this option. Exclusion occurs before adding user effects.

The SDK first derives its pinned historical platform inputs from the supplied
stock firmware. It then compiles the current resident and overlay, assembles both
DSP kernels and the resident hook stubs, and replaces the capture-owned regions
in a generated platform input. `sdk/capture_status/release_binding.json` pins the
supported prior resident region, reservations and exact hook bytes. A different
platform fails closed; porting to another platform requires a reviewed binding.
The generated platform inputs are composed with user features, effects and an
optional boot GIF through the normal SDK build. Packaged source inputs remain
unchanged. The build never connects to or updates the pedal.

Evidence under `work/author_inputs/<id>/` includes:

- `capture/build.json`: resident and overlay symbols, ELF hashes, section bounds,
  hook bytes, DSP frame checks, compiler dependencies and overlay headroom.
- `capture/`: the newly built ELFs, maps, disassemblies, generated cell header,
  resident sections, hooks and paired overlay record.
- `platform_selection.json`: original/generated platform hashes, affected regions
  and excluded effect IDs.

A successful build does not establish hardware timing or audio quality: check new builds on a pedal.
