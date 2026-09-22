; KeyLogix — pattern_scan (x86 32-bit cdecl)
; int32_t pattern_scan(const uint8_t *haystack, uint32_t hay_len, const uint8_t *needle, uint32_t needle_len)

BITS 32

section .text

global pattern_scan
global _pattern_scan

pattern_scan:
_pattern_scan:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi

    mov edx, [ebp + 16]     ; needle
    test edx, edx
    jz .err_invalid

    mov ecx, [ebp + 20]     ; needle_len
    test ecx, ecx
    jz .err_invalid

    mov esi, [ebp + 8]      ; haystack
    mov eax, [ebp + 12]     ; hay_len

    test eax, eax
    jz .not_found_check_hay

    test esi, esi
    jz .err_invalid

.not_found_check_hay:
    cmp ecx, eax            ; needle_len > hay_len?
    ja .not_found

    ; Outer loop: i = 0 to (hay_len - needle_len)
    mov ebx, eax
    sub ebx, ecx            ; max_i = hay_len - needle_len
    xor eax, eax            ; i = 0

.outer_loop:
    cmp eax, ebx
    ja .not_found

    ; Inner loop: compare haystack[i..i+needle_len-1] with needle[0..needle_len-1]
    xor edi, edi            ; j = 0

.inner_loop:
    cmp edi, ecx
    jae .match_found

    ; Compare haystack[i + j] and needle[j]
    push eax
    add eax, edi
    mov dl, [esi + eax]     ; haystack[i + j]
    pop eax

    mov edx, [ebp + 16]     ; needle base
    mov dl, [edx + edi]     ; needle[j]

    push eax
    add eax, edi
    mov al, [esi + eax]     ; reload haystack byte
    cmp al, dl
    pop eax
    jne .mismatch

    inc edi
    jmp .inner_loop

.mismatch:
    inc eax                 ; i++
    jmp .outer_loop

.match_found:
    ; Match at index i (already in eax)
    jmp .done

.not_found:
    mov eax, -1             ; KLX_NOT_FOUND
    jmp .done

.err_invalid:
    mov eax, -2             ; KLX_ERR_INVALID

.done:
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret
