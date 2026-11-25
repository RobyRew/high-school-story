#!/usr/bin/env python3
"""Patch a High School Story 5.4.0 APK for current Android and offline play.

The game itself is not in this repository. Pass the path to an APK you already have.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from hss_native import patch_libhss
from rr_card import build as build_rr_card

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "tools"
PATCHER = ROOT / "patcher"
PACKAGE = "com.pixelberrystudios.hssandroid"
# Tweak releases stay on 1.0.x. Bump only VERSION_PATCH.
VERSION_PATCH = 8
VERSION_NAME = f"1.0.{VERSION_PATCH}"
# 1.0.0 -> 10000. The store build is versionCode 200, so this always sorts after it.
VERSION_CODE = 10000 + VERSION_PATCH
GAME_VERSION = "5.4.0"
# Release assets: the modded build and the untouched original side by side.
APK_NAME = f"High-School-Story_{GAME_VERSION}_RR-Mod_{VERSION_NAME}.apk"
ORIGINAL_NAME = f"High-School-Story_{GAME_VERSION}_original.apk"
# One permanent key signs every build, so each release installs over the last
# and keeps the save. Locally it is build/offline.keystore (restored from the
# gitignored signing/offline.keystore copy if build/ was wiped); CI writes the
# SIGNING_KEYSTORE_B64 secret there and passes SIGNING_PASSWORD.
KEYSTORE = Path(os.environ.get("SIGNING_KEYSTORE") or ROOT / "build" / "offline.keystore")
KEYSTORE_COPY = ROOT / "signing" / "offline.keystore"
KEY_PASSWORD = os.environ.get("SIGNING_PASSWORD") or "android"
KEY_ALIAS = os.environ.get("SIGNING_ALIAS") or "hss"
EXTRA_SMALI = (
    "ModernCompat.smali",
    "OfflineMenu.smali",
    "OfflineMenu$Open.smali",
)

METHOD_RE = re.compile(r"^\.method\b.*?^\.end method", re.M | re.S)
LOCALS_RE = re.compile(r"^([ \t]*)\.locals (\d+)\s*$", re.M)
PEND_RE = re.compile(
    r"^([ \t]*)invoke-static \{([^}]*)\}, Landroid/app/PendingIntent;->"
    r"(getActivity|getActivities|getBroadcast|getService|getForegroundService)"
    r"\(([^)]*)\)Landroid/app/PendingIntent;\s*$",
    re.M,
)
RECV_RE = re.compile(
    r"^([ \t]*)invoke-virtual \{([^}]*)\}, L[^;]+;->registerReceiver"
    r"\(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;\)Landroid/content/Intent;\s*$",
    re.M,
)
RECV4_RE = re.compile(
    r"^([ \t]*)invoke-virtual \{([^}]*)\}, L[^;]+;->registerReceiver"
    r"\(Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;Ljava/lang/String;Landroid/os/Handler;\)"
    r"Landroid/content/Intent;\s*$",
    re.M,
)
SIG_RE = re.compile(r"^\.method\s+(.*?)\((.*?)\)", re.M)


def slots(descriptor: str) -> int:
    count = index = 0
    while index < len(descriptor):
        char = descriptor[index]
        if char == "[":
            while index < len(descriptor) and descriptor[index] == "[":
                index += 1
            if index < len(descriptor) and descriptor[index] == "L":
                index = descriptor.index(";", index) + 1
            else:
                index += 1
            count += 1
        elif char == "L":
            index = descriptor.index(";", index) + 1
            count += 1
        elif char in "JD":
            count += 2
            index += 1
        else:
            count += 1
            index += 1
    return count


def register_used(method: str, name: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9_/]){name}(?![A-Za-z0-9_])", method) is not None


def patch_method(method: str) -> tuple[str, int, int, int]:
    pending = list(PEND_RE.finditer(method))
    receivers = list(RECV_RE.finditer(method))
    receivers4 = list(RECV4_RE.finditer(method))
    if not pending and not receivers and not receivers4:
        return method, 0, 0, 0
    if re.search(r"^\s*\.registers\s+\d+", method, re.M) and pending:
        raise RuntimeError("a PendingIntent method uses .registers; this patcher expects .locals")

    counts = [0, 0, 0]
    if pending:
        local = LOCALS_RE.search(method)
        if not local:
            raise RuntimeError("PendingIntent method has no .locals")
        local_count = int(local.group(2))
        header = SIG_RE.search(method)
        param_slots = slots(header.group(2)) + (0 if re.search(r"\bstatic\b", header.group(1)) else 1)
        needs_extra = local_count + param_slots >= 16
        new_reg = f"v{local_count}"
        if not needs_extra:
            if register_used(method, new_reg):
                raise RuntimeError(f"{new_reg} is already used in a .locals {local_count} method")
            method = method[: local.start()] + f"{local.group(1)}.locals {local_count + 1}" + method[local.end() :]

        def rewrite(match: re.Match[str]) -> str:
            indent, regs, name, signature = match.group(1), match.group(2), match.group(3), match.group(4)
            parts = [part.strip() for part in regs.split(",") if part.strip()]
            if len(parts) < 4:
                raise RuntimeError(f"unexpected PendingIntent invoke: {match.group(0)}")
            flags = parts[3]
            destination = flags if needs_extra else new_reg
            if needs_extra and flags in parts[:3] + parts[4:]:
                raise RuntimeError(f"cannot reuse aliased flags register {flags}")
            parts[3] = destination
            counts[0] += 1
            return (
                f"{indent}invoke-static {{{flags}}}, Lcom/pixelberrystudios/hssandroid/ModernCompat;->pendingFlags(I)I\n"
                f"{indent}move-result {destination}\n"
                f"{indent}invoke-static {{{', '.join(parts)}}}, Landroid/app/PendingIntent;->"
                f"{name}({signature})Landroid/app/PendingIntent;"
            )

        method = PEND_RE.sub(rewrite, method)

    def rewrite_receiver(match: re.Match[str]) -> str:
        counts[1] += 1
        return (
            f"{match.group(1)}invoke-static {{{match.group(2)}}}, "
            "Lcom/pixelberrystudios/hssandroid/ModernCompat;->registerReceiver"
            "(Landroid/content/Context;Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;)Landroid/content/Intent;"
        )

    def rewrite_receiver4(match: re.Match[str]) -> str:
        counts[2] += 1
        return (
            f"{match.group(1)}invoke-static {{{match.group(2)}}}, "
            "Lcom/pixelberrystudios/hssandroid/ModernCompat;->registerReceiverExported"
            "(Landroid/content/Context;Landroid/content/BroadcastReceiver;Landroid/content/IntentFilter;Ljava/lang/String;Landroid/os/Handler;)Landroid/content/Intent;"
        )

    method = RECV_RE.sub(rewrite_receiver, method)
    method = RECV4_RE.sub(rewrite_receiver4, method)
    return method, counts[0], counts[1], counts[2]


def replace_once(text: str, old: str, new: str, what: str) -> str:
    if new in text:
        return text
    if old not in text:
        raise RuntimeError(f"could not find {what}; this patcher only matches the 5.4.0 client")
    return text.replace(old, new, 1)


def patch_activity(smali_root: Path) -> None:
    activity = smali_root / "com/pixelberrystudios/iab/BaseIabActivity.smali"
    source = activity.read_text(encoding="utf-8")
    needle = "    invoke-super {p0, p1}, Lcom/pixelberrystudios/googleplay/GooglePlayBaseActivity;->onCreate(Landroid/os/Bundle;)V\n"
    source = replace_once(
        source,
        needle,
        needle + "\n    invoke-static {p0}, Lcom/pixelberrystudios/hssandroid/ModernCompat;->requestNotifications(Landroid/app/Activity;)V\n",
        "BaseIabActivity.onCreate",
    )
    # Export/import results come back here first. PBNativeActivity calls super
    # before its own SponsorPay request code, so this sees every result.
    result_old = ".method protected onActivityResult(IILandroid/content/Intent;)V\n    .locals 2\n\n    .prologue\n"
    result_new = result_old + (
        "    invoke-static {p0, p1, p2, p3}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->onResult(Landroid/app/Activity;IILandroid/content/Intent;)Z\n\n"
        "    move-result v0\n\n"
        "    if-eqz v0, :rr_offline_continue\n\n"
        "    return-void\n\n"
        "    :rr_offline_continue\n"
    )
    source = replace_once(source, result_old, result_new, "BaseIabActivity.onActivityResult")
    if "runOnGame" not in source:
        source += """
.method public static runOnGame(Ljava/lang/Runnable;)V
    .locals 1

    sget-object v0, Lcom/pixelberrystudios/iab/BaseIabActivity;->i:Lcom/pixelberrystudios/iab/BaseIabActivity;

    if-eqz v0, :missing

    iget-object v0, v0, Lcom/pixelberrystudios/iab/BaseIabActivity;->j:Lorg/cocos2dx/lib/Cocos2dxGLSurfaceView;

    if-eqz v0, :missing

    invoke-virtual {v0, p0}, Lorg/cocos2dx/lib/Cocos2dxGLSurfaceView;->queueEvent(Ljava/lang/Runnable;)V

    :missing
    return-void
.end method
"""
    activity.write_text(source, encoding="utf-8")


def patch_sponsorpay(decoded: Path) -> None:
    """Repurpose the dead SponsorPay status callbacks as the mod's native entry points.

    libHSS now has the grant dispatcher behind DKSponsorPayOnChangeStatusError,
    taking (wallet, amount), and the RR Mod Settings caller in place of the two
    Close callbacks. The offer wall's own calls into them are removed.
    """
    smali_root = decoded / "smali"
    sponsor = smali_root / "com/pixelberrystudios/darthkitty/DKSponsorPay.smali"
    text = sponsor.read_text(encoding="utf-8")
    text = replace_once(
        text,
        ".method public static native DKSponsorPayOnChangeStatusError()V\n",
        ".method public static native DKSponsorPayOnChangeStatusError(II)V\n",
        "DKSponsorPayOnChangeStatusError",
    )
    sponsor.write_text(text, encoding="utf-8")

    activity = smali_root / "com/pixelberrystudios/hssandroid/PBNativeActivity.smali"
    text = activity.read_text(encoding="utf-8")
    calls = (
        "DKSponsorPayOnChangeStatusCloseFinished()V",
        "DKSponsorPayOnChangeStatusCloseAborted()V",
        "DKSponsorPayOnChangeStatusError()V",
    )
    removed = 0
    for name in calls:
        line = f"    invoke-static {{}}, Lcom/pixelberrystudios/darthkitty/DKSponsorPay;->{name}\n"
        removed += text.count(line)
        text = text.replace(line, "")
    if removed and removed != 4:
        raise RuntimeError(f"expected 4 SponsorPay status calls in PBNativeActivity, found {removed}")
    activity.write_text(text, encoding="utf-8")
    for path in (p for root in decoded.glob("smali*") for p in root.rglob("*.smali")):
        body = path.read_text(encoding="utf-8")
        if any(f"DKSponsorPay;->{name}" in body for name in calls):
            raise RuntimeError(f"{path.name} still calls a repurposed SponsorPay native")


def patch_smali_tree(decoded: Path) -> None:
    smali_root = decoded / "smali"
    destination = smali_root / "com/pixelberrystudios/hssandroid"
    for extra in EXTRA_SMALI:
        shutil.copyfile(PATCHER / extra, destination / extra)
    pending = receivers = receivers4 = 0
    for path in sorted(p for root in decoded.glob("smali*") for p in root.rglob("*.smali")):
        if path.name == "ModernCompat.smali":
            continue
        text = path.read_text(encoding="utf-8")
        if "PendingIntent;->get" not in text and "registerReceiver(" not in text:
            continue
        pieces = []
        cursor = 0
        changed = False
        for method in METHOD_RE.finditer(text):
            pieces.append(text[cursor : method.start()])
            patched, p_count, r_count, r4_count = patch_method(method.group(0))
            pieces.append(patched)
            changed = changed or patched != method.group(0)
            pending += p_count
            receivers += r_count
            receivers4 += r4_count
            cursor = method.end()
        pieces.append(text[cursor:])
        if changed:
            path.write_text("".join(pieces), encoding="utf-8")
    patch_activity(smali_root)
    patch_sponsorpay(decoded)
    print(f"smali: {pending} pending intents, {receivers} receivers, {receivers4} exported receivers")


def patch_manifest(manifest: Path) -> None:
    text = manifest.read_text(encoding="utf-8")
    text = replace_once(
        text,
        '    <uses-permission android:name="android.permission.READ_PHONE_STATE"/>\n',
        '    <uses-permission android:name="android.permission.READ_PHONE_STATE"/>\n'
        '    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>\n',
        "READ_PHONE_STATE permission",
    )
    queries = (
        "    <queries>\n"
        '        <package android:name="com.android.vending"/>\n'
        '        <package android:name="com.facebook.katana"/>\n'
        "        <intent>\n"
        '            <action android:name="android.intent.action.VIEW"/>\n'
        '            <data android:scheme="https"/>\n'
        "        </intent>\n"
        "    </queries>\n"
    )
    old_app = (
        '    <application android:allowBackup="true" android:icon="@drawable/ic_launcher" '
        'android:label="@string/app_name" android:name="com.pixelberrystudios.hssandroid.HSSApp" '
        'android:supportsRtl="true" android:theme="@style/Theme.NoTitleBar.FullScreen">\n'
    )
    new_app = (
        queries
        + '    <application android:allowBackup="true" android:extractNativeLibs="true" '
        'android:icon="@drawable/ic_launcher" android:label="@string/app_name" '
        'android:name="com.pixelberrystudios.hssandroid.HSSApp" '
        'android:preserveLegacyExternalStorage="true" android:requestLegacyExternalStorage="true" '
        'android:supportsRtl="true" android:theme="@style/Theme.NoTitleBar.FullScreen" '
        'android:usesCleartextTraffic="true">\n'
        '        <uses-library android:name="org.apache.http.legacy" android:required="false"/>\n'
    )
    text = replace_once(text, old_app, new_app, "application tag")
    # Android 12 refuses to install a component with an intent-filter and no
    # android:exported. These two are the only ones in 5.4.0.
    text = replace_once(
        text,
        '<receiver android:name="com.leanplum.GcmBroadcastReceiver"',
        '<receiver android:exported="true" android:name="com.leanplum.GcmBroadcastReceiver"',
        "LeanPlum receiver",
    )
    text = replace_once(
        text,
        '<receiver android:enabled="true" android:name="com.google.android.gms.measurement.AppMeasurementReceiver">',
        '<receiver android:enabled="true" android:exported="true" android:name="com.google.android.gms.measurement.AppMeasurementReceiver">',
        "AppMeasurement receiver",
    )
    for match in re.finditer(r"<(activity|activity-alias|service|receiver)\b([^>]*)>\s*<intent-filter", text):
        if "android:exported" not in match.group(2):
            raise RuntimeError(f"component without android:exported: {match.group(0)[:120]}")
    manifest.write_text(text, encoding="utf-8")


def patch_styles(decoded: Path) -> None:
    """Keep the full-screen theme out of Android 15's forced edge-to-edge."""
    item = '        <item name="android:windowOptOutEdgeToEdgeEnforcement">true</item>\n'
    for folder in ("values", "values-v11", "values-v14"):
        path = decoded / "res" / folder / "styles.xml"
        text = path.read_text(encoding="utf-8")
        if "windowOptOutEdgeToEdgeEnforcement" in text:
            continue
        empty = re.compile(r'(    <style name="Theme\.NoTitleBar\.FullScreen" parent="[^"]+") />\n')
        full = re.compile(r'(    <style name="Theme\.NoTitleBar\.FullScreen" parent="[^"]+">\n)')
        if empty.search(text):
            text = empty.sub(lambda m: m.group(1) + ">\n" + item + "    </style>\n", text, count=1)
        elif full.search(text):
            text = full.sub(lambda m: m.group(1) + item, text, count=1)
        else:
            raise RuntimeError(f"no Theme.NoTitleBar.FullScreen in {folder}/styles.xml")
        path.write_text(text, encoding="utf-8")


def patch_apktool_yml(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    text = re.sub(r"targetSdkVersion:\s*\d+", "targetSdkVersion: 35", text, count=1)
    text = re.sub(r"versionCode:\s*\d+", f"versionCode: {VERSION_CODE}", text, count=1)
    text = re.sub(r"versionName:\s*\S+", f"versionName: {VERSION_NAME}", text, count=1)
    if "targetSdkVersion: 35" not in text:
        raise RuntimeError("apktool.yml has no targetSdkVersion")
    path.write_text(text, encoding="utf-8")


def patch_assets(decoded: Path) -> None:
    """Write the RR MOD settings card next to the game's own cards."""
    assets = decoded / "assets"
    template = assets / "android_settings_card.ccb"
    if not template.is_file():
        raise RuntimeError("assets/android_settings_card.ccb is missing")
    (assets / "rr_mod_card.ccb").write_bytes(build_rr_card(template.read_bytes()))


def patch_native_libs(decoded: Path) -> None:
    lib = decoded / "lib"
    armeabi = lib / "armeabi"
    v7a = lib / "armeabi-v7a"
    if not (armeabi / "libHSS.so").is_file():
        raise RuntimeError("lib/armeabi/libHSS.so is missing; this is not the 5.4.0 client")
    if v7a.exists():
        shutil.rmtree(v7a)
    shutil.copytree(armeabi, v7a)
    for folder in (armeabi, v7a):
        patch_libhss(folder / "libHSS.so")
    print(f"native: offline store, account gates, store locks, RR Mod Settings, {VERSION_NAME}")


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, check=True)


def find_java(explicit: Path | None) -> Path:
    candidates = []
    if explicit:
        candidates.append(explicit)
    if "JAVA_HOME" in os.environ:
        candidates.append(Path(os.environ["JAVA_HOME"]) / "bin" / "java")
    # Homebrew installs keg-only JDKs that are not on PATH.
    candidates += [Path("/opt/homebrew/opt/openjdk@21/bin/java"), Path("/opt/homebrew/opt/openjdk/bin/java")]
    on_path = shutil.which("java")
    if on_path:
        candidates.append(Path(on_path))
    for candidate in candidates:
        if candidate.is_file():
            probe = subprocess.run([str(candidate), "-version"], capture_output=True)
            if probe.returncode == 0:
                return candidate
    sys.exit("Java 17 or newer is required. Install a JDK and pass --java or set JAVA_HOME.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apk", required=True, type=Path, help="path to High School Story 5.4.0")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / APK_NAME)
    parser.add_argument("--java", type=Path, default=None, help="java binary; defaults to JAVA_HOME or PATH")
    parser.add_argument("--work", type=Path, default=ROOT / "build" / "decoded")
    args = parser.parse_args()

    java = find_java(args.java)
    apktool = TOOLS / "apktool.jar"
    signer = TOOLS / "uber-apk-signer.jar"
    if args.work.exists():
        shutil.rmtree(args.work)
    args.work.parent.mkdir(parents=True, exist_ok=True)
    run([str(java), "-Xmx3g", "-jar", str(apktool), "d", "-f", "-o", str(args.work), str(args.apk)])
    if f'package="{PACKAGE}"' not in (args.work / "AndroidManifest.xml").read_text(encoding="utf-8"):
        sys.exit(f"{args.apk} is not {PACKAGE}")
    patch_apktool_yml(args.work / "apktool.yml")
    patch_manifest(args.work / "AndroidManifest.xml")
    patch_styles(args.work)
    patch_smali_tree(args.work)
    patch_assets(args.work)
    patch_native_libs(args.work)

    unsigned = args.work.parent / "unsigned.apk"
    run([str(java), "-Xmx3g", "-jar", str(apktool), "b", str(args.work), "-o", str(unsigned)])
    keystore = KEYSTORE
    if not keystore.exists() and KEYSTORE_COPY.exists() and "SIGNING_KEYSTORE" not in os.environ:
        keystore.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(KEYSTORE_COPY, keystore)
    if not keystore.exists():
        if os.environ.get("CI"):
            sys.exit(f"{keystore} is missing. Set the SIGNING_KEYSTORE_B64 and SIGNING_PASSWORD secrets.")
        # First local build only: create the permanent key and keep a copy.
        keystore.parent.mkdir(parents=True, exist_ok=True)
        keytool = Path(java).with_name("keytool")
        run(
            [
                str(keytool), "-genkeypair", "-keystore", str(keystore), "-alias", KEY_ALIAS,
                "-keyalg", "RSA", "-keysize", "2048", "-validity", "10000",
                "-storepass", KEY_PASSWORD, "-keypass", KEY_PASSWORD,
                "-dname", "CN=High School Story Offline, O=Local, C=US",
            ]
        )
    if not KEYSTORE_COPY.exists() and not os.environ.get("CI"):
        KEYSTORE_COPY.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(keystore, KEYSTORE_COPY)
    signed_dir = args.work.parent / "signed"
    if signed_dir.exists():
        shutil.rmtree(signed_dir)
    run(
        [
            str(java), "-jar", str(signer), "-a", str(unsigned),
            "--ks", str(keystore), "--ksAlias", KEY_ALIAS, "--ksPass", KEY_PASSWORD, "--ksKeyPass", KEY_PASSWORD,
            "-o", str(signed_dir),
        ]
    )
    signed = next(signed_dir.glob("*.apk"))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(signed, args.out)
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
