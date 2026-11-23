from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect

ADMIN = "admin"            # the developer
OWNER = "shop_owner"
STAFF = "counter_staff"
CUSTOMER = "customer"


def _normalize(value):
    if not value:
        return None
    return str(value).strip().lower().replace(" ", "_").replace("-", "_")


def shop_of(user):
    profile = getattr(user, "profile", None)
    return getattr(profile, "shop", None)


def role_of(user):
    """Returns the user's role, or None if the account is not usable
    (no role, owner/staff without a shop, or the shop's subscription is suspended)."""
    if not getattr(user, "is_authenticated", False):
        return None
    if user.is_superuser:
        return ADMIN
    profile = getattr(user, "profile", None)
    role = _normalize(getattr(profile, "role", None))
    if role == ADMIN:
        return ADMIN
    if role not in (OWNER, STAFF, CUSTOMER):
        return None
    shop = getattr(profile, "shop", None)
    if shop is not None and not shop.is_active:
        return None
    if role in (OWNER, STAFF) and shop is None:
        return None
    return role


def is_staff_role(user):
    return role_of(user) in (STAFF, OWNER)


def role_flags(user):
    r = role_of(user)
    return {
        "user_role": r,
        "can_manage": r == STAFF,   # create, edit, advance, cancel orders
        "can_delete": r == OWNER,   # permanently delete an order
    }


def roles_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapper(request, *args, **kwargs):
            if role_of(request.user) not in roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect("manage:home")
            return view(request, *args, **kwargs)
        return wrapper
    return decorator