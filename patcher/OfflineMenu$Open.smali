.class public Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;
.super Ljava/lang/Object;
.source "OfflineMenu.java"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field private final a:Landroid/app/Activity;


# direct methods
.method public constructor <init>(Landroid/app/Activity;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->a:Landroid/app/Activity;

    return-void
.end method


# virtual methods
# Runs on the UI thread. The native ABOUT button calls in from the cocos thread,
# which has no Looper, so the Dialog is built here instead.
.method public run()V
    .locals 1

    :try_start_0
    iget-object v0, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Open;->a:Landroid/app/Activity;

    invoke-static {v0}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->show(Landroid/app/Activity;)V
    :try_end_0
    .catch Ljava/lang/Throwable; {:try_start_0 .. :try_end_0} :catch_0

    :catch_0
    return-void
.end method
