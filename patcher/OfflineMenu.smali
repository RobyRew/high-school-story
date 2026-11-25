.class public Lcom/pixelberrystudios/hssandroid/OfflineMenu;
.super Ljava/lang/Object;
.source "OfflineMenu.java"


# direct methods
.method private constructor <init>()V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    return-void
.end method

# Called from libHSS on the cocos thread when a button on the RR MOD settings
# tab is tapped; the argument is the button's node tag (assets/rr_mod_card.ccb).
# Tags 1..11 credit one wallet through the native grant dispatcher
# (DKSponsorPayOnChangeStatusError(wallet, amount)), so the HUD counters move at
# once. Wallets: 0 coins, 1 rings, 2 books, 3 pencils, 4 tickets, 5 XP,
# 6 "+1 level", 7 "max level". The native side caps every wallet at
# 2,000,000,000. Tag 12 (UNLOCK ALL) adds 100,000,000 to wallets 0..4 and then
# raises the player to the max level. 13 export and 14 import open the system
# file picker on the UI thread. A Java exception here would stay pending in
# native code, so nothing escapes; failures are logged under RRMod.
.method public static action(I)V
    .locals 5

    const-string v0, "RRMod"

    new-instance v1, Ljava/lang/StringBuilder;

    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V

    const-string v2, "action "

    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v1, p0}, Ljava/lang/StringBuilder;->append(I)Ljava/lang/StringBuilder;

    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v1

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    :try_start_0
    invoke-static {}, Lcom/pixelberrystudios/iab/BaseIabActivity;->getInstance()Lcom/pixelberrystudios/iab/BaseIabActivity;

    move-result-object v0

    if-eqz v0, :done

    const/16 v1, 0xd

    if-lt p0, v1, :not_file

    new-instance v1, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;

    invoke-direct {v1, v0, p0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;-><init>(Landroid/app/Activity;I)V

    invoke-virtual {v0, v1}, Landroid/app/Activity;->runOnUiThread(Ljava/lang/Runnable;)V

    goto :done

    :not_file
    const/16 v1, 0xc

    if-ne p0, v1, :single

    const/4 v2, 0x0

    const v3, 0x5f5e100

    :unlock_loop
    const/4 v4, 0x5

    if-ge v2, v4, :unlock_level

    invoke-static {v2, v3}, Lcom/pixelberrystudios/darthkitty/DKSponsorPay;->DKSponsorPayOnChangeStatusError(II)V

    add-int/lit8 v2, v2, 0x1

    goto :unlock_loop

    :unlock_level
    const/4 v2, 0x7

    const/4 v3, 0x0

    invoke-static {v2, v3}, Lcom/pixelberrystudios/darthkitty/DKSponsorPay;->DKSponsorPayOnChangeStatusError(II)V

    goto :done

    :single
    if-lez p0, :done

    const/16 v1, 0xc

    new-array v2, v1, [I

    fill-array-data v2, :wallets

    aget v2, v2, p0

    new-array v3, v1, [I

    fill-array-data v3, :amounts

    aget v3, v3, p0

    invoke-static {v2, v3}, Lcom/pixelberrystudios/darthkitty/DKSponsorPay;->DKSponsorPayOnChangeStatusError(II)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :failed

    :done
    return-void

    :failed
    move-exception v0

    const-string v1, "RRMod"

    const-string v2, "action failed"

    invoke-static {v1, v2, v0}, Landroid/util/Log;->w(Ljava/lang/String;Ljava/lang/String;Ljava/lang/Throwable;)I

    return-void

    # index = tag: 1 +10M coins, 2 +100M coins, 3 +1M rings, 4 +100M rings,
    # 5 +100K books, 6 +100M books, 7 +100M pencils, 8 +100M tickets,
    # 9 +1 level, 10 +5M XP, 11 max level
    :wallets
    .array-data 4
        0x0
        0x0
        0x0
        0x1
        0x1
        0x2
        0x2
        0x3
        0x4
        0x6
        0x5
        0x7
    .end array-data

    :amounts
    .array-data 4
        0x0
        0x989680
        0x5f5e100
        0xf4240
        0x5f5e100
        0x186a0
        0x5f5e100
        0x5f5e100
        0x5f5e100
        0x0
        0x4c4b40
        0x0
    .end array-data
.end method

.method public static beginExport(Landroid/app/Activity;)V
    .locals 3

    new-instance v0, Landroid/content/Intent;

    const-string v1, "android.intent.action.CREATE_DOCUMENT"

    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v1, "android.intent.category.OPENABLE"

    invoke-virtual {v0, v1}, Landroid/content/Intent;->addCategory(Ljava/lang/String;)Landroid/content/Intent;

    const-string v1, "application/json"

    invoke-virtual {v0, v1}, Landroid/content/Intent;->setType(Ljava/lang/String;)Landroid/content/Intent;

    const-string v1, "android.intent.extra.TITLE"

    const-string v2, "HighSchoolStory-save.json"

    invoke-virtual {v0, v1, v2}, Landroid/content/Intent;->putExtra(Ljava/lang/String;Ljava/lang/String;)Landroid/content/Intent;

    const/16 v1, 0x835

    invoke-virtual {p0, v0, v1}, Landroid/app/Activity;->startActivityForResult(Landroid/content/Intent;I)V

    return-void
.end method

.method public static beginImport(Landroid/app/Activity;)V
    .locals 2

    new-instance v0, Landroid/content/Intent;

    const-string v1, "android.intent.action.OPEN_DOCUMENT"

    invoke-direct {v0, v1}, Landroid/content/Intent;-><init>(Ljava/lang/String;)V

    const-string v1, "android.intent.category.OPENABLE"

    invoke-virtual {v0, v1}, Landroid/content/Intent;->addCategory(Ljava/lang/String;)Landroid/content/Intent;

    const-string v1, "*/*"

    invoke-virtual {v0, v1}, Landroid/content/Intent;->setType(Ljava/lang/String;)Landroid/content/Intent;

    const/16 v1, 0x836

    invoke-virtual {p0, v0, v1}, Landroid/app/Activity;->startActivityForResult(Landroid/content/Intent;I)V

    return-void
.end method

.method public static onResult(Landroid/app/Activity;IILandroid/content/Intent;)Z
    .locals 2

    const/4 v0, -0x1

    const/4 v1, 0x0

    if-ne p2, v0, :miss

    if-nez p3, :have

    :miss
    return v1

    :have
    const/16 v0, 0x835

    if-ne p1, v0, :imp

    invoke-virtual {p3}, Landroid/content/Intent;->getData()Landroid/net/Uri;

    move-result-object v0

    invoke-static {p0, v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->writeExport(Landroid/app/Activity;Landroid/net/Uri;)V

    const/4 v0, 0x1

    return v0

    :imp
    const/16 v0, 0x836

    if-ne p1, v0, :miss

    invoke-virtual {p3}, Landroid/content/Intent;->getData()Landroid/net/Uri;

    move-result-object v0

    invoke-static {p0, v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->readImport(Landroid/app/Activity;Landroid/net/Uri;)V

    const/4 v0, 0x1

    return v0
.end method

.method public static toast(Landroid/app/Activity;Ljava/lang/String;)V
    .locals 1

    const/4 v0, 0x1

    invoke-static {p0, p1, v0}, Landroid/widget/Toast;->makeText(Landroid/content/Context;Ljava/lang/CharSequence;I)Landroid/widget/Toast;

    move-result-object p0

    invoke-virtual {p0}, Landroid/widget/Toast;->show()V

    return-void
.end method

.method private static readAll(Ljava/io/InputStream;)[B
    .locals 4

    new-instance v0, Ljava/io/ByteArrayOutputStream;

    invoke-direct {v0}, Ljava/io/ByteArrayOutputStream;-><init>()V

    const/16 v1, 0x1000

    new-array v1, v1, [B

    :loop
    invoke-virtual {p0, v1}, Ljava/io/InputStream;->read([B)I

    move-result v2

    if-gez v2, :more

    invoke-virtual {v0}, Ljava/io/ByteArrayOutputStream;->toByteArray()[B

    move-result-object p0

    return-object p0

    :more
    const/4 v3, 0x0

    invoke-virtual {v0, v1, v3, v2}, Ljava/io/ByteArrayOutputStream;->write([BII)V

    goto :loop
.end method

.method private static addTree(Lorg/json/JSONObject;Ljava/io/File;Ljava/lang/String;)V
    .locals 6

    invoke-virtual {p1}, Ljava/io/File;->exists()Z

    move-result v0

    if-eqz v0, :done

    invoke-virtual {p1}, Ljava/io/File;->isDirectory()Z

    move-result v0

    if-eqz v0, :file

    invoke-virtual {p1}, Ljava/io/File;->listFiles()[Ljava/io/File;

    move-result-object p1

    if-eqz p1, :done

    array-length v0, p1

    const/4 v1, 0x0

    :dir
    if-ge v1, v0, :done

    aget-object v2, p1, v1

    new-instance v3, Ljava/lang/StringBuilder;

    invoke-direct {v3}, Ljava/lang/StringBuilder;-><init>()V

    invoke-virtual {v3, p2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    const-string v4, "/"

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/io/File;->getName()Ljava/lang/String;

    move-result-object v4

    invoke-virtual {v3, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v3}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v3

    invoke-static {p0, v2, v3}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->addTree(Lorg/json/JSONObject;Ljava/io/File;Ljava/lang/String;)V

    add-int/lit8 v1, v1, 0x1

    goto :dir

    :file
    new-instance v0, Ljava/io/FileInputStream;

    invoke-direct {v0, p1}, Ljava/io/FileInputStream;-><init>(Ljava/io/File;)V

    invoke-static {v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->readAll(Ljava/io/InputStream;)[B

    move-result-object p1

    invoke-virtual {v0}, Ljava/io/FileInputStream;->close()V

    const/4 v0, 0x2

    invoke-static {p1, v0}, Landroid/util/Base64;->encodeToString([BI)Ljava/lang/String;

    move-result-object p1

    invoke-virtual {p0, p2, p1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    :done
    return-void
.end method

.method private static writeExport(Landroid/app/Activity;Landroid/net/Uri;)V
    .locals 5

    :try_start_0
    new-instance v0, Lorg/json/JSONObject;

    invoke-direct {v0}, Lorg/json/JSONObject;-><init>()V

    const-string v1, "format"

    const-string v2, "highschoolstory-save-1"

    invoke-virtual {v0, v1, v2}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    const-string v1, "package"

    invoke-virtual {p0}, Landroid/app/Activity;->getPackageName()Ljava/lang/String;

    move-result-object v2

    invoke-virtual {v0, v1, v2}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    new-instance v1, Lorg/json/JSONObject;

    invoke-direct {v1}, Lorg/json/JSONObject;-><init>()V

    invoke-virtual {p0}, Landroid/app/Activity;->getFilesDir()Ljava/io/File;

    move-result-object v2

    invoke-virtual {v2}, Ljava/io/File;->getParentFile()Ljava/io/File;

    move-result-object v2

    const-string v3, "files"

    new-instance v4, Ljava/io/File;

    invoke-direct {v4, v2, v3}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-static {v1, v4, v3}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->addTree(Lorg/json/JSONObject;Ljava/io/File;Ljava/lang/String;)V

    const-string v3, "shared_prefs"

    new-instance v4, Ljava/io/File;

    invoke-direct {v4, v2, v3}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-static {v1, v4, v3}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->addTree(Lorg/json/JSONObject;Ljava/io/File;Ljava/lang/String;)V

    const-string v3, "databases"

    new-instance v4, Ljava/io/File;

    invoke-direct {v4, v2, v3}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-static {v1, v4, v3}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->addTree(Lorg/json/JSONObject;Ljava/io/File;Ljava/lang/String;)V

    const-string v2, "files"

    invoke-virtual {v0, v2, v1}, Lorg/json/JSONObject;->put(Ljava/lang/String;Ljava/lang/Object;)Lorg/json/JSONObject;

    invoke-virtual {p0}, Landroid/app/Activity;->getContentResolver()Landroid/content/ContentResolver;

    move-result-object v1

    invoke-virtual {v1, p1}, Landroid/content/ContentResolver;->openOutputStream(Landroid/net/Uri;)Ljava/io/OutputStream;

    move-result-object p1

    invoke-virtual {v0}, Lorg/json/JSONObject;->toString()Ljava/lang/String;

    move-result-object v0

    const-string v1, "UTF-8"

    invoke-virtual {v0, v1}, Ljava/lang/String;->getBytes(Ljava/lang/String;)[B

    move-result-object v0

    invoke-virtual {p1, v0}, Ljava/io/OutputStream;->write([B)V

    invoke-virtual {p1}, Ljava/io/OutputStream;->close()V

    const-string p1, "Progress exported"
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    invoke-static {p0, p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->toast(Landroid/app/Activity;Ljava/lang/String;)V

    return-void

    :catch_0
    move-exception p1

    invoke-virtual {p1}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object p1

    if-nez p1, :msg

    const-string p1, "Export failed"

    :msg
    invoke-static {p0, p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->toast(Landroid/app/Activity;Ljava/lang/String;)V

    return-void
.end method

.method private static readImport(Landroid/app/Activity;Landroid/net/Uri;)V
    .locals 7

    :try_start_0
    invoke-virtual {p0}, Landroid/app/Activity;->getContentResolver()Landroid/content/ContentResolver;

    move-result-object v0

    invoke-virtual {v0, p1}, Landroid/content/ContentResolver;->openInputStream(Landroid/net/Uri;)Ljava/io/InputStream;

    move-result-object p1

    invoke-static {p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->readAll(Ljava/io/InputStream;)[B

    move-result-object v0

    invoke-virtual {p1}, Ljava/io/InputStream;->close()V

    new-instance p1, Ljava/lang/String;

    const-string v1, "UTF-8"

    invoke-direct {p1, v0, v1}, Ljava/lang/String;-><init>([BLjava/lang/String;)V

    new-instance v0, Lorg/json/JSONObject;

    invoke-direct {v0, p1}, Lorg/json/JSONObject;-><init>(Ljava/lang/String;)V

    const-string p1, "format"

    invoke-virtual {v0, p1}, Lorg/json/JSONObject;->getString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object p1

    const-string v1, "highschoolstory-save-1"

    invoke-virtual {v1, p1}, Ljava/lang/String;->equals(Ljava/lang/Object;)Z

    move-result p1

    if-nez p1, :ok

    const-string p1, "That file is not a High School Story save"

    invoke-static {p0, p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->toast(Landroid/app/Activity;Ljava/lang/String;)V

    return-void

    :ok
    const-string p1, "files"

    invoke-virtual {v0, p1}, Lorg/json/JSONObject;->getJSONObject(Ljava/lang/String;)Lorg/json/JSONObject;

    move-result-object p1

    invoke-virtual {p0}, Landroid/app/Activity;->getFilesDir()Ljava/io/File;

    move-result-object v0

    invoke-virtual {v0}, Ljava/io/File;->getParentFile()Ljava/io/File;

    move-result-object v0

    invoke-virtual {p1}, Lorg/json/JSONObject;->keys()Ljava/util/Iterator;

    move-result-object v1

    :loop
    invoke-interface {v1}, Ljava/util/Iterator;->hasNext()Z

    move-result v2

    if-eqz v2, :restart

    invoke-interface {v1}, Ljava/util/Iterator;->next()Ljava/lang/Object;

    move-result-object v2

    check-cast v2, Ljava/lang/String;

    const-string v3, ".."

    invoke-virtual {v2, v3}, Ljava/lang/String;->contains(Ljava/lang/CharSequence;)Z

    move-result v3

    if-nez v3, :loop

    new-instance v3, Ljava/io/File;

    invoke-direct {v3, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

    invoke-virtual {v3}, Ljava/io/File;->getParentFile()Ljava/io/File;

    move-result-object v4

    invoke-virtual {v4}, Ljava/io/File;->mkdirs()Z

    invoke-virtual {p1, v2}, Lorg/json/JSONObject;->getString(Ljava/lang/String;)Ljava/lang/String;

    move-result-object v2

    const/4 v4, 0x2

    invoke-static {v2, v4}, Landroid/util/Base64;->decode(Ljava/lang/String;I)[B

    move-result-object v2

    new-instance v4, Ljava/io/FileOutputStream;

    invoke-direct {v4, v3}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    invoke-virtual {v4, v2}, Ljava/io/FileOutputStream;->write([B)V

    invoke-virtual {v4}, Ljava/io/FileOutputStream;->close()V

    goto :loop

    :restart
    new-instance p1, Landroid/content/Intent;

    invoke-virtual {p0}, Landroid/app/Activity;->getPackageManager()Landroid/content/pm/PackageManager;

    move-result-object v0

    invoke-virtual {p0}, Landroid/app/Activity;->getPackageName()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {v0, v1}, Landroid/content/pm/PackageManager;->getLaunchIntentForPackage(Ljava/lang/String;)Landroid/content/Intent;

    move-result-object p1

    const v0, 0x10008000

    invoke-virtual {p1, v0}, Landroid/content/Intent;->addFlags(I)Landroid/content/Intent;

    invoke-virtual {p0, p1}, Landroid/app/Activity;->startActivity(Landroid/content/Intent;)V

    invoke-static {}, Landroid/os/Process;->myPid()I

    move-result v5

    invoke-static {v5}, Landroid/os/Process;->killProcess(I)V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0

    return-void

    :catch_0
    move-exception p1

    invoke-virtual {p1}, Ljava/lang/Exception;->getMessage()Ljava/lang/String;

    move-result-object p1

    if-nez p1, :msg

    const-string p1, "Import failed"

    :msg
    invoke-static {p0, p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->toast(Landroid/app/Activity;Ljava/lang/String;)V

    return-void
.end method
