; KeyLogix — key_classify (x86 32-bit cdecl)
; int32_t key_classify(uint32_t vk_code)

BITS 32

section .text

global key_classify
global _key_classify

key_classify:
_key_classify:
    push ebp
    mov ebp, esp

    mov ecx, [ebp + 8]      ; vk_code

    cmp ecx, 255
    ja .cat_unknown

    ; Modifiers (2): 0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0..0xA5
    cmp ecx, 0x10
    je .cat_modifier
    cmp ecx, 0x11
    je .cat_modifier
    cmp ecx, 0x12
    je .cat_modifier
    cmp ecx, 0x5B
    je .cat_modifier
    cmp ecx, 0x5C
    je .cat_modifier
    cmp ecx, 0xA0
    jb .check_lock
    cmp ecx, 0xA5
    jbe .cat_modifier

.check_lock:
    ; Lock (6): 0x14, 0x90, 0x91
    cmp ecx, 0x14
    je .cat_lock
    cmp ecx, 0x90
    je .cat_lock
    cmp ecx, 0x91
    je .cat_lock

.check_nav:
    ; Navigation (3): 0x21..0x28
    cmp ecx, 0x21
    jb .check_ctrl
    cmp ecx, 0x28
    jbe .cat_navigation

.check_ctrl:
    ; Control (4): 0x08, 0x09, 0x0D, 0x1B, 0x2C, 0x2D, 0x2E, 0x13, 0x5D, 0x03, 0x0C
    cmp ecx, 0x08
    je .cat_control
    cmp ecx, 0x09
    je .cat_control
    cmp ecx, 0x0D
    je .cat_control
    cmp ecx, 0x1B
    je .cat_control
    cmp ecx, 0x2C
    je .cat_control
    cmp ecx, 0x2D
    je .cat_control
    cmp ecx, 0x2E
    je .cat_control
    cmp ecx, 0x13
    je .cat_control
    cmp ecx, 0x5D
    je .cat_control
    cmp ecx, 0x03
    je .cat_control
    cmp ecx, 0x0C
    je .cat_control

.check_func:
    ; Function (5): 0x70..0x87 (F1..F24)
    cmp ecx, 0x70
    jb .check_numpad
    cmp ecx, 0x87
    jbe .cat_function

.check_numpad:
    ; Numpad (7): 0x60..0x6F
    cmp ecx, 0x60
    jb .check_ordinary
    cmp ecx, 0x6F
    jbe .cat_numpad

.check_ordinary:
    ; Ordinary (1): 0x20 (Space), 0x30..0x39 (0-9), 0x41..0x5A (A-Z)
    cmp ecx, 0x20
    je .cat_ordinary
    cmp ecx, 0x30
    jb .check_oem
    cmp ecx, 0x39
    jbe .cat_ordinary
    cmp ecx, 0x41
    jb .check_oem
    cmp ecx, 0x5A
    jbe .cat_ordinary

.check_oem:
    ; OEM (8): 0xBA..0xC0, 0xDB..0xDF, 0xE2
    cmp ecx, 0xBA
    jb .check_oem_special
    cmp ecx, 0xC0
    jbe .cat_oem
    cmp ecx, 0xDB
    jb .check_oem_special
    cmp ecx, 0xDF
    jbe .cat_oem

.check_oem_special:
    cmp ecx, 0xE2
    je .cat_oem

.cat_unknown:
    xor eax, eax            ; KLX_CAT_UNKNOWN (0)
    jmp .done

.cat_ordinary:
    mov eax, 1              ; KLX_CAT_ORDINARY
    jmp .done

.cat_modifier:
    mov eax, 2              ; KLX_CAT_MODIFIER
    jmp .done

.cat_navigation:
    mov eax, 3              ; KLX_CAT_NAVIGATION
    jmp .done

.cat_control:
    mov eax, 4              ; KLX_CAT_CONTROL
    jmp .done

.cat_function:
    mov eax, 5              ; KLX_CAT_FUNCTION
    jmp .done

.cat_lock:
    mov eax, 6              ; KLX_CAT_LOCK
    jmp .done

.cat_numpad:
    mov eax, 7              ; KLX_CAT_NUMPAD
    jmp .done

.cat_oem:
    mov eax, 8              ; KLX_CAT_OEM

.done:
    pop ebp
    ret
