from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import UserRegistrationForm, UserUpdateForm, UserProfileUpdateForm

def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # Hashes password securely
            user.save()
            
            # Save selected role
            user.profile.role = form.cleaned_data['role']
            user.profile.save()
            
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def dashboard_redirect(request):
    """Directs users to their specific dashboard based on their role."""
    if hasattr(request.user, 'profile') and request.user.profile.role == 'admin':
        return redirect('admin_dashboard')
    return redirect('customer_dashboard')

@login_required
def admin_dashboard(request):
    if request.user.profile.role != 'admin':
        messages.error(request, "Access denied. Admins only.")
        return redirect('customer_dashboard')
    return render(request, 'accounts/admin_dashboard.html')

@login_required
def customer_dashboard(request):
    if request.user.profile.role != 'customer':
        messages.error(request, "Access denied. Customers only.")
        return redirect('admin_dashboard')
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