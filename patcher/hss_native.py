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
# Wallet number the Java side passes, in this order. 5 is XP; 6 means "+1 level"
# and 7 "max level" (both credit XP computed from the level table).
WALLETS = (CREDIT_COINS, CREDIT_HEARTS, CREDIT_STARS, CREDIT_PENCILS, CREDIT_TICKETS, CREDIT_XP)
GETTERS = (
    0x3E4CAC,  # PlayerLogic::getCoins
    0x3E4E7C,  # PlayerLogic::getHearts
    0x3E4D94,  # PlayerLogic::getStars
    0x3E4F64,  # PlayerLogic::getPencils
    0x3E504C,  # PlayerLogic::getTickets
    0x3E4B58,  # PlayerLogic::getXP
)
# Every wallet, XP included, is capped below 2^31 so repeated taps cannot wrap.
WALLET_CAP = 2_000_000_000
# Every wallet change in the game (credit, debit, promo rewards, save load)
# ends in one of these setters. Each entry branches to a stub that clamps the
# new value at WALLET_CAP, so game income cannot push a wallet past it either.
SETTERS = {
    0x3E4CD0: "f8b5061c",  # PlayerLogic::setCoins
    0x3E4EA0: "f8b5061c",  # PlayerLogic::setHearts
    0x3E4DB8: "f8b5061c",  # PlayerLogic::setStars
    0x3E4F88: "f8b5061c",  # PlayerLogic::setPencils
    0x3E5070: "f8b5061c",  # PlayerLogic::setTickets
    0x3E4B9C: "f8b5051c",  # PlayerLogic::setXP
}
CLAMP_CAVE = 0x368218  # inside track(const char*, double, map) 0x368214..0x3682A0
CLAMP_CAVE_END = 0x3682A0
GET_SHARED_CONFIG = 0x37CD74  # Config::getSharedConfig(); +0x58 is the player level count
CONFIG_LEVEL_COUNT = 0x58
GET_XP_FOR_LEVEL = 0x3E4B28  # PlayerLogic::getXPForLevel(unsigned), 0 for level <= 1
GET_XP = 0x3E4B58  # PlayerLogic::getXP
GET_PLAYER_LEVEL = 0x3E4B7C  # PlayerLogic::getPlayerLevel
IS_PLAYER_MAX_LEVEL = 0x3E4B88  # PlayerLogic::isPlayerMaxLevel(); max level is count + 1

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
LEANPLUM_TRACK = {  # DKLeanPlumManager::track overloads
    0x367FA8: "30b5",
    0x368010: "f0b5",
    0x368090: "f0b5",
    0x368100: "f0b5",
    0x368198: "70b5",
    0x368214: "f0b5",
}
POST_PURCHASE_SCENE = 0x3C22F2  # bl inside MainStoreDialogState::handlePostPurchaseFlow
# HUD::animateIcon(double, CCNode*) builds a pulse sequence whose step count comes
# from its double argument. With zero steps CCSequence::actionsWithArray returns
# NULL and the next store writes through it; a local buy reached that from
# PlayerLogic::credit -> HUD::onCurrencyEarned. The empty case now returns.
HUD_ANIMATION_EMPTY = 0x476C86  # beq 0x476D2E (build the sequence)
HUD_ANIMATION_EXIT = 0x476D5E  # add sp, #0x20 ... pop {r4-r7, pc}

# --- Store-card locks ------------------------------------------------------------
RETURN_TRUE = {
    0x3F5D10: "38b5051c",  # StoreLogic::isCurrencyItemUnlocked
    0x3F5C50: "f0b54746",  # StoreLogic::isCurrencyBuildingUnlocked
    0x3F4B8C: "70b5ca6e",  # StoreLogic::isCurrencyClothingUnlocked
    0x3F4C28: "10b58823",  # StoreLogic::hasQuestIdUnlocked ("Unlocks with Quest")
    0x3D6EE4: "38b5051c",  # ClothingLogic::isClothingUnlocked
    0x3F5BF0: "38b5051c",  # StoreLogic::isDecorationStoreUnlocked (Decor tab)
    0x3CE3C4: "10b50ff0",  # CharacterLogic::isMakeoverUnlocked
    # Classmate cards gated by player level or by owning a building of type 10.
    0x3CE2A4: "70b5041c",  # CharacterLogic::canPurchaseCharacterType
}
RETURN_FALSE = {
    0x3D6E00: "f8b5061c",  # ClothingLogic::isLocked
    0x3D6DB8: "38b5081c",  # ClothingLogic::isLockedByUnlockDateTime
}
# Hidden and seasonal store content. Items the store would normally hide can
# reference icon frames that are not in the APK, so a missing frame must not
# crash: CCSprite::initWithSpriteFrame(NULL) falls back to CCSprite::init().
INIT_WITH_SPRITE_FRAME = 0x5F5E80
CCSPRITE_INIT = 0x5F5294
SPRITE_GUARD_CAVE = 0x36819C  # inside DKLeanPlumManager::track(const char*, map) 0x368198..0x368214
SPRITE_GUARD_CAVE_END = 0x368214
RETURN_TRUE_HIDDEN = {
    0x3F5D2C: "f0b54546",  # StoreLogic::isCurrencyItemVisible (expired offers, bundles)
    0x3CFAF8: "f0b55746",  # CharacterLogic::isBuyableGameMakerVisibleInStore (celebrities)
    0x3CFCA8: "38b50c1c",  # CharacterLogic::canPurchaseBuyableGameMaker
    0x3D7D40: "f0b54746",  # ClothingLogic::isClothingQuestUnlocked (quest and event clothes)
}
# StoreLogic::getCharacterStoreItemState(type, party, level, &visible, &buyable, &isNew)
# hides a classmate type below its visibility level or with its "hidden" flag,
# and allows buying only when level-unlocked or party-gated. Both branches now
# lead to visible = 1, buyable = 1 and the game's own "new" badge logic.
CHARACTER_STATE_HIDE = 0x3F5B94  # ldr r2, [r0, #0x3c]: visibility-level check
CHARACTER_STATE_SHOW = 0x3F5BB6  # visible = 1
CHARACTER_STATE_GATE = 0x3F5BBC  # ldr r3, [r0, #0x48]: level / party gate
CHARACTER_STATE_BUY = 0x3F5BC8  # buyable = 1, isNew = !hasBeenSeen
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
# The settings dialog gets a fourth tab, RR MOD, next to HELP / SETTINGS / ALERTS.
# Its card is assets/rr_mod_card.ccb (written by patch_apk.py from the game's own
# android_settings_card.ccb), a SettingsCard whose buttons all call
# aboutButtonCallback with node tags 1..8. The callback cave passes a non-zero
# tag to Java OfflineMenu.action(int); tag 0 (the real ABOUT button) runs the
# original callback.
ABOUT_BUTTON = 0x49E434  # Settings::SettingsCard::aboutButtonCallback
ABOUT_RESUME = 0x49E438  # after the two relocated prologue instructions
CCNODE_TAG = 0x7C  # cocos2d::CCNode::getTag is ldr r0, [r0, #0x7c]
# SettingsDialogState::onInit, right after the ALERTS tab is added and enabled:
# movs r3, #0xa4; mov r1, sb; str r4, [r1, r3]  (stores the alerts card)
TAB_SPLICE = 0x3B9C34
SHARED_BUILDER = 0x61082C  # cocos2d::CCBuilder::sharedBuilder
NODE_GRAPH = 0x6109F4  # CCBuilder::nodeGraphWithFile(const char*, CCBuilderNode*, bool)
ADD_TAB = 0x4B6510  # Tabs::TabbedDialog::addTab(label, icon, node, bool)
SET_TAB_ENABLED = 0x4B6578  # Tabs::TabbedDialog::setTabEnabled(label, bool)
CONTENT_LISTENER = 0x15C  # TabbedDialogContentNode listener, set the same way for every card
TAB_LABEL = b"RR MOD"
TAB_ICON = b"button_currency.png"  # interface sheet, the store's currency tab icon
TAB_CARD = b"rr_mod_card.ccb"
# The SponsorPay offer wall is gone. These three JNI bodies are contiguous
# (0x369068..0x369170) and their Java call sites are removed by the smali patch.
ACTION_CAVE = 0x369068  # was DKSponsorPayOnChangeStatusCloseFinished (+ CloseAborted)
GRANT = 0x369118  # was DKSponsorPayOnChangeStatusError, now (int wallet, int amount)
GRANT_END = 0x369170
MENU_CLASS = b"com/pixelberrystudios/hssandroid/OfflineMenu"
# Dead DKLeanPlumManager::track bodies (their entries are bx lr) hold the rest.
TAB_CAVE = 0x368104  # inside track(const char*, double, const char*) 0x368100..0x368198
TAB_CAVE_END = 0x368198
LOCK_CAVE = 0x368014  # inside track(const char*, const char*) 0x368010..0x368090
LOCK_CAVE_END = 0x368020
GRANT_CAVE = 0x368020  # rest of that body: the grant dispatcher proper
GRANT_CAVE_END = 0x368090
LEVEL_CAVE = 0x368094  # inside track(const char*, double) 0x368090..0x368100
LEVEL_CAVE_END = 0x368100
TABLE_CAVE = 0x367FAC  # inside track(const char*) 0x367FA8..0x368010: offset tables
TABLE_CAVE_END = 0x368010

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
    POST_PURCHASE_SCENE: "fff78dfd",
    HUD_ANIMATION_EMPTY: "52d0",
    HUD_ANIMATION_EXIT: "08b01cbc",
    SET_LOCKED: "f8b58623",
    ABOUT_BUTTON: "10b5041c",
    TAB_SPLICE: "a4234946cc50",
    SHARED_BUILDER: "38b50a4c",
    NODE_GRAPH: "f0b583b0",
    ADD_TAB: "30b583b0",
    SET_TAB_ENABLED: "08b5ba23",
    ACTION_CAVE: "30b51820",
    0x3690C0: "30b51820",  # CloseAborted, overwritten by the end of the action cave
    TAB_CAVE_END: "70b51b4b",  # next track overload, must stay untouched
    INIT_WITH_SPRITE_FRAME: "70b50a1c",
    CCSPRITE_INIT: "f0b54746",
    SPRITE_GUARD_CAVE_END: "f0b54746",  # next track overload, must stay untouched
    CHARACTER_STATE_HIDE: "c26b9542",
    CHARACTER_STATE_GATE: "836cdb06",
    CLAMP_CAVE_END: "f8b5041c",  # next function, must stay untouched
    GRANT_CAVE_END: "f0b50f1c",  # next track overload, must stay untouched
    TABLE_CAVE_END: "f0b51c4b",  # next track overload, must stay untouched
    LEVEL_CAVE_END: "f0b54f46",  # next track overload, must stay untouched
    GET_SHARED_CONFIG: "38b5084d",
    GET_XP_FOR_LEVEL: "10b50129",
    GET_XP: "08b54068",
    GET_PLAYER_LEVEL: "08b5fff7",
    IS_PLAYER_MAX_LEVEL: "10b5041c",
    **{g: "08b54068" for g in GETTERS[:5]},
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
CONDITIONS = {"eq": 0, "ne": 1, "hs": 2, "lo": 3, "hi": 8, "ls": 9, "ge": 10, "lt": 11, "gt": 12, "le": 13}


class _Asm:
    """Tiny label-resolving Thumb assembler for the caves."""

    def __init__(self, base: int) -> None:
        self.base = base
        self.out = bytearray()
        self.labels: dict[str, int] = {}
        self.fixups: list[tuple[str, int, str]] = []
        self.strings: list[tuple[int, int, object]] = []

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

    def addr(self, reg: int, target: int) -> None:
        """ldr reg, [pc, #pool]; add reg, pc  -> reg = target (any address)."""
        self.strings.append((reg, self.here(), target))
        self.emit(b"\x00\x00" + _hw(0x4478 | reg))

    def lit(self, reg: int, value: int) -> None:
        """ldr reg, [pc, #pool] with a 32-bit constant."""
        self.strings.append((reg, self.here(), ("value", value)))
        self.emit(b"\x00\x00")

    def adr(self, reg: int, text: bytes) -> None:
        """ldr reg, [pc, #pool]; add reg, pc  -> reg = address of NUL-terminated text."""
        self.strings.append((reg, self.here(), text))
        self.emit(b"\x00\x00" + _hw(0x4478 | reg))

    def finish(self) -> bytes:
        for kind, src, name in self.fixups:
            dst = self.labels[name]
            code = _b_short(src, dst) if kind == "al" else _b_cond(src, CONDITIONS[kind], dst)
            self.out[src - self.base : src - self.base + 2] = code
        if self.strings:
            while len(self.out) & 3:
                self.out += b"\x00"
            pool = self.here()
            text_at = pool + 4 * len(self.strings)
            words = bytearray()
            texts = bytearray()
            for reg, ldr_addr, text in self.strings:
                slot = pool + len(words)
                imm = slot - ((ldr_addr + 4) & ~3)
                if imm < 0 or imm > 0x3FC or imm & 3:
                    raise RuntimeError(f"literal out of range at {ldr_addr:#x}")
                self.out[ldr_addr - self.base : ldr_addr - self.base + 2] = _hw(0x4800 | (reg << 8) | (imm >> 2))
                if isinstance(text, tuple):
                    words += struct.pack("<I", text[1] & 0xFFFFFFFF)
                    continue
                if isinstance(text, int):
                    target = text
                else:
                    target = text_at + len(texts)
                    texts += text + b"\x00"
                words += struct.pack("<I", (target - (ldr_addr + 2 + 4)) & 0xFFFFFFFF)
            self.out += words + texts
        return bytes(self.out)


# --- Generated code ------------------------------------------------------------------
def local_purchase() -> bytes:
    """AppStoreManager::purchase(this, id, qty) replacement.

    Credits the product's own config reward through StoreLogic::creditPurchase,
    then tells the store listeners the buy completed. No Google Play call.
    """
    a = _Asm(PURCHASE)
    # Four registers keep sp 8-byte aligned (AAPCS) for the calls below.
    a.emit(_hw(0xB570))  # push {r4, r5, r6, lr}
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
    a.emit(_hw(0xBD70))  # pop {r4, r5, r6, pc}
    blob = a.finish()
    if len(blob) > PURCHASE_SIZE:
        raise RuntimeError("local purchase does not fit")
    return blob


def offset_tables() -> tuple[bytes, int, int]:
    """Getter and credit tables of (function | 1) - table, so no relocations are needed."""
    getters = TABLE_CAVE
    credits = getters + 4 * len(GETTERS)
    blob = b"".join(struct.pack("<I", ((f | 1) - getters) & 0xFFFFFFFF) for f in GETTERS)
    blob += b"".join(struct.pack("<I", ((f | 1) - credits) & 0xFFFFFFFF) for f in WALLETS)
    if TABLE_CAVE + len(blob) > TABLE_CAVE_END:
        raise RuntimeError("offset tables do not fit")
    return blob, getters, credits


def grant_entry() -> bytes:
    """JNI DKSponsorPayOnChangeStatusError(int wallet, int amount): jump to the dispatcher."""
    return _b_wide(GRANT, GRANT_CAVE)


def grant_dispatcher(getters: int, credits: int) -> bytes:
    """(JNIEnv*, jclass, jint wallet, jint amount) -> PlayerLogic credit.

    Wallets 0..5 (5 is XP) are capped at WALLET_CAP using the matching getter.
    6 and 7 credit the XP the level routine returns (nothing at max level),
    through the same cap. push five registers + 4 bytes keeps sp 8-byte aligned.
    """
    a = _Asm(GRANT_CAVE)
    a.emit(_hw(0xB5F0))  # push {r4, r5, r6, r7, lr}
    a.emit(_hw(0xB081))  # sub sp, #4
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
    a.emit(_mov_low(6, 0))
    a.emit(_cmp_imm(4, 6))
    a.branch("lt", "capped")
    a.bl(LEVEL_CAVE)
    a.emit(_mov_low(5, 0))
    a.emit(_cmp_imm(5, 0))
    a.branch("le", "done")
    a.emit(_movs_imm(4, 5))
    a.mark("capped")
    a.addr(7, getters)
    a.emit(_hw(0x00A3))  # lsls r3, r4, #2
    a.emit(_hw(0x58FB))  # ldr r3, [r7, r3]
    a.emit(_hw(0x19DB))  # adds r3, r3, r7
    a.emit(_mov_low(0, 6))
    a.emit(_hw(0x4798))  # blx r3   -> current amount
    a.lit(1, WALLET_CAP)
    a.emit(_hw(0x4288))  # cmp r0, r1
    a.branch("hs", "done")
    a.emit(_hw(0x1A09))  # subs r1, r1, r0   room left
    a.emit(_hw(0x428D))  # cmp r5, r1
    a.branch("ls", "credit")
    a.emit(_mov_low(5, 1))
    a.mark("credit")
    a.addr(7, credits)
    a.emit(_hw(0x00A3))  # lsls r3, r4, #2
    a.emit(_hw(0x58FB))  # ldr r3, [r7, r3]
    a.emit(_hw(0x19DB))  # adds r3, r3, r7
    a.emit(_mov_low(0, 6))
    a.emit(_mov_low(1, 5))
    a.emit(_hw(0x4798))  # blx r3
    a.mark("done")
    a.emit(_hw(0xB001))  # add sp, #4
    a.emit(_hw(0xBDF0))  # pop {r4, r5, r6, r7, pc}
    blob = a.finish()
    if GRANT_CAVE + len(blob) > GRANT_CAVE_END:
        raise RuntimeError(f"grant dispatcher is {len(blob)} bytes, room for {GRANT_CAVE_END - GRANT_CAVE}")
    return blob


def level_routine() -> bytes:
    """r4 = 6 (+1 level) or 7 (max level), r6 = PlayerLogic -> r0 = XP still needed.

    +1 level: 0 at max level, else getXPForLevel(level + 1) - getXP().
    Max level: getXPForLevel(count + 1) - getXP(), count from the level table.
    """
    a = _Asm(LEVEL_CAVE)
    a.emit(_hw(0xB520))  # push {r5, lr}
    a.emit(_cmp_imm(4, 6))
    a.branch("ne", "max")
    a.emit(_mov_low(0, 6))
    a.bl(IS_PLAYER_MAX_LEVEL)
    a.emit(_cmp_imm(0, 0))
    a.branch("ne", "zero")
    a.emit(_mov_low(0, 6))
    a.bl(GET_PLAYER_LEVEL)
    a.emit(_hw(0x1C41))  # adds r1, r0, #1
    a.branch("al", "target")
    a.mark("max")
    a.bl(GET_SHARED_CONFIG)
    a.emit(_cmp_imm(0, 0))
    a.branch("eq", "zero")
    a.emit(_ldr_imm(1, 0, CONFIG_LEVEL_COUNT))
    a.emit(_hw(0x3101))  # adds r1, #1
    a.mark("target")
    a.emit(_mov_low(0, 6))
    a.bl(GET_XP_FOR_LEVEL)
    a.emit(_mov_low(5, 0))
    a.emit(_mov_low(0, 6))
    a.bl(GET_XP)
    a.emit(_hw(0x1A28))  # subs r0, r5, r0
    a.emit(_hw(0xBD20))  # pop {r5, pc}
    a.mark("zero")
    a.emit(_movs_imm(0, 0))
    a.emit(_hw(0xBD20))  # pop {r5, pc}
    blob = a.finish()
    if LEVEL_CAVE + len(blob) > LEVEL_CAVE_END:
        raise RuntimeError(f"level routine is {len(blob)} bytes, room for {LEVEL_CAVE_END - LEVEL_CAVE}")
    return blob


def action_cave() -> bytes:
    """aboutButtonCallback(this, sender) entry.

    sender->tag (CCNode +0x7c) 1..8 calls OfflineMenu.action(tag) through
    JniHelper on the cocos thread. A null sender or tag 0 runs the original
    callback: its two relocated prologue instructions, then 0x49E438.
    push {r4, r5, r6, lr} plus a 16-byte frame keeps sp 8-byte aligned; the
    1.0.0 cave left sp 4 bytes off and faulted inside JNI FindClass.
    """
    a = _Asm(ACTION_CAVE)
    a.emit(_cmp_imm(1, 0))
    a.branch("eq", "original")
    a.emit(_ldr_imm(2, 1, CCNODE_TAG))
    a.emit(_cmp_imm(2, 0))
    a.branch("eq", "original")
    a.emit(_hw(0xB570))  # push {r4, r5, r6, lr}
    a.emit(_hw(0xB084))  # sub sp, #16 (JniMethodInfo is 12 bytes)
    a.emit(_mov_low(6, 2))
    a.emit(_hw(0x4668))  # mov r0, sp
    a.adr(1, MENU_CLASS)
    a.adr(2, b"action")
    a.adr(3, b"(I)V")
    a.bl(GET_STATIC_METHOD)
    a.emit(_cmp_imm(0, 0))
    a.branch("eq", "done")
    a.emit(_hw(0x9800))  # ldr r0, [sp, #0]   env
    a.emit(_hw(0x9901))  # ldr r1, [sp, #4]   class
    a.emit(_hw(0x9A02))  # ldr r2, [sp, #8]   method
    a.emit(_mov_low(3, 6))  # tag, the one vararg
    a.emit(_ldr_imm(4, 0, 0))
    # JNINativeInterface index 141 (+0x234) is CallStaticVoidMethod(env, cls, mid, ...).
    # 142 (+0x238) is the va_list variant; 1.0.2-1.0.4 called that one, and ART
    # read the tag in r3 as a va_list pointer and faulted.
    a.emit(_movs_imm(5, 0x8D))
    a.emit(_hw(0x00AD))  # lsls r5, r5, #2   CallStaticVoidMethod
    a.emit(_hw(0x5965))  # ldr r5, [r4, r5]
    a.emit(_hw(0x47A8))  # blx r5
    a.mark("done")
    a.emit(_hw(0xB004))  # add sp, #16
    a.emit(_hw(0xBD70))  # pop {r4, r5, r6, pc}
    a.mark("original")
    a.emit(bytes.fromhex("10b5041c"))  # push {r4, lr}; adds r4, r0, #0
    a.emit(_b_wide(a.here(), ABOUT_RESUME))
    return a.finish()


def tab_cave() -> bytes:
    """Called with bl from SettingsDialogState::onInit after the ALERTS tab.

    r5 is the TabbedDialog and sb the dialog state, as at the splice. Runs the
    three instructions the bl replaced, then loads rr_mod_card.ccb and adds it
    as the RR MOD tab. If the card cannot be loaded nothing is added.
    """
    a = _Asm(TAB_CAVE)
    a.emit(_hw(0xB510))  # push {r4, lr}
    a.emit(_hw(0xB082))  # sub sp, #8 (stack argument, keeps 8-byte alignment)
    a.emit(bytes.fromhex("a4234946cc50"))  # movs r3, #0xa4; mov r1, sb; str r4, [r1, r3]
    a.bl(SHARED_BUILDER)
    a.adr(1, TAB_CARD)
    a.emit(_movs_imm(2, 0))
    a.emit(_movs_imm(3, 1))
    a.bl(NODE_GRAPH)
    a.emit(_cmp_imm(0, 0))
    a.branch("eq", "out")
    a.emit(_mov_low(4, 0))
    a.emit(_movs_imm(3, CONTENT_LISTENER >> 1))
    a.emit(_hw(0x005B))  # lsls r3, r3, #1
    a.emit(_hw(0x50E5))  # str r5, [r4, r3]
    a.emit(_movs_imm(3, 0))
    a.emit(_hw(0x9300))  # str r3, [sp, #0]
    a.emit(_mov_low(0, 5))
    a.adr(1, TAB_LABEL)
    a.adr(2, TAB_ICON)
    a.emit(_mov_low(3, 4))
    a.bl(ADD_TAB)
    a.emit(_mov_low(0, 5))
    a.adr(1, TAB_LABEL)
    a.emit(_movs_imm(2, 1))
    a.bl(SET_TAB_ENABLED)
    a.mark("out")
    a.emit(_hw(0xB002))  # add sp, #8
    a.emit(_hw(0xBD10))  # pop {r4, pc}
    blob = a.finish()
    if TAB_CAVE + len(blob) > TAB_CAVE_END:
        raise RuntimeError(f"tab cave is {len(blob)} bytes, room for {TAB_CAVE_END - TAB_CAVE}")
    return blob


def clamp_stubs() -> tuple[bytes, dict[int, int]]:
    """One stub per setter: r1 = min(r1, WALLET_CAP), then the setter's own prologue."""
    a = _Asm(CLAMP_CAVE)
    entries = {}
    for setter, original in SETTERS.items():
        entries[setter] = a.here()
        a.lit(2, WALLET_CAP)
        a.emit(_hw(0x4291))  # cmp r1, r2
        a.branch("ls", f"ok{setter:x}")
        a.emit(_mov_low(1, 2))
        a.mark(f"ok{setter:x}")
        a.emit(bytes.fromhex(original))  # push {r3-r7, lr}; adds rX, r0, #0
        a.emit(_b_wide(a.here(), setter + 4))
    blob = a.finish()
    if CLAMP_CAVE + len(blob) > CLAMP_CAVE_END:
        raise RuntimeError(f"clamp stubs are {len(blob)} bytes, room for {CLAMP_CAVE_END - CLAMP_CAVE}")
    return blob, entries


def sprite_guard() -> bytes:
    """CCSprite::initWithSpriteFrame(this, frame): a null frame becomes CCSprite::init()."""
    a = _Asm(SPRITE_GUARD_CAVE)
    a.emit(_cmp_imm(1, 0))
    a.branch("ne", "frame")
    a.emit(_b_wide(a.here(), CCSPRITE_INIT))  # tail call, lr still points at the caller
    a.mark("frame")
    a.emit(bytes.fromhex("70b50a1c"))  # push {r4, r5, r6, lr}; adds r2, r1, #0
    a.emit(_b_wide(a.here(), INIT_WITH_SPRITE_FRAME + 4))
    blob = a.finish()
    if SPRITE_GUARD_CAVE + len(blob) > SPRITE_GUARD_CAVE_END:
        raise RuntimeError("sprite guard does not fit")
    return blob


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
    checks = {
        **EXPECTED,
        **RETURN_TRUE,
        **RETURN_FALSE,
        **RETURN_TRUE_HIDDEN,
        **SETTERS,
        **LEANPLUM_TRACK,
        **TEST_PURCHASE_REQUIREMENTS,
    }
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
    for addr in LEANPLUM_TRACK:
        put(addr, BX_LR)
    put(POST_PURCHASE_SCENE, NOP + NOP)
    put(HUD_ANIMATION_EMPTY, _b_cond(HUD_ANIMATION_EMPTY, EQ, HUD_ANIMATION_EXIT))

    # Store-card locks.
    for addr in RETURN_TRUE:
        put(addr, _return_imm(1))
    for addr in RETURN_FALSE:
        put(addr, _return_imm(0))
    for addr in TEST_PURCHASE_REQUIREMENTS:
        put(addr, _movs_imm(0, 0))

    # Hidden, seasonal and celebrity content, with the missing-art guard first.
    put(SPRITE_GUARD_CAVE, sprite_guard())
    put(INIT_WITH_SPRITE_FRAME, _b_wide(INIT_WITH_SPRITE_FRAME, SPRITE_GUARD_CAVE))
    for addr in RETURN_TRUE_HIDDEN:
        put(addr, _return_imm(1))
    put(CHARACTER_STATE_HIDE, _b_short(CHARACTER_STATE_HIDE, CHARACTER_STATE_SHOW))
    put(CHARACTER_STATE_GATE, _b_short(CHARACTER_STATE_GATE, CHARACTER_STATE_BUY))

    # setLocked always clears the lock badge.
    lock = set_locked_stub(LOCK_CAVE, bytes(data[SET_LOCKED : SET_LOCKED + 4]))
    if LOCK_CAVE + len(lock) > LOCK_CAVE_END:
        raise RuntimeError("lock stub spills into the next function")
    put(LOCK_CAVE, lock)
    put(SET_LOCKED, _b_wide(SET_LOCKED, LOCK_CAVE))

    # RR MOD tab: onInit adds the card, its buttons reach OfflineMenu.action(tag),
    # and the Java side credits through GRANT on the cocos thread.
    put(TAB_CAVE, tab_cave())
    put(TAB_SPLICE, _bl(TAB_SPLICE, TAB_CAVE) + NOP)
    action = action_cave()
    if ACTION_CAVE + len(action) > GRANT:
        raise RuntimeError("action cave spills into the grant dispatcher")
    put(ACTION_CAVE, action)
    put(ABOUT_BUTTON, _b_wide(ABOUT_BUTTON, ACTION_CAVE))
    tables, getters, credits = offset_tables()
    put(TABLE_CAVE, tables)
    put(GRANT_CAVE, grant_dispatcher(getters, credits))
    put(LEVEL_CAVE, level_routine())
    put(GRANT, grant_entry())
    clamps, entries = clamp_stubs()
    put(CLAMP_CAVE, clamps)
    for setter, stub in entries.items():
        put(setter, _b_wide(setter, stub))

    _expect(data, GRANT_END, EXPECTED[GRANT_END])
    path.write_bytes(data)
