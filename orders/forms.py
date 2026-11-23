from decimal import Decimal

from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import Order, OrderItem, Service
from .permissions import CUSTOMER

User = get_user_model()


class OrderForm(forms.ModelForm):
    customer = forms.ModelChoiceField(queryset=User.objects.none(), label="Customer")
    cash_rendered = forms.DecimalField(
        min_value=Decimal("0"), max_digits=10, decimal_places=2, label="Cash rendered (₱)"
    )

    class Meta:
        model = Order
        fields = ["customer", "notes", "cash_rendered"]

    def __init__(self, *args, shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        if shop is not None:
            self.fields["customer"].queryset = User.objects.filter(
                is_active=True, profile__role=CUSTOMER, profile__shop=shop
            ).order_by("username")


class ItemForm(forms.ModelForm):
    service = forms.ModelChoiceField(queryset=Service.objects.none())
    quantity = forms.IntegerField(min_value=1, max_value=50)

    class Meta:
        model = OrderItem
        fields = ["service", "quantity"]

    def __init__(self, *args, shop=None, **kwargs):
        super().__init__(*args, **kwargs)
        if shop is not None:
            q = Q(is_active=True)
            if self.instance.pk:  # keep an already-used service selectable when editing
                q |= Q(pk=self.instance.service_id)
            self.fields["service"].queryset = Service.objects.filter(q, shop=shop)


class BaseItemFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        seen, count = set(), 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            count += 1
            svc = form.cleaned_data["service"]
            if svc in seen:
                raise forms.ValidationError(f"“{svc.name}” is listed twice. Combine it into one line.")
            seen.add(svc)
        if count == 0:
            raise forms.ValidationError("Add at least one item to the order.")


ItemFormSet = inlineformset_factory(
    Order, OrderItem, form=ItemForm, formset=BaseItemFormSet, extra=2, can_delete=True
)


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ["name", "price"]

    def __init__(self, *args, shop=None, **kwargs):
        self.shop = shop
        super().__init__(*args, **kwargs)

    def clean_name(self):
        name = self.cleaned_data["name"].strip()
        dup = Service.objects.filter(shop=self.shop, name__iexact=name).exclude(pk=self.instance.pk)
        if dup.exists():
            raise forms.ValidationError("You already have a service with this name.")
        return name