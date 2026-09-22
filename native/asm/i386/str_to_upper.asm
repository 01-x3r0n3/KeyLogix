; KeyLogix — str_to_upper (x86 32-bit cdecl)
; int32_t str_to_upper(char *s, uint32_t len)

BITS 32

section .text

global str_to_upper
global _str_to_upper

str_to_upper:
_str_to_upper:
    push ebp
    mov ebp, esp
    push ebx
    push esi

    mov esi, [ebp + 8]      ; s pointer
    test esi, esi
    jz .err_null

    mov ecx, [ebp + 12]     ; len
    test ecx, ecx
    jz .zero_len

    xor eax, eax            ; converted count = 0
    xor edx, edx            ; index = 0

.loop:
    cmp edx, ecx
    jae .done

    mov bl, [esi + edx]
    test bl, bl
    jz .done                ; stop at NUL terminator

    cmp bl, 'a'
    jb .next
    cmp bl, 'z'
    ja .next

    sub bl, 32              ; 'a' - 'A' = 32
    mov [esi + edx], bl
    inc eax

.next:
    inc edx
    jmp .loop

.zero_len:
    xor eax, eax
    jmp .done

.err_null:
    mov eax, -1             ; KLX_ERR_NULL

.done:
    pop esi
    pop ebx
    pop ebp
    ret
