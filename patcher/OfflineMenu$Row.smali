.class public Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;
.super Ljava/lang/Object;
.source "OfflineMenu.java"

# interfaces
.implements Landroid/view/View$OnClickListener;


# instance fields
.field private final a:Landroid/app/Activity;

.field private final b:Landroid/app/Dialog;

.field private final c:I

.field private final d:I

.field private final e:Ljava/lang/String;


# direct methods
.method public constructor <init>(Landroid/app/Activity;Landroid/app/Dialog;IILjava/lang/String;)V
    .locals 0

    invoke-direct {p0}, Ljava/lang/Object;-><init>()V

    iput-object p1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->a:Landroid/app/Activity;

    iput-object p2, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->b:Landroid/app/Dialog;

    iput p3, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->c:I

    iput p4, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->d:I

    iput-object p5, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->e:Ljava/lang/String;

    return-void
.end method


# virtual methods
# Action 0..5 is a wallet grant (coins, rings, books, pencils, tickets, XP).
# 10 export, 11 import, anything else closes the panel.
.method public onClick(Landroid/view/View;)V
    .locals 4

    iget-object p1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->a:Landroid/app/Activity;

    iget v0, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->c:I

    const/16 v1, 0xa

    if-ge v0, v1, :not_grant

    iget v1, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->d:I

    invoke-static {v0, v1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->grant(II)V

    new-instance v2, Ljava/lang/StringBuilder;

    invoke-direct {v2}, Ljava/lang/StringBuilder;-><init>()V

    const-string v3, "Added "

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    iget-object v3, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->e:Ljava/lang/String;

    invoke-virtual {v2, v3}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    invoke-virtual {v2}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v2

    invoke-static {p1, v2}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->toast(Landroid/app/Activity;Ljava/lang/String;)V

    return-void

    :not_grant
    iget-object v2, p0, Lcom/pixelberrystudios/hssandroid/OfflineMenu$Row;->b:Landroid/app/Dialog;

    invoke-virtual {v2}, Landroid/app/Dialog;->dismiss()V

    if-ne v0, v1, :not_export

    invoke-static {p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->beginExport(Landroid/app/Activity;)V

    return-void

    :not_export
    add-int/lit8 v1, v1, 0x1

    if-ne v0, v1, :close

    invoke-static {p1}, Lcom/pixelberrystudios/hssandroid/OfflineMenu;->beginImport(Landroid/app/Activity;)V

    :close
    return-void
.end method
