from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import Address, CustomerProfile


class CustomerProfileInline(admin.StackedInline):
    model = CustomerProfile
    can_delete = False


class AddressInline(admin.TabularInline):
    model = Address
    extra = 0


class UserAdmin(BaseUserAdmin):
    inlines = [CustomerProfileInline, AddressInline]


admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'user', 'city', 'address_type', 'is_default', 'phone')
    list_filter = ('address_type', 'is_default', 'city')
    search_fields = ('full_name', 'phone', 'city', 'user__username')
