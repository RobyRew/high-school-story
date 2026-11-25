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
push {r4, r5, r6, lr}                  (four registers keep sp 8-byte aligned)
r4 = this, r5 = id
bl  LogicManager::sharedManager        0x3DD8E0
blx [vtable + 0x68]                    getStoreLogic
bl  StoreLogic::creditPurchase(id)     0x3F5EE8
bl  AppStoreManager::firePurchaseCompleted(this, id)   0x40284C
pop {r4, r5, r6, pc}
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

### Calls after a buy

The first three were neutralised because on Hollywood U they aborted the process after a buy (JNI `FindClass` faults). The currency is already credited when they run.

| Function | Address | Patch |
| --- | --- | --- |
| `SoundManager::onCurrencyEarned` | `0x41B720` | `bx lr` |
| `bl SoundManager::playEffect` inside `creditPurchase` | `0x3F6154` | two nops |
| `TelemetryManager::emitTelemetryEvent` | `0x42DCC0` | `bx lr` |
| `DKLeanPlumManager::track` ×6 | `0x367FA8`, `0x368010`, `0x368090`, `0x368100`, `0x368198`, `0x368214` | `bx lr` (bodies reused as caves) |
| `bl` to the reward scene in `handlePostPurchaseFlow` | `0x3C22F2` | two nops |
| `HUD::animateIcon` empty-sequence branch | `0x476C86` | `beq 0x476D2E` → `beq 0x476D5E` (epilogue) |

`ThumbnailTextureCache::createCharacterTypeSprite(type, gender)` (`0x4B5358`) returned NULL when the type's thumbnail texture is not in the APK (`CCTextureCache::addImage` fails), and `CharacterThumbnail::setStoreImage` (`0x456A1C`) dereferences the result at `0x456A46`. A fresh game crashed there from the admissions HUD (`AdmissionsBuildingHudState::addMenuItems` → `HUDIcon::setCharacter`) right after buying a classmate. The missing-texture branch at `0x4B538C` now branches to a stub after the special routine that returns `CCSprite::spriteWithSpriteFrame(NULL)`, an empty sprite through the NULL-frame guard, and rejoins at `0x4B5376`.

`HUD::animateIcon(double, CCNode*)` (`0x476BD0`) builds a pulse sequence whose step count comes from its `double` argument. With zero steps `CCSequence::actionsWithArray` returns NULL and `str r1, [r0, #0x1c]` faults. A local buy reached it through `PlayerLogic::credit` → `HUD::onCurrencyEarned` (tombstone in test build 10009); the empty case now returns.

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

`ClothingLogic::isLocked` (`0x3D6E00`) and `ClothingLogic::isLockedByUnlockDateTime` (`0x3D6DB8`) return false. `Store::StoreItem::setLocked(bool)` (`0x4AD47C`) branches to a 10-byte stub at `0x368014` (inside a dead `track` body) that sets `r1 = 0`, runs the two original instructions and jumps back to `0x4AD480`, so the lock badge is always cleared.

`StoreLogic::testPurchase` (`0x3F5A80`) return codes:

| Code | Meaning | Patched |
| --- | --- | --- |
| 2 | no config for this product id | no |
| 3 | one-time item already owned | no |
| 4 | clothing: `ClothingLogic::canBuyOneMore` false and a required flag clear (sites `0x3F5B20`, `0x3F5B42`) | → 0 |
| 5 | no admissions building with an open slot | no |
| 6 | clothing required-flag byte set (`0x3F5B52`) | → 0 |

Quest predicates (`QuestLogic::meetsPassiveCompletionRequirements`, `doesCharacterMeetRequirement`) and the tutorial functions are not patched. Quests and the tutorial run on the game's own logic.

## Hidden, seasonal and celebrity content

| Change | Address | Effect |
| --- | --- | --- |
| `CCSprite::initWithSpriteFrame` → guard at `0x36819C` | `0x5F5E80` | a null frame calls `CCSprite::init()` (empty sprite) instead of crashing; lets hidden items whose icons are not in the APK appear |
| `StoreLogic::isCurrencyItemVisible` → true | `0x3F5D2C` | expired offers and bundles listed |
| `CharacterLogic::isBuyableGameMakerVisibleInStore` → true | `0x3CFAF8` | celebrities (Monster High, Lea Michele) listed regardless of dates / quests |
| `CharacterLogic::canPurchaseBuyableGameMaker` → true | `0x3CFCA8` | and buyable |
| `ClothingLogic::isClothingQuestUnlocked` → true | `0x3D7D40` | quest and event clothes listed (`isVisibleInStore` = config + product + this) |
| `getCharacterStoreItemState` `0x3F5B94` → `b 0x3F5BB6`, `0x3F5BBC` → `b 0x3F5BC8` | | every classmate type visible (hidden flag `+0x41` and visibility level `+0x3C` ignored) and buyable (level `+0x2C` / party `+0x40` gates ignored); the "new" badge keeps the game's `hasBeenSeen` logic |

`isCurrencyItemVisible` only reads the config and parses sale dates with `DKDateTime` (no JNI). Test builds 10001–10002 forced it true without the sprite guard; hidden items whose icon frames are not in the APK then crashed the currency store in `CCSprite::spriteWithSpriteFrameName` from `StoreItem::configureIconSprite`.

Buildings sold only through a Google Play product (for example `hss_building_monsterhighdorm`) are still listed from `AppStoreManager::getProductIds`, which is the Play inventory and is empty offline.

## RR MOD tab

The settings dialog (`SettingsDialogState::onInit`, `0x3B9A54`) builds its tabs with `TabbedDialog::addTab(label, icon, node, false)` (`0x4B6510`) and `setTabEnabled(label, true)` (`0x4B6578`); each card comes from `CCBuilder::nodeGraphWithFile(file, 0, true)` (`0x6109F4`). HELP uses `help_card.ccb` / `button_help.png`, SETTINGS `android_settings_card.ccb`, ALERTS `alerts_settings_card.ccb` / `button_notifications_tab.png`.

A fourth tab, **RR MOD**, uses the store's `button_currency.png` icon:

- `0x3B9C34` (`movs r3, #0xa4; mov r1, sb; str r4, [r1, r3]`, right after the ALERTS tab) is `bl 0x368104; nop`. The cave at `0x368104` (inside a dead `DKLeanPlumManager::track` body) runs those three instructions, loads `rr_mod_card.ccb`, stores the dialog at card `+0x15C` like the other cards, and adds and enables the tab.
- `assets/rr_mod_card.ccb` is written by `patcher/rr_card.py` from the game's `android_settings_card.ccb`. The `.ccb` files are `darthkitty.Proto.CcbNode` protobufs (field numbers read from the descriptor in `libHSS.so`: 7 member name, 9 position, 10 content size, 11/12 scale, 17 tag, 59 custom class, 62 label, 63–65 sprites, 67 selector, 69 children). The card reuses the settings card's `LinenDarkest9Slice` panels (four of them), `freshman_title_18_font` titles and `button_generic06` buttons. Root class stays `SettingsCard` so selectors resolve on it, and `SettingsCard::init` is not called for it.
- Every RR button has selector `aboutButtonCallback` and a node tag. `aboutButtonCallback` (`0x49E434`) starts with `b.w 0x369068`. That cave reads `sender->m_nTag` (`CCNode +0x7C`); 0 (the real ABOUT button) or a null sender runs the two relocated prologue instructions and returns to `0x49E438`. Tags 1..16 call `OfflineMenu.action(int)` via `JniHelper::getStaticMethodInfo` (`0x35E970`) and `CallStaticVoidMethod` (`JNIEnv` `+0x234`, index 141).

| Tag | Button | Grant entry wallet, amount |
| --- | --- | --- |
| 1 / 2 | +10M COINS / +100M COINS | 0, 10,000,000 / 100,000,000 |
| 3 / 4 | +1M RINGS / +100M RINGS | 1, 1,000,000 / 100,000,000 |
| 5 / 6 | +100K BOOKS / +100M BOOKS | 2, 100,000 / 100,000,000 |
| 7 | +100M PENCILS | 3, 100,000,000 |
| 8 | +100M TICKETS | 4, 100,000,000 |
| 9 | +1 LEVEL | 6 (XP to the next level) |
| 10 | +5M XP | 5, 5,000,000 |
| 11 | MAX LEVEL | 7 (XP to the last level) |
| 12 | UNLOCK ALL | 100,000,000 to wallets 0..4, then 7, 8, 9 |
| 13 / 14 | EXPORT / IMPORT | file picker on the UI thread |
| 15 | MAX FRIENDS | 8 |
| 16 | MAX BUILDINGS | 9 |

`action` runs on the cocos thread and calls the grant entry directly, so the HUD counters move without a separate dialog. Nothing in Java grants on its own: every amount goes through the native cap. The activity comes from the public `BaseIabActivity.getInstance()`; the field `BaseIabActivity.i` is package-private, and reading it from `com.pixelberrystudios.hssandroid.OfflineMenu` threw `IllegalAccessError` (test builds 10005–10006). Failures are logged under the `RRMod` tag.

Every cave keeps `sp` 8-byte aligned at its calls. The first test build used the HWU menu-cave layout (`push {r4, lr}` + `sub sp, #12`, sp off by 4) and tapping it faulted inside ART's `JNI::FindClass` (`FindClass+50` from `getStaticMethodInfo+72`). Test builds 10002–10004 called `JNIEnv +0x238` (`CallStaticVoidMethodV`, the `va_list` variant), and ART read the tag in `r3` as a `va_list` pointer.

### Grant entry and dispatcher

The SponsorPay offer wall is dead. Its three JNI status callbacks are contiguous and 0x58 bytes each:

| JNI symbol | Address | New use |
| --- | --- | --- |
| `…DKSponsorPayOnChangeStatusCloseFinished` | `0x369068` | action cave (runs into the next body) |
| `…DKSponsorPayOnChangeStatusCloseAborted` | `0x3690C0` | strings of the action cave |
| `…DKSponsorPayOnChangeStatusError` | `0x369118` | grant entry; ends before `0x369170` (`DKSponsorPay::~DKSponsorPay`) |

JNI resolves natives by short name, so the smali declaration of `DKSponsorPayOnChangeStatusError` was changed to `(II)V`: `r2` = wallet, `r3` = amount. Wallets 0..6 tail-call the dispatcher (`b.w 0x368020`). Wallets 7..9 first get `TutorialLogic` (`LogicManager` vtable `+0x74`); if `TutorialState::isTutorialActive()` (`0x3FBE7C`, state at `TutorialLogic +0x2C`) is true they call the game's `TutorialLogic::stopTutorial()` (`0x40078C`), then `bl` the dispatcher (7) or the special routine at `0x42B788` (8, 9). Maxing the player or the characters mid-tutorial soft-locked Hollywood U's "level up" tutorial step, which waits for a character that is not at max level yet. The four Java calls to the old status callbacks in `PBNativeActivity.onActivityResult` (request code 100) are removed, and the patcher stops if any other smali still calls them.

The dispatcher (`0x368020`) null-checks `sharedManager()` and `getPlayerLogic()` (`+0x4C`):

```
wallet 0 coins    getCoins   0x3E4CAC  creditCoins    0x3E74C4
       1 rings    getHearts  0x3E4E7C  creditHearts   0x3E7500
       2 books    getStars   0x3E4D94  creditStars    0x3E74E0
       3 pencils  getPencils 0x3E4F64  creditPencils  0x3E7520
       4 tickets  getTickets 0x3E504C  creditTickets  0x3E7540
       5 XP       getXP      0x3E4B58  creditXP       0x3E4BF0
       6 +1 level:  getXPForLevel(getPlayerLevel() + 1) - getXP(), nothing if isPlayerMaxLevel()
       7 max level: getXPForLevel(levelCount + 1) - getXP(), levelCount = Config +0x58
```

`getXPForLevel(L)` (`0x3E4B28`) is 0 for L <= 1, else the XP field (`+0x10`) of entry `min(L - 2, count - 1)` of the config level table (`Config +0x54`, count at `+0x58`); `isPlayerMaxLevel(L)` is `L == count + 1`. Each wallet, XP included, is read with its getter first and the amount cut so the wallet stays at or below 2,000,000,000. Getters and credit functions are called through tables of `(function | 1) − table` at `0x367FAC` (no relocations needed). The level routine is at `0x368094`. All of these live in dead `DKLeanPlumManager::track` bodies.

### Wallet cap in the setters

Every wallet change in the game (credit, debit, promo rewards, save load) ends in `PlayerLogic::setCoins` `0x3E4CD0`, `setHearts` `0x3E4EA0`, `setStars` `0x3E4DB8`, `setPencils` `0x3E4F88`, `setTickets` `0x3E5070` or `setXP` `0x3E4B9C`. Each entry branches to a 16-byte stub at `0x368218..0x368290` that clamps `r1` at 2,000,000,000 and runs the setter's own prologue, so the game's income cannot push a wallet past the cap either.

### MAX FRIENDS and MAX BUILDINGS

`TelemetryHelper::emitActionRushed` (`0x42B784`, 0x750 bytes, builds a telemetry event for the disabled `emitTelemetryEvent`) is `bx lr`; its body holds the routine at `0x42B788`:

- **Wallet 8.** `CharacterLogic` (`LogicManager` vtable `+0x28`) keeps its characters in a `std::map<id, Character*>` with the header at `+0x5C` and the leftmost node at `+0x64` (as `CharacterLogic::getCharacter` reads it, `0x3CD5E0`). For each node (id at `+0x10`) it calls `getNumOfSkillLevelsToMax(id)` (`0x3CE5A4`) and, when positive, `addSkillPoints(id, levels)` (`0x3D4C58`), then `_Rb_tree_increment` (`0x7F4384`, not exported; found by its bytes from the HWU library).
- **Wallet 9.** `BuildingLogic` (vtable `+0x20`) → `+0x24` provider → vtable `+0x14` mutable `GameState`; buildings at `+0x38`, count at `+0x3C`. For each `Building` (type `+0x20`, id `+0x24`) with `getMaxUpgradeLevel(type)` (`0x3C86D0`, -1 when none) above its level (`+0x2C`), it writes the level, sets has-bit 4 at `+0x3C`, builds a `BuildingKey` on the stack (vptr from the `R_ARM_RELATIVE` slot `0x96C6AC` → `_ZTVN3HSS11BuildingKeyE` + 8, type, id) and calls every listener in the `std::list` at `BuildingLogic +0x1C` through vtable `+4` (`onBuildingUpgradePurchased(key, level)`), exactly as `BuildingLogic::purchaseUpgrade` (`0x3CBAE8`) does after a paid upgrade.

## Java / manifest

- `targetSdkVersion` 35, `versionName` `1.0.x`, `versionCode` `10100 + x` (test builds before 1.0.0 used 10000–10010).
- `android:debuggable` only with `patch_apk.py --debuggable` (file name ends in `_debuggable`); the release workflow fails if the manifest is debuggable.
- `android:exported="true"` on `com.leanplum.GcmBroadcastReceiver` and `AppMeasurementReceiver`, the two components in 5.4.0 with an intent-filter and no `exported`.
- `usesCleartextTraffic`, `requestLegacyExternalStorage`, `preserveLegacyExternalStorage`, `extractNativeLibs`, `org.apache.http.legacy`, `POST_NOTIFICATIONS`, `<queries>`.
- `PendingIntent` calls get `FLAG_IMMUTABLE` unless they ask for mutable, and two-argument `registerReceiver` calls get `RECEIVER_NOT_EXPORTED` on Android 13+ (`ModernCompat`). Both `smali` and `smali_classes2` are scanned.
- `windowOptOutEdgeToEdgeEnforcement` on `Theme.NoTitleBar.FullScreen`.
- `lib/armeabi` is also packaged as `lib/armeabi-v7a`.
- Save export/import (`OfflineMenu.writeExport` / `readImport`) is the HWU code with format `highschoolstory-save-1`. It covers `files/`, `shared_prefs/` and `databases/`.

## Tutorial

HSS has no `tutorialWaitForTap` in `assets/hss.lua` (the HWU acceptance-letter hook). The HSS tutorial is driven by `ScriptManager` tutorial triggers and ran through offline on a fresh game (below).

## Device runs

Phone: LG Wing, Android 10, not rooted. Test builds are named by their versionCode.

- Unpatched 5.4.0: reaches the campus offline (level 1, 3500 coins, 499 rings, 15 books, "Admit your Classmate" tutorial step, gear on the HUD).
- 10000 (fresh install): new game with no Pixelberry servers; character creation, hangouts, admissions and the scripted tutorial ran through to level 2 and the first "More Decor" quest. The first RR MOD entry aborted the process (stack alignment, above).
- 10001 installed over 10000 with the same key; the save loaded.
- 10002: the currency store crashed in `StoreItem::configureIconSprite` (forced visibility without the sprite guard, above).
- 10004: the RR MOD tab showed under ALERTS (the tab column scrolls); a button reached `getStaticMethodInfo` without the alignment fault, then aborted in `CallStaticVoidMethodV` (wrong JNI slot).
- 10006: `action` logged `IllegalAccessError` on `BaseIabActivity.i`.
- 10007: the grant buttons logged `action 1`..`action 6` and the HUD moved (300,000,640 coins, 2,000,016 rings, 100,001 books, level 3).
- 10008: 4×4 tab; +1 LEVEL and UNLOCK ALL ran to level 40; repeated +100M taps stopped at the cap (books exactly 2,000,000,000); the classmates tab listed the hidden types (Hipster, Emo) with "NEW!". Game income could still push coins past the cap.
- 10009: with the setter clamp, coins, rings and books read exactly 2,000,000,000 after collecting income; a currency buy aborted in `HUD::animateIcon` (empty sequence, above).
- 10010: the same ring-pack buy completed with no crash.
- 1.0.0 (versionCode 10100) installed over 10010; the level-40 save loaded and the tab showed the fourth row. MAX BUILDINGS and MAX FRIENDS ran with no crash and no `RRMod` failure (their effect on the save not yet inspected).
- 1.0.0 fresh game (after `pm clear com.pixelberrystudios.hssandroid`, with the save backed up through a `--debuggable` build and `run-as`): character creation and the opening tutorial ran; the RR MOD tab opened mid-tutorial; UNLOCK ALL took the new game to level 40 with every wallet at 2,000,000,000; the tutorial continued into "Enroll a friend!" with the classmate store open. No crash.
- 1.0.0 fresh game, continued: after UNLOCK ALL mid-tutorial and buying a classmate, the admissions HUD crashed in `CharacterThumbnail::setStoreImage` (NULL thumbnail sprite, above). Fixed in the same 1.0.0 build together with the tutorial stop. On the fixed build the same game bought a Street Artist classmate from the tutorial store, the admissions HUD (ADMIT / INFO / MOVE) drew, and the store showed the Monster High cards with blank pictures (types without thumbnail art) instead of crashing.
