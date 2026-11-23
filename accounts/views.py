from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from orders.permissions import ADMIN, CUSTOMER, OWNER, STAFF, role_of

from .forms import UserUpdateForm, UserProfileUpdateForm
from .manage_forms import CustomerRegistrationForm


def home_for(request):
    """Send the user to the dashboard that matches their role."""
    role = role_of(request.user)
    if role == ADMIN:
        return redirect('admin_dashboard')
    if role == OWNER:
        return redirect('manage:owner_dashboard')
    if role == STAFF:
        return redirect('orders:staff_dashboard')
    if role == CUSTOMER:
        return redirect('customer_dashboard')
    logout(request)
    messages.error(request, "Your account is not active. Please contact your shop owner or the administrator.")
    return redirect('login')


def register_view(request):
    """Public registration. Always creates a customer of the chosen shop."""
    if request.method == 'POST':
        form = CustomerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # Hashes password securely
            user.save()

            profile = user.profile
            profile.role = CUSTOMER
            profile.shop = form.cleaned_data['shop']
            profile.save()

            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    else:
        form = CustomerRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard_redirect(request):
    return home_for(request)


@login_required
def admin_dashboard(request):
    if role_of(request.user) != ADMIN:
        messages.error(request, "Access denied. Administrator only.")
        return home_for(request)
    return render(request, 'accounts/admin_dashboard.html')


@login_required
def customer_dashboard(request):
    if role_of(request.user) != CUSTOMER:
        messages.error(request, "Access denied. Customers only.")
        return home_for(request)
    return render(request, 'accounts/customer_dashboard.html')


@login_required
def profile_view(request):
    if request.method == 'POST':
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = UserProfileUpdateForm(request.POST, request.FILES, instance=request.user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = UserProfileUpdateForm(instance=request.user.profile)

    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })