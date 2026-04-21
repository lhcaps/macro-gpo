try:
    import win32con
    import win32gui

    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


IGNORED_TITLES = {
    "",
    "Program Manager",
}


def _normalize_title(title):
    return (title or "").strip().lower()


def list_visible_window_titles():
    if not WIN32_AVAILABLE:
        return []

    titles = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd).strip()
        if title in IGNORED_TITLES:
            return
        titles.append(title)

    win32gui.EnumWindows(enum_handler, None)
    return sorted(dict.fromkeys(titles))


def get_foreground_window_title():
    if not WIN32_AVAILABLE:
        return ""
    try:
        hwnd = win32gui.GetForegroundWindow()
        root_hwnd = win32gui.GetAncestor(hwnd, win32con.GA_ROOT)
        return win32gui.GetWindowText(root_hwnd).strip()
    except Exception:
        return ""


def find_window_by_title(title_query):
    if not WIN32_AVAILABLE:
        return None

    normalized_query = _normalize_title(title_query)
    if not normalized_query:
        return None

    exact_matches = []
    partial_matches = []

    def enum_handler(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return

        title = win32gui.GetWindowText(hwnd).strip()
        normalized_title = _normalize_title(title)
        if title in IGNORED_TITLES or not normalized_title:
            return

        if normalized_title == normalized_query:
            exact_matches.append((hwnd, title))
        elif normalized_query in normalized_title:
            partial_matches.append((hwnd, title))

    win32gui.EnumWindows(enum_handler, None)

    def score(match):
        hwnd, _ = match
        try:
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        except Exception:
            return 0
        return max(0, right - left) * max(0, bottom - top)

    if exact_matches:
        return max(exact_matches, key=score)
    if partial_matches:
        return max(partial_matches, key=score)
    return None


def is_window_active(title_query):
    match = find_window_by_title(title_query)
    if not match or not WIN32_AVAILABLE:
        return False

    try:
        active_hwnd = win32gui.GetForegroundWindow()
        active_root_hwnd = win32gui.GetAncestor(active_hwnd, win32con.GA_ROOT)
    except Exception:
        return False

    if active_root_hwnd == match[0]:
        return True

    active_title = win32gui.GetWindowText(active_root_hwnd).strip()
    normalized_active_title = _normalize_title(active_title)
    normalized_query = _normalize_title(title_query)
    return bool(normalized_query and normalized_query in normalized_active_title)


def get_window_rect(title_query):
    match = find_window_by_title(title_query)
    if not match or not WIN32_AVAILABLE:
        return None

    hwnd, _ = match
    try:
        client_left_top = win32gui.ClientToScreen(hwnd, (0, 0))
        client_rect = win32gui.GetClientRect(hwnd)
        left = int(client_left_top[0])
        top = int(client_left_top[1])
        right = left + int(client_rect[2] - client_rect[0])
        bottom = top + int(client_rect[3] - client_rect[1])
    except Exception:
        return None

    try:
        screen_width = int(win32gui.GetSystemMetrics(win32con.SM_CXSCREEN))
        screen_height = int(win32gui.GetSystemMetrics(win32con.SM_CYSCREEN))
        left = max(0, left)
        top = max(0, top)
        right = min(screen_width, right)
        bottom = min(screen_height, bottom)
    except Exception:
        pass

    if right <= left or bottom <= top:
        return None
    return left, top, right, bottom


def bring_window_to_foreground(title_query):
    match = find_window_by_title(title_query)
    if not match or not WIN32_AVAILABLE:
        return False

    hwnd, _ = match
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        else:
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        win32gui.BringWindowToTop(hwnd)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False
