#include "keylogix_abi.h"

int32_t evt_buffer_init(void *dest, uint32_t capacity) {
    if (!dest) {
        return KLX_ERR_NULL;
    }
    if (capacity == 0 || capacity > KLX_MAX_CAPACITY) {
        return KLX_ERR_INVALID;
    }
    EvtBufferHeader *hdr = (EvtBufferHeader *)dest;
    hdr->magic = KLX_BUF_MAGIC;
    hdr->capacity = capacity;
    hdr->count = 0;
    hdr->rec_size = (uint32_t)sizeof(EvtRawPacked);
    return KLX_OK;
}

int32_t key_classify(uint32_t vk_code) {
    if (vk_code > 255) {
        return KLX_CAT_UNKNOWN;
    }
    /* Modifiers */
    if (vk_code == 0x10 || vk_code == 0x11 || vk_code == 0x12 ||
        vk_code == 0x5B || vk_code == 0x5C ||
        vk_code == 0xA0 || vk_code == 0xA1 || vk_code == 0xA2 ||
        vk_code == 0xA3 || vk_code == 0xA4 || vk_code == 0xA5) {
        return KLX_CAT_MODIFIER;
    }
    /* Locks */
    if (vk_code == 0x14 || vk_code == 0x90 || vk_code == 0x91) {
        return KLX_CAT_LOCK;
    }
    /* Navigation */
    if (vk_code >= 0x21 && vk_code <= 0x28) {
        return KLX_CAT_NAVIGATION;
    }
    /* Control */
    if (vk_code == 0x08 || vk_code == 0x09 || vk_code == 0x0D ||
        vk_code == 0x1B || vk_code == 0x2C || vk_code == 0x2D ||
        vk_code == 0x2E || vk_code == 0x13 || vk_code == 0x5D ||
        vk_code == 0x03 || vk_code == 0x0C) {
        return KLX_CAT_CONTROL;
    }
    /* Function keys F1-F24 */
    if (vk_code >= 0x70 && vk_code <= 0x87) {
        return KLX_CAT_FUNCTION;
    }
    /* Numpad */
    if (vk_code >= 0x60 && vk_code <= 0x6F) {
        return KLX_CAT_NUMPAD;
    }
    /* Ordinary keys */
    if (vk_code == 0x20 || (vk_code >= 0x30 && vk_code <= 0x39) ||
        (vk_code >= 0x41 && vk_code <= 0x5A)) {
        return KLX_CAT_ORDINARY;
    }
    /* OEM keys */
    if ((vk_code >= 0xBA && vk_code <= 0xC0) ||
        (vk_code >= 0xDB && vk_code <= 0xDF) ||
        vk_code == 0xE2) {
        return KLX_CAT_OEM;
    }
    return KLX_CAT_UNKNOWN;
}

int32_t modifier_state(uint32_t prior_state, uint32_t vk_code, uint32_t is_key_up) {
    uint32_t state = prior_state & 0x0F;
    uint32_t bit = 0;

    if (vk_code == 0x10 || vk_code == 0xA0 || vk_code == 0xA1) {
        bit = KLX_MOD_SHIFT;
    } else if (vk_code == 0x11 || vk_code == 0xA2 || vk_code == 0xA3) {
        bit = KLX_MOD_CTRL;
    } else if (vk_code == 0x12 || vk_code == 0xA4 || vk_code == 0xA5) {
        bit = KLX_MOD_ALT;
    } else if (vk_code == 0x5B || vk_code == 0x5C) {
        bit = KLX_MOD_WIN;
    }

    if (bit != 0) {
        if (is_key_up == 0) {
            state |= bit;
        } else {
            state &= ~bit;
        }
    }
    return (int32_t)state;
}

int32_t evt_normalize(const EvtRawPacked *src, EvtNormPacked *dst) {
    if (!src || !dst) {
        return KLX_ERR_NULL;
    }
    dst->event_type = (src->flags & 0x80u) ? 1u : 0u;
    dst->key_code = src->vk_code;
    dst->modifier_bits = 0u;
    dst->tick_ms = src->tick_ms;
    dst->class_id = (src->vk_code <= 255u) ? (uint32_t)key_classify(src->vk_code) : 0u;
    return KLX_OK;
}

int32_t str_to_upper(char *s, uint32_t len) {
    if (!s) {
        return KLX_ERR_NULL;
    }
    if (len == 0) {
        return 0;
    }
    int32_t converted = 0;
    for (uint32_t i = 0; i < len; ++i) {
        if (s[i] == '\0') {
            break;
        }
        if (s[i] >= 'a' && s[i] <= 'z') {
            s[i] = (char)(s[i] - ('a' - 'A'));
            converted++;
        }
    }
    return converted;
}

int32_t pattern_scan(const uint8_t *haystack, uint32_t hay_len, const uint8_t *needle, uint32_t needle_len) {
    if (!needle || needle_len == 0) {
        return KLX_ERR_INVALID;
    }
    if (hay_len > 0 && !haystack) {
        return KLX_ERR_INVALID;
    }
    if (needle_len > hay_len) {
        return KLX_NOT_FOUND;
    }
    for (uint32_t i = 0; i <= hay_len - needle_len; ++i) {
        uint32_t match = 1;
        for (uint32_t j = 0; j < needle_len; ++j) {
            if (haystack[i + j] != needle[j]) {
                match = 0;
                break;
            }
        }
        if (match) {
            return (int32_t)i;
        }
    }
    return KLX_NOT_FOUND;
}
