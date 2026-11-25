# High School Story 5.4.0 notes

These notes cover the personal offline patch of `com.pixelberrystudios.hssandroid` 5.4.0 (versionCode 200). The game is not in this repo. Addresses are offsets in `lib/armeabi/libHSS.so`. The first executable LOAD segment is identity-mapped, so a file offset is the same number as the Thumb address with the low bit cleared.

The library is stripped of `.symtab` but still exports about 38,000 dynamic symbols, including the whole `HSS::` C++ namespace. It is the same Pixelberry engine as Hollywood U 3.8.0 (the HWU library also uses the `HSS::` namespace). Each HWU patch site was looked up by its mangled name in the HWU library, the same name was looked up in the HSS library, and the bytes around the site were compared. None of the HWU addresses carry over, and some structures differ (see "LogicManager getters").

```bash
nm -D --defined-only -S lib/armeabi/libHSS.so | c++filt > hss_syms.txt
```

## Names in HSS

| Game UI | Code |
| --- | --- |
| Coins | `coins`, `PlayerLogic::creditCoins` |
| Rings (premium) | `hearts`, `PlayerLogic::creditHearts` |
| Books | `stars`, `PlayerLogic::creditStars` |
| Pencils | `pencils`, `PlayerLogic::creditPencils` |
| Tickets | `tickets`, `PlayerLogic::creditTickets` |
| XP | `PlayerLogic::creditXP` |

Store product ids in `assets/config.protobin` include `hss_rings_280` … `hss_rings_19600`, `hss_coins_28000` … `hss_coins_1960000`, `hss_books_*`, `hss_pencils_*`, `hss_multipack_*`, `hss_megapack_*`, `hss_celebrity_*`, `hss_single_item_*`, `hss_quest_dating` and `hss_ring_generator_*`. The local buy pays whatever the product's config says, so bundles pay their real contents.

## LogicManager getters

`LogicManager::sharedManager()` is `0x3DD8E0`. The getters are virtual. HSS has one more slot ahead of them than Hollywood U (`getPathLogic` at `+0x48`), so:

| Getter | HSS vtable offset | HWU offset |
| --- | --- | --- |
| `getPlayerLogic` | `+0x4C` | `+0x48` |
| `getStoreLogic` | `+0x68` | `+0x64` |

Read from `_ZTVN3HSS23VisitFriendLogicManagerE`, and the store code itself loads `[vtable+0x68]` before `StoreLogic` calls (for example `0x3C2EFA` in `MainStoreDialogState::onInit`). Using the HWU offsets would call the wrong logic object.

## Server time / offline wall

There is nothing to patch in 5.4.0:

- `BaseLoadingState` has no server-time phase. The HWU functions `onServerTimeFailure`, `onServerTimeSuccess`, `handleStartServerTimeSync` and `handleBlockOnServerTimeSync` do not exist in HSS.
- `HSS::Net::ServerTimeGenerator::getCurrentMillis` (`0x411228`) returns `base + (deviceNow - deviceAtBase)`. The constructor (`0x411284`) sets both to 0, so until a server answers it returns the phone clock.
- The unpatched 5.4.0 on the LG Wing reached the campus with the Pixelberry servers gone (`api.growmobile.com` and the game hosts do not resolve).

## Store (AppStoreManager)

| Function | Address | Patch |
| --- | --- | --- |
| `areProductsAvailable` | `0x401448` | return 1 |
| `hasProduct` | `0x4014E0` | return 1 |
| `canPurchase` | `0x401534` | return 1 |
| `purchase(id, qty)` | `0x401540` (0x22 bytes) | local buy, below |

The original `purchase` hands the product to `DKAppStore::purchase` (Google Play). The replacement, 32 bytes, is:

```
push {r4, r5, lr}
r4 = this, r5 = id
bl  LogicManager::sharedManager        0x3DD8E0
blx [vtable + 0x68]                    getStoreLogic
bl  StoreLogic::creditPurchase(id)     0x3F5EE8
bl  AppStoreManager::firePurchaseCompleted(this, id)   0x40284C
pop {r4, r5, pc}
```

`creditPurchase` runs `testPurchase` and then pays the config reward (`Config::getCurrencyStoreItemCurrencyReward` → `PlayerLogic::credit`, or the building / character / clothing / makeover credit paths).

### Account gates

| Site | Address | Original | Patch |
| --- | --- | --- | --- |
| `InGamePurchaseState::purchaseItem` busy dialog | `0x3BFE06` | `beq` | `b` |
| `purchaseItem` account check | `0x3BFE6C` | `bne` | `b` |
| `MainStoreDialogState::purchaseCurrency` busy dialog | `0x3C0DE0` | `beq` | `b` |
| `purchaseCurrency` account check | `0x3C0E44` | `beq` to error | nop |
| `ServerManager::hasPixelberryAccount` | `0x40C718` | | return 1 |
| `prepurchaseCurrency` | `0x3C0F22` | `bl sharedManager` | `b 0x3C0F7E` (the `canPurchase` → `purchaseCurrency` call) |

`prepurchaseCurrency` checks bit 8 of the game-state word at `+0x114` and bit 4 of `[+0x24]+0x20`, and shows a choice dialog when either is clear. The patch branches past both.

### "Network error. Cannot access currency store"

`MainStoreDialogState::onInit` (`0x3C237C`, 0xF14 bytes) has the same two branches as HWU:

- `0x3C29EC` `bpl` → nop, so it always takes `b 0x3C2ECC`.
- `0x3C2EE4` `b 0x3C29F0` (back into the error card) → `b` to the next instruction, which is the real pack list.

`ClothingStoreCard::initWithItems` `0x45AA68` `bne` → nop for the clothing tab's matching error.

### Calls after a buy that reach Java

These were neutralised because on Hollywood U they aborted the process after a buy (JNI `FindClass` faults on current Android). The currency is already credited when they run.

`StoreLogic::isCurrencyItemVisible` (`0x3F5D2C`) is not patched. In HSS it only reads the config and parses sale dates with `DKDateTime` (no JNI). 1.0.1 and 1.0.2 forced it true, which listed hidden currency items whose icon frames are not in the APK, and opening the currency store then crashed in `CCSprite::spriteWithSpriteFrameName` from `StoreItem::configureIconSprite`.

| Function | Address | Patch |
| --- | --- | --- |
| `SoundManager::onCurrencyEarned` | `0x41B720` | `bx lr` |
| `bl SoundManager::playEffect` inside `creditPurchase` | `0x3F6154` | two nops |
| `TelemetryManager::emitTelemetryEvent` | `0x42DCC0` | `bx lr` |
| `DKLeanPlumManager::track` ×6 | `0x367FA8`, `0x368010`, `0x368090`, `0x368100`, `0x368198`, `0x368214` | `bx lr` |
| `bl` to the reward scene in `handlePostPurchaseFlow` | `0x3C22F2` | two nops |

## Store-card locks

Return true (`movs r0, #1; bx lr`):

| Check | Address |
| --- | --- |
| `StoreLogic::isCurrencyItemUnlocked` | `0x3F5D10` |
| `StoreLogic::isCurrencyBuildingUnlocked` | `0x3F5C50` |
| `StoreLogic::isCurrencyClothingUnlocked` | `0x3F4B8C` |
| `StoreLogic::hasQuestIdUnlocked` ("Unlocks with Quest") | `0x3F4C28` |
| `ClothingLogic::isClothingUnlocked` | `0x3D6EE4` |
| `StoreLogic::isDecorationStoreUnlocked` (Decor tab) | `0x3F5BF0` |
| `CharacterLogic::isMakeoverUnlocked` | `0x3CE3C4` |
| `CharacterLogic::canPurchaseCharacterType` (classmate cards gated by level, or by owning a building of type 10) | `0x3CE2A4` |

`ClothingLogic::isLocked` (`0x3D6E00`) and `ClothingLogic::isLockedByUnlockDateTime` (`0x3D6DB8`) return false. `Store::StoreItem::setLocked(bool)` (`0x4AD47C`) branches to a 10-byte stub after the menu cave (`0x3690E2`) that sets `r1 = 0`, runs the two original instructions and jumps back to `0x4AD480`, so the lock badge is always cleared.

`StoreLogic::testPurchase` (`0x3F5A80`) return codes:

| Code | Meaning | Patched |
| --- | --- | --- |
| 2 | no config for this product id | no |
| 3 | one-time item already owned | no |
| 4 | clothing requirement (two sites `0x3F5B20`, `0x3F5B42`) | → 0 |
| 5 | no admissions building with an open slot | no |
| 6 | clothing requirement flag (`0x3F5B52`) | → 0 |

Quest predicates (`QuestLogic::meetsPassiveCompletionRequirements`, `doesCharacterMeetRequirement`) and the tutorial functions are not patched. Quests and the tutorial run on the game's own logic.

## RR Mod Settings

The settings dialog (`SettingsDialogState::onInit`, `0x3B9A54`) builds its tabs with `TabbedDialog::addTab(label, icon, node, false)` (`0x4B6510`) and `setTabEnabled(label, true)` (`0x4B6578`); each card comes from `CCBuilder::nodeGraphWithFile(file, 0, true)` (`0x6109F4`). HELP uses `help_card.ccb` / `button_help.png`, SETTINGS `android_settings_card.ccb`, ALERTS `alerts_settings_card.ccb` / `button_notifications_tab.png`.

1.0.2 adds a fourth tab, **RR MOD**, with the store's `button_currency.png` icon:

- `0x3B9C34` (`movs r3, #0xa4; mov r1, sb; str r4, [r1, r3]`, right after the ALERTS tab) is `bl 0x368104; nop`. The cave at `0x368104` (inside a dead `DKLeanPlumManager::track` body) runs those three instructions, loads `rr_mod_card.ccb`, stores the dialog at card `+0x15C` like the other cards, and adds and enables the tab.
- `assets/rr_mod_card.ccb` is written by `patcher/rr_card.py` from the game's `android_settings_card.ccb`. The `.ccb` files are `darthkitty.Proto.CcbNode` protobufs (field numbers read from the descriptor in `libHSS.so`: 7 member name, 9 position, 11/12 scale, 17 tag, 59 custom class, 62 label, 63–65 sprites, 67 selector, 69 children). The card keeps the settings card's three `LinenDarkest9Slice` panels, `freshman_title_18_font` titles and `button_generic06` buttons. Root class stays `SettingsCard` so selectors resolve on it, and `SettingsCard::init` is not called for it.
- Every RR button has selector `aboutButtonCallback` and a node tag. `aboutButtonCallback` (`0x49E434`) now starts with `b.w 0x369068`. That cave reads `sender->m_nTag` (`CCNode +0x7C`); 0 (the real ABOUT button) or a null sender runs the two relocated prologue instructions and returns to `0x49E438`. Tags 1..8 call `OfflineMenu.action(int)` via `JniHelper::getStaticMethodInfo` (`0x35E970`) and `CallStaticVoidMethod` (`JNIEnv` `+0x238`).

| Tag | Button | Java |
| --- | --- | --- |
| 1 | +10M COINS | wallet 0, 10,000,000 |
| 2 | +1M RINGS | wallet 1, 1,000,000 |
| 3 | +10K XP | wallet 5, 10,000 |
| 4 | +100K BOOKS | wallet 2, 100,000 |
| 5 | +10K PENCILS | wallet 3, 10,000 |
| 6 | +1K TICKETS | wallet 4, 1,000 |
| 7 | EXPORT | file picker on the UI thread |
| 8 | IMPORT | file picker on the UI thread |

`action` runs on the cocos thread and calls the grant dispatcher directly, so the HUD counters move without a separate dialog.

The cave frames keep `sp` 8-byte aligned (`push {r4, r5, r6, lr}` + `sub sp, #16`; the tab cave `push {r4, lr}` + `sub sp, #8`). In 1.0.0 the menu cave used the HWU layout (`push {r4, lr}` + `sub sp, #12`, sp off by 4) and tapping it faulted inside ART's `JNI::FindClass` (`FindClass+50` from `getStaticMethodInfo+72`). The local `purchase` stub had the same misalignment (`push {r4, r5, lr}`) and pushes four registers since 1.0.1. On the same phone the HWU 1.0.20 build faulted at the same `FindClass+50` from its `onServerTimeFailure` cave.

The SponsorPay offer wall is dead. Its three JNI status callbacks are contiguous and 0x58 bytes each:

| JNI symbol | Address | New use |
| --- | --- | --- |
| `…DKSponsorPayOnChangeStatusCloseFinished` | `0x369068` | action cave (runs into the next body) |
| `…DKSponsorPayOnChangeStatusCloseAborted` | `0x3690C0` | strings of the action cave |
| `…DKSponsorPayOnChangeStatusError` | `0x369118` | grant dispatcher, ends at `0x369170` (`DKSponsorPay::~DKSponsorPay`) |

The `setLocked` stub lives at `0x368014`, inside another dead `track` body.

The grant dispatcher is the native body of `DKSponsorPayOnChangeStatusError`. JNI resolves natives by short name, so the smali declaration was changed to `(II)V` and the native reads `r2` = wallet and `r3` = amount:

```
wallet 0 creditCoins    0x3E74C4
       1 creditHearts   0x3E7500   (rings)
       2 creditStars    0x3E74E0   (books)
       3 creditPencils  0x3E7520
       4 creditTickets  0x3E7540
       * creditXP       0x3E4BF0
```

It null-checks `sharedManager()` and `getPlayerLogic()` (`+0x4C`). The four Java calls to the old status callbacks in `PBNativeActivity.onActivityResult` (request code 100) are removed, and the patcher stops if any other smali still calls them.

## Java / manifest

- `targetSdkVersion` 35, `versionName` `1.0.x`, `versionCode` `10000 + x`.
- `android:exported="true"` on `com.leanplum.GcmBroadcastReceiver` and `AppMeasurementReceiver`, the two components in 5.4.0 with an intent-filter and no `exported`.
- `usesCleartextTraffic`, `requestLegacyExternalStorage`, `preserveLegacyExternalStorage`, `extractNativeLibs`, `org.apache.http.legacy`, `POST_NOTIFICATIONS`, `<queries>`.
- `PendingIntent` calls get `FLAG_IMMUTABLE` unless they ask for mutable, and two-argument `registerReceiver` calls get `RECEIVER_NOT_EXPORTED` on Android 13+ (`ModernCompat`). Both `smali` and `smali_classes2` are scanned.
- `windowOptOutEdgeToEdgeEnforcement` on `Theme.NoTitleBar.FullScreen`.
- `lib/armeabi` is also packaged as `lib/armeabi-v7a`.
- Save export/import (`OfflineMenu.writeExport` / `readImport`) is the HWU code with format `highschoolstory-save-1`. It covers `files/`, `shared_prefs/` and `databases/`.

## Tutorial

HSS has no `tutorialWaitForTap` in `assets/hss.lua` (the HWU acceptance-letter hook). The HSS tutorial is driven by `ScriptManager` tutorial triggers. Whether any first-run step blocks offline is recorded under "Device runs" below.

## Device runs

Phone: LG Wing, Android 10, not rooted.

- Unpatched 5.4.0: reaches the campus offline (level 1, 3500 coins, 499 rings, 15 books, "Admit your Classmate" tutorial step, gear on the HUD).
- 1.0.0 (fresh install, 2026-11-25): new game started with no network to Pixelberry, character creation, hangouts, admissions and the scripted tutorial ran through to level 2 and the first "More Decor" quest. Settings → SETTINGS → GENERAL shows RR MOD. Tapping it aborted the process (stack alignment, above).
- 1.0.1 installed over 1.0.0 with the same key; the level-2 save loaded.
- 1.0.2: opening the currency store from "buy more currency" crashed in `StoreItem::configureIconSprite` (the forced `isCurrencyItemVisible`, above).
- 1.0.3 installed; the RR MOD tab and a store buy have not been exercised on it yet.
