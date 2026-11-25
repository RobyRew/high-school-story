# Changelog

Each `## 1.0.x` section is used as the notes of that GitHub release. 1.0.0 lists everything the mod does; later versions list only what changed.

## 1.0.0

High School Story 5.4.0 rebuilt to run on the phone alone.

**Runs on current Android**
- `targetSdkVersion` 35, `android:exported` on the receivers that needed it, `PendingIntent` immutability and receiver export flags for Android 12–14
- Cleartext HTTP, legacy storage and `org.apache.http.legacy` kept for the 2015 SDKs; edge-to-edge opt-out for the full-screen theme
- 32-bit libraries also packaged as `armeabi-v7a`
- No server needed: 5.4.0 falls back to the phone clock when no server answers, so there is no offline wall

**Store that pays out**
- Every pack, bundle, building, outfit and classmate buys locally and credits what the game config says — no Google Play, no Pixelberry account, no network
- The account-creation step and the "Network error" store cards are skipped
- Java calls after a buy that crash on current Android (sound, telemetry, LeanPlum, reward scene, an empty HUD pulse) are skipped

**Unlocked**
- Store-card locks: *Unlocks with Quest …*, level- and building-gated classmates, the Decor tab, makeovers, date-locked clothes
- Hidden and seasonal content listed and buyable: hidden classmate types, celebrities (Monster High, Lea Michele), quest and event clothes, expired offers and bundles
- A store item or classmate whose picture is not in the APK shows an empty picture instead of crashing

**RR MOD tab** — a fourth tab in the game's own Settings dialog, drawn with the game's panels, fonts and buttons

| Row | Buttons |
| --- | --- |
| Currency | +10M COINS · +100M COINS · +1M RINGS · +100M RINGS |
| Supplies | +100K BOOKS · +100M BOOKS · +100M PENCILS · +100M TICKETS |
| Levels | +1 LEVEL · +5M XP · MAX LEVEL · UNLOCK ALL |
| Progress | MAX FRIENDS · MAX BUILDINGS · EXPORT · IMPORT |

- **+1 LEVEL** adds exactly the XP to the next level; **MAX LEVEL** the XP to the last one
- **MAX FRIENDS** raises every classmate to the top skill level; **MAX BUILDINGS** every building to its top upgrade
- **UNLOCK ALL** adds 100,000,000 of every currency, then runs MAX LEVEL, MAX FRIENDS and MAX BUILDINGS
- MAX LEVEL, MAX FRIENDS, MAX BUILDINGS and UNLOCK ALL end a running tutorial first (the game's own stop), so its "level up" steps cannot get stuck
- Every wallet (coins, rings, books, pencils, tickets, XP) is capped at 2,000,000,000 — for grants and for the game's own income
- **EXPORT / IMPORT** the real save (`files/`, `shared_prefs/`, `databases/`) as a JSON file

**Install**
- Signed with the mod's permanent key: every later release installs over this one and keeps the save
- Pixelberry's Play Store build cannot be updated in place; uninstalling it deletes its save
