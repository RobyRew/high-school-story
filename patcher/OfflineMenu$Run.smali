.class public Lcom/pixelberrystudios/hssandroid/OfflineMenu$Run;
.super Ljava/lang/Object;
.source "OfflineMenu.java"

# interfaces
.implements Ljava/lang/Runnable;


# instance fields
.field public final a:I

.field public final b:I


# direct methods
.method public constructor <init>(II)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput p1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Run;->a:I

    iput p2, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Run;->b:I

    return-void
.end method


# virtual methods
# Queued on the cocos GL thread. The native side of this JNI name is the grant
# dispatcher written by patcher/hss_native.py: wallet a, amount b.
.method public run()V
    .locals 2

    iget v0, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Run;->a:I

    iget v1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Run;->b:I

    invoke-static {v0, v1}, Lcom/pixelberrystudios/darthkitty/DKSponsorPay;->DKSponsorPayOnChangeStatusError(II)V

    return-void
.end method
