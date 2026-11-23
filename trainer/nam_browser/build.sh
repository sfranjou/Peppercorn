#!/bin/sh
set -eu
TASK_ROOT=$(CDPATH= cd -- "$(dirname "$0")/../../.." && pwd)
export EM_CACHE="$TASK_ROOT/work/tone_capture/browser_teacher_069/em_cache"
TASK_BUILD="$TASK_ROOT/work/tone_capture/browser_teacher_069/build"
emcmake cmake -S "$TASK_ROOT/tools/tone_trainer/nam_browser" -B "$TASK_BUILD" -DNAM_CORE="$TASK_ROOT/work/tone_capture/browser_teacher_069/vendor/core" -DCMAKE_BUILD_TYPE=Release
cmake --build "$TASK_BUILD" -j 4
cp "$TASK_BUILD/teacher.js" "$TASK_ROOT/tools/tone_trainer/web/browser_teacher/teacher.js"
cp "$TASK_BUILD/teacher.wasm" "$TASK_ROOT/tools/tone_trainer/web/browser_teacher/teacher.wasm"
