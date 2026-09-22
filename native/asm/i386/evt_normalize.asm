; KeyLogix — evt_normalize (x86 32-bit cdecl)
; int32_t evt_normalize(const EvtRawPacked *src, EvtNormPacked *dst)

BITS 32

section .text

global evt_normalize
global _evt_normalize
extern key_classify
extern _key_classify

evt_normalize:
_evt_normalize:
    push ebp
    mov ebp, esp
    push ebx
    push esi
    push edi

    mov esi, [ebp + 8]      ; src
    test esi, esi
    jz .err_null

    mov edi, [ebp + 12]     ; dst
    test edi, edi
    jz .err_null

    ; event_type = (flags & 0x80) ? 1 : 0
    mov eax, [esi + 8]      ; flags
    and eax, 0x80
    test eax, eax
    setnz al
    movzx eax, al
    mov [edi], eax          ; dst->event_type

    ; key_code = src->vk_code
    mov ebx, [esi]          ; vk_code
    mov [edi + 4], ebx      ; dst->key_code

    ; modifier_bits = 0
    mov dword [edi + 8], 0  ; dst->modifier_bits

    ; tick_ms = src->tick_ms
    mov eax, [esi + 16]     ; tick_ms
    mov [edi + 12], eax     ; dst->tick_ms

    ; class_id = key_classify(vk_code) if vk_code <= 255 else 0
    cmp ebx, 255
    ja .zero_class

    push ebx
    call key_classify
    add esp, 4
    mov [edi + 16], eax     ; dst->class_id
    jmp .success

.zero_class:
    mov dword [edi + 16], 0 ; dst->class_id = 0

.success:
    xor eax, eax            ; KLX_OK (0)
    jmp .done

.err_null:
    mov eax, -1             ; KLX_ERR_NULL

.done:
    pop edi
    pop esi
    pop ebx
    pop ebp
    ret
