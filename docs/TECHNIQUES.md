# Techniques

How the High School Story 5.4.0 client was taken apart, where each change was found, and how native buttons were injected into a 2015 cocos2d-x game without its source. Addresses and the per-patch reasoning are in [REVERSE.md](REVERSE.md); this file is the method.

## 1. Toolchain

| Tool | Used for |
| --- | --- |
| `apktool` 3.0.3 (`tools/apktool.jar`) | APK → smali + decoded `AndroidManifest.xml` / resources, and back |
| `uber-apk-signer` 1.3.0 | zipalign + v1/v2/v3 signing with the permanent key |
| JDK 21 (Homebrew `openjdk@21`, keg-only) | runs both jars; `keytool` for the key |
| `nm -D --defined-only -S` + `c++filt` | the dynamic symbol table of `libHSS.so` (≈38,000 exported C++ symbols) |
| Python `capstone` | Thumb disassembly of single functions or ranges |
| small Python scripts (below) | cross-references, protobuf decoding, Thumb assembling |
| `adb logcat`, tombstones (`F DEBUG`) | every on-device crash was diagnosed from these |
| `adb exec-out screencap` + `adb shell input tap` | driving the game and seeing the result |

No commercial disassembler was needed: the library keeps its symbols.

## 2. Decompiling

```bash
java -jar tools/apktool.jar d -f -o build/decoded High+School+Story_5.4.0_APKPure.apk
```

- `build/decoded/smali*/` — Dalvik bytecode as smali. The game's Java layer is thin (`BaseIabActivity`, `PBNativeActivity`, SDK wrappers); almost all logic is native.
- `build/decoded/lib/armeabi/libHSS.so` — 9.9 MB 32-bit ARM ELF, Thumb-1/Thumb-2 code.
- `build/decoded/assets/` — Lua scripts, `.ccb` UI layouts, `config.protobin` (the game config), sprite sheets (`*.plist` are protobufs here, not XML).

## 3. Finding things in `libHSS.so`

### Symbols first
```bash
nm -D --defined-only -S libHSS.so | c++filt > hss_syms.txt
```
Every class the game uses is there by name: `HSS::AppStoreManager::purchase`, `HSS::PlayerLogic::creditCoins`, `HSS::Flow::Settings::SettingsDialogState::onInit`, `cocos2d::JniHelper::getStaticMethodInfo` … The first LOAD segment is identity-mapped, so a symbol's value (low bit cleared) is also its file offset.

### Mapping from a sister game
Hollywood U 3.8.0 ships the same engine (it also uses the `HSS::` namespace). For each Hollywood U patch site the enclosing function was found by address, the same mangled name was looked up in High School Story, and the bytes at the same offset inside the function were compared. Identical or near-identical bytes confirm the site; differences flag where HSS changed (for example the `LogicManager` vtable has one more getter, so `getStoreLogic` is `+0x68` instead of `+0x64`).

### Cross-references without a disassembler database
A linear scan of every halfword for 32-bit `BL`/`BLX` encodings, decoding the target and printing the enclosing symbol, answers "who calls X" in a second:

```python
h1, h2 = struct.unpack_from('<HH', lib, a)
if (h1 & 0xF800) == 0xF000 and (h2 & 0xC000) == 0xC000:
    s = (h1 >> 10) & 1; j1 = (h2 >> 13) & 1; j2 = (h2 >> 11) & 1
    off = (s << 24) | ((1 - (j1 ^ s)) << 23) | ((1 - (j2 ^ s)) << 22) | ((h1 & 0x3FF) << 12) | ((h2 & 0x7FF) << 1)
    target = a + 4 + off - (s << 25)        # BLX: & ~3
```

### Reading literals
Thumb code loads strings and constants as `ldr rX, [pc, #imm]; add rX, pc`. Resolving that pair (`slot = ((ldr + 4) & ~3) + imm`, `target = word + add + 4`) gives the asset names a function uses — that is how `help_card.ccb`, `button_help.png` and `alerts_settings_card.ccb` were read out of `SettingsDialogState::onInit`.

### Vtables
`_ZTV…` symbols point at vtables in the data segment; walking them (after mapping virtual address → file offset through the program headers) names each slot. That gave the `LogicManager` getter offsets.

### Protobuf descriptors
Pixelberry's assets are protobufs. The serialized `FileDescriptorProto`s are embedded in the library; searching for `\x0a\x07CcbNode\x12` and decoding the enclosing `DescriptorProto` yields every field name and number of `darthkitty.Proto.CcbNode` (7 member name, 9 position, 17 tag, 59 custom class, 62 label, 67 selector, 69 children …).

## 4. Patching native code

Everything is done in Python on the raw bytes (`patcher/hss_native.py`):

- **Expect, then write.** Every site has its original bytes recorded; the patcher checks all of them before changing anything, so another game version stops with an error.
- **Small encoders.** `BL`/`B.W`, short and conditional branches, `movs`/`cmp`/`ldr` immediates, and a tiny label-resolving assembler (`_Asm`) with literal pools for strings, addresses and constants.
- **Return-value patches.** A gate such as `StoreLogic::hasQuestIdUnlocked` becomes `movs r0, #1; bx lr`.
- **Branch flips.** `beq` → `b`, `bpl` → `nop`, to skip a dialog or an error card while leaving the function intact.
- **Code caves.** New code needs room. Functions that can never run again are reused: the SponsorPay offer-wall JNI callbacks, and the bodies of the six `DKLeanPlumManager::track` overloads (their entries are patched to `bx lr`, so everything after that first halfword is dead). Each cave checks it ends before the next live function.
- **Relocating prologues.** To hook a function, its first instructions are copied into a cave, the entry becomes `b.w cave`, and the cave jumps back after them (`setLocked`, `aboutButtonCallback`, `initWithSpriteFrame`).
- **No new relocations.** A shared library cannot gain absolute addresses without relocation entries, so function tables are stored as `(function | 1) − table` and turned into addresses with `add`.
- **Reusing JNI entry points.** Adding a new JNI export would mean rebuilding the ELF hash tables. Instead an existing, dead native (`DKSponsorPayOnChangeStatusError`) gets a new body, and its smali declaration a new signature `(II)V`: ART binds natives by short name, so Java can now call native code with arguments.

## 5. Injecting native buttons (the RR MOD tab)

1. **Find how the real tabs are built.** `SettingsDialogState::onInit` calls `CCBuilder::nodeGraphWithFile("help_card.ccb")`, then `TabbedDialog::addTab(label, icon, node)` and `setTabEnabled`, once per tab.
2. **Splice a fourth call.** The three instructions after the ALERTS tab become `bl cave`; the cave runs them, loads `rr_mod_card.ccb`, stores the dialog pointer in the card like the game does for its own cards (`+0x15C`), and adds the tab with the store's currency icon.
3. **Author the card in the game's own format.** `.ccb` files are `CcbNode` protobufs. `patcher/rr_card.py` decodes the game's `android_settings_card.ccb`, keeps its panels, fonts and button art, and writes a new tree: four sections, buttons with node tags 1–14, labels in the game's bitmap font. The root stays a `SettingsCard`, so the button selectors resolve on that class.
4. **One selector, many buttons.** Every RR button uses `aboutButtonCallback`. That callback is hooked: the cave reads `sender->m_nTag` (`CCNode + 0x7C`); tag 0 (the real ABOUT button) runs the original code, any other tag calls Java `OfflineMenu.action(int)` through `JniHelper::getStaticMethodInfo` + `JNIEnv->CallStaticVoidMethod`.
5. **Back into native for the effect.** `action` calls the repurposed JNI native with `(wallet, amount)`. The native dispatcher fetches `PlayerLogic` from `LogicManager`, caps the wallet with its getter, and calls `creditCoins` / `creditHearts` / … or computes the XP for "+1 level" / "max level" from the game's level table.

## 6. Smali side

- New classes (`OfflineMenu`, `OfflineMenu$Open`, `ModernCompat`) are written directly in smali and copied into the decoded tree before `apktool b`.
- Existing methods are changed by exact-text replacement with a check that the anchor exists (`onCreate`, `onActivityResult`, the SponsorPay declarations), so a different client fails loudly.
- Android 12+ fixes are mechanical rewrites over every smali file: `PendingIntent` flags pass through `ModernCompat.pendingFlags`, two-argument `registerReceiver` through `ModernCompat.registerReceiver`.

## 7. Testing on the device

- `adb install -r` with the same key keeps the save between builds.
- `adb logcat -c`, then reproduce, then `adb logcat -d | grep -E "F DEBUG|runtime.cc|RRMod"`.
- Tombstone backtraces name the libHSS function and offset of every native crash; Java failures inside `OfflineMenu.action` are logged under the `RRMod` tag.
- Before tapping, `dumpsys activity activities` must show the game as the resumed activity on display 0 (the LG Wing has two displays, and other sessions shared the phone).

## 8. Lessons from the crashes

| Symptom (tombstone) | Cause | Fix |
| --- | --- | --- |
| fault in `JNI::FindClass+50` from `getStaticMethodInfo` | cave left `sp` 4 bytes off 8-byte alignment | caves push an even number of registers / pad the frame |
| abort in `CallStaticVoidMethodV` → `BuildArgArrayFromVarArgs` | `JNIEnv +0x238` is the `va_list` variant | use `+0x234`, `CallStaticVoidMethod(env, cls, mid, ...)` |
| `IllegalAccessError` on `BaseIabActivity.i` | the field is package-private | call the public `BaseIabActivity.getInstance()` |
| crash in `CCSprite::spriteWithSpriteFrameName` from `StoreItem::configureIconSprite` | a forced-visible store item's icon frame is not in the APK | `initWithSpriteFrame(NULL)` falls back to an empty sprite |
| wallet values near 2^31 | `+100M` taps can wrap a 32-bit counter | the native dispatcher caps every wallet at 2,000,000,000 |
