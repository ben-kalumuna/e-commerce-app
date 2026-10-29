from django import forms
from django.contrib.auth.models import User
from django.utils.text import slugify

from apps.catalog.models import Category, Product
from apps.orders.models import Order


class DashboardProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            'name',
            'category',
            'description',
            'price',
            'compare_at_price',
            'image',
            'stock',
            'low_stock_threshold',
            'is_featured',
            'is_active',
        )
        widgets = {
            'name': forms.TextInput(attrs={'class': 'dash-input'}),
            'category': forms.Select(attrs={'class': 'dash-input'}),
            'description': forms.Textarea(attrs={'class': 'dash-input', 'rows': 4}),
            'price': forms.NumberInput(attrs={'class': 'dash-input', 'step': '0.01'}),
            'compare_at_price': forms.NumberInput(attrs={'class': 'dash-input', 'step': '0.01'}),
            'image': forms.ClearableFileInput(attrs={'class': 'dash-input'}),
            'stock': forms.NumberInput(attrs={'class': 'dash-input', 'min': 0}),
            'low_stock_threshold': forms.NumberInput(attrs={'class': 'dash-input', 'min': 0}),
            'is_featured': forms.CheckboxInput(attrs={'class': 'dash-check'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'dash-check'}),
        }

    def save(self, commit=True):
        product = super().save(commit=False)
        if not product.slug:
            product.slug = slugify(product.name)
        if commit:
            product.save()
        return product


class DashboardCategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'parent', 'sort_order', 'is_active')
        widgets = {
            'name': forms.TextInput(attrs={'class': 'dash-input'}),
            'parent': forms.Select(attrs={'class': 'dash-input'}),
            'sort_order': forms.NumberInput(attrs={'class': 'dash-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'dash-check'}),
        }

    def save(self, commit=True):
        category = super().save(commit=False)
        if not category.slug:
            category.slug = slugify(category.name)
        if commit:
            category.save()
        return category


class DashboardOrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('status', 'notes')
        widgets = {
            'status': forms.Select(attrs={'class': 'dash-input'}),
            'notes': forms.Textarea(attrs={'class': 'dash-input', 'rows': 3}),
        }


class InventoryStockForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('stock', 'is_active')
        widgets = {
            'stock': forms.NumberInput(attrs={'class': 'dash-input', 'min': 0}),
            'is_active': forms.CheckboxInput(attrs={'class': 'dash-check'}),
        }
