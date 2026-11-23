from django.urls import path

from . import views

app_name = "orders"

urlpatterns = [
    path("", views.order_list, name="list"),
    path("dashboard/", views.staff_dashboard, name="staff_dashboard"),
    path("services/", views.service_list, name="services"),
    path("new/", views.order_create, name="create"),
    path("<int:pk>/", views.order_detail, name="detail"),
    path("<int:pk>/edit/", views.order_update, name="update"),
    path("<int:pk>/advance/", views.order_advance, name="advance"),
    path("<int:pk>/cancel/", views.order_cancel, name="cancel"),
    path("<int:pk>/delete/", views.order_delete, name="delete"),
]