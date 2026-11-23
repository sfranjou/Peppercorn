#include <string.h>
#include "gp50_native.h"

void gp50_test(void) {
    gp50_strip s;
    uint8_t r[4];
    /* Not GR Comp, or another block: no strip. */
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 0);
    gp50_native.block[GP50_PRE].model = 0x01000041u;
    GP50_CHECK(gp50_native_strip(GP50_DLY, &s) == 0);
    /* GR Comp in PRE: label, value, bar in tenths of a dB. */
    gp50_native.meter = (gp50_meter){GP50_METER_OK, GP50_PRE, 352};
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 1 && !strcmp(s.label, "Gain Reduction") && !strcmp(s.value, "3.5 dB") &&
               s.level == 35 && s.level_max == 200);
    gp50_native.meter.gain_reduction = 1234;
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 1 && !strcmp(s.value, "12.3 dB") && s.level == 123);
    gp50_native.meter.gain_reduction = 9000;                      /* clamps: 60.0 text, full bar */
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 1 && !strcmp(s.value, "60.0 dB") && s.level == 200);
    /* No usable reading: words, empty bar. */
    static const char *const words[] = {"", "--", "ERR", "OLD", "NONE", "OFF"};
    for (uint8_t st = GP50_METER_NO_DATA; st <= GP50_METER_BYPASSED; st++) {
        gp50_native.meter.status = st;
        GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 1 && !strcmp(s.value, words[st]) && s.level == 0);
    }
    /* Host read. */
    gp50_native.meter = (gp50_meter){GP50_METER_OK, GP50_PRE, 352};
    GP50_CHECK(gp50_native_host_get(r, sizeof r) == 4 && r[0] == 1 && r[1] == 0 && r[2] == 352 % 256 && r[3] == 352 / 256);
    /* Readings are requested only while shown (strip or host read). */
    uint32_t reads = gp50_native.meter_reads;
    gp50_native_ticks(10, 10);
    GP50_CHECK(gp50_native.meter_reads == reads);
}
