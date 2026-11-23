# Audio effects in C (ARM audio processor)

Write a mono effect in C, test its behavior on your computer, then build its ARM
record, catalog descriptor and a complete firmware image from your own GP-50 V1.1.0 file. Starter: Chop Trem
(`sdk/effects/chop_trem`). To build an effect into Peppercorn, use
`firmware/build_custom.sh` (see the package README); steps 3 to 6 below make a stock firmware with only your effect.
Give your effect an unused `public_id`: the starter keeps Chop Trem's.

Run the commands below from this package's root. Tools and the original firmware
are supplied separately; the package contains no firmware image or tool binaries.
The commands have been checked on macOS with Python 3.11+, Apple Clang, ARM GNU
14.2.rel1 binutils and liblzo2 2.10. Other host/tool combinations are unqualified.

1. Copy the starter to a folder of your own:

   ```sh
   cp -R sdk/effects/chop_trem /path/to/my_effect
   ```

   Edit `chop_trem.c` and the display name in `effect.json`. Keep the entry-point
   names consistent with the metadata. The header `sdk/include/gp50_effect.h`
   documents the audio callback ABI: stereo float buffers, normally 64 frames at
   44.1 kHz; the chain is mono in practice. Respect bypass, honor the frame count,
   use no heap or external library calls, and keep code/state within the effect's
   slot. The builder checks the record layout, link addresses and undefined symbols.

2. Run the example behavior check against your copied C implementation:

   ```sh
   clang -std=c11 -Wall -Wextra -Werror -fsanitize=undefined \
     -I sdk/include -I /path/to/my_effect sdk/tests/test_chop_trem.c \
     -o /path/to/chop_check
   /path/to/chop_check
   ```

   The supplied test checks the original tremolo's unity, mono output, bypass/state
   continuity, gain bounds and mute. Adapt these checks when changing the algorithm.
   A native pass checks the C algorithm, rather than timing or hardware integration.

3. Prepare build inputs from your unmodified V1.1.0 update file:

   ```sh
   python3 sdk/prepare_stock.py --stock /path/to/original-V1.1.0.bin \
     --out /path/to/stock-inputs --lzo-library /path/to/liblzo2 --with-catalog
   ```

   Use a fresh output directory. The helper checks the exact supported stock hash
   and all region checksums, then writes `decoded_g.bin`, `decoded_e.bin` and `stock_inputs.json`.
   The original image remains unchanged.

4. Compile your effect with explicit tool and stock paths:

   ```sh
   python3 sdk/build_effect.py /path/to/my_effect --out /path/to/effect-build \
     --stock-g /path/to/stock-inputs/decoded_g.bin \
     --clang /path/to/clang --arm-bin /path/to/arm-none-eabi/bin
   ```

   The build folder contains the record, descriptor, ARM payload, ELF/disassembly
   and a manifest identifying the author inputs and decoded stock input. Step 6 integrates
   these artifacts into a stock-based image. No command here communicates with a device.

5. Optionally create a catalog extension for host tools or the combined feature SDK:

   ```sh
   python3 scripts/build_catalog_ext.py \
     --stock-e /path/to/stock-inputs/decoded_e.bin \
     --from-e /path/to/stock-inputs/decoded_e.bin \
     --add-effect /path/to/effect-build \
     --ext /path/to/catalog.json --header /path/to/catalog.h
   python3 scripts/build_catalog_ext.py \
     --stock-e /path/to/stock-inputs/decoded_e.bin \
     --ext /path/to/catalog.json --header /path/to/catalog.h --check
   ```

   Start with fresh catalog/header output paths. To append another effect to this
   extension, omit `--from-e` and use the same `--ext` / `--header` paths with its
   build folder. Keep each effect's metadata public ID unique within its group;
   duplicate IDs refuse before writing. Existing stock entries are retained.
   The header is an input for firmware integration. For host tools, the same
   command with `--logical /path/to/logical_e.bin` writes a logical catalog image;
   this is a catalog artifact, rather than a firmware update file.

6. Build a complete image from the original stock firmware and your compiled effect:

   ```sh
   python3 scripts/build_add_effect.py \
     --base /path/to/original-V1.1.0.bin \
     --effect /path/to/effect-build --source-dir /path/to/my_effect \
     --lzo-library /path/to/liblzo2 \
     --out /path/to/fresh-image-build --name My_Effect.bin
   python3 scripts/build_add_effect.py --verify /path/to/fresh-image-build
   ```

   The builder places the record and descriptor automatically. It checks the
   compiled source hashes, effect/overlay limits, catalog space, retained records
   and descriptors, container fields and all decoded region checksums. The verify
   command rebuilds from the manifest's original inputs and compares the image.
   Keep those input folders available for that command. Output folders must be fresh.

   This ordinary-effect path uses the stock catalog; step 5's separate extension
   is optional here. The resulting file contains original firmware combined with
   your effect. Its manifest records the exact image hash and original inputs.
   The version shown on the pedal remains the stock version in this starter
   workflow. Identify the build by its filename and manifest hash. Suite's editor
   list does not learn new effects automatically; select them on the pedal.

   These commands only write local files; install the image with Valeton Suite
   (`sdk/INSTALL_AND_RECOVER.md`).

`package_manifest.json` records the package's file hashes. Not covered by this starter: managed tail memory and
coprocessor programs. Supported surface: `sdk/SUPPORTED_SURFACE.md`; installing and recovery:
`sdk/INSTALL_AND_RECOVER.md`.
