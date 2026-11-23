from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.db import transaction
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ItemFormSet, OrderForm, ServiceForm
from .models import Order, Service
from .permissions import (
    CUSTOMER, OWNER, STAFF, is_staff_role, role_flags, role_of, roles_required, shop_of,
)


def _scope(user):
    """Customers: own orders. Staff and owner: only their own shop's orders."""
    qs = Order.objects.select_related("customer", "created_by")
    if role_of(user) == CUSTOMER:
        return qs.filter(customer=user)
    shop = shop_of(user)
    return qs.filter(shop=shop) if shop else qs.none()


@roles_required(CUSTOMER, STAFF, OWNER)
def order_list(request):
    orders = _scope(request.user)
    status = request.GET.get("status", "")
    q = request.GET.get("q", "").strip()
    if status:
        orders = orders.filter(status=status)
    if q and is_staff_role(request.user):
        orders = orders.filter(Q(customer__username__icontains=q) | Q(claim_code__iexact=q))
    ctx = {"orders": orders, "statuses": Order.Status.choices, "status": status, "q": q}
    ctx.update(role_flags(request.user))
    return render(request, "orders/order_list.html", ctx)


@roles_required(CUSTOMER, STAFF, OWNER)
def order_detail(request, pk):
    order = get_object_or_404(_scope(request.user), pk=pk)
    ctx = {"order": order}
    ctx.update(role_flags(request.user))
    return render(request, "orders/order_detail.html", ctx)


def _cart_total(formset):
    total = Decimal("0")
    for f in formset.forms:
        d = f.cleaned_data
        if d and not d.get("DELETE"):
            total += d["service"].price * d["quantity"]
    return total


def _save_order(request, form, formset, success_msg):
    """Check cash against the server-computed total BEFORE touching the database."""
    total = _cart_total(formset)
    if form.cleaned_data["cash_rendered"] < total:
        form.add_error("cash_rendered", f"Cash is short. Total is ₱{total}.")
        return None
    with transaction.atomic():
        order = form.save(commit=False)
        if order.pk is None:
            order.created_by = request.user
        order.save()
        formset.instance = order
        formset.save()
        order.recalc_total()
        order.save()
    messages.success(request, success_msg.format(order=order))
    return order


@roles_required(STAFF)
def order_create(request):
    shop = shop_of(request.user)
    form = OrderForm(request.POST or None, instance=Order(shop=shop), shop=shop)
    formset = ItemFormSet(request.POST or None, instance=form.instance, form_kwargs={"shop": shop})
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        order = _save_order(request, form, formset,
                            "Order #{order.pk} created. Change due: ₱{order.change}.")
        if order:
            return redirect("orders:detail", pk=order.pk)
    ctx = {"form": form, "formset": formset, "title": "New order"}
    ctx.update(role_flags(request.user))
    return render(request, "orders/order_form.html", ctx)


@roles_required(STAFF)
def order_update(request, pk):
    shop = shop_of(request.user)
    order = get_object_or_404(_scope(request.user), pk=pk)
    if not order.is_editable:
        messages.error(request, "Only orders still in “Received” can be edited.")
        return redirect("orders:detail", pk=pk)
    form = OrderForm(request.POST or None, instance=order, shop=shop)
    formset = ItemFormSet(request.POST or None, instance=order, form_kwargs={"shop": shop})
    if request.method == "POST" and form.is_valid() and formset.is_valid():
        if _save_order(request, form, formset, "Order #{order.pk} updated."):
            return redirect("orders:detail", pk=pk)
    ctx = {"form": form, "formset": formset, "title": f"Edit order #{order.pk}"}
    ctx.update(role_flags(request.user))
    return render(request, "orders/order_form.html", ctx)


@require_POST
@roles_required(STAFF)
def order_advance(request, pk):
    order = get_object_or_404(_scope(request.user), pk=pk)
    nxt = order.next_status
    if nxt is None:
        messages.error(request, "This order can't move to another stage.")
    else:
        order.status = nxt
        order.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Order #{order.pk} is now “{order.get_status_display()}”.")
    return redirect("orders:detail", pk=pk)


@require_POST
@roles_required(STAFF)
def order_cancel(request, pk):
    order = get_object_or_404(_scope(request.user), pk=pk)
    if not order.is_editable:
        messages.error(request, "Only orders still in “Received” can be cancelled.")
    else:
        order.status = Order.Status.CANCELLED
        order.save(update_fields=["status", "updated_at"])
        messages.success(request, f"Order #{order.pk} cancelled.")
    return redirect("orders:detail", pk=pk)


@roles_required(OWNER)
def order_delete(request, pk):
    order = get_object_or_404(_scope(request.user), pk=pk)
    if request.method == "POST":
        order.delete()
        messages.success(request, f"Order #{pk} deleted.")
        return redirect("orders:list")
    return render(request, "orders/order_confirm_delete.html", {"order": order})


@roles_required(STAFF)
def staff_dashboard(request):
    in_progress = (
        _scope(request.user)
        .exclude(status__in=[Order.Status.CLAIMED, Order.Status.CANCELLED])
        .order_by("created_at")[:8]
    )
    return render(request, "accounts/counter_staff_dashboard.html", {"in_progress": in_progress})


@roles_required(OWNER)
def service_list(request):
    """Owner manages their shop's services and prices."""
    shop = shop_of(request.user)
    form = ServiceForm(shop=shop)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "add":
            form = ServiceForm(request.POST, shop=shop)
            if form.is_valid():
                svc = form.save(commit=False)
                svc.shop = shop
                svc.save()
                messages.success(request, f"“{svc.name}” added.")
                return redirect("orders:services")
        else:
            sid = request.POST.get("id", "")
            if not sid.isdigit():
                raise Http404
            svc = get_object_or_404(Service, pk=int(sid), shop=shop)
            if action == "toggle":
                svc.is_active = not svc.is_active
                svc.save(update_fields=["is_active"])
                messages.success(request, f"“{svc.name}” is now {'active' if svc.is_active else 'hidden'}.")
            elif action == "price":
                try:
                    price = Decimal(request.POST.get("price", "")).quantize(Decimal("0.01"))
                    valid = price.is_finite() and Decimal("0.01") <= price < Decimal("100000")
                except InvalidOperation:
                    valid = False
                if valid:
                    svc.price = price
                    svc.save(update_fields=["price"])
                    messages.success(request, f"Price of “{svc.name}” updated to ₱{price}.")
                else:
                    messages.error(request, "Enter a valid price between 0.01 and 99999.99.")
            return redirect("orders:services")
    return render(request, "orders/service_list.html",
                  {"services": Service.objects.filter(shop=shop), "form": form})