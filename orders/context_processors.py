from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone

from accounts.models import Shop, UserProfile

from .models import Order
from .permissions import ADMIN, CUSTOMER, OWNER, STAFF, role_of, shop_of


def order_stats(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}

    role = role_of(user)
    ctx = {"user_role": role}

    if role == ADMIN:
        ctx["shop_stats"] = {
            "total": lambda: Shop.objects.count(),
            "active": lambda: Shop.objects.filter(is_active=True).count(),
            "suspended": lambda: Shop.objects.filter(is_active=False).count(),
        }
    elif role in (CUSTOMER, STAFF, OWNER):
        shop = shop_of(user)
        closed = [Order.Status.CLAIMED, Order.Status.CANCELLED]

        def base():
            if role == CUSTOMER:
                return Order.objects.filter(customer=user)
            return Order.objects.filter(shop=shop) if shop else Order.objects.none()

        def today():
            return base().filter(created_at__date=timezone.localdate()).exclude(status=Order.Status.CANCELLED)

        ctx["order_stats"] = {
            "active": lambda: base().exclude(status__in=closed).count(),
            "ready": lambda: base().filter(status=Order.Status.READY).count(),
            "total": lambda: base().count(),
            "today_count": lambda: today().count(),
            "today_revenue": lambda: today().aggregate(s=Sum("total"))["s"] or Decimal("0"),
            "customers": lambda: UserProfile.objects.filter(
                shop=shop, role=CUSTOMER, user__is_active=True).count() if shop else 0,
            "staff": lambda: UserProfile.objects.filter(
                shop=shop, role=STAFF, user__is_active=True).count() if shop else 0,
        }
    return ctx