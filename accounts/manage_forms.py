from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.core.exceptions import ValidationError

from .forms import UserRegistrationForm
from .models import Shop

User = get_user_model()


class CustomerRegistrationForm(UserRegistrationForm):
    """Your existing registration form, minus the role choice, plus a shop choice."""
    shop = forms.ModelChoiceField(
        queryset=Shop.objects.filter(is_active=True),
        empty_label="Select your laundry shop",
        label="Laundry shop",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("role", None)


class AccountCreateForm(forms.Form):
    """Used by the owner (to create staff) and by the admin (to create an owner)."""
    username = forms.CharField(max_length=150, validators=[UnicodeUsernameValidator()])
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("That username is already taken.")
        return username

    def clean(self):
        cd = super().clean()
        p, c = cd.get("password"), cd.get("confirm_password")
        if p and c and p != c:
            self.add_error("confirm_password", "Passwords do not match.")
        if p:
            try:
                validate_password(p)
            except ValidationError as e:
                self.add_error("password", e)
        return cd


class ShopCreateForm(AccountCreateForm):
    shop_name = forms.CharField(max_length=100, label="Shop name")
    field_order = ["shop_name", "username", "email", "password", "confirm_password"]

    def clean_shop_name(self):
        name = self.cleaned_data["shop_name"].strip()
        if Shop.objects.filter(name__iexact=name).exists():
            raise ValidationError("A shop with this name already exists.")
        return name