/* Slap Echo 0.1.0 (PRE group 1): Long Echo's line/fallback/lease logic with a
 * 40-200 ms range. Needs 8,820 Q15 samples (17,640 B) from the managed tail; the
 * PRE slot keeps only a 2,048-sample fallback (46 ms clamp). With Long Echo
 * resident the pool cannot fit it, so it is DENIED (FULL) and falls back: the
 * on-device MEM page shows that as PRE!F. */
#define FALLBACK_N 2048u
#define TAIL_N 8820u
#define TIME_MIN 40.0f
#define TIME_MAX 200.0f
#include "../long_echo/long_echo.c"
