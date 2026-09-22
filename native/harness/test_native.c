#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "keylogix_abi.h"

static int g_pass = 0;
static int g_fail = 0;

#define TEST_ASSERT(expr, msg) do { \
    if (expr) { \
        g_pass++; \
    } else { \
        g_fail++; \
        fprintf(stderr, "[-] FAIL: %s (line %d)\n", msg, __LINE__); \
    } \
} while (0)

static void test_evt_buffer_init(void) {
    printf("[*] Testing evt_buffer_init...\n");
    EvtBufferHeader hdr;
    memset(&hdr, 0xCC, sizeof(hdr));

    TEST_ASSERT(evt_buffer_init(NULL, 100) == KLX_ERR_NULL, "NULL dest must return KLX_ERR_NULL");
    TEST_ASSERT(evt_buffer_init(&hdr, 0) == KLX_ERR_INVALID, "0 capacity must return KLX_ERR_INVALID");
    TEST_ASSERT(evt_buffer_init(&hdr, 1000001) == KLX_ERR_INVALID, ">1000000 capacity must return KLX_ERR_INVALID");

    int32_t rc = evt_buffer_init(&hdr, 500);
    TEST_ASSERT(rc == KLX_OK, "Valid init returns KLX_OK");
    TEST_ASSERT(hdr.magic == KLX_BUF_MAGIC, "Magic matches KLX_BUF_MAGIC");
    TEST_ASSERT(hdr.capacity == 500, "Capacity set to 500");
    TEST_ASSERT(hdr.count == 0, "Count initialized to 0");
    TEST_ASSERT(hdr.rec_size == 20, "rec_size set to 20");
}

static void test_key_classify(void) {
    printf("[*] Testing key_classify...\n");
    TEST_ASSERT(key_classify(0x41) == KLX_CAT_ORDINARY, "0x41 'A' is ordinary");
    TEST_ASSERT(key_classify(0x30) == KLX_CAT_ORDINARY, "0x30 '0' is ordinary");
    TEST_ASSERT(key_classify(0x20) == KLX_CAT_ORDINARY, "0x20 Space is ordinary");

    TEST_ASSERT(key_classify(0x10) == KLX_CAT_MODIFIER, "0x10 Shift is modifier");
    TEST_ASSERT(key_classify(0x11) == KLX_CAT_MODIFIER, "0x11 Ctrl is modifier");
    TEST_ASSERT(key_classify(0x12) == KLX_CAT_MODIFIER, "0x12 Alt is modifier");
    TEST_ASSERT(key_classify(0x5B) == KLX_CAT_MODIFIER, "0x5B LWin is modifier");
    TEST_ASSERT(key_classify(0xA0) == KLX_CAT_MODIFIER, "0xA0 LShift is modifier");
    TEST_ASSERT(key_classify(0xA5) == KLX_CAT_MODIFIER, "0xA5 RAlt is modifier");

    TEST_ASSERT(key_classify(0x21) == KLX_CAT_NAVIGATION, "0x21 PageUp is navigation");
    TEST_ASSERT(key_classify(0x25) == KLX_CAT_NAVIGATION, "0x25 Left is navigation");
    TEST_ASSERT(key_classify(0x28) == KLX_CAT_NAVIGATION, "0x28 Down is navigation");

    TEST_ASSERT(key_classify(0x08) == KLX_CAT_CONTROL, "0x08 Backspace is control");
    TEST_ASSERT(key_classify(0x0D) == KLX_CAT_CONTROL, "0x0D Return is control");
    TEST_ASSERT(key_classify(0x1B) == KLX_CAT_CONTROL, "0x1B Escape is control");
    TEST_ASSERT(key_classify(0x5D) == KLX_CAT_CONTROL, "0x5D Apps is control");

    TEST_ASSERT(key_classify(0x70) == KLX_CAT_FUNCTION, "0x70 F1 is function");
    TEST_ASSERT(key_classify(0x7B) == KLX_CAT_FUNCTION, "0x7B F12 is function");
    TEST_ASSERT(key_classify(0x87) == KLX_CAT_FUNCTION, "0x87 F24 is function");

    TEST_ASSERT(key_classify(0x14) == KLX_CAT_LOCK, "0x14 CapsLock is lock");
    TEST_ASSERT(key_classify(0x90) == KLX_CAT_LOCK, "0x90 NumLock is lock");

    TEST_ASSERT(key_classify(0x60) == KLX_CAT_NUMPAD, "0x60 NumPad0 is numpad");
    TEST_ASSERT(key_classify(0x69) == KLX_CAT_NUMPAD, "0x69 NumPad9 is numpad");

    TEST_ASSERT(key_classify(0xBA) == KLX_CAT_OEM, "0xBA Oem1 is oem");
    TEST_ASSERT(key_classify(0xE2) == KLX_CAT_OEM, "0xE2 Oem102 is oem");

    TEST_ASSERT(key_classify(0x00) == KLX_CAT_UNKNOWN, "0x00 is unknown");
    TEST_ASSERT(key_classify(0xFF) == KLX_CAT_UNKNOWN, "0xFF is unknown");
    TEST_ASSERT(key_classify(300) == KLX_CAT_UNKNOWN, ">255 is unknown");
}

static void test_modifier_state(void) {
    printf("[*] Testing modifier_state...\n");
    int32_t s = 0;

    s = modifier_state(s, 0x10, 0); // Shift down
    TEST_ASSERT(s == 1, "Shift down sets bit 1");

    s = modifier_state(s, 0x11, 0); // Ctrl down
    TEST_ASSERT(s == 3, "Ctrl down sets bit 2 (total 3)");

    s = modifier_state(s, 0x12, 0); // Alt down
    TEST_ASSERT(s == 7, "Alt down sets bit 4 (total 7)");

    s = modifier_state(s, 0x5B, 0); // Win down
    TEST_ASSERT(s == 15, "Win down sets bit 8 (total 15)");

    s = modifier_state(s, 0x41, 0); // 'A' down (non-modifier)
    TEST_ASSERT(s == 15, "Non-modifier VK leaves state unchanged");

    s = modifier_state(s, 0xA0, 1); // LShift up
    TEST_ASSERT(s == 14, "Shift up clears bit 1");

    s = modifier_state(s, 0x5C, 1); // RWin up
    TEST_ASSERT(s == 6, "Win up clears bit 8");

    s = modifier_state(0xF0, 0x10, 0); // High bits in prior_state
    TEST_ASSERT(s == 1, "Prior state masked to 4 bits");
}

static void test_evt_normalize(void) {
    printf("[*] Testing evt_normalize...\n");
    EvtRawPacked raw;
    EvtNormPacked norm;
    memset(&raw, 0, sizeof(raw));
    memset(&norm, 0xFF, sizeof(norm));

    TEST_ASSERT(evt_normalize(NULL, &norm) == KLX_ERR_NULL, "NULL src returns KLX_ERR_NULL");
    TEST_ASSERT(evt_normalize(&raw, NULL) == KLX_ERR_NULL, "NULL dst returns KLX_ERR_NULL");

    raw.vk_code = 0x41;
    raw.scan_code = 0x1E;
    raw.flags = 0; // key down
    raw.extra = 0;
    raw.tick_ms = 12345;

    int32_t rc = evt_normalize(&raw, &norm);
    TEST_ASSERT(rc == KLX_OK, "evt_normalize returns KLX_OK");
    TEST_ASSERT(norm.event_type == 0, "flags=0 -> event_type=0 (KEY_DOWN)");
    TEST_ASSERT(norm.key_code == 0x41, "key_code=0x41");
    TEST_ASSERT(norm.modifier_bits == 0, "modifier_bits=0");
    TEST_ASSERT(norm.tick_ms == 12345, "tick_ms preserved");
    TEST_ASSERT(norm.class_id == KLX_CAT_ORDINARY, "class_id is ORDINARY (1)");

    raw.flags = 0x80; // key up
    raw.vk_code = 0x10; // Shift
    evt_normalize(&raw, &norm);
    TEST_ASSERT(norm.event_type == 1, "flags=0x80 -> event_type=1 (KEY_UP)");
    TEST_ASSERT(norm.class_id == KLX_CAT_MODIFIER, "class_id is MODIFIER (2)");
}

static void test_str_to_upper(void) {
    printf("[*] Testing str_to_upper...\n");
    char buf[] = "hello, World! 123";

    TEST_ASSERT(str_to_upper(NULL, 10) == KLX_ERR_NULL, "NULL string returns KLX_ERR_NULL");
    TEST_ASSERT(str_to_upper(buf, 0) == 0, "0 len returns 0");

    int32_t count = str_to_upper(buf, (uint32_t)strlen(buf));
    TEST_ASSERT(count == 9, "Converted 9 lowercase letters");
    TEST_ASSERT(strcmp(buf, "HELLO, WORLD! 123") == 0, "String converted in place");

    char buf2[10] = "abc\0def";
    count = str_to_upper(buf2, 10);
    TEST_ASSERT(count == 3, "Stops at NUL byte");
    TEST_ASSERT(strcmp(buf2, "ABC") == 0, "First 3 letters uppercase");
}

static void test_pattern_scan(void) {
    printf("[*] Testing pattern_scan...\n");
    uint8_t haystack[] = {0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70};
    uint8_t needle1[] = {0x30, 0x40};
    uint8_t needle_start[] = {0x10, 0x20};
    uint8_t needle_end[] = {0x60, 0x70};
    uint8_t needle_none[] = {0x99, 0x88};

    TEST_ASSERT(pattern_scan(NULL, 7, needle1, 2) == KLX_ERR_INVALID, "NULL haystack with len>0 returns KLX_ERR_INVALID");
    TEST_ASSERT(pattern_scan(haystack, 7, NULL, 2) == KLX_ERR_INVALID, "NULL needle returns KLX_ERR_INVALID");
    TEST_ASSERT(pattern_scan(haystack, 7, needle1, 0) == KLX_ERR_INVALID, "0 needle_len returns KLX_ERR_INVALID");

    TEST_ASSERT(pattern_scan(haystack, 7, needle1, 10) == KLX_NOT_FOUND, "needle_len > hay_len returns KLX_NOT_FOUND");
    TEST_ASSERT(pattern_scan(haystack, 7, needle1, 2) == 2, "Found in middle at index 2");
    TEST_ASSERT(pattern_scan(haystack, 7, needle_start, 2) == 0, "Found at start (index 0)");
    TEST_ASSERT(pattern_scan(haystack, 7, needle_end, 2) == 5, "Found at end (index 5)");
    TEST_ASSERT(pattern_scan(haystack, 7, needle_none, 2) == KLX_NOT_FOUND, "Not found returns KLX_NOT_FOUND (-1)");
}

int main(void) {
    printf("========================================\n");
    printf(" KeyLogix Native ABI Test Suite\n");
    printf("========================================\n");

    test_evt_buffer_init();
    test_key_classify();
    test_modifier_state();
    test_evt_normalize();
    test_str_to_upper();
    test_pattern_scan();

    printf("========================================\n");
    printf(" Results: %d passed, %d failed\n", g_pass, g_fail);
    printf("========================================\n");

    return (g_fail == 0) ? 0 : 1;
}
