from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from apps.orders.models import Order, confirm_delivery_by_customer

from .forms import LoginForm, RegisterForm


def _post_login_url(user):
    if user.is_staff:
        return reverse('dashboard:overview')
    return reverse('catalog:home')


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return _post_login_url(self.request.user)

    def get_redirect_url(self):
        if self.request.user.is_authenticated:
            return _post_login_url(self.request.user)
        return super().get_redirect_url()

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['register_form'] = RegisterForm()
        ctx['show_register'] = False
        return ctx


class UserRegisterView(CreateView):
    form_class = RegisterForm
    template_name = 'accounts/login.html'
    success_url = reverse_lazy('catalog:home')

    def form_valid(self, form):
        response = super().form_valid(form)
        self.object.is_staff = False
        self.object.is_superuser = False
        self.object.save(update_fields=['is_staff', 'is_superuser'])
        login(self.request, self.object)
        messages.success(self.request, 'Welcome! Your account has been created.')
        return response

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        register_form = ctx.get('form')
        ctx['register_form'] = register_form
        ctx['form'] = LoginForm()
        ctx['show_register'] = True
        return ctx


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('catalog:home')


@login_required
def order_list(request):
    if request.user.is_staff:
        return redirect('dashboard:order_list')
    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'accounts/order_list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    if request.user.is_staff:
        return redirect('dashboard:order_detail', pk=pk)
    order = get_object_or_404(
        Order.objects.prefetch_related('items'),
        pk=pk,
        user=request.user,
    )
    return render(request, 'accounts/order_detail.html', {'order': order})


@login_required
def cancel_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == 'POST' and order.can_cancel:
        for item in order.items.select_related('product'):
            if item.product_id:
                item.product.stock += item.quantity
                item.product.save(update_fields=['stock', 'updated_at'])
        order.status = Order.Status.CANCELLED
        order.save(update_fields=['status', 'updated_at'])
        messages.success(
            request,
            f'Order #{order.pk} cancelled. Items remain in your cart so you can order again.',
        )
    else:
        messages.error(request, 'This order cannot be cancelled.')
    return redirect('accounts:order_detail', pk=order.pk)


@login_required
@require_POST
def confirm_delivery(request, pk):
    """Customer confirms they received the COD order — reflects as Delivered for admin."""
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        confirm_delivery_by_customer(order)
        messages.success(
            request,
            f'Thanks! Order #{order.pk} marked as received. '
            f'Your cart is now clear for new shopping.',
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('accounts:order_detail', pk=order.pk)
