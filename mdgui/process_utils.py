"""Safe process management for Windows EXE builds.

Only terminates processes whose *full executable path* matches the current
interpreter or EXE.  This prevents the old substring-matching bug where
unrelated processes containing "markitdown" in their name could be killed.
"""
import os
import sys

def _kill_old_instances():
    """Kill previously-running MarkItDown EXE instances (Windows only, frozen only)."""
    if os.name != "nt":
        return
    if not getattr(sys, "frozen", False):
        return
    try:
        import ctypes
        from ctypes import wintypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        PROCESS_TERMINATE = 0x0001
        psapi = ctypes.WinDLL("psapi")
        kernel32 = ctypes.WinDLL("kernel32")

        EnumProcesses = psapi.EnumProcesses
        EnumProcesses.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint)]
        EnumProcesses.restype = wintypes.BOOL
        GetModuleFileNameExW = psapi.GetModuleFileNameExW
        GetModuleFileNameExW.argtypes = [wintypes.HANDLE, wintypes.HMODULE,
                                          wintypes.LPWSTR, wintypes.DWORD]
        GetModuleFileNameExW.restype = wintypes.DWORD
        OpenProcess = kernel32.OpenProcess
        OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        OpenProcess.restype = wintypes.HANDLE
        TerminateProcess = kernel32.TerminateProcess
        TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        TerminateProcess.restype = wintypes.BOOL
        CloseHandle = kernel32.CloseHandle
        CloseHandle.argtypes = [wintypes.HANDLE]
        CloseHandle.restype = wintypes.BOOL

        buf = (ctypes.c_uint * 4096)()
        cb = ctypes.c_uint()
        if not EnumProcesses(ctypes.byref(buf), ctypes.sizeof(buf), ctypes.byref(cb)):
            return
        n = cb.value // ctypes.sizeof(ctypes.c_uint)
        my_pid = os.getpid()
        # Match by full absolute path (lowercased) instead of substring
        target_path = os.path.abspath(sys.executable).lower()

        for i in range(n):
            pid = buf[i]
            if pid == 0 or pid == my_pid:
                continue
            h = OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_TERMINATE,
                            False, pid)
            if not h:
                continue
            try:
                name_buf = ctypes.create_unicode_buffer(1024)
                if GetModuleFileNameExW(h, None, name_buf, 1024):
                    exe_path = os.path.abspath(name_buf.value or "").lower()
                    if exe_path == target_path:
                        TerminateProcess(h, 1)
            finally:
                CloseHandle(h)
    except Exception:
        pass
