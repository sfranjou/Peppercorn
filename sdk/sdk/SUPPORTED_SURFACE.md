# Supported surface (v0.1.0)

| Interface | Status | Reference |
| --- | --- | --- |
| Feature components, ABI 3 (`sdk/nds/components/gp50.h`): events, blocks, parameters, presets, per-preset storage, host GET/SET/notify, screen services, editor strip, Global settings tile, load readings | Supported. Our features use it and were tested on the pedal (A1.1.0i). | `sdk/DEVELOPER_GUIDE.md` |
| Host-only components, ABI 1 (`component.h`) | Supported (example `sdk/nds/components/user_examples/answer`, selector `0x77`) | `sdk/DEVELOPER_GUIDE.md` |
| Audio effects on the ARM audio processor | Supported for the documented effect ABI (44.1 kHz, 64-frame blocks); new algorithms need their CPU cost and sound checked on a pedal | `sdk/ARM_QUICKSTART.md` |
| Coprocessor effects | Not part of the supported surface | — |

Limits and rules:

- Input: official GP-50 V1.1.0 only.
- Host selectors: features own `0x76`–`0x7e` (one each, from the manifest); `0x71`, `0x74`, `0x75` may be taken
  over by one feature each. Duplicates are refused.
- Code, RAM and stack are placed and checked by the build; an image that does not fit is refused, never truncated.
- No libc, heap or blocking calls; no sandbox: wrong C can crash the pedal (recovery: `sdk/INSTALL_AND_RECOVER.md`).
- Checked host: macOS. Other hosts are likely to work but are not checked.
- The release adds three effects: Auto Swell, Cloud Verb and DST Capture. The other effects in `sdk/effects/` and
  `../firmware/extra_effects/` are examples.
