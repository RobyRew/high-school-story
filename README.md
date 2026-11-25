# High School Story offline patch

Patcher for a personal copy of **High School Story 5.4.0** (`com.pixelberrystudios.hssandroid`). It rewrites that client so it installs on current Android and so the ring, coin, book and bundle store pays out with no Google account and no network.

This repository does **not** contain the game. High School Story is copyright Pixelberry Studios. You supply an APK you already have. The patcher only rewrites that file.

## What it changes

| Tweak | Why |
| --- | --- |
| `targetSdkVersion` 35 | Android 15 and later refuse anything below 24, and Play Protect warns about old targets. |
| `android:exported` on the receivers that were missing it | Required before an app targeting Android 12 or later will install. |
| Cleartext HTTP, legacy storage, `org.apache.http.legacy` | The client and its SDKs still rely on them. |
| `PendingIntent` immutability and `registerReceiver` export flags | Without them the process crashes on Android 12 and 13. |
| 32-bit libraries also packaged as `armeabi-v7a` | Many phones dropped the old `armeabi` ABI name. |
| Store offline | `canPurchase`, `hasProduct` and `areProductsAvailable` no longer depend on Google Play. A buy credits the product's own reward from the game config into the local save. |
| Account and network gates | The "create an account" step and the "Network error. Cannot access currency store" cards are skipped. |
| Store-card locks | "Unlocks with Quest", level-gated classmates, the Decor tab, makeovers and date-locked clothes no longer block a buy. Quests themselves still run on the game's own logic. |
| Calls after a buy | Sound, telemetry, LeanPlum, sale-date checks and the reward scene, which call into Java after a buy, are skipped. |
| RR Mod Settings | Settings → **RR MOD** (the old ABOUT row) adds coins, rings, books, pencils, tickets or XP, and exports or imports the save. |

The server-time check from the Hollywood U patch is not needed. 5.4.0 has no server-time phase at startup and falls back to the phone clock. See [docs/REVERSE.md](docs/REVERSE.md).

## Requirements

- Python 3.9 or newer
- A JDK, 17 or newer (`java` on `PATH`, `JAVA_HOME`, or Homebrew's `openjdk@21`)
- High School Story 5.4.0, package `com.pixelberrystudios.hssandroid`

Apktool 3.0.3 and uber-apk-signer 1.3.0 are included under `tools/`. Their licenses are in `tools/THIRD_PARTY.txt`.

## Build a patched APK

```bash
python3 patcher/patch_apk.py --apk /path/to/High-School-Story-5.4.0.apk
```

The result is `dist/High-School-Story-1.0.x.apk`. The first run creates `build/offline.keystore` and signs with it. Keep that keystore if you want later builds to install as an update.

Every native patch is matched against the original 5.4.0 bytes first. Another version stops with an error instead of writing a broken library.

## Install

1. A copy signed by Pixelberry cannot be updated in place. Uninstalling it deletes its save.
2. Install the patched APK. Play Protect will say it has not seen this developer. Choose **Install anyway**.
3. Open Settings (the gear on the map), the SETTINGS tab, and tap **RR MOD** for currency and save export/import.

The client ships only 32-bit ARM code. Phones without 32-bit support (for example the Galaxy S24 and later) cannot run it.

## License

The patcher is [MIT](LICENSE). High School Story, its art, scripts and native library remain Pixelberry Studios' copyright and are not licensed by this repository.
