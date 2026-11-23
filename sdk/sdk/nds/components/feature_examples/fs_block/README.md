# fs_block: computer-only example (not for pedal images)

Shows the ABI 3 callbacks (event, host get/set, status line, per-preset bytes) on the native test platform:

    python3 sdk/nds/components/native/run_native.py sdk/nds/components/feature_examples/fs_block

Do not build it into a pedal image. It switches a block directly while the pedal's home screen keeps showing the
footswitch's stock assignment, so the screen no longer matches what the footswitch does, and its status text
replaces the preset name in the effect editor. Pedal features should use the pedal's own mechanisms where one exists
and never change existing behaviour unannounced.
