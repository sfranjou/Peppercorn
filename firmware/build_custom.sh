#!/bin/bash
# Build Peppercorn plus your own features and effects from your own official GP-50 V1.1.0 file.
# Usage: firmware/build_custom.sh STOCK.bin NDS32_TOOLCHAIN_PREFIX LIBLZO2 ARM_BIN_DIR VERSION DIR...
#   VERSION: shown on the pedal, X1.1.0Y (only the first and last characters are free), e.g. Z1.1.0a
#   DIR: a feature (component.json) or an effect (effect.json); a name used in user_features/ or user_effects/ replaces ours
# Env: BOOT_GIF=/path/to/boot.gif (your own boot animation; the stock one by default), MOD (200-999, default 200)
set -euo pipefail
[ $# -ge 6 ] || { sed -n 2,6p "$0"; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"; WORK="$(mktemp -d)"; START="$PWD"
abs() { (cd "$(dirname "$1")" && echo "$PWD/$(basename "$1")"); }
STOCK="$(abs "$1")"; PREFIX="$(abs "$2")"; LZO="$(abs "$3")"; ARM="$(abs "$4")"; VERSION="$5"; shift 5
cp -R "$HERE/../sdk"/. "$WORK"/; cp -R "$HERE/user_features" "$HERE/user_effects" "$WORK"/
EXTRA=()
for d in "$@"; do
  n="$(basename "$d")"
  if [ -f "$d/component.json" ]; then rm -rf "$WORK/user_features/$n"; cp -R "$d" "$WORK/user_features/$n"
  elif [ -f "$d/effect.json" ]; then
    [ -d "$WORK/user_effects/$n" ] || EXTRA+=(--effect "user_effects/$n")
    rm -rf "$WORK/user_effects/$n"; cp -R "$d" "$WORK/user_effects/$n"
  else echo "$d: no component.json or effect.json" >&2; exit 2; fi
done
if [ -n "${BOOT_GIF:-}" ]; then mkdir -p "$WORK/user_assets"; cp "$BOOT_GIF" "$WORK/user_assets/boot.gif"; EXTRA+=(--boot-gif user_assets/boot.gif); fi
cd "$WORK"
python3 sdk/build_feature_image.py --stock "$STOCK" --toolchain-prefix "$PREFIX" --lzo-library "$LZO" --arm-bin "$ARM" \
  --clang "$(command -v clang)" --id my_build --component-root user_features --mod "${MOD:-200}" --version "$VERSION" \
  --admission-table v8 --capture-player latest --exclude-effect 0x0b0000f5 --exclude-effect 0x04000031 --exclude-effect 0x04000030 --exclude-effect 0x01000062 --exclude-effect 0x01000061 --exclude-effect 0x01000060 --exclude-effect 0x07000070 --exclude-effect 0x03000060 --exclude-effect 0x0300007d --exclude-effect 0x0300007e --exclude-effect 0x01000041 --exclude-effect 0x01000040 --exclude-effect 0x0b0000f4 --effect user_effects/auto_swell --effect user_effects/clouds_verb --effect user_effects/dst_capture --effect sdk/effects/pitch_splice --admission-estimate-override pitch_splice --effect sdk/effects/detune_splice --admission-estimate-override detune_splice ${EXTRA[@]+"${EXTRA[@]}"}
python3 - "$WORK" <<'PY'
import hashlib, json, pathlib, sys
w = pathlib.Path(sys.argv[1]); d = json.loads((w / 'work/my_build/latest.json').read_text())
image, = (p for p in (w / d['folder']).glob('*.bin') if hashlib.sha256(p.read_bytes()).hexdigest() == d['image_sha256'])
print('image:', image)
print('SHA-256:', d['image_sha256'])
PY
