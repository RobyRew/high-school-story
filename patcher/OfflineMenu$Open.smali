.class public Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;
.super Ljava/lang/Object;
.source "OfflineMenu.java"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field private final a:Landroid/app/Activity;

.field private final b:I


# direct methods
.method public constructor <init>(Landroid/app/Activity;I)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->a:Landroid/app/Activity;

    iput p2, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->b:I

    return-void
.end method


# virtual methods
# Runs on the UI thread: the RR MOD tab's EXPORT (13) and IMPORT (14) buttons are
# tapped on the cocos thread, which cannot start an activity for a result.
.method public run()V
    .locals 2

    :try_start_0
    iget-object v0, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->a:Landroid/app/Activity;

    iget v1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->b:I

    const/16 p0, 0xd

    if-ne v1, p0, :import

    invoke-static {v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->beginExport(Landroid/app/Activity;)V

    goto :done

    :import
    invoke-static {v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->beginImport(Landroid/app/Activity;)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :done

    :done
    return-void
.end method
