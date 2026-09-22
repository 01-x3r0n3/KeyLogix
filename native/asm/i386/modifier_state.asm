; KeyLogix — modifier_state (x86 32-bit cdecl)
; int32_t modifier_state(uint32_t prior_state, uint32_t vk_code, uint32_t is_key_up)

BITS 32

section .text

global modifier_state
global _modifier_state

modifier_state:
_modifier_state:
    push ebp
    mov ebp, esp

    mov eax, [ebp + 8]      ; prior_state
    and eax, 0x0F           ; mask to 4 bits

    mov edx, [ebp + 12]     ; vk_code
    xor ecx, ecx            ; bit mask

    ; Shift (bit 1)
    cmp edx, 0x10
    je .set_shift
    cmp edx, 0xA0
    je .set_shift
    cmp edx, 0xA1
    je .set_shift

    ; Ctrl (bit 2)
    cmp edx, 0x11
    je .set_ctrl
    cmp edx, 0xA2
    je .set_ctrl
    cmp edx, 0xA3
    je .set_ctrl

    ; Alt (bit 4)
    cmp edx, 0x12
    je .set_alt
    cmp edx, 0xA4
    je .set_alt
    cmp edx, 0xA5
    je .set_alt

    ; Win (bit 8)
    cmp edx, 0x5B
    je .set_win
    cmp edx, 0x5C
    je .set_win

    ; Not a modifier VK
    jmp .done

.set_shift:
    mov ecx, 1
    jmp .apply_bit

.set_ctrl:
    mov ecx, 2
    jmp .apply_bit

.set_alt:
    mov ecx, 4
    jmp .apply_bit

.set_win:
    mov ecx, 8

.apply_bit:
    mov edx, [ebp + 16]     ; is_key_up
    test edx, edx
    jnz .clear_bit
    or eax, ecx             ; key down: set bit
    jmp .done

.clear_bit:
    not ecx
    and eax, ecx            ; key up: clear bit
    and eax, 0x0F

.done:
    pop ebp
    ret
