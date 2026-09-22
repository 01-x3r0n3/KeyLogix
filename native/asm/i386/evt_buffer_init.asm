; KeyLogix — evt_buffer_init (x86 32-bit cdecl)
; int32_t evt_buffer_init(void *dest, uint32_t capacity)

BITS 32

section .text

global evt_buffer_init
global _evt_buffer_init

evt_buffer_init:
_evt_buffer_init:
    push ebp
    mov ebp, esp

    mov edx, [ebp + 8]      ; dest pointer
    test edx, edx
    jz .err_null

    mov ecx, [ebp + 12]     ; capacity
    test ecx, ecx
    jz .err_invalid

    cmp ecx, 1000000
    ja .err_invalid

    ; Write header fields
    mov dword [edx], 0x314C4B58  ; magic 'XKL1'
    mov [edx + 4], ecx           ; capacity
    mov dword [edx + 8], 0       ; count = 0
    mov dword [edx + 12], 20     ; rec_size = sizeof(EvtRawPacked) = 20

    xor eax, eax                ; KLX_OK (0)
    jmp .done

.err_null:
    mov eax, -1                 ; KLX_ERR_NULL
    jmp .done

.err_invalid:
    mov eax, -2                 ; KLX_ERR_INVALID

.done:
    pop ebp
    ret
