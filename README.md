# Peppercorn

Unofficial firmware mod and web tools for the Valeton GP-50.

Build the modified firmware in your browser using your copy of Valeton’s V1.1.0 file.

**[Install](https://sfranjou.com/gp50/installer/)** · [Editor](https://sfranjou.com/gp50/editor/) · [Trainer](https://sfranjou.com/gp50/trainer/) · [Captures](https://sfranjou.com/gp50/captures/) · [Uploader](https://sfranjou.com/gp50/uploader/) · [Release notes](RELEASE_NOTES.md)

<!-- PHOTO: assigned knobs on the home screen, or the gain-reduction meter -->

## Features

- LTTC captures (Lean Twin Trained Clippers): a higher-fidelity alternative to SnapTone for tone captures.
- Run LTTC capture and IR together, or two LTTC captures
- New parameter assignment menu: assign parameters to knobs on the home page or to footswtiches
- Expression pedal Auto Engage: turn effects when the expression pedal is in use
- Gain-reduction meters for gate and compressors
- New CPU panel in Global settings with CPU usage measurements
- New effects — Auto Swell and Cloud Verb
- An SDK to write your own features and effects

[Read the full release notes](RELEASE_NOTES.md)

## Install

1. Download the official GP-50 V1.1.0 firmware from Valeton's website.
2. Back up your presets.
3. Open the [installer](https://sfranjou.com/gp50/installer/), drop the V1.1.0 file on the page and download the result. The page checks your file first, and the finished firmware afterwards.
4. In Valeton Suite, start a firmware update and select the file you downloaded. Keep the pedal connected until the update finishes.
5. In Global settings → About, check that the Version screen shows A1.1.0i.

## Can this brick the pedal?

I won't say it's impossible, but it is unlikely: this doesn't touch the bootloader at all, and firmware loading is done via the official Valeton Suite loader.
Reverting back is just a matter of reloading the official V1.1.0 firmware via Valeton Suite.

If the pedal freezes / won't start, you can force reboot the pedal or load it in bootloader mode. See the [recovery steps](https://sfranjou.com/gp50/#recovery)

In the course of making this mod, I've done a number of foolish things to my GP50, but it's always been really easy to recover.
I've also gigged several times with earlier versions of this firmware without issue. However, use it at your own risk → [disclaimer](#disclaimer)

## What data is collected?

Although the firmware is built from a file you provide, it all happens locally, and LTTC captures are trained in browser. None of it leaves your browser. The only analytics I collect is a firmware download count.

## Build your own

The Peppercorn SDK builds a complete firmware image from your official GP-50 V1.1.0 file and your own C code. The release’s features and effects are included as source. The builder places the code and data and checks imports, stack use and memory limits.

- **Pedal features** run on the NDS32 main processor. Use C and a `component.json` manifest to react to knobs and footswitches, change effect parameters, save settings per preset, add screen controls, or exchange messages with a computer over USB. [Developer guide](sdk/sdk/DEVELOPER_GUIDE.md)
- **Audio effects** run on the ARM audio processor. Use C and an `effect.json` manifest to add an effect to NR, PRE, MOD, DLY or RVB, with up to eight parameters and access to the pedal’s tempo. [Audio effect quickstart](sdk/sdk/ARM_QUICKSTART.md)

You’ll need the official GP-50 V1.1.0 `.bin`, Python 3.11+, liblzo2, Clang, Arm GNU binutils and an NDS32 GCC toolchain. The build has been tested on macOS. [SDK setup](sdk/README.md) · [NDS32 toolchain](sdk/sdk/NDS_TOOLCHAIN.md)

From the repository root, copy the sample USB feature and build it into Peppercorn:

```sh
cp -R sdk/sdk/nds/components/user_examples/answer my_answer
firmware/build_custom.sh "/path/to/Valeton GP-50 V1.1.0.bin" \
  /path/to/nds32-toolchain/prefix /path/to/liblzo2.dylib \
  /path/to/arm-none-eabi/bin Z1.1.0a my_answer
```

Add more feature or effect folders at the end of the command. A folder with the same name as a bundled feature or effect replaces it in the build. The script prints the image path and SHA-256. `Z1.1.0a` is the version shown on the pedal.

To rebuild the **Peppercorn v0.2.0-rc.1** firmware preview (About: **A1.1.0j**), run `firmware/build.sh` with the same first four arguments. See the [release notes](RELEASE_NOTES.md#peppercorn-v020-rc1) and [build checksum](QA_PREVIEW.md#reproduce-the-reviewed-firmware). The browser installer offers **v0.1.0** (About: **A1.1.0i**).

## What's in this repository

- `firmware/`: this release's features + effects, build scripts
- `sdk/`: the SDK
- `site/`: web tools, JavaScript API (`site/gp50/`)
- `trainer/`: NAM player + data service sources

## Credits and license

- MIT. The installer is GPL-2.0 (miniLZO). See [Licensing](LICENSING.md).
- Captures trained from TONE3000 captures. See the source credits in [captures.json](site/captures/captures.json).
- Cloud Verb is a port of the Mutable Instruments Clouds reverb by Emilie Gillet. The trainer uses [Neural Amp Modeler](https://github.com/sdatkinson/NeuralAmpModelerCore) code. See the [site credits](site/THIRD_PARTY.md) and [SDK third-party notices](sdk/sdk/FEATURE_THIRD_PARTY.md).
- This repository contains no Valeton code or assets.

## Disclaimer

This project is independent and is not affiliated with, endorsed by, or supported by Valeton or its parent company.
The software is provided “as is”, without warranty of any kind. Installing modified firmware is at your own risk; it may
void your warranty and could make the pedal unusable. The authors are not liable for any damage or loss. Keep a copy of
the official V1.1.0 firmware so you can return to it. All product names and trademarks belong to their owners.
