from decimal import Decimal

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from orders.models import Service
from orders.permissions import ADMIN, CUSTOMER, OWNER, STAFF, roles_required, shop_of

from .manage_forms import AccountCreateForm, ShopCreateForm
from .models import Shop, UserProfile
from .views import home_for

User = get_user_model()

# Starter services for a new shop. The owner can change names and prices.
DEFAULT_SERVICES = [("Wash load", "60.00"), ("Detergent", "10.00"), ("Fabric conditioner (Downy)", "10.00")]


def _make_account(form, role, shop):
    cd = form.cleaned_data
    user = User.objects.create_user(
        username=cd["username"], email=cd.get("email", ""), password=cd["password"]
    )
    profile, _ = UserProfile.objects.get_or_create(user=user)
    profile.role = role
    profile.shop = shop
    profile.save()
    return user


@login_required
def home(request):
    return home_for(request)


# ---------- Admin (developer): shops and owners ----------

@roles_required(ADMIN)
def shop_list(request):
    shops = Shop.objects.annotate(
        staff_count=Count("members", filter=Q(members__role=STAFF)),
        customer_count=Count("members", filter=Q(members__role=CUSTOMER)),
    )
    rows = []
    for s in shops:
        owner = s.members.filter(role=OWNER).select_related("user").first()
        rows.append({"shop": s, "owner": owner.user if owner else None})
    return render(request, "accounts/shop_list.html", {"rows": rows})


@roles_required(ADMIN)
def shop_create(request):
    form = ShopCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            shop = Shop.objects.create(name=form.cleaned_data["shop_name"])
            _make_account(form, OWNER, shop)
            Service.objects.bulk_create(
                [Service(shop=shop, name=n, price=Decimal(p)) for n, p in DEFAULT_SERVICES]
            )
        messages.success(request, f"Shop “{shop.name}” and its owner account were created.")
        return redirect("manage:shop_list")
    return render(request, "accounts/account_form.html", {
        "form": form, "title": "New shop and owner account",
        "back": "manage:shop_list", "submit": "Create shop",
    })


@require_POST
@roles_required(ADMIN)
def shop_toggle(request, pk):
    shop = get_object_or_404(Shop, pk=pk)
    shop.is_active = not shop.is_active
    shop.save(update_fields=["is_active"])
    if shop.is_active:
        messages.success(request, f"“{shop.name}” reactivated. Its owner, staff and customers can log in again.")
    else:
        messages.success(request, f"“{shop.name}” suspended. Nobody from this shop can log in until it is reactivated.")
    return redirect("manage:shop_list")


# ---------- Shop owner: staff and customers ----------

@roles_required(OWNER)
def owner_dashboard(request):
    return render(request, "accounts/owner_dashboard.html", {"shop": shop_of(request.user)})


@roles_required(OWNER)
def staff_list(request):
    people = UserProfile.objects.filter(shop=shop_of(request.user), role=STAFF) \
        .select_related("user").order_by("user__username")
    return render(request, "accounts/staff_list.html", {"people": people})


@roles_required(OWNER)
def staff_create(request):
    form = AccountCreateForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = _make_account(form, STAFF, shop_of(request.user))
        messages.success(request, f"Counter staff account “{user.username}” created.")
        return redirect("manage:staff_list")
    return render(request, "accounts/account_form.html", {
        "form": form, "title": "New counter staff account",
        "back": "manage:staff_list", "submit": "Create staff account",
    })


@roles_required(OWNER)
def customer_list(request):
    people = UserProfile.objects.filter(shop=shop_of(request.user), role=CUSTOMER) \
        .select_related("user").annotate(order_count=Count("user__orders")).order_by("user__username")
    return render(request, "accounts/customer_list.html", {"people": people})


@require_POST
@roles_required(OWNER)
def member_toggle(request, user_id):
    """Owner deactivates or reactivates their own staff or customers. Nobody else's."""
    profile = get_object_or_404(
        UserProfile.objects.select_related("user"),
        user_id=user_id, shop=shop_of(request.user), role__in=[STAFF, CUSTOMER],
    )
    user = profile.user
    user.is_active = not user.is_active
    user.save(update_fields=["is_active"])
    messages.success(request, f"“{user.username}” is now {'active' if user.is_active else 'deactivated'}.")
    return redirect("manage:staff_list" if profile.role == STAFF else "manage:customer_list")