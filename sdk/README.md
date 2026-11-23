# Peppercorn SDK

Write your own Valeton GP-50 pedal features in C (main processor) and audio effects in C (audio processor), and
build them into a complete firmware image from your own official **GP-50 V1.1.0** file. The package contains no
Valeton firmware: everything the build needs from it is taken from your file and checked by SHA-256.

- Full guide: [sdk/DEVELOPER_GUIDE.md](sdk/DEVELOPER_GUIDE.md) (the `gp50.h` feature API, effects, building,
  installing, limits).
- What is supported: [sdk/SUPPORTED_SURFACE.md](sdk/SUPPORTED_SURFACE.md).
- Peppercorn's own features, as working examples: `sdk/nds/components/features/` (knob and footswitch assignment,
  DRUM button, EXP Auto Engage, CPU tile) and `../firmware/user_features/` (the exact release set, including the
  gain-reduction meters).

## Requirements

- Python 3.11+, a liblzo2 shared library (e.g. Homebrew `lzo`)
- Clang and Arm GNU binutils (needed by every build; [sdk/ARM_QUICKSTART.md](sdk/ARM_QUICKSTART.md))
- NDS32 GCC toolchain: [sdk/NDS_TOOLCHAIN.md](sdk/NDS_TOOLCHAIN.md)
- The official GP-50 V1.1.0 firmware file (SHA-256
  `0e14f2b0293be233db3da8dc3573bf9135dddc575992055570842433dadae836`)
- Checked on macOS

## Peppercorn plus your own code

From the repository root. Each folder you add is a feature (it has a `component.json`) or an effect (`effect.json`):

```sh
cp -R sdk/sdk/nds/components/user_examples/answer my_answer
firmware/build_custom.sh "/path/to/Valeton GP-50 V1.1.0.bin" /path/to/nds32-toolchain/prefix \
  /path/to/liblzo2.dylib /path/to/arm-none-eabi/bin Z1.1.0a my_answer
```

- Everything in the release is included; a feature of yours with the same folder name as one of ours replaces it.
- `Z1.1.0a` is the version shown on the pedal: `X1.1.0Y`, only the first and last characters are free.
- The script prints the image's path and SHA-256.

## A smaller image: the platform and your code only

From this folder, without Peppercorn's features (captures and the stock-effect fixes stay):

```sh
mkdir -p user_features
cp -R sdk/nds/components/features/cpu_load user_features/cpu_load
python3 sdk/nds/components/native/run_native.py user_features/cpu_load     # tests on the computer
python3 sdk/build_feature_image.py \
  --stock "/path/to/Valeton GP-50 V1.1.0.bin" \
  --toolchain-prefix /path/to/nds32-toolchain/prefix \
  --lzo-library /path/to/liblzo2.dylib \
  --clang /usr/bin/clang --arm-bin /path/to/arm-none-eabi/bin \
  --capture-player latest \
  --id my_build --mod 200 --version Z1.1.0a \
  --component-root user_features
```

- To make it your own: rename the folder, the `id` and the callbacks in `component.json` and the `.c` file (they start
  with `<id>_`), and pick a free host selector.
- Add effects with `--effect user_effects/<name>`.
- This build's effect list also contains the example effects in `sdk/effects/` that the release leaves out; leave them
  out with `--exclude-effect <public ID>` as `../firmware/build.sh` does.
- Optional `--boot-gif user_assets/boot.gif`: your boot animation (GIF89a, 144x28, at most 27,136 bytes and 3.92 s).

The build checks imports, stack use, selector ownership, code/RAM placement and container checksums, then writes
`work/<id>/latest.json` and `sdk_build_result.json` (image hash and every input used).

## Installing and going back

- Install the built image with Valeton Suite's firmware update; going back = the official V1.1.0 file the same way.
- Details, checks and the cold-recovery key combination: [sdk/INSTALL_AND_RECOVER.md](sdk/INSTALL_AND_RECOVER.md).
- Talking to your feature from a browser or Node: [sdk/FEATURE_HOST.md](sdk/FEATURE_HOST.md).

## License

MIT (`LICENSE`). Third-party notices: `web/THIRD_PARTY.md`, `sdk/FEATURE_THIRD_PARTY.md`.
