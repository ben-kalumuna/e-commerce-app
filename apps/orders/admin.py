from django.contrib import admin

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'product_name', 'unit_price', 'quantity', 'line_total')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'status',
        'payment_method',
        'total',
        'full_name',
        'city',
        'created_at',
    )
    list_filter = ('status', 'payment_method', 'created_at')
    search_fields = ('id', 'user__username', 'full_name', 'phone', 'city')
    list_editable = ('status',)
    readonly_fields = (
        'user',
        'payment_method',
        'subtotal',
        'service_charge',
        'total',
        'created_at',
        'updated_at',
    )
    inlines = [OrderItemInline]
