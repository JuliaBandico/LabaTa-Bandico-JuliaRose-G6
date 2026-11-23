import secrets
from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Service(models.Model):
    """Priced item sold at one shop: a wash load, detergent, Downy, etc."""
    shop = models.ForeignKey("accounts.Shop", null=True, on_delete=models.CASCADE, related_name="services")
    name = models.CharField(max_length=80)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [models.UniqueConstraint(fields=["shop", "name"], name="uniq_service_per_shop")]

    def __str__(self):
        return f"{self.name} (₱{self.price})"


class Order(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        WASHING = "washing", "Washing"
        DRYING = "drying", "Drying"
        FOLDING = "folding", "Folding"
        READY = "ready", "Ready for pickup"
        CLAIMED = "claimed", "Claimed"
        CANCELLED = "cancelled", "Cancelled"

    FLOW = [Status.RECEIVED, Status.WASHING, Status.DRYING, Status.FOLDING, Status.READY, Status.CLAIMED]

    shop = models.ForeignKey("accounts.Shop", null=True, on_delete=models.PROTECT, related_name="orders")
    customer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="orders_created")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    notes = models.CharField(max_length=255, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    cash_rendered = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    claim_code = models.CharField(max_length=8, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.pk} – {self.customer}"

    @property
    def change(self):
        return self.cash_rendered - self.total

    @property
    def is_editable(self):
        return self.status == self.Status.RECEIVED

    @property
    def next_status(self):
        if self.status in (self.Status.CANCELLED, self.Status.CLAIMED):
            return None
        i = self.FLOW.index(self.status)
        return self.FLOW[i + 1]

    def recalc_total(self):
        self.total = sum((i.subtotal for i in self.items.all()), Decimal("0"))

    def save(self, *args, **kwargs):
        if not self.claim_code:
            self.claim_code = self._new_code()
        super().save(*args, **kwargs)

    @classmethod
    def _new_code(cls):
        while True:
            code = secrets.token_hex(3).upper()
            if not cls.objects.filter(claim_code=code).exists():
                return code


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    service = models.ForeignKey(Service, on_delete=models.PROTECT, related_name="order_items")
    quantity = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    unit_price = models.DecimalField(max_digits=8, decimal_places=2, editable=False)

    @property
    def subtotal(self):
        return self.unit_price * self.quantity

    def save(self, *args, **kwargs):
        if not self.unit_price:
            self.unit_price = self.service.price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} × {self.service.name}"