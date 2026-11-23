from django.urls import path

from . import manage_views as views

app_name = "manage"

urlpatterns = [
    path("home/", views.home, name="home"),
    path("owner/", views.owner_dashboard, name="owner_dashboard"),
    path("shops/", views.shop_list, name="shop_list"),
    path("shops/new/", views.shop_create, name="shop_create"),
    path("shops/<int:pk>/toggle/", views.shop_toggle, name="shop_toggle"),
    path("staff/", views.staff_list, name="staff_list"),
    path("staff/new/", views.staff_create, name="staff_create"),
    path("customers/", views.customer_list, name="customer_list"),
    path("members/<int:user_id>/toggle/", views.member_toggle, name="member_toggle"),
]