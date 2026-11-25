"""Binary patches for libHSS.so from High School Story 5.4.0.

The library is a 32-bit ARM ELF with its C++ symbols still exported. The first
LOAD segment is identity-mapped, so a file offset is the same number as the
Thumb address with the low bit cleared. Every address below was found by symbol
name in the 5.4.0 library (see docs/REVERSE.md) and is checked against the
original bytes before anything is written.
"""

from __future__ import annotations

import struct
from pathlib import Path

# --- Engine entry points used by the new code -------------------------------
SHARED_LOGIC_MANAGER = 0x3DD8E0  # HSS::LogicManager::sharedManager()
# LogicManager virtual getters. HSS has one more getter than Hollywood U ahead
# of these, so the slots are +4 from the HWU ones (0x48/0x64 there).
VT_GET_PLAYER_LOGIC = 0x4C
VT_GET_STORE_LOGIC = 0x68
CREDIT_PURCHASE = 0x3F5EE8  # StoreLogic::creditPurchase(const std::string&)
FIRE_PURCHASE_COMPLETED = 0x40284C  # AppStoreManager::firePurchaseCompleted
GET_STATIC_METHOD = 0x35E970  # cocos2d::JniHelper::getStaticMethodInfo

# PlayerLogic wallets. In the game UI rings are "hearts" and books are "stars".
CREDIT_COINS = 0x3E74C4
CREDIT_HEARTS = 0x3E7500
CREDIT_STARS = 0x3E74E0
CREDIT_PENCILS = 0x3E7520
CREDIT_TICKETS = 0x3E7540
CREDIT_XP = 0x3E4BF0
# Wallet number the Java menu passes, in this order.
WALLETS = (CREDIT_COINS, CREDIT_HEARTS, CREDIT_STARS, CREDIT_PENCILS, CREDIT_TICKETS, CREDIT_XP)

# --- AppStoreManager -----------------------------------------------------------
ARE_PRODUCTS_AVAILABLE = 0x401448
HAS_PRODUCT = 0x4014E0
CAN_PURCHASE = 0x401534
PURCHASE = 0x401540  # 0x22 bytes; called with (this, productId, quantity)
PURCHASE_SIZE = 0x22

# --- Account gates -------------------------------------------------------------
# A buy with no Pixelberry account used to call the dead create-account server.
PURCHASE_ITEM_SKIP_BUSY = 0x3BFE06  # InGamePurchaseState::purchaseItem beq
PURCHASE_ITEM_REQUIRE_ACCOUNT = 0x3BFE6C  # bne into the real buy
PURCHASE_CURRENCY_SKIP_BUSY = 0x3C0DE0  # MainStoreDialogState::purchaseCurrency beq
PURCHASE_CURRENCY_REQUIRE_ACCOUNT = 0x3C0E44  # beq into the account error
HAS_PIXELBERRY_ACCOUNT = 0x40C718  # ServerManager::hasPixelberryAccount
# prepurchaseCurrency shows a choice dialog (tutorial / account flags) before
# the buy. The first instruction after the prologue jumps straight to the buy.
PREPURCHASE_GATE = 0x3C0F22
PREPURCHASE_BUY = 0x3C0F7E

# --- "Network error" store tabs ------------------------------------------------
CURRENCY_NETWORK_BPL = 0x3C29EC  # MainStoreDialogState::onInit
CURRENCY_NETWORK_B = 0x3C2EE4
CLOTHING_NETWORK_BNE = 0x45AA68  # ClothingStoreCard::initWithItems

# --- Java calls after a buy that fault on current Android ----------------------
CURRENCY_EARNED_SOUND = 0x41B720  # SoundManager::onCurrencyEarned
CREDIT_PURCHASE_SOUND = 0x3F6154  # bl SoundManager::playEffect inside creditPurchase
EMIT_TELEMETRY = 0x42DCC0  # TelemetryManager::emitTelemetryEvent
CURRENCY_ITEM_VISIBLE = 0x3F5D2C  # StoreLogic::isCurrencyItemVisible (sale-date checks)
LEANPLUM_TRACK = {  # DKLeanPlumManager::track overloads
    0x367FA8: "30b5",
    0x368010: "f0b5",
    0x368090: "f0b5",
    0x368100: "f0b5",
    0x368198: "70b5",
    0x368214: "f0b5",
}
POST_PURCHASE_SCENE = 0x3C22F2  # bl inside MainStoreDialogState::handlePostPurchaseFlow

# --- Store-card locks ------------------------------------------------------------
RETURN_TRUE = {
    0x3F5D10: "38b5051c",  # StoreLogic::isCurrencyItemUnlocked
    0x3F5C50: "f0b54746",  # StoreLogic::isCurrencyBuildingUnlocked
    0x3F4B8C: "70b5ca6e",  # StoreLogic::isCurrencyClothingUnlocked
    0x3F4C28: "10b58823",  # StoreLogic::hasQuestIdUnlocked ("Unlocks with Quest")
    0x3D6EE4: "38b5051c",  # ClothingLogic::isClothingUnlocked
}
RETURN_FALSE = {
    0x3D6E00: "f8b5061c",  # ClothingLogic::isLocked
}
SET_LOCKED = 0x4AD47C  # Store::StoreItem::setLocked(bool)
# testPurchase return codes 4, 4 and 6 are requirement failures (level, quest,
# clothing). They become 0 so a real product still credits. 2 (no such
# product), 3 (one-time item already owned) and 5 (admissions full) stay.
TEST_PURCHASE_REQUIREMENTS = {
    0x3F5B20: "0420",
    0x3F5B42: "0420",
    0x3F5B52: "0620",
}

# --- RR Mod Settings ---------------------------------------------------------------
ABOUT_BUTTON = 0x49E434  # Settings::SettingsCard::aboutButtonCallback
# The SponsorPay offer wall is gone. These three JNI bodies are contiguous
# (0x369068..0x369170) and their Java call sites are removed by the smali patch.
MENU_CAVE = 0x369068  # was DKSponsorPayOnChangeStatusCloseFinished (+ CloseAborted)
GRANT = 0x369118  # was DKSponsorPayOnChangeStatusError, now (int wallet, int amount)
GRANT_END = 0x369170
MENU_CLASS = b"com/pixelberrystudios/hssandroid/OfflineMenu"

EXPECTED = {
    SHARED_LOGIC_MANAGER: "10b5054c",
    CREDIT_PURCHASE: "f0b5",
    FIRE_PURCHASE_COMPLETED: "f0b54746",
    GET_STATIC_METHOD: "f0b54f46",
    CREDIT_COINS: "10b50023",
    CREDIT_HEARTS: "10b50023",
    CREDIT_STARS: "10b50022",
    CREDIT_PENCILS: "10b50023",
    CREDIT_TICKETS: "10b50023",
    CREDIT_XP: "f0b55746",
    ARE_PRODUCTS_AVAILABLE: "00b53422",
    HAS_PRODUCT: "f8b54646",
    CAN_PURCHASE: "08b55ff7",
    PURCHASE: "f8b5071c0e1c141c5ff7c8f9",
    PURCHASE_ITEM_SKIP_BUSY: "2ad0",
    PURCHASE_ITEM_REQUIRE_ACCOUNT: "01d1",
    PURCHASE_CURRENCY_SKIP_BUSY: "2bd0",
    PURCHASE_CURRENCY_REQUIRE_ACCOUNT: "11d0",
    HAS_PIXELBERRY_ACCOUNT: "044908b5",
    PREPURCHASE_GATE: "1cf0ddfc",
    PREPURCHASE_BUY: "41f095f9",
    CURRENCY_NETWORK_BPL: "00d56de2",
    CURRENCY_NETWORK_B: "84e5",
    CLOTHING_NETWORK_BNE: "68d1",
    CURRENCY_EARNED_SOUND: "38b5",
    CREDIT_PURCHASE_SOUND: "25f046fa",
    EMIT_TELEMETRY: "10b5",
    CURRENCY_ITEM_VISIBLE: "f0b54546",
    POST_PURCHASE_SCENE: "fff78dfd",
    SET_LOCKED: "f8b58623",
    ABOUT_BUTTON: "10b5041c",
    MENU_CAVE: "30b51820",
    0x3690C0: "30b51820",  # CloseAborted, overwritten by the end of the menu cave
    GRANT: "30b51820",
    GRANT_END: "074b10b5",  # DKSponsorPay::~DKSponsorPay, must stay untouched
}


# --- Thumb encoders ------------------------------------------------------------------
def _hw(value: int) -> bytes:
    return struct.pack("<H", value)


def _branch32(src: int, dst: int, link: bool) -> bytes:
    offset = dst - (src + 4)
    if offset & 1 or not (-0x1000000 <= offset <= 0xFFFFFF):
        raise ValueError(f"branch out of range {src:#x} -> {dst:#x}")
    sign = (offset >> 24) & 1
    i1 = (offset >> 23) & 1
    i2 = (offset >> 22) & 1
    j1 = (~(i1 ^ sign)) & 1
    j2 = (~(i2 ^ sign)) & 1
    hw1 = 0xF000 | (sign << 10) | ((offset >> 12) & 0x3FF)
    hw2 = ((0b11 if link else 0b10) << 14) | (j1 << 13) | (1 << 12) | (j2 << 11) | ((offset >> 1) & 0x7FF)
    return struct.pack("<HH", hw1, hw2)


def _bl(src: int, dst: int) -> bytes:
    return _branch32(src, dst, True)


def _b_wide(src: int, dst: int) -> bytes:
    return _branch32(src, dst, False)


def _b_short(src: int, dst: int) -> bytes:
    offset = dst - (src + 4)
    if offset % 2 or not (-2048 <= offset <= 2046):
        raise ValueError(f"b {src:#x} -> {dst:#x}")
    return _hw(0xE000 | ((offset >> 1) & 0x7FF))


def _b_cond(src: int, cond: int, dst: int) -> bytes:
    offset = dst - (src + 4)
    if offset % 2 or not (-256 <= offset <= 254):
        raise ValueError(f"short branch {src:#x} -> {dst:#x}")
    return _hw(0xD000 | (cond << 8) | ((offset >> 1) & 0xFF))


def _movs_imm(reg: int, imm: int) -> bytes:
    return _hw(0x2000 | (reg << 8) | imm)


def _cmp_imm(reg: int, imm: int) -> bytes:
    return _hw(0x2800 | (reg << 8) | imm)


def _mov_low(dst: int, src: int) -> bytes:
    return _hw(0x1C00 | (src << 3) | dst)  # adds dst, src, #0


def _ldr_imm(dst: int, base: int, byte_off: int) -> bytes:
    if byte_off % 4 or byte_off > 124:
        raise ValueError(byte_off)
    return _hw(0x6800 | ((byte_off // 4) << 6) | (base << 3) | dst)


def _return_imm(value: int) -> bytes:
    return _movs_imm(0, value) + _hw(0x4770)  # movs r0, #imm; bx lr


NOP = _hw(0x46C0)  # mov r8, r8
BX_LR = _hw(0x4770)
EQ, NE = 0, 1


class _Asm:
    """Tiny label-resolving Thumb assembler for the caves."""

    def __init__(self, base: int) -> None:
        self.base = base
        self.out = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[str, int, str]] = []

    def here(self) -> int:
        return self.base + len(self.out)

    def emit(self, data: bytes) -> None:
        self.out += data

    def mark(self, name: str) -> None:
        self.labels[name] = self.here()

    def bl(self, target: int) -> None:
        self.emit(_bl(self.here(), target))

    def branch(self, kind: str, name: str) -> None:
        self.fixups.append((kind, self.here(), name))
        self.emit(b"\x00\x00")

    def finish(self) -> bytes:
        for kind, src, name in self.fixups:
            dst = self.labels[name]
            code = _b_short(src, dst) if kind == "al" else _b_cond(src, {"eq": EQ, "ne": NE}[kind], dst)
            self.out[src - self.base : src - self.base + 2] = code
        return bytes(self.out)


# --- Generated code ------------------------------------------------------------------
def local_purchase() -> bytes:
    """AppStoreManager::purchase(this, id, qty) replacement.

    Credits the product's own config reward through StoreLogic::creditPurchase,
    then tells the store listeners the buy completed. No Google Play call.
    """
    a = _Asm(PURCHASE)
    a.emit(_hw(0xB530))  # push {r4, r5, lr}
    a.emit(_mov_low(4, 0))
    a.emit(_mov_low(5, 1))
    a.bl(SHARED_LOGIC_MANAGER)
    a.emit(_ldr_imm(3, 0, 0))
    a.emit(_ldr_imm(3, 3, VT_GET_STORE_LOGIC))
    a.emit(_hw(0x4798))  # blx r3
    a.emit(_mov_low(1, 5))
    a.bl(CREDIT_PURCHASE)
    a.emit(_mov_low(0, 4))
    a.emit(_mov_low(1, 5))
    a.bl(FIRE_PURCHASE_COMPLETED)
    a.emit(_hw(0xBD30))  # pop {r4, r5, pc}
    blob = a.finish()
    if len(blob) > PURCHASE_SIZE:
        raise RuntimeError("local purchase does not fit")
    return blob


def grant_dispatcher() -> bytes:
    """JNI (JNIEnv*, jclass, jint wallet, jint amount) -> PlayerLogic::creditX(amount).

    Wallet 0 coins, 1 rings, 2 books, 3 pencils, 4 tickets, anything else XP.
    """
    a = _Asm(GRANT)
    a.emit(_hw(0xB570))  # push {r4, r5, r6, lr}
    a.emit(_mov_low(4, 2))
    a.emit(_mov_low(5, 3))
    a.bl(SHARED_LOGIC_MANAGER)
    a.emit(_cmp_imm(0, 0))
    a.branch("eq", "done")
    a.emit(_ldr_imm(3, 0, 0))
    a.emit(_ldr_imm(3, 3, VT_GET_PLAYER_LOGIC))
    a.emit(_hw(0x4798))  # blx r3
    a.emit(_cmp_imm(0, 0))
    a.branch("eq", "done")
    a.emit(_mov_low(1, 5))
    for index, target in enumerate(WALLETS[:-1]):
        a.emit(_cmp_imm(4, index))
        a.branch("ne", f"k{index + 1}")
        a.bl(target)
        a.branch("al", "done")
        a.mark(f"k{index + 1}")
    a.bl(WALLETS[-1])
    a.mark("done")
    a.emit(_hw(0xBD70))  # pop {r4, r5, r6, pc}
    blob = a.finish()
    if GRANT + len(blob) > GRANT_END:
        raise RuntimeError(f"grant dispatcher is {len(blob)} bytes, room for {GRANT_END - GRANT}")
    return blob


def menu_cave() -> bytes:
    """Call OfflineMenu.showFromGame() through JniHelper from the cocos thread."""
    body = bytearray(
        bytes.fromhex(
            "10b5"  # push {r4, lr}
            "83b0"  # sub sp, #12
            "6846"  # mov r0, sp
            "0000"  # ldr r1, [pc, #?]
            "7944"  # add r1, pc
            "0000"  # ldr r2, [pc, #?]
            "7a44"  # add r2, pc
            "0000"  # ldr r3, [pc, #?]
            "7b44"  # add r3, pc
            "00000000"  # bl getStaticMethodInfo
            "0028"  # cmp r0, #0
            "00d0"  # beq done
            "0098"  # ldr r0, [sp, #0]   env
            "0199"  # ldr r1, [sp, #4]   class
            "029a"  # ldr r2, [sp, #8]   method
            "0368"  # ldr r3, [r0]
            "8e24"  # movs r4, #0x8e
            "a400"  # lsls r4, r4, #2    CallStaticVoidMethod
            "1c59"  # ldr r4, [r3, r4]
            "a047"  # blx r4
            "03b0"  # done: add sp, #12
            "10bd"  # pop {r4, pc}
        )
    )
    done = body.find(bytes.fromhex("03b010bd"))
    beq = body.find(bytes.fromhex("002800d0")) + 2
    body[beq : beq + 2] = _b_cond(MENU_CAVE + beq, EQ, MENU_CAVE + done)
    call = body.find(bytes.fromhex("00000000"))
    body[call : call + 4] = _bl(MENU_CAVE + call, GET_STATIC_METHOD)
    while len(body) & 3:
        body += b"\x00"
    pool = MENU_CAVE + len(body)
    cls = MENU_CLASS + b"\x00"
    method = b"showFromGame\x00"
    sig = b"()V\x00"
    strings_at = pool + 12
    targets = [strings_at, strings_at + len(cls), strings_at + len(cls) + len(method)]
    words = bytearray()
    cursor = 0
    for index, target in enumerate(targets):
        rt = index + 1
        at = body.find(_hw(0x0000) + _hw(0x4478 | rt), cursor)
        if at < 0:
            raise RuntimeError("menu cave literal slot missing")
        cursor = at + 4
        ldr_addr = MENU_CAVE + at
        slot = pool + len(words)
        imm = slot - ((ldr_addr + 4) & ~3)
        if imm < 0 or imm > 0x3FC or imm & 3:
            raise RuntimeError(f"menu cave literal {imm:#x}")
        body[at : at + 2] = _hw(0x4800 | (rt << 8) | (imm >> 2))
        words += struct.pack("<I", (target - (ldr_addr + 2 + 4)) & 0xFFFFFFFF)
    return bytes(body + words + cls + method + sig)


def set_locked_stub(at: int, original: bytes) -> bytes:
    """setLocked(bool) with the argument forced to false, then the original body."""
    stub = _movs_imm(1, 0) + original + _b_wide(at + 2 + len(original), SET_LOCKED + 4)
    return stub


# --- Driver --------------------------------------------------------------------------
def _expect(data: bytearray, addr: int, expected: str) -> None:
    want = bytes.fromhex(expected)
    found = bytes(data[addr : addr + len(want)])
    if found != want:
        raise RuntimeError(
            f"libHSS.so at {addr:#x} is {found.hex()}, expected {want.hex()}. "
            "This patcher only matches the High School Story 5.4.0 library."
        )


def patch_libhss(path: Path) -> None:
    data = bytearray(path.read_bytes())
    checks = {**EXPECTED, **RETURN_TRUE, **RETURN_FALSE, **LEANPLUM_TRACK, **TEST_PURCHASE_REQUIREMENTS}
    for addr, expected in checks.items():
        _expect(data, addr, expected)

    def put(addr: int, blob: bytes) -> None:
        data[addr : addr + len(blob)] = blob

    # Store answers "available" and pays out locally.
    put(ARE_PRODUCTS_AVAILABLE, _return_imm(1))
    put(HAS_PRODUCT, _return_imm(1))
    put(CAN_PURCHASE, _return_imm(1))
    put(PURCHASE, local_purchase())

    # No Pixelberry account: skip the busy dialog, then take the buy branch.
    put(PURCHASE_ITEM_SKIP_BUSY, bytes.fromhex("2ae0"))  # beq -> b
    put(PURCHASE_ITEM_REQUIRE_ACCOUNT, bytes.fromhex("01e0"))  # bne -> b
    put(PURCHASE_CURRENCY_SKIP_BUSY, bytes.fromhex("2be0"))  # beq -> b
    put(PURCHASE_CURRENCY_REQUIRE_ACCOUNT, NOP)
    put(HAS_PIXELBERRY_ACCOUNT, _return_imm(1))
    put(PREPURCHASE_GATE, _b_short(PREPURCHASE_GATE, PREPURCHASE_BUY))

    # Fall through into the real currency list instead of "Network error".
    put(CURRENCY_NETWORK_BPL, NOP)
    put(CURRENCY_NETWORK_B, _hw(0xE7FF))  # b to the next instruction
    put(CLOTHING_NETWORK_BNE, NOP)

    # Post-purchase Java calls that abort the process on current Android.
    put(CURRENCY_EARNED_SOUND, BX_LR)
    put(CREDIT_PURCHASE_SOUND, NOP + NOP)
    put(EMIT_TELEMETRY, BX_LR)
    put(CURRENCY_ITEM_VISIBLE, _return_imm(1))
    for addr in LEANPLUM_TRACK:
        put(addr, BX_LR)
    put(POST_PURCHASE_SCENE, NOP + NOP)

    # Store-card locks.
    for addr in RETURN_TRUE:
        put(addr, _return_imm(1))
    for addr in RETURN_FALSE:
        put(addr, _return_imm(0))
    for addr in TEST_PURCHASE_REQUIREMENTS:
        put(addr, _movs_imm(0, 0))

    # RR Mod Settings: ABOUT opens the Java panel; the panel calls GRANT.
    menu = menu_cave()
    put(MENU_CAVE, menu)
    lock_at = MENU_CAVE + len(menu)
    lock_at += lock_at & 1
    lock = set_locked_stub(lock_at, bytes(data[SET_LOCKED : SET_LOCKED + 4]))
    if lock_at + len(lock) > GRANT:
        raise RuntimeError("menu cave and lock stub spill into the grant dispatcher")
    put(lock_at, lock)
    put(SET_LOCKED, _b_wide(SET_LOCKED, lock_at))
    put(ABOUT_BUTTON, _b_wide(ABOUT_BUTTON, MENU_CAVE))
    put(GRANT, grant_dispatcher())

    _expect(data, GRANT_END, EXPECTED[GRANT_END])
    path.write_bytes(data)
