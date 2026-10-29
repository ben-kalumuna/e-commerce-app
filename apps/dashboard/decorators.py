from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def staff_required(view_func):
    """Require authenticated staff/admin. Customers are sent back to the store."""

    @wraps(view_func)
    @login_required
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_staff:
            messages.error(request, 'You do not have admin access.')
            return redirect('catalog:home')
        return view_func(request, *args, **kwargs)

    return _wrapped


def role_home_name(user):
    if user.is_authenticated and user.is_staff:
        return 'dashboard:overview'
    return 'catalog:home'
