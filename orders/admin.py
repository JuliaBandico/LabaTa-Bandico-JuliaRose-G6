from django.contrib import admin

from .models import Order, OrderItem, Service


class ItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "shop", "customer", "status", "total", "created_at")
    inlines = [ItemInline]


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ("name", "shop", "price", "is_active")