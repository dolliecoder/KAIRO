"""One KAIRO per data folder, and a way to stop it from outside (the Start-menu "Quit KAIRO" shortcut runs
`KAIRO.exe --quit`).

Windows only, using two named kernel objects:
- a mutex: whoever creates it first is "the" running KAIRO; a second launch sees it and shows a message instead;
- an event: the running KAIRO waits on it, and `--quit` sets it.
Both names include a hash of the data folder, so the installed app, a source checkout and tests never block each other."""
import ctypes
import hashlib
import os
import sys
import threading

_ERROR_ALREADY_EXISTS = 183
_EVENT_MODIFY_STATE = 0x0002
_INFINITE = 0xFFFFFFFF
_handles: list = []  # kept alive for the life of the process
_quit_event = None  # created together with the mutex, so --quit works even while KAIRO is still loading


def _names() -> tuple[str, str]:
    from .paths import DATA_DIR
    tag = hashlib.sha1(str(DATA_DIR).lower().encode("utf-8")).hexdigest()[:10]
    return f"Local\\KAIRO.Instance.{tag}", f"Local\\KAIRO.Quit.{tag}"


def _kernel32():
    from ctypes import wintypes
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    k.CreateMutexW.restype, k.CreateMutexW.argtypes = wintypes.HANDLE, [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    k.CreateEventW.restype = wintypes.HANDLE
    k.CreateEventW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
    k.OpenEventW.restype, k.OpenEventW.argtypes = wintypes.HANDLE, [wintypes.DWORD, wintypes.BOOL, wintypes.LPCWSTR]
    k.SetEvent.argtypes = [wintypes.HANDLE]
    k.CloseHandle.argtypes = [wintypes.HANDLE]
    k.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    return k


def _message(text: str) -> None:
    """A small Windows message box (KAIRO has no console). KAIRO_NO_DIALOGS=1 prints instead, for tests."""
    if os.environ.get("KAIRO_NO_DIALOGS"):
        print(text, flush=True)
        return
    ctypes.windll.user32.MessageBoxW(None, text, "KAIRO", 0x40)  # 0x40 = information icon


def acquire() -> bool:
    """True if this is the first KAIRO; False if one is already running."""
    k = _kernel32()
    mutex_name, _ = _names()
    handle = k.CreateMutexW(None, False, mutex_name)
    if ctypes.get_last_error() == _ERROR_ALREADY_EXISTS:
        k.CloseHandle(handle)
        return False
    _handles.append(handle)
    _ensure_quit_event(k)
    return True


def _ensure_quit_event(k):
    global _quit_event
    if _quit_event is None:
        _, quit_name = _names()
        _quit_event = k.CreateEventW(None, False, False, quit_name)  # auto-reset, starts unsignalled
        _handles.append(_quit_event)
    return _quit_event


def request_quit() -> bool:
    """Ask the running KAIRO to stop. False if none is running."""
    k = _kernel32()
    _, quit_name = _names()
    handle = k.OpenEventW(_EVENT_MODIFY_STATE, False, quit_name)
    if not handle:
        return False
    k.SetEvent(handle)
    k.CloseHandle(handle)
    return True


def watch_for_quit(callback) -> None:
    """In the running KAIRO: call `callback` when another process runs `KAIRO.exe --quit`."""
    if sys.platform != "win32":
        return
    k = _kernel32()
    event = _ensure_quit_event(k)  # already signalled if --quit arrived while KAIRO was loading

    def wait() -> None:
        k.WaitForSingleObject(event, _INFINITE)
        callback()

    threading.Thread(target=wait, daemon=True, name="kairo-quit-watcher").start()


def guard() -> None:
    """Call once at startup. Handles `--quit`, and exits quietly if KAIRO is already running.
    Self-tests and the --learned window are exempt so they work while KAIRO is running."""
    if sys.platform != "win32" or "--learned" in sys.argv or any(a.startswith("--selftest") for a in sys.argv):
        return
    if "--quit" in sys.argv:
        if not request_quit():
            _message("KAIRO is not running.")
        sys.exit(0)
    if not acquire():
        _message("KAIRO is already running.\n\nLook for the pink K in your system tray (near the clock; it may be "
                 "under the ^ arrow). Hold Right Ctrl to talk.\n\nTo stop it: right-click the K and choose Quit KAIRO.")
        sys.exit(0)
