#include <string.h>
#include "gp50_native.h"

void gp50_test(void) {
    gp50_strip s;
    gp50_native.block[GP50_NR].model = 0x1bu;       /* stock Gate */
    gp50_native.block[GP50_PRE].model = 0u;         /* stock COMP */
    GP50_CHECK(gp50_native_strip(GP50_DLY, &s) == 0);
    GP50_CHECK(gp50_native_strip(GP50_NR, &s) == 1 && !strcmp(s.label, "Gain Reduction") && s.level_max == 200);
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 1 && !strcmp(s.label, "Gain Reduction") && strlen(s.value) < sizeof s.value);
    gp50_native.block[GP50_PRE].model = 2u;         /* not a compressor with a meter */
    GP50_CHECK(gp50_native_strip(GP50_PRE, &s) == 0);
}
