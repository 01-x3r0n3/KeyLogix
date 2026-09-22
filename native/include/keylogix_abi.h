#ifndef KEYLOGIX_ABI_H
#define KEYLOGIX_ABI_H

#include <stdint.h>
#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define KLX_BUF_MAGIC 0x314C4B58u  /* 'XKL1' in little-endian */

/* Error codes */
#define KLX_OK                 0
#define KLX_ERR_NULL          -1
#define KLX_ERR_INVALID       -2
#define KLX_ERR_NOSPACE       -3
#define KLX_ERR_OVERFLOW      -4
#define KLX_ERR_MAGIC         -5
#define KLX_NOT_FOUND         -1   /* For pattern_scan when input is valid but pattern not found */

#define KLX_MAX_CAPACITY 1000000u

/* Category IDs */
#define KLX_CAT_UNKNOWN     0
#define KLX_CAT_ORDINARY    1
#define KLX_CAT_MODIFIER    2
#define KLX_CAT_NAVIGATION  3
#define KLX_CAT_CONTROL     4
#define KLX_CAT_FUNCTION    5
#define KLX_CAT_LOCK        6
#define KLX_CAT_NUMPAD      7
#define KLX_CAT_OEM         8

/* Modifier bits */
#define KLX_MOD_SHIFT 1
#define KLX_MOD_CTRL  2
#define KLX_MOD_ALT   4
#define KLX_MOD_WIN   8

#pragma pack(push, 1)

typedef struct {
    uint32_t magic;      /* KLX_BUF_MAGIC after init */
    uint32_t capacity;   /* caller-provided max records */
    uint32_t count;      /* set to 0 by init */
    uint32_t rec_size;   /* sizeof(EvtRawPacked) = 20 */
} EvtBufferHeader;       /* 16 bytes */

typedef struct {
    uint32_t vk_code;
    uint32_t scan_code;
    uint32_t flags;      /* LLKHF_* compatible; bit 7 = up */
    uint32_t extra;
    uint32_t tick_ms;
} EvtRawPacked;          /* 20 bytes */

typedef struct {
    uint32_t event_type;     /* 0 = KEY_DOWN, 1 = KEY_UP */
    uint32_t key_code;
    uint32_t modifier_bits;  /* 0; native normalize does not invent modifiers */
    uint32_t tick_ms;
    uint32_t class_id;       /* key_classify(vk_code) */
} EvtNormPacked;             /* 20 bytes */

#pragma pack(pop)

/* Function declarations */
int32_t evt_buffer_init(void *dest, uint32_t capacity);
int32_t evt_normalize(const EvtRawPacked *src, EvtNormPacked *dst);
int32_t key_classify(uint32_t vk_code);
int32_t modifier_state(uint32_t prior_state, uint32_t vk_code, uint32_t is_key_up);
int32_t str_to_upper(char *s, uint32_t len);
int32_t pattern_scan(const uint8_t *haystack, uint32_t hay_len, const uint8_t *needle, uint32_t needle_len);

#ifdef __cplusplus
}
#endif

#endif /* KEYLOGIX_ABI_H */
