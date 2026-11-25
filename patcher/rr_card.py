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
CONTENT_SIZE = 10
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

GREEN = "button_generic06.png"
BLUE = "button_generic06_blue.png"
RED = "button_generic06_red.png"
# (title, buttons). Each button is (tag, label, sprite); tags match
# OfflineMenu.action. Four buttons share a row; a two-button row uses wider ones.
SECTIONS = (
    ("CURRENCY", ((1, "+10M COINS", GREEN), (2, "+100M COINS", GREEN), (3, "+1M RINGS", GREEN), (4, "+100M RINGS", GREEN))),
    ("SUPPLIES", ((5, "+100K BOOKS", GREEN), (6, "+100M BOOKS", GREEN), (7, "+100M PENCILS", GREEN), (8, "+100M TICKETS", GREEN))),
    ("LEVELS", ((9, "+1 LEVEL", GREEN), (10, "+5M XP", GREEN), (11, "MAX LEVEL", GREEN), (12, "UNLOCK ALL", RED))),
    ("PROGRESS", ((13, "EXPORT", BLUE), (14, "IMPORT", BLUE))),
)
# Geometry in the card's own units (the settings card spans x -140..195).
PANEL_X = -140
PANEL_WIDTH = 335
TOP_TITLE_Y = 100
SECTION_STEP = 66
PANEL_HEIGHT = 50
MENU_OFFSET_Y = 4  # the template's CCMenu and label container sit at y = 4
COLUMNS = {4: ((-98, -14, 70, 154), 0.55, 0.6), 2: ((-56, 112), 0.75, 0.9)}


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
    panel_template = panels[0]
    title_template = _drop(titles[0], MEMBER_NAME, MEMBER_TYPE)

    new_panels, new_titles, buttons, button_labels = [], [], [], []
    for index, (title, row) in enumerate(SECTIONS):
        title_y = TOP_TITLE_Y - SECTION_STEP * index
        panel = _set(panel_template, POSITION, 2, _point(PANEL_X, title_y - PANEL_HEIGHT))
        panel = _set(panel, CONTENT_SIZE, 2, encode([(1, 5, _f32(PANEL_WIDTH)), (2, 5, _f32(PANEL_HEIGHT))]))
        new_panels.append(panel)
        new_titles.append(
            _set(_set(title_template, POSITION, 2, _point(27, title_y)), LABEL_STRING, 2, title.encode())
        )
        xs, scale, label_scale = COLUMNS[len(row)]
        y = title_y - PANEL_HEIGHT / 2 - 2 - MENU_OFFSET_Y
        for (tag, text, sprite), x in zip(row, xs):
            button = _set(button_template, POSITION, 2, _point(x, y))
            button = _set(button, SCALE_X, 5, _f32(scale))
            button = _set(button, SCALE_Y, 5, _f32(scale))
            button = _set(button, TAG, 0, tag)
            for field in (SPRITE_NORMAL, SPRITE_SELECTED, SPRITE_DISABLED):
                button = _set(button, field, 2, sprite.encode())
            button = _set(button, SELECTOR, 2, b"aboutButtonCallback")
            buttons.append(button)
            label = _set(label_template, POSITION, 2, _point(x, y + 1))
            label = _set(label, SCALE_X, 5, _f32(label_scale))
            label = _set(label, SCALE_Y, 5, _f32(label_scale))
            label = _set(label, LABEL_STRING, 2, text.encode())
            button_labels.append(label)

    children = (
        new_panels
        + [_with_children(menu, buttons)]
        + new_titles
        + [_with_children(_drop(labels, MEMBER_NAME, MEMBER_TYPE), button_labels)]
    )
    root = _with_children(root, children)
    return encode(_set(top, ROOT, 2, encode(root)))
