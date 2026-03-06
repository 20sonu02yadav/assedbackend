# signals.py
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from .models import Order, OrderStatusHistory

@receiver(pre_save, sender=Order)
def cache_old_status(sender, instance: Order, **kwargs):
    if not instance.pk:
        instance._old_status = None
        return
    old = Order.objects.filter(pk=instance.pk).only("status").first()
    instance._old_status = old.status if old else None

@receiver(post_save, sender=Order)
def create_status_history(sender, instance: Order, created: bool, **kwargs):
    if created:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            note="Order created"
        )
        return

    old_status = getattr(instance, "_old_status", None)
    if old_status and old_status != instance.status:
        OrderStatusHistory.objects.create(
            order=instance,
            status=instance.status,
            note=f"Status changed from {old_status} to {instance.status}"
        )