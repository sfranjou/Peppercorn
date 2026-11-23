/* stock_in_place (patching release): preset storage runs as stock code, except what the A/B footswitches change.
 * Stored-preset read, migration and apply are stock (the stored-slot read call at 0x43fbc is re-pointed to
 * gp50_fs_ab_preset_read by host_layer_c). Ours: the factory-load wrapper (clears the A/B foot state when the current
 * preset is replaced; stock load through preset_stock_442f2, a prologue-replay tail) and the save chain
 * preset_save -> flash_store_request -> flash_stage_sector, which propagates a refused stage instead of queueing a
 * write anyway (stock queued it after a failed read/allocation and published the buffer before staging). */
#include <stdint.h>

#define SAVE_SLOT_MAP (0x20011658u - 0x1010u + 0x24fu)   /* byte per preset slot: flash record index */
#define FLASH_STORE_OBJECT (0x20011658u - 0xcaccu)     /* word: flash-store object (+4 buffer, +8 sector, +0xc request) */
#define CURRENT_PRESET (0x20011658u - 0xfa3u)          /* u16, unaligned */
#define FLASH_ALLOC 0x5cfb0u
#define FLASH_RELEASE 0x5cfd8u
#define FLASH_READ 0x10f9eu
#define FLASH_BUSY 0x49a6cu
#define PAUSE 0x5cb88u
#define STAGE_SECTOR 0x4965au    /* stock entry, redirected to nds_host_4965a below */
#define STORE_REQUEST 0x49772u   /* stock entry, redirected to nds_host_49772 below */

typedef uint32_t (*fn1)(uint32_t);
typedef uint32_t (*fn3)(uint32_t, uint32_t, uint32_t);
typedef uint32_t (*fn4)(uint32_t, uint32_t, uint32_t, uint32_t);
static uint8_t byte_at(uint32_t a) { return *(volatile uint8_t *)(uintptr_t)a; }
static void byte_put(uint32_t a, uint8_t v) { *(volatile uint8_t *)(uintptr_t)a = v; }
static uint32_t word_at(uint32_t a) { return byte_at(a) | byte_at(a + 1) << 8 | byte_at(a + 2) << 16 | (uint32_t)byte_at(a + 3) << 24; }
static void word_put(uint32_t a, uint32_t v) { for (int i = 0; i < 4; i++) byte_put(a + i, (uint8_t)(v >> 8 * i)); }

void gp50_fs_ab_active_replaced(void);
uint32_t gp50_fs_ab_stage_record(uint32_t destination, uint32_t source, uint32_t length, const void *io);
uint32_t preset_stock_442f2(uint32_t slot, uint32_t rec);

/* Factory presets start the N->S capture at the first user slot. Stock factory load (0x442f2: factory table 0x49750 for presets
 * 0..54, the default record otherwise, DEFAULT_MODELS[9] = 0x0f000000) gives N->S factory capture 0. Where the N->S
 * block (9) is off (enable word +0x18 bit 9) and holds capture 0, it becomes user slot 50 (0x0f000032); an N->S block
 * that is on keeps its capture. Record layout: firmware/reconstructed/nds/preset_record.h. When the record is the
 * current preset, stock has already copied it to the live block (+0x65) and rebuilt the ordinal cache (+0x2b6) from
 * the model IDs (preset_record.c preset_load_factory): the same two updates are made for block 9. */
#define NTOS_BLOCK 9u
#define NTOS_FIRST_FACTORY 0x0f000000u
#define NTOS_FIRST_USER 0x0f000032u
#define PRESET_ACTIVE (0x20011658u - 0x1010u)
#define ID_TO_ORDINAL 0x439dcu
typedef uint32_t (*fn2)(uint32_t, uint32_t);
static uint32_t ntos_default_user_slot(uint32_t rec) {
    if (word_at(rec + 0x18) >> NTOS_BLOCK & 1u) return 0;
    if (word_at(rec + 0x26 + 4u * NTOS_BLOCK) != NTOS_FIRST_FACTORY) return 0;
    word_put(rec + 0x26 + 4u * NTOS_BLOCK, NTOS_FIRST_USER);
    return 1;
}

uint32_t nds_host_442f2(uint32_t slot, uint32_t rec) {
    uint32_t r = preset_stock_442f2(slot, rec);
    if (ntos_default_user_slot(rec) &&
        (byte_at(CURRENT_PRESET) | (uint32_t)byte_at(CURRENT_PRESET + 1) << 8) == slot) {
        word_put(PRESET_ACTIVE + 0x65 + 0x26 + 4u * NTOS_BLOCK, NTOS_FIRST_USER);
        byte_put(PRESET_ACTIVE + 0x2b6 + NTOS_BLOCK, (uint8_t)((fn2)(uintptr_t)ID_TO_ORDINAL)(NTOS_BLOCK, NTOS_FIRST_USER));
    }
    if ((byte_at(CURRENT_PRESET) | (uint32_t)byte_at(CURRENT_PRESET + 1) << 8) == slot) gp50_fs_ab_active_replaced();
    return r;
}

/* 1 = staged and published to the flash-store object; 0 = refused, object unchanged. */
uint32_t nds_host_4965a(uint32_t rec, uint32_t index, uint32_t n) {
    uint32_t obj = word_at(FLASH_STORE_OBJECT);
    if (byte_at(obj + 0xc)) return 0;                     /* earlier write still pending: keep its buffer */
    uint32_t buf = ((fn1)(uintptr_t)FLASH_ALLOC)(0x1000);
    if (!buf) return 0;
    for (uint32_t i = 0; i < 0x1000; i++) byte_put(buf + i, 0);
    uint32_t sector = ((index + 0x5dc) << 10) & ~0xfffu;
    if (((fn4)(uintptr_t)FLASH_READ)(sector, buf, 0x1000, 10) || !gp50_fs_ab_stage_record(buf + ((index & 3) << 10), rec, n, 0)) {
        ((fn1)(uintptr_t)FLASH_RELEASE)(buf);
        return 0;
    }
    word_put(obj + 4, buf); word_put(obj + 8, sector);
    return 1;
}

/* 0 = queued; 0xffffff01 index out of range (as stock); 0xffffff02 refused (nothing queued). */
uint32_t nds_host_49772(uint32_t rec, uint32_t index, uint32_t n) {
    if (index >= 100) return 0xffffff01u;
    if (!((fn3)(uintptr_t)STAGE_SECTOR)(rec, index, n)) return 0xffffff02u;
    byte_put(word_at(FLASH_STORE_OBJECT) + 0xc, 1);
    return 0;
}

/* Waits only for a queued write and returns the request result (stock: always 0). */
uint32_t nds_host_4468a(uint32_t slot, uint32_t rec) {
    uint32_t r = ((fn3)(uintptr_t)STORE_REQUEST)(rec, byte_at(SAVE_SLOT_MAP + slot), 0x1aa);
    if (r) return r;
    do ((fn1)(uintptr_t)PAUSE)(10); while (((uint32_t (*)(void))(uintptr_t)FLASH_BUSY)());
    return 0;
}
