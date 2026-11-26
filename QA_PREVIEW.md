# Peppercorn v0.2.0 build and technical notes

See the [release notes](RELEASE_NOTES.md#peppercorn-v020-on-screen-version-a110j) for the user-facing changes and hardware qualification status.

## Reproduce the reviewed firmware

Run [`firmware/build.sh`](README.md#build-your-own) using your official GP-50 V1.1.0 file and the same four arguments shown in the build instructions. The recipe restores the reviewed code placement and checks the output against the reviewed SHA-256:

`688cd45006f888762f86913302748e1965b056f6870a9a40ecfc0dd1d3337c2c`

The About screen shows A1.1.0j. For stock restoration, see the [recovery steps](https://sfranjou.com/gp50/#recovery).

## Enable advice API

Firmware identity bit 14 advertises read-only block enable advice. `Pedal.enableConstraints()` sends `12 7e`. The reply is `12 7e 01` followed by ten reason bytes, in NR, PRE, DST, AMP, CAB, EQ, MOD, DLY, RVB, N→S order. Advice describes the current chain. Read back the block state after attempting a write.

## Design TODO

Unify footswitch assignment on the pedal and in the web editor. Let a single press toggle block enable and parameters together on the same footswitch. Decide how paired states and LEDs are shown, what happens when the pedal refuses to enable a block, and how existing presets keep their assignments.
