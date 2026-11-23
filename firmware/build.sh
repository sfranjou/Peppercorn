#!/bin/bash
# Rebuild the firmware (v0.1.0, on-screen A1.1.0i) from your own official GP-50 V1.1.0 file.
# Usage: firmware/build.sh STOCK.bin NDS32_TOOLCHAIN_PREFIX LIBLZO2 ARM_BIN_DIR
# Needs: Python 3.11+, clang, the NDS32 toolchain (sdk/sdk/NDS_TOOLCHAIN.md), Arm GNU toolchain, liblzo2.
# Expected SHA-256 of the result: 33963b31a168a4e827fffc22f50d7deef1f2c01c582c24686b8681718a005d70
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"; WORK="$(mktemp -d)"
cp -R "$HERE/../sdk"/. "$WORK"/; cp -R "$HERE/user_features" "$HERE/user_effects" "$WORK"/
# The custom boot animation is an edit of the stock one: only the edits ship, the rest comes from your file.
python3 "$HERE/boot_gif.py" unpack --stock "$1" --lzo-library "$3" --packed "$HERE/boot_gif.packed.json" --out "$WORK/user_assets/boot_peppercorn.gif"
cd "$WORK"
python3 sdk/build_feature_image.py --stock "$1" --toolchain-prefix "$2" --lzo-library "$3" --arm-bin "$4" \
  --clang "$(command -v clang)" --id release_author --component-root user_features ${FORBID_PROJECT:+--forbid-project "$FORBID_PROJECT"} \
  --mod 174 --version A1.1.0i --admission-table v8 --boot-gif user_assets/boot_peppercorn.gif --capture-player latest --exclude-effect 0x0b0000f5 --exclude-effect 0x04000031 --exclude-effect 0x04000030 --exclude-effect 0x01000062 --exclude-effect 0x01000061 --exclude-effect 0x01000060 --exclude-effect 0x07000070 --exclude-effect 0x03000060 --exclude-effect 0x0300007d --exclude-effect 0x0300007e --exclude-effect 0x01000041 --exclude-effect 0x01000040 --exclude-effect 0x0b0000f4 --effect user_effects/auto_swell --effect user_effects/clouds_verb --effect user_effects/dst_capture --effect sdk/effects/pitch_splice --admission-estimate-override pitch_splice --effect sdk/effects/detune_splice --admission-estimate-override detune_splice
python3 - "$WORK" <<'PY'
import hashlib, json, pathlib, sys
w = pathlib.Path(sys.argv[1]); d = json.loads((w / 'work/release_author/latest.json').read_text())
image, = (p for p in (w / d['folder']).glob('*.bin') if hashlib.sha256(p.read_bytes()).hexdigest() == d['image_sha256'])
print('image:', image)
print('image SHA-256:', d['image_sha256'])
PY
echo "build folder: $WORK"
