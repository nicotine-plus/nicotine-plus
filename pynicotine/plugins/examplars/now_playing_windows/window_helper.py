import ctypes
import ctypes.wintypes
import re


def get_now_playing(class_name, endswith_text):
    wnd_enum_proc = ctypes.WINFUNCTYPE(
        ctypes.wintypes.BOOL,
        ctypes.wintypes.HWND,
        ctypes.wintypes.LPARAM
    )
    found_text = None

    def enum_windows_callback(hwnd, _lparam):
        nonlocal found_text
        class_name_buffer = ctypes.create_unicode_buffer(256)
        text_buffer = ctypes.create_unicode_buffer(256)

        if ctypes.windll.user32.GetClassNameW(hwnd, class_name_buffer, 256) > 0:
            if class_name_buffer.value == class_name:
                if ctypes.windll.user32.GetWindowTextW(hwnd, text_buffer, 256) > 0:
                    window_text = text_buffer.value
                    if window_text.endswith(endswith_text):
                        found_text = window_text.removesuffix(endswith_text)
                        if endswith_text in {" - Winamp", " - MediaMonkey 2024"}:
                            found_text = re.sub(r"^\d+\.\s", "", found_text)  # strip track number
                        return False  # Stop enumeration once found
        return True  # Continue enumeration

    enum_func = wnd_enum_proc(enum_windows_callback)
    ctypes.windll.user32.EnumWindows(enum_func, 0)

    return found_text
