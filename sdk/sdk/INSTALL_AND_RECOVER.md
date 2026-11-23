# Installing, checking and recovering

## Input

- Official GP-50 **V1.1.0** firmware file, 1,425,393 bytes, SHA-256
  `0e14f2b0293be233db3da8dc3573bf9135dddc575992055570842433dadae836`. Other versions are refused.
- A build writes the image hash and every input to `work/<id>/sdk_build_result.json`; keep it with your source.

## Install

1. Keep the official V1.1.0 file and a backup of your presets and captures. Reinstalling firmware does not restore
   user data.
2. Close every other program that talks to the pedal (editors, MIDI tools).
3. Valeton Suite → firmware update → your built image. Do not unplug or power off during the update.
4. Close Suite, then check the version screen, your feature and the sound. Test in a spare preset.

## Go back

- Install the official V1.1.0 file the same way. The bootloader is never modified.

## Cold recovery (pedal does not start normally)

Observed on the project's pedal; not a guarantee for every failure:

1. Power off. If the screen is frozen, hold **SAVE + EXIT + GLOBAL** for more than two seconds to force a shutdown
   (unsaved changes are lost).
2. Power on while holding **both footswitches + PARA**: the pedal starts in Update/Restore mode (USB product ID
   `0x018b` instead of `0x018a`).
3. Valeton Suite → install the official V1.1.0 file → wait for completion → check a normal start.

A damaged bootloader, a hardware fault or a power loss during an update can behave differently. No debug-probe
recovery is offered.
