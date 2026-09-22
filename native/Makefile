CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra -Werror -std=c11 -Iinclude
NASM ?= nasm
MINGW_CC ?= i686-w64-mingw32-gcc

BUILD_DIR = build
INCLUDE_DIR = include
C_SRC = c/keylogix_ref.c
HARNESS_SRC = harness/test_native.c
ASM_DIR = asm/i386
ASM_SRCS = $(wildcard $(ASM_DIR)/*.asm)
ASM_OBJS = $(patsubst $(ASM_DIR)/%.asm,$(BUILD_DIR)/%.obj,$(ASM_SRCS))

.PHONY: all lib test-ref asm-win32 observer-win32 test-win32-asm clean dirs

all: dirs lib test-ref asm-win32 observer-win32 test-win32-asm

dirs:
	mkdir -p $(BUILD_DIR)

lib: dirs $(C_SRC)
	$(CC) $(CFLAGS) -fPIC -shared $(C_SRC) -o $(BUILD_DIR)/libkeylogix_ref.so

test-ref: dirs $(C_SRC) $(HARNESS_SRC)
	$(CC) $(CFLAGS) -I$(INCLUDE_DIR) $(C_SRC) $(HARNESS_SRC) -o $(BUILD_DIR)/test_native
	$(BUILD_DIR)/test_native

asm-win32: dirs $(ASM_OBJS)

$(BUILD_DIR)/%.obj: $(ASM_DIR)/%.asm
	$(NASM) -f win32 $< -o $@

test-win32-asm: dirs asm-win32
	@if command -v $(MINGW_CC) >/dev/null 2>&1; then \
		echo "Linking Win32 test harness with NASM routines..."; \
		$(MINGW_CC) -O2 -Wall -Wextra -I$(INCLUDE_DIR) $(HARNESS_SRC) $(ASM_OBJS) -o $(BUILD_DIR)/test_native_win32.exe; \
		echo "Win32 native test harness linked: $(BUILD_DIR)/test_native_win32.exe"; \
	fi

observer-win32: dirs
	@if command -v $(MINGW_CC) >/dev/null 2>&1; then \
		echo "Cross-compiling Win32 observer..."; \
		$(MINGW_CC) -O2 -Wall -Wextra -I$(INCLUDE_DIR) win32/observer.c -o $(BUILD_DIR)/observer.exe -luser32 -lole32; \
		echo "Win32 observer built: $(BUILD_DIR)/observer.exe"; \
	else \
		echo "MinGW cross-compiler ($(MINGW_CC)) not found, skipping observer-win32"; \
	fi

clean:
	rm -rf $(BUILD_DIR)
