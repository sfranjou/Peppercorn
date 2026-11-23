# Long Echo 0.1.0 (SDK example, DLY group 7)

Mono feedback delay using a resident-granted managed-tail lease (1.8 s, Q15,
158,760 B) with an in-slot fallback line (16,384 samples ≈ 0.37 s) when no
resident adapter/grant exists. Parameters: Mix, Time (20–1800 ms), Feedback
(0–95 %), Tone, VOL. Bypass (`*enable==0`) returns untouched, as stock overlays.
Cost: 64 × (1 write + 2 reads) = 192 tail halfword accesses per block.

Build: `python3 sdk/build_effect.py sdk/effects/long_echo --out work/long_echo/build`.
