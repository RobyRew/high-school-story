"""Build assets/rr_mod_card.ccb from the game's own android_settings_card.ccb.

High School Story's .ccb files are darthkitty.Proto.CcbNode protobufs (the
field numbers below come from the descriptor embedded in libHSS.so). The RR MOD
card reuses the settings card's panels, fonts and button art so it looks like
the other tabs. Every button calls SettingsCard::aboutButtonCallback; the
node tag tells hss_native's action cave which RR action to run.
"""

from __future__ import annotations

import struct

# darthkitty.Proto.CcbNode fields
NODE_CLASS = 1
MEMBER_NAME = 7
MEMBER_TYPE = 8
POSITION = 9
SCALE_X = 11
SCALE_Y = 12
TAG = 17
CUSTOM_CLASS = 59
LABEL_STRING = 62
SPRITE_NORMAL = 63
SPRITE_SELECTED = 64
SPRITE_DISABLED = 65
SELECTOR = 67
CHILDREN = 69  # CcbNodeList, repeated field 1 = CcbNode
ROOT = 2  # field of the file message that holds the root node

# (tag, label, column x, row y, scale, sprite). Tags match OfflineMenu.action.
GREEN = "button_generic06.png"
BLUE = "button_generic06_blue.png"
SMALL = 0.75
BUTTONS = (
    (1, "+10M COINS", -86, 54, SMALL, GREEN),
    (2, "+1M RINGS", 27, 54, SMALL, GREEN),
    (3, "+10K XP", 140, 54, SMALL, GREEN),
    (4, "+100K BOOKS", -86, -27, SMALL, GREEN),
    (5, "+10K PENCILS", 27, -27, SMALL, GREEN),
    (6, "+1K TICKETS", 140, -27, SMALL, GREEN),
    (7, "EXPORT", -60, -110, 1.0, BLUE),
    (8, "IMPORT", 115, -110, 1.0, BLUE),
)
TITLES = ("CURRENCY", "SUPPLIES", "PROGRESS")


def _varint(data: bytes, i: int) -> tuple[int, int]:
    result = shift = 0
    while True:
        byte = data[i]
        i += 1
        result |= (byte & 0x7F) << shift
        shift += 7
        if byte < 0x80:
            return result, i


def _put_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def parse(data: bytes) -> list[tuple[int, int, object]]:
    fields = []
    i = 0
    while i < len(data):
        key, i = _varint(data, i)
        number, wire = key >> 3, key & 7
        if wire == 0:
            value, i = _varint(data, i)
        elif wire == 1:
            value, i = data[i : i + 8], i + 8
        elif wire == 2:
            length, i = _varint(data, i)
            value, i = data[i : i + length], i + length
        elif wire == 5:
            value, i = data[i : i + 4], i + 4
        else:
            raise ValueError(f"unsupported wire type {wire}")
        fields.append((number, wire, value))
    return fields


def encode(fields: list[tuple[int, int, object]]) -> bytes:
    out = bytearray()
    for number, wire, value in fields:
        out += _put_varint((number << 3) | wire)
        if wire == 0:
            out += _put_varint(value)  # type: ignore[arg-type]
        elif wire == 2:
            out += _put_varint(len(value)) + value  # type: ignore[arg-type,operator]
        else:
            out += value  # type: ignore[operator]
    return bytes(out)


def _get(fields, number):
    for n, _, value in fields:
        if n == number:
            return value
    return None


def _set(fields, number, wire, value):
    kept = [f for f in fields if f[0] != number]
    return kept + [(number, wire, value)]


def _drop(fields, *numbers):
    return [f for f in fields if f[0] not in numbers]


def _f32(value: float) -> bytes:
    return struct.pack("<f", value)


def _point(x: float, y: float) -> bytes:
    return encode([(1, 5, _f32(x)), (2, 5, _f32(y))])


def _children(node):
    return [parse(v) for n, _, v in parse(_get(node, CHILDREN) or b"") if n == 1]


def _with_children(node, children):
    body = encode([(1, 2, encode(child)) for child in children])
    return _set(node, CHILDREN, 2, body)


def _named(nodes, member):
    for node in nodes:
        if _get(node, MEMBER_NAME) == member.encode():
            return node
    raise RuntimeError(f"android_settings_card.ccb has no {member}")


def build(template: bytes) -> bytes:
    top = parse(template)
    root = parse(_get(top, ROOT))
    if _get(root, CUSTOM_CLASS) != b"SettingsCard":
        raise RuntimeError("android_settings_card.ccb root is not a SettingsCard")
    nodes = _children(root)
    panels = [n for n in nodes if _get(n, CUSTOM_CLASS) == b"LinenDarkest9Slice"]
    menu = next(n for n in nodes if _get(n, NODE_CLASS) == b"CCMenu")
    titles = [n for n in nodes if _get(n, NODE_CLASS) == b"CCLabelBMFont"]
    labels = _named(nodes, "buttonLabels")
    button_template = _drop(_named(_children(menu), "aboutButton"), MEMBER_NAME, MEMBER_TYPE)
    label_template = _drop(_named(_children(labels), "musicOnLabel"), MEMBER_NAME, MEMBER_TYPE)
    if len(panels) != 3 or len(titles) != 3:
        raise RuntimeError("android_settings_card.ccb layout changed")

    buttons = []
    button_labels = []
    for tag, text, x, y, scale, sprite in BUTTONS:
        button = _set(button_template, POSITION, 2, _point(x, y))
        button = _set(button, SCALE_X, 5, _f32(scale))
        button = _set(button, SCALE_Y, 5, _f32(scale))
        button = _set(button, TAG, 0, tag)
        for field in (SPRITE_NORMAL, SPRITE_SELECTED, SPRITE_DISABLED):
            button = _set(button, field, 2, sprite.encode())
        button = _set(button, SELECTOR, 2, b"aboutButtonCallback")
        buttons.append(button)
        label = _set(label_template, POSITION, 2, _point(x, y + 1))
        label = _set(label, SCALE_X, 5, _f32(0.85 if scale < 1 else 1.0))
        label = _set(label, SCALE_Y, 5, _f32(0.85 if scale < 1 else 1.0))
        label = _set(label, LABEL_STRING, 2, text.encode())
        button_labels.append(label)

    new_titles = [
        _set(_drop(title, MEMBER_NAME, MEMBER_TYPE), LABEL_STRING, 2, text.encode())
        for title, text in zip(titles, TITLES)
    ]
    children = (
        panels
        + [_with_children(menu, buttons)]
        + new_titles
        + [_with_children(_drop(labels, MEMBER_NAME, MEMBER_TYPE), button_labels)]
    )
    root = _with_children(root, children)
    return encode(_set(top, ROOT, 2, encode(root)))
