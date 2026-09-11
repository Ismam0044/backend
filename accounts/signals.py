from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CashBookEntry, Voucher


@receiver(post_save, sender=Voucher)
def post_cash_voucher_to_cashbook(sender, instance, created, **kwargs):
    if not created or instance.mode != Voucher.Mode.CASH:
        return
    CashBookEntry.objects.create(
        warehouse=instance.warehouse,
        date=instance.date,
        entry_type=CashBookEntry.EntryType.IN if instance.voucher_type == Voucher.VoucherType.RECEIPT else CashBookEntry.EntryType.OUT,
        amount=instance.amount,
        category=instance.get_voucher_type_display(),
        reference=f"Voucher-{instance.pk}",
        description=instance.description or f"{instance.get_voucher_type_display()} - {instance.party or ''}",
        created_by=instance.created_by,
    )
