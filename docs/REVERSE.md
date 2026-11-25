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

| Function | Address | Patch |
| --- | --- | --- |
| `SoundManager::onCurrencyEarned` | `0x41B720` | `bx lr` |
| `bl SoundManager::playEffect` inside `creditPurchase` | `0x3F6154` | two nops |
| `TelemetryManager::emitTelemetryEvent` | `0x42DCC0` | `bx lr` |
| `StoreLogic::isCurrencyItemVisible` (sale dates) | `0x3F5D2C` | return 1 |
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

`ClothingLogic::isLocked` (`0x3D6E00`) returns false. `Store::StoreItem::setLocked(bool)` (`0x4AD47C`) branches to a 10-byte stub after the menu cave (`0x3690E2`) that sets `r1 = 0`, runs the two original instructions and jumps back to `0x4AD480`, so the lock badge is always cleared.

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

The settings card is `HSS::Settings::SettingsCard`. Its ABOUT row callback `aboutButtonCallback` (`0x49E434`) now starts with `b.w 0x369068`. `assets/strings.json` `settings.about` is relabelled `RR MOD`. The settings gear is on the map HUD from the start of a new game.

The SponsorPay offer wall is dead. Its three JNI status callbacks are contiguous and 0x58 bytes each:

| JNI symbol | Address | New use |
| --- | --- | --- |
| `…DKSponsorPayOnChangeStatusCloseFinished` | `0x369068` | menu cave (runs into the next body) |
| `…DKSponsorPayOnChangeStatusCloseAborted` | `0x3690C0` | strings of the menu cave, then the `setLocked` stub |
| `…DKSponsorPayOnChangeStatusError` | `0x369118` | grant dispatcher, ends at `0x369170` (`DKSponsorPay::~DKSponsorPay`) |

The menu cave is the HWU one with the HSS class name: `JniHelper::getStaticMethodInfo` (`0x35E970`) for `com/pixelberrystudios/hssandroid/OfflineMenu.showFromGame()V`, then `CallStaticVoidMethod` (`JNIEnv` vtable `+0x238`). It runs on the cocos thread, so `showFromGame` posts the dialog to the UI thread and catches every `Throwable` so no exception is left pending in native code.

The grant dispatcher is the native body of `DKSponsorPayOnChangeStatusError`. JNI resolves natives by short name, so the smali declaration was changed to `(II)V` and the native reads `r2` = wallet and `r3` = amount:

```
wallet 0 creditCoins    0x3E74C4
       1 creditHearts   0x3E7500   (rings)
       2 creditStars    0x3E74E0   (books)
       3 creditPencils  0x3E7520
       4 creditTickets  0x3E7540
       * creditXP       0x3E4BF0
```

It null-checks `sharedManager()` and `getPlayerLogic()` (`+0x4C`). `OfflineMenu$Run` calls it through `Cocos2dxGLSurfaceView.queueEvent` (`BaseIabActivity.runOnGame`). The four Java calls to the old status callbacks in `PBNativeActivity.onActivityResult` (request code 100) are removed, and the patcher stops if any other smali still calls them.

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
