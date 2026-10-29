from django.contrib import admin

from .models import Category, Product, StockAlert


class ProductInline(admin.TabularInline):
    model = Product
    extra = 0
    fields = ('name', 'price', 'stock', 'low_stock_threshold', 'is_active', 'is_featured')
    show_change_link = True


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'parent', 'sort_order', 'is_active')
    list_filter = ('is_active', 'parent')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductInline]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'category',
        'price',
        'stock',
        'low_stock_threshold',
        'is_featured',
        'is_active',
    )
    list_filter = ('category', 'is_active', 'is_featured')
    search_fields = ('name', 'slug', 'description')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('price', 'stock', 'low_stock_threshold', 'is_featured', 'is_active')


@admin.register(StockAlert)
class StockAlertAdmin(admin.ModelAdmin):
    list_display = (
        'product',
        'severity',
        'stock_at_alert',
        'threshold_at_alert',
        'is_resolved',
        'created_at',
        'resolved_at',
    )
    list_filter = ('severity', 'is_resolved', 'created_at')
    search_fields = ('product__name',)
    readonly_fields = ('created_at', 'resolved_at')
