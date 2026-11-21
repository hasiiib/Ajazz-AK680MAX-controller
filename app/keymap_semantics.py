"""Conservative human-readable labels for documented gen2 keymap entries.

Only exact, documented entry shapes receive friendly labels. Unknown or
composite entries remain visibly opaque instead of being guessed.
"""
from __future__ import annotations

_KEY_NAMES = {
    **{usage: chr(ord("A") + usage - 0x04) for usage in range(0x04, 0x1E)},
    **{usage: str((usage - 0x1D) % 10) for usage in range(0x1E, 0x28)},
    0x28: "Enter", 0x29: "Escape", 0x2A: "Backspace", 0x2B: "Tab",
    0x2C: "Space", 0x2D: "-", 0x2E: "=", 0x2F: "[", 0x30: "]",
    0x31: "\\", 0x33: ";", 0x34: "'", 0x35: "`", 0x36: ",",
    0x37: ".", 0x38: "/", 0x39: "Caps Lock",
    **{usage: f"F{usage - 0x3A + 1}" for usage in range(0x3A, 0x46)},
    0x46: "Print Screen", 0x47: "Scroll Lock", 0x48: "Pause",
    0x49: "Insert", 0x4A: "Home", 0x4B: "Page Up", 0x4C: "Delete",
    0x4D: "End", 0x4E: "Page Down", 0x4F: "Right", 0x50: "Left",
    0x51: "Down", 0x52: "Up",
    0xE0: "Left Ctrl", 0xE1: "Left Shift", 0xE2: "Left Alt",
    0xE3: "Left GUI", 0xE4: "Right Ctrl", 0xE5: "Right Shift",
    0xE6: "Right Alt", 0xE7: "Right GUI",
}

_CONSUMER_NAMES = {
    0x00E2: "Mute",
    0x00B5: "Next Track",
    0x00B6: "Previous Track",
    0x00B7: "Stop",
    0x00CD: "Play / Pause",
    0x00E9: "Volume Up",
    0x00EA: "Volume Down",
}



def extract_layout_usage(entry: bytes | bytearray) -> int | None:
    """Return the original HID usage for a simple key assignment, if exact."""
    if not isinstance(entry, (bytes, bytearray)) or len(entry) != 4:
        return None
    kind, a, b, c = bytes(entry)
    if kind == 0x00 and a == 0 and c == 0 and 0x04 <= b <= 0xE7:
        return b
    if kind == 0x0A and a == 1 and b == 0 and c == 0:
        return 1033
    return None

def describe_key_entry(entry: bytes | bytearray) -> str:
    """Describe only known 4-byte gen2 slot encodings; otherwise stay opaque."""
    if not isinstance(entry, (bytes, bytearray)) or len(entry) != 4:
        raise ValueError("A keymap entry must contain exactly four bytes.")
    value = bytes(entry)
    if value == bytes(4):
        return "Unassigned"
    kind, a, b, c = value

    if kind == 0x00:
        if a == 0 and c == 0 and b in _KEY_NAMES:
            return _KEY_NAMES[b]
        if a == 0 and c == 0 and b == 0:
            return "Unassigned"
        return "HID combination / extended usage (raw)"

    if kind == 0x01:
        return "Mouse button (raw)"
    if kind == 0x03 and a == 0:
        usage = b | (c << 8)
        return _CONSUMER_NAMES.get(usage, f"Consumer usage 0x{usage:04X}")
    if kind == 0x09 and c == 0:
        modes = {0: "repeat", 1: "toggle", 2: "while held"}
        mode = modes.get(a, f"mode {a}")
        return f"Macro {b + 1} ({mode})"
    if kind == 0x0A and b == 0 and c == 0:
        specials = {1: "Fn", 12: "Power save", 17: "Caps LED swap"}
        return specials.get(a, f"Special function {a}")
    return "Unknown assignment (raw)"
