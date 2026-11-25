# Firmware QA preview: A1.1.0j

- Auto Swell detects quieter picks and can restart after a rest or a distinct pick over a decaying note. Bypass clears detector state.
- Stomp A/B LEDs follow the current parameter value at saved endpoints.
- Exit commits a complete knob assignment and leaves the editor in one press. Save the preset as usual to keep the assignment across reloads.
- The web editor shows current knob and A/B assignments, displays block enable constraints, and reads the block state back after a write.

Build from your own official GP-50 V1.1.0 file using `firmware/build.sh` with the same four arguments as in the [build instructions](README.md).
The reviewed candidate displays A1.1.0j and has SHA-256 `688cd45006f888762f86913302748e1965b056f6870a9a40ecfc0dd1d3337c2c`.
Physical LED colors and refresh timing, assignment reload, and Auto Swell under pedal load still need pedal checks. The browser installer still offers A1.1.0i.

Firmware identity bit 14 advertises read-only block enable advice. `Pedal.enableConstraints()` sends `12 7e`. The reply is `12 7e 01` followed by ten reason bytes, in NR, PRE, DST, AMP, CAB, EQ, MOD, DLY, RVB, N→S order. Advice describes the current chain. Read back the block state after attempting a write.

## Design TODO

Unify footswitch assignment on the pedal and in the web editor. Let a single press toggle block enable and parameters together on the same footswitch. Decide how paired states and LEDs are shown, what happens when the pedal refuses to enable a block, and how existing presets keep their assignments.
